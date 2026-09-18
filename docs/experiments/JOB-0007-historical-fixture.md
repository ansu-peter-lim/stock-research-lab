# JOB-0007 Historical Fixture Experiment

## Scope and provenance

This is a two-observation, one-date (`2024-04-18`) local boundary experiment.
The raw bytes are at `data/fixtures/job-0007/raw/top30-2024-04-18.txt`; its
manifested SHA-256 is
`1e5e46cfa022c43cf4d97868769d16b3c9bebe8a79175c4c3da675ecfd75fe04`.

The legacy reference repository was inspected read-only. It contains no raw
Telegram export in either the checkout or tracked Git tree. The legacy parser
and the JOB-0006 audit also establish that a reconstructed Telegram text file
cannot prove message availability or edit history. Therefore this raw artifact
is an explicitly **synthetic local boundary fixture**, not a claimed Telegram
export and not evidence of external historical publication. No network source,
current KRX master, or outcome data was used.

The fixture's local construction timestamp, local availability timestamp, and
assessment cutoff are all the declared `2024-04-18T12:00:00Z`. They model a
known local fixture boundary only; they do not assert a real-world historical
publication time. The manifest supports `availability_state: unknown` with no
timestamp, and fail-closes such a fixture before it can enter an assessment.

## Manifest and parsing

`fixture-manifest.json` deterministically binds the fixture ID, raw relative
path, exact byte length, SHA-256, provenance, source timestamp, ingestion time,
availability state/time, artifact type, and parser version. Validation reads
bytes directly and rejects a length or digest mismatch before parsing.

The narrow parser consumes only the fixture's four fields: rank, source-observed
name, an optional embedded code, and raw detail. It produces two observations:

- `Fixture Resolved Co` resolves to `005930` from the immutable fixture row.
- `Fixture Unresolved Co` has no cutoff-visible identity evidence and remains
  `unresolved` with no code.

The resolved mapping is solely a synthetic parser-contract demonstration. It is
not a KRX historical identity assertion. The unresolved row is retained through
the frozen assessment without current mapping or guessing.

## Freeze semantics

The frozen file is
`data/fixtures/job-0007/frozen/job-0007-top30-2024-04-18.json`. It binds the
manifest digest, cutoff, all assessment payloads, schema/contract versions,
creation metadata, and a deterministic content digest. `write_frozen_assessment`
uses exclusive creation: an identical file is an idempotent no-op; any different
content at the same path raises `FileExistsError` and is never replaced.

The serialized artifact has no retrospective identity collection and no outcome,
future OHLCV, horizon-return, sector-performance, or success-label fields.

## Limitations and readiness

This validates the mechanics, not a historical source claim. A real fixture
still needs byte-preserved Top30 source material plus independently evidenced
historical availability and, for a resolved name, identity evidence that binds
the exact source-observed name to the code at the date. The current synthetic
known-local availability must never be reinterpreted as a Telegram timestamp.

READY_WITH_RESTRICTIONS
