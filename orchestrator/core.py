"""Small, reviewable job lifecycle and Codex execution adapter."""

from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REASONING_EFFORTS = {"low": "low", "medium": "medium", "high": "high"}
SANDBOXES = {"read-only": "read_only", "workspace-write": "workspace_write"}
TRANSITIONS = {
    "pending": {"running", "failed"},
    "running": {"review", "failed"},
    "review": {"accepted", "rework"},
    "rework": {"pending", "running", "failed"},
    "failed": {"rework", "pending"},
    "accepted": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    job_id: str
    objective: str
    reasoning_tier: str
    prompt: str
    sandbox: str = "read-only"
    status: str = "pending"
    thread_id: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    result_location: str | None = None

    def __post_init__(self) -> None:
        if self.reasoning_tier not in REASONING_EFFORTS:
            raise ValueError("reasoning_tier must be low, medium, or high; xhigh is not supported")
        if self.sandbox not in SANDBOXES:
            raise ValueError("sandbox must be read-only or workspace-write")
        if self.status not in TRANSITIONS:
            raise ValueError(f"invalid job status: {self.status}")
        self.created_at = self.created_at or _now()

    def transition(self, status: str) -> None:
        if status not in TRANSITIONS:
            raise ValueError(f"invalid job status: {status}")
        if status not in TRANSITIONS[self.status]:
            raise ValueError(f"invalid transition: {self.status} -> {status}")
        self.status = status
        if status == "running":
            self.started_at = self.started_at or _now()
        if status in {"accepted", "failed"}:
            self.completed_at = _now()


class JobStore:
    """Read and write TOML job files without introducing a database."""

    def __init__(self, jobs_dir: str | Path = "jobs") -> None:
        self.jobs_dir = Path(jobs_dir)
        self.results_dir = self.jobs_dir / "results"

    def load(self, path: str | Path) -> Job:
        job_path = Path(path)
        with job_path.open("rb") as handle:
            data = tomllib.load(handle)
        return Job(**{key: data[key] for key in (
            "job_id", "objective", "reasoning_tier", "prompt", "sandbox",
            "status", "thread_id", "created_at", "started_at", "completed_at",
            "result_location",
        ) if key in data})

    def save(self, job: Job, path: str | Path) -> None:
        # JSON is intentionally used for state snapshots so status updates are
        # deterministic and do not require a TOML writer dependency.
        target = Path(path).with_suffix(".state.json")
        target.write_text(json.dumps(asdict(job), indent=2) + "\n", encoding="utf-8")


def load_job(path: str | Path) -> Job:
    return JobStore(Path(path).parent).load(path)


def _codex_sandbox(name: str) -> Any:
    from openai_codex import Sandbox

    return getattr(Sandbox, SANDBOXES[name])


def _get_thread(codex: Any, job: Job, sandbox: Any) -> Any:
    if job.thread_id:
        return codex.thread_resume(job.thread_id, cwd=str(Path.cwd()), sandbox=sandbox)
    return codex.thread_start(cwd=str(Path.cwd()), sandbox=sandbox)


def run_job(path: str | Path, *, codex_factory: Any | None = None) -> Job:
    """Run one job and persist response/metadata; never commits or pushes."""
    job_path = Path(path)
    store = JobStore(job_path.parent)
    job = store.load(job_path)
    if job.status not in {"pending", "rework"}:
        raise ValueError(f"job must be pending or rework to run, got {job.status}")

    job.transition("running")
    store.save(job, job_path)
    result_dir = store.results_dir / job.job_id
    result_dir.mkdir(parents=True, exist_ok=True)
    try:
        if codex_factory is None:
            from openai_codex import Codex
            codex_factory = Codex
        sandbox = _codex_sandbox(job.sandbox)
        with codex_factory() as codex:
            thread = _get_thread(codex, job, sandbox)
            job.thread_id = str(thread.id)
            result = thread.run(job.prompt, effort=REASONING_EFFORTS[job.reasoning_tier], sandbox=sandbox)
        response = getattr(result, "final_response", str(result))
        (result_dir / "response.md").write_text(response, encoding="utf-8")
        job.result_location = str((result_dir / "response.md").as_posix())
        (result_dir / "metadata.json").write_text(json.dumps({
            "job_id": job.job_id,
            "thread_id": job.thread_id,
            "reasoning_tier": job.reasoning_tier,
            "sandbox": job.sandbox,
            "completed_at": _now(),
        }, indent=2) + "\n", encoding="utf-8")
        job.transition("review")
    except Exception as exc:
        (result_dir / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        job.transition("failed")
        job.result_location = str((result_dir / "error.txt").as_posix())
    store.save(job, job_path)
    return job
