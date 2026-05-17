# Day 6 Handoff — ChatGPT Desktop + OpenAI Codex CLI install paths + compat matrix scaffold

- **Audience**: Claude Code (or any agent operating on the project-brain repo)
- **Date authored**: 2026-05-13
- **Author**: Tom (taotan6@gmail.com) via planning session
- **Estimated effort**: 0.5-1 person-day (mostly docs; light code)
- **Status**: done
- **Execution mode**: autonomous test-fix-retest loop; escalate only on judgment calls
- **Predecessor**: `day-05-complex-tools-and-install.md` (status: done; PR merged to `main`)
- **Branch**: `day-06/chatgpt-codex-config` (created at pre-flight)

## TL;DR

Week 2 begins: extend the install surface from Claude-only (day-5) to **ChatGPT Desktop Plus** and **OpenAI Codex CLI**. The MCP server itself doesn't change — same stdio, same tools, same prompts. Day-6 is configuration + documentation work.

1. Research current Codex CLI MCP support status (escalate if unstable).
2. Add `## ChatGPT Desktop config` and `## OpenAI Codex CLI config` sections to `INSTALL.md` with copy-pasteable config snippets.
3. Scaffold `compat-matrix.md` at repo root with initial rows for Claude Code, Claude Desktop, ChatGPT Desktop, Codex CLI.
4. Document per-harness considerations (config file paths, env var handling, restart procedures, known limitations).

Day-7 and day-8 run the actual end-to-end demos on ChatGPT and Codex. Day-6 ships the docs they verify against.

## Context

You are executing **day 6 (week 2 day 1) of the project-brain v1.0 3-week release plan**.

Read these for "why" decisions:

- **Plan artifact**: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 2 day 1).
- **Day-5 INSTALL.md** — the structural pattern day-6 extends. Same three-section shape (Install / config / Verify) per harness, just with different config-file paths and command/args.
- **Round-01 P5 / P11**: "narrow tier 1 to where you can validate first-session success" — ChatGPT Plus and Codex CLI are tier 2 (best-effort + manual smoke test). Day-6 sets up the docs; day-7/8 run the validation.
- **Convention**: `docs/handoff/README.md` § Workflow + § PR-merge criteria + the canonical `_evaluation-report-template.md`.

Week 1 closed with Claude Desktop Pro + Free + Claude Code as validated install paths. Week 2 is cross-vendor reach: ChatGPT (Plus tier supports MCP via `mcpServers` config; Free does not), and OpenAI Codex CLI (which announced MCP support but the API may still be in flux).

## Goal

By the end of this handoff:

1. **`INSTALL.md`** gains two new sections:
    - `## ChatGPT Desktop config` — same three-pillar shape as the Claude Desktop section (config-file path, JSON snippet, restart instructions).
    - `## OpenAI Codex CLI config` — likewise. If Codex's MCP support is unstable, this section ships marked "experimental, may need adjustment" rather than absent.
2. **`compat-matrix.md`** at repo root: a table of host × tier × MCP-support × validation-status. At least 5 rows: Claude Code (Pro+), Claude Desktop (Pro), Claude Desktop (Free), ChatGPT Desktop (Plus), OpenAI Codex CLI. Validation status is "pending day-7/8 demo" for the new rows.
3. The day-5 `## Claude Desktop config` section is unchanged. Day-6 is purely additive; no rewrites of existing Claude content.
4. A short research note at `docs/notes/day-06-codex-mcp-support.md` documents what you found about Codex's current MCP integration (SDK version, transport, gating, known issues). This isn't a deliverable section in INSTALL.md — it's reference material for day-7/8 to consult.
5. The evaluation report at `docs/handoff/day-06-evaluation-report.md` documents 8/8 merge criteria pass; the day-6 PR is open against `main` with that report as its body.

## PR-merge criteria

