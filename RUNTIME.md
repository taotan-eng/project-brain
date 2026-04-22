# Runtime compatibility

## TL;DR

The project-brain pack is **portable across six runtimes** (Claude Code, Claude Desktop / Cowork, Codex, Gemini CLI, Cursor, Aider) with gracefully documented degradations. All runtimes require a POSIX filesystem and git. Promote/finalize/discard-promotion skills hard-refuse without `gh`. Multi-agent-debate open mode degrades to scaffold-and-refuse on runtimes without subagent spawning. Every SKILL.md is a standalone instruction sheet that any runtime can follow.

| Runtime | Skill invocation | Subagent spawn | `gh` required | Verified | Notes |
|---------|---|---|---|---|---|
| Claude Code | native `skill:` | yes (Task tool) | yes | **verified** | reference implementation |
| Claude Desktop / Cowork | native `skill:` | yes | yes | **verified** | identical to Claude Code |
| Codex | prompt-driven | via sub-session | yes | **expected** | manual SKILL.md invocation |
| Gemini CLI | prompt-driven | varies (unknown) | yes | **expected** | undocumented subagent model |
| Cursor | prompt-driven or MCP | varies (unknown) | yes | **expected** | MCP support unverified |
| Aider | prompt-driven | no (single-session) | yes | **expected** | file-editing focus; good fit for tree/thread work |

## How portability works in this pack

Every SKILL.md is a standalone instruction sheet. Even runtimes with no native skill invocation concept can follow the **Process** section manually, or hand the SKILL.md to an LLM and ask it to execute step-by-step.

`CONVENTIONS.md` is read by skills at runtime — not by humans — to resolve frontmatter schemas, validator invariants, lifecycle transitions, and naming rules. This means all skills inherit schema changes automatically without per-skill edits.

Assets (templates, prompt scaffolds) and scripts (validator, context materializer) live at predictable paths (`assets/`, `scripts/`) that each skill references. The pack does not hard-code paths relative to any one runtime; install instructions provide three layouts (Claude Code, generic manual, Aider-specific), and each is equally first-class.

Capabilities are explicitly required and documented. When a capability is absent, the skill either hard-refuses with clear error messages (e.g., "install `gh`") or gracefully degrades (e.g., multi-agent-debate scaffold-and-refuse when subagents unavailable).

## Capability matrix

| Capability | Required by | Criticality | If absent |
|---|---|---|---|
| POSIX filesystem + Read/Write/Edit | all 14 skills | hard | no fallback — inherent to pack design |
| shell (bash 3.2+) | every skill that commits to git | hard | no fallback — git needs a shell |
| `git` 2.30+ | every skill that commits | hard | no fallback — inherent |
| `gh` CLI 2.0+ | `promote-thread-to-tree`, `finalize-promotion`, `discard-promotion` | **hard** | skill refuses; user must install; no silent degrade |
| Python 3.10+ | `verify-tree` only | hard for verify-tree | port `scripts/verify-tree.py` to your language; invariant registry (V-01..V-21, N-01..N-04) is language-neutral |
| `AskUserQuestion` or equivalent | `init-project-brain`, `multi-agent-debate`, `park-thread`, others | soft | degrade: accept answers via CLI flags (`--domain-list=...`) or single-prompt form |
| Subagent spawning (Task tool or equivalent) | `multi-agent-debate` open mode only | **partial** | `multi-agent-debate` open mode writes prompt scaffolds to `tryouts/`, refuses, and user spawns reviewers externally; close mode works without subagents |
| MCP connectors | `materialize-context` for `mcp://` URIs | soft | `mcp://` refs resolve to "Unresolved ref" in `context.md`; all other schemes work |
| Native skill invocation syntax | none — all skills are instruction sheets | soft | read SKILL.md manually and follow the Process section; works on any runtime that can read files and follow English prose |

## Per-runtime matrix

### Claude Code — reference implementation, **verified**

**Verified:** Pack maintainers ran all 14 skills end-to-end during v0.9.0-alpha.3 cut.

All capabilities present. Native `skill:` invocation. `AskUserQuestion` supported. `Task` tool spawns subagents. `gh` and bash available in the IDE's shell. Project registry at `~/.ai/projects.yaml` works as documented. No degradations.

