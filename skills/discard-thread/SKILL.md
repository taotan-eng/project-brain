---
name: discard-thread
description: Kill an active or parked thread before it was ever promoted. Flips status to archived, writes archived_at plus archived_by plus discard_reason, git mv's the thread directory from threads/ to archive/, removes the thread's row from Active or Parked sections of thread-index.md and adds it to Archived, and commits. Refuses if tree_prs is non-empty (route to discard-promotion or finalize-promotion instead) or if the thread is in-review. Use when the user says "discard this thread", "drop this idea", "kill this thread", "abandon <slug>", or "archive this — it was never promoted".
version: 0.2.2
pack: project-brain
requires:
  - git
  - "read:~/.ai/projects.yaml"
  - "write:[brain-root]"
---

# discard-thread

The pre-promotion counterpart to `finalize-promotion`'s archive disposition and to `discard-promotion`. Sometimes an idea runs out of steam before it ever reaches the tree — the original question turned out to be wrong, a different thread subsumed it, or the author decided not to pursue it. `discard-thread` is the clean exit for that case.

Unlike `finalize-promotion`'s archive branch (which happens after a PR merged and leaves landed on main) or `discard-promotion` (which handles a closed-unmerged promote PR), `discard-thread` handles the pure pre-PR case: no leaves exist on main, `tree_prs` is empty, and the thread can be moved to `archive/` without any cross-tree cleanup. The guarantee this skill preserves is simple: a thread that was never promoted leaves no trace on the tree.

## When to invoke

- "Discard this thread" / "drop this idea" / "kill this thread"
- "Abandon <slug>" / "I'm not going to pursue this"
- "Archive this — it was never promoted"
- When `thread-index.md` or `current-state.md` is cluttered with dead ideas
- After realizing a parked thread is not worth resuming

## Inputs

| Name              | Source                          | Required | Description                                                                                     |
|-------------------|---------------------------------|----------|-------------------------------------------------------------------------------------------------|
| `thread_slug`     | user prompt or cwd inference    | yes      | Slug of the thread. Defaults to the thread whose directory contains cwd.                        |
| `discard_reason`  | user prompt                     | yes      | Short "why dropped". 1–3 sentences; goes into `discard_reason` frontmatter and the Archived row of `thread-index.md`. Required — unreasoned discards are hostile to future audits. |
| `--brain=<path>`  | user prompt or cwd inference    | no       | Absolute path to the brain root. Defaults to the nearest ancestor `thoughts/` directory.        |
| `--dry-run`       | boolean                         | no       | Print the plan (status flip, archive metadata, git mv, commit message) without performing any file writes, git mutations, or audit-log writes. See Process § Dry-run semantics. |

Prompt strategy: resolve `thread_slug` from cwd. Always prompt for `discard_reason` even if the user supplied an inline "because X" in their message — discarded threads are often re-read during quarterly reviews and need a standalone explanation.

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory is inside a brain root (a `thoughts/` directory containing `CONVENTIONS.md`) or an explicit `--brain=<path>` was given.
2. `thoughts/threads/[thread_slug]/thread.md` exists.
3. Thread `status` is `active` or `parked`. `in-review` threads have a live PR (use `discard-promotion` after closing it or `finalize-promotion` after merging); `archived` threads are already terminal.
4. `tree_prs` is empty or absent. A non-empty `tree_prs` means the thread has promotion history, so the correct exit is one of `discard-promotion` (if the most recent PR is CLOSED-unmerged), `finalize-promotion` with `archive` disposition (if MERGED), or manual reconciliation (if still OPEN). The skill refuses and names the right alternative based on `gh pr view` of the most recent entry.
5. `discard_reason` is non-empty.
6. Working tree has no uncommitted changes to `thoughts/thread-index.md`, `thoughts/current-state.md`, or the thread's `thread.md`.
7. `git config user.email` returns a value (used to populate `archived_by`).
8. `thoughts/archive/[thread_slug]/` does not exist. A collision suggests an earlier discard was partially rolled back; refuse rather than overwriting.

## Process

