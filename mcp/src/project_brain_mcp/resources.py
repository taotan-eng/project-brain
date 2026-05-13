"""MCP resources — current brain context, read fresh on each request."""

from __future__ import annotations

import os
from pathlib import Path

RESOURCES: dict[str, str] = {
    "thread-index": "thread-index.md",
    "current-state": "current-state.md",
    "CONVENTIONS": "CONVENTIONS.md",
}


def resolve_brain() -> Path:
    bh = os.environ.get("PROJECT_BRAIN_HOME")
    if not bh:
        raise RuntimeError(
            "PROJECT_BRAIN_HOME not set; cannot resolve brain root for resources"
        )
    p = Path(bh).resolve()
    if not p.is_dir():
        raise RuntimeError(f"PROJECT_BRAIN_HOME={p} is not a directory")
    return p


def read_resource(name: str) -> str:
    if name not in RESOURCES:
        raise KeyError(f"unknown resource: {name} (known: {sorted(RESOURCES)})")
    rel = RESOURCES[name]
    return (resolve_brain() / rel).read_text(encoding="utf-8")
