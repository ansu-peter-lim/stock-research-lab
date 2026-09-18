# Experiment Policy

Experiments are scoped, reproducible investigations. Each experiment should
have a README or report containing question, preregistered hypothesis,
cutoff/universe definition, allowed information set, features, outcome
horizons, sample split, code/data identifiers, results, error analysis, and
decision.

Assessment artifacts are frozen before outcome artifacts are joined. Exploratory
work must be labeled exploratory and cannot be presented as validation.
Parameters, exclusions, failed runs, and changes in interpretation are part of
the record. Prefer deterministic scripts and small composable modules over
frameworks. No experiment may place credentials or live-execution behavior in
the repository.