Each step is atomic. Failure at step N leaves the tree in whatever state it was after step N-1.

1. **Resolve inputs.** Infer `thread_slug` from cwd. Prompt for `discard_reason`.
2. **Validate preconditions.** Run checks 1–8. If `tree_prs` is non-empty (precondition 4 fails), run `gh pr view` on the most recent entry and report which sibling skill to use. On any other failure, stop and name the precondition.
3. **Compute timestamp.** Run `date -u +%Y-%m-%dT%H:%M:%SZ` for `archived_at`.
4. **Flip frontmatter.** In `thoughts/threads/[thread_slug]/thread.md`:
    - `status: active|parked → archived`.
    - Remove `maturity` field. Archived threads do not carry a maturity; § 4.1 says "archived has no maturity."
    - Add `archived_at: <timestamp>` and `archived_by: <git config user.email>`.
    - Add `discard_reason: <string>`.
    - If coming from `parked`: remove `parked_at`, `parked_by`, `parked_reason`, and `unpark_trigger` (if present). These fields are park-only metadata and must not persist into the archived record.
5. **Move to archive.** `git mv thoughts/threads/[thread_slug] thoughts/archive/[thread_slug]`. This moves the entire thread directory — `thread.md`, `decisions-candidates.md`, `open-questions.md`, and any companions — in a single git operation that preserves history.
6. **Update `thread-index.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
7. **Update `current-state.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
8. **Commit staging.** Stage the moved archive directory (the `git mv` is already staged): `git add thoughts/archive/[slug]/`. The index files will be staged in the Final step.
9. **Final step — rebuild indexes**

Invoke `verify-tree --rebuild-index` to regenerate `thoughts/thread-index.md` and `thoughts/current-state.md` from the now-updated per-thread frontmatter.

- If the rebuild returns exit 0: proceed to commit; stage both index files along with the archive move in a single commit: `git add thoughts/ && git commit -m "chore([slug]): discard thread — [reason truncated to 50 chars]"`.
- If the rebuild returns exit 1 (source validation failure): abort this skill's commit. Report the thread(s) that failed source validation — they indicate schema violations introduced (or already present) in this operation. Fix the underlying thread before retrying this skill.
- If the rebuild returns exit 2 (write / verify failure): abort. The live index files are unchanged (atomic write). Report the error; this is typically a filesystem / permissions issue.

Rationale: per CONVENTIONS § 1, `thread-index.md` and `current-state.md` are autogenerated projections of per-thread frontmatter. This skill maintains its invariants by updating the per-thread source; the aggregate view is refreshed as the last step so that (a) index files always reflect post-operation state, and (b) concurrent skills never collide on hand-edits of the aggregate files.

10. **Report.** Return the commit SHA, the new thread path (`archive/[slug]/`), and a closing note (see § Outputs).

No automatic push. Users who want the discard visible to collaborators can push manually.

### Dry-run semantics

When `--dry-run` is set:

1. **Run all preconditions** (steps 1–2 above), including brain-root existence, thread existence, status checks, tree_prs check, and git-state cleanliness. Exit 1 if any precondition fails.
2. **Compute the full plan:** print the new thread path (`archive/<slug>/`), the frontmatter changes (status flip, maturity removal, archive metadata add, park metadata removal if coming from parked), the `git mv` operation, and the commit message.
3. **Invoke `verify-tree --rebuild-index --dry-run`** to surface any index-rebuild failures (step 9). If that fails, print the rebuild error and exit 1.
4. **Write NOTHING to disk:** neither frontmatter edits, nor git mv operations, nor the audit log.
5. **Invoke NO git mutations:** no `git mv`, no `git add`, no `git commit`. Read-only git operations are allowed.
6. **Exit 0** if the plan would succeed end-to-end, **exit 1** if any precondition or rebuild-dry-run check failed, **exit 2** on unexpected error.

Print the plan to stdout as a numbered list (e.g., "1. Validate preconditions passed", "2. Edit thread.md: status active → archived, remove maturity, add archived_at/archived_by/discard_reason", "3. Execute: git mv thoughts/threads/<slug> thoughts/archive/<slug>", "4. Run verify-tree --rebuild-index --dry-run", "5. Commit: chore(<slug>): discard thread — <reason>"). When exiting 1, also print the failing precondition or rebuild error.

