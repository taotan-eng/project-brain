# Cowork Tool-Name Audit — Day 1 Report

- Generated: 2026-05-12
- Method: `git grep` against five patterns
- Inputs: all `.md`, `.sh`, `.py` files in the repo (excluding `.git/`)
- Source command:

```bash
git grep -nE '(\$\{CLAUDE_PLUGIN_ROOT\}|AskUserQuestion|TodoWrite|mcp__cowork__|mcp__visualize__)' \
  -- '*.md' '*.sh' '*.py'
```

## Totals

Counts below are exact substring occurrences (a single line containing two patterns is counted once per pattern).

| Pattern | Occurrences |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | 37 |
| `AskUserQuestion` | 65 |
| `TodoWrite` | 0 |
| `mcp__cowork__` | 1 |
| `mcp__visualize__` | 0 |
| **Total** | **103** |

Distinct lines (raw `git grep` lines): 99
Distinct files affected: 33

### Per-file hit counts (top to bottom)

| File | Lines |
|---|---|
| `RUNTIME.md` | 12 |
| `skills/promote-thread-to-tree/SKILL.md` | 11 |
| `skills/init-project-brain/SKILL.md` | 8 |
| `skills/assign-thread/SKILL.md` | 6 |
| `skills/record-artifact/SKILL.md` | 5 |
| `skills/new-thread/SKILL.md` | 5 |
| `scripts/promote-local.sh` | 5 |
| `skills/update-thread/SKILL.md` | 4 |
| `commands/promote-thread-to-tree.md` | 4 |
| `skills/review-thread/SKILL.md` | 3 |
| `skills/restore-thread/SKILL.md` | 3 |
| `skills/park-thread/SKILL.md` | 3 |
| `skills/discard-thread/SKILL.md` | 3 |
| `scripts/diagnostics/analyze-cycles.py` | 3 |
| `skills/multi-agent-debate/SKILL.md` | 2 |
| `skills/list-threads/SKILL.md` | 2 |
| `skills/discard-promotion/SKILL.md` | 2 |
| `skill-contract-template.md` | 2 |
| `CONVENTIONS.md` | 2 |
| `skills/verify-tree/SKILL.md` | 1 |
| `skills/finalize-promotion/SKILL.md` | 1 |
| `PORTING.md` | 1 |
| 11 × `commands/*.md` (one hit each) | 11 |

> **Scope flag (per handoff escalation conditions):** total occurrences (103) and distinct-line count (99) both exceed the ~50-line escalation threshold. Day 2 scope is materially larger than the original estimate; recommend re-baselining day-2 effort before starting. See "Notes for day 2" below.

## By file

### `CONVENTIONS.md`

- L476: `4. Any probe fails → present one \`AskUserQuestion\` with three options:`
- L659: `> **Agents reading this section: do NOT copy any name shown below into a thread's \`tree_domain\`, into a staged path under \`tree-staging/\`, or into a \`--allow-domain\` flag. These are illustrations o...`

### `PORTING.md`

- L116: `\`AskUserQuestion\` tool. In your adapter, use whatever clarification`

### `RUNTIME.md`

- L35: `| \`AskUserQuestion\` or equivalent | \`init-project-brain\`, \`multi-agent-debate\`, \`park-thread\`, others | soft | degrade: accept answers via CLI flags (\`--domain-list=...\`) or single-prompt form |`
- L46: `All capabilities present. Native \`skill:\` invocation. \`AskUserQuestion\` supported. \`Task\` tool spawns subagents. \`gh\` and bash available in the IDE's shell. Project registry at \`~/.config/project-b...`
- L52: `**Verified:** Identical runtime to Claude Code; same tool suite + Cowork-specific mcp__cowork__* tools for context materialization.`
- L54: `All capabilities present. Native \`skill:\` invocation. Same subagent, AskUserQuestion, and shell support as Claude Code. No degradations.`
- L68: `- \`AskUserQuestion\`: absent. Skills that prompt accept answers via flags (\`--domain-list=...\`, \`--personas=...\`) or fall back to inline single-prompt form.`
- L73: `- \`init-project-brain\`: falls back to flag-driven input (\`--project-alias=..., --domains=...\`) instead of interactive \`AskUserQuestion\`.`
- L88: `- \`AskUserQuestion\`: absent. Flags + fallback prompts.`
- L107: `- \`AskUserQuestion\`: absent. Flags + fallback.`
- L132: `- \`AskUserQuestion\`: absent. Flags + fallback.`
- L153: `| Skill | Filesystem | Git | \`gh\` | Python | Subagents | AskUserQuestion | MCP |`
- L186: `- **Codex, Gemini CLI, Cursor, Aider:** Expected (all runtimes have stable bash, git, filesystem APIs; documented flag-based fallbacks for AskUserQuestion and subagent spawn; degrade paths tested i...`
- L221: `| No \`AskUserQuestion\` | init-project-brain, multi-agent-debate, park-thread, new-thread | Skills accept same answers via CLI flags (e.g., \`--domains=eng,product,ops\`) or fall back to a single inli...`

