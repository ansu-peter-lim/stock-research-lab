# JOB-0006 Point-in-Time Leakage Audit

Date: 2026-09-18  
Verdict: **READY_WITH_RESTRICTIONS**  
Scope of verdict: one small local historical fixture experiment only; not the
three-year study.

## Audit scope

This audit reviewed the complete intended boundary:

```text
Top30 source observation
  -> Top30Observation
  -> HistoricalIdentityBundle
  -> IdentityResolution
  -> AssessmentPayload
```

All canonical repository documents were read before the implementation review.
The audit then reviewed `src/research_contracts/top30.py`, its exports, fixtures,
and all tests. The local legacy repository at
`D:/Project/stock-trading-system-reference` was inspected at commit
`97aa1e67b0b40a6d8696f5ab2e57413724be800d`, including the Telegram collector
and parser, manual corrections, historical master, KRX master builder, official
event evidence, historical eligibility, and relevant tests. The legacy worktree
was not modified. No network sources were used.

The review tested ordinary constructors, alternate direct constructors,
dictionary/JSON deserialization, round trips, duplicated fields, timezone
normalization, equality at cutoff, later projections, and retrospective
collections. It also considered source behavior that the current contract does
not itself implement, especially Telegram acquisition and KRX evidence
production.

## Threat model

The threat is not limited to a malicious actor. It includes an honest adapter
using `effective_date`, `source_as_of`, a Telegram filename timestamp, or a
current master snapshot as if it proved historical availability. It also
includes stale or hand-edited JSON, digest/reference mix-ups, later manual
corrections, re-running an old cutoff after new evidence is learned, and
downstream code silently dropping unresolved rows.

Inputs and serialized objects are therefore treated as untrusted until the
following are established independently:

- the exact raw bytes and their digest;
- what the referenced artifact is and which identity assertion it supports;
- when those exact bytes or that fact were observable;
- publication, retrieval/ingestion, edit, and effective times without
  collapsing them;
- whether an assessment artifact was already frozen and must not be replaced.

The Python models can enforce internal consistency. They cannot prove that a
caller told the truth about an artifact, timestamp, or evidence subject.

## Finding counts

| Severity | Count | Fixed here | Residual |
|---|---:|---:|---:|
| CRITICAL | 1 | 1 | 0 |
| HIGH | 6 | 2 | 4 |
| MEDIUM | 5 | 0 | 5 |
| LOW | 2 | 0 | 2 |

## Findings by severity

### CRITICAL

#### C-01: `AssessmentPayload` accepted unchecked direct construction — fixed

Before this audit, `AssessmentPayload` had no `__post_init__`. A caller could
directly provide a historical cutoff, a stock code, a confirmed status, a
future or retrospective source, and no selected identity state. The object
would serialize the injected code. This bypassed both
`AssessmentPayload.from_observation(...)` and all earlier cutoff checks, so
explicitly future information could enter the assessment.

The fix revalidates the point-in-time boundary, source availability, rank,
identity presence, mapping status/code consistency, and identity-evidence
availability for every construction path. Deterministic payload
`to_json`/`from_json` and `from_dict` paths now re-run the same invariants.

### HIGH

#### H-01: A confirmed observation could bypass the identity bundle — fixed

`Top30Observation(identity=None, mapping=<confirmed>)` was accepted when the
mapping evidence timestamp was at or before cutoff. That made
`HistoricalIdentityBundle` optional on the exact path where it was supposed to
be the identity boundary. A caller could therefore attach a manually produced
or current-master-derived `MappingState` without the advertised resolution
chain.

Confirmed observations now require a bundle, and the stored mapping must equal
the bundle's cutoff-selected result. Safe legacy observations may still omit a
bundle only when they remain unresolved.

#### H-02: Missing provenance boundaries were upgraded and retrospective sources were accepted — fixed

`Provenance.from_dict` defaulted a missing `boundary` to `point_in_time`, and
`Top30Observation` did not require its source itself to be point-in-time. A
legacy or edited serialized artifact could consequently lose its retrospective
marker and enter an assessment as a source observation.

