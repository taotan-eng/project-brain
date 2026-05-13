"""End-to-end smoke test — MCP server roundtrip against a scratch brain.

Spawns the `project-brain-mcp` server as a stdio subprocess, connects an
MCP client, and exercises one full roundtrip:

  1. initialize
  2. tools/list   — must include new_thread, list_threads, verify_tree, run_skill
  3. prompts/list — must include new-thread, list-threads, verify-tree
  4. resources/list — must include the 3 brain:// URIs
  5. tools/call new_thread (valid args) — succeeds, thread lands on disk
  6. tools/call verify_tree — reports 0 errors
  7. tools/call new_thread (empty slug) — Pydantic rejects before subprocess

Pass condition: every assertion above holds. Exit 0 prints
'MCP SMOKE TEST PASSED'.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


SCRIPT_DIR = Path(__file__).resolve().parent
PACK_ROOT = SCRIPT_DIR.parent


def _scaffold_brain(root: Path) -> None:
    """Create a minimal brain that passes verify-tree.py."""
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


async def _run() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="mcp-smoke-"))
    brain = tmp / "brain"
    try:
        _scaffold_brain(brain)

        # Strip every host-specific env var so we're testing the host-neutral
        # path. The server resolves the pack root via _subprocess.find_pack_root
        # which falls through to auto-detect from the module's location.
        env = {k: v for k, v in os.environ.items()
               if k not in {
                   "CLAUDE_PLUGIN_ROOT",
                   "PROJECT_BRAIN_PACK_ROOT",
                   "COWORK_WORKSPACE_FOLDER",
                   "CODEX_PROJECT_ROOT",
                   "CLAUDE_PROJECT_ROOT",
               }}
        env["PROJECT_BRAIN_HOME"] = str(brain)

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "project_brain_mcp"],
            env=env,
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 2. tools/list
                tools_resp = await session.list_tools()
                tool_names = {t.name for t in tools_resp.tools}
                expected_tools = {"new_thread", "list_threads", "verify_tree", "run_skill"}
                missing = expected_tools - tool_names
                assert not missing, f"missing tools: {missing}; got {tool_names}"

                # 3. prompts/list
                prompts_resp = await session.list_prompts()
                prompt_names = {p.name for p in prompts_resp.prompts}
                expected_prompts = {"new-thread", "list-threads", "verify-tree"}
                missing = expected_prompts - prompt_names
                assert not missing, f"missing prompts: {missing}; got {prompt_names}"

                # 4. resources/list
                resources_resp = await session.list_resources()
                uris = {str(r.uri) for r in resources_resp.resources}
                expected_uris = {
                    "brain://thread-index",
                    "brain://current-state",
                    "brain://CONVENTIONS",
                }
                missing = expected_uris - uris
                assert not missing, f"missing resources: {missing}; got {uris}"

                # 5. tools/call new_thread with valid args
                call_resp = await session.call_tool(
                    "new_thread",
                    arguments={
                        "brain": str(brain),
                        "slug": "smoke-mcp-thread",
                        "title": "Smoke MCP thread",
                        "purpose": "MCP roundtrip smoke",
                        "primary_project": "smoketest",
                        "owner": "smoke@example.com",
                    },
                )
                assert not call_resp.isError, f"new_thread tool call returned error: {call_resp}"
                thread_dir = brain / "threads" / "smoke-mcp-thread"
                assert thread_dir.is_dir(), f"thread dir not created at {thread_dir}"
                thread_md = (thread_dir / "thread.md").read_text()
                assert "id: smoke-mcp-thread" in thread_md, \
                    f"thread.md missing expected id; first lines:\n{thread_md[:300]}"

                # 6. tools/call verify_tree against the same scratch brain
                verify_resp = await session.call_tool(
                    "verify_tree",
                    arguments={"brain": str(brain)},
                )
                assert not verify_resp.isError, f"verify_tree errored: {verify_resp}"
                verify_text = "\n".join(
                    c.text for c in verify_resp.content if hasattr(c, "text")
                )
                assert "0 errors" in verify_text, \
                    f"verify_tree did not report 0 errors. Got:\n{verify_text[:500]}"

                # 7. tools/call new_thread with empty slug — Pydantic rejection
                bad_resp = await session.call_tool(
                    "new_thread",
                    arguments={
                        "brain": str(brain),
                        "slug": "",
                        "title": "x",
                        "purpose": "x",
                        "primary_project": "smoketest",
                    },
                )
                assert bad_resp.isError, \
                    "Pydantic should have rejected empty slug; got non-error response"

                # 8. resource read returns the file content
                res_resp = await session.read_resource("brain://CONVENTIONS")
                conv_text = "\n".join(
                    c.text for c in res_resp.contents if hasattr(c, "text")
                )
                assert "Smoke conventions" in conv_text, \
                    f"CONVENTIONS resource content unexpected: {conv_text[:200]}"

        print("MCP SMOKE TEST PASSED")
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


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
