---
name: finalize-promotion
description: Close out a merged promotion PR. Verifies the PR is merged via gh, flips each landed leaf from in-review to decided on main, appends one entry to promoted_to plus one to promoted_at per leaf, and either returns the thread to active/refining for further work or archives it to thoughts/archive/. Updates thread-index.md and current-state.md to reflect the new state. Use when the user says "finalize the promotion", "close out the PR", "the promotion merged", "archive this thread", or after observing a promote PR go green.
version: 0.3.2
pack: project-brain
requires:
  - git
  - gh
  - "read:~/.ai/projects.yaml"
  - "write:[brain-root]"
---

# finalize-promotion

Runs after a promotion PR merges. Its job is to reconcile main with the merged state — the leaves are on main as `in-review`, but nothing has told main "these are decided now." This skill is the telling. It also makes the thread-cycling decision: does this thread have more to promote (back to `active/refining`) or is it done (move to `archive/`)?

The skill intentionally does not trigger on its own. There is no git hook, no CI watcher, no polling loop — the user invokes it when they see the PR go green. This is a small piece of friction that keeps the lifecycle honest: someone should look at what landed before declaring it `decided`.

## When to invoke

- "Finalize the promotion" / "close out the PR" / "the promotion merged"
- "Archive this thread" (when the last wave has merged)
- After observing a `promote/[slug]` PR go green and wanting to reconcile main
- When `thread-index.md` shows a thread in `in-review` whose PR has since merged

## Inputs

| Name                | Source                          | Required | Description                                                                                     |
|---------------------|---------------------------------|----------|-------------------------------------------------------------------------------------------------|
| `thread_slug`       | user prompt or cwd inference    | yes      | Slug of the source thread. Defaults to the most recently touched `in-review` thread if unambiguous. |
| `pr_url`            | derived or user prompt          | yes      | The merged promote PR. If the thread has exactly one unfinalized entry in `tree_prs`, pick it automatically; otherwise prompt. |
| `disposition`       | user prompt                     | yes      | Either `continue` (thread re-enters `active/refining`) or `archive` (thread moves to `thoughts/archive/<slug>/`). |
| `merge_commit`      | derived from `gh pr view`       | yes      | SHA of the merge commit on the PR's base branch. Used for the audit trail; not stored in frontmatter. |
| `--brain=<path>`    | user prompt or cwd inference    | no       | Absolute path to the brain root. Defaults to the nearest ancestor `thoughts/` directory.        |

Prompt strategy: infer `thread_slug` from cwd; infer `pr_url` from `tree_prs[last]` when there's only one unfinalized. Ask `disposition` via a single `AskUserQuestion` with two options ("Keep thread active — more to promote" / "Archive thread — this was the last wave"). Default-preview `archive` if `decisions-candidates.md` has no remaining `locking` entries, otherwise default-preview `continue`.

