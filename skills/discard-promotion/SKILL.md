---
name: discard-promotion
description: Revert a promote PR back to active so the thread becomes editable again. Handles both cases — PR was closed by reviewers (rejected/abandoned), or the user wants to cancel a still-OPEN PR mid-review to keep editing the thread. For OPEN PRs, the skill runs `gh pr close --delete-branch` itself before reverting; for already-closed PRs it just verifies state and reverts. Reverts thread on main from in-review back to active/refining without touching tree_prs (the closed URL stays as audit per CONVENTIONS section 4.1). Does NOT flip any leaf status since leaves never reached main. Use when the user says "discard this promotion", "cancel the promotion", "I want to edit the in-review thread", or after observing a promote PR close without a merge commit.
version: 1.0.0-rc4
pack: project-brain
requires:
  - git
  - gh
  - "read:~/.config/project-brain/projects.yaml"
  - "write:[brain-root]"
---

# discard-promotion

The counterpart to `finalize-promotion`. When a promote PR is closed without merging — rejected in review, superseded by a different PR, or deliberately abandoned — the thread is stuck in `status: in-review` on main with no mechanism to get unstuck. This skill is the unstick.

Unlike `finalize-promotion`, there are no leaves on main to flip — leaves only existed on the promote branch. All the skill has to do is reverse the thread frontmatter mirror commit that `promote-thread-to-tree` made on main, and (optionally) prune the branch that now has no future. The closed PR URL stays in `tree_prs` as an audit trail per CONVENTIONS § 4.1. Future waves append to the list; past failures stay visible.

## When to invoke

- "Discard this promotion" / "cancel the promotion" / "the PR was closed not merged"
- After observing a `promote/[slug]` PR close without a merge commit
- When `thread-index.md` shows a thread in `in-review` whose PR has since been closed without merge
- When the user wants to rework the promotion content and re-open with a fresh branch

## Inputs

| Name              | Source                          | Required | Description                                                                                     |
|-------------------|---------------------------------|----------|-------------------------------------------------------------------------------------------------|
| `thread_slug`     | user prompt or cwd inference    | yes      | Slug of the source thread. Defaults to the most recently-touched `in-review` thread if unambiguous. |
| `pr_url`          | derived or user prompt          | yes      | The closed promote PR. If the thread has exactly one unfinalized entry in `tree_prs`, pick it automatically; otherwise prompt. |
| `delete_branch`   | user prompt                     | no       | Whether to delete the promote branch on the remote after discarding. Default preview: `yes` if the branch is safely behind main, else `no`. |
| `--brain=<path>`  | user prompt or cwd inference    | no       | Absolute path to the brain root. Defaults to the nearest ancestor `project-brain/` directory.        |

Prompt strategy: infer `thread_slug` from cwd; infer `pr_url` from `tree_prs[last]` when there's one unfinalized. Ask `delete_branch` via a single `AskUserQuestion` with two options ("Delete the remote promote branch" / "Keep the branch — I'll reuse it").

| `--dry-run`       | boolean                         | no       | Print the plan (thread status revert, commit message) without performing any file writes, git mutations, or audit-log writes. See Process § Dry-run semantics. |

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory is inside a brain root (§ 1). Resolved via `project-brain/CONVENTIONS.md`.
2. `gh` is on PATH and authenticated for the host in `pr_url`.
3. `gh pr view [pr_url] --json state,mergedAt,closedAt` returns either `state: "CLOSED"` with `mergedAt: null` (PR was rejected or abandoned externally) **or** `state: "OPEN"` (user-initiated cancel — they want to back out mid-review to make further edits to the thread). A MERGED state routes to `finalize-promotion` (refuse with pointer). When state is OPEN, the skill closes the PR itself via `gh pr close <pr_url> --delete-branch=<delete_branch>` before proceeding with the revert. The user-initiated-cancel path is the canonical edit-mid-review escape hatch — see CONVENTIONS § 4.1 for why this is preferred over selectively loosening update-thread's gate.
4. Main is checked out with a clean working tree (`git status --porcelain` empty).
5. Main has been fetched from the remote (`git fetch [default_remote]`) and is at or ahead of `[default_remote]/main`. If behind, run `git pull --ff-only`; refuse if fast-forward isn't possible.
6. `project-brain/threads/[thread_slug]/thread.md` exists with `status: in-review` and `pr_url ∈ tree_prs`.
7. The thread has exactly one *unfinalized* entry in `tree_prs` and that entry is `pr_url`. (An unfinalized entry is one whose PR is not marked MERGED or CLOSED-discarded; determined by cross-referencing `gh pr view` for every entry.) If the thread has multiple unfinalized entries, the workflow is out of band — refuse and ask the user to reconcile manually.

