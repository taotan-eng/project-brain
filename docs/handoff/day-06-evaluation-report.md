# Day-6 Evaluation Report

- Generated: 2026-05-16T15:08:14Z
- Plan reference: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md` § 4 (week 2 day 1)
- Handoff: `docs/handoff/day-06-chatgpt-codex-config.md`
- Predecessor: day-05 (merged to main via PR #5, commit 48b3eb4)
- Week 2 day 1: opens the cross-vendor reach phase (ChatGPT + Codex)

## Script adjustments from handoff spec

Three adjustments to the handoff's embedded evaluation script, all transparently documented:

1. **All `grep` invocations use `command grep`** to bypass the user's interactive-shell alias that routes `grep` through Claude Code's `ugrep` wrapper. Carried forward from days 1-5.
2. **Criterion 7 test-suite check** accepts "4 PromoteLocalTests failures and no others" as a passing baseline. Pre-existing bash 3.2 `declare -A` issue; same exclusion as day-3/4/5.
3. **Task 2 + Task 3 INSTALL.md edits bundled into one commit** (`51c30dd`). The spec's Task 2 and Task 3 each describe a separate commit, but both new sections (`## ChatGPT Desktop config` and `## OpenAI Codex CLI config`) landed in one edit hunk before staging, and the standing instruction "Don't rewrite history" prevents splitting after the fact. The commit's diff is the union of both sections; criterion 8 still passes because the message uses Conventional Commits format (`docs(install): add ChatGPT Desktop config section`).

## Architecture note: ChatGPT requires a bridge

Research turned up that ChatGPT Desktop only accepts **remote** MCP endpoints (HTTP/SSE URLs added via Settings → Connectors → Developer mode), not local stdio servers like Claude Desktop does. project-brain is a stdio server. To use it with ChatGPT, users run a local `mcp-remote` bridge that exposes the stdio process at `http://localhost:8787/sse`, then point ChatGPT at that URL. INSTALL.md § "ChatGPT Desktop config" documents the full flow. Day-7's E2E demo will validate end-to-end.

## Codex MCP research summary

Codex CLI ships native MCP over stdio. Config at `~/.codex/config.toml` in TOML format (NOT JSON). Recommendation: **READY** — full working snippet shipped in INSTALL.md. Known limitation: Codex's MCP feature set is `Resources, Tools, Elicitation` per modelcontextprotocol.io/clients — Prompts are not surfaced. The 17 tools and 3 resources work normally; the 17 prompts won't appear in Codex's UI but `run_skill(name)` is available as a tool fallback. Full research at `docs/notes/day-06-codex-mcp-support.md`. Day-8 will validate end-to-end.

## Merge criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | ChatGPT Desktop config section | ✓ | section present with mcpServers mention + uvx command. Documents the local-stdio->remote-HTTP bridge (mcp-remote) that ChatGPT requires; tier note (Plus/Pro/Team/Enterprise; Free excluded). |
| 2 | OpenAI Codex CLI config section | ✓ | section present in READY shape (matches research-note recommendation READY). TOML config at ~/.codex/config.toml with full uvx + PROJECT_BRAIN_HOME snippet. |
| 3 | compat-matrix.md with >=5 data rows | ✓ | 8 table rows (1 header + 6 data: Claude Code, Claude Desktop Pro, Claude Desktop Free, ChatGPT Plus+, ChatGPT Free, Codex CLI) |
| 4 | Day-5 Claude content unchanged (additive only) | ✓ | 0 deletions vs main (<=5 tolerated for minor edits); ChatGPT and Codex sections added between Claude Desktop config and Multi-brain setup |
| 5 | Codex research note | ✓ | docs/notes/day-06-codex-mcp-support.md present with Summary + Findings (4 subsections) + Recommendation (READY) |
| 6 | No regression (validator + smoke + no Cowork) | ✓ | validator: 0 errors, 0 warnings (44 artifacts walked).; smoke: PASS; cowork refs in skills/: 0 |
| 7 | Test suite green (modulo bash 3.2 baseline) | ✓ | 4 baseline PromoteLocalTests failures (declare -A on macOS bash 3.2); no new failures |
| 8 | Conventional Commits + smoke-test naming | ✓ | 0 bad test_*.py; 0 non-conventional commit subjects |

## Files changed (this branch vs main)

```
   INSTALL.md                             | 80 ++++++++++++++++++++++++++++++++++
   compat-matrix.md                       | 28 ++++++++++++
   docs/notes/day-06-codex-mcp-support.md | 56 ++++++++++++++++++++++++
   3 files changed, 164 insertions(+)
```

## Commits (this branch)

```
  a2624aa docs: scaffold compat-matrix.md at repo root
  51c30dd docs(install): add ChatGPT Desktop config section
  5693d1f docs(research): document current Codex CLI MCP support status
```

## Verdict: **MERGE-READY**

All eight criteria pass (with three transparently documented script adjustments — see § Script adjustments above). Day-6 ships the docs + matrix that day-7/8 verify end-to-end. The Codex section is READY (working TOML config snippet); the ChatGPT section documents the local-stdio→remote-HTTP bridge path.
