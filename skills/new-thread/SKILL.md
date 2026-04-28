---
name: new-thread
description: Scaffold a new private thought thread in the project brain. Creates the thread directory under project-brain/threads/, populates thread.md plus decisions-candidates.md and open-questions.md from templates, and registers the thread in thread-index.md and current-state.md. Use when the user says "start a new thread", "capture an idea", "new thought", "begin thinking about something", or similar.
version: 1.0.0-rc4
pack: project-brain
requires:
  - "read:<brain>/config.yaml"
  - "write:[brain-root]"
---

# new-thread

Scaffolds a fresh private thread so the user can start capturing thoughts. A thread is a directory under `project-brain/threads/<slug>/` containing an initial frontmatter-equipped `thread.md` plus two companion files (`decisions-candidates.md`, `open-questions.md`). The thread is immediately registered in the global `thread-index.md` and `current-state.md` so it is discoverable from the moment it is created.

The skill is deliberately minimal. It does not pre-create optional artifacts (`proposal.md`, `diagrams/`, etc.) — those appear when the thread needs them. Empty scaffolding tends to either be forgotten or filled with filler.

## When to invoke

- "Start a new thread" / "new idea" / "capture a thought"
- "I want to begin thinking about X"
- "Scaffold a thread for <topic>"
- After a conversation where the user says "let's track this as a thread"
- At the start of any substantive investigation the user expects to revisit

## Inputs

| Name                 | Source                              | Required | Description                                                                           |
|----------------------|-------------------------------------|----------|---------------------------------------------------------------------------------------|
| `slug`               | user prompt                         | yes      | Kebab-case identifier per CONVENTIONS.md § 11.1. Short-and-memorable.                 |
| `title`              | user prompt                         | yes      | Human-readable title; matches the H1 in `thread.md`.                                  |
| `purpose`            | user prompt                         | yes      | One-line "what this thread is about." Goes into the `thread-index.md` row.            |
| `owner`              | `--owner <email>` flag, else the placeholder `TODO@example.com` with a TODO marker in the thread body | yes      | Email or github handle. No env-var read in default flow — "setup/capture/refine → Done" runs without any shell call.                                                               |
| `primary_project`    | user prompt (constrained by aliases)| yes      | Key from `<brain>/config.yaml` aliases block. If only one alias exists, default to it. |
| `tree_domain`        | user prompt                         | no       | Guess at where this thread will eventually promote. Nullable.                         |
| `related_projects`   | user prompt                         | no       | Other project aliases this thread touches. Default `[]`.                              |
| `--brain=<path>`     | user prompt or cwd inference        | no       | Absolute path to the brain root. Defaults to the nearest ancestor `project-brain/` directory containing `CONVENTIONS.md`. Use this flag when cwd is outside the brain. |
| `--dry-run`          | boolean                             | no       | Print the plan (new frontmatter, files to create, commit message) without performing any file writes, git mutations, or audit-log writes. See Process § Dry-run semantics. |

Prompt strategy: ask for `slug` + `title` + `purpose` in one `AskUserQuestion` call with preview-equivalent text. Resolve `owner` from `--owner <email>` if supplied; otherwise write the literal placeholder `TODO@example.com` and append a TODO marker to the thread body reminding the user to replace it. **Do NOT run `git config user.email`, do NOT read `$EMAIL`, do NOT run any shell command** — every shell call triggers a permission prompt in agentic IDEs, and rc4's pre-promote flow is "capture → refine → Done, no prompts". Ask for `primary_project` separately (with options from `<brain>/config.yaml` aliases). `tree_domain` and `related_projects` are asked only if the user volunteers or the previous conversation makes them obvious.

## Preconditions

The skill **refuses** if any of these are not met. It does not silently fix.

1. Current working directory is inside a brain root (a `project-brain/` directory containing `CONVENTIONS.md`) or an explicit `--brain=<path>` was given.
2. `<brain>/config.yaml` exists and contains at least one alias, or the user provides `primary_project` explicitly. See CONVENTIONS § 2.
3. The resolved `primary_project` alias has a `brain:` path that matches the current brain root.
4. `project-brain/threads/<slug>/` does not already exist. If it does, skill offers `<slug>-2`, `<slug>-3`, … and asks the user to confirm.
5. `owner` is resolvable. If `--owner <email>` (or the skill-specific equivalent flag) is supplied, use it; otherwise write the literal placeholder `TODO@example.com` with a TODO marker in the thread body. Users can always pass `--owner <email>` explicitly. **No `git` binary is invoked** — rc4 defers git to promote-time.

## Process

