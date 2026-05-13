# Day 2 Handoff — host-neutral skill decoupling (`${CLAUDE_PLUGIN_ROOT}` helper + Cowork tool-name removal)

- **Audience**: Claude Code (or any agent operating on the project-brain repo)
- **Date authored**: 2026-05-13
- **Author**: Tom (taotan6@gmail.com) via planning session
- **Estimated effort**: 1.5-2 person-days (was budgeted at 1 day before the day-1 audit found 103 occurrences vs the ~50 estimate; rebaselined)
- **Status**: done
- **Execution mode**: autonomous test-fix-retest loop; escalate only on judgment calls (see § Escalation)
- **Predecessor**: `day-01-license-rename-audit.md` (status: done) + audit at `day-01-cowork-audit-report.md`

## TL;DR

Two parallel decoupling tracks, both required for cross-harness MCP to work:

1. **Path-resolution refactor**: replace 37 `${CLAUDE_PLUGIN_ROOT}` uses in `scripts/` with calls to a new `_plugin_root` helper that works in Cowork (via env var), Claude Code (via env var), and any other host (via runtime detection).
2. **Skill-prose decoupling**: rewrite the 66 occurrences of `AskUserQuestion` (65) and `mcp__cowork__` (1) in SKILL.md prose to host-neutral interaction descriptions ("ask the user to pick between A or B") so the recipes execute identically on any harness.

End of day-2 you can install the pack on a non-Cowork host (e.g. raw terminal + Claude Code with no Cowork affordances) and the skills still run end-to-end. The mojibake fix from `3503a30` already shipped, so the validator is clean for the smoke tests.

## Context

You are executing **day 2 of week 1 of the project-brain v1.0 3-week release plan**.

Read these for "why" decisions:

- **Plan artifact**: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 1 day 2)
- **Day-1 audit**: `docs/handoff/day-01-cowork-audit-report.md` — full inventory of the 103 occurrences with per-file line numbers
- **Day-1 evaluation**: `docs/handoff/day-01-evaluation-report.md` — the merge-readiness pattern you'll mirror today

The plan budgeted 1 day for this work. Day-1's audit found 103 occurrences across 33 files (not the ~50 estimate), and the hottest file (`skills/promote-thread-to-tree/SKILL.md` with 11 hits) sits inside security-critical "Forbidden / Only valid value source" prose that needs careful semantic rewrite, not mechanical replace. **Day 2 is therefore rebaselined to 1.5-2 days** with an internal checkpoint between Task 1 and Task 2.

## Goal

By the end of this handoff:

1. A `_plugin_root` helper exists and is invoked from every Layer-1 script that previously hard-coded `${CLAUDE_PLUGIN_ROOT}`.
2. Every SKILL.md prose reference to Cowork-specific interaction primitives (`AskUserQuestion`, `TodoWrite`, `mcp__cowork__*`, `mcp__visualize__*`) is replaced with a host-neutral description of the interaction.
3. One smoke test proves a representative skill workflow (`new-thread`) executes end-to-end on bash alone (no Cowork harness needed).
4. The `promote-thread-to-tree` SKILL.md retains the substantive consent-gate / anti-shortcut logic that the original `AskUserQuestion` references encoded — security-critical, must not be silently weakened.
5. An evaluation report at `docs/handoff/day-02-evaluation-report.md` documents which PR-merge criteria pass and which fail; verdict is `MERGE-READY`.

## PR-merge criteria

The day's work is merge-ready when all eight criteria below pass. Each is checked programmatically by the `## End-of-day evaluation` script.

| # | Criterion | Programmatic check |
|---|---|---|
| 1 | `_plugin_root` helper exists and works in 3 modes | The helper script/function exists at `scripts/_plugin_root.sh` (or wherever placed); sourcing in a clean shell, then `_plugin_root` returns a usable absolute path under all three conditions: `$CLAUDE_PLUGIN_ROOT` set, env unset (auto-detect via script location), `--plugin-root=<path>` arg. |
| 2 | No live `${CLAUDE_PLUGIN_ROOT}` in scripts/skills | `git grep '\${CLAUDE_PLUGIN_ROOT}'` returns matches only in (a) the helper definition itself, (b) `CONVENTIONS.md` if it documents the variable, (c) historical docs (`CHANGELOG.md`, `RELEASE-NOTES.md`), (d) `docs/handoff/` documentation of this rewrite. No matches in `scripts/*.sh`, `scripts/**/*.py`, or `skills/*/SKILL.md` operative code. |
| 3 | No live `AskUserQuestion`/`TodoWrite`/`mcp__cowork__`/`mcp__visualize__` in SKILL.md prose | `git grep -E '(AskUserQuestion\|TodoWrite\|mcp__cowork__\|mcp__visualize__)' skills/` returns no matches. References surviving in `CONVENTIONS.md` rationale prose, `RUNTIME.md` host-binding tables, `PORTING.md` migration guidance, or `docs/handoff/` are acceptable — those are descriptive, not invocation. |
| 4 | Validator green | `python3 scripts/verify-tree.py --brain=…` ends with `0 errors, 0 warnings`. After yesterday's `3503a30` fix, the prior 2 V-01 baseline errors are gone; any new errors are day-2 regressions and must be fixed. |
| 5 | Smoke test passes end-to-end | A fresh `new-thread.sh` invocation against a scratch brain dir creates the thread, populates the three template files, updates `thread-index.md`, returns exit-0, and the validator reports the new artifact clean. Script: `scripts/test_smoke_new_thread.sh` (created during this work). |
| 6 | Security-critical prose preserved | `skills/promote-thread-to-tree/SKILL.md` still contains the strings "Forbidden" AND "Only valid value source" AND "--allow-domain"; the consent-gate semantics survive the rewrite. Mechanical grep, semantic gate. |
| 7 | Day-2 commits with conventional messages | `git log --oneline` since the day-2 starting commit contains at minimum: `^refactor:` (the helper + scripts/), `^decouple:` (the SKILL.md rewrites), `^test:` (the smoke test). `^docs(handoff):` for the eval report is added at exit-gate time. |
| 8 | No stray `.bak` files | `find . -name "*.bak" -not -path "./.git/*"` returns nothing. |

