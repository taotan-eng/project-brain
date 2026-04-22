"""Node & debate invariants: V-04, V-05, V-19.

V-04: every .md file in a NODE.md's directory appears in ## Leaves.
V-05: every link in ## Leaves points at an existing file.
V-19: debate rounds are sequential (round-01, round-02, ... no gaps).
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import Artifact


def _parse_leaves_section(body: str) -> list[str]:
    """Extract markdown-link targets under the '## Leaves' section."""
    lines = body.split("\n")
    in_section = False
    targets: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("## leaves"):
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section:
            for m in re.finditer(r"\]\(([^)]+)\)", line):
                targets.append(m.group(1))
    return targets


class NodesInvariantsMixin:
    def check_v04_v05_node_leaves(self, a: Artifact) -> None:
        node_dir = a.path.parent
        listed = _parse_leaves_section(a.body)
        actual_leaves: list[str] = []
        for entry in node_dir.iterdir():
            if entry.is_file() and entry.suffix == ".md" and entry.name != "NODE.md":
                actual_leaves.append(entry.name)
        listed_names = {Path(x).name for x in listed}
        for leaf in actual_leaves:
            if leaf not in listed_names and (
                Path(leaf).stem + ".md" not in listed_names
            ):
                self.add(
                    "V-04",
                    a,
                    f"leaf file {leaf!r} is not listed in NODE.md ## Leaves section.",
                )
        for link in listed:
            target = (node_dir / link.lstrip("/").lstrip("./")).resolve()
            if not target.exists():
                self.add(
                    "V-05",
                    a,
                    f"NODE.md ## Leaves link {link!r} does not resolve.",
                )

    def check_v19_debate_rounds(self, a: Artifact) -> None:
        candidates = []
        if a.path.is_file():
            parent = a.path.parent
            if a.kind == "thread":
                d = parent / "debate"
                if d.is_dir():
                    candidates.append(d)
            if a.kind == "leaf":
                d1 = parent / (a.path.stem + ".debate")
                d2 = parent / "debate" / a.path.stem
                d3 = parent / "debate"
                for d in (d1, d2, d3):
                    if d.is_dir():
                        candidates.append(d)
                        break
        for debate_dir in candidates:
            rounds = sorted(
                p.name
                for p in debate_dir.iterdir()
                if p.is_dir() and p.name.startswith("round-")
            )
            expected = [f"round-{i:02d}" for i in range(1, len(rounds) + 1)]
            if rounds != expected:
                self.add(
                    "V-19",
                    a,
                    f"debate rounds under {debate_dir.relative_to(self.brain)} "
                    f"expected {expected}, found {rounds}.",
                )
