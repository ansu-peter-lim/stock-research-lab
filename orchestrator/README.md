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
not a job is active. Jobs default to model tier `standard` and resolve to the
verified `gpt-5.6-terra` model. The four tiers are `economy` →
`gpt-5.6-luna`, `standard` → `gpt-5.6-terra`, `advanced` → `gpt-5.6-sol`, and
`critical` → `gpt-6-astra`. Runners can report optional state with
`JobStore.record_progress(...)` and `JobStore.record_activity(...)`; omitted
progress remains omitted. The one-shot monitor shows compact runtime telemetry
without re-running a job or scanning result output.

Telemetry sources and limits:

- The immutable job specification supplies `model_tier`, which resolves to the
  requested model, reasoning tier, and sandbox. The state records requested
  and resolved model separately (they currently match under the four-tier
  policy).
- The installed `openai_codex` SDK (0.154.0) supplies `TurnResult.usage.last`
  when the App Server emits usage: input, output, total, and—when supplied—
  cached-input and reasoning-output tokens. Job and today's totals sum only
  recorded turn totals from this orchestrator; no quota or missing value is
  estimated.
- SDK App Server turn results supply turn start/end and duration, plus completed
  command-item durations. Only aggregate local command and recognizable test
  command durations are saved; command text, output, and arguments are never
  persisted as telemetry.
- Local orchestrator timing supplies total elapsed wall time.

SDK 0.154.0's completed-turn and `TurnResult` schemas do **not** expose the
actual runtime model identifier. Therefore `Actual Model` is deliberately
`N/A` unless a future SDK result explicitly provides `actual_model` or
`runtime_model`; the requested/resolved model is never presented as actual.
Telemetry collection is best-effort: a telemetry exception leaves a successful
Codex job successful and records only a concise warning.

Lifecycle commands always load the state snapshot first, so a pending status in
the TOML does not prevent accepting or reworking a job whose runtime state has
advanced.

Jobs default to `read-only`. Set `sandbox = "workspace-write"` only when the
job explicitly needs repository edits. `xhigh` is rejected, full filesystem
access is unsupported, and the runner never commits or pushes. Rework uses the
persisted `thread_id` to resume the same Codex thread.

Lifecycle: `pending -> running -> review -> accepted`, with `failed` and
`rework` paths. A reviewer must accept a job separately.
