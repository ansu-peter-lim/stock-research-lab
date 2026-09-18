Implemented compact, fail-safe telemetry.

- Model policy unchanged: economy→Luna, standard→Terra, advanced→Sol, critical→Astra.
- Requested/resolved model are persisted separately. Actual runtime model remains `N/A`: installed `openai_codex` 0.154.0 completed-turn telemetry does not expose it.
- Token telemetry now records SDK-supplied turn input/output/total, optional cached/reasoning detail, job total, and today’s total from this orchestrator’s recorded events only.
- Timing now records runtime Codex turn duration, aggregate local-command/test durations when runtime items expose them, and local total elapsed.
- Monitor renders the requested Usage and Execution sections one-shot.
- Telemetry failures leave successful jobs successful; command contents/output/secrets are not stored.

Changed: [core.py](D:\Project\research\orchestrator\core.py), [README.md](D:\Project\research\orchestrator\README.md), [test_orchestrator.py](D:\Project\research\tests\test_orchestrator.py).

Validation: `python -m unittest tests.test_orchestrator` — 19 tests passed in 1.05s; `git diff --check` passed.

Telemetry overhead is limited to processing the SDK result already returned for a turn; no polling, second runtime, log archive, or command-output persistence. Recommended next step: run one normal orchestrated job and inspect `python -m orchestrator monitor` with real App Server telemetry.