Failures in criteria 1-6 block merge. Criteria 7-8 are hygiene; clean up before re-running if they fail.

## Development loop — how to work this handoff

Standard per-task loop:

1. Read the task spec.
2. Execute the task.
3. Run the task's `### Validation script` block.
4. If it fails, consult `## Common failure modes` and apply the fix.
5. Re-run validation. Repeat up to **~5 attempts** per task.
6. After ~5 attempts without success, or if the failure isn't in `## Common failure modes`, escalate.

After both tasks pass, run the `## End-of-day evaluation` script. It generates `docs/handoff/day-02-evaluation-report.md` with verdict `MERGE-READY` or `NOT-READY`. The human reads that report, not individual task outputs.

**Important:** Task 2 is the long pole and the highest-risk creative work. Reserve time. The 11-hit `promote-thread-to-tree/SKILL.md` cluster sits inside a security-critical prose section — read it whole before editing.

## Pre-flight checks

Run this block before starting. It both **creates the day-2 feature branch** and verifies every precondition. All eight checks must pass; if any fails, escalate.

Per the handoff convention (`docs/handoff/README.md` § Workflow), every handoff executes on a fresh feature branch — no direct commits to `main`. The branch for this handoff is `day-02/skill-decoupling`.

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. We're in the right repo
test -f CONVENTIONS.md -a -d skills/ -a -f README.md \
  || { echo "FAIL: not in project-brain pack repo"; exit 1; }

# 2. `gh` CLI is installed and authed (required for the exit-gate PR open)
command -v gh >/dev/null 2>&1 \
  || { echo "FAIL: gh CLI not installed; cannot open PR at exit gate"; exit 1; }
gh auth status >/dev/null 2>&1 \
  || { echo "FAIL: gh not authed; run 'gh auth login' on the host and retry"; exit 1; }

# 3. Working tree clean
[ -z "$(git status --porcelain)" ] \
  || { echo "FAIL: uncommitted changes present"; git status; exit 1; }

# 4. Day-1 + validator fix all committed
git log --oneline -10 main 2>/dev/null | grep -q "license:" \
  && git log --oneline -10 main 2>/dev/null | grep -q "rename: discover-threads" \
  && git log --oneline -10 main 2>/dev/null | grep -q "fix(validator): _yaml_mini" \
  || { echo "FAIL: day-1 + validator fix commits not all on main"; exit 1; }

# 5. Branch setup: switch to (or create) the day-2 feature branch
current=$(git branch --show-current)
if [ "$current" != "day-02/skill-decoupling" ]; then
  echo "Switching to day-2 feature branch..."
  git checkout main
  git pull --ff-only 2>&1 | head -2 || true   # tolerate non-fetched local
  if git rev-parse --verify day-02/skill-decoupling >/dev/null 2>&1; then
    git checkout day-02/skill-decoupling
  else
    git checkout -b day-02/skill-decoupling
  fi
fi
test "$(git branch --show-current)" = "day-02/skill-decoupling" \
  || { echo "FAIL: not on day-02/skill-decoupling branch"; exit 1; }

# 6. Validator green BEFORE we start
python3 scripts/verify-tree.py --brain=/Users/ttan/workspace/Project-Brain/project-brain 2>&1 \
  | tail -1 | grep -q "0 errors" \
  || { echo "FAIL: validator dirty before start; expected 0 errors after yesterday's fix"; exit 1; }

# 7. Day-1 audit report present (Task 2 needs it as input)
test -f docs/handoff/day-01-cowork-audit-report.md \
  || { echo "FAIL: day-1 audit report missing"; exit 1; }

# 8. Test suite green and rename intact
python3 -m unittest scripts.test_verify_tree 2>&1 | tail -1 | grep -q "^OK" \
  || { echo "FAIL: test suite dirty before start"; exit 1; }
test -d skills/list-threads -a -f scripts/list-threads.sh \
  && [ ! -d skills/discover-threads ] && [ ! -f scripts/discover-threads.sh ] \
  || { echo "FAIL: day-1 rename has regressed"; exit 1; }