Install: Use the "Claude Code specific prompt" from README.md § "Install by pointing an AI agent at the repo" or manual layout at `.claude/skills/project-brain/`.

### Claude Desktop / Cowork — reference implementation, **verified**

**Verified:** Identical runtime to Claude Code; same tool suite + Cowork-specific mcp__cowork__* tools for context materialization.

All capabilities present. Native `skill:` invocation. Same subagent, AskUserQuestion, and shell support as Claude Code. No degradations.

Install: Same prompt as Claude Code; Cowork's skill discovery is identical.

### Codex — **expected**, not exhaustively verified

**Expected:** Codex has documented bash/git access. Skill invocation unverified; subagent model assumed via documentation.

**Skill invocation:** Prompt-driven. User opens `skills/<skill-name>/SKILL.md`, reads the Process section, and follows it manually. The pack provides no Codex-native invocation syntax; the SKILL.md prose *is* the interface.

**Subagent spawn:** Codex can create sub-sessions. `multi-agent-debate` open mode works if the user spawns reviewer sessions in parallel. Otherwise, degrades to scaffold-and-refuse: skill writes per-reviewer prompts to `tryouts/`, refuses, and user collects outputs manually.

**Capabilities:**
- `gh`: present in Codex shell; `promote-thread-to-tree` and finalize/discard work as documented.
- `AskUserQuestion`: absent. Skills that prompt accept answers via flags (`--domain-list=...`, `--personas=...`) or fall back to inline single-prompt form.
- Filesystem + git + bash: fully supported.

**Known degrade paths:**
- `multi-agent-debate` open mode: scaffold-and-refuse if subagent spawn unavailable.
- `init-project-brain`: falls back to flag-driven input (`--project-alias=..., --domains=...`) instead of interactive `AskUserQuestion`.
- `materialize-context`: works for all URI schemes except `mcp://` (no MCP connector); `mcp://` refs log as unresolved.

**Install:** Manual layout at `thoughts/.pack-skills/` or wherever Codex expects user-provided tools. Copy `CONVENTIONS.md` to `thoughts/`. Follow INSTALL.md § 2b step-by-step.

### Gemini CLI — **expected**, not exhaustively verified

**Expected:** Assumed similar to Codex. Subagent model and native tool support not documented in pack repo.

**Skill invocation:** Prompt-driven; same as Codex.

**Subagent spawn:** Unknown. Conservatively assume: absent or unreliable. `multi-agent-debate` open mode degrades to scaffold-and-refuse. Close mode works.

**Capabilities:**
- `gh`: assumed available (CLI access standard); `promote-thread-to-tree` etc. work if authenticated.
- `AskUserQuestion`: absent. Flags + fallback prompts.
- Filesystem + git + bash: fully supported.

**Known issues (unverified, assume from Codex parity):**
- Same multiagent degrade as Codex.
- `materialize-context` MCP refs: unresolved.

**Install:** Same as Codex.

### Cursor — **expected**, partially verified via community reports

**Expected:** Cursor has documented bash and file-editing. MCP support unverified in this pack.

**Skill invocation:** Prompt-driven or MCP-driven. If Cursor's MCP support is active, skills *could* be exposed as MCP tools. Otherwise, treat SKILL.md as project documentation and follow Process sections manually. Community reports suggest MCP is opt-in and not standard; default to manual invocation unless the project has explicitly wired MCP.

**Subagent spawn:** Unreliable or absent in the standard Cursor release. If MCP is configured, subagents might be available via MCP. Otherwise, degrade to scaffold-and-refuse.

**Capabilities:**
- `gh`: present; promote trio work.
- `AskUserQuestion`: absent. Flags + fallback.
- Filesystem + git + bash: fully supported.
- MCP: optional; if absent, `materialize-context` cannot resolve `mcp://` refs.

**Known degrade paths:**
- Same multiagent and MCP limitation as Codex.

**Install:** Manual layout. INSTALL.md § 2b. Optionally wire MCP if supported; document the adapter for future users.

### Aider — **expected**, with explicit degradations

**Expected:** Aider is a single-session, file-editing-focused agent. No subagent spawn. Community testing suggests good fit for file-heavy skills.

