"""MCP prompts — bodies sourced from skills/<slug>/SKILL.md."""

from __future__ import annotations

from .tools import read_skill_body

PROMPT_SKILLS: tuple[str, ...] = ("new-thread", "list-threads", "verify-tree")


def get_prompt_body(slug: str) -> str:
    if slug not in PROMPT_SKILLS:
        raise ValueError(f"prompt '{slug}' not registered (known: {PROMPT_SKILLS})")
    return read_skill_body(slug)