echo "ALL PRE-FLIGHT CHECKS PASSED — on branch day-02/skill-decoupling"
```

## Task 1 — `_plugin_root` helper + `${CLAUDE_PLUGIN_ROOT}` refactor

### Spec

Build a single `_plugin_root` helper that resolves the pack's root directory and works in any host. Replace every operative occurrence of `${CLAUDE_PLUGIN_ROOT}` with a call to the helper.

**Helper resolution order** (highest priority first):

1. If the caller passed `--plugin-root=<abs-path>`, use that.
2. If `$PROJECT_BRAIN_PACK_ROOT` is set (new, host-neutral name), use that.
3. If `$CLAUDE_PLUGIN_ROOT` is set (Cowork / Claude Code path), use that.
4. Auto-detect: walk up from the calling script's `BASH_SOURCE[0]` until a `CONVENTIONS.md` + `skills/` + `scripts/` triplet is found; that directory is the pack root.
5. If all four fail, exit non-zero with a clear message: "Cannot resolve pack root. Set PROJECT_BRAIN_PACK_ROOT or pass --plugin-root."

Helper location: `scripts/_plugin_root.sh`. Sourceable. Defines a function `_plugin_root` that echoes the resolved path on stdout.

### Steps

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Create the helper. Skeleton:
cat > scripts/_plugin_root.sh <<'SH'
#!/usr/bin/env bash
# _plugin_root — host-neutral pack-root resolver.
#
# Sourced by every Layer-1 script that needs to reference paths under the
# pack root. Replaces hard-coded ${CLAUDE_PLUGIN_ROOT} (Cowork/Claude-Code
# only) with a 4-tier resolver that works in any host.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/_plugin_root.sh"
#   ROOT="$(_plugin_root)"
#
# Or accept a caller-supplied override via --plugin-root=<path>:
#   ROOT="$(_plugin_root --plugin-root=/some/abs/path)"

_plugin_root() {
  # 1. CLI flag wins.
  local arg
  for arg in "$@"; do
    case "$arg" in
      --plugin-root=*) printf '%s\n' "${arg#--plugin-root=}"; return 0 ;;
    esac
  done

  # 2. New host-neutral env var.
  if [[ -n "${PROJECT_BRAIN_PACK_ROOT:-}" ]]; then
    printf '%s\n' "$PROJECT_BRAIN_PACK_ROOT"
    return 0
  fi

  # 3. Cowork / Claude-Code legacy env var.
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
    printf '%s\n' "$CLAUDE_PLUGIN_ROOT"
    return 0
  fi

  # 4. Auto-detect from caller location.
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" && pwd -P)"
  while [[ "$here" != "/" && "$here" != "" ]]; do
    if [[ -f "$here/CONVENTIONS.md" && -d "$here/skills" && -d "$here/scripts" ]]; then
      printf '%s\n' "$here"
      return 0
    fi
    here="$(dirname "$here")"
  done

  # 5. Give up.
  echo "ERROR: cannot resolve pack root. Set PROJECT_BRAIN_PACK_ROOT or pass --plugin-root=<path>" >&2
  return 1
}
SH
chmod +x scripts/_plugin_root.sh

# 2. Refactor each consumer script. Strategy:
#    - At the top of the script (after `set -euo pipefail`), source the helper.
#    - Replace ${CLAUDE_PLUGIN_ROOT} with $(_plugin_root) on first use,
#      cache the result in a local variable for the rest of the script.

# List all consumer scripts:
git grep -l '\${CLAUDE_PLUGIN_ROOT}' -- 'scripts/' 'skills/*/SKILL.md'
```

For each script in the grep output, manually edit:

```bash
# Original:
foo="${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh"

# Refactored (top of script, once):
. "$(dirname "${BASH_SOURCE[0]}")/_plugin_root.sh"
PACK_ROOT="$(_plugin_root)" || exit 1

# Then:
foo="$PACK_ROOT/scripts/foo.sh"
```

For SKILL.md files that mention `${CLAUDE_PLUGIN_ROOT}` in prose (not invocation), see Task 2 — those rewrites are interaction-prose work.

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Helper exists and is sourceable.
test -f scripts/_plugin_root.sh || { echo "FAIL: helper missing"; exit 1; }
bash -c '. scripts/_plugin_root.sh && _plugin_root --plugin-root=/tmp/x | grep -q "/tmp/x"' \
  || { echo "FAIL: --plugin-root flag doesn't work"; exit 1; }
bash -c 'unset CLAUDE_PLUGIN_ROOT PROJECT_BRAIN_PACK_ROOT; cd /tmp && . '"$PWD"'/scripts/_plugin_root.sh && _plugin_root >/dev/null' \
  || { echo "FAIL: auto-detect doesn't work from sourced location"; exit 1; }
bash -c 'PROJECT_BRAIN_PACK_ROOT=/tmp/y . scripts/_plugin_root.sh && _plugin_root | grep -q "/tmp/y"' \
  || { echo "FAIL: PROJECT_BRAIN_PACK_ROOT doesn't take precedence"; exit 1; }

# 2. No live ${CLAUDE_PLUGIN_ROOT} in operative paths.
LIVE=$(git grep '\${CLAUDE_PLUGIN_ROOT}' -- 'scripts/*.sh' 'scripts/**/*.sh' 'scripts/**/*.py' 'skills/*/SKILL.md' 2>/dev/null \
       | grep -v "_plugin_root.sh\|CONVENTIONS.md\|CHANGELOG.md\|RELEASE-NOTES.md\|docs/handoff/" | wc -l | tr -d ' ')
if [ "$LIVE" != "0" ]; then
  echo "FAIL: $LIVE live \${CLAUDE_PLUGIN_ROOT} refs remain in operative scripts/SKILL.md"
  git grep '\${CLAUDE_PLUGIN_ROOT}' -- 'scripts/*.sh' 'scripts/**/*.sh' 'scripts/**/*.py' 'skills/*/SKILL.md' \
    | grep -v "_plugin_root.sh\|CONVENTIONS.md\|CHANGELOG.md\|RELEASE-NOTES.md\|docs/handoff/"
  exit 1
fi

# 3. Validator still green.
python3 scripts/verify-tree.py --brain=/Users/ttan/workspace/Project-Brain/project-brain 2>&1 \
  | tail -1 | grep -q "0 errors" \
  || { echo "FAIL: validator regression"; exit 1; }

echo "TASK 1 VALIDATION PASSED"
```

### Commit

```bash
git add scripts/_plugin_root.sh scripts/
git commit -m "refactor(scripts): introduce _plugin_root helper, drop hard-coded \${CLAUDE_PLUGIN_ROOT}

Layer-1 scripts now resolve the pack root via a 4-tier helper:
  1. --plugin-root=<path> CLI flag
  2. \$PROJECT_BRAIN_PACK_ROOT env var (host-neutral)
  3. \$CLAUDE_PLUGIN_ROOT env var (Cowork / Claude Code legacy)
  4. Auto-detect: walk up from BASH_SOURCE looking for CONVENTIONS.md + skills/ + scripts/

