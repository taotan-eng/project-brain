"""Minimal YAML parser — stdlib-only fallback for PyYAML.

project-brain's YAML surface is narrow (frontmatter, config.yaml, the
user-global registry). None of it uses anchors, tags, complex types,
merge keys, or flow collections beyond `[]` and `{}`. A full YAML
parser is overkill and introduces a pip dependency that breaks installs
in minimal Python environments (bare Python 3, Alpine containers, CI
runners without caches).

This module implements ``safe_load`` and ``YAMLError`` with just the
shapes the pack actually writes:

- Top-level is a mapping (dict) or empty.
- Values are: strings (quoted or bare), ints, floats, booleans, null.
- Empty flow collections: ``[]`` and ``{}``.
- Block lists: lines starting with ``- `` at consistent indent.
- Block maps: 2-space (or deeper) nested indent.
- ``# ...`` line comments are stripped.

Anything outside the subset raises ``YAMLError`` with an actionable
message. If a project relies on exotic YAML, they can keep PyYAML
installed — ``frontmatter.py`` / ``config.py`` prefer it when available
and fall back to this module only if the import fails.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple


class YAMLError(Exception):
    """Raised on anything we can't parse. Mimics yaml.YAMLError's role."""


_TRUE_LITERALS = {"true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON"}
_FALSE_LITERALS = {"false", "False", "FALSE", "no", "No", "NO", "off", "Off", "OFF"}
_NULL_LITERALS = {"null", "Null", "NULL", "~", ""}
_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+[eE][+-]?\d+)$")


def _strip_comment(line: str) -> str:
    """Remove ``#`` comments not inside a quoted string."""
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            # Inline comment — strip from the first '#' that's preceded by
            # whitespace (YAML comment rule) or sits at column 0.
            if i == 0 or line[i - 1] in " \t":
                return line[:i].rstrip()
    return line


def _parse_scalar(raw: str) -> Any:
    """Parse a scalar token — quoted string, number, bool, null, or bare string."""
    raw = raw.strip()
    if not raw or raw in _NULL_LITERALS:
        return None
    if raw in _TRUE_LITERALS:
        return True
    if raw in _FALSE_LITERALS:
        return False
    # Quoted strings
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        inner = raw[1:-1]
        if raw[0] == '"':
            # Minimal escape handling — \n, \t, \\, \"
            return inner.encode("utf-8").decode("unicode_escape")
        return inner  # single-quoted: literal, except doubled '' → '
    # Numbers (but ISO-8601 timestamps and slugs go through as strings)
    if _INT_RE.match(raw):
        try:
            return int(raw)
        except ValueError:
            pass
    if _FLOAT_RE.match(raw):
        try:
            return float(raw)
        except ValueError:
            pass
    # Empty flow collections
    if raw == "[]":
        return []
    if raw == "{}":
        return {}
    # Bare string — includes ISO-8601 timestamps, slugs, emails, paths.
    return raw


def _indent_of(line: str) -> int:
    """Count leading spaces. Tabs are not supported (YAML spec agrees)."""
    i = 0
    for ch in line:
        if ch == " ":
            i += 1
        else:
            break
    if i < len(line) and line[i] == "\t":
        raise YAMLError(
            "tabs are not allowed for YAML indentation (use spaces)"
        )
    return i


