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


_PROJECT_ROOT_CACHE = Path.home() / ".config" / "project-brain" / "last-used-root.txt"

# Env-var names consulted in priority order. Mirrors verify_tree.config's
# _HOST_ENV_PROBES so Layer-1 and Layer-2 agree on the source set.
_ROOT_ENV_VARS = (
    "PROJECT_BRAIN_HOME",        # explicit MCP config env (chat apps)
    "COWORK_WORKSPACE_FOLDER",   # Cowork sets at session start
    "CODEX_PROJECT_ROOT",        # OpenAI Codex CLI
    "CLAUDE_PROJECT_ROOT",       # Claude Code CLI
)


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


def _read_root_cache() -> str | None:
    """Best-effort read of the last-used-root cache. Returns None on any failure."""
    try:
        return _PROJECT_ROOT_CACHE.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None
    except Exception:
        return None  # corrupt cache; ignore


def _write_root_cache(root: str) -> None:
    """Best-effort write of the last-used-root cache. Failures don't propagate."""
    try:
        _PROJECT_ROOT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _PROJECT_ROOT_CACHE.write_text(root.rstrip("/").rstrip("\\") + "\n", encoding="utf-8")
    except Exception:
        pass


def _validate_and_normalize(path: str) -> tuple[str | None, str | None]:
    """Reject trailing `/project-brain` (Path C); normalize trailing slash."""
    normalized = path.rstrip("/").rstrip("\\")
    if normalized.endswith("/project-brain") or normalized.endswith("\\project-brain"):
        suggested = normalized[: -len("/project-brain")]
        return None, (
            f"PROJECT_BRAIN_HOME (or target) should be the parent dir, not the brain itself. "
            f"You passed {path!r}; try {suggested!r} instead. "
            f"The brain at <root>/project-brain/ will be created or used automatically."
        )
    return normalized, None


def resolve_project_root(arg: str | None) -> tuple[str | None, str | None]:
    """Resolve the project root via the documented 8-step chain.

    Priority order (filesystem signals first, env vars second, cache last):
      1. Explicit `arg`
      2. Nearest .git/ ancestor of cwd (filesystem signal)
      3. $PROJECT_BRAIN_HOME (MCP config / chat-app)
      4. $COWORK_WORKSPACE_FOLDER (Cowork session env)
      5. $CODEX_PROJECT_ROOT (OpenAI Codex CLI)
      6. $CLAUDE_PROJECT_ROOT (Claude Code CLI)
      7. Last-used cache at ~/.config/project-brain/last-used-root.txt
      8. Structured error listing every source tried

    Filesystem-first rationale: if the server is launched from inside a git
    repo, that repo is almost certainly the project the user means right now
    — CLI hosts (Claude Code, Codex) rely on this. Chat apps that pin to a
    single brain via $PROJECT_BRAIN_HOME still resolve correctly because the
    cwd they launch from (the OS app dir / $HOME) isn't inside any git repo,
    so step 2 misses cleanly and step 3 takes over.

    Returns `(root_path, error_message)`. Successful resolution sets
    `error_message=None`. Trailing `/project-brain` is rejected with a
    helpful hint (Path C).
    """
    # 1. Explicit arg wins
    if arg and arg.strip():
        return _validate_and_normalize(arg.strip())

    # 2. Git walk-up from cwd (filesystem signal)
    git_root = _walk_up_for_git()
    if git_root is not None:
        return _validate_and_normalize(str(git_root))

    # 3-6. Env vars in priority order
    for env_var in _ROOT_ENV_VARS:
        value = os.environ.get(env_var, "").strip()
        if value:
            return _validate_and_normalize(value)

    # 7. Last-used cache (consulted only when nothing else matches)
    cached = _read_root_cache()
    if cached:
        return _validate_and_normalize(cached)

    # 8. Fail with informative error listing every source tried
    tried = "arg, git-walk-up, " + ", ".join(_ROOT_ENV_VARS) + ", last-used-cache"
    return None, (
        f"could not resolve project root — tried: {tried}. "
        f"Set PROJECT_BRAIN_HOME in your MCP config's env block, or run from "
        f"inside a git repo (cwd's .git/ ancestor is the resolved root). "
        f"Server cwd: {Path.cwd()}"
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

    Same 4-tier order as scripts/_plugin_root.sh:
      1. $PROJECT_BRAIN_PACK_ROOT
      2. $CLAUDE_PLUGIN_ROOT
      3. Auto-detect: walk up from `start` until CONVENTIONS.md + skills/ + scripts/
      4. Auto-detect: walk up from this module's location
    """
    env = os.environ.get("PROJECT_BRAIN_PACK_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        p = Path(env).resolve()
        if _looks_like_pack(p):
            return p

    for here in [start, Path(__file__).resolve().parent]:
        if here is None:
            continue
        here = Path(here).resolve()
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