## Process

Each step is atomic. Failure at step N leaves main in whatever state it was after step N-1.

1. **Resolve inputs.** Infer `thread_slug` from cwd. Resolve `pr_url` from `tree_prs` unfinalized entries. Query `gh pr view` for state metadata.
2. **Validate preconditions.** Run checks 1–7. On any failure, stop and report the specific precondition. If `gh pr view` returns OPEN, prompt the user via one `AskUserQuestion`: "PR is currently OPEN. Close it now and revert the thread to active? (Any review comments will be retained on the closed PR for reference, but the thread becomes locally editable.)" Default Yes.
2a. **(OPEN-only) Close the PR.** Run `gh pr close [pr_url] --delete-branch=[delete_branch]`. The PR transitions OPEN → CLOSED with `mergedAt: null`. From here the flow merges with the rejected-PR path.
3. **Flip thread frontmatter (commit 1 of 1).** In `project-brain/threads/[thread_slug]/thread.md`:
    - `status: in-review → active`
    - `maturity: locking → refining`
    - `tree_prs` untouched. The closed URL stays as audit per § 4.1.
    - `promoted_to` untouched (no merge happened, no entries to append).
    - `promoted_at` untouched.
4. **Update `thread-index.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
5. **Update `current-state.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
6. **Commit staging.** Stage the thread directory: `git add project-brain/threads/[slug]/`. The index files will be staged in the Final step.
7. **Final step — rebuild indexes**

Invoke `verify-tree --rebuild-index` to regenerate `project-brain/thread-index.md` and `project-brain/current-state.md` from the now-updated per-thread frontmatter.

- If the rebuild returns exit 0: proceed to commit; stage both index files along with the thread directory in a single commit: `git add project-brain/ && git commit -m "chore([thread_slug]): discard promotion — PR closed unmerged ([pr_url])"`.
- If the rebuild returns exit 1 (source validation failure): abort this skill's commit. Report the thread(s) that failed source validation — they indicate schema violations introduced (or already present) in this operation. Fix the underlying thread before retrying this skill.
- If the rebuild returns exit 2 (write / verify failure): abort. The live index files are unchanged (atomic write). Report the error; this is typically a filesystem / permissions issue.

Rationale: per CONVENTIONS § 1, `thread-index.md` and `current-state.md` are autogenerated projections of per-thread frontmatter. This skill maintains its invariants by updating the per-thread source; the aggregate view is refreshed as the last step so that (a) index files always reflect post-operation state, and (b) concurrent skills never collide on hand-edits of the aggregate files.

8. **Push.** `git push [default_remote] main`.
9. **Optional branch cleanup.** If `delete_branch == yes`:
    - Verify the branch has no unique commits of value. Run `git log [default_remote]/main..[default_remote]/promote/[thread_slug][-wave-suffix]` — expect exactly the three promote commits (stage, land, flip-to-in-review) with no unrelated work. If anything else appears, refuse the delete and flag for manual review.
    - `git push [default_remote] --delete promote/[thread_slug][-wave-suffix]`.
    - Locally: `git branch -D promote/[thread_slug][-wave-suffix]` (if present).
10. **Report.** Return the commit SHA, the thread's new path (unchanged; still at `threads/[slug]/`), whether the branch was deleted, and a next-step suggestion — rework the candidate in `decisions-candidates.md` and run `promote-thread-to-tree` again, or archive the thread manually if the idea is being dropped.

