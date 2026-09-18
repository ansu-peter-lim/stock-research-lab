from pathlib import Path
from openai_codex import Codex, Sandbox

ROOT = Path(r"D:\Project\research")
LEGACY = Path(r"D:\Project\stock-trading-system-reference")
THREAD_ID = "01a0b4c3-e4a6-7730-94e8-2242e20b9af7"

PROMPT = f"""
REWORK JOB-0002 — Legacy Research Asset Inventory.

The first inventory used repeated GitHub web requests. Revalidate it using
the local legacy repository instead.

TARGET REPOSITORY:
{ROOT}

LEGACY REFERENCE:
{LEGACY}

IMPORTANT:
- Treat the legacy repository as strictly READ ONLY.
- Do not modify, commit, checkout, pull, reset, clean, or otherwise alter it.
- Do not use Invoke-WebRequest or browse GitHub for repository contents.
- Inspect local files only.
- You may update the target report:
  docs/migration/legacy-inventory.md
- Do NOT migrate code yet.

Reinspect at minimum:
- telegram_collect_3years.py
- src/telegram_top30_parser
- src/research_universe
- src/backtest_engine
- src/kiwoom_daily
- src/kiwoom_rest
- src/krx_openapi
- src/stock_mapping
- relevant tests
- docs/research
- token-efficiency work

Revalidate every REUSE / ADAPT / REFERENCE / DEFER classification.

Pay particular attention to:
1. actual dependencies between components;
2. historical Top30 reconstruction capability;
3. point-in-time eligibility and look-ahead leakage;
4. historical stock-name/code/corporate-event handling;
5. daily OHLCV sources;
6. credentials or external API dependencies;
7. which backtest/indicator code is genuinely reusable;
8. existing research knowledge worth preserving;
9. unnecessary legacy complexity that should NOT migrate.

Update docs/migration/legacy-inventory.md with:
- verified classification matrix;
- dependency map;
- minimal migration slice;
- migration order;
- deferred components;
- risks and unknowns;
- source legacy commit SHA;
- proposed next job.

Keep the report concise but evidence-based.
Reference concrete legacy paths for important conclusions.

Run no destructive commands.
Do not commit or push.

At completion report:
- major corrections versus the first inventory;
- report path;
- recommended next migration job.
"""

with Codex() as codex:
    thread = codex.thread_resume(THREAD_ID, cwd=str(ROOT))
    result = thread.run(
        PROMPT,
        effort="low",
        sandbox=Sandbox.workspace_write,
    )
    print(result.final_response)
    