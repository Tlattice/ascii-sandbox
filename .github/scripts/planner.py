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


async def plan(
    issue_number: int,
    issue_body: str,
    file_scan: str,
    model: str,
) -> str:

    context = build_context(
        [
            file_scan,
            load_prompt("planner")
        ]
    )

    agent = make_agent(
        name="planner",
        model=model,
        instructions=context,
        tools=NO_TOOLS,
    )

    plan = await run_agent(
        agent=agent,
        instruction=f"The requested feature/changes by the user:\n{issue_body}\n",
        max_turns=5,
    )

    return plan


async def main():

    model = os.environ["OPENROUTER_MODEL"]

    parser = argparse.ArgumentParser()

    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--issue-title", type=str, required=True)
    parser.add_argument("--issue-body", type=str, required=True)
    parser.add_argument("--file-scan", type=Path, required=True)
    parser.add_argument(
        "--model",
        default="openrouter/free",
    )

    args = parser.parse_args()

    with open(args.file_scan, "r") as file:
        file_scan_content = file.read()

    result = await plan(
        issue_number=args.issue_number,
        issue_body=args.issue_body,
        file_scan=file_scan_content,
        model=args.model,
    )
    sections = [
        Section(f"{IDENTITY}_plan", result, False),
        Section(f"{IDENTITY}_visible", f"### The {IDENTITY} generated a plan.", True),
    ]
    write_output(args.issue_number, f"{IDENTITY}_output.md", sections)


if __name__ == "__main__":
    asyncio.run(main())
