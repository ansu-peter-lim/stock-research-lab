# Legacy Research Asset Inventory — Revalidated Locally

Source: `D:\\Project\\stock-trading-system-reference`  
Verified legacy commit: `97aa1e67b0b40a6d8696f5ab2e57413724be800d`  
Inspection only; no legacy files were changed and no code was migrated.

## Verified classification matrix

| Component | Class | Evidence-based conclusion |
|---|---|---|
| `telegram_collect_3years.py` | REFERENCE | Collects three years from Telegram channel `balanceasset` into `data/raw/telegram/daily`; uses `python-dotenv`, Telethon, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and a local session. Useful acquisition knowledge, not a research-safe importer: availability, edits, deletions, and report-date semantics are not established. |
| `src/telegram_top30_parser` | ADAPT | `parser.py` extracts daily Top30 rows, report type/date, Telegram posted time/message ID, source file, SHA-256, and quality issues; `manual_corrections.py` applies logged corrections. Strong input layer, but target artifacts must freeze availability and distinguish report date from publication time. Tests: `tests/test_telegram_top30_parser.py`, `test_manual_corrections.py`, `test_report_investigation.py`. |
| `src/stock_mapping` | ADAPT | `historical_master.py` provides interval-based code/name mapping; `krx_historical_master_builder.py` builds provenance-bearing intervals; `krx_stock_basic_adapter.py` detects transitions/absence; `official_event_evidence.py` validates event evidence and publication timestamps. Strongest corporate-event foundation, but `source_as_of` is not automatically historical availability. Tests: `test_historical_stock_mapping.py`, `test_krx_historical_master_builder.py`, `test_krx_stock_basic_adapter.py`, `test_official_event_evidence.py`. |
| `src/research_universe` | ADAPT | `historical_eligibility.py` checks interval coverage, identity, market transfer, listing/relisting/delisting uncertainty, conflicts, provenance, and manual evidence. `daily_eligibility.py` validates canonical bars, calendar coverage, digests, and raw/signal-adjusted roles. Adapt to cutoff-visible evidence only. Tests: `test_historical_research_eligibility.py`, `test_daily_research_eligibility.py`, `test_research_eligibility_models.py`. |
| `src/krx_openapi` | ADAPT | `services.py`, `transport.py`, `parser.py`, `collector.py`, and `store.py` provide secret-safe `KRX_AUTH_KEY` access, schema validation, immutable raw artifacts, SHA-256 identity, and append-only manifests. Reuse contracts/store ideas; ingest frozen evidence bundles rather than query KRX during analysis. Tests: `test_krx_openapi_pilot.py`, `test_krx_integration_k1.py`. |
| `src/kiwoom_daily` | ADAPT | `collector.py` depends on `src.kiwoom_rest.auth` and `market_data_pilot`; parser/adapter produce canonical OHLCV and eligibility evidence; store keeps immutable pages/manifests. Relevant for features and +5/+10/+20/+60 outcomes. Adapt for bulk history, adjusted/raw policy, pagination, rate limits, and vintage metadata. Tests: `test_kiwoom_daily_pipeline.py` plus boundary/acquisition/integrity tests. |
| `src/kiwoom_rest` | DEFER | Auth and chart pagination provide Kiwoom REST plumbing; `minute_history_probe.py` is minute-oriented. Credentials are environment-only and network tests require `KIWOOM_RUN_NETWORK_TESTS=1`. Retain the interface as a future adapter dependency; do not migrate REST/minute code first. Tests: `test_kiwoom_rest_auth.py`, `test_kiwoom_rest_market_data_pilot.py`, `test_kiwoom_rest_minute_history_probe.py`, network tests. |
| `src/backtest_engine` | ADAPT | Reusable foundation: `models.py`, `validation.py`, `trading_calendar.py`, and selected daily `indicators.py`. Indicators carry `signal_available_at`/`as_of`; tests prove future removal does not alter prior indicators and unconfirmed pivots stay unavailable. Do not migrate strategies, execution, ledgers, or accounting. Tests: `test_backtest_indicators.py`, `test_backtest_calendar.py`, `test_backtest_models_and_validation.py`. |
| `tests` | ADAPT | Use parser, mapping, KRX, eligibility, daily pipeline, calendar, validation, and indicator tests as behavioral specifications. Exclude network, execution, visualization, and frozen proof tests from the minimal slice; replace external behavior with fixtures/contracts. |
| `docs/research` | REFERENCE | Preserve conclusions and provenance. The algorithm checkpoint labels prior tracks reference/frozen/paused; the Market-Bar hypothesis documents anti-look-ahead invariants; validation docs record source-readiness limits and no strategy outputs. Knowledge, not Top30 pipeline code. |
| Token-efficiency work (`tools/codebase_token_efficiency_audit.py`, `docs/research/codebase_token_efficiency_audit_v0_1.md`) | REFERENCE | Audit found 100 source files, 75 tests, many frozen proof modules, and a 17-file/8,109-line closure for one Daily proof. It recommends a small new Daily core and preserving frozen duplication. Do not import proof scripts or generic frameworks. |

