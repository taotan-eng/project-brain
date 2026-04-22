"""Lifecycle invariants: V-07, V-08, V-09, V-11, V-12, V-13.

V-07: thread status ↔ maturity matrix.
V-08: promoted_to / promoted_at list parity.
V-09: per-status leaf lifecycle invariants (in-review / decided / hardening /
      specified / building / built / superseded).
V-11: valid (leaf.status, impl-spec.status) pairs.
V-12: parked threads carry parked_at / parked_by / parked_reason.
V-13: hardening leaves record pre_hardening_status.
"""

from __future__ import annotations

from .model import (
    LEAF_IMPL_SPEC_PAIRS,
    ROUND_DIR_RE,
    THREAD_STATUS_MATURITY,
    VALID_HARDENING_PRE_STATUSES,
    VALID_THREAD_STATUSES,
    Artifact,
)


def _nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    return True


class LifecycleInvariantsMixin:
    def check_v07_thread_status_maturity(self, a: Artifact) -> None:
        status = a.frontmatter.get("status")
        if status not in VALID_THREAD_STATUSES:
            self.add("V-07", a, f"invalid thread status {status!r}.")
            return
        maturity = a.frontmatter.get("maturity")
        allowed = THREAD_STATUS_MATURITY.get(status, set())
        if status == "archived":
            if maturity is not None:
                self.add(
                    "V-07",
                    a,
                    f"archived thread must not set maturity (got {maturity!r}).",
                )
        else:
            if maturity not in allowed:
                self.add(
                    "V-07",
                    a,
                    f"thread status={status} requires maturity in "
                    f"{sorted(x for x in allowed if x)!r}, got {maturity!r}.",
                )

    def check_v08_promoted_parity(self, a: Artifact) -> None:
        to = a.frontmatter.get("promoted_to") or []
        at = a.frontmatter.get("promoted_at") or []
        if not isinstance(to, list) or not isinstance(at, list):
            self.add("V-08", a, "promoted_to and promoted_at must be lists.")
            return
        if len(to) != len(at):
            self.add(
                "V-08",
                a,
                f"promoted_to length ({len(to)}) != promoted_at length ({len(at)}).",
            )

    def check_v09_leaf_state_invariants(self, a: Artifact) -> None:
        status = a.frontmatter.get("status")
        if status == "in-review":
            source = a.frontmatter.get("source_thread")
            if isinstance(source, str) and source:
                thread = self._find_thread(source)
                if thread is not None:
                    prs = thread.frontmatter.get("tree_prs") or []
                    if not prs:
                        self.add(
                            "V-09",
                            a,
                            f"leaf status=in-review but parent thread '{source}' has no tree_prs.",
                        )
        elif status == "decided":
            parts = a.rel_path.split("/")
            # Rel paths are relative to brain (= thoughts/). Either the leaf
            # is directly under tree-staging/, or it's in a thread's scoped
            # staging: threads/<slug>/tree-staging/<domain>/<leaf>.md.
            in_staging = (
                (len(parts) >= 1 and parts[0] == "tree-staging")
                or (
                    len(parts) >= 3
                    and parts[0] == "threads"
                    and parts[2] == "tree-staging"
                )
            )
            if in_staging:
                self.add(
                    "V-09",
                    a,
                    "leaf status=decided but lives under tree-staging/ (should be under tree/).",
                )
        elif status == "hardening":
            # Three supported layouts for per-leaf debate rounds:
            #   (1) <parent>/<stem>.debate/round-NN/        (stem-suffixed)
            #   (2) <parent>/debate/round-NN/               (flat, single-leaf dir)
            #   (3) <parent>/debate/<stem>/round-NN/        (slug-namespaced, avoids
            #                                                collision when multiple
            #                                                leaves share a parent dir
            #                                                such as a NODE.md group)
            debate_dir = a.path.parent / (a.path.stem + ".debate")
            alt = a.path.parent / "debate"
            alt_slug = a.path.parent / "debate" / a.path.stem
            dd = (
                debate_dir if debate_dir.is_dir()
                else alt_slug if alt_slug.is_dir()
                else alt if alt.is_dir()
                else None
            )
            if dd is None:
                self.add(
                    "V-09",
                    a,
                    "leaf status=hardening but no debate/ subdirectory found.",
                )
            else:
                rounds = sorted(
                    [
                        p for p in dd.iterdir()
                        if p.is_dir() and ROUND_DIR_RE.match(p.name)
                    ],
                    key=lambda p: p.name,
                )
                if not rounds or not (rounds[-1] / "feedback-in.md").is_file():
                    self.add(
                        "V-09",
                        a,
                        "leaf status=hardening requires debate/round-NN/feedback-in.md for highest N.",
                    )
        elif status == "specified":
            spec_ref = a.frontmatter.get("impl_spec")
            if not isinstance(spec_ref, str) or not spec_ref:
                self.add("V-09", a, "leaf status=specified requires impl_spec.")
            else:
                spec = self._find_by_id_or_path(spec_ref)
                if spec is None:
                    self.add(
                        "V-09",
                        a,
                        f"leaf status=specified but impl_spec {spec_ref!r} does not resolve.",
                    )
                elif spec.frontmatter.get("status") != "ready":
                    self.add(
                        "V-09",
                        a,
                        f"leaf status=specified requires impl_spec.status=ready "
                        f"(got {spec.frontmatter.get('status')!r}).",
                    )
        elif status == "building":
            it = a.frontmatter.get("impl_thread")
            if not isinstance(it, str) or not it:
                self.add("V-09", a, "leaf status=building requires impl_thread.")
            else:
                thread = self._find_thread(it)
                if thread is None or thread.frontmatter.get("status") != "active":
                    self.add(
                        "V-09",
                        a,
                        f"leaf status=building but impl_thread {it!r} not active.",
                    )
        elif status == "built":
            built = a.frontmatter.get("built_in")
            if not isinstance(built, str) or not built:
                self.add("V-09", a, "leaf status=built requires built_in.")
        elif status == "superseded":
            sup = a.frontmatter.get("superseded_by")
            if not isinstance(sup, str) or not sup:
                self.add("V-09", a, "leaf status=superseded requires superseded_by.")
            else:
                target = self._find_by_id_or_path(sup)
                if target is None:
                    self.add(
                        "V-09",
                        a,
                        f"leaf status=superseded but superseded_by {sup!r} does not resolve.",
                    )
                else:
                    mine = a.frontmatter.get("created_at")
                    theirs = target.frontmatter.get("created_at")
                    if (
                        isinstance(mine, str)
                        and isinstance(theirs, str)
                        and theirs < mine
                    ):
                        self.add(
                            "V-09",
                            a,
                            f"superseded_by target {sup!r} has earlier created_at than this leaf.",
                        )

    def check_v11_impl_spec_pair(self, a: Artifact) -> None:
        spec_ref = a.frontmatter.get("impl_spec")
        if not isinstance(spec_ref, str) or not spec_ref:
            return
        spec = self._find_by_id_or_path(spec_ref)
        if spec is None:
            return  # V-09 handles missing
        leaf_status = a.frontmatter.get("status")
        spec_status = spec.frontmatter.get("status")
        pair = (leaf_status, spec_status)
        if leaf_status in {"draft", "in-review", "decided"}:
            return
        if pair not in LEAF_IMPL_SPEC_PAIRS:
            self.add(
                "V-11",
                a,
                f"invalid leaf/impl-spec status pair: "
                f"leaf={leaf_status!r}, spec={spec_status!r}.",
            )

    def check_v12_parked_fields(self, a: Artifact) -> None:
        status = a.frontmatter.get("status")
        fields = ("parked_at", "parked_by", "parked_reason")
        if status == "parked":
            missing = [f for f in fields if not _nonempty(a.frontmatter.get(f))]
            if missing:
                self.add(
                    "V-12",
                    a,
                    f"status=parked but missing required field(s): {missing}.",
                )
        else:
            present = [
                f for f in fields
                if f in a.frontmatter and a.frontmatter.get(f) not in (None, "")
            ]
            if present:
                self.add(
                    "V-12",
                    a,
                    f"status={status} must not set park metadata field(s): {present}.",
                )

    def check_v13_hardening_pre_status(self, a: Artifact) -> None:
        status = a.frontmatter.get("status")
        pre = a.frontmatter.get("pre_hardening_status")
        if status == "hardening":
            if pre not in VALID_HARDENING_PRE_STATUSES:
                self.add(
                    "V-13",
                    a,
                    f"status=hardening requires pre_hardening_status in "
                    f"{sorted(VALID_HARDENING_PRE_STATUSES)} (got {pre!r}).",
                )
        else:
            if pre is not None:
                self.add(
                    "V-13",
                    a,
                    f"pre_hardening_status={pre!r} present but status={status!r} is not hardening.",
                )
