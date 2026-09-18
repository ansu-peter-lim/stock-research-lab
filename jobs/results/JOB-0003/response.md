Implemented the minimal point-in-time Top30 contract.

- Contract: immutable `Top30Observation`, explicit cutoff/availability timestamps, exact source name, optional rank/return, provenance digest/reference, parser version, ingestion time, unresolved mapping state, and serialized boundary markers.
- Leakage protection: future mapping evidence is rejected; retrospective enrichments are auditable but excluded from `AssessmentPayload`.
- Added deterministic JSON round-trip serialization.
- Added `python -m orchestrator new JOB-0004` convenience command.

Files:

- [top30.py](D:/Project/research/src/research_contracts/top30.py)
- [contract documentation](D:/Project/research/docs/top30-observation-contract.md)
- [contract tests](D:/Project/research/tests/test_top30_contract.py)
- [representative fixture](D:/Project/research/tests/fixtures/top30_legacy_row.json)
- Updated orchestrator and tests.

Verification:

- `17 passed`
- `git diff --check` passed
- No commits or pushes.
- Legacy repository was only read; no writes were performed.

Unresolved questions:

- Telegram edit/deletion and availability semantics.
- Ranking ties, duplicate reports, and cutoff convention.
- Historical name/code evidence publication versus effective dates.

Recommended next job: build one cutoff-aware KRX historical identity bundle with explicit publication and effective-date provenance.