# ChatGPT–Codex Operating Protocol

The owner approves research direction and gates. ChatGPT is research lead:
it frames questions, reviews evidence, identifies ambiguity, and approves
promotion proposals. Codex is implementation agent: it inspects files,
implements scoped changes, runs tests, and reports evidence.

Codex must read canonical repository documents rather than relying on repeated
large prompts. Changes stay inside this repository unless explicitly approved.
Codex does not commit or push unless a later job explicitly authorizes it.

## Reasoning cost policy

- **LOW:** repository/file inspection, deterministic extraction, formatting,
  routine tests, simple migration.
- **MEDIUM:** implementation, debugging, ordinary quantitative analysis,
  backtest development.
- **HIGH:** hypothesis design, ambiguous failure analysis, look-ahead leakage
  investigation, consequential architecture/research decisions.
- **XHIGH:** not the default; only for exceptional problems after research-lead
  escalation.

## Model tier policy

Every job has a `model_tier`; omitted values resolve to the `standard` tier so
legacy job files remain compatible. The installed Codex runtime was verified
on 2026-09-18 and reported these identifiers:

| Project tier | Model | Use |
|---|---|---|
| `economy` | `gpt-5.6-luna` | deterministic inspection, extraction, formatting, repetitive operations, simple migrations, routine tests |
| `standard` (default) | `gpt-5.6-terra` | normal implementation, data processing, debugging, parser work, ordinary quantitative analysis, normal research |
| `advanced` | `gpt-5.6-sol` | important research design, complex debugging, multi-factor analysis, architecture decisions, consequential methodology work |
| `critical` | `gpt-6-astra` | exceptional research gates, major leakage audits, fundamental method changes, difficult cross-domain reasoning, and major strategy architecture decisions |

The orchestrator rejects unknown model tiers. `reasoning_tier` remains an
independent setting and supports only `low`, `medium`, and `high`; it never
automatically selects `xhigh`. Runtime state records the requested model tier,
resolved model identifier, and reasoning tier. If the runtime does not expose
actual model or token information, the monitor displays `N/A`; it does not
estimate ChatGPT Pro quota.

Use deterministic Python for bulk historical calculations. Use model reasoning
primarily for interpretation and hypothesis work. Preserve accepted knowledge
so it is not repeatedly re-derived.
