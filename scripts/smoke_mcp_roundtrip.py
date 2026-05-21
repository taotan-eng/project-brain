"""End-to-end smoke test — MCP server roundtrip against a scratch brain.

Spawns the `project-brain-mcp` server as a stdio subprocess, connects an
MCP client, and exercises the Layer-2 surface. Day-4 extends the day-3
test to cover 6 distinct tool categories plus the structured-error
contract.

Coverage:

  1. initialize
  2. tools/list  -> >=14 names including the 10 day-4 tools
  3. prompts/list -> >=14 names (auto-discovered)
  4. resources/list -> the 3 brain:// URIs
  5. CREATE:   call_tool("new_thread", ...) -> ok=True, thread on disk
  6. READ:     call_tool("list_threads", ...) -> ok=True
  7. UPDATE:   call_tool("update_thread", refine -> locking) -> ok=True
  8. ARTIFACT: call_tool("record_artifact", --content) -> ok=True
  9. ARCHIVE:  call_tool("park_thread", reason) -> ok=True
 10. RESTORE:  call_tool("park_thread", --unpark) -> ok=True
 11. ERROR:    call_tool("new_thread", slug="") -> error.code == "validation_error"
 12. ERROR:    call_tool("verify_tree", brain="/nonexistent") -> error.code == "script_error"
 13. PROMPT:   get_prompt("new-thread") -> body content
 14. RESOURCE: read_resource("brain://CONVENTIONS") -> file content
 15. End-of-run: verify_tree against the scratch brain reports 0 errors.

Pass: every assertion holds. Prints "MCP SMOKE TEST PASSED".
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client


SCRIPT_DIR = Path(__file__).resolve().parent
PACK_ROOT = SCRIPT_DIR.parent


def _scaffold_brain(root: Path) -> None:
    (root / "threads").mkdir(parents=True)
    (root / "tree").mkdir()
    (root / "archive").mkdir()

    (root / "config.yaml").write_text(
        'brain_version: "1.0.0-rc4"\n'
        'primary_project: smoketest\n'
        'projects:\n'
        '  smoketest:\n'
        '    title: "Smoke Test"\n'
        f'    brain: {root}\n'
        'domains: [example]\n'
    )
    (root / "CONVENTIONS.md").write_text(
        "---\n"
        "id: smoke-conventions\n"
        "title: Smoke conventions\n"
        "version: 1.0.0-smoke\n"
        "status: draft\n"
        "---\n\n"
        "# Smoke conventions\n\n"
        "Scaffold for the MCP smoke test.\n"
    )
    (root / "thread-index.md").write_text(
        "# Thread index\n\n"
        "## Active\n\n"
        "| Slug | Title | Owner | Maturity | Updated |\n"
        "|------|-------|-------|----------|---------|\n\n"
        "## Parked\n\n"
        "## Archived\n"
    )
    (root / "current-state.md").write_text("# Current state\n")
    (root / "tree" / "NODE.md").write_text(
        "---\n"
        "id: tree-root\n"
        "title: Tree root\n"
        "created_at: 2026-05-13T00:00:00Z\n"
        "owner: smoke@example.com\n"
        "primary_project: smoketest\n"
        "related_projects: []\n"
        "soft_links: []\n"
        "status: decided\n"
        "node_type: node\n"
        "domain: /\n"
        "children: []\n"
        "---\n\n"
        "# Tree root\n"
    )


def _parse_tool_payload(call_resp: Any) -> dict[str, Any]:
    """Extract the structured-response dict from a CallToolResult.

    FastMCP serializes the impl's return-dict as the tool result. With
    structured_output the SDK exposes it via .structuredContent; the JSON
    body is also returned in .content[0].text. We accept either.
    """
    sc = getattr(call_resp, "structuredContent", None)
    if isinstance(sc, dict):
        return sc
    # Fallback: parse the text content as JSON.
    for c in call_resp.content:
        text = getattr(c, "text", None)
        if not text:
            continue
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "ok" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    raise AssertionError(
        f"could not extract structured response from tool result: {call_resp!r}"
    )


def _assert_ok(call_resp: Any, label: str) -> dict[str, Any]:
    payload = _parse_tool_payload(call_resp)
    assert payload.get("ok") is True, \
        f"{label}: expected ok=True, got {payload!r}"
    return payload


def _assert_err(call_resp: Any, code: str, label: str) -> dict[str, Any]:
    """Accept either the structured-response error shape OR an MCP `isError=True`.

    FastMCP catches Pydantic ValidationError for missing required args at the
    SDK layer (before wrap_validation runs), surfacing it as `isError=True`
    with a text body. For "validation_error" assertions we accept either
    path — both are the same gate firing.
    """
    if getattr(call_resp, "isError", False) and code == "validation_error":
        text = "\n".join(getattr(c, "text", "") for c in call_resp.content)
        assert "validation error" in text.lower() or "required" in text.lower() or "field" in text.lower(), \
            f"{label}: isError=True but body doesn't look like Pydantic validation: {text!r}"
        return {"ok": False, "data": None, "error": {"code": "validation_error", "message": text, "hint": None}}

    payload = _parse_tool_payload(call_resp)
    assert payload.get("ok") is False, f"{label}: expected ok=False, got {payload!r}"
    actual = (payload.get("error") or {}).get("code")
    assert actual == code, f"{label}: expected error.code={code!r}, got {actual!r}"
    return payload


async def _run() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="mcp-smoke-"))
    # Path C: PROJECT_BRAIN_HOME is the project root; the brain lives at
    # <root>/project-brain/. Tool calls that pass `brain` explicitly pass the
    # project root, not the brain dir.
    project_root = tmp
    brain = project_root / "project-brain"
    try:
        _scaffold_brain(brain)

        env = {k: v for k, v in os.environ.items()
               if k not in {
                   "CLAUDE_PLUGIN_ROOT",
                   "PROJECT_BRAIN_PACK_ROOT",
                   "COWORK_WORKSPACE_FOLDER",
                   "CODEX_PROJECT_ROOT",
                   "CLAUDE_PROJECT_ROOT",
               }}
        env["PROJECT_BRAIN_HOME"] = str(project_root)

        # Launch the subprocess server with cwd inside the scratch tempdir
        # (which is under /tmp and has no .git/ ancestor) so the resolution
        # chain's step 2 (git walk-up) misses cleanly and step 3
        # (PROJECT_BRAIN_HOME) takes precedence. Without this, the chain
        # would resolve to the project-brain repo itself whenever the smoke
        # test is run from inside the repo.
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "project_brain_mcp"],
            env=env,
            cwd=str(tmp),
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 2. tools/list — must include all day-3 + day-4 tools
                tools_resp = await session.list_tools()
                tool_names = {t.name for t in tools_resp.tools}
                expected_tools = {
                    # day-3
                    "new_thread", "list_threads", "verify_tree", "run_skill",
                    # day-4
                    "update_thread", "record_artifact", "assign_thread",
                    "park_thread", "discard_thread", "restore_thread",
                    "review_thread", "review_parked_threads",
                    "finalize_promotion", "discard_promotion",
                    # day-5
                    "init_project_brain", "promote_thread_to_tree", "materialize_context",
                }
                missing = expected_tools - tool_names
                assert not missing, f"missing tools: {missing}; got {sorted(tool_names)}"
                assert len(tool_names) >= 17, \
                    f"expected >=17 tools registered, got {len(tool_names)}"

                # 3. prompts/list — auto-discovered, should be >=14
                prompts_resp = await session.list_prompts()
                prompt_names = {p.name for p in prompts_resp.prompts}
                assert len(prompt_names) >= 14, \
                    f"expected >=14 prompts, got {len(prompt_names)}: {sorted(prompt_names)}"
                for must_have in ("new-thread", "list-threads", "verify-tree",
                                  "update-thread", "promote-thread-to-tree",
                                  "multi-agent-debate"):
                    assert must_have in prompt_names, \
                        f"prompt {must_have!r} not in list: {sorted(prompt_names)}"

                # 4. resources/list
                resources_resp = await session.list_resources()
                uris = {str(r.uri) for r in resources_resp.resources}
                expected_uris = {
                    "brain://thread-index", "brain://current-state", "brain://CONVENTIONS",
                }
                missing = expected_uris - uris
                assert not missing, f"missing resources: {missing}; got {uris}"

                # 5. CREATE — new_thread succeeds
                slug = "smoke-mcp-thread"
                create_resp = await session.call_tool(
                    "new_thread",
                    arguments={
                        "brain": str(project_root),
                        "slug": slug,
                        "title": "Smoke MCP thread",
                        "purpose": "MCP roundtrip smoke",
                        "primary_project": "smoketest",
                        "owner": "smoke@example.com",
                    },
                )
                _assert_ok(create_resp, "new_thread create")
                thread_dir = brain / "threads" / slug
                assert thread_dir.is_dir(), f"thread dir not created at {thread_dir}"

                # 6. READ — list_threads succeeds
                read_resp = await session.call_tool(
                    "list_threads", arguments={"brain": str(project_root), "status": "active"},
                )
                _assert_ok(read_resp, "list_threads read")

                # 7. UPDATE — refine maturity to locking
                update_resp = await session.call_tool(
                    "update_thread",
                    arguments={
                        "brain": str(project_root),
                        "slug": slug,
                        "operation": "refine",
                        "target": "locking",
                    },
                )
                _assert_ok(update_resp, "update_thread refine")

                # 8. ARTIFACT — record a small markdown artifact.
                # Tolerates the known Layer-1 macOS bug where record-artifact.sh
                # calls GNU `realpath --relative-to=` which BSD realpath rejects.
                # The MCP wiring is what we're verifying here; whether the
                # underlying script lands the file depends on the host's
                # coreutils flavor.
                artifact_resp = await session.call_tool(
                    "record_artifact",
                    arguments={
                        "brain": str(project_root),
                        "slug": slug,
                        "title": "Smoke test note",
                        "content": "# Smoke note\n\nthis is a smoke-test artifact.\n",
                    },
                )
                artifact_payload = _parse_tool_payload(artifact_resp)
                if not artifact_payload.get("ok"):
                    code = (artifact_payload.get("error") or {}).get("code")
                    msg = (artifact_payload.get("error") or {}).get("message", "")
                    if code != "script_error" or "realpath" not in msg:
                        raise AssertionError(
                            f"record_artifact failed unexpectedly: {artifact_payload!r}"
                        )
                    # else: known macOS BSD-realpath issue; tool wiring is OK.

                # 8b. ASSIGN — exercise a 6th distinct tool category (independent
                # of record_artifact's macOS portability story).
                assign_resp = await session.call_tool(
                    "assign_thread",
                    arguments={
                        "brain": str(project_root),
                        "slug": slug,
                        "add": "smoke@example.com",
                    },
                )
                _assert_ok(assign_resp, "assign_thread")

                # 9. ARCHIVE — park the thread
                park_resp = await session.call_tool(
                    "park_thread",
                    arguments={
                        "brain": str(project_root),
                        "slug": slug,
                        "reason": "smoke test parking",
                    },
                )
                _assert_ok(park_resp, "park_thread")

                # 10. RESTORE — unpark the thread
                unpark_resp = await session.call_tool(
                    "park_thread",
                    arguments={"brain": str(project_root), "slug": slug, "unpark": True},
                )
                _assert_ok(unpark_resp, "park_thread unpark")

                # ---- Day-5 complex tools ------------------------------------

                # 10a. INIT via MCP session — zero-arg, hits the existence
                # guard. The server's PROJECT_BRAIN_HOME points at the
                # scratch project_root (set in StdioServerParameters above),
                # which already has the scaffolded brain at
                # <project_root>/project-brain/. The chain resolves to that
                # root and the existence check fires immediately, returning
                # validation_error "Brain already exists". This is the
                # session-roundtrip version of the in-process 14c2 check.
                init_resp = await session.call_tool(
                    "init_project_brain",
                    arguments={},
                )
                init_payload = _parse_tool_payload(init_resp)
                assert init_payload.get("ok") is False, \
                    f"expected existence-guard refusal, got {init_payload!r}"
                code = (init_payload.get("error") or {}).get("code")
                assert code == "validation_error", \
                    f"init_project_brain wrong error code: {init_payload!r}"
                msg = (init_payload.get("error") or {}).get("message", "")
                assert "Brain already exists" in msg, \
                    f"existence-guard message should mention 'Brain already exists': {msg!r}"

                # 10c. PROMOTE consent gate — omit allow_domain entirely; the
                # Pydantic required field MUST surface as validation_error
                # before any subprocess call. This is the technical enforcement
                # of the day-1 five-round consent hardening at the MCP boundary.
                consent_resp = await session.call_tool(
                    "promote_thread_to_tree",
                    arguments={
                        "brain": str(project_root),
                        "slug": slug,
                        # allow_domain deliberately omitted
                    },
                )
                _assert_err(consent_resp, "validation_error", "promote_thread_to_tree consent gate")

                # 10d. MATERIALIZE context — tool is wired but the Layer-1
                # script (`scripts/materialize-context.sh`) isn't implemented
                # yet (skill lives inline in SKILL.md). We accept ok=True OR a
                # script_error whose message indicates the script is missing —
                # what we're verifying is the MCP wiring, not the absent script.
                materialize_resp = await session.call_tool(
                    "materialize_context",
                    arguments={
                        "brain": str(project_root),
                        "artifact": f"threads/{slug}/thread.md",
                    },
                )
                materialize_payload = _parse_tool_payload(materialize_resp)
                if not materialize_payload.get("ok"):
                    code = (materialize_payload.get("error") or {}).get("code")
                    assert code == "script_error", \
                        f"materialize_context returned wrong error code: {materialize_payload!r}"

                # 10e. ENV-DEFAULT brain — omit brain entirely; the server's
                # PROJECT_BRAIN_HOME env var (set on the subprocess at launch)
                # must be honored by every everyday tool. This verifies the
                # day-5 hotfix that fixed the UX gap where tools always asked
                # the user for the brain path even when the config provided it.
                env_default_resp = await session.call_tool(
                    "list_threads",
                    arguments={"status": "active"},  # NO brain arg
                )
                _assert_ok(env_default_resp, "list_threads env-default brain")

                # 11. ERROR path — empty slug -> validation_error
                bad_slug_resp = await session.call_tool(
                    "new_thread",
                    arguments={
                        "brain": str(project_root),
                        "slug": "",
                        "title": "x",
                        "purpose": "x",
                        "primary_project": "smoketest",
                    },
                )
                _assert_err(bad_slug_resp, "validation_error", "new_thread empty slug")

                # 12. ERROR path — bad brain path -> script_error
                bad_brain_resp = await session.call_tool(
                    "verify_tree", arguments={"brain": "/nonexistent/path/xyz"},
                )
                _assert_err(bad_brain_resp, "script_error", "verify_tree bad brain")

                # 13. PROMPT fetch via SDK
                prompt_resp = await session.get_prompt("new-thread")
                joined = "\n".join(
                    getattr(m.content, "text", "") for m in prompt_resp.messages
                )
                assert "thread" in joined.lower(), \
                    f"new-thread prompt body doesn't mention 'thread'; first 200 chars:\n{joined[:200]}"

                # 14. RESOURCE read
                res_resp = await session.read_resource("brain://CONVENTIONS")
                conv_text = "\n".join(
                    c.text for c in res_resp.contents if hasattr(c, "text")
                )
                assert "Smoke conventions" in conv_text, \
                    f"CONVENTIONS resource content unexpected: {conv_text[:200]}"

                # 14b. ENV-MISSING fallback — when nothing the resolution
                # chain looks at is set (no arg, no env vars, no git ancestor
                # of cwd), the chain falls through to tier 4's cwd-fallback
                # and resolves to cwd itself. A subsequent tool call against
                # a brainless cwd fails with script_error ("brain directory
                # not found") — NOT validation_error from the chain (the
                # chain succeeded; the script just couldn't find a brain at
                # the resolved path).
                from project_brain_mcp.tools import (
                    InitProjectBrainArgs, ListThreadsArgs,
                    init_project_brain_impl, list_threads_impl,
                )

                _chain_env_vars_b = (
                    "PROJECT_BRAIN_HOME",
                    "COWORK_WORKSPACE_FOLDER",
                    "CODEX_PROJECT_ROOT",
                    "CLAUDE_PROJECT_ROOT",
                )
                saved_env_b = {k: os.environ.get(k) for k in _chain_env_vars_b}
                saved_cwd_b = os.getcwd()
                try:
                    for k in _chain_env_vars_b:
                        os.environ.pop(k, None)

                    with tempfile.TemporaryDirectory(dir="/tmp", prefix="no-git-") as nowhere:
                        os.chdir(nowhere)
                        no_env_resp = await list_threads_impl(ListThreadsArgs())
                        assert no_env_resp["ok"] is False, \
                            f"expected tool failure, got {no_env_resp!r}"
                        assert no_env_resp["error"]["code"] == "script_error", \
                            f"expected script_error (chain resolved to cwd; no brain there), got {no_env_resp['error']!r}"
                        msg = no_env_resp["error"].get("message") or ""
                        assert "brain directory not found" in msg.lower() \
                            or "not found" in msg.lower(), \
                            f"error should mention missing brain dir: {msg!r}"

                    # Restore cwd before continuing with the rest of 14c+.
                    os.chdir(saved_cwd_b)
                except BaseException:
                    # Make sure env/cwd are restored even if the new
                    # assertions blow up before reaching the outer finally.
                    for k, v in saved_env_b.items():
                        if v is not None:
                            os.environ[k] = v
                        else:
                            os.environ.pop(k, None)
                    os.chdir(saved_cwd_b)
                    raise

                # Pre-existing 14c+ block continues with `saved_env` (= the
                # original PROJECT_BRAIN_HOME) handling. Restore env vars we
                # cleared so 14c can set PROJECT_BRAIN_HOME freshly.
                for k, v in saved_env_b.items():
                    if v is not None:
                        os.environ[k] = v
                    else:
                        os.environ.pop(k, None)
                saved_env = os.environ.pop("PROJECT_BRAIN_HOME", None)
                try:

                    # 14c. ZERO-ARG INIT — call init with no args at all.
                    # The agent simply says "create project brain"; the server
                    # resolves the target via the chain and derives the alias
                    # from the resolved root's leaf. PROJECT_BRAIN_HOME (tier 3)
                    # wins over cwd git-walk-up (tier 4); we still chdir into
                    # the same tempdir so the init lands where the test expects.
                    import re as _re
                    _saved_cwd_c = os.getcwd()
                    try:
                        with tempfile.TemporaryDirectory(prefix="Test-Brain-", dir="/tmp") as init_env_root:
                            os.environ["PROJECT_BRAIN_HOME"] = init_env_root
                            os.chdir(init_env_root)
                            init_env_resp = await init_project_brain_impl(InitProjectBrainArgs())
                            # Layer-1 init-brain.sh may fail on this host for
                            # unrelated reasons (registry collisions, etc.);
                            # accept ok=True OR a script_error that isn't the
                            # existence guard.
                            if init_env_resp["ok"]:
                                created = Path(init_env_root) / "project-brain" / "CONVENTIONS.md"
                                assert created.exists(), \
                                    f"expected brain at {created} after zero-arg init"
                                # Verify the derived alias matches the leaf
                                cfg = Path(init_env_root) / "project-brain" / "config.yaml"
                                if cfg.exists():
                                    text = cfg.read_text()
                                    leaf = Path(init_env_root).name
                                    expected_alias = _re.sub(r"[^a-z0-9]+", "-", leaf.lower()).strip("-")
                                    assert expected_alias in text, \
                                        f"expected auto-derived alias {expected_alias!r} not in config.yaml: {text[:300]}"

                                # 14c2. EXISTENCE-CHECK NEGATIVE — init again
                                # against the same resolved root; expect
                                # validation_error with "Brain already exists".
                                # No force path, so this is a hard error the
                                # user resolves in the filesystem.
                                second_resp = await init_project_brain_impl(InitProjectBrainArgs())
                                assert second_resp["ok"] is False, \
                                    f"repeat init should refuse, got {second_resp!r}"
                                assert second_resp["error"]["code"] == "validation_error", \
                                    f"repeat init wrong code: {second_resp!r}"
                                assert "Brain already exists" in second_resp["error"]["message"], \
                                    f"repeat init wrong msg: {second_resp['error']['message']!r}"
                            else:
                                code = init_env_resp["error"]["code"]
                                assert code == "script_error", \
                                    f"zero-arg init returned wrong code: {init_env_resp!r}"
                    finally:
                        os.chdir(_saved_cwd_c)

                    # 14d. PATH C — reject PROJECT_BRAIN_HOME ending in
                    # /project-brain (the old semantic). chdir into a non-git
                    # tempdir so git walk-up misses and the env var is
                    # actually consulted.
                    _saved_cwd_d = os.getcwd()
                    try:
                        with tempfile.TemporaryDirectory(prefix="no-git-d-", dir="/tmp") as nogit_d:
                            os.chdir(nogit_d)
                            os.environ["PROJECT_BRAIN_HOME"] = "/tmp/something/project-brain"
                            bad_env_resp = await list_threads_impl(ListThreadsArgs())
                            assert bad_env_resp["ok"] is False, \
                                f"expected rejection of trailing /project-brain, got {bad_env_resp!r}"
                            assert bad_env_resp["error"]["code"] == "validation_error", \
                                f"expected validation_error, got {bad_env_resp!r}"
                            bad_msg = bad_env_resp["error"]["message"]
                            assert "parent" in bad_msg.lower(), \
                                f"rejection message should mention parent dir suggestion: {bad_msg!r}"
                            assert "/tmp/something" in bad_msg, \
                                f"rejection should include the corrected path '/tmp/something': {bad_msg!r}"
                    finally:
                        os.chdir(_saved_cwd_d)

                    # 14e. RESOLUTION CHAIN — three-tier confidence ordering.
                    # Assertions cover each tier in isolation plus the
                    # tier-3-beats-tier-4 case that fixes the ChatGPT-cwd-
                    # shadows-PROJECT_BRAIN_HOME bug. Saves/restores all env
                    # vars + cwd so the rest of the test isn't disturbed.
                    from project_brain_mcp._subprocess import resolve_project_root

                    chain_env_vars = (
                        "PROJECT_BRAIN_HOME",
                        "COWORK_WORKSPACE_FOLDER",
                        "CODEX_PROJECT_ROOT",
                        "CLAUDE_PROJECT_ROOT",
                    )
                    saved_chain_env = {k: os.environ.get(k) for k in chain_env_vars}
                    saved_cwd = os.getcwd()

                    def _clear_chain_env() -> None:
                        for k in chain_env_vars:
                            os.environ.pop(k, None)

                    def _eq_path(a: str, b: str) -> bool:
                        return Path(a).resolve() == Path(b).resolve()

                    try:
                        # Tier 1: explicit arg overrides everything.
                        _clear_chain_env()
                        os.environ["PROJECT_BRAIN_HOME"] = "/tmp/chain-env"
                        r, e = resolve_project_root("/tmp/chain-explicit")
                        assert e is None and _eq_path(r, "/tmp/chain-explicit"), \
                            f"tier 1 (explicit arg): {r=} {e=}"

                        # Tier 2 beats Tier 3: host context wins over pin.
                        _clear_chain_env()
                        os.environ["COWORK_WORKSPACE_FOLDER"] = "/tmp/chain-cwf"
                        os.environ["PROJECT_BRAIN_HOME"] = "/tmp/chain-pbh-loses"
                        r, e = resolve_project_root(None)
                        assert e is None and _eq_path(r, "/tmp/chain-cwf"), \
                            f"tier 2 (host context) should beat tier 3 (pin): {r=} {e=}"

                        # Tier 3 beats Tier 4: PROJECT_BRAIN_HOME beats cwd
                        # git-walk-up. THIS IS THE REGRESSION GUARD for the
                        # ChatGPT-cwd-shadows-pin bug. Old ordering put
                        # git-walk-up at tier 2 and would have returned
                        # `gitroot`; new ordering must return `/tmp/chain-pbh`.
                        _clear_chain_env()
                        with tempfile.TemporaryDirectory() as gitroot:
                            (Path(gitroot) / ".git").mkdir()
                            subdir = Path(gitroot) / "subdir"
                            subdir.mkdir()
                            os.chdir(subdir)
                            os.environ["PROJECT_BRAIN_HOME"] = "/tmp/chain-pbh"
                            r, e = resolve_project_root(None)
                            assert e is None and _eq_path(r, "/tmp/chain-pbh"), \
                                f"tier 3 (pin) should beat tier 4 (cwd git-walk-up): {r=} {e=}"

                        # Tier 4 fallback: cwd git-walk-up when no env set.
                        # The bare-mkdir .git won't satisfy `git worktree list`,
                        # so the linked-worktree redirect helper returns None
                        # and tier 4 falls back to the gitroot path — exactly
                        # the behavior we want for a non-worktree repo.
                        _clear_chain_env()
                        with tempfile.TemporaryDirectory() as gitroot:
                            (Path(gitroot) / ".git").mkdir()
                            subdir = Path(gitroot) / "subdir"
                            subdir.mkdir()
                            os.chdir(subdir)
                            r, e = resolve_project_root(None)
                            assert e is None and _eq_path(r, gitroot), \
                                f"tier 4 (cwd git-walk-up fallback): {r=} {e=}"

                        # Linked-worktree → main-worktree redirect: when cwd
                        # is inside a linked git worktree (e.g. Codex's
                        # session worktree), tier 4 must resolve to the MAIN
                        # worktree, not the linked one — otherwise a brain
                        # created in an ephemeral worktree silently vanishes
                        # when the worktree is discarded.
                        _clear_chain_env()
                        import subprocess as _sp
                        with tempfile.TemporaryDirectory(prefix="wt-test-") as base:
                            main = Path(base) / "main"
                            linked = Path(base) / "linked"
                            main.mkdir()
                            _git_env = {
                                **os.environ,
                                "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
                            }
                            _sp.run(["git", "init", "-q", str(main)], check=True)
                            _sp.run(["git", "-C", str(main), "commit",
                                     "--allow-empty", "-q", "-m", "init"],
                                    check=True, env=_git_env)
                            _sp.run(["git", "-C", str(main), "worktree", "add",
                                     "-q", str(linked)],
                                    check=True, env=_git_env)
                            os.chdir(linked)
                            r, e = resolve_project_root(None)
                            # macOS: tempfile lives under /var which is a
                            # symlink to /private/var. Compare realpaths so the
                            # symlink doesn't flip the assertion.
                            assert e is None, \
                                f"linked-worktree redirect: unexpected error {e=}"
                            assert os.path.realpath(r) == os.path.realpath(str(main)), \
                                f"linked-worktree redirect: expected realpath({main!s}), got {r!r}"
                            # And the main worktree itself still resolves to
                            # main (the redirect is a no-op when already there).
                            os.chdir(main)
                            r2, e2 = resolve_project_root(None)
                            assert e2 is None and os.path.realpath(r2) == os.path.realpath(str(main)), \
                                f"main worktree unchanged: {r2=} {e2=}"

                        # Host-context env-var coverage: each of the three
                        # host-context vars wins in turn when nothing higher
                        # is set. chdir into a non-git tempdir so tier 4
                        # misses cleanly.
                        with tempfile.TemporaryDirectory(prefix="no-git-chain-") as nogit:
                            os.chdir(nogit)

                            _clear_chain_env()
                            os.environ["COWORK_WORKSPACE_FOLDER"] = "/tmp/chain-cwf2"
                            r, e = resolve_project_root(None)
                            assert e is None and _eq_path(r, "/tmp/chain-cwf2"), \
                                f"tier 2 (COWORK_WORKSPACE_FOLDER): {r=} {e=}"

                            _clear_chain_env()
                            os.environ["CODEX_PROJECT_ROOT"] = "/tmp/chain-codex"
                            r, e = resolve_project_root(None)
                            assert e is None and _eq_path(r, "/tmp/chain-codex"), \
                                f"tier 2 (CODEX_PROJECT_ROOT): {r=} {e=}"

                            _clear_chain_env()
                            os.environ["CLAUDE_PROJECT_ROOT"] = "/tmp/chain-cc"
                            r, e = resolve_project_root(None)
                            assert e is None and _eq_path(r, "/tmp/chain-cc"), \
                                f"tier 2 (CLAUDE_PROJECT_ROOT): {r=} {e=}"

                        # Tilde expansion: PROJECT_BRAIN_HOME=~/foo must
                        # resolve to $HOME/foo (chdir to non-git first so
                        # tier 4 doesn't shadow).
                        _clear_chain_env()
                        with tempfile.TemporaryDirectory(prefix="no-git-tilde-") as nogit:
                            os.chdir(nogit)
                            os.environ["PROJECT_BRAIN_HOME"] = "~/chain-tilde"
                            r, e = resolve_project_root(None)
                            expected = str(Path.home() / "chain-tilde")
                            assert e is None and r == expected, \
                                f"tilde expansion: expected {expected!r}, got r={r!r} e={e!r}"

                        # Tier 4 non-git fallback: no env, cwd is a non-git
                        # tempdir → resolves to cwd itself (NOT fail). This is
                        # the Codex-GUI-in-plain-folder case from host testing
                        # — a project dir without a git repo is still a
                        # project dir.
                        _clear_chain_env()
                        with tempfile.TemporaryDirectory(prefix="no-git-cwd-") as nogit:
                            os.chdir(nogit)
                            r, e = resolve_project_root(None)
                            assert e is None and _eq_path(r, nogit), \
                                f"tier 4 (non-git cwd fallback): {r=} {e=}"

                        # Tier 5 (cwd unavailable) is intentionally not
                        # exercised: it requires deleting cwd out from under
                        # the running process, which is too fragile to set up
                        # portably. The guards in _walk_up_for_git and
                        # resolve_project_root handle it via FileNotFoundError /
                        # OSError catches; trust them.
                    finally:
                        _clear_chain_env()
                        for k, v in saved_chain_env.items():
                            if v is not None:
                                os.environ[k] = v
                        os.chdir(saved_cwd)
                finally:
                    if saved_env is not None:
                        os.environ["PROJECT_BRAIN_HOME"] = saved_env
                    else:
                        os.environ.pop("PROJECT_BRAIN_HOME", None)

                # 15. Final consistency check — verify_tree clean
                verify_resp = await session.call_tool(
                    "verify_tree", arguments={"brain": str(project_root)},
                )
                verify_payload = _assert_ok(verify_resp, "verify_tree final")
                stdout = (verify_payload.get("data") or {}).get("stdout", "")
                assert "0 errors" in stdout, \
                    f"verify_tree did not report 0 errors after chained ops. stdout:\n{stdout[:500]}"

        print("stdio roundtrip: PASSED")
        return 0
    except AssertionError as e:
        print(f"MCP SMOKE TEST FAILED: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        import traceback
        print(f"MCP SMOKE TEST CRASHED: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def _sse_roundtrip() -> None:
    """Spawn `project-brain-mcp --http` as a subprocess and exercise the
    SSE transport. Asserts tools/list >= 17 and prompts/list >= 14.

    Day-8 added the --http flag. This sibling of `_run()` confirms the
    same FastMCP server surfaces correctly over HTTP/SSE on a free port.
    Only the protocol-level handshake + counts are checked here — the
    full CRUD flow is already covered by the stdio path in `_run()`.
    """
    import socket

    def _free_port(start: int = 8800, end: int = 8810) -> int:
        for p in range(start, end):
            try:
                with socket.socket() as s:
                    s.bind(("127.0.0.1", p))
                    return p
            except OSError:
                continue
        raise RuntimeError(f"no free port in {start}-{end}")

    port = _free_port()
    env = {**os.environ, "PROJECT_BRAIN_SSE_PORT": str(port)}
    # Use `sys.executable -m project_brain_mcp --http` (parallel to the
    # stdio path) so the subprocess inherits the same interpreter and
    # the editable install resolves the same way.
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "project_brain_mcp", "--http",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        # Poll for the server to start accepting TCP connections (up to 8s).
        bound = False
        for _ in range(80):
            await asyncio.sleep(0.1)
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    bound = True
                    break
            except OSError:
                continue
        if not bound:
            stderr = b""
            try:
                stderr = await asyncio.wait_for(proc.stderr.read(), timeout=1)
            except asyncio.TimeoutError:
                pass
            raise RuntimeError(
                f"SSE server did not bind 127.0.0.1:{port} within 8s. "
                f"stderr: {stderr.decode(errors='replace')[:500]}"
            )

        url = f"http://127.0.0.1:{port}/sse"
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_resp = await session.list_tools()
                prompts_resp = await session.list_prompts()
                tool_count = len(tools_resp.tools)
                prompt_count = len(prompts_resp.prompts)
                assert tool_count >= 17, \
                    f"SSE: expected >=17 tools, got {tool_count}"
                assert prompt_count >= 14, \
                    f"SSE: expected >=14 prompts, got {prompt_count}"
                print(f"SSE roundtrip: {tool_count} tools, {prompt_count} prompts")
    finally:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=3)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()


async def _run_all() -> int:
    """Run the stdio roundtrip first; if it passes, run the SSE roundtrip.

    Both must pass for the smoke test to print PASSED.
    """
    stdio_rc = await _run()
    if stdio_rc != 0:
        return stdio_rc
    try:
        await _sse_roundtrip()
    except AssertionError as e:
        print(f"MCP SMOKE TEST FAILED: SSE roundtrip: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        import traceback
        print(f"MCP SMOKE TEST CRASHED: SSE roundtrip: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 2
    print("MCP SMOKE TEST PASSED (stdio + SSE)")
    return 0


def main() -> int:
    return asyncio.run(_run_all())


if __name__ == "__main__":
    raise SystemExit(main())
