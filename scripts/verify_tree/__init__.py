"""verify_tree — read-only validator for the project-brain tree.

Implements the contract in skills/verify-tree/SKILL.md. Checks invariants
V-01..V-21 from CONVENTIONS § 9 and naming rules N-01..N-04 from § 11.

Entry point: `main()` — wraps argparse and runs either validation or
--rebuild-index mode. Exit codes: 0 ok, 1 violations, 2 invocation error.

Modules:
    model               — constants, Violation, Artifact
    frontmatter         — YAML + H1 parsing
    discovery           — brain-root discovery, artifact classification, walking
    checker             — Checker orchestrator + cross-artifact helpers
    invariants_core     — V-01, V-02, V-06, V-10, V-21
    invariants_lifecycle— V-07, V-08, V-09, V-11, V-12, V-13
    invariants_refs     — V-03, V-14, V-15, V-16, V-17, V-18, V-20
    invariants_nodes    — V-04, V-05, V-19
    naming              — N-01..N-04
    rebuild             — --rebuild-index mode
    output              — human + JSON formatters
    extensions          — scripts/verify-tree.d/*.py loader
    cli                 — argparse + main()
"""

from .cli import main  # re-export for `python -m verify_tree`

__all__ = ["main"]
