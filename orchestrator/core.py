"""Small, reviewable job lifecycle and Codex execution adapter."""

from __future__ import annotations

import json
import re
import tomllib
from time import perf_counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REASONING_EFFORTS = {"low": "low", "medium": "medium", "high": "high"}
MODEL_TIERS = {
    "economy": "gpt-5.6-luna",
    "standard": "gpt-5.6-terra",
    "advanced": "gpt-5.6-sol",
    "critical": "gpt-6-astra",
}
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
    model_tier: str = "standard"
    status: str = "pending"
    thread_id: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    result_location: str | None = None
    # `model` is retained for backwards-compatible snapshots.  New snapshots
    # make the requested/resolved/runtime distinction explicit.
    model: str | None = None
    requested_model: str | None = None
    resolved_model: str | None = None
    actual_model: str | None = None
    current_turn_input_tokens: int | None = None
    current_turn_output_tokens: int | None = None
    current_turn_total_tokens: int | None = None
    current_turn_cached_input_tokens: int | None = None
    current_turn_reasoning_output_tokens: int | None = None
    # Legacy alias for snapshots written before detailed token telemetry.
    current_turn_tokens: int | None = None
    cumulative_tokens: int | None = None
    usage_recorded_at: str | None = None
    usage_events: list[dict[str, Any]] | None = None
    turn_started_at: str | None = None
    turn_completed_at: str | None = None
    codex_elapsed_ms: int | None = None
    local_command_elapsed_ms: int | None = None
    test_elapsed_ms: int | None = None
    total_elapsed_ms: int | None = None
    telemetry_warning: str | None = None
    progress: dict[str, Any] | None = None
    activity: list[dict[str, str]] | None = None

    def __post_init__(self) -> None:
        if self.reasoning_tier not in REASONING_EFFORTS:
            raise ValueError("reasoning_tier must be low, medium, or high; xhigh is not supported")
        if self.model_tier not in MODEL_TIERS:
            raise ValueError("model_tier must be economy, standard, advanced, or critical")
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
            "model_tier", "status", "thread_id", "created_at", "started_at", "completed_at",
            "result_location", "model", "current_turn_tokens",
            "requested_model", "resolved_model", "actual_model",
            "current_turn_input_tokens", "current_turn_output_tokens", "current_turn_total_tokens",
            "current_turn_cached_input_tokens", "current_turn_reasoning_output_tokens",
            "cumulative_tokens", "usage_recorded_at", "progress", "activity", "usage_events",
            "turn_started_at", "turn_completed_at", "codex_elapsed_ms",
            "local_command_elapsed_ms", "test_elapsed_ms", "total_elapsed_ms", "telemetry_warning",
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


def create_job_file(job_id: str, jobs_dir: str | Path = "jobs") -> Path:
    """Create a small pending TOML specification for a future approved job."""
    if not re.fullmatch(r"JOB-[0-9]{4}", job_id):
        raise ValueError("job id must match JOB-0000")
    target = Path(jobs_dir) / f"{job_id}.toml"
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f'job_id = "{job_id}"\n'
        'objective = "Describe the bounded objective before implementation."\n'
        'model_tier = "standard"\n'
        'reasoning_tier = "medium"\n'
        'sandbox = "read-only"\n'
        'status = "pending"\n'
        'prompt = "Replace this prompt with the approved job scope and acceptance criteria."\n',
        encoding="utf-8",
    )
    return target


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


def _nonnegative_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _runtime_model(result: Any) -> str | None:
    """Return only a runtime-confirmed model, never a requested model."""
    model = _value(result, "actual_model", "runtime_model")
    return str(model) if model else None


def _runtime_timestamp(value: Any) -> str | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    return None


def _is_test_command(command: Any) -> bool:
    if not isinstance(command, str):
        return False
    return bool(re.search(r"(^|[\s;&|])(pytest|unittest|tox|nox)([\s;&|]|$)|\b(?:npm|pnpm|yarn|cargo|make)\s+test\b", command, re.I))


def _capture_telemetry(job: Job, result: Any) -> None:
    """Copy compact SDK/runtime telemetry without retaining command content."""
    usage = _value(result, "usage", "token_usage")
    # The SDK exposes `last` as this turn and `total` as thread lifetime.  We
    # use only `last` so a resumed thread cannot inflate this job's total.
    turn_usage = _value(usage, "last") if usage is not None else None
    turn_usage = turn_usage if turn_usage is not None else usage
    fields = {
        "current_turn_input_tokens": _nonnegative_int(_value(turn_usage, "input_tokens")),
        "current_turn_output_tokens": _nonnegative_int(_value(turn_usage, "output_tokens")),
        "current_turn_total_tokens": _nonnegative_int(_value(turn_usage, "total_tokens", "total")),
        "current_turn_cached_input_tokens": _nonnegative_int(_value(turn_usage, "cached_input_tokens")),
        "current_turn_reasoning_output_tokens": _nonnegative_int(_value(turn_usage, "reasoning_output_tokens")),
    }
    for name, value in fields.items():
        setattr(job, name, value)
    job.current_turn_tokens = job.current_turn_total_tokens  # legacy alias
    if job.current_turn_total_tokens is not None:
        job.cumulative_tokens = (job.cumulative_tokens or 0) + job.current_turn_total_tokens
        job.usage_recorded_at = _now()
        job.usage_events.append({
            "timestamp": job.usage_recorded_at,
            "input_tokens": job.current_turn_input_tokens,
            "output_tokens": job.current_turn_output_tokens,
            "total_tokens": job.current_turn_total_tokens,
        })

    job.actual_model = _runtime_model(result)
    job.turn_started_at = _runtime_timestamp(_value(result, "started_at"))
    job.turn_completed_at = _runtime_timestamp(_value(result, "completed_at"))
    job.codex_elapsed_ms = _nonnegative_int(_value(result, "duration_ms"))
    local_elapsed = test_elapsed = 0
    local_found = test_found = False
    for item in _value(result, "items") or []:
        item = _value(item, "root") or item
        duration = _nonnegative_int(_value(item, "duration_ms"))
        if duration is None or _value(item, "type") != "commandExecution":
            continue
        local_elapsed += duration
        local_found = True
        if _is_test_command(_value(item, "command")):
            test_elapsed += duration
            test_found = True
    job.local_command_elapsed_ms = local_elapsed if local_found else None
    job.test_elapsed_ms = test_elapsed if test_found else None