### Dry-run semantics

When `--dry-run` is set:

1. **Run all preconditions** (including PR-state verification via `gh pr view`, projects.yaml resolution, working-tree cleanliness, and branch-cleanup eligibility if `--delete-branch` was requested). Exit 1 if any precondition fails.
2. **Compute the full plan:** the thread.md frontmatter flips that would happen (status `in-review → active`, maturity `locking → refining`, `tree_prs` retained as audit trail), the commit message, whether the branch would be deleted (local and remote), and the rebuild of the two index files.
3. **Invoke `verify-tree --rebuild-index --dry-run`** to surface any index-rebuild failures before committing. If that fails, print the rebuild error and exit 1.
4. **Write NOTHING to disk:** no thread.md edits, no index-file edits, no audit-log writes.
5. **Invoke NO git mutations:** no `git add`, no `git commit`, no `git push`, no `git branch -D`, no `git push --delete`. Read-only git operations (`git status`, `git log`, `git rev-parse`, `gh pr view`) are allowed.
6. **Exit 0** if the plan would succeed end-to-end, **exit 1** if any precondition or rebuild-dry-run check failed, **exit 2** on unexpected error.

Print the plan to stdout in a numbered list matching the `## Process` steps. Under future audit-log wiring (per `AUDIT-LOG.md`), a record with `"dry_run": true` is appended; the v0.9.0-alpha.4 stub is spec-only, so no audit write happens either way.

## Side effects

### Files written or modified

| Path (relative to brain root)     | Operation | Notes                                                                                     |
|------------------------------------|-----------|-------------------------------------------------------------------------------------------|
| `threads/[slug]/thread.md`         | edit      | `status` + `maturity` flips. Other fields untouched.                                     |
| `thread-index.md`                  | edit (autogenerated) | Row moves from `## In review` back to `## Active`; regenerated by Final step.    |
| `current-state.md`                 | edit (autogenerated) | Entry re-added to "Active threads"; regenerated by Final step.                 |

No leaf files are touched — leaves never reached main.

### Git operations

| Operation                                            | Trigger | Notes                                                                |
|------------------------------------------------------|---------|----------------------------------------------------------------------|
| `git fetch [default_remote]`                         | step 2  | Ensures precondition 5 can be evaluated.                             |
| `git pull --ff-only`                                 | step 2  | If fast-forward fits; refuses otherwise.                             |
| `git add project-brain/ && git commit -m …`               | step 7  | Single commit on main; contains frontmatter + regenerated indexes.    |
| `git push [default_remote] main`                     | step 8  | Push the discard commit.                                             |
| `git push [default_remote] --delete promote/[slug][-N]` | step 9 | Only if `delete_branch == yes` and safety check passes.              |
| `git branch -D promote/[slug][-N]`                   | step 9  | Local deletion of the same branch.                                   |

### External calls

- **`gh pr view <url> --json state,mergedAt,closedAt`** — verifies the closed-unmerged state. Refuse at precondition 2 if `gh` is unavailable or unauthenticated.

## Outputs

**User-facing summary.** A short message with:

- The commit SHA on main.
- The thread's path (unchanged — still at `threads/[slug]/`).
- Whether the promote branch was deleted and the deletion target (branch name + remote).
- A next-step suggestion: "Rework the candidate in `decisions-candidates.md` and re-run `promote-thread-to-tree` when ready, or archive the thread manually if the idea is being dropped."

**State passed forward.**

- `discard_commit` — SHA of the reconciliation commit on main.
- `thread_path` — path to the thread (unchanged from pre-discard).
- `branch_deleted` — boolean; true iff step 8 ran.
- `kept_in_audit` — the `pr_url` that remains in `tree_prs`.

## Frontmatter flips

