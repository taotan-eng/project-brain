#!/usr/bin/env python3
"""Validate (and NFC-normalize) a slug per CONVENTIONS § 11.1.

Usage:
    python3 _validate_slug.py <slug>

Behavior:
    - Read the input string from argv[1].
    - Apply Unicode NFC normalization.
    - Validate against the rule (Unicode-friendly kebab-case): 3-40 chars,
      no ASCII uppercase, no whitespace, no FS-reserved chars (/\\:*?"<>|),
      no control chars, no leading/trailing/doubled hyphens.
    - On success: print the NFC-normalized form to stdout, exit 0.
    - On failure: print a clear, multi-line error to stderr, exit 1.
    - On wrong arg count: exit 2.

Bash scripts use this helper so they don't have to encode Unicode-aware
regex logic in bash (which is unreliable across platforms — macOS ships
bash 3.2 by default with limited Unicode support).

Example bash usage:
    if ! NORMALIZED="$(python3 .../scripts/_validate_slug.py "$SLUG")"; then
      # error message already printed to stderr by the helper
      exit 2
    fi
    SLUG="$NORMALIZED"
"""

from __future__ import annotations

import sys
import unicodedata


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: _validate_slug.py <slug>",
            file=sys.stderr,
        )
        return 2
    raw = argv[1]
    nfc = unicodedata.normalize("NFC", raw)

    # Length check (Unicode codepoints, not bytes).
    # Min lowered from 3 to 2 to accommodate CJK 2-char compounds like 旅行
    # (travel), 认证 (authentication), 决策 (decision) — semantically dense
    # words that Latin scripts express in 5-10 letters. ASCII users can
    # still use 2-char slugs like "ai" or "ml" if they want; that's fine.
    if not (2 <= len(nfc) <= 40):
        print(
            f"error: slug {nfc!r} length {len(nfc)} is outside the 2-40 char range "
            f"required by CONVENTIONS § 11.1.",
            file=sys.stderr,
        )
        return 1

    # Forbidden characters: ASCII uppercase, whitespace, FS-reserved, control.
    import re

    forbidden = re.compile(r'[A-Z\s/\\:*?"<>|\x00-\x1f]')
    m = forbidden.search(nfc)
    if m:
        ch = m.group(0)
        # Show codepoint for non-printables.
        if ord(ch) < 0x20:
            ch_repr = f"U+{ord(ch):04X}"
        else:
            ch_repr = repr(ch)
        print(
            f"error: slug {nfc!r} contains forbidden character {ch_repr} at position {m.start()}.\n"
            f"\n"
            f"  Slugs cannot contain: ASCII uppercase A-Z, whitespace,\n"
            f"  filesystem-reserved chars (/\\:*?\"<>|), or control chars.\n"
            f"  Unicode letters/digits in any script (中, ア, ا, ñ, etc.) are fine.",
            file=sys.stderr,
        )
        return 1

    # Kebab shape: split on `-`, every segment must be non-empty.
    parts = nfc.split("-")
    if any(p == "" for p in parts):
        print(
            f"error: slug {nfc!r} has an empty segment "
            f"(leading hyphen, trailing hyphen, or `--`).\n"
            f"\n"
            f"  Kebab shape: segments separated by single hyphens, no\n"
            f"  leading/trailing/doubled hyphens. Examples (valid):\n"
            f"    auth, auth-rotation, runtime-v2, 香港-转机, データ-モデル",
            file=sys.stderr,
        )
        return 1

    # Success: emit NFC-normalized form (caller may have passed NFD).
    print(nfc, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
