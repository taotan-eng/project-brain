"""Two-layer configuration resolver — per-project primary, global opt-in.

CONVENTIONS § 2 (v1.0.0-rc4):

* Per-project config lives at ``<brain>/config.yaml`` and is authoritative
  for the brain it sits beside. It declares the brain's primary alias,
  any aliases it wants to reference cross-project, and optional
  operational knobs (verbosity, transcript policy).

* A user-global registry at ``~/.config/project-brain/projects.yaml`` is
  OPTIONAL. It only matters when a ``soft_links`` URI uses an alias that
  isn't in the per-project ``aliases:`` block. If the global registry is
  absent, cross-project references resolve to a V-03 *warning* — never an
  error — so the brain remains fully functional without ``~/`` access.

Precedence for alias resolution:
  per-project aliases  >  global registry  >  unresolvable (warning)

Environment overrides (testing / CI):
  PROJECT_BRAIN_CONFIG          — absolute path to per-project config.yaml
  PROJECT_BRAIN_PROJECTS_YAML   — absolute path to global registry
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    import sys

    sys.stderr.write(
        "error: PyYAML is required. Install with `pip install PyYAML`.\n"
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def per_project_config_path(brain: Path) -> Path:
    """Return the expected location of per-project config.yaml."""
    override = os.environ.get("PROJECT_BRAIN_CONFIG")
    if override:
        return Path(override).expanduser()
    return brain / "config.yaml"


def global_registry_path() -> Path:
    """Return the expected location of the user-global registry.

    Defaults to ``$XDG_CONFIG_HOME/project-brain/projects.yaml`` per XDG,
    falling back to ``~/.config/project-brain/projects.yaml``.
    """
    override = os.environ.get("PROJECT_BRAIN_PROJECTS_YAML")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / "project-brain" / "projects.yaml"
    return Path("~/.config/project-brain/projects.yaml").expanduser()


# ---------------------------------------------------------------------------
# Loaders — each returns None if absent, {} sentinel if malformed.
# ---------------------------------------------------------------------------


def _safe_load(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def load_per_project_config(brain: Path) -> Optional[dict]:
    """Parse per-project config.yaml. Return None if absent, {} if malformed."""
    return _safe_load(per_project_config_path(brain))


def load_global_registry() -> Optional[dict]:
    """Parse the user-global registry. Return None if absent, {} if malformed."""
    return _safe_load(global_registry_path())


# ---------------------------------------------------------------------------
# Alias resolution
# ---------------------------------------------------------------------------


def resolve_alias(brain: Path, alias: str) -> Optional[dict]:
    """Look up an alias across the two layers.

    Returns the alias entry (a dict with at least a ``brain`` key) or None
    if the alias cannot be resolved anywhere. A ``None`` return at this
    layer is NOT necessarily an error — the caller decides severity
    based on whether any layer even exists.
    """
    per_project = load_per_project_config(brain)
    if isinstance(per_project, dict):
        aliases = per_project.get("aliases")
        if isinstance(aliases, dict) and alias in aliases:
            entry = aliases[alias]
            return _normalize_alias_entry(entry)

    registry = load_global_registry()
    if isinstance(registry, dict) and alias in registry:
        entry = registry[alias]
        return _normalize_alias_entry(entry)

    return None


def _normalize_alias_entry(entry: Any) -> Optional[dict]:
    """Accept both dict (rc4 canonical) and str (legacy bare path) forms."""
    if isinstance(entry, dict):
        return entry
    if isinstance(entry, str):
        return {"brain": entry}
    return None


def any_layer_available(brain: Path) -> bool:
    """True if at least one config layer is present on disk.

    Callers use this to decide whether an unresolvable alias is a
    V-03 ERROR (some layer exists; alias just wasn't listed) or a
    WARNING (no layer exists at all; cross-project validation
    can't happen, but the brain is still usable).
    """
    return (
        per_project_config_path(brain).is_file()
        or global_registry_path().is_file()
    )


# ---------------------------------------------------------------------------
# Operational knobs (consumed by skills, exposed here for symmetry)
# ---------------------------------------------------------------------------


VALID_VERBOSITY = frozenset({"terse", "normal", "verbose"})
VALID_TRANSCRIPT = frozenset({"on", "off"})


def get_verbosity(brain: Path) -> str:
    """Return configured verbosity level; default ``terse``."""
    env = os.environ.get("PROJECT_BRAIN_VERBOSITY")
    if env in VALID_VERBOSITY:
        return env
    cfg = load_per_project_config(brain)
    if isinstance(cfg, dict):
        v = cfg.get("verbosity")
        if v in VALID_VERBOSITY:
            return v
    return "terse"


def get_transcript_policy(brain: Path) -> str:
    """Return transcript_logging setting; default ``on``."""
    env = os.environ.get("PROJECT_BRAIN_TRANSCRIPT")
    if env in VALID_TRANSCRIPT:
        return env
    cfg = load_per_project_config(brain)
    if isinstance(cfg, dict):
        v = cfg.get("transcript_logging")
        if v in VALID_TRANSCRIPT:
            return v
    return "on"
