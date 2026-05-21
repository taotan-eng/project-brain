"""Layer-1 invocation helper.

Enforces the trust boundary from round-01 P6: no shell expansion, argv-only
invocation, structured response. Layer-2 code never builds shell commands
from strings.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


# Host-context env vars: the host (Cowork, Codex CLI, Claude Code) deliberately
# named the current project. Higher confidence than a user pin — if the host
# says "this is the project," trust it over a global PROJECT_BRAIN_HOME.
_HOST_CONTEXT_ENV_VARS = (
    "COWORK_WORKSPACE_FOLDER",   # Cowork sets at session start
    "CODEX_PROJECT_ROOT",        # OpenAI Codex CLI (if it sets it)
    "CLAUDE_PROJECT_ROOT",       # Claude Code CLI (if it sets it; cwd-based today)
)

# User pin: a deliberate global default the user set in their MCP config.
# Beats cwd inference (lower confidence) but yields to host context (higher).
_USER_PIN_ENV_VAR = "PROJECT_BRAIN_HOME"


def _walk_up_for_git(start: Path | None = None) -> Path | None:
    """Walk up from cwd looking for .git/. Returns the repo root or None."""
    current = (start or Path.cwd()).resolve()
    for _ in range(40):  # bounded against malformed symlinks
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


def _validate_and_normalize(raw: str) -> tuple[str | None, str | None]:
    """Expand `~`, reject trailing `/project-brain`, normalize trailing slash."""
    expanded = os.path.expanduser(raw)
    normalized = expanded.rstrip("/").rstrip("\\")
    if normalized.endswith("/project-brain") or normalized.endswith("\\project-brain"):
        suggested = normalized[: -len("/project-brain")]
        return None, (
            f"PROJECT_BRAIN_HOME (or target) should be the parent dir, not the brain itself. "
            f"You passed {raw!r}; try {suggested!r} instead. "
            f"The brain at <root>/project-brain/ will be created or used automatically."
        )
    return normalized, None


def resolve_project_root(arg: str | None) -> tuple[str | None, str | None]:
    """Resolve the project root via a three-tier confidence chain.

    Priority order (most explicit / highest confidence first):
      1. Explicit per-call `arg` (most explicit; what callers pass)
      2. Host-context env vars (host deliberately named the project):
           COWORK_WORKSPACE_FOLDER, CODEX_PROJECT_ROOT, CLAUDE_PROJECT_ROOT
      3. PROJECT_BRAIN_HOME (user's deliberate pin; beats cwd inference)
      4. Git walk-up from cwd (lowest confidence; Claude Code's signal)
      5. Fail with informative error

    Tier-3-beats-tier-4 fixes a sharp edge that bit ChatGPT-over-tunnel: an
    incidental git repo in the server's cwd would otherwise shadow an explicit
    PROJECT_BRAIN_HOME. The user's pin is more deliberate than wherever the
    server happens to be launched from.

    Returns `(root_path, error_message)`. Successful resolution sets
    `error_message=None`. Trailing `/project-brain` is rejected with a
    helpful hint. `~` in env values is expanded to `$HOME`.
    """
    # 1. Explicit arg wins
    if arg and arg.strip():
        return _validate_and_normalize(arg.strip())

    # 2. Reliable host context (host explicitly named the project)
    for env_var in _HOST_CONTEXT_ENV_VARS:
        value = os.environ.get(env_var, "").strip()
        if value:
            return _validate_and_normalize(value)

    # 3. User pin (deliberate; beats cwd inference)
    pin = os.environ.get(_USER_PIN_ENV_VAR, "").strip()
    if pin:
        return _validate_and_normalize(pin)

    # 4. Cwd inference — git walk-up (lowest confidence; Claude Code's signal)
    git_root = _walk_up_for_git()
    if git_root is not None:
        return _validate_and_normalize(str(git_root))

    # 5. Fail with informative error
    tried = (
        "explicit arg, host-context env (COWORK_WORKSPACE_FOLDER / "
        "CODEX_PROJECT_ROOT / CLAUDE_PROJECT_ROOT), PROJECT_BRAIN_HOME, "
        "cwd git-walk-up"
    )
    return None, (
        f"could not resolve a project root. Tried: {tried}. "
        f"Set PROJECT_BRAIN_HOME to your project root, or run from inside "
        f"the project directory. Server cwd: {Path.cwd()}"
    )


def resolve_brain_dir(arg: str | None) -> tuple[str | None, str | None]:
    """Resolve the brain directory — where CONVENTIONS.md, threads/, etc. live.

    Used by every tool except `init_project_brain`. Returns `(brain_dir,
    error_message)` where `brain_dir = <root>/project-brain/`. Errors from
    `resolve_project_root` (env unset, trailing `/project-brain`) propagate
    verbatim.

    Caller pattern in *_impl:

        brain, err_msg = resolve_brain_dir(args.brain)
        if err_msg:
            return err("validation_error", err_msg, hint=...)
    """
    root, err_msg = resolve_project_root(arg)
    if err_msg:
        return None, err_msg
    return str(Path(root) / "project-brain"), None


def find_pack_root(start: Path | None = None) -> Path:
    """Resolve the project-brain pack root.

    Resolution order (first match wins):
      1. $PROJECT_BRAIN_PACK_ROOT
      2. $CLAUDE_PLUGIN_ROOT
      3. Walk up from `start` (caller-provided cwd)
      4. Bundled pack at `<module>/_pack/` (pip/brew/wheel installs)
      5. Walk up from this module's location (editable installs)
    """
    env = os.environ.get("PROJECT_BRAIN_PACK_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        p = Path(env).resolve()
        if _looks_like_pack(p):
            return p

    # Source 3: walk up from `start` (caller-provided cwd)
    if start is not None:
        start = Path(start).resolve()
        for candidate in [start, *start.parents]:
            if _looks_like_pack(candidate):
                return candidate

    # Source 4: bundled pack alongside the installed module (pip/brew installs)
    bundled = Path(__file__).resolve().parent / "_pack"
    if _looks_like_pack(bundled):
        return bundled

    # Source 5: walk up from this module's location (editable-install fallback)
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if _looks_like_pack(candidate):
            return candidate

    raise RuntimeError(
        "Cannot resolve pack root. Set PROJECT_BRAIN_PACK_ROOT or run from inside the pack."
    )


def _looks_like_pack(path: Path) -> bool:
    return (
        (path / "CONVENTIONS.md").is_file()
        and (path / "skills").is_dir()
        and (path / "scripts").is_dir()
    )


def run_script(script_name: str, argv: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    """Invoke a Layer-1 script under scripts/ with shell=False.

    Returns a structured dict:
      { ok: bool, exit_code: int, stdout: str, stderr: str, error: {message} | None }
    """
    pack = find_pack_root()
    script = pack / "scripts" / script_name
    if not script.is_file():
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "error": {"message": f"script not found: {script}"},
        }

    if not _has_exec_for(script):
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "error": {"message": f"cannot execute {script.name}: required interpreter missing"},
        }

    cmd: list[str] = [str(script), *argv]
    try:
        result = subprocess.run(
            cmd,
            shell=False,
            cwd=str(cwd) if cwd is not None else None,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
            "error": {"message": f"subprocess failed to start: {e}"},
        }

    payload: dict[str, Any] = {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error": None,
    }
    if result.returncode != 0:
        payload["error"] = {"message": result.stderr.strip() or f"exit {result.returncode}"}
    return payload


def _has_exec_for(script: Path) -> bool:
    suffix = script.suffix
    if suffix == ".sh":
        return shutil.which("bash") is not None
    if suffix == ".py":
        return shutil.which("python3") is not None
    return os.access(script, os.X_OK)
