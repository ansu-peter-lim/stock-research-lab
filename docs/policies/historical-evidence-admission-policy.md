# Historical Evidence Admission Policy

Policy version: `historical-evidence-admission-policy-1`

Decision date: 2026-09-19

Scope: historical Top30 source evidence; this policy does not authorize a bulk
three-year execution.

## Decision

Class B evidence may enter historical assessment and may later participate in
outcome evaluation and a three-year walk-forward study, but only through a
separate, permanently labeled evidence lane. Class B is not cutoff-verified,
must never be represented as Class A, and cannot inherit A's strict
`AssessmentPayload` semantics by inventing an availability timestamp.

For Telegram message `15617`, the decision is:

`PROMOTE_WITH_RESTRICTIONS`

Promotion creates a new policy-admitted descendant bound to the quarantined
JOB-0011 representation. It does not mutate that source artifact, change its
Class B classification, set historical availability to known, or authorize an
outcome join.

## Evidence classes and confidence semantics

The classes are ordinal evidence categories, not calibrated probabilities.
They describe source-content evidence only. Identity, correction, market-data,
freeze, and outcome eligibility have their own independent gates.

- **A — `A_CUTOFF_VERIFIED`:** strong evidence binds source identity, message
  identity, content, and availability at the historical cutoff. A is the
  highest class, not a guarantee that every source statement is true.
- **B — `B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED`:** source/message/time
  are verified and current content strongly agrees with an independently
  preserved artifact, but exact cutoff-visible bytes and revision history are
  not proven. Historical availability remains `unknown`.
- **C — `C_SOURCE_VERIFIED_CONTENT_UNCERTAIN`:** source/message identity is
  verified, but content or edit-state uncertainty is material.
- **D — `D_LOCAL_ONLY_PROVENANCE`:** only a local artifact is available; source
  authenticity was not independently verified.
- **E — `E_CONTRADICTED`:** verified source evidence materially conflicts with
  the local artifact or its metadata.

No aggregate score, default, missing field, filename, neighboring record, or
successful parse may upgrade a class. A later upgrade requires a new,
digest-bound evidence record that names the additional evidence, retains the
prior record as a parent, and produces new descendants. Existing artifacts
keep their original class.

## Admission matrix

“Conditional” means the class passes the source-evidence gate only; all stated
restrictions and independent downstream gates still apply.

| Class | Parsing / inventory | Historical assessment | Outcome evaluation | Full three-year walk-forward |
|---|---|---|---|---|
| A | Yes | Yes, conditional | Yes, conditional | Yes, conditional |
| B | Yes | Yes, restricted Class-B lane | Yes, restricted and separately stratified | Yes, conditional on corpus preflight and separate reporting |
| C | Yes, quarantined only | No | No | No |
| D | Yes, quarantined only | No | No | No |
| E | No research parsing; forensic isolation only | No | No | No |

Parsing C or D establishes structure and quality issues only. It must not
create an assessment-eligible observation. E material may be examined in an
isolated forensic workflow, but it is excluded from research inputs.

## Restrictions on admitted A and B evidence

All admitted evidence must retain immutable source bytes or an immutable
external reference, exact digest and digest kind, source identity, source and
retrieval timestamps, parser version, evidence class, policy version, parent
artifact digests, correction state, identity state, and all known limitations.
Derived artifacts are write-once and content-addressed. Assessment inputs must
be frozen before any outcome data are accessed or joined.

Class A additionally remains subject to the canonical point-in-time contract:
the evidenced `available_at` must be at or before the cutoff. Identity evidence
must independently satisfy its cutoff and lifecycle rules.

Class B has these additional mandatory restrictions:

1. Preserve `evidence_class=B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED`,
   `historical_availability_state=unknown`, and an explicit confidence meaning
   of “strong source/content support; not cutoff-verified.”
2. Never synthesize `available_at` from a message timestamp, report date,
   filename, filesystem timestamp, current retrieval, or parser-time digest.
3. Keep A and B as separate strata in storage, analysis, tables, counts, and
   conclusions. Report combined A+B results only with the mix visible; never
   label them A or “cutoff verified.”
4. Freeze the Class-B assessment input and its exact evidence metadata before
   obtaining outcomes. Later evidence cannot replace that freeze.
5. Run and report a B-excluded sensitivity analysis when enough A data exist.
   If A is absent or inadequate, state that conclusions rely on B and cannot
   establish exact historical byte availability.
6. Retain missing dates, failed repairs, C/D/E records, unresolved identities,
   duplicates, and exclusions in coverage/missingness accounting. They cannot
   disappear from denominators.
7. Do not use a current master, future constituent list, later sector label,
   future price, or outcome to select, repair, rank, resolve, or exclude a
   source observation.

### Full-study preflight for Class B

The matrix permits B in a future full study, but bulk execution remains blocked
until a separate reviewed preflight has:

- predeclared the date range, expected report schedule, cutoff convention,
  sampling frame, duplicate rule, exclusions, hypotheses, horizons, and
  walk-forward splits before outcomes are inspected;
- classified each source artifact independently as A/B/C/D/E through a
  reproducible evidence adapter—message `15617` cannot confer Class B on the
  remaining corpus;