### `commands/assign-thread.md`

- L6: `Run the \`assign-thread\` skill. Derive operation from language: "assign X to bob" → \`--add bob\`, "unassign bob from X" → \`--remove bob\`, "only alice owns X now" → \`--set alice\`, "clear assignments o...`

### `commands/discard-thread.md`

- L6: `Run the \`discard-thread\` skill. Derive \`--reason\` from the user's stated motivation ("this approach didn't pan out", "dupe of X"); only ask if absent. Invoke \`${CLAUDE_PLUGIN_ROOT}/scripts/discard-...`

### `commands/init-project-brain.md`

- L5: `Run the \`init-project-brain\` skill to scaffold a project-brain directory into the current project. Invoke \`${CLAUDE_PLUGIN_ROOT}/scripts/init-brain.sh\` directly — the script auto-detects the projec...`

### `commands/list-threads.md`

- L6: `Run the \`list-threads\` skill — pure read-only thread query. Invoke \`${CLAUDE_PLUGIN_ROOT}/scripts/list-threads.sh\` once with \`--brain=<path>\` plus filter flags derived from the user's question. Exa...`

### `commands/new-thread.md`

- L6: `Run the \`new-thread\` skill to scaffold a fresh thread under \`threads/<slug>/\`. Derive \`slug\`, \`title\`, and \`purpose\` from the user's own message where possible ("start a thread about auth" → \`slug=...`

### `commands/park-thread.md`

- L6: `Run the \`park-thread\` skill. Derive mode + reason from language: "park this for now, waiting on X" → \`--reason='waiting on X'\`; "pick this back up, X just landed" → \`--unpark --trigger='X landed'\`....`

### `commands/promote-thread-to-tree.md`

- L10: `Run \`ls project-brain/tree/\` to gather existing folders. Then invoke \`AskUserQuestion\`:`
- L16: `**Forbidden:** deriving \`$DOMAIN\` from thread frontmatter \`tree_domain\`, existing-folder count, prior \`promoted_to\`, content topic, or any other context. Only the user's \`AskUserQuestion\` answer in...`
- L22: `4. Any probe fails → AskUserQuestion with three options: **Stay local** (default), **Set up git** (print fix commands, exit), **Cancel**.`
- L24: `**For \`--mode=local\`** — one tool call to \`${CLAUDE_PLUGIN_ROOT}/scripts/promote-local.sh\`, **passing \`--allow-domain=$DOMAIN\`** (the user's Step 0 answer). Requires leaves pre-staged at \`threads/<...`

### `commands/record-artifact.md`

- L6: `Run the \`record-artifact\` skill. Derive \`--slug\` from cwd (nearest \`threads/<slug>/\` ancestor), \`--title\` from the user's framing, and \`--artifact-kind\` from language ("debate result" → \`debate\`, "...`

### `commands/restore-thread.md`

- L6: `Run the \`restore-thread\` skill. Inverse of discard-thread. Invoke \`${CLAUDE_PLUGIN_ROOT}/scripts/restore-thread.sh\` with \`--brain\` and \`--slug\`. The script moves \`archive/<slug>/\` back to \`threads/...`

### `commands/review-thread.md`

- L6: `Run the \`review-thread\` skill. Pure read-only. Derive \`--slug\` from cwd; derive flags from phrasing ("full transcript" → \`--full\`, "last 10" → \`--last=10\`). Invoke \`${CLAUDE_PLUGIN_ROOT}/scripts/re...`

