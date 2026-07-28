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
    issue_number: int,
    issue_body: str,
    model: str,
) -> str:

    diff = git_diff()

    context = collect_context(issue_number)

    prompt = compose_instruction(
        system_prompt=load_prompt("reviewer"),
        context=context,
        task=f"""
Review the implementation.

GitHub Issue
------------

{issue_body}

Git Diff
--------

{diff}
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
        issue_body,
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
        issue_body=args.issue_body,
        model=args.model,
    )

    with open(args.output, "w") as file:
        file.write(result)


if __name__ == "__main__":
    asyncio.run(main())
