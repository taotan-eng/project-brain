"""MCP server wiring — registers tools, prompts, resources.

All tool registrations route through `wrap_validation` so Pydantic errors
become structured `validation_error` responses at the MCP boundary rather
than raw exceptions.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import __version__
from .prompts import PROMPT_SKILLS, get_prompt_body
from .resources import RESOURCES, read_resource
from .tools import (
    AssignThreadArgs,
    DiscardPromotionArgs,
    DiscardThreadArgs,
    FinalizePromotionArgs,
    InitProjectBrainArgs,
    ListThreadsArgs,
    MaterializeContextArgs,
    NewThreadArgs,
    ParkThreadArgs,
    PromoteThreadToTreeArgs,
    RecordArtifactArgs,
    RestoreThreadArgs,
    ReviewParkedThreadsArgs,
    ReviewThreadArgs,
    RunSkillArgs,
    UpdateThreadArgs,
    VerifyTreeArgs,
    assign_thread_impl,
    discard_promotion_impl,
    discard_thread_impl,
    finalize_promotion_impl,
    init_project_brain_impl,
    list_threads_impl,
    materialize_context_impl,
    new_thread_impl,
    park_thread_impl,
    promote_thread_to_tree_impl,
    record_artifact_impl,
    restore_thread_impl,
    review_parked_threads_impl,
    review_thread_impl,
    run_skill_impl,
    update_thread_impl,
    verify_tree_impl,
    wrap_validation,
)

app = FastMCP("project-brain", instructions=f"project-brain MCP server v{__version__}")


# ---------------------------------------------------------------------------
# Day-3 tools (4)
# ---------------------------------------------------------------------------

_new_thread = wrap_validation(NewThreadArgs, new_thread_impl)
_list_threads = wrap_validation(ListThreadsArgs, list_threads_impl)
_verify_tree = wrap_validation(VerifyTreeArgs, verify_tree_impl)
_run_skill = wrap_validation(RunSkillArgs, run_skill_impl)


@app.tool(name="new_thread", description="Scaffold a new thread under <brain>/threads/<slug>/ with template files.")
async def new_thread(
    slug: str,
    title: str,
    purpose: str,
    primary_project: str,
    brain: str | None = None,
    owner: str | None = None,
) -> dict[str, Any]:
    return await _new_thread(
        brain=brain, slug=slug, title=title, purpose=purpose,
        primary_project=primary_project, owner=owner,
    )


@app.tool(name="list_threads", description="Read-only thread query against per-thread frontmatter.")
async def list_threads(
    brain: str | None = None, status: str | None = None, domain: str | None = None,
) -> dict[str, Any]:
    return await _list_threads(brain=brain, status=status, domain=domain)


@app.tool(name="verify_tree", description="Validate the brain (V-01..V-22) or rebuild aggregate indexes.")
async def verify_tree(brain: str | None = None, rebuild_index: bool = False) -> dict[str, Any]:
    return await _verify_tree(brain=brain, rebuild_index=rebuild_index)


@app.tool(name="run_skill", description="Return the body of skills/<name>/SKILL.md (prompt-fidelity fallback).")
async def run_skill(name: str) -> dict[str, Any]:
    return await _run_skill(name=name)


# ---------------------------------------------------------------------------
# Day-4 tools (10)
# ---------------------------------------------------------------------------

_update_thread = wrap_validation(UpdateThreadArgs, update_thread_impl)
_record_artifact = wrap_validation(RecordArtifactArgs, record_artifact_impl)
_assign_thread = wrap_validation(AssignThreadArgs, assign_thread_impl)
_park_thread = wrap_validation(ParkThreadArgs, park_thread_impl)
_discard_thread = wrap_validation(DiscardThreadArgs, discard_thread_impl)
_restore_thread = wrap_validation(RestoreThreadArgs, restore_thread_impl)
_review_thread = wrap_validation(ReviewThreadArgs, review_thread_impl)
_review_parked_threads = wrap_validation(ReviewParkedThreadsArgs, review_parked_threads_impl)
_finalize_promotion = wrap_validation(FinalizePromotionArgs, finalize_promotion_impl)
_discard_promotion = wrap_validation(DiscardPromotionArgs, discard_promotion_impl)


@app.tool(name="update_thread", description="Apply a structured update to an active or parked thread.")
async def update_thread(
    slug: str,
    operation: str,
    brain: str | None = None,
    target: str | None = None,
    merge_into_slug: str | None = None,
    url: str | None = None,
    leaf_slug: str | None = None,
    leaf_slug_new: str | None = None,
    by: str | None = None,
) -> dict[str, Any]:
    return await _update_thread(
        brain=brain, slug=slug, operation=operation, target=target,
        merge_into_slug=merge_into_slug, url=url, leaf_slug=leaf_slug,
        leaf_slug_new=leaf_slug_new, by=by,
    )


@app.tool(name="record_artifact", description="Capture an artifact (markdown, attachment, or transcript append) into a thread.")
async def record_artifact(
    slug: str,
    title: str,
    brain: str | None = None,
    content: str | None = None,
    file: str | None = None,
    artifact_kind: str | None = None,
    append: bool = False,
    by: str | None = None,
) -> dict[str, Any]:
    return await _record_artifact(
        brain=brain, slug=slug, title=title, content=content,
        file=file, artifact_kind=artifact_kind, append=append, by=by,
    )


@app.tool(name="assign_thread", description="Manage the assigned_to list on a thread (add/remove/set/clear).")
async def assign_thread(
    slug: str,
    brain: str | None = None,
    add: str | None = None,
    remove: str | None = None,
    set_: str | None = None,
    clear: bool = False,
    actor: str | None = None,
    by: str | None = None,
) -> dict[str, Any]:
    return await _assign_thread(
        brain=brain, slug=slug, add=add, remove=remove,
        set=set_, clear=clear, actor=actor, by=by,
    )


@app.tool(name="park_thread", description="Park (pause) or unpark a thread.")
async def park_thread(
    slug: str,
    brain: str | None = None,
    reason: str | None = None,
    unpark: bool = False,
    trigger: str | None = None,
    by: str | None = None,
) -> dict[str, Any]:
    return await _park_thread(
        brain=brain, slug=slug, reason=reason, unpark=unpark,
        trigger=trigger, by=by,
    )


@app.tool(name="discard_thread", description="Archive an active or parked thread that was never promoted.")
async def discard_thread(
    slug: str, reason: str, brain: str | None = None, by: str | None = None,
) -> dict[str, Any]:
    return await _discard_thread(brain=brain, slug=slug, reason=reason, by=by)


@app.tool(name="restore_thread", description="Restore a discarded thread from archive/ back to threads/.")
async def restore_thread(
    slug: str,
    brain: str | None = None,
    maturity: str | None = None,
    reason: str | None = None,
    by: str | None = None,
) -> dict[str, Any]:
    return await _restore_thread(
        brain=brain, slug=slug, maturity=maturity, reason=reason, by=by,
    )


@app.tool(name="review_thread", description="Print a read-only summary of a thread (status, leaves, transcript).")
async def review_thread(
    slug: str,
    brain: str | None = None,
    full: bool = False,
    last: int | None = None,
    since: str | None = None,
) -> dict[str, Any]:
    return await _review_thread(
        brain=brain, slug=slug, full=full, last=last, since=since,
    )


@app.tool(name="review_parked_threads", description="Audit parked threads — surface actionable, stale, and hygiene-warning ones.")
async def review_parked_threads(brain: str | None = None, stale_days: int | None = None) -> dict[str, Any]:
    return await _review_parked_threads(brain=brain, stale_days=stale_days)


@app.tool(name="finalize_promotion", description="Close out a merged promote PR — flip leaves to decided, archive thread if last wave.")
async def finalize_promotion(slug: str, brain: str | None = None) -> dict[str, Any]:
    return await _finalize_promotion(brain=brain, slug=slug)


@app.tool(name="discard_promotion", description="Close out a promote PR that was closed without merging.")
async def discard_promotion(
    slug: str, brain: str | None = None, pr_status: str | None = None,
) -> dict[str, Any]:
    return await _discard_promotion(brain=brain, slug=slug, pr_status=pr_status)


# ---------------------------------------------------------------------------
# Day-5 complex tools (3) — multi_agent_debate is deliberately not exposed
# as a tool (subagent spawning belongs to the calling host, not the MCP
# server); its prompt is already auto-registered via PROMPT_SKILLS.
# ---------------------------------------------------------------------------

_init_project_brain = wrap_validation(InitProjectBrainArgs, init_project_brain_impl)
_promote_thread_to_tree = wrap_validation(PromoteThreadToTreeArgs, promote_thread_to_tree_impl)
_materialize_context = wrap_validation(MaterializeContextArgs, materialize_context_impl)


@app.tool(
    name="init_project_brain",
    description=(
        "Create a new project-brain at a target directory. Refuses if a brain "
        "already exists at the target unless force=True (which backs up the "
        "existing brain to project-brain.bak.<timestamp>/)."
    ),
)
async def init_project_brain(
    target: str | None = None,
    primary_project: str | None = None,
    owner: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    return await _init_project_brain(
        target=target, primary_project=primary_project, owner=owner, force=force,
    )


@app.tool(
    name="promote_thread_to_tree",
    description=(
        "Promote thread leaves into tree/<allow_domain>/. allow_domain is a "
        "REQUIRED parameter and MUST come from explicit user authorization; "
        "the agent must NOT infer it from thread frontmatter, folder list, or "
        "conversation context. See the promote-thread-to-tree prompt for the "
        "full consent protocol. v1.0 wraps mode=local; other modes return "
        "script_error with guidance to orchestrate git directly."
    ),
)
async def promote_thread_to_tree(
    slug: str,
    allow_domain: str,
    brain: str | None = None,
    leaves: list[str] | None = None,
    mode: str = "local",
    archive_thread: bool = False,
    no_commit: bool = False,
    by: str | None = None,
) -> dict[str, Any]:
    return await _promote_thread_to_tree(
        brain=brain, slug=slug, allow_domain=allow_domain,
        leaves=leaves, mode=mode, archive_thread=archive_thread,
        no_commit=no_commit, by=by,
    )


@app.tool(
    name="materialize_context",
    description=(
        "Walk the soft_links graph for a thread, leaf, or NODE.md per "
        "CONVENTIONS § 5.1, returning resolved content as structured response "
        "data. Pure read; no state mutation."
    ),
)
async def materialize_context(
    artifact: str,
    brain: str | None = None,
    consumer: str = "reviewer",
    roles: list[str] | None = None,
    persist: bool = False,
    detect_stale: bool = False,
) -> dict[str, Any]:
    if roles is None:
        roles = ["spec", "prior-decision"]
    return await _materialize_context(
        brain=brain, artifact=artifact, consumer=consumer,
        roles=roles, persist=persist, detect_stale=detect_stale,
    )


# ---------------------------------------------------------------------------
# Prompts (auto-discovered) + resources
# ---------------------------------------------------------------------------


def _register_one_prompt(slug: str) -> None:
    @app.prompt(name=slug, description=f"Body of skills/{slug}/SKILL.md (frontmatter stripped).")
    async def _prompt() -> str:
        return get_prompt_body(slug)


def _register_prompts() -> None:
    for slug in PROMPT_SKILLS:
        _register_one_prompt(slug)


def _register_one_resource(name: str) -> None:
    uri = f"brain://{name}"

    @app.resource(uri, name=name, description=f"Current content of <brain>/{RESOURCES[name]}")
    async def _resource() -> str:
        return read_resource(name)


def _register_resources() -> None:
    for name in RESOURCES:
        _register_one_resource(name)


_register_prompts()
_register_resources()
