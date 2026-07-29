from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from dataclasses import dataclass

from openai import AsyncOpenAI
import re

from agents import (
    Agent,
    ModelSettings,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)

# from npcpy.npc_compiler import _DEFAULT_AGENT_TOOLS
from npcpy.npc_compiler import _tool_load_file, _tool_edit_file, _tool_stop
TOOLS = [_tool_load_file, _tool_edit_file, _tool_stop]

set_tracing_disabled(True)

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

DEFAULT_MODEL = os.environ["OPENROUTER_MODEL"]

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

ROOT = Path.cwd()

WORK = ROOT / ".work"

DEFAULT_REASONING = True


# ---------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------


def read_file(path: str | Path) -> str:
    """Return file contents or empty string if missing."""

    path = Path(path)

    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8")


def load_prompt(name: str) -> str:
    """
    Load .github/prompts/<name>.md
    """

    return read_file(ROOT / ".github" / "prompts" / f"{name}.md")


def load_agents_rules() -> str:
    return read_file(ROOT / "AGENTS.md")


def load_architecture() -> str:
    return read_file(ROOT / "docs" / "architecture.md")


# ---------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------


def workspace(issue: int | str) -> Path:
    """
    Return .work/<issue>
    """

    path = WORK / str(issue)
    path.mkdir(parents=True, exist_ok=True)
    return path

@dataclass(frozen=True)
class Section:
    name: str
    content: str
    visible: bool = True

    
def write_output(issue: int, filename: str, sections: list[Section] ) -> Path:
    def wrap_invisible(name: str, content: str):
        return f"<!-- section:{name}:hidden\n{content}\n-->"
    def wrap_visible(name: str, content: str):
        return f"<!-- section:{name} -->\n{content}"

    path = workspace(issue) / filename
    output = []
    for section in sections:
        if section.visible:
            output.append( wrap_visible(section.name, section.content) )
        else:
            output.append( wrap_invisible(section.name, section.content) )
    with open(path, "w", encoding="utf-8") as file:
        file.write( "\n".join(output) )
    return path

def read_sections(text: str) -> dict[str, Section]:
    sections = {}

    pattern = r"<!-- section:(\w+)(?::hidden)? -->\n?(.*?)\n?(?:<!--|$)"

    for match in re.finditer(pattern, text, re.DOTALL):
        name, content = match.groups()
        sections[name] = Section(
            name=name,
            content=content.strip(),
            visible=True,
        )

    return sections

def write_workspace_file(issue: int | str, filename: str, content: str) -> Path:
    path = workspace(issue) / filename
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------


def build_context(files: Iterable[str | Path]) -> str:
    """
    Combine multiple files into one markdown context.
    If str is received, assume it is the content.
    If Path, load the file.
    """
    parts = []

    for file in files:
        if isinstance(file, Path):
            if not file.exists():
                continue
            content = file.read_text(encoding="utf-8")
        else:
            content = file

        parts.append(content)
        parts.append("\n")

    return "\n".join(parts)


# ---------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------


def make_agent(
    *,
    name: str,
    instructions: str,
    model: str = DEFAULT_MODEL,
    tools=None,
    reasoning: bool = DEFAULT_REASONING,
) -> Agent:

    api_key = os.environ["OPENROUTER_API_KEY"]

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=DEFAULT_BASE_URL,
    )

    llm = OpenAIChatCompletionsModel(
        model=model,
        openai_client=client,
    )

    functions = tools if tools is not None else TOOLS

    wrapped = [function_tool(fn) for fn in functions]

    settings = ModelSettings(
        max_tokens=20000,
        extra_body={
            "reasoning": {
                "enabled": False,
            }
        }
        if reasoning
        else None
    )

    return Agent(
        name=name,
        instructions=instructions,
        model=llm,
        tools=wrapped,
        model_settings=settings,
    )


# ---------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------


async def run_agent(
    *,
    agent: Agent,
    instruction: str,
    max_turns: int = 20,
) -> str:
    """
    Execute an agent until completion.
    """

    result = await Runner.run(
        agent,
        instruction,
        max_turns=max_turns,
    )

    return result.final_output or ""


# ---------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------


def compose_instruction(
    *,
    system_prompt: str,
    context: str,
    task: str,
) -> str:
    """
    Build the final instruction sent to the coding model.
    """

    return f"""
# SYSTEM

{system_prompt}

# PROJECT RULES

{load_agents_rules()}

# ARCHITECTURE

{load_architecture()}

# CONTEXT

{context}

# TASK

{task}
""".strip()


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------


def log(issue: int | str, message: str):

    log_file = workspace(issue) / "agent.log"

    with log_file.open("a", encoding="utf-8") as f:
        f.write(message)
        f.write("\n")
