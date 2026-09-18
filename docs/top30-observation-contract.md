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
with point-in-time evidence that was available by the cutoff.

## Retrospective boundary

Later identity or classification data is represented separately as
`RetrospectiveEnrichment`. It is retained for audit but never appears in
`AssessmentPayload.from_observation(...)`. Future-dated observations are
rejected, and future mapping evidence cannot be attached to the observation.
Enrichment provenance must carry `boundary="retrospective"`.

`AssessmentPayload` is the cutoff-visible projection to use before any future
outcome join. It deliberately has no enrichment collection, so current KRX
master data cannot silently become historical truth.

Serialization uses sorted JSON keys, explicit UTC timestamps, and decimal
strings for deterministic round-trips. The source artifact remains identified
by its digest and raw reference; this contract does not acquire or rewrite
source data.