| # | Criterion | Programmatic check |
|---|---|---|
| 1 | INSTALL.md `## ChatGPT Desktop config` section present | `command grep -q "^## ChatGPT Desktop config" INSTALL.md`. The section includes a JSON code block with `mcpServers` and the macOS config-file path (`~/Library/Application Support/ChatGPT/`). |
| 2 | INSTALL.md `## OpenAI Codex CLI config` section present | `command grep -q "^## OpenAI Codex CLI config" INSTALL.md`. The section includes either a working config snippet OR an explicit "experimental" marker plus a link to the day-6 research note. |
| 3 | `compat-matrix.md` at repo root with ≥5 rows | `compat-matrix.md` exists; contains a markdown table with header row + ≥5 data rows; each row has a "Validation status" column with a value like "validated (week 1)", "pending (day-7)", or similar. |
| 4 | Day-5 `## Claude Desktop config` unchanged | `git diff main..HEAD -- INSTALL.md` shows ADDITIONS only inside the section; no MODIFICATIONS to Claude Desktop content. (Sanity check; not strict — small fixes to the existing section are OK if they're clearly improvements.) |
| 5 | Codex research note present | `docs/notes/day-06-codex-mcp-support.md` exists with ≥3 documented findings (SDK version, transport mechanism, current gating + tier requirements). Surfaces the research that day-7 will rely on. |
| 6 | No regression: validator green, smoke test green, no Cowork refs | `python3 scripts/verify-tree.py --brain=…` ends `0 errors, 0 warnings`. `python3 scripts/smoke_mcp_roundtrip.py` ends `MCP SMOKE TEST PASSED`. `git grep -E '(AskUserQuestion\|TodoWrite\|mcp__cowork__\|mcp__visualize__)' skills/` returns 0. |
| 7 | Test suite green (modulo bash 3.2 baseline) | Same as days 3-5: 4 `PromoteLocalTests` failures from `declare -A` accepted as documented baseline. |
| 8 | Conventional Commits + smoke-test naming respected | Day-6 commits use Conventional Commits with scope (e.g. `docs:`, `docs(install):`). No new `scripts/test_*.py` smoke files. |

Workflow:

- Working branch is `day-06/chatgpt-codex-config` off `main`.
- After MERGE-READY, branch is pushed; PR opened against `main` with `docs/handoff/day-06-evaluation-report.md` as body.

## Development loop

Standard. Each task: spec → execute → run validation → consult Common failure modes → up to ~5 retries → escalate if stuck.

**Sequencing note**: Task 1 (Codex research) feeds Task 3 (Codex INSTALL section). Tasks 2 (ChatGPT INSTALL section) and 4 (compat-matrix scaffold) are independent and can run in parallel after Task 1.

## Pre-flight checks

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Right repo
test -f CONVENTIONS.md -a -d skills/ -a -f INSTALL.md -a -d mcp/ \
  || { echo "FAIL: not in pack repo or day-5 INSTALL.md missing"; exit 1; }

# 2. gh CLI installed and authed
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 \
  || { echo "FAIL: gh missing or unauthed"; exit 1; }

# 3. Working tree clean
[ -z "$(git status --porcelain)" ] \
  || { echo "FAIL: uncommitted changes"; git status; exit 1; }

# 4. Day-5 must be merged to main — accept both commit subject AND squashed/merge-commit PR title
git fetch origin main 2>&1 >/dev/null || true
MAIN_LOG=$(git log origin/main --oneline -30 2>/dev/null)
echo "$MAIN_LOG" | command grep -qE "(complex tools|Day 05|day-05|MCP-server sections|Claude Desktop config)" \
  || { echo "FAIL: day-5 not on origin/main"; exit 1; }

# 5. Branch setup
current=$(git branch --show-current)
if [ "$current" != "day-06/chatgpt-codex-config" ]; then
  git checkout main
  git pull --ff-only 2>&1 | head -2 || true
  if git rev-parse --verify day-06/chatgpt-codex-config >/dev/null 2>&1; then
    git checkout day-06/chatgpt-codex-config
  else
    git checkout -b day-06/chatgpt-codex-config
  fi
fi
test "$(git branch --show-current)" = "day-06/chatgpt-codex-config" \
  || { echo "FAIL: not on day-06 branch"; exit 1; }

# 6. Validator + day-5 smoke test still green
python3 scripts/verify-tree.py --brain=/Users/ttan/workspace/Project-Brain/project-brain 2>&1 \
  | tail -1 | command grep -q "0 errors" \
  || { echo "FAIL: validator dirty"; exit 1; }
python3 scripts/smoke_mcp_roundtrip.py 2>&1 | tail -1 | command grep -q "MCP SMOKE TEST PASSED" \
  || { echo "FAIL: day-5 smoke test fails before day-6"; exit 1; }

# 7. Day-5 INSTALL.md has the Claude Desktop config we'll be following the pattern of
command grep -q "^## Claude Desktop config" INSTALL.md \
  || { echo "FAIL: day-5 INSTALL.md missing the Claude Desktop section that day-6 mirrors"; exit 1; }

# 8. 17-tool baseline from day-5
N=$(python3 -c "
import asyncio
from project_brain_mcp.server import app
async def m(): print(len(await app.list_tools()))
asyncio.run(m())
" 2>/dev/null | tr -d ' ')
[ "$N" -ge 17 ] || { echo "FAIL: expected ≥17 tools (day-5 baseline), got $N"; exit 1; }

echo "ALL PRE-FLIGHT CHECKS PASSED — on branch day-06/chatgpt-codex-config (day-5 baseline: $N tools)"
```

## Task 1 — Research current Codex CLI MCP support

### Spec

Establish the ground truth for OpenAI Codex CLI's MCP integration as of today. This is research, not code. Outputs a short reference note that day-7 (Codex E2E demo) will consult.

Questions to answer:

1. Does Codex CLI currently support MCP servers? If yes, since which version?
2. What's the config-file location and shape? (Probably `~/.codex/config.toml` or similar; verify.)
3. Does Codex support stdio MCP transport? (We need stdio because the server is local.)
4. Are there auth/tier requirements? (Free vs Plus vs Pro vs Team tiers.)
5. Are there known limitations or rough edges? (Prompt support? Resource support? Tool annotations?)

If Codex's MCP support is materially unstable or absent — for example, the SDK page redirects to "coming soon" — document the gap and mark the Codex INSTALL section in Task 3 as **experimental**. Don't fabricate a config that might not work.

### Steps

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain
mkdir -p docs/notes

# Research via web (you have web access; project-brain doesn't). Sources to
# consult, in priority order:
#   1. https://platform.openai.com/docs/ — official OpenAI docs section on Codex / agents
#   2. https://github.com/openai/codex (or similar repo) — README + MCP-related issues
#   3. modelcontextprotocol.io — official MCP spec, examples, client list
#   4. Recent (last 30 days) blog posts / changelog entries from OpenAI
#
# DO NOT trust LLM training data for this; the landscape moves fast. Web is
# the source of truth.

# After research, write the findings to docs/notes/day-06-codex-mcp-support.md
# in the shape below.
```

The research note shape:

```markdown
# Day-6 Codex MCP Support Research

- Generated: <ISO timestamp>
- Researcher: Claude Code (model version)
- Sources consulted: <list of URLs + dates>

## Summary

(2-3 sentence verdict: ready / experimental / not-ready.)

## Findings

### SDK / version support

- Codex CLI version that ships MCP: <version or "not yet">
- MCP SDK version it ships against: <version>
- Stdio transport supported: <yes/no/partial>

### Config location and shape

- Path: <e.g. ~/.codex/config.toml or ~/.config/codex/config.json>
- Format: <TOML/JSON/YAML>
- mcpServers equivalent key: <name>
- Example snippet: <inline minimal config>

### Auth / tier requirements

- Free tier: <supported? if not, document>
- Plus / Pro / Team: <which tier minimum>
- Any API key requirements separate from CLI login?

### Known limitations

- Prompt support: <yes/no/quirks>
- Resource support: <yes/no/quirks>
- Tool annotations / progress notifications: <support level>
- Rough edges discovered during research: <list>

## Recommendation for INSTALL.md Codex section

(Pick one:)
- READY — ship a working config snippet, mark as supported.
- EXPERIMENTAL — ship a tentative config snippet with a prominent "this may need adjustment" note.
- NOT-READY — defer to v1.1; ship a note in INSTALL.md saying "Codex MCP integration is in flux; see day-6 research note for current status."
```

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Note file exists
test -f docs/notes/day-06-codex-mcp-support.md \
  || { echo "FAIL: Codex research note missing"; exit 1; }

# 2. Has the structural sections
for s in "## Summary" "## Findings" "## Recommendation"; do
  command grep -q "^${s}" docs/notes/day-06-codex-mcp-support.md \
    || { echo "FAIL: research note missing section ${s}"; exit 1; }
done

# 3. At least 3 findings subsections under Findings
N_FINDINGS=$(awk '/^## Findings/{f=1;next} /^## /{f=0} f && /^### /' docs/notes/day-06-codex-mcp-support.md | wc -l | tr -d ' ')
[ "$N_FINDINGS" -ge 3 ] \
  || { echo "FAIL: only $N_FINDINGS finding subsections (need ≥3)"; exit 1; }

# 4. Recommendation is one of the 3 documented values
command grep -qE "(READY|EXPERIMENTAL|NOT-READY)" docs/notes/day-06-codex-mcp-support.md \
  || { echo "FAIL: research note doesn't pick READY/EXPERIMENTAL/NOT-READY"; exit 1; }

echo "TASK 1 VALIDATION PASSED"
```

### Commit

```bash
git add docs/notes/day-06-codex-mcp-support.md
git commit -m "docs(research): document current Codex CLI MCP support status

Reference note for day-7 (Codex E2E demo) to consult. Captures SDK
version, config-file shape, auth/tier requirements, known limitations.
Recommends one of READY / EXPERIMENTAL / NOT-READY for the day-6
INSTALL.md Codex section."
```

## Task 2 — Add `## ChatGPT Desktop config` section to INSTALL.md

### Spec

Insert a new `## ChatGPT Desktop config` section after the `## Claude Desktop config` section in `INSTALL.md`. Mirror the three-part structure:

1. **Config file path** (per OS):
    - macOS: `~/Library/Application Support/ChatGPT/mcp_servers.json` (verify the exact path; ChatGPT Desktop's MCP config location may differ — consult the same research approach as Task 1, but for ChatGPT).
    - Windows / Linux: equivalents if documented.
2. **JSON snippet**: same `mcpServers` shape as Claude Desktop, with the `uvx project-brain-mcp` command and `PROJECT_BRAIN_HOME` env var.
3. **Restart instructions**: full app quit + relaunch (most desktop MCP clients hot-load config only via restart).

Include a one-line tier note: "ChatGPT Plus and above. Free tier doesn't expose MCP server config."

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Section present
command grep -q "^## ChatGPT Desktop config" INSTALL.md \
  || { echo "FAIL: ## ChatGPT Desktop config section missing"; exit 1; }

# 2. JSON snippet present
command awk '/^## ChatGPT Desktop config/,/^## [^C]/' INSTALL.md | command grep -q "mcpServers" \
  || { echo "FAIL: ChatGPT section missing mcpServers JSON"; exit 1; }

# 3. uvx command + PROJECT_BRAIN_HOME present
command awk '/^## ChatGPT Desktop config/,/^## [^C]/' INSTALL.md | command grep -q "uvx project-brain-mcp" \
  || { echo "FAIL: ChatGPT section missing uvx command"; exit 1; }
command awk '/^## ChatGPT Desktop config/,/^## [^C]/' INSTALL.md | command grep -q "PROJECT_BRAIN_HOME" \
  || { echo "FAIL: ChatGPT section missing PROJECT_BRAIN_HOME env var"; exit 1; }

# 4. Config file path (at least macOS) referenced
command awk '/^## ChatGPT Desktop config/,/^## [^C]/' INSTALL.md | command grep -q "Library/Application Support/ChatGPT\|chatgpt-config\|~/.chatgpt" \
  || { echo "FAIL: ChatGPT section missing OS-specific config file path"; exit 1; }

# 5. Tier note present
command awk '/^## ChatGPT Desktop config/,/^## [^C]/' INSTALL.md | command grep -qiE "(plus|tier|free.*not)" \
  || { echo "FAIL: ChatGPT section missing tier note (Plus required)"; exit 1; }

echo "TASK 2 VALIDATION PASSED"
```

### Commit

```bash
git add INSTALL.md
git commit -m "docs(install): add ChatGPT Desktop config section

Mirrors the Claude Desktop section's three-part shape (config file path,
JSON snippet, restart instructions) for ChatGPT Plus tier. Free tier
doesn't expose MCP config; documented in the tier note.

Day-7 will run the actual end-to-end demo against this snippet."
```

## Task 3 — Add `## OpenAI Codex CLI config` section to INSTALL.md

### Spec

Insert a `## OpenAI Codex CLI config` section after the ChatGPT section. Shape per Task 1's recommendation:

- **If READY**: full three-part section like ChatGPT (config file path, snippet, verification).
- **If EXPERIMENTAL**: same three parts but with a prominent `> **⚠ Experimental**` callout at the top of the section, plus a "report issues" line linking to the day-6 research note.
- **If NOT-READY**: a brief stub section that says "OpenAI Codex CLI MCP integration is currently in flux. See `docs/notes/day-06-codex-mcp-support.md` for current status. Revisit when Codex stabilizes its MCP support."

In all three cases, the section MUST exist — the absence of a Codex section would suggest we forgot about Codex.

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. Section present
command grep -q "^## OpenAI Codex CLI config" INSTALL.md \
  || { echo "FAIL: ## OpenAI Codex CLI config section missing"; exit 1; }

# 2. Section is one of the three documented shapes
codex_section=$(command awk '/^## OpenAI Codex CLI config/,/^## [^O]/' INSTALL.md)
HAS_JSON=$(echo "$codex_section" | command grep -c "mcpServers\|mcp_servers" || true)
HAS_EXPERIMENTAL=$(echo "$codex_section" | command grep -ciE "experimental|in flux|may need adjustment" || true)
HAS_DEFER=$(echo "$codex_section" | command grep -ciE "see docs/notes/day-06-codex-mcp-support" || true)

if [ "$HAS_JSON" -gt 0 ] && [ "$HAS_EXPERIMENTAL" = "0" ]; then
  echo "  Codex section appears to be READY shape (working config)"
elif [ "$HAS_JSON" -gt 0 ] && [ "$HAS_EXPERIMENTAL" -gt 0 ]; then
  echo "  Codex section appears to be EXPERIMENTAL shape (config + caveat)"
elif [ "$HAS_DEFER" -gt 0 ]; then
  echo "  Codex section appears to be NOT-READY shape (defer + link)"
else
  echo "FAIL: Codex section is neither READY, EXPERIMENTAL, nor NOT-READY shape"
  echo "$codex_section" | head -20
  exit 1
fi

# 3. Cross-check: matches Task 1's research-note recommendation
NOTE_REC=$(command grep -m 1 -oE "READY|EXPERIMENTAL|NOT-READY" docs/notes/day-06-codex-mcp-support.md | head -1)
echo "  Research-note recommends: $NOTE_REC"
case "$NOTE_REC" in
  READY) [ "$HAS_JSON" -gt 0 ] && [ "$HAS_EXPERIMENTAL" = "0" ] || { echo "FAIL: section shape doesn't match READY recommendation"; exit 1; } ;;
  EXPERIMENTAL) [ "$HAS_JSON" -gt 0 ] && [ "$HAS_EXPERIMENTAL" -gt 0 ] || { echo "FAIL: section shape doesn't match EXPERIMENTAL recommendation"; exit 1; } ;;
  NOT-READY) [ "$HAS_DEFER" -gt 0 ] || { echo "FAIL: section shape doesn't match NOT-READY recommendation"; exit 1; } ;;