> ### ⛔️ HARD CONSTRAINT — ONE TOOL CALL
>
> **Call `${CLAUDE_PLUGIN_ROOT}/scripts/new-thread.sh` ONCE.** No `Read` of `config.yaml`, no `Read` of templates, no `Write` / `Edit` / `mkdir`. The script reads config.yaml itself, validates the slug, scaffolds, and rebuilds indexes. Every pre-script tool call adds 30–60s of Cowork overhead; skip them.
>
> **DERIVE `slug`, `title`, `purpose` from the user's own message before asking.** "Start a thread about authentication" → `slug=authentication`, `title="Authentication"`, `purpose="thread for authentication"`. Only use `AskUserQuestion` if slug/title are genuinely ambiguous (e.g., the user said "new thread" with no topic).
>
> Strip `${CLAUDE_PLUGIN_ROOT}` and the bare `scripts/new-thread.sh` resolves against the skill's own dir → "no such file". Keep it.

**One call, happy path:**

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/new-thread.sh" \
  --brain='<absolute brain path>' \
  --slug='<slug>' \
  --title='<title>' \
  --purpose='<purpose>' \
  [--primary-project='<alias>']  # OMIT — script auto-reads from config.yaml
  [--owner='<email>']            # OMIT unless user supplied one
  [--tree-domain='<slug>']       # OMIT unless user volunteered one
```

The script auto-resolves `--primary-project` from `<brain>/config.yaml` (picks `primary_project:` or the single alias). Pass it explicitly only if the brain has multiple aliases and the user picked a non-primary one. `--brain` can be the nearest ancestor `project-brain/` dir containing `CONVENTIONS.md` — if you can infer it from cwd context without a Read, do; otherwise pass the path already known from the conversation.

What the script does (no need to replicate): slug validation → create `threads/<slug>/` → copy and substitute three templates → run `verify-tree --rebuild-index`. ~90ms, one permission prompt.

**Do not** append to transcript.md in a separate Edit call — `record-artifact --append` is the right skill for transcript additions during a session. `new-thread` just scaffolds.

After success, **report.** Echo the script's stdout in your response message verbatim — don't rely on the Bash tool's result card to display it; the user should see the script's output as part of your reply. No commentary about git, commits, or next steps. At verbosity=terse:

    ```
    Created thread '<slug>' at <brain>/threads/<slug>.
      owner = TODO@example.com placeholder; replace when ready.     # only if placeholder was used
    ```

    Do not mention git, commits, or "run git add". Capture is git-free; promote-time is where git shows up. Telling the user about git at capture cues a mental model this pack has intentionally moved away from.

**On failure**: if the script exits non-zero, the error message names the specific precondition. Report it verbatim. No partial-state recovery — capture is git-free, nothing is committed, and re-invoking with a different `--slug` is always safe.

### Dry-run semantics

When `--dry-run` is set:

1. **Run all preconditions** (steps 1–5 above), including brain-root existence, config.yaml availability, and slug collision check. Exit 1 if any precondition fails.
2. **Compute the full plan:** print the new thread directory path, the three files that would be created (`thread.md`, `decisions-candidates.md`, `open-questions.md`), the resolved frontmatter placeholders (slug, title, owner, created_at, etc.).
3. **Invoke `verify-tree --rebuild-index --dry-run`** to surface any index-rebuild failures. If that fails, print the rebuild error and exit 1.
4. **Write NOTHING to disk:** neither the thread directory, nor `thread-index.md`, `current-state.md`, nor the transcript.
5. **Exit 0** if the plan would succeed end-to-end, **exit 1** if any precondition or rebuild-dry-run check failed, **exit 2** on unexpected error.

Print the plan to stdout in a numbered list format. When exiting 1, also print the failing precondition or rebuild error.

## Side effects

### Files written or modified

| Path (relative to brain root)     | Operation | Notes                                   |
|------------------------------------|-----------|------------------------------------------|
| `threads/<slug>/thread.md`         | create    | From `assets/thread-template/thread.md`  |
| `threads/<slug>/decisions-candidates.md` | create | From template                         |
| `threads/<slug>/open-questions.md` | create    | From template                            |
| `threads/<slug>/transcript.md`     | create    | If `transcript_logging=on` (default); append-only session log |
| `thread-index.md`                  | regenerate | By `verify-tree --rebuild-index` from per-thread frontmatter |
| `current-state.md`                 | regenerate | By `verify-tree --rebuild-index` from per-thread frontmatter |

Brain root is `<project>/project-brain/` (see CONVENTIONS.md § 1). Paths in this table are relative to that directory.

### Git operations

**None.** This skill performs file operations only. The user runs `git add` and `git commit` themselves (§ Git deferred).

When `--dry-run` is set: NO side effects. Stdout output only.

### External calls

None. Purely local filesystem + git operations.

## Outputs

**User-facing summary.** A short message with:

- The created thread path (as a `computer://` link).
- The commit SHA.
- A next-step suggestion: "Open `thread.md` and replace the initial comment with what you're thinking about."

