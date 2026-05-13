# Day-4 Evaluation Report

- Generated: 2026-05-13T14:38:38Z
- Plan reference: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 1 day 4)
- Handoff: `docs/handoff/day-04-mcp-tool-coverage.md`
- Predecessor: day-03 (PR #3 marked MERGED in gh; commits live on `origin/day-03/mcp-server-scaffold` but did not propagate to `origin/main`. Day-4 stacked on day-3 branch tip; see Execution log.)
- MCP SDK: `mcp==1.27.1` via FastMCP; Pydantic `2.13.4`; Python 3.12.7
- Evaluator: Claude Code (opus-4-7) via `/tmp/day04-eval.sh` (corrected variant — see § Script adjustments)

## Script adjustments from handoff spec

Two adjustments to the handoff's embedded evaluation script, both transparently documented in the affected criterion's evidence cell:

1. **All `grep` invocations use `command grep`** to bypass the user's interactive-shell alias that routes `grep` through Claude Code's `ugrep` wrapper. The wrapper doesn't reliably accept stdin. Carried forward from day-1, day-2, and day-3.
2. **Criterion 7 (test suite)** accepts "4 PromoteLocalTests failures and no others" as a passing baseline. Those 4 failures (in `scripts/test_verify_tree.py`) are caused by `scripts/promote-local.sh:179` using `declare -A` which requires bash 4+; macOS ships bash 3.2 as default. Pre-existing from before day-1; not a day-4 regression. Same exclusion-pattern as day-3 criterion 8.

## Merge criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | 13 tools wired with Pydantic schemas | ✓ | 14 tools registered |
| 2 | Prompts auto-discovered (one per skill) | ✓ | 17 prompts registered for 17 skills |
| 3 | Structured error shape with closed code set | ✓ | _response.py present; ok/err/from_subprocess_result helpers; closed-set enforcement verified |
| 4 | Extended smoke test passes (>=6 tools + error paths) | ✓ | 6 distinct tools exercised; 3 error-path assertions |
| 5 | Subprocess invariants preserved | ✓ | shell=False in helper; no direct subprocess calls in tools.py |
| 6 | Validator green | ✓ | 0 errors, 0 warnings (37 artifacts walked). |
| 7 | Test suite green (modulo bash 3.2 baseline) | ✓ | 4 baseline PromoteLocalTests failures (bash 3.2 `declare -A` incompat on macOS default bash); no new day-4 failures |
| 8 | No regression (Cowork refs, discover-threads, test_*.py smoke pattern) | ✓ | 0 Cowork refs in skills/, 0 live discover-threads refs, 0 bad test_*.py smoke files |

## Files changed (this branch since day-3 closure)

```
   mcp/src/project_brain_mcp/_response.py |  76 +++++++++
   mcp/src/project_brain_mcp/prompts.py   |  27 ++-
   mcp/src/project_brain_mcp/server.py    | 234 +++++++++++++++++++++-----
   mcp/src/project_brain_mcp/tools.py     | 296 ++++++++++++++++++++++++++++++++-
   scripts/smoke_mcp_roundtrip.py         | 233 +++++++++++++++++++++-----
   5 files changed, 768 insertions(+), 98 deletions(-)
```

## Commits (this branch since day-3 closure)

```
  af30b82 test(mcp): extend smoke test to >=6 tools + structured-error assertions
  8510bf2 feat(mcp): expand to 14 tools + 17 auto-discovered prompts + structured errors
```

## Verdict: **MERGE-READY**

All eight criteria pass (with two transparently documented script adjustments — see § Script adjustments above). Day-4 work is ready to merge via the day-04/mcp-tool-coverage feature branch.
