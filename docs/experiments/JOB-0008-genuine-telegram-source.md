# JOB-0008 Genuine Telegram Source Attempt

## Scope

This job attempted to acquire exactly one historical daily Top30 report from
the public legacy target, `balanceasset`. It did not collect bulk history,
consult KRX/master data, construct outcomes, or create classifications.

## Acquisition method and security

The legacy collector was read-only inspected. It requires `TELEGRAM_API_ID`
and `TELEGRAM_API_HASH`, but only saves current message text under a
date-derived filename. It does not preserve ingestion time, edit time, or
historical byte availability, so it was not used as the artifact format.

`scripts/acquire_job_0008_telegram.py` is a minimal Telethon adapter. It would
search at most 200 messages before `2024-07-01T00:00:00Z`, preserve one
matching daily Top30 message as canonical UTF-8 bytes, and write a deterministic
manifest under `data/raw/telegram/job-0008/`. The manifest binds the Telegram
channel/message identity, source and edit timestamps, ingestion timestamp,
byte length, SHA-256, raw path, provenance, availability statement, parser
version, and acquisition version.

Before the attempt, `.env`, `telegram_sessions/`, `*.session`, and
`*.session-journal` were verified as Git-ignored. The required local credential
variables were present and were consumed only at runtime. No credential values
were printed or persisted.

## Result

Telegram network access succeeded, but Telethon reported that the available
local session is not authorized. No interactive login, phone number, or OTP was
requested or stored. Consequently no Telegram message was retrieved and no raw
artifact, manifest, selected historical report/date, Telegram message ID,
source timestamp, edit timestamp, ingestion timestamp, SHA-256, or parser
observation count exists for this job.

## Availability and assessment boundary

The adapter is intentionally conservative even when a future authorized run
succeeds. Telegram's current API response can establish a message timestamp and
whether an edit timestamp is reported, but it cannot establish a revision
history or prove that retrieved current bytes were visible at the original
historical cutoff. It records `availability_state: unknown` with no invented
availability time. The JOB-0007 parser refuses such a manifest. It also rejects
a known-cutoff fixture when its reported edit time is later than that cutoff.

Therefore no `Top30Observation`, `HistoricalIdentityBundle`, identity mapping,
or frozen assessment was produced. In particular, no current or retrospective
master mapping could enter an assessment.

## Verification

Focused tests cover Git-ignore protection, deterministic manifest metadata,
digest validation, byte-tamper failure, distinct source/edit/ingestion fields,
unknown availability, post-cutoff edits, exact source-name preservation, and
unresolved identity preservation. Existing JOB-0006 and JOB-0007 tests remain
part of the complete test suite.

## Limitation and next gate

An authorized Telegram session is required before one genuine source can be
acquired. Authorization alone would not prove cutoff-visible historical bytes;
the resulting artifact would remain restricted unless independent,
cutoff-timestamped byte availability evidence is obtained. No assessment freeze
is allowed in this run.

ACQUISITION_BLOCKED
