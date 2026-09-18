# Historical Top30 Observation Contract

This contract is the narrow boundary between parsing a historical Top30 source
and a future research pipeline. It is not a KRX, eligibility, market-data, or
backtest model.

## Cutoff-known observation

`Top30Observation` stores the report's `observation_date`, the immutable
`cutoff_at` (the source publication/availability time), optional rank, and the
stock name exactly as parsed. It also stores the parser version, ingestion
time, raw detail, return percentage when parsed, and a `Provenance` record with
source identity, raw reference, SHA-256, availability time, and an explicit
`boundary="point_in_time"` marker.

The source availability and any code evidence must be at or before
`cutoff_at`. An unresolved mapping is represented explicitly by
`MappingState(status="unresolved", stock_code=None)`. A code is accepted only
with point-in-time evidence that was available by the cutoff. Provenance must
carry an explicit boundary; deserialization never defaults a missing boundary
to point-in-time. A confirmed observation mapping must be derived from and
match a `HistoricalIdentityBundle`; direct confirmed mappings are rejected.

## Historical identity bundle

`HistoricalIdentityBundle` is the deliberately small name-to-code boundary.
It preserves the source-observed name and a single resolution classified as
`source_observed`, `point_in_time_verified`, or `unresolved`. A verified
resolution contains immutable `IdentityEvidence`: provenance (including raw
reference, digest, and `available_at`), optional `published_at`, optional
`effective_date`, and an explicit resolution method. Publication/availability
time answers when the evidence could be used; effective date describes the
identity fact and is never substituted for availability.

The bundle may also retain `retrospective_enrichment` resolutions. Those have
retrospective provenance and remain serializable for audit, but
`assessment_mapping(cutoff_at)` never promotes them. A point-in-time candidate
whose evidence becomes available after the cutoff likewise yields an explicit
unresolved mapping with method `evidence_after_cutoff`; no code is guessed.
`AssessmentPayload` carries the resulting point-in-time `MappingState` only,
not the bundle's retrospective collection.

Known limitation: no local historical KRX notices/master artifacts have yet
been acquired for the three-year Top30 history. A current KRX master, an
observed interval reconstructed later, or an unproven effective date can be
kept only as retrospective/review material until an immutable source with a
cutoff-visible availability timestamp is supplied.

## Retrospective boundary

Later identity or classification data is represented separately as
`RetrospectiveEnrichment`. It is retained for audit but never appears in
`AssessmentPayload.from_observation(...)`. Future-dated observations are
rejected, and future mapping evidence cannot be attached to the observation.
Enrichment provenance must carry `boundary="retrospective"`.

`AssessmentPayload` is the cutoff-visible projection to use before any future
outcome join. It deliberately has no enrichment collection, so current KRX
master data cannot silently become historical truth. Its constructor and
deserializer revalidate the source boundary, cutoff visibility, identity
evidence, mapping status, and stock-code consistency. Callers cannot bypass
`from_observation(...)` by directly supplying inconsistent duplicated fields.

Serialization uses sorted JSON keys, explicit UTC timestamps, and decimal
strings for deterministic round-trips. The source artifact remains identified
by its digest and raw reference; this contract does not acquire or rewrite
source data.
