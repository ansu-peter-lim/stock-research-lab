Implemented the file-based terminal monitor:

- Added `python -m orchestrator monitor`
- Preserved existing TOML job syntax and lifecycle
- Added persisted `started_at`, model, token usage, progress, and activity
- Added `JobStore.record_progress()` and `record_activity()`
- Added no-active-job handling and recent activity rendering
- Added usage aggregation limited to orchestrator-recorded Codex usage
- Added tests for rendering, no active job, aggregation, and unavailable tokens
- Updated orchestrator documentation

Verification:

- `python -m pytest -q`: 10 passed
- `python -m unittest discover -s tests -v`: 10 passed
- `git diff --check`: passed

Token limitation: usage is recorded only when the SDK exposes explicit total token data; otherwise the monitor displays `N/A`. No counts are fabricated.

Git status: modified orchestrator/docs/tests files, plus existing untracked `jobs/JOB-0001.toml` and state file. No commit or push performed.