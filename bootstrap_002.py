from pathlib import Path

from openai_codex import Codex, Sandbox

ROOT = Path(r"D:\Project\research")
THREAD_ID = "01a0b49e-b392-76f0-bb65-6a7d8b54cb77"

JOB = """
JOB: BOOTSTRAP-002
REASONING TIER: MEDIUM

Read the canonical project documents created in BOOTSTRAP-001 before working.

OBJECTIVE
Build a minimal Codex job orchestrator so future Stock Research Lab work
does not require a new custom bootstrap script for every job.

REQUIREMENTS

1. Implement a small Python orchestrator under orchestrator/.

2. A job must be stored as a human-readable file under jobs/ and contain:
   - job_id
   - objective
   - reasoning_tier: low / medium / high
   - sandbox policy
   - status
   - Codex thread_id when available
   - prompt/instructions
   - created/completed metadata
   - result location

3. Implement reasoning policy:
   low -> low Codex reasoning effort
   medium -> medium
   high -> high
   xhigh must NOT be selectable by ordinary job files.

4. Implement job lifecycle:
   pending -> running -> review -> accepted
   with failed/rework support.

5. Preserve Codex thread IDs so follow-up/rework can resume the same thread.

6. Save Codex final responses and basic execution metadata under jobs/results/
   rather than requiring terminal output to be manually copied.

7. Default sandbox must be read-only.
   Workspace-write must require the job to explicitly request it.
   Do not support dangerous/full filesystem access.

8. The orchestrator must NOT automatically git commit or push.
   Git remains a separate reviewed step.

9. Add tests for:
   - reasoning-tier mapping
   - invalid xhigh rejection
   - default read-only sandbox
   - explicit workspace-write
   - job state transitions
   - thread ID persistence

10. Add concise usage documentation.

KEEP IT SMALL.
Do not build a web UI, database server, queue service, scheduler,
App Server UI, or generalized agent framework.

Do not migrate legacy trading code in this job.

Run the relevant tests after implementation.

FINAL RESPONSE
Report:
- implementation files
- test results
- design decisions
- limitations
- recommended next job
- git status

Do not commit or push.
"""

def main():
    with Codex() as codex:
        thread = codex.thread_resume(
            THREAD_ID,
            cwd=str(ROOT),
        )

        result = thread.run(
            JOB,
            effort="medium",
            sandbox=Sandbox.workspace_write,
        )

        print("\n===== CODEX RESULT =====\n")
        print(result.final_response)

        print("\n===== THREAD ID =====")
        print(thread.id)


if __name__ == "__main__":
    main()