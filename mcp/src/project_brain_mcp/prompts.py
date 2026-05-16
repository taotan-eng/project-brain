"""MCP prompts — bodies sourced from skills/<slug>/SKILL.md.

PROMPT_SKILLS is computed at module import time by scanning the pack's
skills/ directory. Adding a new skill in the future requires restarting
the server; no code change here.
"""

from __future__ import annotations

from ._subprocess import find_pack_root
from .tools import read_skill_body


def _discover_skills() -> tuple[str, ...]:
    """Return slugs of every skill that has a SKILL.md."""
    try:
        root = find_pack_root()
    except RuntimeError:
        return ()
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return ()
    return tuple(
        d.name
        for d in sorted(skills_dir.iterdir())
        if d.is_dir() and (d / "SKILL.md").is_file()
    )


PROMPT_SKILLS: tuple[str, ...] = _discover_skills()


def get_prompt_body(slug: str) -> str:
    if slug not in PROMPT_SKILLS:
        raise ValueError(f"prompt '{slug}' not registered (known: {PROMPT_SKILLS})")
    return read_skill_body(slug)
