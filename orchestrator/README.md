# Job Orchestrator

The orchestrator is a small file-backed runner for approved Codex work. A job
is a human-readable TOML file under `jobs/`; it is the immutable job
specification/input. Execution state is saved beside it as `*.state.json`, and
that runtime snapshot is the source of truth once it exists. Final responses/metadata are written to
`jobs/results/<job_id>/`.

Run a job from the repository root:

```text
python -m orchestrator jobs/example.toml
python -m orchestrator jobs/example.toml --accept
python -m orchestrator monitor
```

`monitor` reads the file-backed `*.state.json` snapshots and works whether or
not a job is active. Runners can report optional state with
`JobStore.record_progress(...)` and `JobStore.record_activity(...)`; omitted
progress remains omitted. Model and token fields are persisted only when the
installed Codex SDK exposes them, otherwise the monitor displays `N/A`.

Lifecycle commands always load the state snapshot first, so a pending status in
the TOML does not prevent accepting or reworking a job whose runtime state has
advanced.

Jobs default to `read-only`. Set `sandbox = "workspace-write"` only when the
job explicitly needs repository edits. `xhigh` is rejected, full filesystem
access is unsupported, and the runner never commits or pushes. Rework uses the
persisted `thread_id` to resume the same Codex thread.

Lifecycle: `pending -> running -> review -> accepted`, with `failed` and
`rework` paths. A reviewer must accept a job separately.
