#!/usr/bin/env python3
"""verify-tree — thin shim for the verify_tree package.

This file exists so that `python3 scripts/verify-tree.py` continues to work
(CI and the original SKILL.md contract invoke it by path). All logic lives
in the `verify_tree/` sibling package.

Exit codes, flags, and behaviour are unchanged; see verify_tree/cli.py for
the contract.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Make the sibling `verify_tree/` package importable when this script is
# invoked by path (e.g. `python3 scripts/verify-tree.py`), without requiring
# the caller to set PYTHONPATH.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from verify_tree.cli import main  # noqa: E402
from verify_tree.model import EXIT_INVOCATION  # noqa: E402


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:  # pragma: no cover - defensive
        traceback.print_exc()
        sys.exit(EXIT_INVOCATION)
