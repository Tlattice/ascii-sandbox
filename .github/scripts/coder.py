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
import json

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

# Use npcpy's default coding tools.
TOOLS = None


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

    issue_text = issue_body

    context = collect_context()

    prompt = compose_instruction(
        system_prompt=load_prompt("coder"),
        context="",
        task=f"""
Implement the feature exactly as described.

{plan}
""",
    )

    agent = make_agent(
        name="coder",
        model=model,
        instructions=prompt,
        tools=TOOLS,
    )

    report = await run_agent(
        agent=agent,
        instruction="Implement the planned feature.",
        max_turns=3,
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
        changes = json.load(file)["changes"]

    for change in changes:
        filepath = change["filepath"]
        action = change["action"]
        task = change["task"]

        print("Applying change:")
        print(change)

        result = await implement(
            issue_number=args.issue_number,
            issue_title=args.issue_title,
            issue_body=args.issue_body,
            plan=str(change),
            model=args.model,
        )
        parsed_result = json.loads(result)
        commit_message = parsed_result["commit_message"]
        del parsed_result["commit_message"]
        with open(".work/{args.issue_number}/pr_body.txt", "a", encoding="utf-8") as file:
            json.dump(parsed_result["pr_body"], file, indent=4)
        with open(".work/{args.issue_number}/pr_name.txt", "a", encoding="utf-8") as file:
            json.dump(parsed_result["pr_name"], file, indent=4)
        with open(".work/{args.issue_number}/commit_message.txt", "a", encoding="utf-8") as file:
            json.dump(parsed_result["commit_message"], file, indent=4)


if __name__ == "__main__":
    asyncio.run(main())
