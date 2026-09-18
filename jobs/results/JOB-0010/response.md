JOB-0010 completed for message `15617` only.

- Requested model tier: `advanced`
- Actual model: not exposed by telemetry (`null`)
- Authorization: `AUTHORIZED`; no interactive login
- Original session mutation check: passed; size and SHA-256 unchanged
- Telegram source timestamp: `2023-09-01T07:36:30Z`
- Edit timestamp: none reported by current API; historical no-edit is not proven
- Retrieval timestamp: `2026-09-18T16:06:16.838955Z`
- Legacy artifact SHA-256: `67125a36f13ca6dcd300e4814cfb478332e16295f7ecf80e1a629088bbf5c3f4`
- Legacy manifest hash: match
- Content comparison: `CANONICAL_MATCH`—exact match after documented Windows LF-to-CRLF legacy serialization; direct current UTF-8 bytes differ only at that explicit serialization layer
- Evidence classification: `B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED`
- Correction linkage: none (`0` entries)
- Genuine fixture manifest: allowed with restrictions; availability remains unknown and assessment is prohibited
- Assessment/frozen assessment created: no
- Tests: `74 passed`
- `git diff --check`: passed
- Commit/push: not performed

Artifacts:

- [Experiment report](D:/Project/research/docs/experiments/JOB-0010-telegram-provenance-repair.md)
- [Provenance repair record](D:/Project/research/data/metadata/job-0010-telegram-provenance-repair.json)
- [Restricted fixture manifest](D:/Project/research/data/fixtures/job-0010/fixture-manifest.json)
- [Acquisition adapter](D:/Project/research/scripts/acquire_job_0010_telegram_provenance.py)
- [Focused tests](D:/Project/research/tests/test_job_0010_telegram_provenance_repair.py)

Residual risks are the missing acquisition-time timestamp/hash, unavailable revision history, lack of channel/deletion completeness evidence, and no independent archival witness proving these exact bytes at the historical cutoff.

Recommended next job: validate parsing of this single restricted external fixture into a pre-assessment representation while proving that unknown availability cannot produce a `Top30Observation`, `AssessmentPayload`, or frozen assessment. Do not add outcomes or broaden acquisition.

REAL_FIXTURE_PROVENANCE_READY_WITH_RESTRICTIONS