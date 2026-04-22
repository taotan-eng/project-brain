---
name: assign-thread
description: Manage the assigned_to list on a thread. Supports --add (append handles), --remove (delete handles), --set (replace list), and --clear (remove field entirely). Appends an audit-trail line to the thread body recording who made the change, when, and why. Rebuilds thread-index.md and current-state.md. Use when the user says "assign this thread to <handles>", "add <name> to assigned_to", "unassign from <name>", "clear all assignments", or when managing thread ownership.
version: 0.1.3
pack: project-brain
requires:
  - git
  - "read:~/.ai/projects.yaml"
  - "write:[brain-root]"
---

# assign-thread

Teams use the `assigned_to` list to track thread ownership and collaboration scope. This skill is a thin, auditable way to mutate the list per CONVENTIONS § 3.2. It is intentionally policy-neutral — the pack does not enforce any semantics (single owner, multi-collaborator, role-based are all valid). Teams wire enforcement externally via CODEOWNERS, branch protection, or custom CI.

Every assignment change is recorded in an audit trail appended to the thread body (not just frontmatter) so the history is readable without `git log`. The skill stages the thread file, calls `verify-tree --rebuild-index` to regenerate the aggregate snapshots, and commits in one step.

## When to invoke

- "Assign this thread to <handle>"
- "Add <name> to assigned_to"
- "Remove <name> from this thread"
- "Set assigned_to to <list of handles>"
- "Clear assignments — thread has no owner"
- "Reassign the thread from Alice to Bob"

## Inputs

| Name              | Source                          | Required | Description                                                                                     |
|-------------------|---------------------------------|----------|-------------------------------------------------------------------------------------------------|
| `thread_slug`     | user prompt or cwd inference    | yes      | Slug of the thread to modify. Defaults to the thread whose directory contains cwd.              |
| `operation`       | flag (`--add`, `--remove`, `--set`, `--clear`) | yes | Exactly one of the four mutation modes. Mutually exclusive.              |
| `handles`         | user prompt (comma-separated)   | cond.    | List of handles to add/remove/set. Required for `--add`, `--remove`, `--set`; forbidden for `--clear`. |
| `note`            | user prompt                     | no       | Optional free-form note explaining the assignment change (e.g., "handoff to Alice per 1:1").    |
| `actor`           | flag or git config              | no       | Override for "who performed this action" in the audit line. Defaults to `git config user.email`, then `git config user.name`. |
| `push`            | flag (`--push`)                 | no       | Push to the default remote after commit. Default off.                                           |
| `--brain=<path>`  | user prompt or cwd inference    | no       | Absolute path to the brain root. Defaults to the nearest ancestor `thoughts/` directory.        |

Prompt strategy: resolve `thread_slug` from cwd. Ask which operation via `AskUserQuestion` if not supplied as a flag. For each operation, prompt for the handles (none for `--clear`). Optionally prompt for a note. Infer the actor from git config.