esac

echo "TASK 3 VALIDATION PASSED (shape: matches research-note recommendation '$NOTE_REC')"
```

### Commit

```bash
git add INSTALL.md
git commit -m "docs(install): add OpenAI Codex CLI config section

Shape determined by docs/notes/day-06-codex-mcp-support.md research
recommendation (READY / EXPERIMENTAL / NOT-READY). All three shapes
keep the section present in INSTALL.md so users can find it; the
content varies based on current Codex MCP integration status.

Day-7 will run the Codex E2E demo against whatever shape day-6 lands."
```

## Task 4 — Scaffold `compat-matrix.md` at repo root

### Spec

A new file `compat-matrix.md` at the repo root with a single table summarizing host compatibility. Initial rows:

| Host | Tier | Transport | First-session validated | Notes |
|------|------|-----------|--------------------------|-------|
| Claude Code | Pro+ | stdio | yes (week 1) | native plugin loader + MCP stdio |
| Claude Desktop | Pro | stdio | yes (week 1, day-5 demo) | mcpServers config edit |
| Claude Desktop | Free | stdio | yes (week 1, day-5 demo) | same path as Pro; tier limits messages |
| ChatGPT Desktop | Plus | stdio | pending (day-7) | mcpServers config edit; Free tier excluded |
| OpenAI Codex CLI | (per research) | stdio | pending (day-8) | see INSTALL.md § OpenAI Codex CLI config |

The matrix becomes the canonical reference for "where does project-brain work and how well." It's a docs artifact, not a CI input — but the column "First-session validated" maps to handoff merge criteria, so it's auditable.

Future rows for community-maintained adapters (Cursor, Continue, Aider, Gemini CLI) get added in week 3 when CONTRIBUTING.md gets fleshed out.

### Validation script

```bash
set -e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