### `commands/update-thread.md`

- L12: `Invoke \`${CLAUDE_PLUGIN_ROOT}/scripts/update-thread.sh\` with \`--brain\`, \`--slug\`, \`--operation\`, plus operation-specific flags. ~120ms.`

### `commands/verify-tree.md`

- L6: `Run the \`verify-tree\` skill. Invoke \`${CLAUDE_PLUGIN_ROOT}/scripts/verify-tree.py --brain=<path>\` to check invariants, or add \`--rebuild-index\` to regenerate \`thread-index.md\` and \`current-state.md...`

### `scripts/diagnostics/analyze-cycles.py`

- L20: `- breakdown by tool type (bash, Read, AskUserQuestion, Edit, etc.)`
- L26: `- Skills with non-zero AskUserQuestion average — the LLM is hedging when`
- L193: `ask_n = c.get("AskUserQuestion", 0)`

### `scripts/promote-local.sh`

- L175: `# user (via AskUserQuestion) before staging.`
- L205: `# topic) instead of actually invoking AskUserQuestion. Stripping the`
- L208: `# AskUserQuestion is the unconditional first action.`
- L215: `is owned by the user and must come from a fresh AskUserQuestion in`
- L222: `No file moves have occurred. To proceed, invoke AskUserQuestion for`

### `skill-contract-template.md`

- L31: `- **user prompt** — if not supplied, ask via \`AskUserQuestion\`.`
- L104: `- **prompt** — skill asks user via \`AskUserQuestion\`.`

### `skills/assign-thread/SKILL.md`

- L39: `Prompt strategy: resolve \`thread_slug\` from cwd. Ask which operation via \`AskUserQuestion\` if not supplied as a flag. For each operation, prompt for the handles (none for \`--clear\`). Optionally pro...`
- L62: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/assign-thread.sh\` ONCE.** No \`Read\` of thread.md, no pre-validation, no \`AskUserQuestion\` about operation mode when the user's own sentence already reveals i...`
- L64: `> **Derive the operation from language.** "Assign X to bob" → \`--add bob\`. "Unassign bob from X" → \`--remove bob\`. "Who's on X?" → use \`review-thread\`, not this. Only use \`AskUserQuestion\` if the u...`
- L66: `> Strip \`${CLAUDE_PLUGIN_ROOT}\` and the bare path resolves against the skill's own dir → "no such file". Keep it.`
- L71: `"${CLAUDE_PLUGIN_ROOT}/scripts/assign-thread.sh" \`
- L173: `| No mutation flag supplied                      | User forgot to specify an operation                                           | refuse — ask which operation via \`AskUserQuestion\`                ...`

### `skills/discard-promotion/SKILL.md`

- L35: `Prompt strategy: infer \`thread_slug\` from cwd; infer \`pr_url\` from \`tree_prs[last]\` when there's one unfinalized. Ask \`delete_branch\` via a single \`AskUserQuestion\` with two options ("Delete the re...`
- L56: `2. **Validate preconditions.** Run checks 1–7. On any failure, stop and report the specific precondition. If \`gh pr view\` returns OPEN, prompt the user via one \`AskUserQuestion\`: "PR is currently O...`

### `skills/discard-thread/SKILL.md`

- L53: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/discard-thread.sh\` ONCE.** No \`Read\` of thread.md, no pre-check of \`tree_prs\`, no \`mv\`, no \`Edit\` of frontmatter. The script reads frontmatter, validates pre...`
- L55: `> **Derive \`--reason\` from context.** The user likely already said WHY they're discarding ("this approach didn't pan out", "dupe of X"). Use that as the reason. Only ask via \`AskUserQuestion\` if th...`
- L60: `"${CLAUDE_PLUGIN_ROOT}/scripts/discard-thread.sh" \`

### `skills/finalize-promotion/SKILL.md`

- L36: `Prompt strategy: infer \`thread_slug\` from cwd; infer \`pr_url\` from \`tree_prs[last]\` when there's only one unfinalized. Ask \`disposition\` via a single \`AskUserQuestion\` with two options ("Keep threa...`

