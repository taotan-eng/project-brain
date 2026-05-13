"""MCP server wiring — registers tools, prompts, resources."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import __version__
from .prompts import PROMPT_SKILLS, get_prompt_body
from .resources import RESOURCES, read_resource
from .tools import (
    ListThreadsArgs,
    NewThreadArgs,
    RunSkillArgs,
    VerifyTreeArgs,
    list_threads_impl,
    new_thread_impl,
    run_skill_impl,
    verify_tree_impl,
)

app = FastMCP("project-brain", instructions=f"project-brain MCP server v{__version__}")


@app.tool(
    name="new_thread",
    description="Scaffold a new thread under <brain>/threads/<slug>/ with template files.",
)
async def new_thread(
    brain: str,
    slug: str,
    title: str,
    purpose: str,
    primary_project: str,
    owner: str | None = None,
) -> dict[str, Any]:
    return await new_thread_impl(
        NewThreadArgs(
            brain=brain,
            slug=slug,
            title=title,
            purpose=purpose,
            primary_project=primary_project,
            owner=owner,
        )
    )


@app.tool(
    name="list_threads",
    description="Read-only thread query against per-thread frontmatter.",
)
async def list_threads(
    brain: str,
    status: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    return await list_threads_impl(
        ListThreadsArgs(brain=brain, status=status, domain=domain)
    )


@app.tool(
    name="verify_tree",
    description="Validate the brain (V-01..V-22) or optionally rebuild the aggregate indexes.",
)
async def verify_tree(brain: str, rebuild_index: bool = False) -> dict[str, Any]:
    return await verify_tree_impl(
        VerifyTreeArgs(brain=brain, rebuild_index=rebuild_index)
    )


@app.tool(
    name="run_skill",
    description="Return the body of skills/<name>/SKILL.md (fallback for MCP clients with weak prompt support).",
)
async def run_skill(name: str) -> str:
    return await run_skill_impl(RunSkillArgs(name=name))


def _register_prompts() -> None:
    """Register one MCP prompt per skill in PROMPT_SKILLS."""
    for slug in PROMPT_SKILLS:
        _register_one_prompt(slug)


def _register_one_prompt(slug: str) -> None:
    @app.prompt(name=slug, description=f"Body of skills/{slug}/SKILL.md (frontmatter stripped).")
    async def _prompt() -> str:
        return get_prompt_body(slug)


def _register_resources() -> None:
    for name in RESOURCES:
        _register_one_resource(name)


def _register_one_resource(name: str) -> None:
    uri = f"brain://{name}"

    @app.resource(uri, name=name, description=f"Current content of <brain>/{RESOURCES[name]}")
    async def _resource() -> str:
        return read_resource(name)


_register_prompts()
_register_resources()