def _preprocess(text: str) -> List[Tuple[int, str]]:
    """Strip comments and blank lines; return list of (indent, content)."""
    out: List[Tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = _strip_comment(raw)
        if not stripped.strip():
            continue
        out.append((_indent_of(stripped), stripped.lstrip(" ")))
    return out


class _Stream:
    """Line cursor over the preprocessed token list."""

    def __init__(self, lines: List[Tuple[int, str]]):
        self.lines = lines
        self.i = 0

    def peek(self) -> Optional[Tuple[int, str]]:
        return self.lines[self.i] if self.i < len(self.lines) else None

    def advance(self) -> None:
        self.i += 1


def _parse_block(stream: _Stream, base_indent: int) -> Any:
    """Parse a block (either a mapping or a list) starting at base_indent.

    Returns a dict or list. Caller guarantees the next line is at base_indent
    or deeper.
    """
    first = stream.peek()
    if first is None:
        return {}
    indent, content = first
    if indent < base_indent:
        return {}
    # List block if first line starts with '- '
    if content.startswith("- ") or content == "-":
        return _parse_list(stream, base_indent)
    return _parse_mapping(stream, base_indent)


def _parse_mapping(stream: _Stream, base_indent: int) -> dict:
    result: dict = {}
    while True:
        peek = stream.peek()
        if peek is None:
            break
        indent, content = peek
        if indent < base_indent:
            break
        if indent > base_indent:
            raise YAMLError(
                f"unexpected indent at '{content[:60]}' "
                f"(expected {base_indent}, got {indent})"
            )
        if ":" not in content:
            raise YAMLError(
                f"expected 'key: value' or 'key:' in mapping, got: {content!r}"
            )
        # Split on the first ':' followed by space/EOL — but not inside quotes.
        key, value_part = _split_key_value(content)
        stream.advance()
        if value_part == "":
            # Nested block follows — peek for indent.
            nxt = stream.peek()
            if nxt is None or nxt[0] <= base_indent:
                # Empty value: treat as null.
                result[key] = None
            else:
                result[key] = _parse_block(stream, nxt[0])
        else:
            result[key] = _parse_scalar(value_part)
    return result


def _parse_list(stream: _Stream, base_indent: int) -> list:
    result: list = []
    while True:
        peek = stream.peek()
        if peek is None:
            break
        indent, content = peek
        if indent < base_indent or not (content.startswith("- ") or content == "-"):
            break
        if indent > base_indent:
            raise YAMLError(
                f"list item indent {indent} > expected {base_indent}: {content!r}"
            )
        # Consume the '- ' prefix
        item_body = content[2:] if content.startswith("- ") else ""
        stream.advance()
        if item_body == "":
            # Next-line nested value
            nxt = stream.peek()
            if nxt is None or nxt[0] <= base_indent:
                result.append(None)
            else:
                result.append(_parse_block(stream, nxt[0]))
        elif ":" in item_body and _looks_like_map_start(item_body):
            # List-of-maps: first key inline, further keys on subsequent lines.
            # We represent the inline key and then merge any continuation keys
            # at base_indent + 2.
            first_key, first_value_part = _split_key_value(item_body)
            item: dict = {}
            if first_value_part == "":
                # Unusual case — key with no value, with nested block below.
                nxt = stream.peek()
                if nxt is not None and nxt[0] > base_indent:
                    item[first_key] = _parse_block(stream, nxt[0])
                else:
                    item[first_key] = None
            else:
                item[first_key] = _parse_scalar(first_value_part)
            # Merge continuation keys at base_indent + 2 (or deeper).
            cont_indent = base_indent + 2
            while True:
                nxt = stream.peek()
                if nxt is None:
                    break
                nxt_indent, nxt_content = nxt
                if nxt_indent < cont_indent:
                    break
                # This line is a continuation of the current item's mapping.
                if nxt_indent == cont_indent and ":" in nxt_content:
                    ck, cv = _split_key_value(nxt_content)
                    stream.advance()
                    if cv == "":
                        deeper = stream.peek()
                        if deeper is not None and deeper[0] > cont_indent:
                            item[ck] = _parse_block(stream, deeper[0])
                        else:
                            item[ck] = None
                    else:
                        item[ck] = _parse_scalar(cv)
                else:
                    break
            result.append(item)
        else:
            result.append(_parse_scalar(item_body))
    return result


def _looks_like_map_start(text: str) -> bool:
    """Does text look like 'key: something' (vs. a URL-ish scalar)?"""
    # Find the first ':' not inside quotes. If followed by space or EOL, it's a map key.
    return bool(_split_key_value_safe(text))


def _split_key_value(content: str) -> Tuple[str, str]:
    """Split a 'key: value' line. Raises YAMLError if malformed."""
    result = _split_key_value_safe(content)
    if not result:
        raise YAMLError(f"expected 'key: value' format: {content!r}")
    key, value = result
    return key.strip(), value.lstrip()


def _split_key_value_safe(content: str) -> Optional[Tuple[str, str]]:
    """Like _split_key_value but returns None instead of raising."""
    in_single = False
    in_double = False
    for i, ch in enumerate(content):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ":" and not in_single and not in_double:
            after = content[i + 1 :]
            if after == "" or after.startswith(" ") or after.startswith("\t"):
                return content[:i], after.lstrip(" \t")
    return None


def safe_load(text: str) -> Any:
    """Parse ``text`` as YAML; return dict/list/scalar/None.

    Mirrors the public API of ``yaml.safe_load`` for the subset we use.
    """
    if text is None:
        return None
    lines = _preprocess(text)
    if not lines:
        return None
    stream = _Stream(lines)
    first_indent = lines[0][0]
    return _parse_block(stream, first_indent)