### `skills/init-project-brain/SKILL.md`

- L32: `**Fallback flow: one prompt** if detection lands on source 6 (raw cwd with no git). The ambiguity is real — the agent has no idea where the project should live — so one AskUserQuestion surfaces wit...`
- L53: `| \`project_home\`      | **detected** via \`detect_host_project_root()\` (see preamble); falls through to one AskUserQuestion only when detection returns the raw-cwd source | yes | Absolute path to th...`
- L82: `- If \`brain_path/CONVENTIONS.md\` exists: prompt via AskUserQuestion: \`"A project-brain already exists at <brain_path>. Overwrite (rename existing to project-brain.bak.<YYYYMMDD-HHMMSS>/ and scaffol...`
- L93: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/init-brain.sh\` ONCE. Nothing else.** No \`Read\`, no \`Write\`, no \`mkdir\`, no \`AskUserQuestion\`, no pre-check of anything. The script auto-detects the host proj...`
- L95: `> Strip \`${CLAUDE_PLUGIN_ROOT}\` and you hit "no such file or directory" — the bare path resolves against the skill's own dir. Keep it.`
- L100: `"${CLAUDE_PLUGIN_ROOT}/scripts/init-brain.sh"`
- L107: `The script refuses with exit 1 and prints \`error: project-brain already scaffolded at <path>. Pass --force to back up...\`. Only THEN ask the user via one \`AskUserQuestion\`: "Overwrite the existing ...`
- L216: `| Brain already scaffolded at target     | \`<brain_path>/CONVENTIONS.md\` exists                        | prompt via AskUserQuestion — \`overwrite\` renames existing to \`.bak.<timestamp>/\` and proceed...`

### `skills/list-threads/SKILL.md`

- L76: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/list-threads.sh\` ONCE.** No \`Read\` of thread.md files, no manual frontmatter parsing, no \`glob\` walks. The script enumerates threads, parses frontmatter, app...`
- L92: `"${CLAUDE_PLUGIN_ROOT}/scripts/list-threads.sh" \`

### `skills/multi-agent-debate/SKILL.md`

- L41: `| \`personas\`            | flag or prompt                  | cond.    | Comma-separated list of persona names drawn from § 10.2, e.g. \`--personas=fresh-eyes-reader,red-team,cross-ref-auditor\`. If om...`
- L50: `Prompt strategy: resolve \`artifact_path\` from cwd. Infer \`scope\` from the path prefix. Infer \`mode\` from artifact status and round state. For \`open\`, ask \`personas\` via \`AskUserQuestion\` multi-sele...`

### `skills/new-thread/SKILL.md`

