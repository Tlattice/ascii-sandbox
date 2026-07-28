"""
planner.py

Reads a GitHub issue and produces an implementation plan.

Output:
    .work/<issue>/plan.md
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import os

from common import (
    build_context,
    compose_instruction,
    load_prompt,
    make_agent,
    run_agent,
    write_workspace_file,
    Section,
    write_output,
    read_sections
)

# Planner should not edit files.
NO_TOOLS: list = []
IDENTITY = "planner"


# def load_issue(issue_file: str | Path) -> str:
#     return Path(issue_file).read_text(encoding="utf-8")


async def plan(
    issue_number: int,
    issue_body: str,
    file_scan: str,
    model: str,
) -> str:

    context = build_context(
        [
            file_scan
        ]
    )

    prompt = compose_instruction(
        system_prompt=load_prompt("planner"),
        context=context,
        task=f"""
issue body:
{issue_body}
""",
    )

    agent = make_agent(
        name="planner",
        model=model,
        instructions=prompt,
        tools=NO_TOOLS,
    )

    plan = await run_agent(
        agent=agent,
        instruction="Produce the implementation plan.",
        max_turns=5,
    )

    write_workspace_file(
        issue_number,
        "plan.md",
        plan,
    )

    return plan


async def main():

    model = os.environ["OPENROUTER_MODEL"]

    parser = argparse.ArgumentParser()

    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--issue-title", type=str, required=True)
    parser.add_argument("--issue-body", type=str, required=True)
    parser.add_argument("--file-scan", type=str, required=True)
    parser.add_argument(
        "--model",
        default="openrouter/free",
    )

    args = parser.parse_args()

    result = await plan(
        issue_number=args.issue_number,
        issue_body=args.issue_body,
        file_scan=args.file_scan,
        model=args.model,
    )
    sections = [
        Section(f"{IDENTITY}_plan", result, False),
        Section(f"{IDENTITY}_visible", f"### {IDENTITY} generated a plan.", True),
    ]
    write_output(args.issue_number, f"{IDENTITY}_output.md", sections)


if __name__ == "__main__":
    asyncio.run(main())
