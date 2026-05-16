"""MCP resources — current brain context, read fresh on each request."""

from __future__ import annotations

from pathlib import Path

from ._subprocess import resolve_brain_dir

RESOURCES: dict[str, str] = {
    "thread-index": "thread-index.md",
    "current-state": "current-state.md",
    "CONVENTIONS": "CONVENTIONS.md",
}


def resolve_brain() -> Path:
    """Resolve the brain directory (<root>/project-brain/) for resource reads."""
    brain_dir, err_msg = resolve_brain_dir(None)
    if err_msg:
        raise RuntimeError(err_msg)
    p = Path(brain_dir).resolve()
    if not p.is_dir():
        raise RuntimeError(f"brain dir {p} does not exist (PROJECT_BRAIN_HOME may point at an empty project root)")
    return p


def read_resource(name: str) -> str:
    if name not in RESOURCES:
        raise KeyError(f"unknown resource: {name} (known: {sorted(RESOURCES)})")
    rel = RESOURCES[name]
    return (resolve_brain() / rel).read_text(encoding="utf-8")
