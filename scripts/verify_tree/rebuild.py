"""`--rebuild-index` mode: regenerate thread-index.md and current-state.md.

Contract (SKILL.md § Rebuild):
  * Source of truth = `thoughts/threads/*/thread.md` + `thoughts/archive/*/thread.md`
  * Validate sources first; refuse to write if any source has V-06/V-01/V-07/V-08/V-12 errors.
  * Group by status (active / in-review / parked / archived), sort by
    per-status timestamp (desc), tie-break by slug.
  * Write atomically via `os.replace()` and re-read to verify.
  * `--dry-run` prints a unified diff to stderr instead of writing.
"""

from __future__ import annotations

import difflib
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .checker import Checker
from .discovery import load_artifact
from .frontmatter import parse_frontmatter
from .model import EXIT_INVOCATION, EXIT_OK, EXIT_VIOLATIONS, Artifact


def rebuild_index(brain: Path, dry_run: bool) -> int:
    # Per CONVENTIONS § 1 the brain root IS the thoughts/ directory; this
    # alias preserves the rest of the function's naming but no longer
    # assumes a parent dir. See Finding F5 in sandbox/TEST-REPORT.md.
    thoughts = brain
    if not thoughts.is_dir():
        sys.stderr.write(f"error: brain directory {brain} not found.\n")
        return EXIT_INVOCATION

    # 1. Enumerate and validate source thread files.
    threads: list[Artifact] = []
    for loc in ("threads", "archive"):
        loc_dir = thoughts / loc
        if not loc_dir.is_dir():
            continue
        for slug_dir in sorted(loc_dir.iterdir()):
            tm = slug_dir / "thread.md"
            if tm.is_file():
                threads.append(load_artifact(tm, brain))

    # Also collect tree leaves — the "Leaves building" section in
    # current-state.md derives from them, so a malformed leaf can corrupt
    # the rebuilt snapshot just like a malformed thread corrupts the index.
    # Validate both before touching the aggregate files.
    leaves: list[Artifact] = []
    tree_dir = thoughts / "tree"
    if tree_dir.is_dir():
        for p in tree_dir.rglob("*.md"):
            if p.name == "NODE.md":
                continue
            # Skip debate/impl-spec/etc. sub-files; they're not "leaves".
            parts = p.relative_to(thoughts).parts
            if "debate" in parts:
                continue
            leaves.append(load_artifact(p, brain))

    min_checker = Checker(brain, threads + leaves)
    for a in threads:
        min_checker.check_parse(a)
        min_checker.check_v01_title_matches_h1(a)
        min_checker.check_v06_required_fields(a)
        min_checker.check_v07_thread_status_maturity(a)
        min_checker.check_v08_promoted_parity(a)
        min_checker.check_v12_parked_fields(a)
    for a in leaves:
        min_checker.check_parse(a)
        min_checker.check_v06_required_fields(a)
    errors = [v for v in min_checker.violations if v.severity == "error"]
    if errors:
        sys.stderr.write(
            "refusing to rebuild: source files have validation errors.\n"
        )
        for v in errors:
            sys.stderr.write(f"  {v.file}:{v.line}: [{v.code}] {v.message}\n")
        return EXIT_VIOLATIONS

    # 2. Group by status.
    groups: dict[str, list[Artifact]] = {
        "active": [],
        "in-review": [],
        "parked": [],
        "archived": [],
    }
    for a in threads:
        st = a.frontmatter.get("status")
        if st in groups:
            groups[st].append(a)

    ts_field_by_status = {
        "active": "last_modified_at",
        "in-review": "created_at",
        "parked": "parked_at",
        "archived": "archived_at",
    }
    for key, lst in groups.items():
        lst.sort(key=lambda a: a.frontmatter.get("id") or "")
        lst.sort(
            key=lambda a: (a.frontmatter.get(ts_field_by_status[key]) or ""),
            reverse=True,
        )

    # 3. Primary project metadata from CONVENTIONS.md.
    conv_path = brain / "CONVENTIONS.md"
    primary_project = "project"
    project_title = "Project"
    if conv_path.is_file():
        conv = load_artifact(conv_path, brain)
        pp = conv.frontmatter.get("primary_project")
        if isinstance(pp, str):
            primary_project = pp
        pt = conv.frontmatter.get("project_title") or conv.frontmatter.get("title")
        if isinstance(pt, str):
            project_title = pt

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 4. Render.
    index_md = _render_thread_index(primary_project, project_title, timestamp, groups)
    state_md = _render_current_state(
        primary_project, project_title, timestamp, groups, brain, thoughts
    )

    # 5. Write atomically.
    index_target = thoughts / "thread-index.md"
    state_target = thoughts / "current-state.md"

    if dry_run:
        for target, new_content in ((index_target, index_md), (state_target, state_md)):
            old = target.read_text(encoding="utf-8") if target.is_file() else ""
            diff = list(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{target.relative_to(brain)}",
                    tofile=f"b/{target.relative_to(brain)}",
                )
            )
            if diff:
                sys.stderr.write("".join(diff) + "\n")
            else:
                sys.stderr.write(f"{target.relative_to(brain)}: no changes\n")
        return EXIT_OK

    try:
        _atomic_write(index_target, index_md)
        _atomic_write(state_target, state_md)
    except OSError as exc:
        sys.stderr.write(f"error: failed to write index file: {exc}\n")
        return EXIT_INVOCATION

    # 6. Verify re-read parses.
    try:
        reload_index = index_target.read_text(encoding="utf-8")
        reload_state = state_target.read_text(encoding="utf-8")
        _, _, _, err_i = parse_frontmatter(reload_index)
        _, _, _, err_s = parse_frontmatter(reload_state)
        if err_i:
            sys.stderr.write(f"error: thread-index.md re-read parse error: {err_i}\n")
            return EXIT_INVOCATION
        if err_s:
            sys.stderr.write(f"error: current-state.md re-read parse error: {err_s}\n")
            return EXIT_INVOCATION
    except OSError as exc:
        sys.stderr.write(f"error: re-read failed: {exc}\n")
        return EXIT_INVOCATION

    return EXIT_OK


