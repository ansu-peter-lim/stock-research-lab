# JOB-0009 Legacy Historical Artifact Audit

Date: 2026-09-19  
Scope: read-only inventory of a small sample from `D:/Project/stock` and code
reference from `D:/Project/stock-trading-system-reference`. No legacy artifact
was copied, altered, parsed in bulk, re-downloaded, or joined to market data.
This audit follows the historical protocol, Top30 contract, and JOB-0006--0008
findings.

## 1. Scope and method

The raw Telegram directory was metadata-enumerated only. Three files were
read to calculate a **CURRENT AUDIT DIGEST** and compare it to the existing
processed report manifest. The term does not mean an acquisition-time digest
and does not prove historical bytes. The compact corresponding inventory is
`data/metadata/job-0009-legacy-artifact-inventory.json`; it references legacy
paths and hashes only.

No credentials, `.env` content, or Telegram session content was inspected.

## 2. Legacy Telegram inventory

| Item | Finding | Evidence / limit |
|---|---|---|
| Raw directory | `D:/Project/stock/data/raw/telegram/daily` | observed path |
| Files / bytes | 782 `.txt` files; 6,319,231 bytes total | metadata enumeration |
| Available filename range | `2023-09-01_07-36-30_15617.txt` through `2026-09-10_09-06-38_30934.txt` | filename range, not ingestion range |
| Convention | `YYYY-MM-DD_HH-MM-SS_<message_id>.txt` | inferred from filename; parser independently decodes this convention |
| Processed manifest | 774 rows, `data/processed/telegram/top30_report_manifest.csv` | stored metadata |
| Manifest coverage gap | eight latest raw files (2026-08-31 through 2026-09-10) are absent; manifest ends `2026-08-28T09:03:56Z` | stored metadata comparison |
| Stored source timestamps / IDs | `telegram_posted_at`, `telegram_message_id` | manifest fields, derived by legacy parser from filename |
| Stored digest | `content_sha256` | processed parser output; acquisition-time creation is not evidenced |
| Ingestion / edit time | absent | no raw/manifest fields found |
| Channel identity | `balanceasset` configured in collector | no numeric chat/channel ID preserved with each raw file |
| Parser/acquisition version | absent from raw and Telegram manifest | collector and parser source have no recorded version field |

The legacy collector (`telegram_collect_3years.py`) reads a configured
Telegram entity and writes `message.text` as UTF-8 to a date-and-ID filename.
It does not write an acquisition timestamp, `edit_date`, revision/deletion
state, chat ID, or digest. A file already at the same filename is skipped.
The raw text is therefore a local normalized UTF-8 text representation, not a
Telegram transport-byte archive.

## 3. Representative artifacts and provenance

All paths below are read-only. `source_timestamp` is from the stored manifest
(which obtains it from the filename); it is a claimed Telegram post time, not
independent proof of cutoff-visible content.

| Case | Raw path / bytes | ID and source timestamp | Stored digest validation | Metadata absent | Class |
|---|---|---|---|---|---|
| Early | `.../2023-09-01_07-36-30_15617.txt`; 8,713 | 15617; `2023-09-01T07:36:30Z` | `67125a36f13ca6dcd300e4814cfb478332e16295f7ecf80e1a629088bbf5c3f4`: match | edit, ingestion, chat ID, acquisition version | C |
| Correction | `.../2024-02-16_09-08-41_17910.txt`; 8,384 | 17910; `2024-02-16T09:08:41Z` | `bc6a222a10241f34ce62267a40ab5f6a28ebd591422d9e25e6fde6d3c6d0c65c`: match | same | C |
| Exact duplicate | `.../2025-12-02_08-37-44_26652.txt`; 8,802 | 26652; `2025-12-02T08:37:44Z` | `a6b7d0acb470f51ad10dc2021f125e8ca5d5563b14bb51695c430ab96e939f6d`: match | same | C |

“Match” means the audit recomputed the current raw file SHA-256 and it equals
the later processed-manifest value. It is not historical digest availability.
Each artifact has `historical_digest_available: false` in the machine-readable
inventory.

`17910` has manifest report date `2024-02-15`, status
`CONFLICTING_REPORT_VERSION`, and a correction to `2024-02-16`. `26652` is one
of two byte-identical reports on `2025-12-02`, with matching digest to `26650`;
the registry excludes `26652`. The duplicate report file exists despite the
collector's same-filename skip because its message ID/timestamp differs.

## 4. Provenance chain reconstructed from code

```text
Telegram balanceasset message
  -> telegram_collect_3years.py: iter_messages / make_filename / write_text
  -> data/raw/telegram/daily/<date>_<time>_<message-id>.txt
  -> telegram_top30_parser/parser.py: parse_report / build_dataset
  -> report_investigation.py: manifest_rows / duplicate reports outputs
  -> manual_corrections.py: apply_corrections
  -> processed/telegram Top30 analysis CSVs
```

Concrete parser functions are `parse_filename`, `parse_report`,
`parse_daily_rows`, and `build_dataset` in
`src/telegram_top30_parser/parser.py`. They compute SHA-256 when parsing and
derive message ID/posted time from the filename. `report_investigation.py`
writes the report manifest and exact/conflicting duplicate files.

This chain preserves current text, filename-encoded post time and ID, and a
parser-time digest. It does not preserve collection time, original message
revision, Telegram edit time, deletion/completeness evidence, raw transport
bytes, or an acquisition-time digest. Thus no sample can establish exactly
what bytes were visible at a historical cutoff.

