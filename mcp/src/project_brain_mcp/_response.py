"""Structured-response helpers — every tool's return shape.

Every MCP tool returns:
    {
        "ok": bool,
        "data": dict | str | None,
        "error": {"code": str, "message": str, "hint": str | None} | None,
    }

`error.code` is drawn from a closed set: validation_error, script_error,
internal_error. Anything else raises AssertionError at construction time
so callers can't slip in ad-hoc codes.

Implements round-01 P6 (Layer 1/2 trust boundary): Layer 2 translates
Layer-1 exit codes + stderr into a discoverable, parseable shape rather
than passing through opaque process exceptions.
"""

from __future__ import annotations

from typing import Any, Literal

ErrorCode = Literal["validation_error", "script_error", "internal_error"]
_VALID_CODES: frozenset[str] = frozenset({"validation_error", "script_error", "internal_error"})


def ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def err(code: str, message: str, hint: str | None = None) -> dict[str, Any]:
    assert code in _VALID_CODES, f"unknown error code: {code!r} (must be one of {sorted(_VALID_CODES)})"
    return {
        "ok": False,
        "data": None,
        "error": {"code": code, "message": message, "hint": hint},
    }


def from_subprocess_result(result: dict[str, Any]) -> dict[str, Any]:
    """Convert _subprocess.run_script's raw dict to the structured shape.

    Success path (exit code 0): returns ok(stdout-as-data).
    Failure path: maps to script_error with a stderr-based hint when patternable.
    Script-not-found / interpreter-missing: maps to script_error with the
    raw error string and a "check the pack install" hint.
    """
    if result.get("ok") is True:
        return ok(
            {
                "stdout": (result.get("stdout") or "").strip(),
                "stderr": (result.get("stderr") or "").strip() or None,
                "exit_code": result.get("exit_code", 0),
            }
        )

    raw_err = result.get("error") or {}
    stderr = result.get("stderr") or raw_err.get("message") or ""
    message = stderr[-500:].strip() if stderr else "script returned non-zero exit"
    return err("script_error", message, hint=_hint_from_stderr(stderr))


def _hint_from_stderr(stderr: str) -> str | None:
    """Best-effort hint matching for common Layer-1 failures."""
    lower = stderr.lower()
    if "not a directory" in lower or "no such file" in lower or "not found" in lower:
        return "Check the --brain path; it must point at an existing brain directory."
    if "already exists" in lower:
        return "A thread with this slug already exists; pick a different slug."
    if "slug" in lower and ("invalid" in lower or "must match" in lower or "must be" in lower):
        return "Slug must be kebab-case Unicode (2-40 chars, no whitespace or filesystem-reserved characters)."
    if "tree_prs" in lower or "in-review" in lower:
        return "Thread has open promotion PRs or is in-review; use finalize-promotion or discard-promotion first."
    if "missing frontmatter" in lower or "frontmatter" in lower:
        return "The target file's YAML frontmatter is malformed or missing; run verify-tree for a precise error."
    return None