def run_job(path: str | Path, *, codex_factory: Any | None = None) -> Job:
    """Run one job and persist response/metadata; never commits or pushes."""
    job_path = Path(path)
    store = JobStore(job_path.parent)
    job = store.load(job_path)
    if job.status not in {"pending", "rework"}:
        raise ValueError(f"job must be pending or rework to run, got {job.status}")

    job.transition("running")
    job.requested_model = MODEL_TIERS[job.model_tier]
    job.resolved_model = MODEL_TIERS[job.model_tier]
    job.model = job.resolved_model
    store.save(job, job_path)
    result_dir = store.results_dir / job.job_id
    result_dir.mkdir(parents=True, exist_ok=True)
    run_started = perf_counter()
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
            result = thread.run(
                job.prompt,
                effort=REASONING_EFFORTS[job.reasoning_tier],
                model=MODEL_TIERS[job.model_tier],
                sandbox=sandbox,
            )
            try:
                _capture_telemetry(job, result)
            except Exception as exc:  # Telemetry must never discard a successful turn.
                job.telemetry_warning = f"telemetry unavailable: {type(exc).__name__}"
        response = getattr(result, "final_response", str(result))
        (result_dir / "response.md").write_text(response, encoding="utf-8")
        job.result_location = str((result_dir / "response.md").as_posix())
        job.total_elapsed_ms = round((perf_counter() - run_started) * 1000)
        (result_dir / "metadata.json").write_text(json.dumps({
            "job_id": job.job_id,
            "thread_id": job.thread_id,
            "started_at": job.started_at,
            "model_tier": job.model_tier,
            "reasoning_tier": job.reasoning_tier,
            "sandbox": job.sandbox,
            "requested_model": job.requested_model,
            "resolved_model": job.resolved_model,
            "actual_model": job.actual_model,
            "current_turn_input_tokens": job.current_turn_input_tokens,
            "current_turn_output_tokens": job.current_turn_output_tokens,
            "current_turn_total_tokens": job.current_turn_total_tokens,
            "cumulative_tokens": job.cumulative_tokens,
            "turn_started_at": job.turn_started_at,
            "turn_completed_at": job.turn_completed_at,
            "codex_elapsed_ms": job.codex_elapsed_ms,
            "local_command_elapsed_ms": job.local_command_elapsed_ms,
            "test_elapsed_ms": job.test_elapsed_ms,
            "total_elapsed_ms": job.total_elapsed_ms,
            "completed_at": _now(),
        }, indent=2) + "\n", encoding="utf-8")
        job.transition("review")
        job.activity.append({"timestamp": _now(), "message": "Codex run completed; awaiting review"})
    except Exception as exc:
        (result_dir / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        job.transition("failed")
        job.result_location = str((result_dir / "error.txt").as_posix())
        job.activity.append({"timestamp": _now(), "message": f"Codex run failed: {type(exc).__name__}"})
    job.total_elapsed_ms = round((perf_counter() - run_started) * 1000)
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
                tokens = event.get("total_tokens", event.get("tokens"))
                if (event.get("timestamp") or "").startswith(today) and _nonnegative_int(tokens) is not None:
                    today_tokens += tokens
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
            f"  Status: {_display(job.get('status'))}",
            f"  Model Tier: {_display(job.get('model_tier') or 'standard')}",
            f"  Requested Model: {_display(job.get('requested_model') or job.get('model'))}",
            f"  Actual Model: {_display(job.get('actual_model'))}",
            f"  Reasoning: {_display(job.get('reasoning_tier'))}",
            f"  Sandbox: {_display(job.get('sandbox'))}",
            f"  Thread: {_short_thread_id(job.get('thread_id'))}",
            f"  Elapsed: {_display(job.get('total_elapsed_ms'))} ms",
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
        f"  Turn input: {_display(job.get('current_turn_input_tokens') if job else None)}",
        f"  Turn output: {_display(job.get('current_turn_output_tokens') if job else None)}",
        f"  Turn total: {_display(job.get('current_turn_total_tokens') if job and job.get('current_turn_total_tokens') is not None else (job.get('current_turn_tokens') if job else None))}",
        f"  Job total: {_display(job.get('cumulative_tokens') if job else None)}",
        f"  Today total: {today_tokens if usage_found else 'N/A'}",
        "",
        "Execution",
        f"  Codex elapsed: {_display(job.get('codex_elapsed_ms') if job else None)} ms",
        f"  Local command elapsed: {_display(job.get('local_command_elapsed_ms') if job else None)} ms",
        f"  Test elapsed: {_display(job.get('test_elapsed_ms') if job else None)} ms",
        "",
        "Recent Activity",
    ])
    lines.extend(f"  {timestamp} {message}" for timestamp, message in activity[:10])
    if not activity:
        lines.append("  No activity recorded")
    return "\n".join(lines)
