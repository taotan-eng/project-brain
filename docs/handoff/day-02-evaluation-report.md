# Day-2 Evaluation Report

- Generated: 2026-05-13T13:11:48Z
- Plan reference: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 1 day 2)
- Handoff: `docs/handoff/day-02-skill-decoupling.md`
- Day-1 audit input: `docs/handoff/day-01-cowork-audit-report.md` (103 occurrences flagged)
- Evaluator: Claude Code (opus-4-7) via `/tmp/day02-eval.sh` (corrected variant of the handoff's embedded script — see § Script adjustments below)

## Script adjustments from handoff spec

Two adjustments to the handoff's § "End-of-day evaluation" script — both documented here and in the affected criterion's evidence cell:

1. **Criterion 1 invocation pattern.** The spec uses `bash -c 'VAR=val . scripts/_plugin_root.sh && _plugin_root | grep -q ...'`. Bash's `VAR=val` prefix scopes the variable to the duration of the immediately-following command — in this case the `.` builtin. After `.` returns, the variable is gone, so the subsequent `_plugin_root` invocation runs without it and falls through to auto-detect. The helper itself is correct; the check is over-strict. Adjusted to `export VAR=val; . scripts/_plugin_root.sh; _plugin_root` which keeps the variable live across both commands. Real callers do this naturally (the agent's parent process exports the env var).
2. **`grep` invocations.** The user's interactive shell aliases `grep` to Claude Code's `ugrep` wrapper, which does not reliably accept stdin. Bare `grep -q` / `grep -c` inside the eval script silently returned empty during day-1 evaluation. Fix: every `grep` in this script is `command grep`, bypassing the alias. This is a host-environment quirk, not a project-brain issue.

## Merge criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | _plugin_root helper works in 4 modes | ✓ | flag + PROJECT_BRAIN_PACK_ROOT + CLAUDE_PLUGIN_ROOT + auto-detect all resolve correctly. Note: spec's `VAR=val . src.sh` pattern is adjusted to `export VAR=val; . src.sh` because bash drops the var after the `.` builtin returns. |
| 2 | No live ${CLAUDE_PLUGIN_ROOT} in operative code | ✓ | 0 refs in scripts/ + skills/SKILL.md outside helper / docs |
| 3 | No Cowork tool names in SKILL.md | ✓ | 0 refs in skills/ |
| 4 | Validator green | ✓ | 0 errors, 0 warnings (37 artifacts walked). |
| 5 | Smoke test end-to-end | ✓ | new-thread.sh succeeds with no Cowork env vars; thread created, indexes updated, validator clean |
| 6 | promote-thread-to-tree consent-gate preserved | ✓ | 'Forbidden' + 'Only valid value source' + '--allow-domain' all present in skills/promote-thread-to-tree/SKILL.md |
| 7 | Day-2 commits with conventional prefixes | ✓ | refactor + decouple + test all present in last 10 commits |
| 8 | No stray .bak files | ✓ | clean |

## Files changed (since day-1 evaluation report)

```
   scripts/_plugin_root.sh                |  52 ++++++++++++
   scripts/test_smoke_new_thread.sh       | 140 +++++++++++++++++++++++++++++++++
   scripts/test_verify_tree.py            |  44 +++++++++++
   scripts/verify_tree/_yaml_mini.py      |  31 +++++++-
   skills/assign-thread/SKILL.md          |  12 +--
   skills/discard-promotion/SKILL.md      |   4 +-
   skills/discard-thread/SKILL.md         |   6 +-
   skills/finalize-promotion/SKILL.md     |   2 +-
   skills/init-project-brain/SKILL.md     |  16 ++--
   skills/list-threads/SKILL.md           |   4 +-
   skills/multi-agent-debate/SKILL.md     |   4 +-
   skills/new-thread/SKILL.md             |  10 +--
   skills/park-thread/SKILL.md            |   6 +-
   skills/promote-thread-to-tree/SKILL.md |  25 +++---
   skills/record-artifact/SKILL.md        |  10 +--
   skills/restore-thread/SKILL.md         |   6 +-
   skills/review-thread/SKILL.md          |   6 +-
   skills/update-thread/SKILL.md          |   8 +-
   skills/verify-tree/SKILL.md            |   2 +-
   19 files changed, 326 insertions(+), 62 deletions(-)
```

## Commits

```
  e5cafb8 test(smoke): new-thread.sh runs host-agnostically without Cowork env vars
  af0ee54 decouple(skills): rewrite Cowork tool-name refs to host-neutral interactions
  ef3d03a refactor(scripts): introduce _plugin_root helper, drop hard-coded ${CLAUDE_PLUGIN_ROOT}
  3503a30 fix(validator): _yaml_mini double-quoted scalars preserve non-ASCII Unicode
  192cdeb docs(handoff): day-1 done — evaluation report attached
  6a1c630 docs(handoff): day-1 evaluation report — MERGE-READY
  a741257 docs(handoff): day-1 Cowork tool-name audit report
  c053035 rename: discover-threads → list-threads (safety: tab-typo collision with discard-thread)
  16a11f8 license: add Apache-2.0 NOTICE (LICENSE already in repo)
  803b858 slugs: add rename-thread-slug.sh for migrating existing ASCII slugs
```

## Verdict: **MERGE-READY**

All eight criteria pass (with two transparently documented script adjustments — see § Script adjustments above). Day-2 work is ready to merge via the day-02/skill-decoupling feature branch.
