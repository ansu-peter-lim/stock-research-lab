Completed the audit and added:

- [JOB-0009 audit report](D:\Project\research\docs\audits\JOB-0009-legacy-historical-artifact-audit.md)
- [Machine-readable inventory](D:\Project\research\data\metadata\job-0009-legacy-artifact-inventory.json)
- Read-only inventory safeguards and focused tests in [legacy_artifact_inventory.py](D:\Project\research\src\research_contracts\legacy_artifact_inventory.py)

Requested model tier: not specified. Actual model telemetry: not exposed.

Telegram inventory: 782 raw artifacts, filename range 2023-09-01 through 2026-09-10. The processed manifest covers 774 files and is stale for the newest eight.

Audited samples:

- Early: `2023-09-01_07-36-30_15617.txt`
- Correction: `2024-02-16_09-08-41_17910.txt`
- Exact duplicate: `2025-12-02_08-37-44_26652.txt`

The authoritative correction registry was found at `D:/Project/stock/data/manual/telegram/top30_corrections.csv`. It remains explicitly retrospective and separate from raw artifacts.

Historical acquisition-time digests are unavailable. Current audit SHA-256 values match the stored processed-manifest hashes for all three samples (3/3), but are not historical-byte proof.

Classification counts: C=3 (`LOCALLY_PRESERVED_PROVENANCE_LIMITED`), D=1 retrospective correction layer. Existing Kiwoom daily data and KRX daily-trade data with manifests were found, but require a separate provenance/coverage audit before outcome use.

Verification: `pytest` passed, 61 tests total; `git diff --check` passed. Pytest emitted one non-failing cache-permission warning.

Major residual risks: no acquisition timestamps, edit/revision state, channel/chat ID per artifact, historical availability proof, or acquisition-time digests; the Telegram processed manifest is not current for the newest eight files.

Recommended next job: provenance repair for exactly one message, producing byte-bound evidence of message/channel identity, edit/acquisition timestamps, and cutoff-visible availability before any real fixture conversion.

LEGACY_ARTIFACTS_REQUIRE_PROVENANCE_REPAIR