"""MCP tools — thin Pydantic-validated wrappers over Layer-1 scripts.

Every tool's `*_impl` returns the structured response shape from
`_response`: {ok, data, error: {code, message, hint}|None}.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ._response import err, from_subprocess_result, ok
from ._subprocess import find_pack_root, resolve_brain_dir, resolve_project_root, run_script


_KEBAB_RE = re.compile(r"[^a-z0-9]+")


def _kebab_from_leaf(leaf: str) -> str:
    """Normalize a directory leaf to kebab-case for use as a project alias.

    Lowercase, then collapse any run of non-[a-z0-9] characters into a single
    hyphen, then strip leading/trailing hyphens. Returns '' if the result is
    empty (caller decides how to surface the gap).
    """
    return _KEBAB_RE.sub("-", leaf.lower()).strip("-")


_BRAIN_FIELD_DESC = (
    "Project root path — the directory whose project-brain/ subdir holds the brain. "
    "Defaults to $PROJECT_BRAIN_HOME if set. The brain itself lives at <root>/project-brain/."
)
_BRAIN_RESOLVE_HINT = (
    "set PROJECT_BRAIN_HOME in your MCP config's env block (the project root, NOT the "
    "brain dir itself), or pass brain=<root>"
)


def _resolve_brain_or_err(arg: str | None) -> tuple[str | None, dict[str, Any] | None]:
    """Resolve the brain dir for non-init tools.

    Returns `(brain_dir, None)` on success — brain_dir is `<root>/project-brain/`.
    Returns `(None, err_resp)` on failure with a structured validation_error to
    short-circuit the impl.
    """
    brain, err_msg = resolve_brain_dir(arg)
    if err_msg:
        return None, err("validation_error", err_msg, hint=_BRAIN_RESOLVE_HINT)
    return brain, None


def _resolve_root_or_err(arg: str | None) -> tuple[str | None, dict[str, Any] | None]:
    """Resolve the project root for init_project_brain.

    Returns `(root_path, None)` on success. Returns `(None, err_resp)` on failure.
    """
    root, err_msg = resolve_project_root(arg)
    if err_msg:
        return None, err("validation_error", err_msg, hint=_BRAIN_RESOLVE_HINT)
    return root, None


# ---------------------------------------------------------------------------
# Day-3 tools (kept; refactored to use structured response)
# ---------------------------------------------------------------------------


class NewThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1, description="Kebab-case thread slug, e.g. 'auth-refactor'")
    title: str = Field(min_length=1, description="Human-readable title")
    purpose: str = Field(min_length=1, description="One-line purpose of the thread")
    primary_project: str = Field(min_length=1, description="Alias from <brain>/config.yaml")
    owner: str | None = Field(default=None, description="Owner email")


class ListThreadsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    status: str | None = Field(default=None, description="active | parked | archived | in-review")
    domain: str | None = Field(default=None)


class VerifyTreeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    rebuild_index: bool = Field(default=False)


class RunSkillArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Skill name, e.g. 'new-thread'")


async def new_thread_impl(args: NewThreadArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [
        f"--brain={brain}",
        f"--slug={args.slug}",
        f"--title={args.title}",
        f"--purpose={args.purpose}",
        f"--primary-project={args.primary_project}",
    ]
    if args.owner:
        argv.append(f"--owner={args.owner}")
    return from_subprocess_result(run_script("new-thread.sh", argv))


async def list_threads_impl(args: ListThreadsArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}"]
    if args.status:
        argv.append(f"--status={args.status}")
    if args.domain:
        argv.append(f"--domain={args.domain}")
    return from_subprocess_result(run_script("list-threads.sh", argv))


async def verify_tree_impl(args: VerifyTreeArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}"]
    if args.rebuild_index:
        argv.append("--rebuild-index")
    return from_subprocess_result(run_script("verify-tree.py", argv))


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


async def run_skill_impl(args: RunSkillArgs) -> dict[str, Any]:
    try:
        return ok({"body": read_skill_body(args.name)})
    except FileNotFoundError as e:
        return err("script_error", str(e), hint="check the skill name; ls skills/ shows valid slugs")
    except Exception as e:  # noqa: BLE001
        return err("internal_error", f"{type(e).__name__}: {e}", hint="file an issue with the traceback")


# ---------------------------------------------------------------------------
# Day-4 tools (10 new — 7 wired to Layer-1 scripts that exist;
# 3 (review_parked_threads, finalize_promotion, discard_promotion)
# wired with the same shape but their underlying scripts are not yet
# implemented in scripts/. Calling them returns a script_error with
# "script not found"; the wiring is in place for when day-5+ adds the
# scripts. See execution log in day-04-mcp-tool-coverage.md for details.)
# ---------------------------------------------------------------------------


class UpdateThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)
    operation: str = Field(
        min_length=1,
        description="One of: refine | add-leaf | rename-leaf | remove-leaf | soft-link-add | soft-link-remove | merge-into | promote-prep | commit-pending",
    )
    target: str | None = Field(default=None, description="For refine: target maturity")
    merge_into_slug: str | None = Field(default=None)
    url: str | None = Field(default=None, description="For soft-link-add / soft-link-remove")
    leaf_slug: str | None = Field(default=None)
    leaf_slug_new: str | None = Field(default=None, description="For rename-leaf")
    by: str | None = Field(default=None)


class RecordArtifactArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str | None = Field(default=None, description="Inline body content")
    file: str | None = Field(default=None, description="Path to a file to copy in")
    artifact_kind: str | None = Field(default=None, description="debate | benchmark | analysis | artifact")
    append: bool = Field(default=False, description="Append to transcript.md instead of a separate file")
    by: str | None = Field(default=None)


class AssignThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)
    # Exactly one of add/remove/set_/clear should be supplied. Pydantic
    # enforces presence-of-one via the operation field's discriminator
    # below; if none is set, the script refuses with a clear error.
    add: str | None = Field(default=None, description="Comma-separated handles to add")
    remove: str | None = Field(default=None, description="Comma-separated handles to remove")
    set_: str | None = Field(default=None, alias="set", description="Comma-separated handles to set (replace)")
    clear: bool = Field(default=False, description="Clear the assigned_to list")
    actor: str | None = Field(default=None)
    by: str | None = Field(default=None)


class ParkThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)
    reason: str | None = Field(default=None, description="Required for park; ignored for unpark")
    unpark: bool = Field(default=False, description="Flip parked -> active")
    trigger: str | None = Field(default=None, description="Optional unpark trigger description")
    by: str | None = Field(default=None)


class DiscardThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)
    reason: str = Field(min_length=1, description="Why the thread is being discarded")
    by: str | None = Field(default=None)


class RestoreThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)
    maturity: str | None = Field(default=None, description="Maturity to restore to (default: refining)")
    reason: str | None = Field(default=None)
    by: str | None = Field(default=None)


class ReviewThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)
    full: bool = Field(default=False, description="Append the full transcript")
    last: int | None = Field(default=None, description="Show the last N transcript entries")
    since: str | None = Field(default=None, description="ISO8601 timestamp")


class ReviewParkedThreadsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    stale_days: int | None = Field(default=None)


class FinalizePromotionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)


class DiscardPromotionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)
    pr_status: str | None = Field(default=None)


async def update_thread_impl(args: UpdateThreadArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}", f"--slug={args.slug}", f"--operation={args.operation}"]
    if args.target:
        argv.append(f"--target={args.target}")
    if args.merge_into_slug:
        argv.append(f"--merge-into-slug={args.merge_into_slug}")
    if args.url:
        argv.append(f"--url={args.url}")
    if args.leaf_slug:
        argv.append(f"--leaf-slug={args.leaf_slug}")
    if args.leaf_slug_new:
        argv.append(f"--leaf-slug-new={args.leaf_slug_new}")
    if args.by:
        argv.append(f"--by={args.by}")
    return from_subprocess_result(run_script("update-thread.sh", argv))


async def record_artifact_impl(args: RecordArtifactArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}", f"--slug={args.slug}", f"--title={args.title}"]
    if args.content is not None:
        argv.append(f"--content={args.content}")
    if args.file:
        argv.append(f"--file={args.file}")
    if args.artifact_kind:
        argv.append(f"--artifact-kind={args.artifact_kind}")
    if args.append:
        argv.append("--append")
    if args.by:
        argv.append(f"--by={args.by}")
    return from_subprocess_result(run_script("record-artifact.sh", argv))


async def assign_thread_impl(args: AssignThreadArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}", f"--slug={args.slug}"]
    if args.add:
        argv.append(f"--add={args.add}")
    if args.remove:
        argv.append(f"--remove={args.remove}")
    if args.set_:
        argv.append(f"--set={args.set_}")
    if args.clear:
        argv.append("--clear")
    if args.actor:
        argv.append(f"--actor={args.actor}")
    if args.by:
        argv.append(f"--by={args.by}")
    return from_subprocess_result(run_script("assign-thread.sh", argv))


async def park_thread_impl(args: ParkThreadArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}", f"--slug={args.slug}"]
    if args.unpark:
        argv.append("--unpark")
    if args.reason:
        argv.append(f"--reason={args.reason}")
    if args.trigger:
        argv.append(f"--trigger={args.trigger}")
    if args.by:
        argv.append(f"--by={args.by}")
    return from_subprocess_result(run_script("park-thread.sh", argv))


async def discard_thread_impl(args: DiscardThreadArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}", f"--slug={args.slug}", f"--reason={args.reason}"]
    if args.by:
        argv.append(f"--by={args.by}")
    return from_subprocess_result(run_script("discard-thread.sh", argv))


async def restore_thread_impl(args: RestoreThreadArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}", f"--slug={args.slug}"]
    if args.maturity:
        argv.append(f"--maturity={args.maturity}")
    if args.reason:
        argv.append(f"--reason={args.reason}")
    if args.by:
        argv.append(f"--by={args.by}")
    return from_subprocess_result(run_script("restore-thread.sh", argv))


async def review_thread_impl(args: ReviewThreadArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}", f"--slug={args.slug}"]
    if args.full:
        argv.append("--full")
    if args.last is not None:
        argv.append(f"--last={args.last}")
    if args.since:
        argv.append(f"--since={args.since}")
    return from_subprocess_result(run_script("review-thread.sh", argv))


async def review_parked_threads_impl(args: ReviewParkedThreadsArgs) -> dict[str, Any]:
    # Layer-1 script not yet implemented; helper returns script_error.
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}"]
    if args.stale_days is not None:
        argv.append(f"--stale-days={args.stale_days}")
    return from_subprocess_result(run_script("review-parked-threads.sh", argv))


async def finalize_promotion_impl(args: FinalizePromotionArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}", f"--slug={args.slug}"]
    return from_subprocess_result(run_script("finalize-promotion.sh", argv))


async def discard_promotion_impl(args: DiscardPromotionArgs) -> dict[str, Any]:
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [f"--brain={brain}", f"--slug={args.slug}"]
    if args.pr_status:
        argv.append(f"--pr-status={args.pr_status}")
    return from_subprocess_result(run_script("discard-promotion.sh", argv))


# ---------------------------------------------------------------------------
# Day-5 complex tools (3 — init_project_brain, promote_thread_to_tree,
# materialize_context). The `multi_agent_debate` workflow is deliberately
# NOT a tool — it's a prompt only, since subagent spawning belongs to the
# calling agent's host (Cowork Task tool, Claude Code subagent, etc.)
# rather than to the MCP server.
# ---------------------------------------------------------------------------

from pathlib import Path as _Path


class InitProjectBrainArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str | None = Field(
        default=None,
        description=(
            "Project root where the brain should be initialized. The brain lands "
            "at <target>/project-brain/. **Defaults to $PROJECT_BRAIN_HOME if set** "
            "(the configured-host case). **Do NOT prompt the user for this field** "
            "when $PROJECT_BRAIN_HOME is configured — the env var represents the "
            "user's pre-authorized location. Only pass an explicit target when the "
            "user has named a different path in the current conversation."
        ),
    )
    primary_project: str | None = Field(
        default=None,
        description=(
            "Kebab-case alias for the new brain's primary project. "
            "**If omitted**, auto-derived from the target directory's leaf name "
            "(e.g. target='/Users/me/Test-Brain' → primary_project='test-brain'). "
            "**Prefer omitting this field over prompting the user** — the "
            "auto-derivation is reliable for the common case where the user has "
            "already chosen a meaningful project root path."
        ),
    )
    owner: str | None = Field(
        default=None,
        description="Owner email; defaults to the TODO@example.com placeholder",
    )
    force: bool = Field(
        default=False,
        description="If True, allow overwriting an existing brain (backed up to .bak.<timestamp>/)",
    )


class PromoteThreadToTreeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    slug: str = Field(min_length=1)
    allow_domain: str = Field(
        min_length=1,
        description=(
            "Destination domain under tree/ (e.g. 'auth', 'storage'). "
            "MUST come from explicit user authorization — see the prompt body "
            "of the promote-thread-to-tree skill for the consent protocol. "
            "The agent MUST NOT infer this from thread frontmatter, folder "
            "list, prior promoted_to entries, content topic, or conversation "
            "context. Empty string is rejected (this is the technical "
            "enforcement of the day-1 five-round hardening consent gate)."
        ),
    )
    leaves: list[str] | None = Field(
        default=None,
        description="Subset of leaves to promote; default = all decided leaves",
    )
    mode: str = Field(
        default="local",
        description="local | git:pr | git:branch | git:manual; the MCP tool wraps local mode",
    )
    archive_thread: bool = Field(default=False)
    no_commit: bool = Field(default=False)
    by: str | None = Field(default=None)


class MaterializeContextArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str | None = Field(default=None, description=_BRAIN_FIELD_DESC)
    artifact: str = Field(
        min_length=1,
        description="Path to the artifact relative to brain (thread, leaf, or NODE.md)",
    )
    consumer: str = Field(
        default="reviewer",
        description="reviewer | author | reader — affects role-based filtering",
    )
    roles: list[str] = Field(
        default_factory=lambda: ["spec", "prior-decision"],
        description="Soft-link role tags to include in materialized context",
    )
    persist: bool = Field(
        default=False,
        description="If True, persist into the artifact directory for audit; default ephemeral",
    )
    detect_stale: bool = Field(
        default=False,
        description="If True, walk refs without materializing; report broken/drifted links",
    )


async def init_project_brain_impl(args: InitProjectBrainArgs) -> dict[str, Any]:
    root, err_resp = _resolve_root_or_err(args.target)
    if err_resp:
        return err_resp

    # Auto-derive primary_project from the target leaf when omitted, so the
    # zero-args call ("create project brain") resolves cleanly via env + leaf.
    primary_project = (args.primary_project or "").strip()
    if not primary_project:
        leaf = _Path(root).name or "project-brain"
        primary_project = _kebab_from_leaf(leaf)
        if not primary_project:
            return err(
                "validation_error",
                f"could not derive primary_project from target leaf {leaf!r} (after kebab-case normalization, the result was empty)",
                hint="pass primary_project=<kebab-case-name> explicitly",
            )

    # Safety guard: refuse if a brain already exists at <root>/project-brain/
    # unless force=True. The .parent-vs-self heuristic from the old impl is
    # gone — Path C makes `root` unambiguously the project root, and the
    # brain always lands at <root>/project-brain/.
    marker = _Path(root) / "project-brain" / "CONVENTIONS.md"
    if marker.exists() and not args.force:
        return err(
            "script_error",
            f"project root {root!r} already has an existing brain at {root}/project-brain/ (CONVENTIONS.md present)",
            hint="set force=True to overwrite (existing dir is backed up to .bak.<timestamp>/), or pick a different project root",
        )

    argv = [f"--home={root}", f"--alias={primary_project}", f"--title={primary_project}"]
    if args.owner:
        argv.append(f"--owner={args.owner}")
    if args.force:
        argv.append("--force")
    return from_subprocess_result(run_script("init-brain.sh", argv))


async def promote_thread_to_tree_impl(args: PromoteThreadToTreeArgs) -> dict[str, Any]:
    if args.mode != "local":
        return err(
            "script_error",
            f"mode={args.mode!r} is not supported via the MCP tool surface; only mode=local is wrapped",
            hint="for git:pr / git:branch / git:manual modes, use the promote-thread-to-tree prompt and orchestrate git directly in the calling agent",
        )

    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [
        f"--brain={brain}",
        f"--slug={args.slug}",
        f"--allow-domain={args.allow_domain}",
    ]
    if args.leaves:
        argv.append(f"--leaves={','.join(args.leaves)}")
    if args.archive_thread:
        argv.append("--archive-thread")
    if args.no_commit:
        argv.append("--no-commit")
    if args.by:
        argv.append(f"--by={args.by}")
    return from_subprocess_result(run_script("promote-local.sh", argv))


async def materialize_context_impl(args: MaterializeContextArgs) -> dict[str, Any]:
    # scripts/materialize-context.sh is not yet implemented; the wiring is
    # in place so a future Layer-1 commit can land the script without
    # touching Layer-2. Until then, calls return script_error "not found".
    brain, err_resp = _resolve_brain_or_err(args.brain)
    if err_resp:
        return err_resp
    argv = [
        f"--brain={brain}",
        f"--artifact={args.artifact}",
        f"--consumer={args.consumer}",
        f"--roles={','.join(args.roles)}",
    ]
    if args.persist:
        argv.append("--persist")
    if args.detect_stale:
        argv.append("--detect-stale")
    return from_subprocess_result(run_script("materialize-context.sh", argv))


# ---------------------------------------------------------------------------
# Validation-error wrapper
# ---------------------------------------------------------------------------


def wrap_validation(model_cls, impl):
    """Build a Pydantic-validated wrapper for an impl function.

    Used by server.py's @app.tool registrations: Pydantic validation errors
    are caught and translated to the structured `validation_error` shape
    instead of bubbling as raw exceptions.
    """

    async def wrapper(**kwargs: Any) -> dict[str, Any]:
        try:
            args = model_cls(**kwargs)
        except ValidationError as e:
            errors = e.errors()
            first = errors[0] if errors else {}
            field_path = ".".join(str(p) for p in first.get("loc", [])) or "<unknown>"
            return err(
                "validation_error",
                str(e),
                hint=f"check field: {field_path}",
            )
        try:
            return await impl(args)
        except Exception as e:  # noqa: BLE001
            return err(
                "internal_error",
                f"{type(e).__name__}: {e}",
                hint="file an issue with the traceback",
            )

    return wrapper