## 5. Digest and integrity findings

The three representative manifest hashes all match current local bytes (3/3).
The manifest does not state when its hashes were produced and is itself a
processed artifact. It cannot bind a hash to historical availability. No
mismatch was observed, but no historical digest is available.

## 6. Correction layer

The authoritative local registry is
`D:/Project/stock/data/manual/telegram/top30_corrections.csv`, loaded by
`load_corrections` and applied by `apply_corrections` in
`manual_corrections.py`. It has 12 entries: ten `correct_report_date` entries
and two `exclude_report` entries. The observed correction types are therefore
report-date corrections and duplicate/exclusion; the code also supports stock
name, return, and combined stock parsing corrections, but no such stored entry
was found in this registry.

Each correction links by Telegram message ID and, where applicable, rank. Its
reason is recorded, but it has no correction availability timestamp or immutable
correction artifact digest. The `17910` reason is “author date typo confirmed
manually”; the `26652` reason is “exact duplicate of 26650.” Both change the
interpretation/selection of raw source, and are **RETROSPECTIVE_ONLY** until
their historical availability is independently evidenced. Raw Telegram files
must remain immutable; corrections belong in a separately versioned,
retrospective enrichment layer and must never rewrite source text.

## 7. Point-in-time classifications

| Object | Exact classification | Why |
|---|---|---|
| 15617 raw artifact | C — LOCALLY_PRESERVED_PROVENANCE_LIMITED | genuine-looking local text plus later parser metadata; availability/acquisition state not proven |
| 17910 raw artifact | C — LOCALLY_PRESERVED_PROVENANCE_LIMITED | same, plus conflicting report date |
| 26652 raw artifact | C — LOCALLY_PRESERVED_PROVENANCE_LIMITED | same, plus duplicate selection concern |
| correction rows for 17910 / 26652 | D — RETROSPECTIVE_ONLY | manual layer has no cutoff-availability evidence |

Audited sample count: C=3, D=1, A=0, B=0, E=0. No raw artifact was upgraded
to B because even source/channel attribution is configuration-level rather
than preserved per artifact, and C is the conservative category.

## 8. Compatibility with the new fixture pipeline

The raw files may be retained as external references in an immutable fixture
manifest, then parsed to `Top30Observation` with source-observed name and
unresolved identity, then projected through `HistoricalIdentityBundle` to
`AssessmentPayload`, and frozen write-once. But the manifest must set
availability to `unknown` and the JOB-0007 parser must fail closed. These
legacy artifacts must not enter a point-in-time assessment until a separate
provenance repair provides byte-bound, cutoff-visible availability plus edit
state/time semantics. Corrections remain outside `AssessmentPayload` as
retrospective enrichment.

## 9. KRX / Kiwoom historical-data inventory

The legacy data tree contains 44 Kiwoom daily JSON pages under
`data/raw/kiwoom/daily`, for 11 stock codes and raw/adjusted bases. Its
44-line `manifest/requests.jsonl` records SHA-256, byte size, provider,
parser/schema IDs, price basis, retrieval timestamp, page sequence, and 600
rows per page. All listed daily retrievals have base date `20260831`; they may
include earlier bars but their actual historical bar coverage was not parsed.

KRX contains two daily-trade raw JSON files (KOSPI/KOSDAQ) for 2026-08-28 and
a ten-line raw request manifest, with the observed base-date range
2026-07-21--2026-08-28. Those manifests have raw digests and retrieval times,
but several displayed records are schema errors. These data are potentially
useful later, but need a separate raw-vs-adjusted, coverage, revision/vintage,
calendar, and manifest-integrity audit before any outcome use. No Top30 join
or performance calculation was performed.

## 10. Risks and unknowns

- Raw data date range is filename-derived; the source timestamp in the
  processed manifest is also parser-derived from that filename.
- The manifest is stale for the newest eight source files and is not an
  acquisition manifest.
- Telegram edit, deletion, channel completeness, timezone semantics, and
  retrieval timing are unknown.
- Existing corrections are manual retrospective assertions with no known
  historical availability.
- Name-to-code evidence remains unavailable at the required cutoff; current
  KRX masters and later interval reconstruction remain retrospective.
- KRX/Kiwoom data provenance is stronger for recent retrievals, not yet for
  historical outcome eligibility.

## 11. Recommended minimal migration/import strategy

1. Do not copy or transform legacy raw files. Register only one selected
   external path, current audit digest, byte length, and manifest linkage.
2. Preserve missing availability/edit/ingestion fields as `unknown`; reject
   it from assessment freeze rather than backfilling filename time.
3. Keep corrections in a distinct digest-addressed retrospective registry;
   include neither correction-mutated rows nor correction decisions in raw
   fixture bytes.
4. If independent cutoff-visible evidence is later obtained, create a new
   immutable manifest (never replace this audit) and validate source byte
   digest before a one-fixture parser experiment.

## 12. Recommended next job

`JOB-0010`: provenance repair for exactly one selected legacy Telegram
message. Establish a trustworthy acquisition/archival record that binds the
specific message/channel identity, source/edit timestamps, acquisition time,
exact canonical bytes, digest, timezone/precision, and historical availability
claim. Add a manifest adapter that fails closed for missing proof; do not join
outcomes or migrate the corpus.

LEGACY_ARTIFACTS_REQUIRE_PROVENANCE_REPAIR
