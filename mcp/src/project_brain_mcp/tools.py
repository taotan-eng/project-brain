"""MCP tools — thin Pydantic-validated wrappers over Layer-1 scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from ._subprocess import find_pack_root, run_script


class NewThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1, description="Absolute path to the brain root")
    slug: str = Field(min_length=1, description="Kebab-case thread slug, e.g. 'auth-refactor'")
    title: str = Field(min_length=1, description="Human-readable title")
    purpose: str = Field(min_length=1, description="One-line purpose of the thread")
    primary_project: str = Field(min_length=1, description="Alias from <brain>/config.yaml")
    owner: str | None = Field(default=None, description="Owner email")


class ListThreadsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1)
    status: str | None = Field(default=None, description="active | parked | archived | in-review")
    domain: str | None = Field(default=None)


class VerifyTreeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1)
    rebuild_index: bool = Field(default=False)


class RunSkillArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Skill name, e.g. 'new-thread'")


async def new_thread_impl(args: NewThreadArgs) -> dict[str, Any]:
    argv = [
        f"--brain={args.brain}",
        f"--slug={args.slug}",
        f"--title={args.title}",
        f"--purpose={args.purpose}",
        f"--primary-project={args.primary_project}",
    ]
    if args.owner:
        argv.append(f"--owner={args.owner}")
    return run_script("new-thread.sh", argv)


async def list_threads_impl(args: ListThreadsArgs) -> dict[str, Any]:
    argv = [f"--brain={args.brain}"]
    if args.status:
        argv.append(f"--status={args.status}")
    if args.domain:
        argv.append(f"--domain={args.domain}")
    return run_script("list-threads.sh", argv)


async def verify_tree_impl(args: VerifyTreeArgs) -> dict[str, Any]:
    argv = [f"--brain={args.brain}"]
    if args.rebuild_index:
        argv.append("--rebuild-index")
    return run_script("verify-tree.py", argv)


def read_skill_body(slug: str) -> str:
    """Read a SKILL.md body with YAML frontmatter stripped."""
    pack = find_pack_root()
    md_path = pack / "skills" / slug / "SKILL.md"
    if not md_path.is_file():
        raise FileNotFoundError(f"unknown skill: {slug}")
    text = md_path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + 5 :]
    return text.lstrip()


async def run_skill_impl(args: RunSkillArgs) -> str:
    return read_skill_body(args.name)
