"""Naming rules: N-01, N-02, N-03, N-04 (CONVENTIONS § 11).

N-01: artifact `id` slug is [a-z][a-z0-9]*(-[a-z0-9]+)*, 3–40 chars.
N-02: reserved filenames (NODE.md, thread.md, etc.) must match exact casing.
N-03: reserved directory names (project-brain, threads, archive, ...) must be lowercase.
N-04: debate round directories must be sequential round-01, round-02, ...
"""

from __future__ import annotations

import os
from pathlib import Path

from .model import (
    RESERVED_DIRS,
    RESERVED_FILENAMES,
    ROUND_DIR_RE,
    SLUG_RE,  # legacy ASCII-only, retained for back-compat / extension hooks
    Artifact,
    is_valid_slug,
)


class NamingMixin:
    def check_n01_id_slug(self, a: Artifact) -> None:
        if a.kind not in ("thread", "leaf", "node", "impl-spec"):
            return
        aid = a.frontmatter.get("id")
        if not isinstance(aid, str):
            return  # handled by V-06
        # Unicode-friendly kebab-case: 3-40 chars, no ASCII uppercase, no
        # whitespace, no FS-reserved chars, no leading/trailing/doubled
        # hyphens. Unicode letters/digits in any script are accepted.
        if not is_valid_slug(aid):
            self.add(
                "N-01",
                a,
                f"id {aid!r} must be a valid slug per CONVENTIONS § 11.1: "
                f"3-40 chars, kebab-case, Unicode letters/digits OK, no "
                f"ASCII uppercase, no whitespace, no FS-reserved chars "
                f"(/\\:*?\"<>|), no leading/trailing/doubled hyphens.",
                severity="warning",
            )

    def check_n02_reserved_filenames(self, a: Artifact) -> None:
        name = Path(a.rel_path).name
        low = name.lower()
        for reserved in RESERVED_FILENAMES:
            if low == reserved.lower() and name != reserved:
                self.add(
                    "N-02",
                    a,
                    f"filename {name!r} must match reserved casing {reserved!r}.",
                )

    def check_n03_reserved_dirs(self) -> None:
        # brain IS thoughts/ per CONVENTIONS § 1.
        thoughts = self.brain
        if not thoughts.is_dir():
            return
        for dirpath, dirnames, _ in os.walk(thoughts):
            for d in dirnames:
                if d.lower() in RESERVED_DIRS and d != d.lower():
                    rel = str(Path(dirpath, d).relative_to(self.brain))
                    pseudo = Artifact(
                        path=Path(dirpath) / d,
                        rel_path=rel,
                        kind="unknown",
                    )
                    self.add(
                        "N-03",
                        pseudo,
                        f"reserved directory name {d!r} must be lowercase.",
                    )

    def check_n04_debate_rounds_sequential(self) -> None:
        # brain IS thoughts/ per CONVENTIONS § 1.
        thoughts = self.brain
        if not thoughts.is_dir():
            return
        for dirpath, dirnames, _ in os.walk(thoughts):
            if Path(dirpath).name != "debate":
                continue
            rounds = sorted(d for d in dirnames if d.startswith("round-"))
            for r in rounds:
                if not ROUND_DIR_RE.match(r):
                    pseudo = Artifact(
                        path=Path(dirpath) / r,
                        rel_path=str((Path(dirpath) / r).relative_to(self.brain)),
                        kind="unknown",
                    )
                    self.add(
                        "N-04",
                        pseudo,
                        f"debate round directory {r!r} must match round-NN (zero-padded).",
                    )
            valid = [r for r in rounds if ROUND_DIR_RE.match(r)]
            expected = [f"round-{i:02d}" for i in range(1, len(valid) + 1)]
            if valid and valid != expected:
                pseudo = Artifact(
                    path=Path(dirpath),
                    rel_path=str(Path(dirpath).relative_to(self.brain)),
                    kind="unknown",
                )
                self.add(
                    "N-04",
                    pseudo,
                    f"debate rounds must be sequential from round-01: "
                    f"expected {expected}, got {valid}.",
                )
