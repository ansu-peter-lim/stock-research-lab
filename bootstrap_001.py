from pathlib import Path

from openai_codex import Codex, Sandbox


ROOT = Path(r"D:\Project\research")

JOB = """
JOB: BOOTSTRAP-001
ROLE: You are the implementation agent for Stock Research Lab.

OBJECTIVE
Initialize this repository as a research-first laboratory for historical
Top30 Korean-stock analysis.

PROJECT GOVERNANCE
- Owner controls research direction, scope, and approval gates.
- ChatGPT acts as research lead and reviews Codex work.
- Codex implements, tests, and reports evidence.
- GitHub is the durable source of truth.
- Do not modify the legacy stock-trading-system repository.
- This repository is stock-research-lab.

RESEARCH OBJECTIVE
Start approximately three years in the past and process historical Top30
snapshots forward through time.

For each historical cutoff:
1. Use only information available at that cutoff.
2. Analyze market, sector, and stock conditions.
3. Freeze the assessment before revealing future prices.
4. Then evaluate subsequent +5/+10/+20/+60 trading-day outcomes.
5. Analyze errors.
6. Convert observations into hypotheses.
7. Validate hypotheses across adequate samples.
8. Promote only validated findings into durable knowledge.

CRITICAL RESEARCH RULE
Prevent look-ahead bias. Future prices, later classifications,
future constituents, and post-cutoff information must never leak into
the assessment phase.

CREATE THE INITIAL REPOSITORY STRUCTURE

orchestrator/
jobs/
experiments/
knowledge/
data/
docs/
src/
tests/

Create appropriate README/Markdown documents covering:

1. Project Charter
2. Historical Research Protocol
3. Legacy Migration Plan
4. ChatGPT-Codex Operating Protocol
5. Data Policy
6. Knowledge Registry policy
7. Experiment policy

MIGRATION POLICY
Legacy source:
ansu-peter-lim/stock-trading-system

Initial migration candidates:
- src/telegram_top30_parser
- src/research_universe
- reusable portions of src/backtest_engine
- required Kiwoom daily/REST market-data adapters
- required KRX adapters
- stock mapping
- relevant tests
- relevant research/token-efficiency documents

Do NOT migrate everything yet.
This job establishes structure and migration policy only.

CODEX COST POLICY
Document this policy:

LOW reasoning:
- repository/file inspection
- deterministic extraction
- formatting
- routine tests
- simple migration

MEDIUM reasoning:
- implementation
- debugging
- ordinary quantitative analysis
- backtest development

HIGH reasoning:
- hypothesis design
- ambiguous failure analysis
- look-ahead leakage investigation
- consequential architecture/research decisions

XHIGH:
- do not use by default
- only for exceptional problems after research-lead escalation

TOKEN DISCIPLINE
- Read canonical repository documents instead of repeatedly receiving
  large conversational context.
- Use deterministic Python for bulk historical calculations.
- Use model reasoning primarily for interpretation and hypothesis work.
- Preserve accepted knowledge so it is not repeatedly re-derived.

GIT / SECURITY
- Add an appropriate .gitignore.
- Never store API keys, brokerage credentials, Telegram credentials,
  account information, or secrets.
- Do not push or commit anything in this job.
- Do not modify files outside this repository.

QUALITY
Keep the bootstrap minimal.
Do not prematurely implement trading strategies or live execution.
Do not build unnecessary frameworks.

FINAL RESPONSE
Report:
- files/directories created
- important design decisions
- anything that could not be completed
- recommended next job
- git status summary
"""


def main():
    with Codex() as codex:
        thread = codex.thread_start(
            cwd=str(ROOT),
            sandbox=Sandbox.workspace_write,
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