**Skill invocation:** Prompt-driven. User asks Aider to "follow `skills/<skill-name>/SKILL.md`" and it will read the file and execute steps.

**Subagent spawn:** **Not available.** Single session. `multi-agent-debate` open mode **hard-degrades**: skill writes prompt scaffolds to `tryouts/` and refuses to continue. This is a hard limitation, not a soft fallback — there is no "close mode workaround" that automatically picks up. User *must* manually:
1. Open `tryouts/<persona>.prompt.md` in a second agent / chat window.
2. Run the reviewer manually.
3. Place output in the correct round directory.
4. Re-invoke `multi-agent-debate --close` to finalize.

Alternatively, skip multi-agent-debate for leaf hardening and rely on reviewer feedback gathered offline.

**Capabilities:**
- `gh`: present; promote trio work.
- `AskUserQuestion`: absent. Flags + fallback.
- Filesystem + git + bash: fully supported.
- Subagent spawn: **absent** — hard degrade for open mode, as above.

**Unique strengths:** Aider's surgical file-editing is a natural fit for `promote-thread-to-tree` (stage leaves, land in tree, update NODE.md), `update-thread` (edit candidates), and `finalize-promotion` (flip leaf status, rebuild index). The degrade is isolated to multiagent review; all other skills work well.

**Install:** Manual layout. INSTALL.md § 2b.

## Windows

The pack assumes POSIX paths everywhere. On native Windows (PowerShell, cmd.exe):
- Shell snippets in SKILL.md use `cp -R`, `mkdir -p`, `date -u +...` — these fail on native Windows.
- `materialize-context` uses `$XDG_CACHE_HOME` with fallback to `~/.cache/` — native Windows has no XDG standard.
- Path separators are `\` not `/`.

**Recommendation:** Use **WSL** (Windows Subsystem for Linux). Inside WSL, the pack has no Windows-specific constraints and works identically to Linux/macOS.

A future release may add PowerShell-native equivalents for shell snippets (e.g., Windows batch or PowerShell functions in `scripts/`). Not in scope for v0.9.0.

## Per-skill capability requirements

| Skill | Filesystem | Git | `gh` | Python | Subagents | AskUserQuestion | MCP |
|---|---|---|---|---|---|---|
| `init-project-brain` | yes | yes | no | no | no | yes (fallback: flags) | no |
| `new-thread` | yes | yes | no | no | no | yes (fallback: flags) | no |
| `update-thread` | yes | yes | no | no | no | no | no |
| `park-thread` | yes | yes | no | no | no | yes (fallback: flags) | no |
| `discard-thread` | yes | yes | no | no | no | no | no |
| `promote-thread-to-tree` | yes | yes | **yes** | no | no | yes (fallback: flags) | no |
| `finalize-promotion` | yes | yes | **yes** | no | no | no | no |
| `discard-promotion` | yes | yes | **yes** | no | no | no | no |
| `multi-agent-debate` | yes | yes | no | no | yes (fallback: scaffold-and-refuse) | yes (fallback: flags) | no |
| `materialize-context` | yes | no (git optional) | no | no | no | no | yes (fallback: unresolved) |
| `verify-tree` | yes | no | no | **yes** | no | no | no |
| `discover-threads` | yes | no | no | no | no | no | no |
| `assign-thread` | yes | yes | no | no | no | no | no |
| `review-parked-threads` | yes | no | no | no | no | no | no |

**Key observations:**
- Nine skills (new-thread, update-thread, park-thread, discard-thread, discover-threads, assign-thread, review-parked-threads, materialize-context, verify-tree) have no `gh` or subagent requirement.
- Three skills (promote-thread-to-tree, finalize-promotion, discard-promotion) require `gh` and refuse if absent.
- One skill (multi-agent-debate) requires subagents *only* for open mode; close mode works standalone.
- Only `verify-tree` requires Python; invariant registry is language-neutral so a replacement is straightforward.

## Testing matrix — what we verified

| Verification level | Meaning |
|---|---|
| **Verified** | Pack maintainers ran the skill end-to-end in this runtime during v0.9.0-alpha.3 cut (May 2025). Happy path documented and tested; all preconditions confirmed. |
| **Expected** | The skill has no runtime-specific code path. It reads only documented APIs (git, bash, filesystem, env vars) that are publicly stable on this runtime. Not tested by maintainers but high confidence it works. Degrade paths are documented per the capability matrix. |
| **Unknown** | The skill has not been tested and behavior is uncertain. This status appears only for new runtimes or when a runtime's public API changed since documentation was written. File a pack issue if you try and report results. |

Per-runtime summary:
- **Claude Code, Cowork:** Verified (all 14 skills, all preconditions, all degrade paths).
- **Codex, Gemini CLI, Cursor, Aider:** Expected (all runtimes have stable bash, git, filesystem APIs; documented flag-based fallbacks for AskUserQuestion and subagent spawn; degrade paths tested in principle but not end-to-end).
- No runtimes are "Unknown" at this release.

## Changing runtimes mid-project

Threads and leaves are git-tracked. The tree is portable.

1. **Before switching:** Run `git status`. Commit all pending thoughts under `thoughts/threads/` and `thoughts/tree/`. The brain is version-controlled and carries its state in committed frontmatter.
2. **After switching:** Clone the same repo into the new runtime (or open it if already cloned). Cd into `thoughts/`. Run `verify-tree` to confirm the scaffold is intact (exit code 0).
3. **If a skill fails in the new runtime:** Check the capability matrix and per-runtime section above. The failure is almost always "runtime lacks capability X" — install `gh` if needed, or follow scaffold-and-refuse instructions for multiagent. No data is lost; the failed skill leaves the repo in a clean state.
4. **Resume work:** All per-artifact state (thread frontmatter, leaf status, debate rounds) is in the repo. A different runtime is a toolchain change, not a data migration.

## Reporting compatibility gaps

Found a runtime not listed here, or a skill that fails in an expected way? File an issue at the pack's GitHub repo with this template:

```
**Runtime compatibility report**