The boundary is now mandatory in constructors and serialized input. Observation
and assessment sources must be point-in-time. A retrospective resolution cannot
occupy the bundle's primary resolution slot, and a direct constructor cannot
attach an enrichment whose availability is at or before the cutoff.

#### H-03: Current-master and provenance truth remain declarative — residual

There is no automatic current-master lookup in this repository, which is good.
Correctly labeled current-master evidence with a post-cutoff `available_at` is
excluded. However, `Provenance` validates only required strings, digest syntax,
timestamp awareness, and the declared boundary. It does not open
`raw_reference`, compare the actual bytes to `content_sha256`, authenticate the
source, or prove `available_at`.

A caller can still label a current master `point_in_time` and copy an old
effective or `source_as_of` date into `available_at`. The models cannot
distinguish that lie from valid historical evidence. The legacy historical
master is especially unsafe as a direct input because its mapper selects by
effective intervals while `source_as_of` is not used as a cutoff gate.

This is not fixed locally because it requires a verified artifact manifest and
adapter boundary, not a source-kind blacklist. Current masters must remain
retrospective regardless of the dates they describe.

#### H-04: Legacy Telegram exports do not establish historical message state — residual

The legacy collector writes `message.text` under a filename built from
`message.date` and skips an existing filename. It does not record acquisition
time, `edit_date`, revision history, deletion state, or channel completeness.
When collecting old history, the text can be the latest edited state while the
filename still carries the original post time. The parser then derives
`telegram_posted_at` from that filename and has no edit/acquisition field.

Consequences include post-cutoff edits masquerading as original content,
deleted reports disappearing, delayed ingestion being confused with
availability, and duplicate/conflicting versions lacking an availability-aware
selection rule. The current lab has not migrated this parser, so this is a
blocked adapter path rather than a present automatic leak. Direct adaptation is
not safe.

#### H-05: Frozen in-memory objects do not prevent historical artifact rewrite — residual

The dataclasses are frozen, and a later projection of the same unresolved
`Top30Observation` remains unresolved. That behavior passed adversarial tests.
Nevertheless, a caller can build a new observation for the same source,
cutoff, and row after learning a mapping and overwrite an earlier serialized
assessment. There is no assessment artifact identifier, schema/code version,
creation record, content digest, append-only manifest, or no-overwrite store in
the current slice.

The small fixture must use write-once, digest-addressed assessment artifacts.
Later identity discoveries must create a separately versioned retrospective or
reassessment artifact and must not replace the frozen assessment used for
outcomes.

#### H-06: Identity evidence is not bound to its asserted subject or lifecycle — residual

`IdentityEvidence` contains generic provenance, dates, and a free-form
reference, but it does not encode the names asserted by the evidence, code
namespace, market, event type/revision, or validity interval. Thus any
cutoff-visible artifact can be packaged as support for any observed name and
six-digit code if the caller labels the resolution verified. The model cannot
detect that the notice concerns another issuer or another point in a merger,
split, relisting, or rename lifecycle.

For the fixture, verified mappings require manual byte-level review that the
artifact explicitly binds the exact observed name and canonical code at the
observation date. Anything else remains unresolved. A fuller evidence schema is
deferred.

### MEDIUM

#### M-01: Effective-date applicability is not evaluated

Availability is correctly the cutoff gate: a past effective date does not make
late evidence usable, publication before cutoff does not override later
availability, equality is inclusive, and one microsecond after cutoff is
excluded. However, `assessment_mapping` does not decide whether an
`effective_date` is applicable to the observation date. A pre-cutoff notice of
a future rename could be used too early if the caller creates a verified
resolution. This is an identity-validity error, not availability leakage.

#### M-02: Ambiguity and corporate-event candidates are not represented

