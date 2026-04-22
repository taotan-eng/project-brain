"""Checker orchestrator — composes invariant mixins and drives validation.

The Checker owns: artifact list, by_rel / by_id indexes, violations list, and
the three cross-artifact resolvers (_find_thread, _find_by_id_or_path,
_resolve_tree_uri). Individual invariants live in the invariants_*.py and
naming.py mixins. check_all() dispatches each artifact through the relevant
methods; per-artifact dispatch matches the original single-file behaviour
exactly, so exit codes and violation orderings are unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .invariants_core import CoreInvariantsMixin
from .invariants_lifecycle import LifecycleInvariantsMixin
from .invariants_nodes import NodesInvariantsMixin
from .invariants_refs import RefsInvariantsMixin
from .model import Artifact, Violation
from .naming import NamingMixin


class Checker(
    CoreInvariantsMixin,
    LifecycleInvariantsMixin,
    RefsInvariantsMixin,
    NodesInvariantsMixin,
    NamingMixin,
):
    def __init__(self, brain: Path, artifacts: list[Artifact]):
        self.brain = brain
        self.artifacts = artifacts
        self.violations: list[Violation] = []
        self.by_rel: dict[str, Artifact] = {a.rel_path: a for a in artifacts}
        self.by_id: dict[str, Artifact] = {}
        for a in artifacts:
            aid = a.frontmatter.get("id")
            if isinstance(aid, str):
                self.by_id.setdefault(aid, a)

    def add(
        self,
        code: str,
        artifact: Artifact,
        message: str,
        line: int = 0,
        severity: str = "error",
    ) -> None:
        aid = artifact.frontmatter.get("id")
        self.violations.append(
            Violation(
                code=code,
                file=artifact.rel_path,
                line=line,
                message=message,
                artifact_id=aid if isinstance(aid, str) else None,
                severity=severity,
            )
        )

    def check_all(self) -> None:
        for a in self.artifacts:
            self.check_parse(a)
            self.check_v01_title_matches_h1(a)
            self.check_v06_required_fields(a)
            self.check_v21_ascii_filename(a)
            self.check_n01_id_slug(a)
            self.check_n02_reserved_filenames(a)
            if a.kind == "thread":
                self.check_v07_thread_status_maturity(a)
                self.check_v08_promoted_parity(a)
                self.check_v12_parked_fields(a)
                self.check_v17_promoted_unique(a)
                self.check_v18_promoted_monotonic(a)
                self.check_v19_debate_rounds(a)
            if a.kind == "leaf":
                self.check_v02_domain_matches_path(a)
                self.check_v09_leaf_state_invariants(a)
                self.check_v11_impl_spec_pair(a)
                self.check_v13_hardening_pre_status(a)
                self.check_v14_source_thread(a)
                self.check_v19_debate_rounds(a)
                self.check_v20_source_debate(a)
            if a.kind == "node":
                self.check_v04_v05_node_leaves(a)
                self.check_v10_node_status(a)
            # soft_links applies to every artifact with a frontmatter
            self.check_v03_soft_links(a)
            self.check_v16_soft_link_self(a)
        # Directory-level checks.
        self.check_n03_reserved_dirs()
        self.check_n04_debate_rounds_sequential()
        # Global graph check.
        self.check_v15_soft_links_dag()

    # ----- cross-artifact helpers (used by invariant mixins) -----

    def _find_thread(self, slug: str) -> Optional[Artifact]:
        # Brain root IS thoughts/ (CONVENTIONS § 1). Primary lookup uses
        # relative paths without a thoughts/ prefix; the thoughts/-prefixed
        # form is retained as a backward-compat fallback for older indexes.
        for loc in ("threads", "archive", "thoughts/threads", "thoughts/archive"):
            p = f"{loc}/{slug}/thread.md"
            a = self.by_rel.get(p)
            if a is not None:
                return a
        # Fallback: lookup by id, but only accept thread artifacts.
        cand = self.by_id.get(slug)
        if cand is not None and cand.kind == "thread":
            return cand
        # Scope-aware fallback: if we're running under --path or similar
        # and the threads/ dir wasn't walked, probe the filesystem directly
        # so V-14 doesn't false-positive just because the referent is
        # outside the current scope. Parse the thread's frontmatter fully
        # (not just {id: slug}) so downstream invariants like V-09
        # 'building' — which requires thread.status == 'active' — don't
        # false-positive on the stub either.
        if hasattr(self, "brain"):
            from .discovery import load_artifact  # local import: avoid cycle
            for loc in ("threads", "archive"):
                fs_path = self.brain / loc / slug / "thread.md"
                if fs_path.is_file():
                    art = load_artifact(fs_path, self.brain)
                    # classify() keys off rel_path so the kind should already
                    # be 'thread' for threads/<slug>/thread.md; coerce
                    # defensively in case of an odd archive layout.
                    if art.kind != "thread":
                        art.kind = "thread"
                    return art
        return None

    def _find_by_id_or_path(self, ref: str) -> Optional[Artifact]:
        if ref in self.by_rel:
            return self.by_rel[ref]
        if ref in self.by_id:
            return self.by_id[ref]
        alt = ref.lstrip("/")
        if alt in self.by_rel:
            return self.by_rel[alt]
        legacy = f"thoughts/{alt}"
        if legacy in self.by_rel:
            return self.by_rel[legacy]
        return None

    def _resolve_tree_uri(self, uri: str) -> Optional[str]:
        """Return rel_path string of the resolved artifact, or None if external/unresolved."""
        if uri.startswith(("http://", "https://", "mcp://", "file://")):
            return None
        if ":" in uri and not uri.startswith("/"):
            return None  # alias — skip in DAG
        rel = uri.lstrip("/")
        for candidate in (rel, f"thoughts/{rel}"):
            if candidate in self.by_rel:
                return candidate
            with_node = candidate.rstrip("/") + "/NODE.md"
            if with_node in self.by_rel:
                return with_node
        return None
