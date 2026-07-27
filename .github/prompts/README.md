# prompts

System prompts loaded by the agent scripts in [`../scripts/`](../scripts/README.md).

| Prompt | Agent | Key constraint |
|--------|-------|----------------|
| [`planner.md`](planner.md) | Planner | Analyze only; output JSON plan, no code edits |
| [`coder.md`](coder.md) | Coder | Implement the approved plan; add tests, replay, snapshot |
| [`reviewer.md`](reviewer.md) | Reviewer | Read-only review for correctness, simplicity, determinism |
| [`fixer.md`](fixer.md) | Fixer | Address review feedback (when used) |

Prompts are composed with repo context from [`.agent/`](../../.agent/README.md) and [`docs/`](../../docs/README.md).
