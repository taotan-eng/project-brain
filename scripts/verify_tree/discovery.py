"""Brain-root discovery, artifact classification, and walking.

This is the "filesystem layer". Checkers depend on Artifact objects produced
here; they never read the disk directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

from .frontmatter import find_first_h1, parse_frontmatter
from .model import Artifact


def find_brain_root(start: Path) -> Optional[Path]:
    """Return the nearest ancestor containing a CONVENTIONS.md.

    The brain root is the directory that holds CONVENTIONS.md and a thoughts/
    directory. If the start path is inside a thoughts/ tree, walk up.
    """
    p = start.resolve()
    for candidate in [p] + list(p.parents):
        conv = candidate / "CONVENTIONS.md"
        if conv.is_file():
            return candidate
    return None


def classify(rel_path: str, frontmatter: dict) -> str:
    """Classify a file by its path + frontmatter kind.

    ``rel_path`` is relative to the brain root — which IS the ``thoughts/``
    directory (per CONVENTIONS § 1 and ``init-project-brain``). So
    ``parts[0]`` is ``tree``, ``threads``, ``archive``, ``tree-staging``,
    etc., or a top-level file like ``CONVENTIONS.md``.

    Returns one of:
      thread | leaf | node | impl-spec | index | snapshot | conventions |
      debate-index | debate-synthesized | debate-round-raw | debate-feedback |
      thread-helper | unknown.
    """
    parts = rel_path.split("/")
    name = parts[-1]

    # Top-level reserved files.
    if name == "CONVENTIONS.md":
        return "conventions"
    if name == "thread-index.md":
        return "index"
    if name == "current-state.md":
        return "snapshot"

    # Per F9: debate/ subtrees have a distinct kind vocabulary.
    # Synthesized outputs (index.md above round-NN/, proposed-patches.md +
    # open-issues.md inside round-NN/) carry minimal frontmatter so the
    # classifier can dispatch; everything else under debate/ is raw evidence
    # (transcript, tryouts, defender, feedback-in) and is exempt from V-06.
    if "debate" in parts:
        in_round = any(p.startswith("round-") for p in parts)
        if in_round:
            if name in ("proposed-patches.md", "open-issues.md"):
                return "debate-synthesized"
            if name in ("feedback-in.md", "feedback-out.md"):
                return "debate-feedback"
            if name.endswith(".md"):
                return "debate-round-raw"
        else:
            if name == "index.md":
                return "debate-index"
            if name in ("feedback-in.md", "feedback-out.md"):
                return "debate-feedback"
            # e.g. personas.yaml / open notes at the debate/ level
            return "unknown"

    # Non-debate reserved filenames.
    if name == "NODE.md":
        return "node"
    if name == "thread.md":
        return "thread"
    if frontmatter.get("kind") == "impl-spec":
        return "impl-spec"

    if parts:
        sub = parts[0]
        if sub == "tree" and name.endswith(".md"):
            return "leaf"
        if sub == "tree-staging" and name.endswith(".md"):
            return "leaf"
        # thread-scoped staging: threads/<slug>/tree-staging/<domain>/<leaf>.md
        if (
            sub == "threads"
            and len(parts) >= 3
            and parts[2] == "tree-staging"
            and name.endswith(".md")
        ):
            return "leaf"
        if sub == "archive":
            if name == "thread.md":
                return "thread"
            return "unknown"

    if name in ("decisions-candidates.md", "open-questions.md"):
        return "thread-helper"
    return "unknown"


def iter_scoped_paths(
    brain: Path,
    thread: Optional[str],
    path: Optional[str],
    staging: Optional[str],
) -> Iterable[Path]:
    """Yield absolute paths of markdown files that fall within the scope.

    The brain root IS the ``thoughts/`` directory (per CONVENTIONS § 1), so
    sub-walks start directly under ``brain``. See Finding F6 in
    sandbox/TEST-REPORT.md.
    """
    if not brain.is_dir():
        return
    roots: list[Path] = []
    if staging:
        roots.append(brain / "threads" / staging / "tree-staging")
    elif thread:
        for loc in ("threads", "archive"):
            p = brain / loc / thread
            if p.is_dir():
                roots.append(p)
    elif path:
        roots.append(brain / path)
    else:
        roots = [brain]
        conv = brain / "CONVENTIONS.md"
        if conv.is_file():
            yield conv
    for root in roots:
        if root.is_file() and root.suffix == ".md":
            yield root
            continue
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in filenames:
                if fn.endswith(".md"):
                    yield Path(dirpath) / fn


def load_artifact(abs_path: Path, brain: Path) -> Artifact:
    """Read one markdown file and return a parsed Artifact."""
    try:
        text = abs_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Artifact(
            path=abs_path,
            rel_path=str(abs_path.relative_to(brain)),
            kind="unknown",
            parse_error=f"non-utf8 encoding: {exc}",
        )
    fm, body, body_start, err = parse_frontmatter(text)
    title, title_line = find_first_h1(body, body_start)
    rel = str(abs_path.relative_to(brain))
    kind = classify(rel, fm)
    return Artifact(
        path=abs_path,
        rel_path=rel,
        kind=kind,
        frontmatter=fm,
        body=body,
        title_line=title_line,
        first_h1=title,
        parse_error=err,
    )
