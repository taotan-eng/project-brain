# Day-5 Evaluation Report

- Generated: 2026-05-16T14:43:29Z
- Plan reference: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 1 day 5)
- Handoff: `docs/handoff/day-05-complex-tools-and-install.md`
- Predecessor: day-04 (PR #4 marked MERGED in gh; commits live on `origin/day-03/mcp-server-scaffold` tip but did NOT propagate to `origin/main`. Day-5 branched from `origin/day-03/mcp-server-scaffold` to inherit the full day-1+2+3+4 cumulative state.)
- Week 1 finale: this evaluation closes out week 1 of v1.0.
- Refreshed against branch tip `6fa207e` after the post-demo hotfix arc (six commits: `bae248e` → `6fa207e`) plus the four plumbing commits (`c6c7e45`, `38069b5`, `f4da8c2`, `e199d28`). The earlier auto-generated report was stale before these landed.

## Script adjustments from handoff spec

Three adjustments to the handoff's embedded evaluation script, all transparently documented:

1. **All `grep` invocations use `command grep`** to bypass the user's interactive-shell alias that routes `grep` through Claude Code's `ugrep` wrapper. Carried forward from day-1, day-2, day-3, day-4.
2. **Criterion 8 test-suite check** accepts "4 PromoteLocalTests failures and no others" as a passing baseline. Those 4 failures are caused by `scripts/promote-local.sh:179` using `declare -A` (bash 4+); macOS ships bash 3.2. Pre-existing from before day-1. Same exclusion pattern as day-3/4.
3. **Criterion 3 evolved during execution.** The original handoff spec assumed `force=True` as the existing-brain override path. Day-5 hotfix iteration (commits `bae248e` through `6fa207e`) collapsed `init_project_brain` to a zero-arg tool: no `target`, no `force`, no `owner`, no `primary_project` on the wire. Pre-existing brain at the resolved root now returns `validation_error` with a hint to manually clean up; there is no `force` escape. Criterion 3 below carries the revised wording. The handoff doc itself is preserved as the historical plan record.

## Merge criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | 3 new complex tools wired (17 total) | ✓ | 17 tools registered |
| 2 | promote_thread_to_tree consent gate intact | ✓ | Pydantic rejects missing AND empty allow_domain |
| 3 | init_project_brain existence check | ✓ | `InitProjectBrainArgs` has zero fields (no `target`, no `force`). When the resolved project root already contains `project-brain/CONVENTIONS.md`, the tool returns `error.code == "validation_error"` with a hint instructing the user to manually remove or move the existing directory and retry. No `force` escape — manual cleanup is the only path. Smoke test exercises both the success path (no pre-existing brain) and the existence-check failure path. Re-verified in-process against branch tip 6fa207e: planted marker at `<tmp>/project-brain/CONVENTIONS.md` → `{ok=False, error.code=validation_error, message contains "Brain already exists"}`. |
| 4 | materialize_context wired | ✓ | Args model + impl importable; @app.tool decorator present in server.py; smoke test exercises it (script-not-yet-implemented tolerated) |
| 5 | INSTALL.md present + structurally complete | ✓ | 3 sections, mcpServers JSON, uvx command, Claude config path, PROJECT_BRAIN_HOME env var all present |
| 6 | Demo evidence captured | ✓ | `docs/demos/day-05-claude-desktop-install.md` filled in by Tom on the host: list_threads call produced the active-thread inventory (day-5-gate, mcp-demo, test-mcp-brain); new_thread call landed `threads/mcp-demo/` on disk with `decisions-candidates.md`, `open-questions.md`, `thread.md`. Step-4 / Step-5 / directory-listing sections all carry real evidence rather than placeholder text. Remaining `_<fill in>_` markers in the frontmatter (date, Claude Desktop version, OS, MCP SDK version) are metadata, not blocking. |
| 7 | Extended smoke test passes (>=9 tools + consent + init guards) | ✓ | 10 distinct tools exercised |
| 8 | No regression | ✓ | validator: 0 errors, 0 warnings (44 artifacts walked).; tests: 4 baseline PromoteLocalTests failures (bash 3.2 declare -A; pre-existing); no new failures; cowork=0, discover-threads=0, bad-test=0 |

## Files changed (this branch since day-4 close)

```
   INSTALL.md                                       | 203 +++++
   README.md                                        |   2 +
   docs/demos/day-05-claude-desktop-install.md      |  49 ++
   docs/handoff/_evaluation-report-template.md      | 162 ++++
   docs/handoff/day-01-license-rename-audit.md      |  15 +-
   docs/handoff/day-05-complex-tools-and-install.md | 975 +++++++++++++++++++++++
   docs/handoff/day-06-chatgpt-codex-config.md      | 691 ++++++++++++++++
   mcp/src/project_brain_mcp/_subprocess.py         | 130 +++
   mcp/src/project_brain_mcp/resources.py           |  16 +-
   mcp/src/project_brain_mcp/server.py              | 112 ++-
   mcp/src/project_brain_mcp/tools.py               | 332 +++++++-
   scripts/smoke_mcp_roundtrip.py                   | 417 +++++++++-
   12 files changed, 3037 insertions(+), 67 deletions(-)
```

## Commits (this branch since day-4 close)

```
  e199d28 docs(handoff): stage day-5 plan, day-6 plan, and eval template
  f4da8c2 chore(handoff): fix LICENSE end-marker check in day-01 retro
  38069b5 docs(readme): add 'two operational models' paragraph (CLI vs chat-app install)
  c6c7e45 docs(demo): capture day-5 Claude Desktop install evidence
  6fa207e fix(mcp): collapse init_project_brain to a zero-arg tool
  e286701 test(mcp): clear last-used-root cache before chain-exhaustion assertion
  4f98668 fix(mcp): server-side resolution chain for project root
  58d3a60 fix(mcp): auto-derive primary_project from target leaf when omitted
  536a36f fix(mcp): unify PROJECT_BRAIN_HOME as project root, not brain dir (Path C)
  bae248e fix(mcp): default brain to $PROJECT_BRAIN_HOME for everyday tools
  566c1d4 docs(demo): day-5 Claude Desktop install demo skeleton
  f9fa2db test(mcp): extend smoke test to cover 3 day-5 complex tools
  4de3ecf docs: add INSTALL.md MCP-server sections (Install / Claude Desktop config / Verify)
  66b4559 feat(mcp): wire 3 complex tools (init_project_brain, promote_thread_to_tree, materialize_context)
```

## Verdict: **MERGE-READY**

All eight criteria pass against branch tip `6fa207e` (with the three transparently documented script adjustments — see § Script adjustments above). Week 1 of the v1.0 release is complete: the MCP server has 17 tools, 17 prompts, 3 resources, a structured-error contract, a 7-step server-side resolution chain for the project root, a zero-arg `init_project_brain`, an end-user install path documented in `INSTALL.md`, and a verified Claude Desktop demo. Day-6 (ChatGPT Desktop + Codex CLI MCP config) is staged in `docs/handoff/day-06-chatgpt-codex-config.md`, ready for the next handoff once this PR merges.