The bundle holds one primary resolution, not a set of conflicting candidates.
Same or normalized names, reused names, code changes, market transfers,
mergers, splits, delisting/relisting, and competing revisions must currently be
collapsed by the caller to an unresolved method string. That is safe only if
the caller is conservative. No automatic historical name resolver should be
added until these cases have explicit fixture tests.

#### M-03: Timestamp precision and source timezone semantics are absent

Naive datetimes and date-only serialized datetimes are rejected, and aware
offsets normalize correctly to UTC. The schema still cannot say that an
availability time is only date-precision, estimated, copied from a source
timezone, or publication-time uncertain. Converting a date-only record to
`00:00:00Z` produces a syntactically valid but unjustifiably precise timestamp.
Intraday fixtures must require evidenced timestamps; uncertain publication
times remain unavailable until the end of their uncertainty interval or remain
unresolved.

#### M-04: Duplicate selection and manual correction availability are outside the contract

The legacy parser flags exact/conflicting duplicate report dates, but the later
manual-correction layer can select a report or change report date, name, and
return without an availability timestamp or immutable source digest on the
correction itself. Such corrections may be useful retrospectively but cannot
silently rewrite a historical source observation.

#### M-05: Unresolved downstream behavior is a policy, not yet an enforced pipeline

The payload now carries `mapping_status="unresolved"`, `stock_code=None`, and
its selected `MappingState`; later projection does not guess a code. There is
no downstream analysis implementation in scope, so nothing yet prevents future
code from filtering these rows, joining them to a current map, or excluding
them from missingness denominators. The next pipeline layer needs explicit
fail-closed tests.

### LOW

#### L-01: Serialized contracts have no schema version or strict unknown-field policy

Deterministic round trips preserve recognized provenance, but unknown JSON
fields are ignored and there is no schema version/migration declaration. This
does not presently inject data into the assessment, but it weakens long-lived
artifact diagnostics.

#### L-02: Evidence and resolution taxonomies remain free-form

`source_kind`, `source_id`, `raw_reference`, `reference`, and
`resolution_method` are non-empty or structurally checked only in part. The
freedom is useful for the minimal contract but permits inconsistent audit
labels and makes policy checks harder.

## Attempted exploit paths

| Attempt | Pre-fix result | Result after this audit |
|---|---|---|
| Directly construct an assessment with a future/current code and no identity state | Succeeded and serialized | Rejected |
| Directly construct an assessment whose identity evidence is one microsecond after cutoff | Succeeded | Rejected |
| Supply inconsistent top-level code/status versus embedded mapping | Succeeded | Rejected |
| Confirm an observation with a direct `MappingState` and no bundle | Succeeded | Rejected |
| Remove serialized provenance `boundary` | Defaulted to point-in-time | Rejected |
| Use a retrospective source as the Top30 observation source | Succeeded when its declared time was old enough | Rejected |
| Put a retrospective resolution in the primary bundle slot | Produced unresolved rather than rejecting malformed structure | Rejected |
| Backdate a retrospective enrichment through the direct observation constructor | Stored, though omitted from payload | Rejected |
| Use an old effective date with evidence available one microsecond after cutoff | Stayed unresolved | Stayed unresolved |
| Use publication before cutoff but availability after cutoff | Stayed unresolved | Stayed unresolved |
| Use an equivalent non-UTC timestamp exactly at cutoff | Accepted | Accepted; normalized to UTC |
| Round-trip a valid assessment, then alter only its duplicated stock code | No assessment deserializer existed | Rejected by revalidation |
| Project a frozen unresolved observation at a later requested cutoff | Stayed unresolved | Stayed unresolved |
| Label a current master point-in-time and falsify/backdate `available_at` | Succeeds | Still succeeds; requires manifest/adapter fix |
| Use a valid but unrelated notice as identity evidence | Succeeds | Still succeeds; requires subject/lifecycle binding |
| Point provenance at bytes that do not match the declared digest | Not checked | Still not checked by this pure contract |

## Tests added

`tests/test_point_in_time_leakage.py` adds 15 adversarial tests covering:

- effective versus availability time;
- publication versus availability time;
- equality, one-microsecond boundaries, timezone equivalence, naive time, and
  date-only time;
- missing serialized boundaries;
- retrospective observation sources and primary resolutions;
- direct confirmed-mapping and direct assessment bypasses;
- duplicated-field tampering and deterministic assessment round trips;
- direct enrichment construction; and
- frozen unresolved behavior at a later projection cutoff.

Existing fixtures and tests were adjusted only where the tightened explicit
boundary and resolution-method requirements made previously implicit metadata
invalid.

## Fixes made

- Made `Provenance.boundary` mandatory and removed the point-in-time default
  during deserialization.
- Required Top30 and assessment sources to be point-in-time.
- Required confirmed observation mappings to originate from a matching
  `HistoricalIdentityBundle`.
- Rejected retrospective primary resolutions and backdated direct
  enrichments.
- Required an explicit non-`unresolved` method for a confirmed mapping.
- Added `AssessmentPayload` invariants for cutoff, source, selected identity,
  status, code, and evidence availability.
- Added deterministic, validating assessment dictionary/JSON round trips.
- Documented these invariants in the canonical Top30 contract.

These are local invariant fixes. They do not acquire data, migrate the legacy
stack, or pretend to solve evidence authenticity.

## Residual risks

The dominant residual risk is truthful metadata: an aware UTC timestamp and a
64-character digest are claims, not proof. The current models cannot establish
historical availability, verify raw bytes, bind an artifact to the asserted
identity, or prevent file replacement. Telegram revision/deletion completeness
and corporate-event applicability remain unresolved. Downstream unresolved-row
handling has not yet been implemented or tested.

These risks prohibit current-master auto-resolution, bulk legacy parser use,
or any full-study claim.

## Unresolved data limitations

- No immutable historical KRX notice/master artifacts with reliable
  availability timestamps exist in the lab for the target history.
- A current KRX master, later reconstructed interval, or old effective date
  does not prove historical knowability.
- Legacy Telegram files do not preserve edit time, deletion evidence,
  acquisition time, completeness, or revision history.
- Telegram post/report/ingestion time semantics and the authoritative source
  timezone have not been frozen in an adapter contract.
- Historical name/code lifecycle evidence for ambiguity, rename, reuse,
  transfer, merger, split, delisting, and relisting has not been assembled.
- No write-once assessment artifact manifest or outcome-join gate exists yet.

## Verdict

**READY_WITH_RESTRICTIONS**

The corrected in-memory and serialization boundary is adequate for the next
small fixture experiment only under all of these restrictions:

1. Use a tiny, versioned local fixture; do not process the three-year corpus.
2. Do not use the legacy Telegram export as point-in-time evidence unless the
   exact message bytes, acquisition time, original/edited state, and timezone
   semantics are established. Synthetic boundary fixtures are acceptable for
   contract testing but not empirical claims.
3. Keep every current master and later reconstructed interval retrospective.
4. Resolve an identity only from byte-verified, cutoff-visible evidence that
   explicitly binds the observed name, canonical code, and applicable event
   timing. Otherwise emit unresolved.
5. Freeze each assessment as a new write-once JSON artifact with its own digest
   before any outcome data is joined. Never overwrite an earlier unresolved
   assessment.
6. Retain unresolved rows in counts and missingness reporting; do not drop,
   guess, or current-map them.

This verdict is not readiness for the full three-year study.

## Recommended next job

`JOB-0007`: build and verify one immutable local fixture manifest, without
network acquisition. The manifest should bind raw path, actual SHA-256, byte
size, source ID, publication time, acquisition/availability time, edit/revision
state, timezone/precision, evidence subject (historical name/code/market), and
effective interval. Produce write-once `AssessmentPayload` JSON plus its digest,
and add failure tests for digest/reference mismatch, backdated current-master
metadata, uncertain Telegram edits, subject mismatch, ambiguous identity, and
attempted assessment overwrite. Do not join outcomes in that job.