**State passed forward.** The skill's return value to any calling workflow includes:

- `thread_path` — absolute path to the thread directory.
- `thread_slug` — the final slug (after collision resolution).

### Verbosity contract

Reads `verbosity` from `<brain>/config.yaml` (env override: `PROJECT_BRAIN_VERBOSITY`). Defaults to `terse`.

- **terse** (default): one acknowledgement line naming the action + target, then `Done.` No tool-output echo, no "let me..." preamble, no re-stating what was written.
  - Example output: `Writing thread.md + decisions-candidates.md to project-brain/threads/alpha/. Done.`
- **normal**: structured summary of what changed (file paths, frontmatter values), no conversational framing.
- **verbose**: full narration (pre-rc4 default). Use for debugging.

## Frontmatter flips

Placeholders substituted in templates at step 5. The table below maps template placeholders to resolved values.

| File | Placeholder | Source |
|------|-------------|--------|
| `thread.md` | `{{SLUG}}` | input `slug` |
| `thread.md` | `{{TITLE}}` | input `title` |
| `thread.md` | `{{CREATED_AT}}` | step 3 |
| `thread.md` | `{{OWNER}}` | input `owner` |
| `thread.md` | `{{PRIMARY_PROJECT}}` | input `primary_project` |
| `thread.md` | `{{TREE_DOMAIN_OR_NULL}}` | input `tree_domain` or `null` |

No existing artifact's frontmatter is modified by this skill — `new-thread` only creates new files.

When `--dry-run` is set: no files are written; the frontmatter substitutions are described in the plan output instead.

## Postconditions

- `project-brain/threads/<slug>/` exists with three files, all with valid frontmatter.
- `thread.md` has `status: active` and `maturity: exploring`.
- `thread-index.md` and `current-state.md` both reference the new thread (autogenerated).
- A single commit (SHA returned) contains all of the above.
- `verify-tree` (if installed) passes without errors on the newly-created thread.

## Failure modes

| Failure                                | Cause                                                       | Response                        |
|----------------------------------------|-------------------------------------------------------------|----------------------------------|
| Brain root not found                   | No `project-brain/CONVENTIONS.md` up the tree; no `--brain` given | refuse — prompt user to `init-project-brain` |
| `~/.config/project-brain/projects.yaml` missing or empty | Pack not fully initialized                                  | refuse — prompt user to `init-project-brain` |
| Slug collision                         | `project-brain/threads/<slug>/` already exists                   | prompt — suggest `<slug>-2`, `<slug>-3` |
| Invalid slug characters                | Fails § 11.1 regex                                          | prompt — re-ask for slug        |
| Dirty working tree on index files      | Uncommitted edits to unrelated paths (not thread-local)     | refuse — ask user to stash or commit |
| (no failure — `owner` defaults to `TODO@example.com` placeholder when `--owner` not supplied; user fixes later) | — | (this failure mode is retired in rc4) |
| Template file missing from pack        | Pack installation broken                                    | refuse — report broken pack     |
| Rebuild source-validation failure      | Thread frontmatter schema violations                        | refuse — report violating thread; user must repair before retrying |
| Rebuild write failure                  | Filesystem / permissions issue                             | refuse — live index files unchanged (atomic); report error |
| `--dry-run` plan shows a precondition failure | Any precondition failed during dry-run | skill exits 1 after printing the plan and the failing precondition. The plan is still useful: the user sees both what was intended and why it wouldn't work. |

## Related skills

- **Precedes:** `promote-thread-to-tree` — eventually consumes this thread's `decisions-candidates.md` to produce leaves.
- **Precedes:** `materialize-context` — may be called during thread maturation to pull in related material for the author.
- **Typically followed by:** *(none — the user writes in the thread for hours or days before the next skill)*
- **Compatible with:** `verify-tree` — can be invoked after scaffolding to confirm no validator issues.

## Asset dependencies

- `assets/thread-template/thread.md`
- `assets/thread-template/decisions-candidates.md`
- `assets/thread-template/open-questions.md`
- `assets/commit-templates/promote.txt` *(not used directly; new-thread uses a `chore(<slug>):` message)*

## Versioning

**0.2.2** — Added `--dry-run` flag specification with full semantics contract, including exit codes 0/1/2 (2 reserved for unexpected errors).

**0.2.0** — Stage 2 of v0.9.0: index-file updates moved to centralized `verify-tree --rebuild-index` final step; previous inline edits removed.

**0.1.0** — initial draft. Bump to 0.2.0 if any input, output, or precondition changes.
