# Historical Research Protocol

Every study must use a point-in-time pipeline with an immutable cutoff.

## Required sequence

1. Define the cutoff timestamp, universe snapshot rule, instruments, features,
   and evaluation horizons before inspecting outcomes.
2. Build the information set using only records published or observable by
   that cutoff. Record source timestamps and data vintage.
3. Analyze market, sector, and stock conditions and freeze the assessment.
   The frozen assessment must be serialized before future prices or later
   classifications are joined.
4. Join only subsequent trading-day outcomes at +5, +10, +20, and +60.
5. Report errors, missingness, survivorship effects, selection effects, and
   any failed checks.
6. Convert observations into explicitly labeled hypotheses.
7. Validate hypotheses on adequate samples with a predeclared split or
   walk-forward design. Do not revise the hypothesis after seeing validation
   outcomes without recording a new version.
8. Promote only replicated, reviewed findings to the knowledge registry.

## Leakage controls

Future prices, future constituents, later sector labels, revised histories,
and post-cutoff commentary are prohibited from the assessment phase. Features
must carry an `as_of` timestamp. Outcome joins must be one-way and occur only
after the frozen assessment artifact exists. Tests should fail if a feature's
availability timestamp is after its cutoff.

## Reproducibility

Each experiment records code version, input identifiers/checksums, cutoff
definition, timezone/calendar, exclusions, parameters, and output artifact
locations. Deterministic calculations belong in code; interpretation belongs
in the experiment report.
