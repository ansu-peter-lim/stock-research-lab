Completed the read-only legacy inventory.

Report: [docs/migration/legacy-inventory.md](D:\Project\research\docs\migration\legacy-inventory.md)

Key findings:

- ADAPT: Top30 parser, historical stock mapping, research-universe eligibility, KRX adapters, daily OHLCV adapters, and selected indicator/validation primitives.
- REFERENCE: Telegram collection script, research documents, token-efficiency tooling.
- DEFER: Kiwoom REST/minute data, live trading, execution/ledger/strategy infrastructure, and proof/audit scripts.
- Highest risks: Telegram availability semantics, corporate events, revised histories, adjusted OHLCV, delistings, and look-ahead leakage.
- Recommended next job: define and test a parser-to-point-in-time observation contract before migrating any implementation.

No legacy code was copied, modified, committed, or pushed. The source repository was inspected through read-only GitHub API/raw-file access; no legacy runtime tests were executed.