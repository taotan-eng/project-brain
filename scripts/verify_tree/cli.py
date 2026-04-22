"""CLI entry point — argparse wiring + main() dispatcher.

Exit codes:
  0  success (no errors; or warnings only without --warnings-as-errors)
  1  validation errors, or --rebuild-index source validation failure
  2  invocation error (bad flags, brain not found) or rebuild write/verify failure
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Optional

from .checker import Checker
from .discovery import find_brain_root, iter_scoped_paths, load_artifact
from .extensions import load_extensions
from .frontmatter import parse_frontmatter
from .model import EXIT_INVOCATION, EXIT_OK, EXIT_VIOLATIONS, Artifact
from .output import print_human
from .rebuild import rebuild_index


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="verify-tree",
        description="Read-only validator for the project-brain tree.",
    )
    p.add_argument(
        "--brain",
        metavar="PATH",
        help="Brain root (containing CONVENTIONS.md). Default: nearest ancestor.",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--thread", metavar="SLUG", help="Restrict validation to one thread.")
    g.add_argument("--path", metavar="PATH", help="Restrict validation to a subpath.")
    g.add_argument(
        "--staging",
        metavar="SLUG",
        help="Restrict to a thread's tree-staging/.",
    )
    p.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Regenerate thread-index.md and current-state.md from source frontmatter.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="For --rebuild-index: print diff instead of writing.",
    )
    p.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Output format (default: human).",
    )
    p.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Treat warnings as errors for exit-code purposes.",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    start = Path(args.brain).resolve() if args.brain else Path.cwd()
    brain = find_brain_root(start)
    if brain is None:
        sys.stderr.write(
            f"error: no ancestor of {start} contains CONVENTIONS.md — cannot find brain root.\n"
        )
        return EXIT_INVOCATION

    # Sanity-check CONVENTIONS parses so all downstream code can assume it.
    conv = brain / "CONVENTIONS.md"
    if conv.is_file():
        try:
            _, _, _, err = parse_frontmatter(conv.read_text(encoding="utf-8"))
        except OSError as exc:
            sys.stderr.write(f"error: cannot read CONVENTIONS.md: {exc}\n")
            return EXIT_INVOCATION
        if err:
            sys.stderr.write(f"error: CONVENTIONS.md frontmatter: {err}\n")
            return EXIT_INVOCATION

    if args.rebuild_index:
        if args.thread or args.path or args.staging:
            sys.stderr.write(
                "error: --rebuild-index is mutually exclusive with --thread/--path/--staging.\n"
            )
            return EXIT_INVOCATION
        return rebuild_index(brain, args.dry_run)

    # Validation path.
    artifacts: list[Artifact] = []
    for abs_path in iter_scoped_paths(brain, args.thread, args.path, args.staging):
        artifacts.append(load_artifact(abs_path, brain))

    checker = Checker(brain, artifacts)
    checker.check_all()
    load_extensions(brain, checker)

    errors = [v for v in checker.violations if v.severity == "error"]
    warnings = [v for v in checker.violations if v.severity == "warning"]

    if args.format == "json":
        out = {
            "errors": [v.as_dict() for v in errors],
            "warnings": [v.as_dict() for v in warnings],
            "summary": {"errors": len(errors), "warnings": len(warnings)},
            "artifact_count": len(artifacts),
        }
        sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n")
    else:
        print_human(errors + warnings)
        sys.stdout.write(
            f"\n{len(errors)} error{'s' if len(errors) != 1 else ''}, "
            f"{len(warnings)} warning{'s' if len(warnings) != 1 else ''} "
            f"({len(artifacts)} artifact{'s' if len(artifacts) != 1 else ''} walked).\n"
        )

    if errors:
        return EXIT_VIOLATIONS
    if warnings and args.warnings_as_errors:
        return EXIT_VIOLATIONS
    return EXIT_OK


def _entry() -> None:  # pragma: no cover - invoked by the hyphenated shim
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(EXIT_INVOCATION)
