"""
coder.py

Reads the planner output and implements the requested feature.

Output:
    Repository changes
    .work/<issue>/implementation.md
"""

from __future__ import annotations

import os
import argparse
import asyncio
from pathlib import Path

from common import (
    build_context,
    compose_instruction,
    load_prompt,
    make_agent,
    read_file,
    run_agent,
    workspace,
    write_workspace_file,
    Section,
    write_output,
    read_sections
)

# Use npcpy's default coding tools.
TOOLS = None
IDENTITY = "coder"


def collect_context() -> str:
    """
    Build a context from core project files plus the planner output.
    """

    files = [
    ]

    return build_context(files)

async def implement(
    issue_number: int,
    issue_body: str,
    issue_title: str,
    plan: str,
    model: str,
) -> str:

    context = build_context(
        [
            
            load_prompt("coder"),
            plan
        ]
    )

    agent = make_agent(
        name="coder",
        model=model,
        instructions=context,
        tools=TOOLS,
    )

    report = await run_agent(
        agent=agent,
        instruction=f"Follow the instructions given to implement the changes.",
        max_turns=200,
    )

    return report


async def main():

    model = os.environ["OPENROUTER_MODEL"]

    parser = argparse.ArgumentParser()

    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--issue-title", type=str, required=True)
    parser.add_argument("--issue-body", type=str, required=True)
    parser.add_argument("--planner-output", type=str, required=True)
    parser.add_argument(
        "--model",
        default=model,
    )

    args = parser.parse_args()

    print("Parsing list of changes:")
    with open(args.planner_output, "r") as file:
        planner_output = file.read()
    planner_sections = read_sections(planner_output)
    print("---")
    print(planner_output)
    print("---")
    print(planner_sections)

    print("Applying change:")
    print(planner_sections["planner_plan"])

    result = await implement(
        issue_number=args.issue_number,
        issue_title=args.issue_title,
        issue_body=args.issue_body,
        plan=planner_sections["planner_plan"],
        model=args.model,
    )

    print("done")
    print(result)
    # parsed_result = pyyaml.safe_load(result)

    sections = [
        Section(f"{IDENTITY}_plan", result, False),
        Section(f"{IDENTITY}_visible", f"### The {IDENTITY} proposed some changes.", True),
    ]
    write_output(args.issue_number, f"{IDENTITY}_output.md", sections)


if __name__ == "__main__":
    asyncio.run(main())
