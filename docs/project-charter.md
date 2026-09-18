# Project Charter

## Purpose

Stock Research Lab studies historical Top30 Korean-stock snapshots from
approximately three years before the start date forward through time. It
separates what could have been known at each historical cutoff from outcomes
that became known later.

## Research questions

- What market, sector, and stock conditions were observable at each cutoff?
- Which observations predict subsequent +5, +10, +20, and +60 trading-day
  outcomes?
- Which apparent findings survive across adequate, independently defined
  samples?

## Governance

- The owner controls direction, scope, and approval gates.
- ChatGPT acts as research lead and reviews Codex work.
- Codex implements, tests, and reports evidence.
- GitHub is the durable source of truth.
- This repository is `stock-research-lab`; the legacy trading repository is
  read-only for migration purposes and must not be modified.

## Non-goals for bootstrap

No live execution, credentials, premature strategy, or unnecessary framework
is introduced. Bootstrap-001 establishes the research contract and migration
policy; later jobs must be separately scoped and approved.
