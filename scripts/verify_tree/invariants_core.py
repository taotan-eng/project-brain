"""Core invariants: V-01, V-02, V-06, V-10, V-21 + parse check.

V-01: frontmatter title matches first H1.
V-02: leaf domain matches tree path.
V-06: required frontmatter fields per kind.
V-10: NODE.md has status=decided.
V-21: path components are ASCII-safe.
"""

from __future__ import annotations

from .model import (
    ASCII_NAME_RE,  # legacy, retained for back-compat
    KINDS_WITHOUT_FRONTMATTER,
    REQUIRED_BY_KIND,
    RESERVED_DIRS,
    RESERVED_FILENAMES,
    Artifact,
    is_valid_path_component,
)


class CoreInvariantsMixin:
    def check_parse(self, a: Artifact) -> None:
        # Kinds in KINDS_WITHOUT_FRONTMATTER are evidence/scratchpads; no
        # frontmatter is expected and a missing '---' delimiter is not V-06.
        if a.kind in KINDS_WITHOUT_FRONTMATTER:
            return
        if a.parse_error:
            self.add("V-06", a, f"frontmatter parse error: {a.parse_error}")

    def check_v01_title_matches_h1(self, a: Artifact) -> None:
        # Raw kinds and the synthesized debate outputs (which carry only
        # id/kind/created_at — no title) are exempt from title/H1 parity.
        if a.kind in KINDS_WITHOUT_FRONTMATTER or a.kind in (
            "debate-index",
            "debate-synthesized",
        ):
            return
        title = a.frontmatter.get("title")
        if not isinstance(title, str) or not title.strip():
            return  # handled by V-06
        h1 = a.first_h1
        if h1 is None:
            self.add(
                "V-01",
                a,
                "missing H1 heading in body (expected to match frontmatter title).",
            )
            return
        if h1.strip() != title.strip():
            self.add(
                "V-01",
                a,
                f"frontmatter title {title!r} does not match first H1 {h1!r}.",
                line=a.title_line,
            )

    def check_v02_domain_matches_path(self, a: Artifact) -> None:
        # Paths are relative to brain (= thoughts/). For a leaf at
        # thoughts/tree/<domain>/<leaf>.md the rel_path is tree/<domain>/<leaf>.md
        # → parts[0]=tree, parts[1]=<domain>, parts[-1]=<leaf>.md.
        parts = a.rel_path.split("/")
        if len(parts) < 2:
            return
        if parts[0] not in ("tree", "tree-staging"):
            return
        if parts[0] == "tree-staging":
            return  # staging leaves get a pass on V-02 until promoted
        expected = "/".join(parts[1:-1]) if len(parts) > 2 else ""
        got = a.frontmatter.get("domain")
        if isinstance(got, str) and got != expected:
            self.add(
                "V-02",
                a,
                f"domain {got!r} does not match tree path {expected!r}.",
            )

    def check_v06_required_fields(self, a: Artifact) -> None:
        required = REQUIRED_BY_KIND.get(a.kind)
        if not required:
            return
        for f in required:
            val = a.frontmatter.get(f)
            if val is None or (isinstance(val, str) and not val.strip()):
                self.add(
                    "V-06",
                    a,
                    f"required frontmatter field {f!r} is missing or empty.",
                )

    def check_v10_node_status(self, a: Artifact) -> None:
        status = a.frontmatter.get("status")
        if status != "decided":
            self.add(
                "V-10",
                a,
                f"NODE.md must have status=decided (got {status!r}).",
            )

    def check_v21_ascii_filename(self, a: Artifact) -> None:
        parts = a.rel_path.split("/")
        for p in parts:
            if p in RESERVED_FILENAMES or p in RESERVED_DIRS:
                continue
            # V-21 used to require ASCII-only path components. Relaxed to
            # allow Unicode (Chinese, Cyrillic, accented Latin, etc.) — only
            # filesystem-unsafe chars are rejected: whitespace, FS-reserved
            # (/\:*?"<>|), control chars. Modern filesystems handle Unicode
            # dirnames fine; the ASCII-only rule was conservative
            # defensiveness. (See is_valid_path_component in model.py.)
            if not is_valid_path_component(p):
                self.add(
                    "V-21",
                    a,
                    f"path component {p!r} contains unsafe characters "
                    f"(whitespace, FS-reserved /\\:*?\"<>|, or control chars).",
                )
                break
