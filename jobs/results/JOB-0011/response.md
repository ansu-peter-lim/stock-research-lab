Implemented the quarantined real-source parsing path and documentation: [parser contract](/D:/Project/research/src/research_contracts/pre_assessment.py), [artifact](/D:/Project/research/data/fixtures/job-0011/quarantined/telegram-balanceasset-15617.preassessment.json), and [JOB-0011 report](/D:/Project/research/docs/experiments/JOB-0011-real-pre-assessment-parsing.md).

- Requested model tier: `standard`
- Actual model telemetry: unavailable (`null`)
- Source message ID: `15617`
- Inherited provenance: `B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED`
- Parsed result: recognized Top30; report date `2023-09-01`; 30 rows; ranks 1–30 exactly once
- Malformed/skipped rows: 0
- Corrections for message: 0
- Unresolved identities: 30
- Source digest: `67125a36f13ca6dcd300e4814cfb478332e16295f7ecf80e1a629088bbf5c3f4`
- Parsed representation digest: `97e6e8066e86938d3ae100e89d2d45ff8adb8e7ee133d69e1993e6ad17e1e144`
- Quarantine gate: promotion to `Top30Observation`, `AssessmentPayload`, and frozen assessment explicitly raises `QuarantineError`.
- Tests: complete suite passed, `81 passed`; `git diff --check` passed.
- No legacy source, correction registry, market/outcome data, credentials, or sessions were changed/accessed.

Residual risk: exact cutoff-visible byte availability, historical revisions, acquisition timing, deletion history, and channel completeness remain unproven.

Recommended next job: policy review or acquisition of independent contemporaneous archival evidence establishing cutoff-visible immutable bytes—without authorizing assessment or outcome joins yet.

PREASSESSMENT_PIPELINE_READY_WITH_RESTRICTIONS