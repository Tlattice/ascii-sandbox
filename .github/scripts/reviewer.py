"""
reviewer.py

Reviews an implementation after the coding agent has finished.

Output:
    .work/<issue>/review.md
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
from pathlib import Path
import os

from common import (
    build_context,
    compose_instruction,
    load_prompt,
    make_agent,
    read_file,
    run_agent,
    workspace,
    write_workspace_file,
)

# Reviewer should not modify the repository.
NO_TOOLS: list = []


def git_diff() -> str:
    """
    Return the staged + unstaged diff.
    """
    try:
        return subprocess.check_output(
            ["git", "diff", "--stat", "--patch"],
            text=True,
        )
    except Exception as exc:
        return f"Unable to read git diff.\n{exc}"


def collect_context(issue: int) -> str:
    files = [
        "README.md",
        "AGENTS.md",
        "docs/architecture.md",
        "docs/coding-rules.md",
        workspace(issue) / "plan.md",
        workspace(issue) / "implementation.md",
    ]

    return build_context(files)


async def review(
    issue: int,
    issue_file: str,
    model: str,
) -> str:

    issue_text = read_file(issue_file)
    plan = read_file(workspace(issue) / "plan.md")
    implementation = read_file(workspace(issue) / "implementation.md")
    diff = git_diff()

    context = collect_context(issue)

    prompt = compose_instruction(
        system_prompt=load_prompt("reviewer"),
        context=context,
        task=f"""
Review the implementation.

GitHub Issue
------------

{issue_text}

Implementation Plan
-------------------

{plan}

Implementation Summary
----------------------

{implementation}

Git Diff
--------

{diff}

Review against:

- Issue requirements
- Implementation plan
- Architecture
- AGENTS.md
- Coding rules

Output exactly these sections.

# Verdict

PASS or FAIL

# Findings

Bullet list.

# Missing Requirements

Bullet list.

# Suggested Fixes

Bullet list.

# Architecture Review

Bullet list.

# Test Review

Bullet list.

# Final Summary
""",
    )

    agent = make_agent(
        name="reviewer",
        model=model,
        instructions=prompt,
        tools=NO_TOOLS,
    )

    report = await run_agent(
        agent=agent,
        instruction="Review the implementation.",
        max_turns=8,
    )

    write_workspace_file(
        issue,
        "review.md",
        report,
    )

    return report


async def main():

    model = os.environ["OPENROUTER_MODEL"]
    parser = argparse.ArgumentParser()

    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--issue-body", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument(
        "--model",
        default=model,
    )

    args = parser.parse_args()

    result = await review(
        issue_number=args.issue_number,
        issue_file=args.issue_body,
        model=args.model,
    )

    with open(args.output, "w") as file:
        file.write(result)


if __name__ == "__main__":
    asyncio.run(main())
