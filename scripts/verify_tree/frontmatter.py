"""YAML frontmatter and H1 parsing.

Tolerates leading HTML comment blocks (the autogen banner on index files)
before the opening `---` delimiter, per CONVENTIONS § 3.
"""

from __future__ import annotations

import re
from typing import Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - CI installs PyYAML
    import sys

    sys.stderr.write(
        "error: PyYAML is required. Install with `pip install PyYAML`.\n"
    )
    sys.exit(2)


def parse_frontmatter(text: str) -> tuple[dict, str, int, Optional[str]]:
    """Parse YAML frontmatter from a markdown file.

    Returns (frontmatter_dict, body_text, body_start_line, error_or_none).
    body_start_line is 1-based line where the body content begins.

    Leading HTML comment blocks (e.g. the autogen banner on index files) are
    tolerated and skipped before the `---` delimiter.
    """
    prefix_lines = 0
    cursor = text
    while cursor.lstrip().startswith("<!--"):
        stripped = cursor.lstrip()
        prefix_lines += cursor[: len(cursor) - len(stripped)].count("\n")
        cursor = stripped
        end = cursor.find("-->")
        if end == -1:
            return {}, text, 1, "unterminated HTML comment at top of file"
        consumed = cursor[: end + 3]
        prefix_lines += consumed.count("\n")
        cursor = cursor[end + 3 :]
        stripped = cursor.lstrip("\n")
        prefix_lines += len(cursor) - len(stripped)
        cursor = stripped
    text_effective = cursor
    if not text_effective.startswith("---"):
        return {}, text, 1, "missing frontmatter delimiter"
    lines = text_effective.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, 1, "unterminated frontmatter"
    yaml_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :])
    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        return {}, body, prefix_lines + end + 2, f"YAML error: {exc}"
    if not isinstance(data, dict):
        return {}, body, prefix_lines + end + 2, "frontmatter is not a mapping"
    return data, body, prefix_lines + end + 2, None


def find_first_h1(body: str, body_start_line: int) -> tuple[Optional[str], int]:
    """Return (title_text, absolute_line_number_1_based) or (None, 0)."""
    lines = body.split("\n")
    for idx, line in enumerate(lines):
        m = re.match(r"^# +(.+?)\s*$", line)
        if m:
            return m.group(1).strip(), body_start_line + idx
    return None, 0