- L39: `Prompt strategy: ask for \`slug\` + \`title\` + \`purpose\` in one \`AskUserQuestion\` call with preview-equivalent text. Resolve \`owner\` from \`--owner <email>\` if supplied; otherwise write the literal pla...`
- L55: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/new-thread.sh\` ONCE.** No \`Read\` of \`config.yaml\`, no \`Read\` of templates, no \`Write\` / \`Edit\` / \`mkdir\`. The script reads config.yaml itself, validates the ...`
- L57: `> **DERIVE \`slug\`, \`title\`, \`purpose\` from the user's own message before asking.** "Start a thread about authentication" → \`slug=authentication\`, \`title="Authentication"\`, \`purpose="thread for auth...`
- L59: `> Strip \`${CLAUDE_PLUGIN_ROOT}\` and the bare \`scripts/new-thread.sh\` resolves against the skill's own dir → "no such file". Keep it.`
- L64: `"${CLAUDE_PLUGIN_ROOT}/scripts/new-thread.sh" \`

### `skills/park-thread/SKILL.md`

- L38: `Prompt strategy: resolve \`thread_slug\` from cwd. Infer \`mode\` from current status; if ambiguous (e.g. skill invoked without context), ask via \`AskUserQuestion\`. For \`park\`, always prompt for \`reaso...`
- L60: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/park-thread.sh\` ONCE.** No \`Read\` of thread.md, no pre-flight status check. The script reads frontmatter, determines park vs unpark (from the thread's curren...`
- L67: `"${CLAUDE_PLUGIN_ROOT}/scripts/park-thread.sh" \`

### `skills/promote-thread-to-tree/SKILL.md`

- L36: `Prompt strategy: one \`AskUserQuestion\` call collects \`leaves\` (multi-select from candidate list) + \`base_branch\` (free-text with \`default_base\` as the preview value) + \`target_remote\` (only if mult...`
- L64: `> **The very first thing this skill does is invoke \`AskUserQuestion\` for the destination tree domain.** Not after staging. Not after mode dispatch. Not after probing config. Step 0, before any othe...`
- L66: `> **Phrasing of the AskUserQuestion** (use exactly this):`
- L80: `>   - Anything else you can derive without invoking \`AskUserQuestion\` THIS TURN.`
- L82: `> **Only valid value source:** the user's answer to \`AskUserQuestion\`, in this turn, captured as a string and passed verbatim through every downstream step (staging path, \`--allow-domain\` flag, lea...`
- L84: `> Backstop: \`promote-local.sh\` refuses to run unless \`--allow-domain=<X>\` is passed and matches the staged path's top-level. The error message does not document a workaround — if you arrive at the ...`
- L90: `AskUserQuestion(`
- L116: `5. If any probe fails → present **one** \`AskUserQuestion\` with three options:`
- L129: `"${CLAUDE_PLUGIN_ROOT}/scripts/promote-local.sh" \`
- L154: `1. Read the thread's \`decisions-candidates.md\`. Present \`locking\` entries to the user via \`AskUserQuestion\` for selection (or accept \`--leaves=<csv>\` verbatim).`
- L197: `1. **Resolve inputs.** Infer \`thread_slug\` from cwd if possible. Read \`decisions-candidates.md\`, present \`locking\` entries to the user via \`AskUserQuestion\` for leaf selection. Read \`~/.config/proj...`

### `skills/record-artifact/SKILL.md`

- L38: `Prompt strategy: ask for \`title\` and body source in one \`AskUserQuestion\` call if not already obvious from the conversation. Infer \`slug\` from cwd (the thread dir the user is working in); fall back...`
- L53: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/record-artifact.sh\` ONCE.** No \`mkdir\`, no \`Write\` of artifact files, no \`Edit\` of transcript.md, no \`verify-tree\` call. The script routes markdown to \`artif...`
- L60: `> Only use \`AskUserQuestion\` if slug OR title genuinely can't be inferred.`
- L65: `"${CLAUDE_PLUGIN_ROOT}/scripts/record-artifact.sh" \`
- L77: `"${CLAUDE_PLUGIN_ROOT}/scripts/record-artifact.sh" \`

### `skills/restore-thread/SKILL.md`

- L46: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/restore-thread.sh\` ONCE.** No \`Read\` of thread.md, no manual \`mv\`, no manual frontmatter edit. The script reads, validates, mutates, moves, rebuilds — all at...`
- L48: `> **Derive \`--reason\` from context** when the user provided one ("I want to bring X back because Y" → \`--reason='Y'\`). Use \`AskUserQuestion\` only if the user gave no rationale and you genuinely don...`
- L53: `"${CLAUDE_PLUGIN_ROOT}/scripts/restore-thread.sh" \`

### `skills/review-thread/SKILL.md`

- L34: `Prompt strategy: infer \`slug\` from cwd. Ask via \`AskUserQuestion\` only if the cwd is outside any thread dir and the user didn't name one.`
- L48: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/review-thread.sh\` ONCE.** No \`Read\` of thread.md, transcript.md, or artifacts — the script parses and renders everything.`
- L60: `"${CLAUDE_PLUGIN_ROOT}/scripts/review-thread.sh" \`

### `skills/update-thread/SKILL.md`

- L42: `Prompt strategy: always resolve \`thread_slug\` from cwd first. Ask \`operation\` via \`AskUserQuestion\` with the six options above. Branch on the answer to collect operation-specific inputs. \`commit-pe...`
- L63: `> **Call \`${CLAUDE_PLUGIN_ROOT}/scripts/update-thread.sh\` ONCE.** No \`Read\` of thread.md, no pre-validation, no \`git\` calls. The script reads frontmatter, applies the operation, rebuilds indexes. R...`
- L71: `> Only use \`AskUserQuestion\` if the user's wording is truly ambiguous.`
- L76: `"${CLAUDE_PLUGIN_ROOT}/scripts/update-thread.sh" \`

### `skills/verify-tree/SKILL.md`

- L35: `Flag handling: verify-tree is the one skill in the pack where flags dominate over \`AskUserQuestion\`. Because it is frequently invoked programmatically by other skills, the interface is designed to ...`