- audited report-date coverage, missing dates, collection gaps, duplicate and
  conflicting messages, deletion/completeness limitations, and class counts;
- established a write-once assessment manifest and an outcome-join gate; and
- predeclared A-only, B-only, A+B, unresolved-identity, and missing-source
  reporting or sensitivity outputs.

These controls address survivorship and selection leakage. They are
prerequisites, not findings established by the single-message fixture.

## Permanent confidence and evidence metadata

Every assessment and descendant result must retain, directly or through
digest-bound immutable parents:

- exact evidence class, confidence semantics, policy version, admission
  decision, admitted stage, and restrictions;
- source/channel identity, message ID, source timestamp and its role, report
  date candidate, edit timestamp plus status, and retrieval timestamp;
- raw/external reference, byte length, digest, and digest kind, distinguishing
  acquisition-time evidence from current or parser-time audit hashes;
- provenance-repair record ID/digest, source-fixture digest, parsed
  representation digest, parser/schema versions, and descendant digest;
- historical-availability state and interpretation, every provenance
  limitation, comparison result and documented transformations;
- recognition/parse issues, rank coverage, duplicate/exclusion state, and
  corpus inclusion or exclusion reason;
- correction count, correction boundary, correction artifact/version and
  reason when present, with raw-content mutation prohibited; and
- source-observed name, identity status, identity-evidence reference and
  cutoff status, plus the reason a stock-specific outcome is missing.

Metadata may be referenced through immutable parent digests to avoid copying,
but it must remain reproducibly resolvable. Flattening or export must not drop
the evidence class, availability limitation, identity state, or restrictions.

## Unresolved stock identity

Unresolved identity is allowed in parsing and historical assessment because
the source-observed name, rank, and source fields are legitimate observations.
It is also retained in the full-study sampling frame and all coverage
denominators.

An unresolved row may not receive a stock code, stock-specific OHLCV, sector,
or +5/+10/+20/+60 outcome. It is excluded only from metrics that mathematically
require identity, with the unresolved count and exclusion reason reported.
It must not be silently dropped, guessed, or resolved from a current master.
A primary outcome link requires separately evidenced historical identity that
passes the point-in-time and corporate-lifecycle gates. A later retrospective
identity may appear only in a labeled sensitivity analysis.

## Correction policy

Raw observations are immutable. A correction evidenced as available by the
historical cutoff may be applied in a separately versioned transformation
before the primary assessment is frozen; the original value, corrected value,
reason, evidence, availability, and transformation digest must all remain.

A correction whose availability is after or unknown at the cutoff is
retrospective. It may not change the primary historical assessment, train or
validation inputs, sampling decision, or primary walk-forward results. It may
be applied only after the primary assessment and primary outcome-evaluation
artifacts are frozen, in a separate, labeled retrospective sensitivity run.
That run must point to the primary result and report differences; it never
overwrites it. A parser bug discovered later requires a new parser version and
new full lineage, not an in-place correction selected because outcomes improve.

## Message 15617 application

The fixture has verified Telegram source and message identity, verified source
timestamp, a canonical content match between the current message and the
independently preserved legacy file, and a matching later processed-manifest
hash. The current API reports no edit timestamp. Against that are the absent
acquisition timestamp/digest, absent revision history, lack of deleted-message
or channel-completeness proof, and the fact that “no edit timestamp currently
reported” does not prove no historical edit.

This combination is sufficiently strong for reproducible historical assessment
under Class B, but not for Class A. Requiring an acquisition-time archival hash
for every historical message would make the practical study impossible while
adding little discrimination where source identity, timestamp, independent
preservation, exact collector serialization, and current canonical content all
agree. The conservative response is therefore restricted admission with
visible uncertainty, stratification, missingness controls, and immutable
lineage—not either perfect-proof exclusion or silent certainty.

The implementation in `src/research_contracts/evidence_admission.py` validates
the JOB-0010 repair digest and the clean JOB-0011 parse, then emits a
deterministic `PolicyAdmittedAssessmentInput`. It carries all B limitations,
keeps all 30 identities unresolved, uses no outcome data, and does not call or
weaken the strict `Top30Observation`/`AssessmentPayload` path. The original
JOB-0011 object remains marked `QUARANTINED / NOT ASSESSMENT ELIGIBLE`; its
promotion is represented by a new restricted descendant rather than mutation.

## Known limitations

- Class B cannot prove the exact bytes visible at the original timestamp.
- Current Telegram retrieval cannot reconstruct revisions or deleted history.
- Independent preservation does not prove when the file was first acquired.
- A one-message decision says nothing about three-year corpus completeness or
  the class distribution of other messages.
- Message `15617` has 30 unresolved identities, so it is not currently eligible
  for stock-specific outcome evaluation.
- No outcome-data provenance, calendar, adjustment, delisting, or horizon-join
  policy is validated by this decision.
- No full-study sampling-frame, coverage, write-once assessment-manifest, or
  outcome-join preflight has yet been completed.

## Required next step

Build and review a small, outcome-free corpus preflight that classifies a
predeclared sample independently, measures report-date coverage and missingness,
and freezes the assessment manifest design. Do not launch the bulk three-year
walk-forward yet.
