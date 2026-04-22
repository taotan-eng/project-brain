---
name: update-thread
description: Apply a structured update to an active or parked thread without flipping its status. Supports bumping maturity (exploring to refining to locking and back), adding or renaming or removing candidate-decision leaves under decisions-candidates.md, editing soft_links on thread.md, and committing pending freeform edits to thread.md or companion files with a conventional message. Keeps thread-index.md and current-state.md in sync. Use when the user says "update the thread", "bump maturity to locking", "add a candidate", "rename this option", "drop this candidate", "refresh soft_links", or "commit my edits to this thread". Does NOT flip thread status — use park-thread, discard-thread, promote-thread-to-tree, or finalize-promotion for status transitions.
version: 0.2.2
pack: project-brain
requires:
  - git
  - "read:~/.ai/projects.yaml"
  - "write:[brain-root]"
---

# update-thread

The workhorse for pre-promotion thread maintenance. Between `new-thread` and `promote-thread-to-tree`, the thread is `active` (or `parked`) and accumulates content — new candidates get added to `decisions-candidates.md`, earlier candidates get renamed or dropped, `soft_links` grow, the body prose gets refined. Without a dedicated skill, users hand-edit the frontmatter, forget to update `thread-index.md`, and commit with inconsistent messages. This skill holds the bookkeeping.

`update-thread` is intentionally compositional: a single invocation performs one named operation plus an optional "commit pending edits" pass. Running it twice in a row for two unrelated changes is fine — each is a clean commit. The skill does **not** flip `status`. Status transitions are the business of `park-thread`, `discard-thread`, `promote-thread-to-tree`, and `finalize-promotion`.

## When to invoke

- "Update the thread" / "refresh the thread" / "commit my edits"
- "Bump maturity to refining" / "move this to locking"
- "Add a candidate decision — <title>"
- "Rename option-b to <new-slug>" / "drop option-c"
- "Add a soft_link to <uri>" / "remove the stale spec link"
- "The thread body is ready — commit it"
- After hand-editing `thread.md` or its companion files and wanting a clean commit with index sync

## Inputs

| Name              | Source                          | Required | Description                                                                                     |
|-------------------|---------------------------------|----------|-------------------------------------------------------------------------------------------------|
| `thread_slug`     | user prompt or cwd inference    | yes      | Slug of the thread to update. Defaults to the thread whose directory contains cwd.              |
| `operation`       | user prompt                     | yes      | One of: `bump-maturity`, `add-leaf`, `rename-leaf`, `remove-leaf`, `update-soft-links`, `commit-pending`. Exactly one operation per invocation. |
| `maturity_target` | user prompt                     | cond.    | `exploring | refining | locking`. Required for `bump-maturity`.                                 |
| `leaf_slug`       | user prompt                     | cond.    | Slug for the candidate leaf. Required for `add-leaf`, `rename-leaf` (as source), `remove-leaf`. |
| `leaf_title`      | user prompt                     | cond.    | H2/H3 title for the new candidate. Required for `add-leaf`.                                     |
| `new_leaf_slug`   | user prompt                     | cond.    | Target slug. Required for `rename-leaf`.                                                        |
| `soft_links_ops`  | user prompt                     | cond.    | List of `{op: add|remove, uri, role?}` objects. Required for `update-soft-links`.               |
| `commit_scope`    | inferred                        | no       | Overrides the default commit scope. Defaults to `thread_slug`.                                  |
| `--brain=<path>`  | user prompt or cwd inference    | no       | Absolute path to the brain root. Defaults to the nearest ancestor `thoughts/` directory.        |
| `--dry-run`       | boolean                         | no       | Print the plan (operation, file changes, commit message) without performing any file writes, git mutations, or audit-log writes. See Process § Dry-run semantics. |

