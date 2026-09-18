from pathlib import Path
from openai_codex import Codex, Sandbox

ROOT = Path(r"D:\Project\research")
THREAD_ID = "01a0b4b6-1e0e-7e50-af3c-2ab0f26a6144"

PROMPT = """
REWORK JOB-0001.

A lifecycle bug was found during acceptance.

Observed:
- jobs/JOB-0001.toml still contains status = "pending".
- jobs/JOB-0001.state.json correctly contains status = "review".
- Running:
    python -m orchestrator .\\jobs\\JOB-0001.toml --accept
  loads the TOML status and fails with:
    ValueError: invalid transition: pending -> accepted

Required design correction:

1. Treat the TOML job file as immutable job specification/input.
2. Treat JOB-ID.state.json as the authoritative runtime state once it exists.
3. All lifecycle operations, including --accept, must load runtime state first.
4. Do not require manually rewriting status in the TOML.
5. Preserve thread_id, timestamps, result_location, usage, progress, and activity from runtime state.
6. Add regression tests specifically proving:
   - pending TOML + review state JSON can transition to accepted.
   - accepted status persists in state JSON.
   - original TOML remains unchanged.
7. Review other lifecycle paths for the same specification-vs-runtime-state bug.
8. Keep the fix minimal.
9. Run the complete test suite and git diff --check.
10. Do not commit or push.

Also document clearly:
TOML = job specification
state.json = runtime source of truth

Report tests and files changed.
"""

with Codex() as codex:
    thread = codex.thread_resume(THREAD_ID, cwd=str(ROOT))
    result = thread.run(
        PROMPT,
        effort="medium",
        sandbox=Sandbox.workspace_write,
    )
    print(result.final_response)
    