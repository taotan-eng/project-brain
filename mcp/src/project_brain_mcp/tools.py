"""MCP tools — thin Pydantic-validated wrappers over Layer-1 scripts.

Every tool's `*_impl` returns the structured response shape from
`_response`: {ok, data, error: {code, message, hint}|None}.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ._response import err, from_subprocess_result, ok
from ._subprocess import find_pack_root, run_script


# ---------------------------------------------------------------------------
# Day-3 tools (kept; refactored to use structured response)
# ---------------------------------------------------------------------------


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
    return from_subprocess_result(run_script("new-thread.sh", argv))


async def list_threads_impl(args: ListThreadsArgs) -> dict[str, Any]:
    argv = [f"--brain={args.brain}"]
    if args.status:
        argv.append(f"--status={args.status}")
    if args.domain:
        argv.append(f"--domain={args.domain}")
    return from_subprocess_result(run_script("list-threads.sh", argv))


async def verify_tree_impl(args: VerifyTreeArgs) -> dict[str, Any]:
    argv = [f"--brain={args.brain}"]
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

    brain: str = Field(min_length=1)
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

    brain: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str | None = Field(default=None, description="Inline body content")
    file: str | None = Field(default=None, description="Path to a file to copy in")
    artifact_kind: str | None = Field(default=None, description="debate | benchmark | analysis | artifact")
    append: bool = Field(default=False, description="Append to transcript.md instead of a separate file")
    by: str | None = Field(default=None)


class AssignThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1)
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

    brain: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    reason: str | None = Field(default=None, description="Required for park; ignored for unpark")
    unpark: bool = Field(default=False, description="Flip parked -> active")
    trigger: str | None = Field(default=None, description="Optional unpark trigger description")
    by: str | None = Field(default=None)


class DiscardThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    reason: str = Field(min_length=1, description="Why the thread is being discarded")
    by: str | None = Field(default=None)


class RestoreThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    maturity: str | None = Field(default=None, description="Maturity to restore to (default: refining)")
    reason: str | None = Field(default=None)
    by: str | None = Field(default=None)


class ReviewThreadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    full: bool = Field(default=False, description="Append the full transcript")
    last: int | None = Field(default=None, description="Show the last N transcript entries")
    since: str | None = Field(default=None, description="ISO8601 timestamp")


class ReviewParkedThreadsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1)
    stale_days: int | None = Field(default=None)


class FinalizePromotionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1)
    slug: str = Field(min_length=1)


class DiscardPromotionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    pr_status: str | None = Field(default=None)


async def update_thread_impl(args: UpdateThreadArgs) -> dict[str, Any]:
    argv = [f"--brain={args.brain}", f"--slug={args.slug}", f"--operation={args.operation}"]
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
    argv = [f"--brain={args.brain}", f"--slug={args.slug}", f"--title={args.title}"]
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
    argv = [f"--brain={args.brain}", f"--slug={args.slug}"]
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
    argv = [f"--brain={args.brain}", f"--slug={args.slug}"]
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
    argv = [f"--brain={args.brain}", f"--slug={args.slug}", f"--reason={args.reason}"]
    if args.by:
        argv.append(f"--by={args.by}")
    return from_subprocess_result(run_script("discard-thread.sh", argv))


async def restore_thread_impl(args: RestoreThreadArgs) -> dict[str, Any]:
    argv = [f"--brain={args.brain}", f"--slug={args.slug}"]
    if args.maturity:
        argv.append(f"--maturity={args.maturity}")
    if args.reason:
        argv.append(f"--reason={args.reason}")
    if args.by:
        argv.append(f"--by={args.by}")
    return from_subprocess_result(run_script("restore-thread.sh", argv))


async def review_thread_impl(args: ReviewThreadArgs) -> dict[str, Any]:
    argv = [f"--brain={args.brain}", f"--slug={args.slug}"]
    if args.full:
        argv.append("--full")
    if args.last is not None:
        argv.append(f"--last={args.last}")
    if args.since:
        argv.append(f"--since={args.since}")
    return from_subprocess_result(run_script("review-thread.sh", argv))


async def review_parked_threads_impl(args: ReviewParkedThreadsArgs) -> dict[str, Any]:
    # Layer-1 script not yet implemented; helper returns script_error.
    argv = [f"--brain={args.brain}"]
    if args.stale_days is not None:
        argv.append(f"--stale-days={args.stale_days}")
    return from_subprocess_result(run_script("review-parked-threads.sh", argv))


async def finalize_promotion_impl(args: FinalizePromotionArgs) -> dict[str, Any]:
    argv = [f"--brain={args.brain}", f"--slug={args.slug}"]
    return from_subprocess_result(run_script("finalize-promotion.sh", argv))


async def discard_promotion_impl(args: DiscardPromotionArgs) -> dict[str, Any]:
    argv = [f"--brain={args.brain}", f"--slug={args.slug}"]
    if args.pr_status:
        argv.append(f"--pr-status={args.pr_status}")
    return from_subprocess_result(run_script("discard-promotion.sh", argv))


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