| File                                | Field       | Before       | After      |
|-------------------------------------|-------------|--------------|------------|
| `threads/[slug]/thread.md` (step 3) | `status`    | `in-review`  | `active`   |
| `threads/[slug]/thread.md` (step 3) | `maturity`  | `locking`    | `refining` |

`tree_prs`, `promoted_to`, `promoted_at` are all untouched. The closed URL remains in `tree_prs` as a historical record of an attempted-but-abandoned promotion wave.

## Postconditions

- The thread is `status: active, maturity: refining` on main at its original path.
- `tree_prs` contains the closed URL at its existing position (no reordering).
- `promoted_to` and `promoted_at` are unchanged — no merge means no append.
- `thread-index.md` and `current-state.md` reflect the active state (autogenerated).
- If `delete_branch == yes`, the promote branch is removed from the remote and locally.
- `verify-tree` passes on main.
- All preconditions of `promote-thread-to-tree` are now satisfied for a fresh wave on the same thread, if the user chooses to retry.

### Verbosity contract

Reads `verbosity` from `<brain>/config.yaml` (env override: `PROJECT_BRAIN_VERBOSITY`). Defaults to `terse`.

- **terse** (default): one acknowledgement line naming the action + target, then `Done.` No tool-output echo, no "let me..." preamble.
  - Example output: `Closing thread alpha without tree promotion. Done.`
- **normal**: structured summary of what changed (file paths, artifact counts), no conversational framing.
- **verbose**: full narration (pre-rc4 default). Use for debugging.

## Failure modes

| Failure                                      | Cause                                                                            | Response                                                        |
|----------------------------------------------|----------------------------------------------------------------------------------|-----------------------------------------------------------------|
| PR is MERGED                                  | User invoked the wrong skill                                                      | refuse — redirect to `finalize-promotion`                       |
| PR is still OPEN                              | PR not yet closed                                                                 | refuse — ask user to close on GitHub first                      |
| Thread not in `in-review`                     | Already discarded, already finalized, or never promoted                          | refuse — report current status                                  |
| PR URL not in `tree_prs`                      | Wrong URL supplied, or tree_prs hand-edited                                       | refuse — list `tree_prs` for user to pick                       |
| Multiple unfinalized waves                    | Thread has >1 open/unreconciled wave                                              | refuse — ask user to finalize or discard older waves first      |
| Main not fast-forward-mergeable               | Local main diverged from remote                                                   | refuse — ask user to reconcile manually                         |
| Branch has unrelated commits                  | `git log base..branch` shows commits beyond the expected three                    | refuse the delete (step 8 only); remainder of skill succeeds     |
| Push fails                                    | Branch protection, CI gate, network                                               | refuse — commit remains local; tell user to resolve and push    |
| Branch deletion fails                         | Permissions, protected branch rule                                                | warn, not refuse — report that branch remains but discard committed |
| Rebuild source-validation failure              | Thread frontmatter schema violations                                              | refuse — report violating thread; user must repair before retrying   |
| Rebuild write failure                          | Filesystem / permissions issue                                                   | refuse — live index files unchanged (atomic); report error           |

## Related skills

- **Follows:** `promote-thread-to-tree` — the skill whose state this one reverses.
- **Mutually exclusive with:** `finalize-promotion` — one handles merged PRs, the other handles closed PRs; the `gh pr view` state decides which is valid.
- **Precedes:** `promote-thread-to-tree` — after discard, the thread is eligible for a fresh promotion wave.
- **Compatible with:** `verify-tree` — expected to pass on main post-discard.

## Asset dependencies

None. Like `finalize-promotion`, this skill reads existing artifacts and flips fields; it does not create files from templates.

## Versioning

**0.2.2** — Added `--dry-run` flag specification with full semantics contract.

**0.2.0** — Stage 2 of v0.9.0: index-file updates moved to centralized `verify-tree --rebuild-index` final step; previous inline edits removed.

**0.1.0** — initial draft. Major bump if the audit-retention policy in § 4.1 changes (e.g. moving to remove closed URLs from `tree_prs`), if the single-commit shape changes, or if branch-deletion becomes mandatory rather than opt-in.
