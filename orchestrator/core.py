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
    model: str | None = None
    current_turn_tokens: int | None = None
    cumulative_tokens: int | None = None
    usage_recorded_at: str | None = None
    usage_events: list[dict[str, Any]] | None = None
    progress: dict[str, Any] | None = None
    activity: list[dict[str, str]] | None = None

    def __post_init__(self) -> None:
        if self.reasoning_tier not in REASONING_EFFORTS:
            raise ValueError("reasoning_tier must be low, medium, or high; xhigh is not supported")
        if self.sandbox not in SANDBOXES:
            raise ValueError("sandbox must be read-only or workspace-write")
        if self.status not in TRANSITIONS:
            raise ValueError(f"invalid job status: {self.status}")
        self.created_at = self.created_at or _now()
        self.activity = list(self.activity or [])
        self.usage_events = list(self.usage_events or [])

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
        state_path = job_path.with_suffix(".state.json")
        if state_path.exists():
            # TOML is the immutable job specification. Once a runtime
            # snapshot exists, it is authoritative for lifecycle and all
            # persisted runtime metadata.
            data.update(json.loads(state_path.read_text(encoding="utf-8")))
        return Job(**{key: data[key] for key in (
            "job_id", "objective", "reasoning_tier", "prompt", "sandbox",
            "status", "thread_id", "created_at", "started_at", "completed_at",
            "result_location", "model", "current_turn_tokens",
            "cumulative_tokens", "usage_recorded_at", "progress", "activity",
            "usage_events",
        ) if key in data})

    def save(self, job: Job, path: str | Path) -> None:
        # JSON is intentionally used for state snapshots so status updates are
        # deterministic and do not require a TOML writer dependency.
        target = Path(path).with_suffix(".state.json")
        target.write_text(json.dumps(asdict(job), indent=2) + "\n", encoding="utf-8")

    def record_activity(self, path: str | Path, message: str, *, timestamp: str | None = None) -> None:
        """Append a concise runner event to a persisted state snapshot."""
        state_path = Path(path).with_suffix(".state.json")
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        events = state.setdefault("activity", [])
        events.append({"timestamp": timestamp or _now(), "message": message})
        state["activity"] = events[-20:]
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def record_progress(
        self,
        path: str | Path,
        *,
        completed: int,
        current: str | None = None,
        pending: int | None = None,
    ) -> None:
        """Persist progress explicitly reported by a runner or job."""
        state_path = Path(path).with_suffix(".state.json")
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        state["progress"] = {"completed": completed, "current": current, "pending": pending}
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def state_files(self) -> list[Path]:
        return sorted(self.jobs_dir.glob("*.state.json"))


def load_job(path: str | Path) -> Job:
    return JobStore(Path(path).parent).load(path)


def _codex_sandbox(name: str) -> Any:
    from openai_codex import Sandbox

    return getattr(Sandbox, SANDBOXES[name])


def _get_thread(codex: Any, job: Job, sandbox: Any) -> Any:
    if job.thread_id:
        return codex.thread_resume(job.thread_id, cwd=str(Path.cwd()), sandbox=sandbox)
    return codex.thread_start(cwd=str(Path.cwd()), sandbox=sandbox)


def _value(source: Any, *names: str) -> Any:
    for name in names:
        if isinstance(source, dict) and name in source:
            return source[name]
        value = getattr(source, name, None)
        if value is not None:
            return value
    return None


def _usage_total(result: Any) -> int | None:
    usage = _value(result, "usage", "token_usage")
    total = _value(usage, "total_tokens", "total") if usage is not None else None
    return total if isinstance(total, int) and total >= 0 else None


