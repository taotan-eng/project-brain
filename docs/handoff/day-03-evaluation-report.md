# Day-3 Evaluation Report

- Generated: 2026-05-13T13:56:25Z
- Plan reference: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 1 day 3)
- Handoff: `docs/handoff/day-03-mcp-server-scaffold.md`
- Predecessor: day-02 (PR #2 still open at evaluation time; this branch is stacked on it)
- MCP SDK: `mcp==1.27.1` via FastMCP high-level API; Pydantic `2.13.4`; Python 3.12.7
- Evaluator: Claude Code (opus-4-7) via `/tmp/day03-eval.sh` (corrected variant — see § Script adjustments)

## Script adjustments from handoff spec

Two adjustments to the handoff's embedded evaluation script, both transparently documented in their criterion's evidence cell:

1. **All `grep` invocations use `command grep`** to bypass the user's interactive-shell alias that routes `grep` through Claude Code's `ugrep` wrapper. The wrapper does not reliably accept stdin, so bare `grep -q` / `grep -c` inside the script silently returned empty during day-1 and day-2 evaluation. Same fix carried forward.
2. **Criterion 8 test-suite check** accepts "4 PromoteLocalTests failures and no others" as a passing baseline. Those 4 failures (`test_promote_local_archive_thread`, `test_promote_local_full`, `test_promote_local_leaves_filter_no_match_errors`, `test_promote_local_subset`) are caused by `scripts/promote-local.sh` line 179 using `declare -A` which requires bash 4+; macOS ships bash 3.2 as the default. Pre-existing from before day-1; not a day-3 regression. The 5 pre-existing `ModuleNotFoundError: No module named 'yaml'` failures from day-1/day-2 are gone (PyYAML 6.0.3 landed as a transitive dependency of the `mcp` SDK install).

## Merge criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | mcp/ scaffold present | ✓ | all 8 files present in src-layout under mcp/ |
| 2 | Package installs and imports | ✓ | ok 0.1.0 |
| 3 | MCP server starts + handshakes | ✓ | smoke test initialized server via stdio + ClientSession |
| 4 | >=3 tools wired (new_thread, list_threads, verify_tree) + run_skill fallback | ✓ | smoke test invoked new_thread + verify_tree end-to-end, Pydantic rejected empty slug |
| 5 | >=3 prompts wired (new-thread, list-threads, verify-tree) | ✓ | smoke test verified prompts/list contains all 3 |
| 6 | >=3 resources exposed (brain://thread-index, /current-state, /CONVENTIONS) | ✓ | smoke test verified resources/list + read_resource returned CONVENTIONS body |
| 7 | End-to-end smoke test passes | ✓ | scratch brain produced expected thread, verify_tree reported 0 errors |
| 8 | No regression | ✓ | validator: 0 errors, 0 warnings (37 artifacts walked).; tests: 4 baseline PromoteLocalTests failures (bash 3.2 `declare -A` incompat on macOS default bash; pre-existing from before day-1; no day-3 regressions); Cowork refs in skills/: 0 |

## Files changed (this branch since day-2 evaluation)

```
   mcp/README.md                            |  29 +++++
   mcp/pyproject.toml                       |  23 ++++
   mcp/src/project_brain_mcp/__init__.py    |   3 +
   mcp/src/project_brain_mcp/__main__.py    |  15 +++
   mcp/src/project_brain_mcp/_subprocess.py | 117 +++++++++++++++++
   mcp/src/project_brain_mcp/prompts.py     |  13 ++
   mcp/src/project_brain_mcp/resources.py   |  31 +++++
   mcp/src/project_brain_mcp/server.py      | 108 ++++++++++++++++
   mcp/src/project_brain_mcp/tools.py       |  89 +++++++++++++
   scripts/test_smoke_mcp_roundtrip.py      | 213 +++++++++++++++++++++++++++++++
   10 files changed, 641 insertions(+)
```

## Commits (this branch since day-2)

```
  20631ce test(mcp): end-to-end MCP roundtrip against scratch brain
  7bd0e05 feat(mcp): scaffold project-brain-mcp package with 4 tools, 3 prompts, 3 resources
```

## Verdict: **MERGE-READY**

All eight criteria pass (with two transparently documented script adjustments — see § Script adjustments above). Day-3 work is ready to merge via the day-03/mcp-server-scaffold feature branch.
