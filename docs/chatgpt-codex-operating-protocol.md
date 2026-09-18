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

Use deterministic Python for bulk historical calculations. Use model reasoning
primarily for interpretation and hypothesis work. Preserve accepted knowledge
so it is not repeatedly re-derived.