## Day-2 fix strategy (suggested)

For each pattern, the day-2 replacement direction:

| Pattern | Replacement direction |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | Relative path resolution from `$PROJECT_BRAIN_HOME` or pack root detected at runtime. Per-context decision; many references in scripts are legitimate `${CLAUDE_PLUGIN_ROOT}/scripts/...` and need a host-agnostic equivalent. |
| `AskUserQuestion` | "Ask the user to pick between A or B" / "ask the user for X" — describe the interaction, don't name the tool. |
| `TodoWrite` | (none in repo — no work) |
| `mcp__cowork__bash` / `mcp__workspace__bash` | "Run the shell command" — let the host bind to whatever bash tool it provides. (Only one hit — RUNTIME.md L52, a verification claim about Cowork. Likely keep but rephrase as host-specific note in a "Host-specific runtime notes" subsection.) |
| `mcp__visualize__*` | (none in repo — no work) |

Some matches will be in CONVENTIONS.md examples or rationale prose — review case-by-case rather than mechanical replace.

## Notes for day 2

- **`${CLAUDE_PLUGIN_ROOT}` clusters in two predictable patterns:**
  - `${CLAUDE_PLUGIN_ROOT}/scripts/<skill>.sh` in every SKILL.md "Call ONCE" pull-quote and every `commands/<skill>.md` shim — this is ~30 of the 37 occurrences. A single resolver helper (e.g. a `PACK_ROOT` env var or a `resolve_pack_root()` shell function sourced by every script) would let SKILL.md prose drop the env-var name entirely.
  - Backstop "do NOT strip `${CLAUDE_PLUGIN_ROOT}`" callouts in skill prose — these instruct the agent why the env-var prefix matters. After the resolver change, these callouts become obsolete and can be deleted, not rewritten.
- **`AskUserQuestion` clusters in three predictable patterns:**
  - Skill "Prompt strategy" sections (~10 hits) — these describe when the skill prompts. Replace with neutral phrasing: "Ask the user to choose…" or "Prompt for X if not supplied".
  - "Use `AskUserQuestion` only if X" guard rails — these are anti-hedging callouts. Replace with "Only prompt the user if X" or similar.
  - `commands/promote-thread-to-tree.md` Step 0 (4 hits) — load-bearing prompt-priming logic. Demands a careful rewrite: the surrounding instruction (Forbidden / Only valid value source) names the tool explicitly to forbid frontmatter-derived shortcuts. A host-neutral rewrite must preserve that intent.
- **The single `mcp__cowork__` hit (RUNTIME.md L52)** is the *only* Cowork-specific runtime claim in the repo. It is part of a runtime-compatibility matrix already structured to describe each host separately, so the right day-2 action is probably "keep, but mark as Cowork-specific note" rather than remove.
- **Hottest single file:** `skills/promote-thread-to-tree/SKILL.md` (11 hits). This skill's prompt-priming is the most coupled — budget extra time for it on day 2.
- **`scripts/diagnostics/analyze-cycles.py`** references `AskUserQuestion` as a *tool-name key* in a JSON breakdown, not as a tool *invocation*. This is host-coupled telemetry analysis; consider whether the analyzer stays Cowork-specific or generalizes to "interactive-prompt tool" keyed by host adapter.
- **`scripts/promote-local.sh`** has 5 hits — all in comments and refuse-message bodies, none in actual bash logic. Mechanical comment-prose rewrite.
- **Two `commands/*.md` shims** (assign-thread, discard-thread, init-project-brain, list-threads, new-thread, park-thread, record-artifact, restore-thread, review-thread, update-thread, verify-tree — eleven in total) each carry a single `${CLAUDE_PLUGIN_ROOT}/scripts/...sh` invocation on line ~6. If the resolver-helper refactor lands first, these shims become 11 mechanical one-line edits.
