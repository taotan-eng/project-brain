"""Extension loader.

Loads every `scripts/verify-tree.d/*.py` file and invokes its `check(brain,
artifacts, violations)` function if present. Failures in extensions are
recorded as `X-IMPORT-ERROR` violations rather than aborting validation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from .checker import Checker
from .model import Violation


def load_extensions(brain: Path, checker: Checker) -> None:
    ext_dir = brain / "scripts" / "verify-tree.d"
    if not ext_dir.is_dir():
        return
    for py in sorted(ext_dir.glob("*.py")):
        spec = importlib.util.spec_from_file_location(f"_vt_ext_{py.stem}", py)
        if spec is None or spec.loader is None:
            continue
        try:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            if hasattr(mod, "check") and callable(mod.check):
                mod.check(brain, checker.artifacts, checker.violations)
        except Exception as exc:
            checker.violations.append(
                Violation(
                    code="X-IMPORT-ERROR",
                    file=str(py.relative_to(brain)),
                    line=0,
                    message=f"extension import failed: {exc}",
                )
            )