## Side effects

### Files written or modified

| Path (relative to brain root)              | Operation       | Notes                                                                        |
|--------------------------------------------|-----------------|-------------------------------------------------------------------------------|
| `threads/[slug]/thread.md`                 | edit + move     | Frontmatter flip; then moved with the directory                              |
| `threads/[slug]/*`                         | move            | All sibling files in the thread directory move to `archive/[slug]/`          |
| `archive/[slug]/*`                         | create (as target of move) | Result of `git mv`; no new content generated                     |
| `thread-index.md`                          | edit            | Row moves from `## Active` or `## Parked` to `## Archived`                   |
| `current-state.md`                         | edit            | Bullet removed; "Recent merges" entry appended                                |

Only `thread.md`'s frontmatter changes; every other file in the thread directory moves as-is. No content is deleted — the discard is recoverable via `git mv archive/[slug] threads/[slug]` plus a manual frontmatter reset.

### Git operations

| Operation                                            | Trigger | Notes                                                           |
|------------------------------------------------------|---------|------------------------------------------------------------------|
| `git mv thoughts/threads/[slug] thoughts/archive/[slug]` | step 5  | Preserves file history across the move                        |
| `git add && git commit`                           | step 9  | Single commit with index files and the move                  |

When `--dry-run` is set: NO side effects. Stdout output only.
| `git add thoughts/ && git commit -m …`               | step 8  | Single commit; contains frontmatter + move + index updates      |

No branch creation, no push.

### External calls

- **`gh pr view <url> --json state`** — invoked **only** if precondition 4 fails (non-empty `tree_prs`), to name the correct sibling skill. If `gh` is unavailable, the failure is reported without the cross-reference; the user still sees that `tree_prs` is non-empty.

## Outputs

**User-facing summary.** A short message with:

- The commit SHA.
- The new thread path (`archive/[slug]/`, as a `computer://` link).
- The discard reason (verbatim).
- A next-step suggestion: "The thread is recoverable via `git mv archive/[slug] threads/[slug]` plus a frontmatter flip if you change your mind. Otherwise, run `new-thread` to start the next idea."

**State passed forward.**

- `thread_slug` — unchanged.
- `discard_commit` — SHA of the single commit.
- `archived_path` — new path under `archive/`.
- `discard_reason` — unchanged from input.
- `source_status` — the status the thread held before discard (`active` or `parked`).

## Frontmatter flips

| File                          | Field             | Before              | After                          |
|-------------------------------|-------------------|---------------------|---------------------------------|
| `threads/[slug]/thread.md`    | `status`          | `active` or `parked`| `archived`                      |
| `threads/[slug]/thread.md`    | `maturity`        | `<any>`             | *(removed)*                     |
| `threads/[slug]/thread.md`    | `archived_at`     | *(absent)*          | `<ISO-8601>`                    |
| `threads/[slug]/thread.md`    | `archived_by`     | *(absent)*          | `<email>`                       |
| `threads/[slug]/thread.md`    | `discard_reason`  | *(absent)*          | `<string>`                      |
| `threads/[slug]/thread.md`    | `parked_at`       | `<value>` or absent | *(removed)*                     |
| `threads/[slug]/thread.md`    | `parked_by`       | `<value>` or absent | *(removed)*                     |
| `threads/[slug]/thread.md`    | `parked_reason`   | `<value>` or absent | *(removed)*                     |
| `threads/[slug]/thread.md`    | `unpark_trigger`  | `<value>` or absent | *(removed)*                     |

`tree_prs`, `promoted_to`, `promoted_at` are never written by this skill — by precondition 4 they are already empty. `soft_links`, `owner`, `created_at`, `related_projects` are untouched.

When `--dry-run` is set: no files are written; the frontmatter changes, git mv operation, and any archive metadata removals are described in the plan output instead.

## Postconditions

