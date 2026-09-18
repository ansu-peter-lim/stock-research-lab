Implemented the small fixture pipeline and frozen artifact.

- Requested model tier: not specified
- Actual model: runtime telemetry not exposed
- Fixture: two Top30 observations at `2024-04-18T12:00:00Z` — 1 resolved, 1 unresolved
- Provenance: explicitly synthetic local boundary fixture; legacy repo had no raw Telegram export to reuse, so it makes no claim about external historical publication/availability
- Created/changed:
  - [historical_fixture.py](D:\Project\research\src\research_contracts\historical_fixture.py)
  - [fixture manifest](D:\Project\research\data\fixtures\job-0007\fixture-manifest.json)
  - [raw fixture](D:\Project\research\data\fixtures\job-0007\raw\top30-2024-04-18.txt)
  - [frozen assessment](D:\Project\research\data\fixtures\job-0007\frozen\job-0007-top30-2024-04-18.json)
  - [tests](D:\Project\research\tests\test_historical_fixture.py)
  - [experiment documentation](D:\Project\research\docs\experiments\JOB-0007-historical-fixture.md)
  - [exports](D:\Project\research\src\research_contracts\__init__.py)
- Identity counts: 1 resolved (`005930` from immutable fixture content), 1 explicit unresolved
- Manifest validation: passes; byte modification fails validation
- Frozen write-once: identical re-freeze is a no-op; differing content raises `FileExistsError`
- Outcome safety: frozen artifact has no outcome/future/OHLCV/label fields; no network or outcome data used
- Verification: `python -m pytest -q` → 50 passed; `git diff --check` passed
- Untouched: pre-existing untracked `jobs/JOB-0007.*` files

Residual risk: this validates mechanics only. A real outcome-fixture experiment still requires byte-preserved historical Top30 material with independently proven availability and subject-specific historical identity evidence.

Recommended next job: acquire and manifest one genuine local historical source artifact with reliable availability evidence, then repeat this pipeline before allowing any outcome join.

READY_WITH_RESTRICTIONS