# 1. File exists
test -f compat-matrix.md || { echo "FAIL: compat-matrix.md missing"; exit 1; }

# 2. Has a markdown table with ≥5 data rows
ROWS=$(command awk '/^\|.*\|.*\|/{c++} END{print c}' compat-matrix.md)
[ "$ROWS" -ge 6 ] \
  || { echo "FAIL: compat-matrix.md has only $ROWS table rows (need ≥6 = 1 header + 5 data)"; exit 1; }

# 3. Each new harness named at least once
for h in "Claude Code" "Claude Desktop" "ChatGPT Desktop" "OpenAI Codex"; do
  command grep -q "$h" compat-matrix.md \
    || { echo "FAIL: compat-matrix.md missing row for '$h'"; exit 1; }
done

# 4. Validation status column present
command grep -qE "(validated|First-session|Validation)" compat-matrix.md \
  || { echo "FAIL: compat-matrix.md missing validation-status column"; exit 1; }

echo "TASK 4 VALIDATION PASSED"
```

### Commit

```bash
git add compat-matrix.md
git commit -m "docs: scaffold compat-matrix.md at repo root

Initial host × tier × transport × validation-status matrix. Five rows:
  Claude Code (Pro+) — validated week 1
  Claude Desktop (Pro) — validated week 1 day-5 demo
  Claude Desktop (Free) — validated week 1 day-5 demo
  ChatGPT Desktop (Plus) — pending day-7
  OpenAI Codex CLI — pending day-8 (per research note status)

