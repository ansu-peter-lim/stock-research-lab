Implemented the four-tier model policy.

Verified identifiers and mappings:

- `economy` → `gpt-5.6-luna`
- `standard` → `gpt-5.6-terra` (default)
- `advanced` → `gpt-5.6-sol`
- `critical` → `gpt-6-astra`

Changed:

- [orchestrator/core.py](D:/Project/research/orchestrator/core.py)
- [tests/test_orchestrator.py](D:/Project/research/tests/test_orchestrator.py)
- [docs/chatgpt-codex-operating-protocol.md](D:/Project/research/docs/chatgpt-codex-operating-protocol.md)
- [orchestrator/README.md](D:/Project/research/orchestrator/README.md)

Runtime state now persists model tier, resolved model, and reasoning tier. Unknown tiers are rejected; `xhigh` remains unsupported. Monitor output includes Model Tier, Model, and Reasoning.

Validation:

- Full pytest suite: **21 passed**
- `git diff --check`: **passed**
- No commit or push performed.

Limitation: quota information is not estimated; unavailable runtime/token data remains `N/A`. Pytest emitted one non-failing cache-permission warning.

Recommended next job: review and accept JOB-0004, then create JOB-0005 for the next approved research implementation task.