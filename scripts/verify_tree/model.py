"""Data model: constants, Violation, Artifact.

All "source of truth" values that the validator pins against live here. If
CONVENTIONS.md adds a new status, this file is the first place to touch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Exit codes (SKILL.md § Process, § Failure modes)
EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_INVOCATION = 2

# Regex patterns

# SLUG_FORBIDDEN_RE catches characters that are never allowed in a slug:
# ASCII uppercase A-Z (we preserve the "lower" of kebab-case for Latin
# scripts), whitespace, FS-reserved chars (/\:*?"<>|), and ASCII control
# chars. Unicode letters/digits in any script are fine. Use is_valid_slug()
# below for the full check (length + forbidden chars + kebab shape).
SLUG_FORBIDDEN_RE = re.compile(r'[A-Z\s/\\:*?"<>|\x00-\x1f]')

# Legacy ASCII-only slug regex, retained for callers that explicitly want
# ASCII-only behavior (none in-tree as of this revision; kept for any
# external project's verify-tree.d/ extension hooks that may import it).
SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

# PATH_COMPONENT_FORBIDDEN_RE — same forbidden set as slugs, applied to
# every path segment under project-brain/. Replaces the earlier ASCII-only
# rule. Allows Unicode dirnames, e.g. tree/<chinese>/leaf.md.
PATH_COMPONENT_FORBIDDEN_RE = re.compile(r'[\s/\\:*?"<>|\x00-\x1f]')

# Legacy ASCII-only path-component regex, retained for backwards compat.
ASCII_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)?$")

ROUND_DIR_RE = re.compile(r"^round-\d{2}$")
ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
)


def is_valid_slug(s: str) -> bool:
    """Validate a slug per CONVENTIONS § 11.1 (Unicode-friendly kebab-case).

    Rules:
      - 2-40 characters (Unicode codepoint count, not byte count). The
        2-char floor accommodates CJK 2-char compounds like 旅行 (travel),
        认证 (authentication), 决策 (decision) — semantically dense words
        Latin scripts express in 5-10 letters. ASCII users can also use
        2-char slugs like "ai" or "ml" if they want.
      - No ASCII uppercase A-Z. (Latin scripts must be lowercase; non-Latin
        scripts that have no case distinction pass freely.)
      - No whitespace, no FS-reserved chars (/\\:*?"<>|), no control chars.
      - Kebab shape: segments separated by single hyphens; no leading,
        trailing, or doubled hyphens.
      - Caller's responsibility: NFC-normalize the input first. We don't
        re-normalize here because the same string in NFC vs NFD has
        different lengths and we'd lie to the caller about validity.

    Examples (valid): ai, ml, auth, auth-rotation, runtime-v2,
                      香港转机, 旅行, データ-モデル, café-2
    Examples (invalid): Auth, auth_rotation, -leading, trailing-, dou--ble,
                        runtime/v2, ' spaces ', 'a' (too short)
    """
    if not isinstance(s, str):
        return False
    if not (2 <= len(s) <= 40):
        return False
    if SLUG_FORBIDDEN_RE.search(s):
        return False
    parts = s.split("-")
    if any(p == "" for p in parts):
        return False
    return True


def is_valid_path_component(p: str) -> bool:
    """Validate a path component (file/dir name) per CONVENTIONS § 11
    (V-21). Same forbidden set as slugs, but more permissive on shape:
    leading/trailing dashes, dots (extensions), and underscores are fine.

    Used by V-21 to gate every path segment under project-brain/.
    """
    if not isinstance(p, str) or p == "":
        return False
    if PATH_COMPONENT_FORBIDDEN_RE.search(p):
        return False
    return True

# CONVENTIONS § 11.2 / 11.3 reserved identifiers
RESERVED_FILENAMES = {
    "NODE.md",
    "CONVENTIONS.md",
    "README.md",
    "LICENSE",
    "thread.md",
    "decisions-candidates.md",
    "open-questions.md",
    "feedback-in.md",
    "feedback-out.md",
    "current-state.md",
    "thread-index.md",
    "transcript.md",
    "AUDIT-LOG.md",
    "CODEOWNERS",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "QUICKSTART.md",
    "INSTALL.md",
    "RUNTIME.md",
    "index.md",
    "config.yaml",
}
RESERVED_DIRS = {
    "project-brain",
    "thoughts",            # retained for rc3 → rc4 back-compat (half-migrated brains)
    "threads",
    "archive",
    "tree",
    "tree-staging",
    "debate",
    "tryouts",
    "diagrams",
    "attachments",
    "artifacts",           # per-thread structured products (record-artifact, v1.0.0-rc4+)
}

# Valid states per CONVENTIONS § 4
VALID_THREAD_STATUSES = {"active", "parked", "in-review", "archived"}
VALID_THREAD_MATURITIES = {"exploring", "refining", "locking"}
VALID_LEAF_STATUSES = {
    "draft",
    "in-review",
    "decided",
    "hardening",
    "specified",
    "building",
    "built",
    "superseded",
}
VALID_LEAF_MATURITIES = {None, "exploring", "refining", "locking"}
VALID_IMPL_SPEC_STATUSES = {
    "draft",
    "in-review",
    "ready",
    "building",
    "built",
    "stale",
}
VALID_HARDENING_PRE_STATUSES = {"decided", "specified"}

# status ↔ maturity matrix for threads (CONVENTIONS § 4.1)
THREAD_STATUS_MATURITY = {
    "active": {"exploring", "refining", "locking"},
    "parked": {"exploring", "refining", "locking"},
    "in-review": {"locking"},
    "archived": {None},
}

# Valid (leaf.status, impl-spec.status) pairs from § 4.4
LEAF_IMPL_SPEC_PAIRS = {
    ("specified", "ready"),
    ("building", "building"),
    ("built", "built"),
    ("hardening", "ready"),
    ("hardening", "building"),
    ("hardening", "built"),
    ("superseded", "stale"),
    ("superseded", "built"),
    ("superseded", "ready"),
}

# Required frontmatter fields by artifact kind (V-06)
REQUIRED_BY_KIND = {
    "thread": [
        "id",
        "title",
        "created_at",
        "owner",
        "primary_project",
        "status",
    ],
    "leaf": [
        "id",
        "title",
        "created_at",
        "owner",
        "primary_project",
        "status",
        "node_type",
        "domain",
    ],
    "node": [
        "id",
        "title",
        "created_at",
        "owner",
        "primary_project",
        "status",
        "node_type",
        "domain",
    ],
    "impl-spec": [
        "id",
        "title",
        "created_at",
        "owner",
        "primary_project",
        "kind",
        "source_leaf",
        "status",
    ],
    "index": ["id", "title", "primary_project", "kind"],
    "snapshot": ["id", "title", "primary_project", "kind"],
    # Debate synthesized outputs (F9) — minimal frontmatter so the classifier
    # has something to dispatch on; no title/owner (inherited from parent
    # thread or leaf), no status (implicit from parent's maturity).
    "debate-index": ["id", "kind", "created_at"],
    "debate-synthesized": ["id", "kind", "created_at"],
    # Per-thread artifacts (record-artifact, v1.0.0-rc4+) — structured
    # products that live under threads/<slug>/artifacts/. Always carry
    # frontmatter and V-01/V-06 apply. source_thread must match the parent
    # thread slug (V-22). `artifact_kind` is a free-form label ("debate",
    # "analysis", "benchmark", etc.) — NOT required by V-06, but encouraged.
    "artifact": ["id", "title", "kind", "created_at", "source_thread"],
}

# Artifact kinds that are NOT expected to carry YAML frontmatter.
# Per F9 (Project-Brain v0.9.0-alpha.4 E2E test report):
#   - debate-round-raw: feedback-in, defender, transcript, tryouts/* — evidence
#   - debate-feedback: feedback-in.md / feedback-out.md at thread level
#   - thread-helper:   decisions-candidates.md, open-questions.md — scratchpads
#   - transcript:      per-thread transcript.md — append-only human-LLM log (v1.0.0-rc4)
#   - attachment:      anything inside <thread>/attachments/ — arbitrary evidence (v1.0.0-rc4)
#   - unknown:         anything we can't classify shouldn't fire parse errors
# check_parse skips these entirely so a missing '---' delimiter is not V-06.
KINDS_WITHOUT_FRONTMATTER = frozenset(
    {
        "unknown",
        "debate-feedback",
        "thread-helper",
        "debate-round-raw",
        "transcript",
        "attachment",
    }
)


@dataclass
class Violation:
    """A single rule failure. Codes are stable so callers can filter."""

    code: str
    file: str
    line: int
    message: str
    artifact_id: Optional[str] = None
    severity: str = "error"  # or "warning"

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "artifact_id": self.artifact_id,
            "severity": self.severity,
        }


@dataclass
class Artifact:
    """One markdown file in the brain, after parse."""

    path: Path                         # absolute on-disk path
    rel_path: str                      # relative to brain_path
    kind: str                          # thread|leaf|node|impl-spec|index|snapshot|conventions|debate-feedback|thread-helper|unknown
    frontmatter: dict = field(default_factory=dict)
    body: str = ""
    title_line: int = 0                # 1-based line of first H1, 0 if none
    first_h1: Optional[str] = None
    parse_error: Optional[str] = None
