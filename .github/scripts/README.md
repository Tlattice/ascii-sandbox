# scripts

Python agents built on the OpenAI Agents SDK and OpenRouter.

| Script | Role | Modifies repo? |
|--------|------|----------------|
| [`common.py`](common.py) | Agent setup, context loading, workspace helpers | — |
| [`planner.py`](planner.py) | Reads a GitHub issue and writes an implementation plan | No |
| [`coder.py`](coder.py) | Implements the approved plan using coding tools | Yes |
| [`reviewer.py`](reviewer.py) | Reviews the diff and test results after coding | No |

Output artifacts are written under `.work/<issue_number>/` at the repo root.

```bash
python .github/scripts/planner.py --issue 1 --issue-file issue.md
```