def _atomic_write(target: Path, content: str) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix="." + target.name + ".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _render_thread_index(
    primary: str,
    title: str,
    timestamp: str,
    groups: dict[str, list[Artifact]],
) -> str:
    lines: list[str] = []
    lines.append("<!--")
    lines.append("AUTO-GENERATED by `verify-tree --rebuild-index`.")
    lines.append(
        "Source of truth: per-thread frontmatter in "
        "`thoughts/threads/*/thread.md` and `thoughts/archive/*/thread.md`."
    )
    lines.append("Hand-edits will be overwritten on the next rebuild.")
    lines.append(f"Last rebuild: {timestamp}")
    lines.append("-->")
    lines.append("")
    lines.append("---")
    lines.append(f"id: {primary}-thread-index")
    lines.append(f"title: {title} — Thread Index")
    lines.append(f"primary_project: {primary}")
    lines.append("kind: index")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title} — Thread Index")
    lines.append("")
    lines.append(
        "Every thread in this project, past and present. Autogenerated — "
        "edit thread frontmatter, then re-run `verify-tree --rebuild-index`."
    )
    lines.append("")
    ts_field = {
        "active": "last_modified_at",
        "in-review": "last_modified_at",
        "parked": "parked_at",
        "archived": "archived_at",
    }
    for heading, key in (
        ("Active", "active"),
        ("In review", "in-review"),
        ("Parked", "parked"),
        ("Archived", "archived"),
    ):
        lines.append(f"## {heading}")
        lines.append("")
        items = groups[key]
        if not items:
            lines.append("_None._")
            lines.append("")
            continue
        lines.append("| Slug | Title | Maturity | Last activity | Owner |")
        lines.append("|------|-------|----------|---------------|-------|")
        for a in items:
            slug = a.frontmatter.get("id", "")
            tt = a.frontmatter.get("title", "")
            mat = a.frontmatter.get("maturity", "—") or "—"
            ts = (
                a.frontmatter.get(ts_field[key])
                or a.frontmatter.get("created_at", "")
            )
            owner = a.frontmatter.get("owner", "")
            lines.append(f"| `{slug}` | {tt} | {mat} | {ts} | {owner} |")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def _render_current_state(
    primary: str,
    title: str,
    timestamp: str,
    groups: dict[str, list[Artifact]],
    brain: Path,
    thoughts: Path,
) -> str:
    lines: list[str] = []
    lines.append("<!--")
    lines.append("AUTO-GENERATED by `verify-tree --rebuild-index`.")
    lines.append(f"Last rebuild: {timestamp}")
    lines.append("-->")
    lines.append("")
    lines.append("---")
    lines.append(f"id: {primary}-current-state")
    lines.append(f"title: {title} — Current State")
    lines.append(f"primary_project: {primary}")
    lines.append("kind: snapshot")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title} — Current State")
    lines.append("")
    lines.append(
        "At-a-glance snapshot. Autogenerated from thread frontmatter; the "
        "source of truth is the thread files themselves."
    )
    lines.append("")
    lines.append("## Active threads")
    lines.append("")
    top_active = groups["active"][:5]
    if not top_active:
        lines.append("_None._")
    else:
        for a in top_active:
            slug = a.frontmatter.get("id", "")
            t = a.frontmatter.get("title", "")
            ts = (
                a.frontmatter.get("last_modified_at")
                or a.frontmatter.get("created_at", "")
            )
            lines.append(f"- **{t}** (`{slug}`) — last touched {ts}")
    lines.append("")
    lines.append("## Threads in review")
    lines.append("")
    if not groups["in-review"]:
        lines.append("_None._")
    else:
        for a in groups["in-review"]:
            slug = a.frontmatter.get("id", "")
            t = a.frontmatter.get("title", "")
            prs = a.frontmatter.get("tree_prs") or []
            pr_str = ", ".join(prs) if prs else "no PR"
            lines.append(f"- **{t}** (`{slug}`) — {pr_str}")
    lines.append("")
    lines.append("## Parked threads")
    lines.append("")
    if not groups["parked"]:
        lines.append("_None._")
    else:
        for a in groups["parked"]:
            slug = a.frontmatter.get("id", "")
            t = a.frontmatter.get("title", "")
            reason = a.frontmatter.get("parked_reason", "") or ""
            trigger = a.frontmatter.get("unpark_trigger", "") or ""
            extra = f" (trigger: {trigger})" if trigger else ""
            lines.append(f"- **{t}** (`{slug}`) — {reason}{extra}")
    lines.append("")
    lines.append("## Leaves building")
    lines.append("")
    building: list[tuple[str, str]] = []
    for leaf in thoughts.glob("tree/**/*.md"):
        if leaf.name == "NODE.md":
            continue
        try:
            fm, _, _, _ = parse_frontmatter(leaf.read_text(encoding="utf-8"))
        except OSError:
            continue
        if fm.get("status") == "building":
            building.append((fm.get("id", ""), fm.get("title", "")))
    if not building:
        lines.append("_None._")
    else:
        for slug, t in sorted(building):
            lines.append(f"- **{t}** (`{slug}`)")
    lines.append("")
    lines.append("## Recent merges")
    lines.append("")
    lines.append("_See git log for authoritative history._")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("_None._")
    return "\n".join(lines).rstrip("\n") + "\n"
