"""Provider-neutral tool definitions, converted for Claude or OpenAI-compatible models (Gemma)."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema for the tool's arguments
    run: Callable[[dict], str]


def to_anthropic(tool):
    return {"name": tool.name, "description": tool.description, "input_schema": tool.parameters}


def to_openai(tool):
    return {"type": "function",
            "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters}}
