# Data Policy

Data must be attributable, reproducible, and safe for point-in-time research.

## Required metadata

Every imported dataset or adapter documents source, retrieval time, coverage,
timezone, trading calendar, schema, revision policy, and whether timestamps
represent observation time or publication/availability time. Raw inputs are
immutable; transformations create new, identifiable artifacts.

## Security

Never store API keys, brokerage credentials, Telegram credentials, account
information, cookies, or other secrets. Use local environment configuration or
approved secret management, and commit only sanitized examples and schemas.

## Quality and provenance

Record checksums or stable identifiers, missingness, corporate-action policy,
delistings, ticker changes, and known revisions. Do not silently backfill or
overwrite historical data. Any manual correction requires a documented reason
and version.

The data policy does not authorize data acquisition in Bootstrap-001.