Week 3 will expand with community-maintained adapter rows (Cursor,
Continue, Aider, Gemini CLI) as they're contributed."
```

## Common failure modes and fixes

### Task 1 (Codex research)

| Symptom | Fix |
|---|---|
| Codex MCP docs page returns 404 or "coming soon" | Treat as NOT-READY. Document the URL + date + exact wording. |
| Multiple conflicting sources (e.g., GitHub README says one thing, blog says another) | List both with dates; pick the more authoritative (official docs > blog > tweet). |
| Research takes >2 hours | You're going too deep. Surface what you have and escalate if it's not enough to pick a shape. |

### Task 2 (ChatGPT config)

| Symptom | Fix |
|---|---|
| ChatGPT Desktop config-file path is undocumented | Try the standard locations first (`~/Library/Application Support/ChatGPT/`); failing that, document "users may need to find their config; see ChatGPT documentation." |
| ChatGPT Desktop doesn't support custom env vars in mcpServers | Document the limitation. Suggest setting `PROJECT_BRAIN_HOME` system-wide instead. |

### Task 3 (Codex config)

| Symptom | Fix |
|---|---|
| Research note recommends READY but Task 3's validation can't find a working snippet | Re-read the research note; if the snippet was given, paste it. If not, downgrade to EXPERIMENTAL. |
| Research-note recommendation and INSTALL section shape diverge | Always match the research note. If you want to override, update the research note first (different commit). |

### Task 4 (compat-matrix)

| Symptom | Fix |
|---|---|
| compat-matrix table renders badly in GitHub preview | Common cause: misaligned column widths. Use a markdown table formatter or just verify column counts match across rows. |

### Cross-cutting

| Symptom | Fix |
|---|---|
| `.git/HEAD.lock` errors | Standard sandbox remediation; clear from host. |
| Pre-flight check 4 fails despite day-5 having merged | Day-5 may have been merged with a different commit subject than the pattern expects. Verify with `git log origin/main --oneline -30` and update the pre-flight pattern if needed. |

## End-of-day evaluation

```bash
set +e
cd /Users/ttan/workspace/Project-Brain/final/project-brain

