# Stock Research Lab

Research-first laboratory for historical analysis of Korean equities using
point-in-time Top30 universe snapshots. The lab is deliberately separate from
`ansu-peter-lim/stock-trading-system` and does not execute live trading.

## Start here

1. Read [`docs/project-charter.md`](docs/project-charter.md).
2. Follow [`docs/historical-research-protocol.md`](docs/historical-research-protocol.md)
   for every cutoff-based study.
3. Use [`docs/data-policy.md`](docs/data-policy.md) before adding data.
4. Record experiments and promote only replicated findings to
   [`knowledge/`](knowledge/README.md).

For approved implementation work, use the file-backed runner described in
[`orchestrator/README.md`](orchestrator/README.md).

The bootstrap establishes policy and orchestration only. It does not migrate
legacy code, acquire historical data, or implement a strategy.
