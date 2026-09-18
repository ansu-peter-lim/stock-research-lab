Requested model tier: `standard`. Actual model telemetry: unavailable.

Credentials were successfully consumed at runtime to reach Telegram authentication; no values were exposed or persisted. Telegram reported the local session is unauthorized.

- Historical report/date/message ID: not acquired
- Source/edit/ingestion timestamps and SHA-256: not available; no genuine artifact was written
- Observations / identities: none
- Assessment freeze: not allowed
- Added Git-ignore protection for Telegram session artifacts, a guarded one-message acquisition adapter, timestamp/manifest fields, and focused fail-closed tests.
- Tests: `55 passed` (`python -m pytest -p no:cacheprovider`)
- `git diff --check`: passed

Residual risk: even an authorized current Telegram retrieval cannot prove that current message bytes were visible at the historical cutoff; the adapter records this as unknown and blocks assessment creation.

Recommended next job: authorize a Git-ignored local Telegram session, acquire one message, then seek independent cutoff-time byte-availability evidence before any frozen assessment.

ACQUISITION_BLOCKED