def _model_name(result: Any, thread: Any) -> str | None:
    model = _value(result, "model", "model_name") or _value(thread, "model", "model_name")
    return str(model) if model else None


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
            job.activity.append({"timestamp": _now(), "message": "Codex thread started"})
            store.save(job, job_path)
            result = thread.run(job.prompt, effort=REASONING_EFFORTS[job.reasoning_tier], sandbox=sandbox)
            job.model = _model_name(result, thread) or job.model
            turn_tokens = _usage_total(result)
            job.current_turn_tokens = turn_tokens
            if turn_tokens is not None:
                job.cumulative_tokens = (job.cumulative_tokens or 0) + turn_tokens
                job.usage_recorded_at = _now()
                job.usage_events.append({"timestamp": job.usage_recorded_at, "tokens": turn_tokens})
        response = getattr(result, "final_response", str(result))
        (result_dir / "response.md").write_text(response, encoding="utf-8")
        job.result_location = str((result_dir / "response.md").as_posix())
        (result_dir / "metadata.json").write_text(json.dumps({
            "job_id": job.job_id,
            "thread_id": job.thread_id,
            "started_at": job.started_at,
            "reasoning_tier": job.reasoning_tier,
            "sandbox": job.sandbox,
            "model": job.model,
            "current_turn_tokens": job.current_turn_tokens,
            "cumulative_tokens": job.cumulative_tokens,
            "completed_at": _now(),
        }, indent=2) + "\n", encoding="utf-8")
        job.transition("review")
        job.activity.append({"timestamp": _now(), "message": "Codex run completed; awaiting review"})
    except Exception as exc:
        (result_dir / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        job.transition("failed")
        job.result_location = str((result_dir / "error.txt").as_posix())
        job.activity.append({"timestamp": _now(), "message": f"Codex run failed: {type(exc).__name__}"})
    store.save(job, job_path)
    return job


def _short_thread_id(thread_id: str | None) -> str:
    if not thread_id:
        return "N/A"
    return thread_id[:12]


def _display(value: Any) -> str:
    return "N/A" if value is None or value == "" else str(value)


def render_monitor(jobs_dir: str | Path = "jobs", *, now: datetime | None = None) -> str:
    """Render a concise text monitor from file-backed state snapshots."""
    store = JobStore(jobs_dir)
    states = []
    for path in store.state_files():
        try:
            states.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    active = [state for state in states if state.get("status") == "running"]
    active.sort(key=lambda item: item.get("started_at") or "", reverse=True)
    job = active[0] if active else None
    today = (now or datetime.now(timezone.utc)).date().isoformat()
    today_tokens = 0
    usage_found = False
    for state in states:
        events = state.get("usage_events") or []
        if events:
            for event in events:
                if (event.get("timestamp") or "").startswith(today) and isinstance(event.get("tokens"), int):
                    today_tokens += event["tokens"]
                    usage_found = True
        elif (state.get("usage_recorded_at") or "").startswith(today) and isinstance(state.get("cumulative_tokens"), int):
            # Compatibility with snapshots written before usage_events existed.
            today_tokens += state["cumulative_tokens"]
            usage_found = True
    activity = []
    for state in states:
        for event in state.get("activity") or []:
            activity.append((event.get("timestamp", ""), event.get("message", "")))
    activity.sort(reverse=True)

    lines = ["Stock Research Lab Monitor", "", "Current Job"]
    if job is None:
        lines.append("  No active job")
    else:
        lines.extend([
            f"  ID: {_display(job.get('job_id'))}",
            f"  objective/title: {_display(job.get('objective'))}",
            f"  status: {_display(job.get('status'))}",
            f"  started_at: {_display(job.get('started_at'))}",
            f"  model: {_display(job.get('model'))}",
            f"  reasoning tier: {_display(job.get('reasoning_tier'))}",
            f"  sandbox: {_display(job.get('sandbox'))}",
            f"  thread ID: {_short_thread_id(job.get('thread_id'))}",
        ])
        progress = job.get("progress")
        if progress is not None:
            lines.extend([
                "",
                "Progress",
                f"  completed: {_display(progress.get('completed'))}",
                f"  current: {_display(progress.get('current'))}",
                f"  pending: {_display(progress.get('pending'))}",
            ])
    lines.extend([
        "",
        "Usage",
        f"  current turn tokens: {_display(job.get('current_turn_tokens') if job else None)}",
        f"  current job cumulative tokens: {_display(job.get('cumulative_tokens') if job else None)}",
        f"  today's cumulative tokens: {today_tokens if usage_found else 'N/A'}",
        "",
        "Recent Activity",
    ])
    lines.extend(f"  {timestamp} {message}" for timestamp, message in activity[:10])
    if not activity:
        lines.append("  No activity recorded")
    return "\n".join(lines)
