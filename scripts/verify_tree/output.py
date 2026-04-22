"""Human-readable formatter for violations.

JSON formatting lives inline in cli.main() since it needs access to the
artifact count. This module just handles the grouped-by-file human output.
"""

from __future__ import annotations

import sys

from .model import Violation


def print_human(violations: list[Violation]) -> None:
    violations_sorted = sorted(violations, key=lambda v: (v.file, v.line, v.code))
    last_file = None
    for v in violations_sorted:
        if v.file != last_file:
            sys.stdout.write(f"\n{v.file}:\n")
            last_file = v.file
        tag = "error" if v.severity == "error" else "warning"
        sys.stdout.write(
            f"  {v.file}:{v.line}: [{v.code}] ({tag}) {v.message}\n"
        )
