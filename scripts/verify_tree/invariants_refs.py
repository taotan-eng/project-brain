"""Reference invariants: V-03, V-14, V-15, V-16, V-17, V-18, V-20, V-22.

V-03: soft_links resolve to existing files (or valid alias targets).
V-14: source_thread points to a real thread.
V-15: soft_links graph is a DAG (no cycles).
V-16: soft_link doesn't point at self.
V-17: promoted_to entries are unique.
V-18: promoted_at timestamps are monotonic.
V-20: source_debate resolves to a round-NN directory.
V-22: artifact's `source_thread` matches its parent thread dir on disk.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

# YAML is loaded via .config, which in turn imports yaml or falls back
# to _yaml_mini. This module no longer needs the direct import.

from .config import (
    any_layer_available,
    global_registry_path,
    per_project_config_path,
    resolve_alias,
)
from .model import ROUND_DIR_RE, Artifact


def _iter_soft_link_uris(links: Any) -> Iterable[str]:
    if not isinstance(links, list):
        return
    for item in links:
        if isinstance(item, dict):
            uri = item.get("uri")
            if isinstance(uri, str) and uri:
                yield uri


class RefsInvariantsMixin:
    def check_v03_soft_links(self, a: Artifact) -> None:
        links = a.frontmatter.get("soft_links") or []
        if not isinstance(links, list):
            return
        for link in links:
            uri = link.get("uri") if isinstance(link, dict) else None
            if not isinstance(uri, str) or not uri:
                continue
            if uri.startswith(("http://", "https://", "mcp://", "file://")):
                continue  # syntactic only — no fetch
            if ":" in uri and not uri.startswith("/"):
                alias, _, sub = uri.partition(":")
                # V-03 two-layer alias resolution (v1.0.0-rc4):
                #   1. per-project <brain>/config.yaml `aliases:` block
                #   2. user-global registry (opt-in, may be absent)
                #
                # No layer present → warning (brain is usable without ~/
                # access; we just can't verify cross-project refs).
                # Some layer present but alias not found → error.
                if not any_layer_available(self.brain):
                    self.add(
                        "V-03",
                        a,
                        f"soft_link alias {alias!r} cannot be validated: no "
                        f"config.yaml next to the brain and no global "
                        f"registry at {global_registry_path()}.",
                        severity="warning",
                    )
                    continue
                entry = resolve_alias(self.brain, alias)
                if entry is None:
                    self.add(
                        "V-03",
                        a,
                        f"soft_link alias {alias!r} not found in "
                        f"{per_project_config_path(self.brain)} or "
                        f"{global_registry_path()}.",
                    )
                    continue
                target_root_raw = entry.get("brain") or entry.get("root")
                if not isinstance(target_root_raw, str):
                    self.add(
                        "V-03",
                        a,
                        f"alias {alias!r} entry is missing a "
                        f"`brain:` or `root:` path.",
                    )
                    continue
                target_root = Path(target_root_raw).expanduser()
                # URI sub-form `thread/<slug>` → brain/threads/<slug>/thread.md
                sub_clean = sub.lstrip("/")
                if sub_clean.startswith("thread/"):
                    slug = sub_clean[len("thread/"):]
                    target = target_root / "threads" / slug / "thread.md"
                else:
                    target = target_root / sub_clean
                if not target.exists():
                    self.add(
                        "V-03",
                        a,
                        f"soft_link {uri!r} resolves to missing path {target}.",
                    )
                continue
            rel = uri.lstrip("/")
            # brain IS thoughts/. Try relative to brain directly; also tolerate
            # legacy writers that prefix a redundant "thoughts/" in the URI.
            candidate = self.brain / rel
            if not candidate.exists():
                if rel.startswith("thoughts/"):
                    candidate2 = self.brain / rel[len("thoughts/"):]
                else:
                    candidate2 = self.brain / "thoughts" / rel
                if not candidate2.exists():
                    self.add(
                        "V-03",
                        a,
                        f"soft_link {uri!r} does not resolve to an existing file.",
                    )

    def check_v14_source_thread(self, a: Artifact) -> None:
        source = a.frontmatter.get("source_thread")
        if not isinstance(source, str) or not source:
            return
        if self._find_thread(source) is None:
            self.add(
                "V-14",
                a,
                f"source_thread={source!r} does not match any thread in threads/ or archive/.",
            )

    def check_v15_soft_links_dag(self) -> None:
        graph: dict[str, list[str]] = {a.rel_path: [] for a in self.artifacts}
        for a in self.artifacts:
            for uri in _iter_soft_link_uris(a.frontmatter.get("soft_links")):
                target = self._resolve_tree_uri(uri)
                if target is not None and target != a.rel_path:
                    graph.setdefault(a.rel_path, []).append(target)
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in graph}

        def record_cycle(path: list[str]) -> None:
            if not path:
                return
            art = self.by_rel.get(path[0])
            if art is None:
                return
            self.add(
                "V-15",
                art,
                f"soft_links form a cycle: {' -> '.join(path + [path[0]])}.",
            )

        for start in graph:
            if color[start] != WHITE:
                continue
            stack: list[tuple[str, Iterable[str]]] = [(start, iter(graph[start]))]
            path = [start]
            color[start] = GRAY
            while stack:
                node, children = stack[-1]
                nxt = next(children, None)
                if nxt is None:
                    color[node] = BLACK
                    stack.pop()
                    if path:
                        path.pop()
                    continue
                if nxt not in graph:
                    continue
                if color[nxt] == GRAY:
                    try:
                        i = path.index(nxt)
                        record_cycle(path[i:])
                    except ValueError:
                        record_cycle([nxt])
                    continue
                if color[nxt] == WHITE:
                    color[nxt] = GRAY
                    path.append(nxt)
                    stack.append((nxt, iter(graph[nxt])))

    def check_v16_soft_link_self(self, a: Artifact) -> None:
        for uri in _iter_soft_link_uris(a.frontmatter.get("soft_links")):
            target = self._resolve_tree_uri(uri)
            if target is not None and target == a.rel_path:
                self.add(
                    "V-16",
                    a,
                    f"soft_link {uri!r} resolves to the artifact itself.",
                )

    def check_v17_promoted_unique(self, a: Artifact) -> None:
        to = a.frontmatter.get("promoted_to") or []
        if not isinstance(to, list):
            return
        seen = set()
        dups = []
        for entry in to:
            if entry in seen:
                dups.append(entry)
            seen.add(entry)
        if dups:
            self.add("V-17", a, f"promoted_to contains duplicates: {dups}.")

    def check_v18_promoted_monotonic(self, a: Artifact) -> None:
        at = a.frontmatter.get("promoted_at") or []
        if not isinstance(at, list):
            return
        prev = None
        for i, ts in enumerate(at):
            if not isinstance(ts, (str, datetime)):
                continue
            key = ts.isoformat() if isinstance(ts, datetime) else ts
            if prev is not None and key < prev:
                self.add(
                    "V-18",
                    a,
                    f"promoted_at non-monotonic: entry {i} ({ts}) precedes previous ({prev}).",
                )
                return
            prev = key

    def check_v20_source_debate(self, a: Artifact) -> None:
        src = a.frontmatter.get("source_debate")
        if not isinstance(src, str) or not src:
            return
        if src.startswith("/") or src.startswith("thoughts/"):
            target = (self.brain / src).resolve()
        else:
            target = (a.path.parent / src).resolve()
        if not target.is_dir() or not ROUND_DIR_RE.match(target.name):
            self.add(
                "V-20",
                a,
                f"source_debate={src!r} does not resolve to a round-NN directory.",
            )

    def check_v22_artifact_source_thread(self, a: Artifact) -> None:
        """Artifact's frontmatter source_thread must match its parent thread dir.

        Artifacts live at ``threads/<slug>/artifacts/<file>.md`` (or the
        archived equivalent). The parent thread's slug is ``parts[1]``.
        ``source_thread`` must equal that slug; otherwise the artifact is
        orphaned from the thread it claims to belong to. We also verify the
        referenced thread exists (V-14 covers similar ground for leaves; V-22
        is the artifact-scoped analogue).
        """
        parts = a.rel_path.split("/")
        if len(parts) < 4 or parts[0] not in ("threads", "archive") \
                or parts[2] != "artifacts":
            # Shouldn't happen given the classifier, but be defensive.
            return
        dir_slug = parts[1]
        fm_slug = a.frontmatter.get("source_thread")
        if not isinstance(fm_slug, str) or not fm_slug:
            # V-06 already flagged the missing field; don't double-report.
            return
        if fm_slug != dir_slug:
            self.add(
                "V-22",
                a,
                f"artifact source_thread={fm_slug!r} does not match parent "
                f"thread dir {dir_slug!r}.",
            )
            return
        if self._find_thread(fm_slug) is None:
            self.add(
                "V-22",
                a,
                f"artifact source_thread={fm_slug!r} does not resolve to "
                f"any thread in threads/ or archive/.",
            )