- **Runtime:** [name + version]
- **Skills tested:** [list, e.g. new-thread, promote-thread-to-tree, multi-agent-debate]
- **What worked:** [list]
- **What failed:** [skill name + exact error]
- **Environment:** [bash version, git version, presence of `gh`, Python version, OS]
- **Expected behavior:** [what should have happened per the capability matrix]
- **Actual behavior:** [what happened instead]
```

Include full error messages, not summaries. The pack maintainers will use your report to update the expected/unknown labels and add runtime-specific workarounds if feasible.

## Degrade paths summary

| Issue | Skill impact | Degrade |
|---|---|---|
| No `gh` CLI | promote-thread-to-tree, finalize-promotion, discard-promotion | Hard refuse with clear error. No fallback. User must install `gh`. |
| No `AskUserQuestion` | init-project-brain, multi-agent-debate, park-thread, new-thread | Skills accept same answers via CLI flags (e.g., `--domains=eng,product,ops`) or fall back to a single inline prompt. UX tax but functional parity. |
| No subagent spawn | multi-agent-debate open mode | Skill writes reviewer prompts to `tryouts/<persona>.prompt.md`, refuses to continue. User runs reviewers externally (in parallel chat/session), collects outputs, places them in round dir. Then re-invoke skill with `--close`. Close mode works without subagents. |
| No `mcp://` connectors | materialize-context URI resolution | `mcp://` refs log as "Unresolved ref" in context.md. All other schemes work. Soft fail; skill continues. |
| No Python 3.10+ | verify-tree | Skill refuses. User must port `scripts/verify-tree.py` to their language (invariant registry is language-neutral), or skip verification. Community implementation in Go / Bash / TypeScript would be welcome. |
| Native Windows (no WSL) | all skills' shell snippets | Paths fail on `\` separators; builtins (`cp -R`, `mkdir -p`) unavailable. **Use WSL.** No native Windows support in v0.9.0. |

---

**Recommendation for adoption:**

If you are on Claude Code or Claude Desktop / Cowork: **no constraints.** All 14 skills work end-to-end.

If you are on Codex, Gemini, Cursor, or Aider: **all skills work except multi-agent-debate open mode degrades to scaffold-and-refuse.** This is workable if you:
1. Either skip hardening rounds (unlikely for high-stakes decisions), or
2. Run reviewers manually by handing out `tryouts/<persona>.prompt.md` files to teammates or other agent sessions.

For minimal friction, **try Claude Code** if available. The reference implementation has zero degradations.