| `--dry-run`       | boolean                         | no       | Print the plan (leaf status flips, promoted_to/promoted_at appends, disposition, commit message) without performing any file writes, git mutations, or audit-log writes. See Process § Dry-run semantics. |

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory is inside a brain root (§ 1). Resolved via `thoughts/CONVENTIONS.md`.
2. `gh` is on PATH and authenticated for the host in `pr_url`.
3. `gh pr view <pr_url> --json state,mergedAt,mergeCommit` returns `state: "MERGED"` with a non-empty `mergeCommit.oid`. Any other state (OPEN, CLOSED-without-merge) is a hard refuse — closed-without-merge is handled by `discard-promotion` (not yet drafted).
4. Main is checked out with a clean working tree (`git status --porcelain` empty).
5. Main has been brought up to date with the remote (`git fetch <default_remote> && git merge-base --is-ancestor <merge_commit> HEAD` returns true). If not, the skill runs `git pull --ff-only` against the remote; refuses if fast-forward isn't possible.
6. `thoughts/threads/[thread_slug]/thread.md` exists with `status: in-review` and `pr_url ∈ tree_prs`.
7. Every leaf introduced by the PR exists on main at its declared `domain` path with `status: in-review` and `source_thread: [thread_slug]`. The leaf list is obtained by diffing the merge commit against its first parent and filtering for `thoughts/tree/**/*.md` adds (excluding `NODE.md`). Crucially, this inspection must be done on the merge commit itself (not the promote branch's HEAD), to defend against cases where the promote branch was rebased or force-pushed and in-review state flips were lost. For each added leaf, run `git show <merge-commit>:<leaf-path>` and parse the frontmatter to verify `status: in-review`. If any leaf is not in-review on the merge commit, refuse with: `finalize-promotion refuses: leaf <path> is not in in-review state on the merge commit (found: <actual-status>). This can happen if the promote branch was rebased or force-pushed, losing the flip-to-in-review commit. Manual repair required: revert to the pre-merge state and re-run promote-thread-to-tree, or edit the leaves to in-review and create a fixup commit before re-running finalize.`
8. For each new `NODE.md` introduced by the PR (sub-tree directories), `status: decided` is already set (this is the only legal state per § 4.3 — `promote-thread-to-tree` writes it that way, so no flip is needed here; the precondition just guards against malformed landings).

## Process

Each step is atomic. Failure at step N leaves main in whatever state it was after step N-1; the worst case is a partially-updated thread file that the user can revert with `git reset --hard`.

1. **Resolve inputs.** Infer `thread_slug` from cwd; resolve `pr_url` from `tree_prs` unfinalized entries; prompt for `disposition`. Query `gh pr view` to capture `merge_commit` and `merged_at`.
2. **Validate preconditions.** Run checks 1–8. On any failure, stop and report the specific precondition.
3. **Enumerate merged leaves.** From `git diff-tree --no-commit-id --name-only -r <merge_commit>` filtered to `thoughts/tree/**/*.md` added paths (excluding `NODE.md`), build the list of `[leaf_path, domain, leaf_slug]` tuples. Keep the PR-declared order for stable `promoted_to` ordering.
4. **Flip leaves (commit 1 of 1).** For each leaf in the enumerated list:
    - In `thoughts/tree/[domain]/[leaf-slug].md`, flip `status: in-review → decided` in frontmatter.
    - No other leaf fields are touched — `source_thread`, `domain`, `impl_spec` (empty), `built_in` (empty) all stay as written by `promote-thread-to-tree`.
5. **Pre-commit verification of thread state.** Just before committing, re-read the thread's frontmatter from disk (not from the skill's in-memory copy at step 1). Verify that `tree_prs[-1]` (the most recent PR URL) has not already been added to `promoted_to`. If it has been added, another `finalize-promotion` run has already reconciled this PR; refuse with: `finalize-promotion refuses: tree_prs[-1] (<pr-url>) is already finalized (found in promoted_to). Another finalize run may have completed; pull and check thread state.` Abort without committing. This guards against concurrent or stale invocations.
6. **Update thread frontmatter (same commit).** In `thoughts/threads/[thread_slug]/thread.md`:
    - For each leaf in step 3, append one entry to `promoted_to` (the full tree path, e.g. `tree/engineering/ir/spec-v1.md`) and one matching entry to `promoted_at` (the PR's `merged_at` timestamp). Parallel-list invariant (§ 9) is satisfied because the same loop appends to both.
    - If `disposition == continue`:
       - `status: in-review → active`
       - `maturity: locking → refining`
       - Leave `tree_prs` untouched (historical record).
    - If `disposition == archive`:
       - `status: in-review → archived`
       - `maturity` field deleted (archived threads don't carry maturity).
       - `archived_at: <merged_at>` written (§ 3.2).
       - `archived_by: <git config user.email>` written.
       - Prepare to move the thread directory in step 7.
7. **Move to archive (archive disposition only).** `git mv thoughts/threads/[thread_slug] thoughts/archive/[thread_slug]`. Update any relative links to the thread from elsewhere (most commonly, leaves' `source_thread: [slug]` — unaffected since it's a slug, not a path).
8. **Update `thread-index.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
9. **Update `current-state.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
10. **Commit staging.** Stage the leaf updates and thread directory: `git add thoughts/tree/ thoughts/threads/[slug]/ thoughts/archive/[slug]/` (appropriate subset per disposition). The index files will be staged in the Final step.
11. **Final step — rebuild indexes**

Invoke `verify-tree --rebuild-index` to regenerate `thoughts/thread-index.md` and `thoughts/current-state.md` from the now-updated per-thread frontmatter.

- If the rebuild returns exit 0: proceed to commit; stage both index files along with the other changes in a single commit: `git add thoughts/ && git commit -m "chore([thread_slug]): finalize promotion — [N] leaves decided ([continue|archive])"`.
- If the rebuild returns exit 1 (source validation failure): abort this skill's commit. Report the thread(s) that failed source validation — they indicate schema violations introduced (or already present) in this operation. Fix the underlying thread before retrying this skill.
- If the rebuild returns exit 2 (write / verify failure): abort. The live index files are unchanged (atomic write). Report the error; this is typically a filesystem / permissions issue.

Rationale: per CONVENTIONS § 1, `thread-index.md` and `current-state.md` are autogenerated projections of per-thread frontmatter. This skill maintains its invariants by updating the per-thread source; the aggregate view is refreshed as the last step so that (a) index files always reflect post-operation state, and (b) concurrent skills never collide on hand-edits of the aggregate files.

12. **Push.** `git push [default_remote] main`.
13. **Report.** Return the commit SHA, the list of newly-`decided` leaves (each as a `computer://` link), the disposition, and a next-step suggestion — `derive-impl-spec` for any leaf the user wants to build, or `new-thread` to start the next piece.

### Dry-run semantics

When `--dry-run` is set:

1. **Run all preconditions**, including the concurrent-finalize guard (re-read thread frontmatter and verify `tree_prs[-1]` is not already in `promoted_to`), the PR-merged check via `gh pr view --json state,mergeCommit`, the `git show <merge-sha>:<leaf-path>` verification that each leaf has `status: in-review` on the merge commit itself (not the promote branch HEAD), and the working-tree cleanliness check. Exit 1 if any precondition fails.
2. **Compute the full plan:** the leaves that would flip from `in-review → decided`, the `promoted_to` and `promoted_at` list entries that would be appended (one per leaf), the thread disposition (continue or archive) with the `status`, `maturity`, `archived_at`, and `archived_by` values that would be written, the thread's destination path (stays at `threads/<slug>/` on continue, moves to `archive/<slug>/` on archive), and the commit message.
3. **Invoke `verify-tree --rebuild-index --dry-run`** to surface any index-rebuild failures before committing (step 11). If that fails, print the rebuild error and exit 1.
4. **Write NOTHING to disk:** no leaf edits, no thread.md edits, no `git mv` for archive disposition, no index-file edits, no audit-log writes.
5. **Invoke NO git mutations:** no `git add`, no `git commit`, no `git mv`, no `git push`. Read-only git operations (`git status`, `git show <merge-sha>:<path>`, `git rev-parse`, `gh pr view`) are allowed — they are essential to the precondition checks.
6. **Exit 0** if the plan would succeed end-to-end, **exit 1** if any precondition or rebuild-dry-run check failed, **exit 2** on unexpected error.

Print the plan to stdout in a numbered list matching the `## Process` steps. Under future audit-log wiring (per `AUDIT-LOG.md`), a record with `"dry_run": true` is appended; the v0.9.0-alpha.4 stub is spec-only, so no audit write happens either way.

## Side effects

### Files written or modified

| Path (relative to brain root)             | Operation       | Notes                                                                      |
|-------------------------------------------|-----------------|-----------------------------------------------------------------------------|
| `tree/[domain]/[leaf].md`                 | edit            | `status: in-review → decided`. One per merged leaf.                        |
| `threads/[slug]/thread.md` *(continue)*   | edit            | `status`, `maturity` flips + `promoted_to`/`promoted_at` appends.          |
| `threads/[slug]/thread.md` *(archive)*    | edit + move     | Frontmatter edits, then `git mv` to `archive/[slug]/thread.md`.            |
| `threads/[slug]/*` *(archive)*            | move            | All sibling files in the thread directory move with it.                    |
| `thread-index.md`                         | edit (autogenerated) | Row moves between sections; regenerated by Final step.              |
| `current-state.md`                        | edit (autogenerated) | Entry removed/added per disposition; regenerated by Final step.    |

### Git operations

| Operation                                   | Trigger | Notes                                                           |
|---------------------------------------------|---------|-----------------------------------------------------------------|
| `git fetch [default_remote]`                | step 2  | Ensures precondition 5 can be evaluated against current remote. |
| `git pull --ff-only`                        | step 2  | If fast-forward fits; refuses otherwise.                        |
| `git mv threads/[slug] archive/[slug]`      | step 7  | Archive disposition only.                                       |
| `git add thoughts/ && git commit`           | step 11 | Single commit — frontmatter flips + regenerated index files + (opt) move. |
| `git push [default_remote] main`            | step 12 | Remote's `default_remote` is resolved via `projects.yaml`.      |

### External calls

- **`gh pr view <url> --json state,mergedAt,mergeCommit`** — verifies merged state and captures the merge commit SHA. Handling when unavailable: refuse at precondition 2.

## Outputs

**User-facing summary.** A short message with:

- The commit SHA on main.
- The list of newly-`decided` leaves as `computer://` links.
- The disposition (`continue` with the thread still at `threads/[slug]/`, or `archive` with the new path at `archive/[slug]/`).
- A next-step suggestion: "Run `derive-impl-spec` on any leaf you plan to build, or `new-thread` to start the next one."

**State passed forward.**

- `finalize_commit` — SHA of the reconciliation commit on main.
- `decided_leaves` — list of tree paths now in `status: decided`.
- `disposition` — `continue` or `archive`.
- `thread_path` — current location of the thread (unchanged for `continue`, now under `archive/` for `archive`).

## Frontmatter flips

| File                                             | Field          | Before       | After                                      |
|--------------------------------------------------|----------------|--------------|--------------------------------------------|
| `tree/[domain]/[leaf].md` (step 4, per leaf)     | `status`       | `in-review`  | `decided`                                  |
| `threads/[slug]/thread.md` (step 6, per leaf)    | `promoted_to`  | `[…]`        | `[…, tree/[domain]/[leaf].md]`             |
| `threads/[slug]/thread.md` (step 6, per leaf)    | `promoted_at`  | `[…]`        | `[…, <merged_at ISO-8601>]`                |
| `threads/[slug]/thread.md` *(continue)*          | `status`       | `in-review`  | `active`                                   |
| `threads/[slug]/thread.md` *(continue)*          | `maturity`     | `locking`    | `refining`                                 |
| `threads/[slug]/thread.md` *(archive)*           | `status`       | `in-review`  | `archived`                                 |
| `threads/[slug]/thread.md` *(archive)*           | `maturity`     | `locking`    | *(field removed)*                          |
| `threads/[slug]/thread.md` *(archive)*           | `archived_at`  | *(absent)*   | `<merged_at ISO-8601>`                     |
| `threads/[slug]/thread.md` *(archive)*           | `archived_by`  | *(absent)*   | `<git config user.email>`                  |

No leaf fields other than `status` are flipped here — `source_thread`, `domain`, and everything else stay as written by `promote-thread-to-tree`. No thread fields other than the ones listed are touched — `tree_prs` keeps its history across cycles.

## Postconditions

- Every leaf introduced by the PR is `status: decided` on main.
- The thread's `promoted_to` and `promoted_at` each have exactly one new entry per merged leaf, appended in diff order. Parallel-list length invariant (§ 9) holds.
- The thread is either `active/refining` at its original path (continue) or `archived` at `archive/[slug]/` (archive).
- `thread-index.md` and `current-state.md` reflect the post-finalization state (autogenerated).
- `verify-tree` passes on main.
- All preconditions of `derive-impl-spec` are now satisfied for every `decided` leaf from this wave.

## Failure modes

| Failure                                   | Cause                                                                 | Response                                                           |
|-------------------------------------------|-----------------------------------------------------------------------|--------------------------------------------------------------------|
| PR not merged                             | `gh pr view` returns `OPEN` or `CLOSED` without merge                  | refuse — if closed, direct to `discard-promotion` (unbuilt)        |
| Main not fast-forward-mergeable            | Local main diverged from remote                                        | refuse — ask user to reconcile manually, then re-run               |
| Thread not in `in-review`                 | Already finalized, or never promoted                                   | refuse — report current status and suggest audit of `tree_prs`     |
| PR URL not in `tree_prs`                  | Wrong PR URL given, or thread frontmatter was hand-edited              | refuse — ask user to verify PR URL matches one of `tree_prs`       |
| Leaf missing on main                      | Git LFS pointer, merge conflict fallout, or partial revert             | refuse — list missing leaves and ask user to investigate           |
| Leaf not in `in-review` on merge commit   | Promote branch was rebased or force-pushed after the flip-to-in-review commit was made | refuse — list offending leaf(s) and their current status on merge; suggest reverting to pre-merge state and re-running promote-thread-to-tree, or manually editing leaves and creating fixup commit |
| tree_prs[-1] already in promoted_to       | Another finalize-promotion run already committed this PR's leaves     | refuse — ask user to pull latest and re-verify thread state       |
| `git mv` fails (archive path)             | Case-insensitive filesystem collision, permissions                     | refuse — leave thread in `threads/` with status unchanged          |
| Rebuild source-validation failure         | Thread frontmatter schema violations                                  | refuse — report violating thread; user must repair before retrying |
| Rebuild write failure                     | Filesystem / permissions issue                                       | refuse — live index files unchanged (atomic); report error         |
| Push fails                                | Branch protection, CI gate, network                                    | refuse — commit remains local; tell user to resolve and push       |

## Related skills

- **Follows:** `promote-thread-to-tree` — this skill's precondition is that skill's output.
- **Precedes:** `derive-impl-spec` — consumes each `decided` leaf to produce buildable specs.
- **Precedes:** `new-thread` — user may start a new thread after archive.
- **Compatible with:** `multi-agent-debate` — can be invoked between finalize and derive-impl-spec if a leaf needs hardening first.
- **Mutually exclusive with:** `discard-promotion` *(not yet drafted)* — for PRs closed without merging.

## Asset dependencies

- None. This skill reads existing artifacts and flips fields; it does not create new files from templates.

## Versioning

**0.3.2** — Added `--dry-run` flag specification with full semantics contract.

**0.3.0** — Stage 2 of v0.9.0: index-file updates moved to centralized `verify-tree --rebuild-index` final step; previous inline edits removed. Step renumbering: steps 8–12 now shifted to accommodate Final step.

**0.2.0** — Stage 1 (prior stream): safety hardening. Added precondition 7 (verify leaves are in-review on merge commit, defending against rebase/force-push). Added pre-commit step 5 (re-read thread frontmatter to detect concurrent finalize runs). Added Failure modes for both new cases. Step renumbering: steps 6+ now shifted by 1.

**0.1.0** — initial draft. Major bump if the single-commit shape changes, if the continue/archive choice moves out of the skill (e.g. always re-prompt later), or if the thread-cycling semantics in § 4.1 change.