Prompt strategy: always resolve `thread_slug` from cwd first. Ask `operation` via `AskUserQuestion` with the six options above. Branch on the answer to collect operation-specific inputs. `commit-pending` takes no extra args — it simply stages and commits whatever is already dirty in the thread directory.

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory is inside a brain root (a `thoughts/` directory containing `CONVENTIONS.md`) or an explicit `--brain=<path>` was given.
2. `thoughts/threads/[thread_slug]/thread.md` exists.
3. Thread `status` is `active` or `parked`. `in-review` threads are read-only on main during their PR (edits belong on the promote branch, not here); `archived` threads are terminal.
4. For `bump-maturity`: the target value is one of `exploring | refining | locking` and the transition is not a no-op (current != target). Downgrades (e.g. `locking → refining`) are allowed — users sometimes realize they need more refinement after starting to lock.
5. For `add-leaf`: no leaf with `leaf_slug` exists yet in `decisions-candidates.md` or as a separate file under the thread dir.
6. For `rename-leaf`: the source slug exists; the target slug does not; the source leaf has not yet been promoted (not possible on an `active` or `parked` thread by construction, but the skill still checks).
7. For `remove-leaf`: the leaf exists and has not been promoted.
8. For `update-soft-links`: each `add` URI parses per § 5.1; each `remove` URI is currently present in `soft_links`.
9. Working tree has no uncommitted changes outside the thread directory and the two index files (`thread-index.md`, `current-state.md`). Edits *inside* the thread directory are the point of `commit-pending` mode; edits to index files would collide with the skill's own writes.
10. `commit-pending` additionally requires at least one dirty path under `thoughts/threads/[thread_slug]/` (otherwise there is nothing to commit).

## Process

Each step is atomic. Failure at step N leaves the tree in whatever state it was after step N-1; `git restore` returns you to pre-skill state cleanly.

1. **Resolve inputs.** Infer `thread_slug` from cwd. Ask for `operation` and any operation-specific fields via `AskUserQuestion`.
2. **Validate preconditions.** Run checks 1–10 (subset per operation). On any failure, stop and report the specific precondition.
3. **Apply the operation.** Branches as follows:
    - **`bump-maturity`** — In `thoughts/threads/[thread_slug]/thread.md` frontmatter, flip `maturity: <current> → <maturity_target>`. Nothing else changes.
    - **`add-leaf`** — Append a new H2 section to `decisions-candidates.md` titled `[leaf_title]` with a stable anchor slug (`leaf_slug`). Use `assets/thread-template/candidate-snippet.md` for the skeleton (title, one-line description placeholder, pros/cons/notes scaffold); if the template is missing, fall back to an inline minimal skeleton and log the missing asset. Do not touch `thread.md` frontmatter unless the user also supplied a soft_links delta. All candidates live inline in `decisions-candidates.md` — the skill does not introduce per-candidate companion files (larger write-ups belong in the existing optional `proposal.md` per § 1).
    - **`rename-leaf`** — In `decisions-candidates.md`, rewrite the H2 anchor, the section heading, and any in-file references from `leaf_slug` to `new_leaf_slug`. Update any internal `soft_links` entries in `thread.md` that referenced the old slug (via URI fragment or path containing the slug).
    - **`remove-leaf`** — Delete the H2 section from `decisions-candidates.md`. Emit a short trailer note under a `## Dropped candidates` section of `decisions-candidates.md` (created if absent) with the slug and a one-line reason supplied by the user. The dropped-candidate log preserves why options were considered and rejected.
    - **`update-soft-links`** — Apply each op in `soft_links_ops` to the `thread.md` frontmatter list. Validate each `add` URI per § 5.1 before writing. `remove` ops match on URI string (exact).
    - **`commit-pending`** — No frontmatter edits beyond what is already on disk. The dirty paths are what land in the commit.
4. **Update `thread-index.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
5. **Update `current-state.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
6. **Commit.** Stage the thread directory: `git add thoughts/threads/[slug]/`. The index files will be staged in the Final step.
7. **Final step — rebuild indexes**

Invoke `verify-tree --rebuild-index` to regenerate `thoughts/thread-index.md` and `thoughts/current-state.md` from the now-updated per-thread frontmatter.

- If the rebuild returns exit 0: proceed to commit; stage both index files along with the thread directory in a single commit: `git add thoughts/threads/[slug]/ thoughts/thread-index.md thoughts/current-state.md && git commit -m "chore([slug]): <operation message>"`.
- If the rebuild returns exit 1 (source validation failure): abort this skill's commit. Report the thread(s) that failed source validation — they indicate schema violations introduced (or already present) in this operation. Fix the underlying thread before retrying this skill.
- If the rebuild returns exit 2 (write / verify failure): abort. The live index files are unchanged (atomic write). Report the error; this is typically a filesystem / permissions issue.

