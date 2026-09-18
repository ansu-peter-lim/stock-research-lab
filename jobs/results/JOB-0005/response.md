Implemented the minimal historical identity layer.

- Contract: added `HistoricalIdentityBundle`, `IdentityResolution`, and `IdentityEvidence` in [top30.py](D:\Project\research\src\research_contracts\top30.py). It distinguishes source-observed, point-in-time verified, unresolved, and retrospective identities; preserves provenance, publication/availability timestamps, effective date, and resolution method.
- Integration: `Top30Observation` optionally carries an identity bundle and requires its `MappingState` to exactly equal the bundle’s cutoff-visible result. `AssessmentPayload` includes only that selected point-in-time mapping, never retrospective entries.
- Leakage protection: evidence after cutoff becomes explicit unresolved state (`evidence_after_cutoff`); retrospective-boundary evidence cannot enter assessment; effective date never substitutes for availability.
- Legacy concepts adapted: immutable artifact provenance/digests, temporal identity evidence, explicit effective-date semantics, and unresolved/ambiguous handling. No legacy code or KRX client was migrated.
- Tests: added [test_historical_identity.py](D:\Project\research\tests\test_historical_identity.py) and [historical_identity_bundle.json](D:\Project\research\tests\fixtures\historical_identity_bundle.json), covering all seven requested cases.
- Documentation: updated [top30-observation-contract.md](D:\Project\research\docs\top30-observation-contract.md) with the bundle boundary and limitations.

Validation: `.\.venv\Scripts\python.exe -m pytest -q` → 28 passed. `git diff --check` passed.

Unresolved historical-data question: the repository still lacks immutable historical KRX notice/master artifacts with reliable availability timestamps for the Top30 period; current masters remain retrospective only.

Recommended next job: ingest and validate one small, local historical evidence bundle (raw artifact, digest, publication/availability time) and produce verified/unresolved identity results for a narrow Top30 fixture set.