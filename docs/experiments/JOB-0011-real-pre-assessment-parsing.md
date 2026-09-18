# JOB-0011 Real Pre-Assessment Parsing

Date: 2026-09-19 (Asia/Seoul)  
Scope: exactly Telegram message `15617`; no market, outcome, KRX/master, or bulk-source access.

## Source and inherited provenance

The one source is the read-only legacy artifact
`D:/Project/stock/data/raw/telegram/daily/2023-09-01_07-36-30_15617.txt`.
The prompt's non-`raw` path does not exist; JOB-0010 established this canonical
location.  Its current-audit source digest is
`67125a36f13ca6dcd300e4814cfb478332e16295f7ecf80e1a629088bbf5c3f4`.

The JOB-0010 repair record and external restricted fixture manifest are the
only provenance inputs.  Their binding repair digest is
`ac9e65d1953bb625dea901b64c2326d019b7a59df31ec809bb40a6fa3c8d74d0`.
The inherited classification is
`B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED`; availability remains `unknown`.
The source-fixture manifest digest is
`0edd94de46823d89b6a96aee114f0bf9edd8a51b0f8c8e8ce3635a3aa648953e`.

## Minimal parser adaptation

The legacy parser recognizes daily reports from a Korean calendar-date header
containing `상승률 TOP30`; it obtains Telegram post time and ID from the
filename, captures rank/name/percentage headers, and carries all following
text as row detail. It detects missing, duplicate, and out-of-range ranks.
Its broader architecture also classifies weekly/monthly/intraday reports,
builds whole-directory duplicate groups, and later applies a separate manual
correction layer. None of those broad paths was migrated.

`src/research_contracts/pre_assessment.py` adapts only the message-15617 daily
header and numbered-row grammar. It validates the restricted fixture bytes
and the canonical repair-record digest *before* decoding/parsing. It preserves
the source name exactly in `source_stock_name`; no normalization or KRX/master
lookup exists in this stage. The only safely parsed numeric field is
`return_pct`; raw detail is retained. Malformed numbered lines become explicit
issues and cannot silently count as valid rows.

## Result

The source is recognized as a daily Top30 report. Its report-date candidate and
source timestamp are respectively `2023-09-01` and `2023-09-01T07:36:30Z`.
It yielded 30 rows with ranks 1 through 30 exactly once, no malformed/skipped
rows, and no duplicate ranks. All 30 return percentages parsed. All 30
identities remain explicitly `unresolved`.

Exact source names, in observed rank order, are: 희림, 하나마이크론, 머큐리,
스마트레이더시스템, 시너지이노베이션, 크라우드웍스, 넥스트칩, 피씨엘, 제이티,
노을, 한미글로벌, CBI, 티라유텍, 이노시뮬레이션, 스맥, 미래반도체, 코디,
코아시아, 마이크로컨텍솔, 티에프이, 유진테크, 미코, 유티아이,
하나머티리얼즈, 펨트론, 삼부토건, 라온텍, 디에스케이, 이랜시스, 샘씨엔에스.

The authoritative correction registry was checked by exact message ID. It has
zero entries for `15617`; no correction was applied. Corrections remain an
external retrospective layer and cannot change immutable raw observations.

## Pre-assessment and quarantine boundary

`PreAssessmentTop30` is intentionally not a `Top30Observation`. It carries
fixture/provenance references, source/message timestamps, report-date
candidate, source names, rank, parsed numeric values, parser version,
classification, availability state, unresolved identity state, and quarantine
reason. Its methods for promotion, assessment-payload creation, and assessment
freezing each raise `QuarantineError`.

The deterministic machine-readable artifact is
`data/fixtures/job-0011/quarantined/telegram-balanceasset-15617.preassessment.json`.
It identifies itself as `QUARANTINED / NOT ASSESSMENT ELIGIBLE`; it is not named
or structured as a frozen assessment. Its parsed representation digest is
`97e6e8066e86938d3ae100e89d2d45ff8adb8e7ee133d69e1993e6ad17e1e144`.
The digest covers fixture-manifest digest, source digest, repair record/digest,
parser version, parsed rows, issues, correction count, and quarantine state.
Source-byte mismatch blocks parsing; a changed parser version is rejected; a
changed bound source digest invalidates the representation digest.

## Limitations

This validates parsing and containment, not historical availability. Current
source verification plus a later preserved file does not prove cutoff-visible
immutable bytes, historical edit history, acquisition timing, deletions, or
channel completeness. No assessment, frozen assessment, identity resolution,
outcome join, or three-year processing is authorized.

PREASSESSMENT_PIPELINE_READY_WITH_RESTRICTIONS