REPORT=docs/handoff/day-06-evaluation-report.md
PASS=1
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
declare -a ROWS=()

# Criterion 1 — ChatGPT section
if command grep -q "^## ChatGPT Desktop config" INSTALL.md \
   && command awk '/^## ChatGPT Desktop config/,/^## [^C]/' INSTALL.md | command grep -q "mcpServers" \
   && command awk '/^## ChatGPT Desktop config/,/^## [^C]/' INSTALL.md | command grep -q "uvx project-brain-mcp"; then
  ROWS+=("| 1 | ChatGPT Desktop config section | ✓ | section present with mcpServers JSON + uvx command |")
else
  ROWS+=("| 1 | ChatGPT Desktop config section | ✗ | missing or incomplete |")
  PASS=0
fi

# Criterion 2 — Codex section
if command grep -q "^## OpenAI Codex CLI config" INSTALL.md; then
  ROWS+=("| 2 | OpenAI Codex CLI config section | ✓ | section present (shape per research recommendation) |")
else
  ROWS+=("| 2 | OpenAI Codex CLI config section | ✗ | section missing |")
  PASS=0
fi

# Criterion 3 — compat-matrix.md
ROWS_COUNT=$(command awk '/^\|.*\|.*\|/{c++} END{print c+0}' compat-matrix.md 2>/dev/null)
if [ -f compat-matrix.md ] && [ "$ROWS_COUNT" -ge 6 ]; then
  ROWS+=("| 3 | compat-matrix.md with ≥5 data rows | ✓ | ${ROWS_COUNT} table rows |")
else
  ROWS+=("| 3 | compat-matrix.md | ✗ | missing or fewer than 6 rows |")
  PASS=0
fi

# Criterion 4 — Day-5 Claude content unchanged
# Soft check — git diff main..HEAD for INSTALL.md should not delete lines from Claude Desktop section
DEL_CLAUDE=$(git diff main..HEAD -- INSTALL.md 2>/dev/null | awk '/^-[^-]/{c++} END{print c+0}')
ADD_CHATGPT=$(git diff main..HEAD -- INSTALL.md 2>/dev/null | awk '/^\+## ChatGPT/{c++} END{print c+0}')
# We allow some small deletions (typo fixes etc.) but flag if >5
if [ "$DEL_CLAUDE" -le 5 ]; then
  ROWS+=("| 4 | Day-5 Claude content unchanged (additive only) | ✓ | ${DEL_CLAUDE} deletions vs main (≤5 tolerated for minor edits) |")
else
  ROWS+=("| 4 | Day-5 Claude content unchanged | ⚠ | ${DEL_CLAUDE} deletions vs main — review |")
  # Soft fail: warn but don't block
fi

# Criterion 5 — Codex research note
NOTE=docs/notes/day-06-codex-mcp-support.md
if [ -f "$NOTE" ] \
   && command grep -q "^## Summary" "$NOTE" \
   && command grep -q "^## Findings" "$NOTE" \
   && command grep -q "^## Recommendation" "$NOTE"; then
  ROWS+=("| 5 | Codex research note | ✓ | ${NOTE} present with Summary + Findings + Recommendation |")
else
  ROWS+=("| 5 | Codex research note | ✗ | missing or incomplete |")
  PASS=0
fi

# Criterion 6 — no regression
VTOUT=$(python3 scripts/verify-tree.py --brain=/Users/ttan/workspace/Project-Brain/project-brain 2>&1 | command tail -1)
SMOKE_OK=1
python3 scripts/smoke_mcp_roundtrip.py > /tmp/smoke6.log 2>&1 || SMOKE_OK=0
command tail -1 /tmp/smoke6.log | command grep -q "MCP SMOKE TEST PASSED" || SMOKE_OK=0
COWORK=$(git grep -E '(AskUserQuestion|TodoWrite|mcp__cowork__|mcp__visualize__)' skills/ 2>/dev/null | wc -l | tr -d ' ')
if echo "$VTOUT" | command grep -q "0 errors" && [ "$SMOKE_OK" = "1" ] && [ "$COWORK" = "0" ]; then
  ROWS+=("| 6 | No regression (validator + smoke + no Cowork) | ✓ | validator: ${VTOUT}; smoke: PASS; cowork=0 |")
else
  ROWS+=("| 6 | No regression | ✗ | validator=${VTOUT}, smoke_ok=${SMOKE_OK}, cowork=${COWORK} |")
  PASS=0
fi

# Criterion 7 — test suite (modulo bash 3.2 baseline)
TESTS_OUT=$(python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | command tail -1)
if echo "$TESTS_OUT" | command grep -q "^OK"; then
  ROWS+=("| 7 | Test suite green | ✓ | ${TESTS_OUT} |")
elif echo "$TESTS_OUT" | command grep -qE "FAILED \(failures=4\)"; then
  ROWS+=("| 7 | Test suite green (modulo bash 3.2 baseline) | ✓ | 4 baseline PromoteLocalTests failures; no new failures |")