## Actual dependency map

```text
telegram_collect_3years.py -> raw Telegram files -> telegram_top30_parser
  -> manual_corrections -> Top30 observations + quality/correction logs

KRX transport/auth -> krx_openapi parser/store/manifest
  -> stock_mapping.krx_stock_basic_adapter
  -> stock_mapping.krx_historical_master_builder
  -> stock_mapping.historical_master + official_event_evidence
  -> research_universe.historical_eligibility

kiwoom_rest.auth + market_data_pilot
  -> kiwoom_daily collector/parser/store/adapter
  -> backtest_engine models/validation/calendar
  -> research_universe.daily_eligibility

backtest_engine indicators -> frozen assessment -> later-only
  +5/+10/+20/+60 outcome join
```

Important correction: `kiwoom_daily.collector.py` imports Kiwoom REST directly, while `kiwoom_daily.adapter.py` imports both backtest contracts and daily eligibility. Mapping imports KRX service/parser/store contracts through `krx_stock_basic_adapter.py`; these are not independent candidates.

## Historical Top30 and leakage assessment

The parser can reconstruct report rows over approximately three years, including rank, name, return, posted timestamp, message ID, source file, and digest. It does not prove availability at a chosen cutoff or recover missing/deleted history.

The mapping stack represents name/code intervals, listing and delisting boundaries, transfers, security type, normalized-name ambiguity, manual evidence, and transition candidates. But fixtures such as `tests/fixtures/krx_master_states.csv` use later `source_as_of` values (`2026-08-30`), so retrospective master data cannot automatically enter an old cutoff information set.

Eligibility is conservatively useful: gaps, conflicts, unsupported types, missing provenance, and digest problems become excluded or review-required. It still needs a cutoff-aware evidence selector and publication availability before study use.

Daily OHLCV is provided through the Kiwoom chart path (`ka10081`, `stk_dt_pole_chart_qry`, fields in `src/kiwoom_rest/market_data_pilot.py`) and immutable storage in `src/kiwoom_daily/store.py`. Freeze raw versus adjusted policy and retrieval/vintage/revision metadata.

The indicator layer has the clearest causal tests: availability timestamps, `as_of` filtering, and future-removal invariance. Reuse primitives, not the trading engine. Serialize assessment before adding outcome labels.

## Minimal migration slice and order

1. Define Top30 observation/cutoff schemas: report date, posted/available timestamp, rank, name, return, digest, parser status, and mapping status.
2. Adapt `telegram_top30_parser` plus focused fixtures/tests; do not migrate the collector or credentials.
3. Adapt KRX raw-artifact/provenance contracts and create a cutoff-aware mapping bundle.
4. Adapt `historical_eligibility` to reject evidence published after cutoff and preserve unresolved events.
5. Add a small daily OHLCV fixture/adapter contract using `kiwoom_daily` storage/parser/validation; defer live acquisition.
6. Reuse backtest models, calendar, validation, and daily indicators only after availability/truncation tests pass.
7. Freeze assessment artifacts; add +5/+10/+20/+60 joins as a separate outcome step.

## Explicitly deferred / do not migrate

- Live execution, order handling, ledgers, account/PnL machinery, and strategy classes.
- Kiwoom REST implementation and minute-history probes for the first daily study.
- `kiwoom_daily/*proof.py`, market-clock, Market-Bar, MMA, and visualization scripts.
- Generic provider/plugin/DI abstractions and wholesale CLI/helper deduplication.
- Manual mappings without source evidence or later classifications silently backfilled into old cutoffs.
- Legacy strategy findings as current Top30 hypotheses; preserve as reference only.

## Risks and unknowns

- Telegram completeness, edits/deletions, timezone, channel access, and publication semantics.
- Whether Top30 is a stable ranking definition, including ties, duplicates, and trading-day cutoff.
- KRX event publication versus effective dates; current snapshots cannot establish historical knowability.
- Name/code changes, relistings, transfers, delistings, security types, and survivorship bias.
- Kiwoom adjusted/raw meaning, corporate actions, pagination limits, missing sessions, and API retention.
- External dependencies/credentials: Telethon, `KRX_AUTH_KEY`, and `KIWOOM_*`; secrets must not enter artifacts.
- Legacy complexity: large frozen research closures increase context and leakage risk without helping the first Top30 slice.

## Proposed next job

`JOB-0003`: specify the parser-to-observation contract only. Use local Telegram fixtures/source files, verify duplicate-day and malformed-row behavior, define availability/checksum fields, and add cutoff/leakage tests. Do not collect data, call KRX/Kiwoom, or migrate production modules. Then build one KRX historical identity bundle with explicit publication/effective-date evidence.
