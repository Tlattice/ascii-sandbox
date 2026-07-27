# workflows

GitHub Actions workflow definitions.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| [`ci.yml`](ci.yml) | push, pull_request | Run `go test`, race detector, and `go vet` |
| [`plan.yml`](plan.yml) | `ready_to_plan` label | Run the planner agent; post plan as an issue comment |
| [`coder.yml`](coder.yml) | `ready_to_code` label | Run the coder agent; commit, push branch, open PR |
| [`review.yml`](review.yml) | pull_request | Automated review on new PRs |
| [`agent.yml`](agent.yml) | issue opened/assigned, manual | Full pipeline: plan → code → test → review |

Agent workflows require `OPENROUTER_API_KEY` and use `OPENROUTER_MODEL` from repository variables.