- The thread directory lives at `archive/[slug]/`; nothing remains at `threads/[slug]/`.
- `status == archived`, `maturity` absent, `archived_at` and `archived_by` populated, `discard_reason` populated.
- No park metadata fields remain in frontmatter.
- `thread-index.md` shows the thread only under `## Archived` (autogenerated).
- `current-state.md` has no reference to the thread in Active or Parked sections (autogenerated).
- `thread-index.md` and `current-state.md` reflect the post-operation state of all threads (autogenerated).
- Exactly one commit was added.
- `verify-tree` passes on main.

## Failure modes

| Failure                                      | Cause                                                                             | Response                                                                 |
|----------------------------------------------|-----------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| Brain root not found                         | No `thoughts/CONVENTIONS.md` up the tree                                          | refuse — prompt user to `init-project-brain`                             |
| Thread slug does not resolve                 | Typo; wrong cwd                                                                   | refuse — list nearby slugs                                               |
| Thread in `in-review`                        | PR is live                                                                        | refuse — direct user to close the PR, then to `discard-promotion` or `finalize-promotion` |
| Thread in `archived`                         | Already discarded or archived                                                     | refuse — report current `archived_at` for visibility                     |
| `tree_prs` non-empty, last PR OPEN           | Thread has open promote PR                                                        | refuse — instruct user to close the PR on the host first                 |
| `tree_prs` non-empty, last PR MERGED         | Thread should finalize, not discard                                               | refuse — redirect to `finalize-promotion` (archive disposition)          |
| `tree_prs` non-empty, last PR CLOSED-unmerged| Thread should discard-promotion first                                             | refuse — redirect to `discard-promotion`, then re-evaluate                |
| Empty `discard_reason`                       | Slipped past prompt                                                               | re-prompt — reason is not optional                                       |
| Archive path collision                       | `archive/[slug]/` already exists (prior partial rollback)                         | refuse — ask user to reconcile manually (either delete the old archive or pick a new slug) |
| `git mv` fails                               | Case-insensitive filesystem collision, permissions                                | refuse — leave thread in place with frontmatter unchanged                 |
| `git config user.email` empty                | Git not configured                                                                | refuse — ask user to configure git                                       |
| Uncommitted edits to unrelated paths         | Conflict risk                                                                     | refuse — ask user to stash or commit                                     |
| Rebuild source-validation failure            | Thread frontmatter schema violations                                              | refuse — report violating thread; user must repair before retrying       |
| Rebuild write failure                        | Filesystem / permissions issue                                                   | refuse — live index files unchanged (atomic); report error               |
| `--dry-run` plan shows a precondition failure | Any precondition failed during dry-run | skill exits 1 after printing the plan and the failing precondition. The plan is still useful: the user sees both what was intended and why it wouldn't work. |

## Related skills

- **Coordinates with:** `update-thread`, `park-thread` — the three pre-promotion thread operations; mutually exclusive per invocation.
- **Mutually exclusive with:** `finalize-promotion` — handles post-merge archive; reads `gh pr view` to distinguish.
- **Mutually exclusive with:** `discard-promotion` — handles the closed-unmerged PR case; has `tree_prs` entries; this skill has none.
- **Compatible with:** `verify-tree` — expected to pass on main after discard.
- **Reversible by:** manual `git mv archive/[slug] threads/[slug]` plus frontmatter reset; not automated (rare operation).

## Asset dependencies

None. The skill reads existing artifacts, flips fields, and moves the directory. No templates involved.

## Versioning

**0.2.2** — Added `--dry-run` flag specification with full semantics contract, including exit codes 0/1/2 (2 reserved for unexpected errors).

**0.2.0** — Stage 2 of v0.9.0: index-file updates moved to centralized `verify-tree --rebuild-index` final step; previous inline edits removed.

**0.1.0** — initial draft. Minor bump if an `--undo` flag is added (re-promote from archive). Major bump if the retention policy for discarded threads changes (e.g. moving to delete-after-N-days instead of permanent archive) — that would shift the model from content-preserving to GC-driven and is a user-facing semantics change.
