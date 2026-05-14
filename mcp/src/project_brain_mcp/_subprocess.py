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


def resolve_brain(arg: str | None) -> tuple[str | None, str | None]:
    """Resolve the brain path from an arg or $PROJECT_BRAIN_HOME.

    Returns `(brain_path, error_message)`. On success, `error_message` is
    None and `brain_path` is the resolved string. On failure (neither
    supplied), `brain_path` is None and `error_message` describes the gap.

    Caller pattern in *_impl:

        brain, err_msg = resolve_brain(args.brain)
        if err_msg:
            return err("validation_error", err_msg,
                       hint="set PROJECT_BRAIN_HOME in your MCP config's env block, or pass brain=<path>")
        # use `brain` (not args.brain) in argv-building
    """
    if arg and arg.strip():
        return arg.strip(), None
    env = os.environ.get("PROJECT_BRAIN_HOME", "").strip()
    if env:
        return env, None
    return None, "brain not specified and PROJECT_BRAIN_HOME env var not set"


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
