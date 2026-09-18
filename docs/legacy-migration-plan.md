# Legacy Migration Plan

## Source

`ansu-peter-lim/stock-trading-system` is a source repository only. It must
not be modified as part of this project.

## Candidate inventory

Review and migrate selectively:

- `src/telegram_top30_parser`
- `src/research_universe`
- reusable, research-safe portions of `src/backtest_engine`
- required Kiwoom daily/REST market-data adapters
- required KRX adapters
- stock mapping
- relevant tests
- relevant research and token-efficiency documents

## Migration gates

For each candidate, document purpose, dependencies, license/provenance,
point-in-time behavior, secrets handling, tests, and destination. Prefer a
small copied module with an adapter over importing the legacy application
wholesale. Reject live-trading paths, hidden credentials, undocumented
side-effects, and code that cannot demonstrate cutoff safety.

Bootstrap-001 performs no migration. A later job must inventory and approve
one bounded slice at a time.
