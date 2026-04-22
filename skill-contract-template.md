---
name: [skill-name]
description: "[Single-sentence description that includes trigger keywords; describes what the skill does and when to use it. This is what a calling agent matches against. MUST NOT contain XML-style angle brackets — use square brackets or curly braces for placeholders.]"
version: 0.1.0
pack: project-brain
requires:
  - "[tool or connector, e.g. git, gh, mcp:slack]"
---

# <Skill name>

<One-paragraph elevator pitch — what this skill accomplishes, in the user's voice. This is the first thing a calling agent reads after matching on the description.>

## When to invoke

Concrete triggers. A calling agent uses these to distinguish this skill from peers in the pack.

- <Trigger phrase or user situation>
- <Trigger phrase or user situation>

## Inputs

| Name | Source | Required | Description |
|------|--------|----------|-------------|
| `<arg>` | user prompt | yes | <what it is> |
| `<arg>` | frontmatter | yes | <which file and which field> |
| `<arg>` | env / config | no | <default value and where it's read from> |

Source vocabulary:

- **user prompt** — if not supplied, ask via `AskUserQuestion`.
- **frontmatter** — read from a specific file (always named).
- **env / config** — `~/.ai/projects.yaml`, `CONVENTIONS.md`, or similar; skill must cite which.
- **previous skill output** — passed from a preceding skill in a chain.
- **runtime tool discovery** — e.g. which MCP servers are connected.

## Preconditions

What must be true before the skill can proceed. The skill **refuses** (does not silently fix) if any are not met; it reports the failing precondition and stops.

- <Precondition>
- <Precondition>

## Process

Ordered steps. Each step is atomic: if it fails, the skill stops and reports. No step leaves state half-written — in particular, frontmatter flips and file writes happen in the same commit.

1. <Step>
2. <Step>
3. <Step>

## Side effects

### Files written or modified

| Path (relative to brain root) | Operation | Notes |
|--------------------------------|-----------|-------|
| `<path>` | create / edit / append | <reason> |

### Git operations

| Operation | Trigger | Notes |
|-----------|---------|-------|
| `git checkout -b <branch>` | step N | base is `origin/main` (§ 11.4) |
| `git add … && git commit -m …` | step N | commit message template |
| `gh pr create` | step N | PR body from `assets/pr-body-templates/<kind>.md` |

### External calls

- **<tool or connector>** — <purpose> — <handling when unavailable>

## Outputs

What the skill produces, visible to downstream skills or the user.

- **User-facing summary** — what the chat response contains after success.
- **State passed forward** — file paths, frontmatter fields now populated, PR URLs created, etc.

## Frontmatter flips

Every field the skill modifies, across every file. This is the audit trail — a grep for `status: <value>` should trace back to exactly one skill.

| File | Field | Before | After |
|------|-------|--------|-------|
| `<path>` | `status` | `<before>` | `<after>` |
| `<path>` | `tree_prs[]` | `<list>` | `<list with new entry appended>` |

## Postconditions

What is guaranteed after successful completion. These are the contract the next skill depends on.

- <Postcondition>
- <Postcondition>

## Failure modes

| Failure | Cause | Response |
|---------|-------|----------|
| <name> | <why it happens> | <skill behavior: retry with clarification / prompt user / refuse and exit> |

Responses are limited to:

- **retry** — skill retries internally (bounded attempts).
- **prompt** — skill asks user via `AskUserQuestion`.
- **refuse** — skill exits; user must change state before re-invoking.

## Related skills

- **Precedes:** `<skill-name>` — <how this skill's output feeds the next>
- **Typically followed by:** `<skill-name>` — <natural next step>
- **Compatible with:** `<skill-name>` — <when they compose in parallel or interleave>

## Asset dependencies

Files the skill reads from the pack's `assets/` directory. Listing them here lets `verify-pack` catch dangling references.

- `assets/<template>` — <used at step N>

## Versioning

Semver. Bump the version field in frontmatter when any of the following change:

- **Major** — breaking change to inputs, outputs, or frontmatter flips.
- **Minor** — new optional input, new output field, additional precondition that most callers already satisfy.
- **Patch** — internal refactor, wording fixes, asset updates that don't change behavior.

---

## Template usage notes (remove from actual skill files)

- **Frontmatter constraint: no XML-style angle brackets.** The `description` field (and other frontmatter values) cannot contain `<...>` tokens — the skill-loading validator rejects them as XML tags. Use square brackets `[placeholder]` or curly braces `{{placeholder}}` in example text and avoid angle-bracket placeholders in descriptions entirely. The body of SKILL.md (anything below the frontmatter) has no such restriction.
- Every section above is **required** for a skill to ship. If a section is genuinely empty (e.g. a skill with no git operations), keep the heading and write "None."
- Keep sections in this order. Downstream tooling (`list-pack-skills`, `verify-pack`) parses them positionally.
- The skill's SKILL.md is its complete contract. Additional documentation goes in sibling files (e.g. `DESIGN.md`, `EXAMPLES.md`), not appended to SKILL.md.
- For skills with long internal logic, write the logic in a sibling `PROCESS.md` and keep SKILL.md § Process as a high-level numbered summary that links out.