Rationale: per CONVENTIONS § 1, `thread-index.md` and `current-state.md` are autogenerated projections of per-thread frontmatter. This skill maintains its invariants by updating the per-thread source; the aggregate view is refreshed as the last step so that (a) index files always reflect post-operation state, and (b) concurrent skills never collide on hand-edits of the aggregate files.

8. **Report.** Return the commit SHA, the operation performed, and a next-step suggestion sized to the operation (see § Outputs).

No automatic push. Thread work stays local until the user decides to share — matches the `new-thread` convention. Users who want immediate sharing can `git push` manually.

### Dry-run semantics

When `--dry-run` is set:

1. **Run all preconditions** (steps 1–2 above), including brain-root existence, thread existence, status checks, and operation-specific guards. Exit 1 if any precondition fails.
2. **Compute the full plan:** print the operation name, the files that would be modified (`thread.md`, `decisions-candidates.md`, etc.), the frontmatter changes for `bump-maturity` or `update-soft-links`, any new H2 sections for `add-leaf`, and the commit message.
3. **Invoke `verify-tree --rebuild-index --dry-run`** to surface any index-rebuild failures (step 7). If that fails, print the rebuild error and exit 1.
4. **Write NOTHING to disk:** neither frontmatter edits, nor file appends, nor the audit log.
5. **Invoke NO git mutations:** no `git add`, no `git commit`. Read-only git operations are allowed.
6. **Exit 0** if the plan would succeed end-to-end, **exit 1** if any precondition or rebuild-dry-run check failed, **exit 2** on unexpected error.

Print the plan to stdout as a numbered list (e.g., "1. Apply operation: bump-maturity exploring → refining", "2. Edit thread.md frontmatter", "3. Run verify-tree --rebuild-index --dry-run", "4. Commit: chore(<slug>): <operation message>"). When exiting 1, also print the failing precondition or rebuild error.

## Side effects

### Files written or modified

| Path (relative to brain root)                    | Operation          | Conditional on                                      |
|--------------------------------------------------|--------------------|------------------------------------------------------|
| `threads/[slug]/thread.md`                       | edit (frontmatter) | `bump-maturity` or `update-soft-links`               |
| `threads/[slug]/decisions-candidates.md`         | edit or create     | `add-leaf`, `rename-leaf`, `remove-leaf`             |
| `threads/[slug]/*.md` (any dirty)                | commit only        | `commit-pending`                                     |
| `thread-index.md`                                | edit               | `bump-maturity`                                      |
| `current-state.md`                               | edit               | `bump-maturity` into or out of `locking`             |

Paths are relative to the brain root (`thoughts/`). Shell commands in § Process retain the `thoughts/` prefix since they run from project root.

### Git operations

| Operation                              | Trigger | Notes                                                            |
|----------------------------------------|---------|-------------------------------------------------------------------|
| `git add thoughts/ && git commit -m …` | step 6  | Single commit; message format per § Process step 6                |

No branch creation, no push. Pre-promotion thread work lives on `main` (§ 11.4).

When `--dry-run` is set: NO side effects. Stdout output only.

### External calls

None. Purely local filesystem + git operations.

## Outputs

**User-facing summary.** A short message with:

- The commit SHA.
- The operation performed and the specific change (e.g. `maturity: refining → locking`, or `added candidate [leaf_slug]: [title]`).
- A next-step suggestion:
  - After `bump-maturity → locking`: "Run `promote-thread-to-tree` when you're ready to open the PR."
  - After `add-leaf` / `rename-leaf` / `remove-leaf`: "Continue refining in `decisions-candidates.md`, or run `update-thread` again."
  - After `update-soft-links`: "Links updated. Run `materialize-context` if you want to pre-pull the new refs."
  - After `commit-pending`: "Edits snapshotted. Thread is at maturity `<current>`."

**State passed forward.**

- `thread_slug` — unchanged from input.
- `update_commit` — SHA of the single commit.
- `operation` — the operation that ran.
- `thread_status` — unchanged (always `active` or `parked`).
- `thread_maturity` — current value (may have just changed for `bump-maturity`).

## Frontmatter flips

| File                                    | Field        | Before      | After                         | Operation          |
|-----------------------------------------|--------------|-------------|-------------------------------|--------------------|
| `threads/[slug]/thread.md`              | `maturity`   | current     | `maturity_target`             | `bump-maturity`    |
| `threads/[slug]/thread.md`              | `soft_links` | current list| current list ± applied ops    | `update-soft-links`|