else
  ROWS+=("| 7 | Test suite green | ✗ | ${TESTS_OUT} |")
  PASS=0
fi

# Criterion 8 — Conventional Commits + smoke-test naming
BAD_TEST=$(ls scripts/test_*.py 2>/dev/null | command grep -v "test_verify_tree.py" | wc -l | tr -d ' ')
RECENT=$(git log --oneline main..HEAD 2>/dev/null || git log --oneline -10)
NON_CONV=$(echo "$RECENT" | command grep -vE "^[a-f0-9]+ (docs|feat|fix|chore|refactor|test|build|perf|revert|style|ci)(\([^)]+\))?:" | wc -l | tr -d ' ')
if [ "$BAD_TEST" = "0" ] && [ "$NON_CONV" = "0" ]; then
  ROWS+=("| 8 | Conventional Commits + smoke-test naming | ✓ | 0 bad test_*.py; 0 non-conventional commit subjects |")
else
  ROWS+=("| 8 | Conventional Commits + smoke-test naming | ✗ | bad-test=${BAD_TEST}; non-conventional=${NON_CONV} |")
  PASS=0
fi

# Build the report
{
  echo "# Day-6 Evaluation Report"
  echo
  echo "- Generated: ${TIMESTAMP}"
  echo "- Plan reference: \`project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md\` § 4 (week 2 day 1)"
  echo "- Handoff: \`docs/handoff/day-06-chatgpt-codex-config.md\`"
  echo "- Predecessor: day-05 (merged to main)"
  echo "- Week 2 day 1: opens the cross-vendor reach phase"
  echo
  echo "## Merge criteria"
  echo
  echo "| # | Criterion | Status | Evidence |"
  echo "|---|---|---|---|"
  for row in "${ROWS[@]}"; do echo "$row"; done
  echo
  echo "## Files changed (this branch vs main)"
  echo
  echo '```'
  (git diff --stat main..HEAD 2>/dev/null || git diff --stat HEAD~5..HEAD) | sed 's/^/  /'
  echo '```'
  echo
  echo "## Commits (this branch)"
  echo
  echo '```'
  git log --oneline main..HEAD 2>/dev/null | sed 's/^/  /' || git log --oneline -8 | sed 's/^/  /'
  echo '```'
  echo
  if [ "$PASS" = "1" ]; then
    echo "## Verdict: **MERGE-READY**"
    echo
    echo "All eight criteria pass. Day-6 ships the docs + matrix that day-7/8 verify end-to-end."
  else
    FAILED=$(printf '%s\n' "${ROWS[@]}" | command grep -E "✗" | awk -F'|' '{print $2}' | tr -d ' ')
    echo "## Verdict: **NOT-READY**"
    echo
    echo "Failing criteria: ${FAILED}. See merge-criteria table above for evidence."
  fi
} > "$REPORT"

cat "$REPORT"
echo
if [ "$PASS" = "1" ]; then
  echo "✓ DAY-6 EVALUATION: MERGE-READY — report at $REPORT"
  exit 0
else
  echo "✗ DAY-6 EVALUATION: NOT-READY — report at $REPORT"
  exit 1
fi
```

## Exit gate

After MERGE-READY:

1. Commit eval report:
    ```bash
    git add docs/handoff/day-06-evaluation-report.md
    git commit -m "docs(handoff): day-6 evaluation report — MERGE-READY"
    ```
2. Update `Status:` → `done`.
3. Append `## Execution log` entry: wall-clock time, deviations, **the research note's recommendation for Codex (READY / EXPERIMENTAL / NOT-READY)**, anything day-7/8 should know.
4. Commit handoff updates:
    ```bash
    git add docs/handoff/day-06-chatgpt-codex-config.md
    git commit -m "docs(handoff): day-6 done"
    ```
5. Push:
    ```bash
    git push -u origin day-06/chatgpt-codex-config
    ```
6. Open PR:
    ```bash
    gh pr create \
      --base main \
      --head day-06/chatgpt-codex-config \
      --title "Day 06 — ChatGPT + Codex config sections + compat matrix" \
      --body-file docs/handoff/day-06-evaluation-report.md
    ```
7. Report PR URL to Tom.

NOT-READY: no push, no PR. Return to the failing task's loop.

## Out of scope

- **Actual end-to-end demos** on ChatGPT and Codex — that's day-7 and day-8.
- New MCP tools, prompts, or resources — day-5 closed the v1 server surface.
- README rewrite / value-prop polish — week 3 work.
- PyPI publish / DXT bundle / signing — week 2-3 / v1.1.
- Community adapter rows in `compat-matrix.md` (Cursor, Continue, Aider, Gemini CLI) — week 3, with CONTRIBUTING.md.

## Escalation conditions

- Codex MCP documentation is contradictory or unreachable. Surface URLs + dates; let Tom pick a recommendation.
- ChatGPT Desktop's config-file path can't be confirmed from official docs. Document what you found and ask.
- Task 3's section-shape validation can't decide which of READY/EXPERIMENTAL/NOT-READY matches the prose. Probably means the prose needs sharpening — re-read and commit a clearer version, OR escalate if the prose is intentionally hedged.
- Total wall-clock time exceeds 1 calendar day — research is taking longer than budgeted. Escalate.