| `--dry-run`       | boolean                         | no       | Print the plan (operation, assigned_to changes, audit trail, commit message) without performing any file writes, git mutations, or audit-log writes. See Process § Dry-run semantics. |

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory is inside a brain root (a `thoughts/` directory containing `CONVENTIONS.md`) or an explicit `--brain=<path>` was given.
2. `thoughts/threads/[thread_slug]/thread.md` exists.
3. Thread `status` is `active`, `parked`, or `in-review`. Archived threads are terminal; refuse with guidance to use `update-thread` on the archive if a fix is needed.
4. Exactly one of `--add`, `--remove`, `--set`, `--clear` is supplied. Refuse if zero or more than one.
5. For `--add` and `--set`: `handles` is a non-empty comma-separated list.
6. For `--remove`: `handles` is a non-empty comma-separated list.
7. For `--clear`: no `handles` parameter is given.
8. Working tree has no uncommitted changes to `thoughts/threads/[thread_slug]/thread.md` (don't mix an uncommitted edit into the assign commit). `git status --porcelain thoughts/threads/[thread_slug]/` must be empty.
9. Standard path-traversal guard: `thread_slug` contains only `[a-z0-9-]`, matches the slug in `thoughts/threads/`, and the resolved path is canonical (no `..` escapes).
10. `git config user.email` returns a value (used to populate the actor in the audit line if `--actor` not supplied).

## Process

Each step is atomic. Failure at step N leaves the tree in whatever state it was after step N-1.

1. **Resolve inputs.** Infer `thread_slug` from cwd. If `operation` is not a flag, ask via `AskUserQuestion` which of the four modes to run. Prompt for operation-specific inputs (`handles`, `note`). Infer `actor` from `git config user.email` or `git config user.name` as fallback (or use `--actor` override).
2. **Validate preconditions.** Run checks 1–10 above. On any failure, stop and report the specific precondition.
3. **Load thread frontmatter.** Read `thoughts/threads/[thread_slug]/thread.md` and parse the YAML frontmatter. Detect the current `assigned_to` value (if absent, treat as an empty list).
4. **Compute new `assigned_to` value per operation.**
   - **`--add`**: append each handle in `handles` to the current list. Skip handles already present (idempotent); note skipped handles in the operation report. If the list was absent, create it with the new handles.
   - **`--remove`**: remove each handle in `handles` from the current list. Skip handles not present (idempotent); note skipped handles. If removal leaves the list empty, keep an empty list (not absent) — explicit "unassigned" is a valid state.
   - **`--set`**: replace the entire list with `handles`. If `handles` is empty, set the list to empty (not absent).
   - **`--clear`**: delete the `assigned_to` field entirely (set to absent, not empty). Use when a thread genuinely has no owner/policy.
5. **Update frontmatter.** Modify `thoughts/threads/[thread_slug]/thread.md` frontmatter to the new `assigned_to` value (or remove the field for `--clear`). Leave all other frontmatter unchanged.
6. **Append audit line.** Create or find the `## Assignment history` section at the bottom of the thread markdown body. If the section does not exist, create it. Append a new line in this format:

```
- {{ISO-8601 UTC timestamp}} — {{actor}} — assign-thread: {{operation}} {{handles-involved}}{{ — note if set}}
```

Example:
```
- 2026-04-22T15:34:12Z — alice@example.com — assign-thread: add alice,bob — handoff to Alice per 1:1
```

The operation string is one of: `add`, `remove`, `set`, or `clear`. The `{{handles-involved}}` is the comma-separated list of handles touched (for `clear`, this is `(field removed)`). The note is included iff supplied, prefixed by `—`.

7. **Stage thread file.** Run `git add thoughts/threads/[thread_slug]/thread.md`.
8. **Final step — rebuild indexes.** Invoke `verify-tree --rebuild-index`. Handle exit codes per the Stage 2 contract (see § Rebuild contract):
   - Exit 0: proceed to commit.
   - Exit 1 (source validation failure): abort with repair hint.
   - Exit 2 (write / verify failure): abort, filesystem issue.
9. **Commit.** Stage both index files and the thread directory in one commit:

```
git add thoughts/threads/[slug]/ thoughts/thread-index.md thoughts/current-state.md
git commit -m "assign-thread: [slug] [operation] [handles]"
```

Commit message format follows § 11.6 conventions (scope is the thread slug, subject is the operation and handles).

10. **Push (optional).** If `--push` was set, run `git push` to the default remote. Otherwise, skip.
11. **Report.** Return a confirmation summary: old `assigned_to` list, new list, commit SHA, and the audit-trail entry written.

No automatic push by default — matches `update-thread` and `park-thread` conventions.

### Dry-run semantics

When `--dry-run` is set:

1. **Run all preconditions**, including thread existence, working-tree cleanliness, and validation of any new handles against an optional project-specific allow-list (if the project wires one). Exit 1 if any precondition fails.
2. **Compute the full plan:** the old `assigned_to` list, the new `assigned_to` list after applying the requested operation (`--add`, `--remove`, `--set`, `--clear`), the audit-trail line that would be appended to the thread body's `## Assignment history` section (`YYYY-MM-DD — <actor> — <op>: <handles>`), whether the section would be created or amended, and the commit message.
3. **Invoke `verify-tree --rebuild-index --dry-run`** to surface any index-rebuild failures before committing. If that fails, print the rebuild error and exit 1.
4. **Write NOTHING to disk:** no thread.md edits, no index-file edits, no audit-log writes.
5. **Invoke NO git mutations:** no `git add`, no `git commit`, no `git push` (even if `--push` was also supplied — dry-run dominates). Read-only git operations (`git status`, `git config user.email`) are allowed.
6. **Exit 0** if the plan would succeed end-to-end, **exit 1** if any precondition or rebuild-dry-run check failed, **exit 2** on unexpected error.

Print the plan to stdout including a clear "before" and "after" view of the `assigned_to` list and the verbatim audit line. Under future audit-log wiring (per `AUDIT-LOG.md`), a record with `"dry_run": true` is appended; the v0.9.0-alpha.4 stub is spec-only, so no audit write happens either way.

## Side effects

### Files written or modified

| Path (relative to brain root)    | Operation         | Condition                                              |
|----------------------------------|-------------------|--------------------------------------------------------|
| `threads/[slug]/thread.md`       | edit (frontmatter + body) | all operations         |
| `thread-index.md`                | edit              | rebuild step (all operations)                          |
| `current-state.md`               | edit              | rebuild step (all operations)                          |

### Git operations

| Operation                              | Trigger | Notes                                                            |
|----------------------------------------|---------|-------------------------------------------------------------------|
| `git add thoughts/ && git commit -m …` | step 9  | Single commit per invocation                                      |
| `git push` (if `--push`)               | step 10 | Optional; not run by default                                      |

### External calls

- `verify-tree --rebuild-index` in step 8 (via `Bash` or equivalent).

## Outputs

**User-facing summary.** A short message with:

- The commit SHA.
- The operation performed (`add`, `remove`, `set`, `clear`).
- Old and new `assigned_to` lists (or note if field was absent).
- Handles that were skipped (if any) with a brief explanation.
- The audit-trail entry that was appended.
- A next-step suggestion (e.g., "Assigned to alice,bob. Run `discover-threads --assigned=alice` to find all threads assigned to Alice.").

**State passed forward.**

- `thread_slug` — unchanged from input.
- `assign_commit` — SHA of the single commit.
- `operation` — the operation that ran (`add`, `remove`, `set`, or `clear`).
- `new_assigned_to` — the resulting list (empty list if cleared or empty after removal, absent if `--clear`).

## Frontmatter flips

| File                          | Field             | Before           | After                       | Operation |
|-------------------------------|-------------------|------------------|------------------------------|-----------|
| `threads/[slug]/thread.md`    | `assigned_to`     | current list (or absent) | new list per op    | add/remove/set |
| `threads/[slug]/thread.md`    | `assigned_to`     | current list     | *(removed)*                  | clear     |

No other fields are touched. `status`, `maturity`, `parked_*`, `archived_*` are never written by this skill.

## Postconditions

- Thread directory unchanged at `threads/[slug]/`. Nothing moved, no content deleted.
- Thread `assigned_to` frontmatter matches the new computed value (or field absent if `--clear`).
- Thread body has a new audit-trail line under `## Assignment history`.
- `thread-index.md` and `current-state.md` reflect the post-operation state of all threads (autogenerated).
- Exactly one commit was added.
- `verify-tree` passes on the updated thread.

## Failure modes

| Failure                                        | Cause                                                                         | Response                                                               |
|------------------------------------------------|-------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| Brain root not found                           | No `thoughts/CONVENTIONS.md` up the tree; no `--brain` given                  | refuse — prompt user to `init-project-brain`                           |
| Thread slug does not resolve                   | Typo; wrong cwd                                                               | refuse — list nearby slugs (levenshtein) and re-prompt                 |
| Thread in `archived`                           | Terminal state                                                                | refuse — suggest archiving was final or manual fix needed              |
| Multiple mutation flags supplied               | `--add` + `--remove` or similar                                               | refuse — clarify that exactly one operation per invocation             |
| No mutation flag supplied                      | User forgot to specify an operation                                           | refuse — ask which operation via `AskUserQuestion`                     |
| `--clear` with non-empty `handles`             | Conflicting args                                                              | refuse — `--clear` takes no handles                                    |
| Empty `handles` for `--add`, `--remove`, `--set` | Invalid input                                                                | refuse — ask for a non-empty handle list                               |
| Uncommitted edits to thread.md                 | Concurrent edit risk                                                          | refuse — ask user to commit or stash                                   |
| `git config user.email` empty (no `--actor`)   | Git not configured                                                            | refuse — ask user to configure git or supply `--actor`                 |
| Rebuild source-validation failure              | Thread frontmatter schema violations                                          | refuse — report violating thread; user must repair before retrying     |
| Rebuild write failure                          | Filesystem / permissions issue                                               | refuse — live index files unchanged (atomic); report error             |
| Path traversal attempt in `thread_slug`        | Malicious or malformed slug (e.g., `../../../etc/passwd`)                    | refuse — reject slug, report invalid characters                        |

## Related skills

- **`discover-threads --assigned=<handle>`** — find threads assigned to a given handle (not yet implemented; design sketch in pack roadmap).
- **`update-thread`** — for other structured thread edits (maturity, candidates, soft_links).
- **`park-thread`**, **`discard-thread`** — other lifecycle operations; coordinate with assignment (e.g., unassign on discard).
- **`verify-tree`** — run anytime to validate the tree; called automatically by this skill.

## Asset dependencies

None. The skill emits the audit-trail line inline (format defined in § Process step 6); it does not read any templates from the pack's `assets/` directory.

| Asset path | Used at step | Purpose |
|------------|--------------|---------|
| _(none)_   | _(n/a)_      | _(n/a)_ |

## Security / Privacy

- **Handle format is open.** Handles are written as given; no validation that they match a particular format (GitHub username, email, Slack @-handle, etc.). If a team uses emails, the emails end up in git — this is an intentional design choice per CONVENTIONS § 3.2 note, not a bug. Teams with privacy concerns should set a clear policy on what formats are acceptable.
- **Actor field in audit line.** The `--actor` parameter allows override of who is credited in the audit-trail line. An unscrupulous actor could set `--actor=alice@example.com` to impersonate. The git commit author (visible in `git log`) is the canonical record of who actually ran the skill; the audit line is convenience documentation for quick reading. Projects can validate the two match in CI if desired.
- **No external validation.** The skill does not check if handles are valid in any external system (no LDAP lookup, no GitHub user check, etc.). This keeps the skill lightweight and offline. Validation is a team policy matter.

## Versioning

**0.1.3** (unreleased — Stage 4 of v0.9.0 cut) — added the missing `Asset dependencies` section so the SKILL.md conforms to the full 12-section contract in `skill-contract-template.md`. No behavior change.

**0.1.2** — Added `--dry-run` flag specification with full semantics contract.

**0.1.0** — initial release (Stage 3 of v0.9.0, landed after v0.9.0-alpha.2 which added the `assigned_to` field). Single operation per invocation. Audit trail model. Stage 2 rebuild contract.
