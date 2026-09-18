# JOB-0010 Telegram Provenance Repair

Date: 2026-09-19 (Asia/Seoul)  
Scope: exactly Telegram message `15617`; no bulk acquisition, market outcomes,
current KRX identity, or assessment construction.

## Target and preserved legacy state

The path stated in the job prompt,
`D:/Project/stock/data/telegram/daily/2023-09-01_07-36-30_15617.txt`, does not
exist. The canonical JOB-0009 inventory and the legacy collector both identify
the actual read-only artifact as
`D:/Project/stock/data/raw/telegram/daily/2023-09-01_07-36-30_15617.txt`.
Only that already-audited artifact was used.

Before Telegram access, the artifact was 8,713 bytes and its newly calculated
`CURRENT_AUDIT_DIGEST` was
`67125a36f13ca6dcd300e4814cfb478332e16295f7ecf80e1a629088bbf5c3f4`.
Its filesystem timestamp was `2026-08-29T12:37:20.188550Z`; this is labeled
`LEGACY_FILE_TIMESTAMP` and is not treated as historical availability.

The processed manifest at
`D:/Project/stock/data/processed/telegram/top30_report_manifest.csv` has one
link for message `15617`. It records source file
`2023-09-01_07-36-30_15617.txt`, report date `2023-09-01`, Telegram-posted time
`2023-09-01T07:36:30Z`, and the same digest. The hash match validates current
raw-to-processed linkage only. The manifest hash was calculated by later
parser processing and is not acquisition-time evidence.

The correction registry
`D:/Project/stock/data/manual/telegram/top30_corrections.csv` has no entry for
message `15617`. The repair record nevertheless carries an explicit, separate
retrospective correction link with `entries_found: 0`; no correction was
applied to raw content.

## Session handling and authorization

The original `D:/Project/stock/telegram_test.session` existed and was 28,672
bytes. Its SHA-256 was recorded before access solely as a current mutation
fingerprint. The adapter first verified that
`telegram_sessions/job-0010/telegram_test.session` and its possible journal
are Git-ignored, made a byte-verified working copy there, and passed only the
copy to Telethon. No client opened the original session.

After client disconnect, the original session was again 28,672 bytes and its
SHA-256 equaled the pre-access fingerprint. The high-severity mutation guard
therefore passed. Session contents, phone/account identity, credentials,
tokens, API ID, and API hash were neither printed nor persisted.

The copied session was authorized. No interactive login, OTP, 2FA, or account
inspection was attempted.

## Exact Telegram retrieval

The adapter used the legacy-configured public source name `balanceasset`,
verified the returned entity username, and made one exact-ID request for
message `15617`. It did not iterate, search, or download channel history.

The non-secret retrieval result was:

- stable provenance identifier:
  `telegram:channel_peer_id:-1001428344040:username:balanceasset`;
- message ID: `15617`;
- `SOURCE_TIMESTAMP`: `2023-09-01T07:36:30.000000Z`;
- `EDIT_TIMESTAMP`: no edit timestamp reported by the current API;
- edit semantics: `NONE_REPORTED_BY_CURRENT_API`, not proof that no historical
  edit ever occurred;
- `RETRIEVAL_TIMESTAMP`: `2026-09-18T16:06:16.838955Z`;
- current state: the exact message was returned; this does not prove channel
  completeness or absence of other deleted history.

The source timestamp exactly matches the legacy filename-derived and processed
manifest timestamp. The intended historical cutoff is conservatively the
message source timestamp, because that is the original report publication
boundary implied by the source semantics. It is not promoted to proof that the
retrieved current bytes were immutable at that time.

## Legacy serialization reconstruction and content comparison

Read-only inspection of `telegram_collect_3years.py` established the exact
legacy write operation: `Path.write_text(message.text, encoding="utf-8")` on
Windows. It added no header, metadata, BOM, Unicode normalization, trimming,
or trailing newline. Python's Windows text mode translated each LF in the
Telethon string to CRLF. The preserved raw file has 68 CRLF sequences, no bare
LF or CR, no BOM, and no trailing newline.

The three comparison levels are retained separately in the repair record:

| Level | Bytes / SHA-256 | Result semantics |
|---|---|---|
| `RAW_FILE_BYTES` | 8,713 / `67125a36f13ca6dcd300e4814cfb478332e16295f7ecf80e1a629088bbf5c3f4` | Current audit of the legacy file |
| `LEGACY_SERIALIZED_MESSAGE_CONTENT` | 8,713 / `67125a36f13ca6dcd300e4814cfb478332e16295f7ecf80e1a629088bbf5c3f4` | Current Telegram text after only the documented Windows LF-to-CRLF write transformation |
| `CURRENT_TELEGRAM_MESSAGE_CONTENT` | 8,645 / `be2cefa7a3a08bed3ee6e33ba78e71e0a1c4581a0b265b847f3901eb15d42872` | Direct UTF-8 encoding of the current Telethon string, with no normalization |

The raw file is not byte-identical to the direct current UTF-8 representation
because of those 68 newline bytes. It is an exact byte match to the
deterministically reconstructed legacy serialization. The explicit overall
result is `CANONICAL_MATCH`. No heuristic, whitespace collapse, Unicode
normalization, or undocumented transformation was tried.

## Availability and evidence classification

The current API response verifies the configured source, stable channel peer
identifier, exact message ID, message timestamp, and current content. The
independently preserved legacy artifact matches that content under the exact
collector serialization rules, and its later parser-time manifest hash still
matches.

This does not establish when the local file was first acquired, provide an
acquisition-time hash, expose revision history, or prove immutable byte-level
content at `2023-09-01T07:36:30Z`. The absent current edit timestamp is not
overstated as historical no-edit proof. `HISTORICAL_AVAILABILITY` therefore
remains unknown for assessment purposes.

The single-artifact classification is:

`B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED`

Class A is not justified. There is no content conflict, so Classes C and E are
not justified; Telegram verification succeeded, so Class D is not applicable.

## Repair record and new-pipeline boundary

The deterministic repair record is
`data/metadata/job-0010-telegram-provenance-repair.json`. Its schema is
`job-0010-telegram-provenance-repair-1`, its record ID is
`JOB-0010-telegram-balanceasset-15617`, and its canonical JSON content digest
is `ac9e65d1953bb625dea901b64c2326d019b7a59df31ec809bb40a6fa3c8d74d0`.
The digest binds the legacy current-audit evidence, processed-manifest link,
separate correction link, source/message metadata, timestamp roles, explicit
comparison levels and transformations, evidence class, availability
interpretation, session mutation result, and limitations.

A minimal genuine fixture reference was permitted at
`data/fixtures/job-0010/fixture-manifest.json`. It references the one external
read-only legacy artifact instead of copying the legacy corpus, binds the
repair-record digest, and revalidates the external bytes against an allowlisted
read-only legacy root. It deliberately states:

- `digest_kind: CURRENT_AUDIT_DIGEST`;
- `availability_state: unknown`;
- `available_at: null`;
- `assessment_permitted: false`.

This is enough to identify and reproduce the single genuine source fixture in
the next bounded experiment, but not enough to parse it into a cutoff-visible
`Top30Observation`, create an `AssessmentPayload`, or freeze an assessment.
JOB-0006 protections remain unchanged.

## Verification and limitations

Focused tests cover the original-session isolation guard, ignored working
copies, size/hash mutation detection, secret non-persistence, deterministic
raw and repair digests, processed-manifest linkage, explicit source/message
identity, distinct timestamp roles, conservative no-edit/unknown-edit
semantics, documented serialization, mismatch handling, explicit evidence
classification, current-versus-acquisition digest labels, retrospective
correction separation, restricted fixture behavior, and generated-artifact
digest binding. The complete test suite and `git diff --check` are the final
quality gates for this job.

Residual risks are the unavailable acquisition timestamp and acquisition-time
digest, no historical revision stream, no proof of deleted-message/channel
completeness, and no immutable archival witness at the intended cutoff. The
next job should parse only this externally referenced artifact into unresolved
source observations while preserving `availability_state: unknown`, and test
the gate that refuses assessment. Obtaining genuinely cutoff-verified content
would require independent contemporaneous archival evidence; it must not be
inferred from this match.

REAL_FIXTURE_PROVENANCE_READY_WITH_RESTRICTIONS