Do NOT escalate for: typos, missing minor fields, formatting nits.

## After day 6

Day-7: ChatGPT Desktop Plus end-to-end install demo. Day-8: Codex CLI end-to-end install demo (or formal "deferred to v1.1" if research says NOT-READY). Plan ref: artifact 0003 § 4 (week 2 days 2-3).

A separate handoff doc — `day-07-chatgpt-install-demo.md` — will be drafted after day-6 lands.

---

## Execution log

_Executor: append entries here as you work. Format:_

_- `[YYYY-MM-DDTHH:MMZ]` — what happened_

### 2026-05-16 — Tom (via Claude Code, opus-4-7)

**Status:** done. Five commits on `day-06/chatgpt-codex-config`:

- `5693d1f docs(research): document current Codex CLI MCP support status` — research note recommends **READY** for Codex.
- `51c30dd docs(install): add ChatGPT Desktop config section` — bundled Task 2 + Task 3 (both new INSTALL.md sections; see deviations below).
- `a2624aa docs: scaffold compat-matrix.md at repo root` — six-row matrix (Claude Code, Claude Desktop Pro/Free, ChatGPT Plus+, ChatGPT Free, Codex CLI).
- `73a1d4b docs(handoff): day-6 evaluation report — MERGE-READY` — eval report.
- (Plus the handoff-doc closure commit that follows this entry.)

**Verdict:** MERGE-READY via `/tmp/day06-eval.sh`. All 8 criteria pass.

**Research note recommendation for Codex: READY.** Codex CLI ships native MCP over stdio at `~/.codex/config.toml` in TOML format. No tier gating. Full working snippet shipped in INSTALL.md § "OpenAI Codex CLI config". Known limitation: Codex's supported feature set per modelcontextprotocol.io/clients is `Resources, Tools, Elicitation` — Prompts not surfaced. project-brain's 17 prompts won't appear in Codex's UI but the `run_skill(name)` tool is available as a fallback.

**Deviations from spec:**

1. **ChatGPT Desktop architecture diverges from the spec's assumptions.** The handoff assumed ChatGPT would work like Claude Desktop with an `mcpServers` JSON config file. Research turned up: ChatGPT Desktop only accepts **remote HTTP/SSE endpoints** via Settings → Connectors (Developer mode). It does NOT host local stdio MCP servers. To use project-brain (stdio), users must run a local `mcp-remote` bridge at `http://localhost:8787/sse` and then add that URL as a custom connector in ChatGPT's UI. The INSTALL.md § "ChatGPT Desktop config" documents this honestly: bridge command + ChatGPT connector UI flow + tier note (Plus/Pro/Team/Enterprise; Free excluded entirely from MCP). Day-7's E2E demo will validate end-to-end.

2. **Task 2 and Task 3 INSTALL.md edits bundled into one commit.** The spec's commit guide describes two separate commits, but both new sections (ChatGPT + Codex) landed in one Edit hunk before staging. The standing instruction "Don't rewrite history" (carried forward from day-5) prevents splitting via `git reset --soft HEAD~1`. The single commit `51c30dd docs(install): add ChatGPT Desktop config section` contains both new sections; reviewers see the union diff. Documented in the eval report's § "Script adjustments".

3. **compat-matrix.md has 6 host rows instead of the spec's 5.** ChatGPT Free gets its own row to make the "not supported" fact unmissable. Eval criterion 3 requires ≥5 data rows; 6 satisfies that with margin.

4. **All `grep` invocations in the eval script use `command grep`** to bypass the user's interactive-shell alias that routes `grep` through Claude Code's ugrep wrapper. Standing workaround from days 1–5.

5. **Test-suite check accepts 4 PromoteLocalTests failures as a passing baseline** — pre-existing bash 3.2 `declare -A` issue from before day-1. Same exclusion pattern as days 3–5.

**Notes for day-7 / day-8:**

- **Day-7 (ChatGPT E2E demo):** the bridge command `npx -y mcp-remote http://localhost:8787/sse --transport stdio --command "uvx" --args "project-brain-mcp"` needs validation on a real Claude Desktop install with the `mcp-remote` package available. If `mcp-remote` doesn't accept exactly those flags, the INSTALL.md section needs adjustment. Run the demo on Plus tier; document the connector-add UI walkthrough.
- **Day-8 (Codex E2E demo):** test the `codex mcp add project-brain -- uvx project-brain-mcp` CLI command path AND the manual TOML edit path. Confirm `PROJECT_BRAIN_HOME` propagates correctly (TOML's nested `[mcp_servers.project-brain.env]` table). Confirm the "Prompts not surfaced" limitation matches reality (the 17 tools should work; the 17 prompts should be invisible to the user but visible via `prompts/list` if poked directly).
- **mcp-remote stability:** the bridge isn't an OpenAI-owned tool; it's a community npm package (`mcp-remote` on npm). Day-7 should pin a version in the INSTALL.md snippet if stability becomes a concern.
