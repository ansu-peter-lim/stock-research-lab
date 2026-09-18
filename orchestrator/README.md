# Job Orchestrator

The orchestrator is a small file-backed runner for approved Codex work. A job
is a human-readable TOML file under `jobs/`; execution state is saved beside it
as `*.state.json`, and final responses/metadata are written to
`jobs/results/<job_id>/`.

Run a job from the repository root:

```text
python -m orchestrator jobs/example.toml
python -m orchestrator jobs/example.toml --accept
```

Jobs default to `read-only`. Set `sandbox = "workspace-write"` only when the
job explicitly needs repository edits. `xhigh` is rejected, full filesystem
access is unsupported, and the runner never commits or pushes. Rework uses the
persisted `thread_id` to resume the same Codex thread.

Lifecycle: `pending -> running -> review -> accepted`, with `failed` and
`rework` paths. A reviewer must accept a job separately.