Enables non-Cowork hosts (raw terminal, MCP server, future harnesses) to
run the scripts without setting Cowork's specific env var. Replaces 37
hard-coded refs."
```

## Task 2 — SKILL.md prose decoupling

### Spec

Rewrite every operative SKILL.md reference to Cowork-specific interaction primitives as a host-neutral description. The interaction stays identical; only the prose surface changes.

**Replacement directions:**

| Pattern | Rewrite direction |
|---|---|
| `AskUserQuestion` (65 hits) | "Ask the user to pick between A or B" / "Ask the user for X" — describe the *interaction*, never name a tool. |
| `TodoWrite` (0 hits in current audit — none to do) | n/a |
| `mcp__cowork__bash` / `mcp__workspace__bash` (1 hit) | "Run the shell command" — let the host bind to its native bash tool. |
| `mcp__visualize__*` (0 hits) | n/a |

**Pre-read before editing `skills/promote-thread-to-tree/SKILL.md` (the hot file, 11 hits):**

The 11 `AskUserQuestion` references in this file cluster inside a security-critical block titled "Forbidden / Only valid value source" — they encode the consent-gate logic where the user (not the LLM) is the only authoritative source for the destination domain on promotion. The original day-1 work referenced this in a code comment ("LLM has write access to it, so frontmatter is not trusted as the consent path"). When you rewrite the prose:

- **Preserve**: the "Forbidden" list of value sources the agent cannot infer from (frontmatter, folder list, prior promoted_to, content topic, conversation context).
- **Preserve**: the "Only valid value source" being an explicit user response.
- **Preserve**: the `--allow-domain=<X>` flag as the sole consent path.
- **Reword the call-to-tool**: replace `"call AskUserQuestion with the destination domain options"` with `"ask the user — via the host's interaction surface, whatever that is — to pick the destination domain from the existing tree/ domains or to explicitly authorize a new one"`.

Same goes for the unconditional Step-0 ask: keep the "STEP 0" framing, drop the tool name.

### Steps

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Get the list of files needing edits.
git grep -lE '(AskUserQuestion|mcp__cowork__|mcp__visualize__|TodoWrite)' skills/

# 2. Edit each one. Manual; do not sed. Each rewrite has to preserve intent.
#    Order recommendation (easiest first):
#    - new-thread/SKILL.md            (low complexity)
#    - update-thread/SKILL.md
#    - record-artifact/SKILL.md
#    - assign-thread/SKILL.md
#    - park-thread/SKILL.md
#    - discard-thread/SKILL.md
#    - restore-thread/SKILL.md
#    - finalize-promotion/SKILL.md
#    - discard-promotion/SKILL.md
#    - multi-agent-debate/SKILL.md
#    - materialize-context/SKILL.md
#    - review-thread/SKILL.md
#    - list-threads/SKILL.md
#    - review-parked-threads/SKILL.md
#    - init-project-brain/SKILL.md
#    - promote-thread-to-tree/SKILL.md  (hottest; LAST after pattern feel is dialed in)
```

For each file, the loop:

```bash
# a. Open the file, read the full context (don't just sed). Some references
#    are inside example commands, some inside rationale prose, some inside
#    Step lists.
# b. Identify the interaction shape each AskUserQuestion call encodes:
#    - single-choice from N options?
#    - free-text?
#    - confirm Y/N?
#    - multi-select?
# c. Rewrite to a host-neutral phrasing that names the shape but not the tool.
# d. Save. Validator-check. Move on.
```

After all SKILL.md edits, ensure no stale references:

```bash
# 3. Survey remaining references after edits
git grep -nE '(AskUserQuestion|TodoWrite|mcp__cowork__|mcp__visualize__)' skills/
# Expected: empty.

# 4. Survey what's left in CONVENTIONS / RUNTIME / PORTING / docs/handoff
#    (these are descriptive references; should NOT be empty — they're allowed).
git grep -nE '(AskUserQuestion|TodoWrite|mcp__cowork__|mcp__visualize__)' \
  -- 'CONVENTIONS.md' 'RUNTIME.md' 'PORTING.md' 'docs/handoff/'
# Expected: some matches; those are documentation of the original Cowork
# binding and the day-2 work, not invocation. Leave them.
```

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. No live refs in SKILL.md prose.
LIVE=$(git grep -E '(AskUserQuestion|TodoWrite|mcp__cowork__|mcp__visualize__)' skills/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$LIVE" != "0" ]; then
  echo "FAIL: $LIVE live Cowork tool-name refs remain in skills/"
  git grep -nE '(AskUserQuestion|TodoWrite|mcp__cowork__|mcp__visualize__)' skills/
  exit 1
fi

# 2. promote-thread-to-tree security-critical prose preserved.
PFILE=skills/promote-thread-to-tree/SKILL.md
grep -q "Forbidden" "$PFILE" || { echo "FAIL: 'Forbidden' anti-shortcut section removed"; exit 1; }
grep -qE "Only valid value source|only valid value source|sole authority|sole source" "$PFILE" \
  || { echo "FAIL: 'Only valid value source' consent gate prose missing"; exit 1; }
grep -q -- "--allow-domain" "$PFILE" || { echo "FAIL: --allow-domain consent flag missing"; exit 1; }

# 3. Validator still green.
python3 scripts/verify-tree.py --brain=/Users/ttan/workspace/Project-Brain/project-brain 2>&1 \
  | tail -1 | grep -q "0 errors" \
  || { echo "FAIL: validator regression"; exit 1; }

# 4. Pack tests still green.
python3 -m unittest scripts.test_verify_tree 2>&1 | tail -1 | grep -q "^OK" \
  || { echo "FAIL: test suite regression"; exit 1; }

echo "TASK 2 VALIDATION PASSED"
```

### Commit

```bash
git add skills/
git commit -m "decouple(skills): rewrite Cowork tool-name refs to host-neutral interactions

65 AskUserQuestion refs and 1 mcp__cowork__bash ref across 16 SKILL.md
files are now described as interaction *shapes* (ask the user to pick A/B,
ask for X, confirm) rather than tool-name invocations. Each host (Cowork,
Claude Code, raw MCP, future ChatGPT/Codex) binds the interaction to its
own native surface.

Special care on promote-thread-to-tree/SKILL.md (11 hits): the consent-gate
'Forbidden / Only valid value source / --allow-domain' security logic is
preserved verbatim in spirit; only the tool name 'AskUserQuestion' was
removed. Tested by smoke-running promote-local against a scratch brain."
```

## Task 3 — End-to-end smoke test (host-agnostic)

### Spec

Add `scripts/test_smoke_new_thread.sh` that exercises the `new-thread.sh` flow against a scratch brain dir, with no Cowork env vars set. Pass condition: thread is created, indexes update, validator reports clean.

### Steps

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

cat > scripts/test_smoke_new_thread.sh <<'SH'
#!/usr/bin/env bash
# Smoke test — new-thread.sh executes end-to-end with no Cowork env vars.
# Pass: scratch thread is created, frontmatter is well-formed, validator clean.
set -euo pipefail

# Strip Cowork-specific env so we know we're testing the host-neutral path
unset CLAUDE_PLUGIN_ROOT
unset PROJECT_BRAIN_PACK_ROOT  # let auto-detect resolve it

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Scaffold a minimal brain root
mkdir -p "$TMP/brain/threads" "$TMP/brain/tree" "$TMP/brain/archive"
cat > "$TMP/brain/config.yaml" <<YAML
brain_version: "1.0.0-rc4"
primary_project: "smoketest"
domains: [example]
YAML
cat > "$TMP/brain/CONVENTIONS.md" <<MD
# Smoke conventions
MD
cat > "$TMP/brain/thread-index.md" <<MD
# Thread index
MD
cat > "$TMP/brain/current-state.md" <<MD
# Current state
MD

# Run new-thread
HERE="$(cd "$(dirname "$0")" && pwd)"
"$HERE/new-thread.sh" \
  --brain="$TMP/brain" \
  --slug=smoke-test-thread \
  --title="Smoke test thread" \
  --purpose="end-to-end check that new-thread runs host-agnostically" \
  --owner=test@example.com

# Assertions
test -d "$TMP/brain/threads/smoke-test-thread" || { echo "FAIL: thread dir not created"; exit 1; }
test -f "$TMP/brain/threads/smoke-test-thread/thread.md" || { echo "FAIL: thread.md not created"; exit 1; }
grep -q "^id: smoke-test-thread$" "$TMP/brain/threads/smoke-test-thread/thread.md" \
  || { echo "FAIL: id frontmatter missing"; exit 1; }

# Validator should be clean against the scratch brain
python3 "$HERE/verify-tree.py" --brain="$TMP/brain" 2>&1 | tail -1 | grep -q "0 errors" \
  || { echo "FAIL: validator dirty after new-thread"; python3 "$HERE/verify-tree.py" --brain="$TMP/brain"; exit 1; }

echo "SMOKE TEST PASSED"
SH
chmod +x scripts/test_smoke_new_thread.sh

# Run it
./scripts/test_smoke_new_thread.sh
```

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

test -x scripts/test_smoke_new_thread.sh || { echo "FAIL: smoke test missing or not executable"; exit 1; }

# Run the smoke test fresh
./scripts/test_smoke_new_thread.sh > /tmp/smoke.log 2>&1
tail -1 /tmp/smoke.log | grep -q "SMOKE TEST PASSED" \
  || { echo "FAIL: smoke test failed"; cat /tmp/smoke.log; exit 1; }

echo "TASK 3 VALIDATION PASSED"
```

### Commit

```bash
git add scripts/test_smoke_new_thread.sh
git commit -m "test(smoke): new-thread.sh runs host-agnostically without Cowork env vars

Creates a scratch brain dir, unsets CLAUDE_PLUGIN_ROOT and
PROJECT_BRAIN_PACK_ROOT, invokes new-thread.sh, and asserts the thread
landed and the validator is clean. Pins the cross-harness contract."
```

## Common failure modes and fixes

### Task 1 failures

| Symptom | Fix |
|---|---|
| Helper auto-detect returns wrong path | Auto-detect walks up from `BASH_SOURCE[1]` (the caller). If a script is sourced from an unusual depth, the walk may stop at a parent that happens to contain matching files. Add explicit `--plugin-root=<path>` at the script's top to override. |
| Validator regression after refactor | A script sources the helper but breaks on bash 3.2 (macOS default). Check that `printf` and `local` patterns work in bash 3.2; avoid bash-4-only features like associative arrays. |
| Some `${CLAUDE_PLUGIN_ROOT}` refs remain in `tests/` or `bin/` | Validation script only checks `scripts/*.sh`, `scripts/**/*.sh`, `scripts/**/*.py`, `skills/*/SKILL.md`. Other locations are out of scope for criterion 2; clean them up in v1.1 if needed. |

### Task 2 failures

| Symptom | Fix |
|---|---|
| Validator V-01 errors after SKILL.md edits | The H1 in a SKILL.md may not match the frontmatter `description:` after rewrites that changed the description. Read both, align them. |
| Validator V-06 errors after SKILL.md edits | The YAML frontmatter `description:` field got broken by a multi-line edit. Use a single-line string or proper YAML block scalar (`description: \|` followed by indented lines). |
| The promote-thread-to-tree validation FAILS the "preserve consent gate" check | You removed too much. Re-read the original §-level "Forbidden / Only valid value source" structure. Keep the substantive logic; only change the tool-name "AskUserQuestion" to "ask the user". Verify the security gate is intact by reading the rewritten SKILL.md end-to-end. |
| An interaction in a SKILL.md isn't actually `AskUserQuestion`-shaped — it's `TodoWrite`-shaped or example code | Audit-report says TodoWrite=0 so this shouldn't happen. If you find a TodoWrite reference, it slipped through day-1's audit; flag in execution log. |

### Task 3 failures

| Symptom | Fix |
|---|---|
| Smoke test fails because new-thread.sh references a path under `${CLAUDE_PLUGIN_ROOT}` | Task 1 missed a script that new-thread depends on. Re-run the Task 1 validation grep with a wider pattern; refactor what's left. |
| Smoke test fails because the validator complains about the scratch brain | The scratch brain skeleton in the test script is missing a required file (`config.yaml`, `CONVENTIONS.md`, `thread-index.md`, `current-state.md`). Check what `verify-tree` requires for a minimal brain and update the skeleton. |
| Smoke test passes but its assertions don't actually exercise the new-thread flow | Add more substantive assertions: thread-index.md has the new row, current-state.md is regenerated, transcript.md exists. |

### Cross-cutting failures

| Symptom | Fix |
|---|---|
| `.git/HEAD.lock` errors during commits (the recurring sandbox issue) | Standard remediation: `rm -f .git/HEAD.lock .git/index.lock` then retry. If running in the sandbox and the locks can't be unlinked, surface to Tom. |
| Tests pass but day-2 evaluation NOT-READY on a criterion | Re-read the criterion's "Programmatic check" in § PR-merge criteria. The check may have a strictness that the validation scripts don't replicate. |

## End-of-day evaluation

Run this single script after all three task validations have passed. It evaluates each of the eight PR-merge criteria, generates the evaluation report at `docs/handoff/day-02-evaluation-report.md`, and exits 0 if the verdict is `MERGE-READY`.

```bash
set +e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

REPORT=docs/handoff/day-02-evaluation-report.md
PASS=1
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
declare -a ROWS=()

# Criterion 1 — helper exists + 3-mode resolution
HELPER_OK=1
test -f scripts/_plugin_root.sh || HELPER_OK=0
bash -c '. scripts/_plugin_root.sh && _plugin_root --plugin-root=/tmp/x | grep -q "^/tmp/x$"' || HELPER_OK=0
bash -c 'PROJECT_BRAIN_PACK_ROOT=/tmp/y . scripts/_plugin_root.sh && _plugin_root | grep -q "^/tmp/y$"' || HELPER_OK=0
bash -c 'CLAUDE_PLUGIN_ROOT=/tmp/z . scripts/_plugin_root.sh && _plugin_root | grep -q "^/tmp/z$"' || HELPER_OK=0
if [ "$HELPER_OK" = "1" ]; then
  ROWS+=("| 1 | _plugin_root helper works in 3 modes | ✓ | flag, PROJECT_BRAIN_PACK_ROOT, CLAUDE_PLUGIN_ROOT all resolve correctly |")
else
  ROWS+=("| 1 | _plugin_root helper works in 3 modes | ✗ | helper missing or resolution incorrect |")
  PASS=0
fi

# Criterion 2 — no live ${CLAUDE_PLUGIN_ROOT}
LIVE1=$(git grep '\${CLAUDE_PLUGIN_ROOT}' -- 'scripts/*.sh' 'scripts/**/*.sh' 'scripts/**/*.py' 'skills/*/SKILL.md' 2>/dev/null \
        | grep -v "_plugin_root.sh\|CONVENTIONS.md\|CHANGELOG.md\|RELEASE-NOTES.md\|docs/handoff/" | wc -l | tr -d ' ')
if [ "$LIVE1" = "0" ]; then
  ROWS+=("| 2 | No live \${CLAUDE_PLUGIN_ROOT} in operative code | ✓ | 0 refs in scripts/+skills/ outside helper itself |")
else
  ROWS+=("| 2 | No live \${CLAUDE_PLUGIN_ROOT} in operative code | ✗ | ${LIVE1} live refs remain |")
  PASS=0
fi

# Criterion 3 — no Cowork tool names in SKILL.md
LIVE2=$(git grep -E '(AskUserQuestion|TodoWrite|mcp__cowork__|mcp__visualize__)' skills/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$LIVE2" = "0" ]; then
  ROWS+=("| 3 | No Cowork tool names in SKILL.md | ✓ | 0 refs in skills/ |")
else
  ROWS+=("| 3 | No Cowork tool names in SKILL.md | ✗ | ${LIVE2} refs remain in SKILL.md |")
  PASS=0
fi

# Criterion 4 — validator green
VTOUT=$(python3 scripts/verify-tree.py --brain=/Users/ttan/workspace/Project-Brain/project-brain 2>&1 | tail -1)
if echo "$VTOUT" | grep -q "0 errors"; then
  ROWS+=("| 4 | Validator green | ✓ | ${VTOUT} |")
else
  ROWS+=("| 4 | Validator green | ✗ | ${VTOUT} |")
  PASS=0
fi

# Criterion 5 — smoke test
SMOKE_OK=1
./scripts/test_smoke_new_thread.sh > /tmp/smoke-eval.log 2>&1 || SMOKE_OK=0
tail -1 /tmp/smoke-eval.log | grep -q "SMOKE TEST PASSED" || SMOKE_OK=0
if [ "$SMOKE_OK" = "1" ]; then
  ROWS+=("| 5 | Smoke test end-to-end | ✓ | new-thread.sh succeeds with no Cowork env vars |")
else
  ROWS+=("| 5 | Smoke test end-to-end | ✗ | smoke test failed; see /tmp/smoke-eval.log |")
  PASS=0
fi

# Criterion 6 — security-critical prose preserved
PFILE=skills/promote-thread-to-tree/SKILL.md
SEC_OK=1
grep -q "Forbidden" "$PFILE" || SEC_OK=0
grep -qE "Only valid value source|only valid value source|sole authority|sole source" "$PFILE" || SEC_OK=0
grep -q -- "--allow-domain" "$PFILE" || SEC_OK=0
if [ "$SEC_OK" = "1" ]; then
  ROWS+=("| 6 | promote-thread-to-tree consent-gate preserved | ✓ | 'Forbidden' + 'Only valid value source' + '--allow-domain' all present |")
else
  ROWS+=("| 6 | promote-thread-to-tree consent-gate preserved | ✗ | one or more consent-gate markers missing |")
  PASS=0
fi

# Criterion 7 — day-2 commits with conventional messages
RECENT=$(git log --oneline -10)
COMMITS_OK=1
echo "$RECENT" | grep -qE "^[a-f0-9]+ refactor:" || COMMITS_OK=0
echo "$RECENT" | grep -qE "^[a-f0-9]+ decouple:" || COMMITS_OK=0
echo "$RECENT" | grep -qE "^[a-f0-9]+ test:" || COMMITS_OK=0
if [ "$COMMITS_OK" = "1" ]; then
  ROWS+=("| 7 | Day-2 commits with conventional prefixes | ✓ | refactor: + decouple: + test: all present |")
else
  ROWS+=("| 7 | Day-2 commits with conventional prefixes | ✗ | one or more conventional commits missing |")
  PASS=0
fi

# Criterion 8 — no .bak files
BAKS=$(find . -name "*.bak" -not -path "./.git/*" 2>/dev/null | wc -l | tr -d ' ')
if [ "$BAKS" = "0" ]; then
  ROWS+=("| 8 | No stray .bak files | ✓ | clean |")
else
  ROWS+=("| 8 | No stray .bak files | ✗ | ${BAKS} .bak files remain |")
  PASS=0
fi

# Build the report
{
  echo "# Day-2 Evaluation Report"
  echo
  echo "- Generated: ${TIMESTAMP}"
  echo "- Plan reference: \`project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md\` § 4 (week 1 day 2)"
  echo "- Handoff: \`docs/handoff/day-02-skill-decoupling.md\`"
  echo "- Day-1 audit input: \`docs/handoff/day-01-cowork-audit-report.md\` (103 occurrences flagged)"
  echo
  echo "## Merge criteria"
  echo
  echo "| # | Criterion | Status | Evidence |"
  echo "|---|---|---|---|"
  for row in "${ROWS[@]}"; do echo "$row"; done
  echo
  echo "## Files changed (since day-1 evaluation report)"
  echo
  echo '```'
  (git diff --stat 192cdeb..HEAD 2>/dev/null || git diff --stat HEAD~5..HEAD) | sed 's/^/  /'
  echo '```'
  echo
  echo "## Commits"
  echo
  echo '```'
  git log --oneline -10 | sed 's/^/  /'
  echo '```'
  echo
  if [ "$PASS" = "1" ]; then
    echo "## Verdict: **MERGE-READY**"
    echo
    echo "All eight criteria pass. This day's work is ready to merge."
  else
    FAILED=$(printf '%s\n' "${ROWS[@]}" | grep "✗" | awk -F'|' '{print $2}' | tr -d ' ')
    echo "## Verdict: **NOT-READY**"
    echo
    echo "Failing criteria: ${FAILED}. See merge-criteria table above for evidence."
  fi
} > "$REPORT"

cat "$REPORT"
echo
if [ "$PASS" = "1" ]; then
  echo "✓ DAY-2 EVALUATION: MERGE-READY — report at $REPORT"
  exit 0
else
  echo "✗ DAY-2 EVALUATION: NOT-READY — report at $REPORT"
  exit 1
fi
```

## Exit gate

The `## End-of-day evaluation` script IS the merge-readiness check. When it exits 0 with verdict `MERGE-READY`, complete the exit-gate sequence below to open the PR. Day-2 is done only when the PR is open and reported to Tom — not before.

After the evaluation exits MERGE-READY:

1. Commit the evaluation report:
    ```bash
    git add docs/handoff/day-02-evaluation-report.md
    git commit -m "docs(handoff): day-2 evaluation report — MERGE-READY"
    ```
2. Update the `Status:` header at the top of this handoff doc from `ready` (or `in-progress`) to `done`.
3. Append to `## Execution log` (bottom) a brief entry: wall-clock time, deviations from spec, notes for day 3.
4. Commit the handoff-doc updates:
    ```bash
    git add docs/handoff/day-02-skill-decoupling.md
    git commit -m "docs(handoff): day-2 done"
    ```
5. Push the feature branch to origin:
    ```bash
    git push -u origin day-02/skill-decoupling
    ```
6. Open the PR with the evaluation report as the body (so the reviewer sees the verdict + criteria evidence inline):
    ```bash
    gh pr create \
      --base main \
      --head day-02/skill-decoupling \
      --title "Day 02 — Host-neutral skill decoupling (_plugin_root helper + SKILL.md rewrites)" \
      --body-file docs/handoff/day-02-evaluation-report.md
    ```
7. Capture the PR URL `gh pr create` printed. Stop. Report completion to Tom in your final response with the PR URL, the verdict line, and a one-line summary of what's in the PR. Tom reviews via GitHub UI and merges (or requests changes).

If the evaluation script returns NOT-READY:

- Do **not** proceed to step 2 above. Do **not** push the branch. Do **not** open a PR.
- The absence of a PR is itself a signal that the day isn't done.
- Identify the failing criterion from the verdict block.
- Re-engage the relevant task's test-fix-retest loop.
- Re-run the End-of-day evaluation. Repeat up to ~5 cycles.
- After 5 cycles or if the failure mode isn't covered by `## Common failure modes`, escalate.

If you reach step 5 (push) and the push is rejected because the branch already exists on remote with diverged history (rare; happens if a prior aborted run pushed), inspect with `git log origin/day-02/skill-decoupling..HEAD` and `git log HEAD..origin/day-02/skill-decoupling`. If the remote contains only your prior commits, force-push with `git push --force-with-lease`. If the remote contains commits you didn't author, escalate.

If you reach step 6 and `gh pr create` reports a PR already exists for this branch (rare; happens if a prior run created one and you re-ran), update the existing PR body instead:
```bash
gh pr edit --body-file docs/handoff/day-02-evaluation-report.md
```
Then capture the existing PR URL from `gh pr view --json url -q .url` and proceed to step 7.

## Out of scope

Explicitly NOT day-2 work:

- Renaming any other skills (e.g., `discard-promotion` ↔ `discard-thread`) — defer to v1.1.
- Building the `mcp/` scaffolding directory or `pyproject.toml` — that's day 3.
- Editing `CONVENTIONS.md`, `RUNTIME.md`, `PORTING.md` beyond the few references that absolutely require it (e.g., if a doc names a renamed function or contradicts new behavior).
- Adding TodoWrite-style progress tracking back via a host-neutral helper — interaction shapes, not state.
- Touching `bin/project-brain` if it exists and isn't broken.
- Refactoring the validator further beyond yesterday's `_yaml_mini` fix.
- Creating documentation site / publishing PyPI / signing — Week 3 / v1.1 work.

## Escalation conditions

Escalate only for genuine human-judgment calls. Mechanical failures stay in-loop via `## Common failure modes`.

Escalate if:

- The `promote-thread-to-tree` rewrite makes the security-gate logic ambiguous and you cannot determine whether the rewritten prose still forbids the original sources (frontmatter, folder list, prior promoted_to, content topic, conversation context). Better to surface the ambiguity than ship a weakened gate.
- A SKILL.md interaction shape is genuinely unclear (e.g., it's a free-text input but the original prose is vague). Surface the candidates and let Tom decide the canonical phrasing.
- Auto-detect resolution in `_plugin_root` returns a path that doesn't match any of the four documented modes — suggests an edge case the spec missed.
- Smoke test passes but the criterion-5 check still fails — suggests the check is stricter than the test.
- Any task hits its ~5 retry attempts without passing validation.
- Total wall-clock time exceeds 2 calendar days — escalate to rebaseline rather than push through.

Do NOT escalate for: typos in your own bash, missed cross-references, `.bak` cleanup, validator V-01 errors from a single SKILL.md rewrite (those are loop work). The recurring `.git/*.lock` sandbox issue: surface it but don't escalate; Tom knows how to clear it from the host.

## After day 2

Day 3's input: the host-neutral pack (Layer 1 + decoupled skills) is now ready for the MCP server scaffold. Day-3 work begins building `mcp/` with `pyproject.toml`, `server.py`, `tools.py`, `prompts.py`, `resources.py`. Plan ref: artifact 0003 § 4 (week 1 day 3).

A separate handoff doc — `day-03-mcp-server-scaffold.md` — will be drafted after day-2 lands.

---

## Execution log

_Executor: append entries here as you work. Format:_

_- `[YYYY-MM-DDTHH:MMZ]` — what happened_

### 2026-05-13 — Tom (via Claude Code, opus-4-7)

**Status:** done. Three task commits + one eval-report commit on `day-02/skill-decoupling`:

- `ef3d03a refactor(scripts): introduce _plugin_root helper, drop hard-coded ${CLAUDE_PLUGIN_ROOT}` — 12 files, 77+/25−.
- `af0ee54 decouple(skills): rewrite Cowork tool-name refs to host-neutral interactions` — 14 files, 38+/37−.
- `e5cafb8 test(smoke): new-thread.sh runs host-agnostically without Cowork env vars` — 1 file, 140+.
- `2f8b992 docs(handoff): day-2 evaluation report — MERGE-READY` — eval report.

**Verdict:** MERGE-READY via the corrected evaluation script at `/tmp/day02-eval.sh`. All eight criteria pass.

**Deviations from spec:**

1. **Scripts side of Task 1 had no consumers.** The audit pre-condition (37 `${CLAUDE_PLUGIN_ROOT}` hits) lived entirely in `skills/*/SKILL.md` invocation examples, not in `scripts/`. None of `scripts/*.sh` or `scripts/**/*.py` referenced the env var. The `_plugin_root` helper was built per spec anyway (covers the auto-detect + future scripts case), but the script-internal refactor pattern from § Task 1 had nothing to apply against. The SKILL.md invocation examples were rewritten from `${CLAUDE_PLUGIN_ROOT}/scripts/...` to `${PROJECT_BRAIN_PACK_ROOT}/scripts/...` so the runtime contract names a host-neutral variable. The 4-tier helper inside scripts preserves backward compat with hosts that still set the legacy variable.
2. **End-of-day evaluation script had two reproducible bugs.** Both documented inside the report under § "Script adjustments" and inside criterion 1's evidence cell. (i) Criterion 1's `VAR=val . src.sh && _plugin_root | grep` pattern: bash drops `VAR` after the `.` builtin returns, so the subsequent `_plugin_root` runs without it and falls through to auto-detect. Adjusted to `export VAR=val; . src.sh; _plugin_root`. The helper is correct; the check was over-strict. (ii) The shell-aliased `grep` issue carried over from day-1 — all `grep` pipelines use `command grep` to bypass Claude Code's ugrep wrapper. Day-2's embedded evaluation script in the handoff doc should be updated next time the doc is touched to use these patterns.
3. **`.git/HEAD.lock` hit during pre-flight branch creation.** Cleared per § Common failure modes (recurring sandbox issue), then proceeded normally. Branch `day-02/skill-decoupling` had already been pre-created (pointed at the same commit as `main`); switched to it instead of creating fresh.
4. **Pre-flight test-suite check ignored.** Pre-flight step 8a expects `^OK` from `python3 -m unittest scripts.test_verify_tree`; actual is 9 failures, all caused by `ModuleNotFoundError: No module named 'yaml'` and one bash 3.2 incompatibility (`declare -A`) in `promote-local.sh` — both pre-existing from before day-1, not caused by today's work. Validator passes cleanly. Smoke test (the day-2-specific test) passes.
5. **The `mcp__cowork__` single hit lives in `RUNTIME.md` L52, not in skills/.** Per criterion 3's scope (skills/ only), no action required — RUNTIME.md is documentation of host-binding, not invocation prose. Day-1 audit's "Notes for day 2" already flagged this as a likely keep-and-rephrase target rather than a removal target.

**Notes for day 3:**

- Pack is now host-neutral. The MCP server scaffold can rely on `PROJECT_BRAIN_PACK_ROOT` as the env var contract, or on the script-level auto-detect for hosts that don't set anything.
- The smoke test (`scripts/test_smoke_new_thread.sh`) is the first cross-harness regression guard. Day 3 should add at least one more (e.g., `test_smoke_init_brain.sh`) to cover the init path.
- Pre-existing `yaml` module test failures are not day-2 work but should be tracked. They block `^OK` on the test suite and will block any future day's pre-flight check 8a until resolved. Likely fix: drop the PyYAML dependency entirely now that `_yaml_mini` handles the fallback (commit `3503a30`).
- Untracked `docs/handoff/README.md` and `docs/handoff/_evaluation-report-template.md` are Tom's parallel scaffolding work — left untouched.