All other operations do not touch frontmatter. `status`, `tree_prs`, `promoted_to`, `promoted_at`, `archived_*`, `parked_*` are never written by this skill.

When `--dry-run` is set: no files are written; the frontmatter changes and new H2 sections are described in the plan output instead.

## Postconditions

- The thread remains at its existing path (`threads/[slug]/`).
- `status` is unchanged (`active` or `parked` exactly as before).
- If `bump-maturity` ran: `maturity` equals `maturity_target`.
- The thread directory is in a coherent state — any renamed companion files have matching references in `decisions-candidates.md`; any removed candidates have a "Dropped candidates" note.
- `thread-index.md` and `current-state.md` reflect the post-operation state of all threads (autogenerated).
- Exactly one commit was added.
- `verify-tree` passes on the updated thread.

## Failure modes

| Failure                                        | Cause                                                                         | Response                                                               |
|------------------------------------------------|-------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| Brain root not found                           | No `thoughts/CONVENTIONS.md` up the tree; no `--brain` given                  | refuse — prompt user to `init-project-brain`                           |
| Thread slug does not resolve                   | Typo; wrong cwd                                                               | refuse — list nearby slugs (levenshtein) and re-prompt                 |
| Thread in `in-review`                          | User edited mid-PR (wrong branch)                                             | refuse — explain that `in-review` edits belong on the promote branch   |
| Thread in `archived`                           | Terminal state                                                                | refuse — suggest reopening manually or starting a new thread           |
| `bump-maturity` target equals current          | No-op invocation                                                              | refuse — report current value                                          |
| `add-leaf` slug collision                      | Candidate already exists                                                      | refuse — prompt user to pick a different slug or use `rename-leaf`     |
| `rename-leaf` source missing                   | Typo; already renamed                                                         | refuse — list existing candidate slugs                                 |
| `remove-leaf` candidate already promoted       | Impossible on `active`/`parked` status but guarded                            | refuse — report the promotion state and point at `discard-promotion`   |
| `update-soft-links` add URI malformed          | Fails § 5.1 scheme parser                                                     | refuse — report which URI and which scheme rule                         |
| `update-soft-links` remove URI not present     | Stale reference                                                               | refuse — list current `soft_links`                                     |
| `commit-pending` with clean tree               | Nothing to commit                                                             | refuse — report that there are no dirty paths under the thread dir     |
| Uncommitted edits outside thread               | Shared-file conflict risk                                                     | refuse — ask user to stash or commit unrelated work                    |
| Rebuild source-validation failure              | Thread frontmatter schema violations                                          | refuse — report violating thread; user must repair before retrying     |
| Rebuild write failure                          | Filesystem / permissions issue                                               | refuse — live index files unchanged (atomic); report error             |
| `--dry-run` plan shows a precondition failure | Any precondition failed during dry-run | skill exits 1 after printing the plan and the failing precondition. The plan is still useful: the user sees both what was intended and why it wouldn't work. |

## Related skills

- **Follows:** `new-thread` — produces the thread that `update-thread` maintains.
- **Precedes:** `promote-thread-to-tree` — typically invoked after `bump-maturity` reaches `locking`.
- **Coordinates with:** `park-thread`, `discard-thread` — the other pre-promotion operations; mutually exclusive per invocation.
- **Compatible with:** `verify-tree` — useful to run after `rename-leaf` or bulk `soft_links` edits to catch stale references.
- **Compatible with:** `materialize-context` — after `update-soft-links add`, may be called to pre-pull new refs.

## Asset dependencies

- `assets/thread-template/candidate-snippet.md` — the H2 + pros/cons/notes scaffold inserted by `add-leaf`.
- `assets/commit-templates/chore.txt` *(optional; current scope lives inline in this skill)*.

## Versioning

**0.2.2** — Added `--dry-run` flag specification with full semantics contract, including exit codes 0/1/2 (2 reserved for unexpected errors).

**0.2.0** — Stage 2 of v0.9.0: index-file updates moved to centralized `verify-tree --rebuild-index` final step; previous inline edits removed.

**0.1.0** — initial draft. Minor bump if a new operation is added (e.g. `split-leaf`, `merge-leaves`). Major bump if the one-operation-per-invocation rule relaxes or if the skill begins flipping `status` (which would be a lifecycle change and need to be negotiated against CONVENTIONS § 4.1).
