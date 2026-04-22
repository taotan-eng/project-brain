---
name: park-thread
description: Pause or resume an active thread without archiving it. Park flips status from active to parked, preserves the current maturity, captures parked_at plus parked_by plus parked_reason (and optionally unpark_trigger), and moves the thread row from Active to Parked in thread-index.md. Unpark (via --unpark) reverses it, restoring the preserved maturity and clearing the park metadata. Thread stays at its original threads/<slug>/ path — no file move. Use when the user says "park this thread", "pause this", "shelve this for now", "resume <slug>", "unpark this", or "bring <slug> back active".
version: 0.2.2
pack: project-brain
requires:
  - git
  - "read:~/.ai/projects.yaml"
  - "write:[brain-root]"
---

# park-thread

Parking is the "alive but paused" state. A thread gets parked when work is blocked on something external (a missing dependency, a decision elsewhere, a quarter-boundary wait), or when the author realizes the thread is not the right shape yet but does not want to discard it. Parked threads stay at their original path and keep every byte of their content — only `status` and a small set of park metadata fields change.

Unparking is the symmetric reverse: clear the park metadata, restore `status: active`, and restore the `maturity` value held at park time. The skill treats the two directions as one operation with a `--unpark` flag because they share every non-trivial step (resolve, validate, flip, re-sync index, commit) and the divergence is narrow.

## When to invoke

- "Park this thread" / "pause this" / "shelve this for now"
- "I need to stop thinking about <slug> until <X>"
- "Unpark <slug>" / "resume this thread" / "pick this back up"
- When `current-state.md` is cluttered with threads the user isn't actively working, and they want to hide them without killing them
- Before switching contexts for a long stretch and wanting to document why the thread was left

## Inputs

| Name              | Source                          | Required | Description                                                                                     |
|-------------------|---------------------------------|----------|-------------------------------------------------------------------------------------------------|
| `thread_slug`     | user prompt or cwd inference    | yes      | Slug of the thread. Defaults to the thread whose directory contains cwd.                        |
| `mode`            | flag (`--unpark`) or inferred   | yes      | `park` or `unpark`. If flag is absent, infer from current thread status: `active → park`, `parked → unpark`. Mismatch is a refuse. |
| `reason`          | user prompt                     | cond.    | Short "why paused". Required for `park`. 1–3 sentences; verbatim into `parked_reason`.          |
| `unpark_trigger`  | user prompt                     | no       | Optional for `park`. Free-form description of what would cause resumption (e.g. "after Q3 planning", "when ADP spec lands"). |
| `note`            | user prompt                     | no       | Optional for `unpark`. A brief note appended to `thread.md` under a `## Park log` heading to record the round-trip. |
| `--brain=<path>`  | user prompt or cwd inference    | no       | Absolute path to the brain root. Defaults to the nearest ancestor `thoughts/` directory.        |
| `--dry-run`       | boolean                         | no       | Print the plan (status flip, park metadata, commit message) without performing any file writes, git mutations, or audit-log writes. See Process § Dry-run semantics. |

Prompt strategy: resolve `thread_slug` from cwd. Infer `mode` from current status; if ambiguous (e.g. skill invoked without context), ask via `AskUserQuestion`. For `park`, always prompt for `reason` even if the user supplied an inline reason in their original message — parked threads are often re-read weeks later and a one-word reason is rarely enough.

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory is inside a brain root (a `thoughts/` directory containing `CONVENTIONS.md`) or an explicit `--brain=<path>` was given.
2. `thoughts/threads/[thread_slug]/thread.md` exists.
3. For `park` mode:
   - Thread `status` is `active`. Parking from `in-review` is refused (close or merge the PR first); parking from `parked` is a no-op refuse; parking from `archived` is refused.
   - `reason` is non-empty.
4. For `unpark` mode:
   - Thread `status` is `parked`.
   - `parked_at`, `parked_by`, `parked_reason` are present in frontmatter (any missing means the thread was hand-edited into a bad state; refuse and route to manual fix or `verify-tree`).
   - The preserved `maturity` value is one of `exploring | refining | locking`.
5. Working tree has no uncommitted changes to `thoughts/thread-index.md`, `thoughts/current-state.md`, or the thread's `thread.md`.
6. `git config user.email` returns a value (used to populate `parked_by` on park).

## Process

Each step is atomic. Failure at step N leaves the tree in whatever state it was after step N-1.

1. **Resolve inputs.** Infer `thread_slug` from cwd. Determine `mode` (flag or inferred from status). Prompt for operation-specific fields.
2. **Validate preconditions.** Run the subset for the chosen mode. On any failure, stop and report the specific precondition.
3. **Compute timestamp.** Run `date -u +%Y-%m-%dT%H:%M:%SZ` for `parked_at` (park mode only).
4. **Flip frontmatter.** In `thoughts/threads/[thread_slug]/thread.md`:
    - **`park`**:
       - `status: active → parked`.
       - `maturity` field is left exactly as-is. It stays in frontmatter, unchanged, so `unpark` can restore it without a separate memo. § 4.1's "parked has no maturity progression" wording does not mean the field is deleted — it means the value is frozen.
       - Add `parked_at: <timestamp>`, `parked_by: <git config user.email>`, `parked_reason: <reason>`.
       - If `unpark_trigger` was supplied, add it as `unpark_trigger: <string>`.
    - **`unpark`**:
       - `status: parked → active`.
       - `maturity` untouched (its value was preserved at park time).
       - Remove `parked_at`, `parked_by`, `parked_reason`, and `unpark_trigger` (if present).
       - If `note` was supplied, append it under a `## Park log` heading at the bottom of `thread.md` (create the heading if absent) in the form `YYYY-MM-DD — unparked: <note>`.
5. **Update `thread-index.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
6. **Update `current-state.md`.** **(Removed in 0.9.0-alpha.2: index files are now autogenerated. See Final step below.)**
7. **Commit.** Stage the thread directory: `git add thoughts/threads/[slug]/`. The index files will be staged in the Final step.
8. **Final step — rebuild indexes**

Invoke `verify-tree --rebuild-index` to regenerate `thoughts/thread-index.md` and `thoughts/current-state.md` from the now-updated per-thread frontmatter.

- If the rebuild returns exit 0: proceed to commit; stage both index files along with the thread directory in a single commit: `git add thoughts/threads/[slug]/ thoughts/thread-index.md thoughts/current-state.md && git commit -m "chore([slug]): <park or unpark message>"`.
- If the rebuild returns exit 1 (source validation failure): abort this skill's commit. Report the thread(s) that failed source validation — they indicate schema violations introduced (or already present) in this operation. Fix the underlying thread before retrying this skill.
- If the rebuild returns exit 2 (write / verify failure): abort. The live index files are unchanged (atomic write). Report the error; this is typically a filesystem / permissions issue.

Rationale: per CONVENTIONS § 1, `thread-index.md` and `current-state.md` are autogenerated projections of per-thread frontmatter. This skill maintains its invariants by updating the per-thread source; the aggregate view is refreshed as the last step so that (a) index files always reflect post-operation state, and (b) concurrent skills never collide on hand-edits of the aggregate files.

9. **Report.** Return the commit SHA, the new status + maturity, and a next-step suggestion (see § Outputs).

No automatic push — matches `new-thread` / `update-thread` conventions for pre-promotion thread work.

### Dry-run semantics

When `--dry-run` is set:

1. **Run all preconditions** (steps 1–2 above), including brain-root existence, thread existence, status checks, and mode-specific guards. Exit 1 if any precondition fails.
2. **Compute the full plan:** print the mode (park or unpark), the frontmatter changes (status flip, park metadata add/remove), any body append for unpark note, and the commit message.
3. **Invoke `verify-tree --rebuild-index --dry-run`** to surface any index-rebuild failures (step 8). If that fails, print the rebuild error and exit 1.
4. **Write NOTHING to disk:** neither frontmatter edits, nor body appends, nor the audit log.
5. **Invoke NO git mutations:** no `git add`, no `git commit`. Read-only git operations are allowed.
6. **Exit 0** if the plan would succeed end-to-end, **exit 1** if any precondition or rebuild-dry-run check failed, **exit 2** on unexpected error.

Print the plan to stdout as a numbered list (e.g., "1. Apply operation: park (reason: <reason>)", "2. Edit thread.md: status active → parked, add parked_at/parked_by/parked_reason", "3. Run verify-tree --rebuild-index --dry-run", "4. Commit: chore(<slug>): park thread"). When exiting 1, also print the failing precondition or rebuild error.

## Side effects

### Files written or modified

| Path (relative to brain root)    | Operation         | Mode       | Notes                                                                        |
|----------------------------------|-------------------|------------|-------------------------------------------------------------------------------|
| `threads/[slug]/thread.md`       | edit (frontmatter + optional body append) | both       | Frontmatter flip; `unpark` optionally appends a `## Park log` entry           |
| `thread-index.md`                | edit              | both       | Row moves between `## Active` and `## Parked`                                 |
| `current-state.md`               | edit              | both       | Bullet moves between "Active threads" and "Parked threads"                    |

No file moves. The thread directory stays at `threads/[slug]/` in both directions. This is deliberate — parking is not archiving.

### Git operations

| Operation                              | Trigger | Notes                                                            |
|----------------------------------------|---------|-------------------------------------------------------------------|
| `git add thoughts/ && git commit -m …` | step 7  | Single commit per invocation                                      |

No branch creation, no push.

When `--dry-run` is set: NO side effects. Stdout output only.

### External calls

None.

## Outputs

**User-facing summary.** A short message with:

- The commit SHA.
- The new status (`parked` or `active`) and the preserved (park) or restored (unpark) maturity.
- For `park`: the reason and unpark trigger, plus the suggestion "Run `park-thread --unpark [slug]` when you're ready to resume."
- For `unpark`: a pointer to the `## Park log` entry (if written) and the suggestion "Continue with `update-thread` or `promote-thread-to-tree`."

**State passed forward.**

- `thread_slug` — unchanged.
- `park_commit` — SHA of the single commit.
- `mode` — `park` or `unpark` (the one that ran).
- `thread_status` — resulting status (`parked` or `active`).
- `preserved_maturity` — the maturity value carried through (always present in both directions).
- `parked_reason` — present if `mode == park`.

## Frontmatter flips

| File                          | Field             | Before           | After                       | Mode     |
|-------------------------------|-------------------|------------------|------------------------------|----------|
| `threads/[slug]/thread.md`    | `status`          | `active`         | `parked`                     | park     |
| `threads/[slug]/thread.md`    | `parked_at`       | *(absent)*       | `<ISO-8601>`                 | park     |
| `threads/[slug]/thread.md`    | `parked_by`       | *(absent)*       | `<email>`                    | park     |
| `threads/[slug]/thread.md`    | `parked_reason`   | *(absent)*       | `<string>`                   | park     |
| `threads/[slug]/thread.md`    | `unpark_trigger`  | *(absent)*       | `<string>` *(only if given)* | park     |
| `threads/[slug]/thread.md`    | `status`          | `parked`         | `active`                     | unpark   |
| `threads/[slug]/thread.md`    | `parked_at`       | `<ISO-8601>`     | *(removed)*                  | unpark   |
| `threads/[slug]/thread.md`    | `parked_by`       | `<email>`        | *(removed)*                  | unpark   |
| `threads/[slug]/thread.md`    | `parked_reason`   | `<string>`       | *(removed)*                  | unpark   |
| `threads/[slug]/thread.md`    | `unpark_trigger`  | `<string>` or absent | *(removed)*              | unpark   |

`maturity` is never flipped by this skill in either direction. It is preserved across the park/unpark round-trip by design.

When `--dry-run` is set: no files are written; the frontmatter changes and any body appends are described in the plan output instead.

## Postconditions

- Thread directory unchanged at `threads/[slug]/`. Nothing moved, no content deleted.
- On `park`: `status == parked`, the four park metadata fields are populated, and the thread is visible under `## Parked` in `thread-index.md` (autogenerated).
- On `unpark`: `status == active`, no park metadata present, and the thread is visible under `## Active` in `thread-index.md` (autogenerated).
- `maturity` equals whatever it was pre-skill (park direction) or pre-park (unpark direction). The round-trip is lossless.
- `thread-index.md` and `current-state.md` reflect the post-operation state of all threads (autogenerated).
- Exactly one commit was added.
- `verify-tree` passes on the thread.

## Failure modes

| Failure                                              | Cause                                                                       | Response                                                               |
|-------------------------------------------------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------|
| Brain root not found                                 | No `thoughts/CONVENTIONS.md` up the tree; no `--brain` given                | refuse — prompt user to `init-project-brain`                           |
| Thread slug does not resolve                         | Typo; wrong cwd                                                             | refuse — list nearby slugs                                             |
| `park` on already-`parked` thread                    | Mode mismatch                                                               | refuse — suggest `--unpark` instead                                    |
| `park` on `in-review` thread                         | PR is live                                                                  | refuse — tell user to close, merge, or discard the PR first            |
| `park` on `archived` thread                          | Terminal state                                                              | refuse — no action                                                     |
| `unpark` on non-`parked` thread                      | Mode mismatch                                                               | refuse — report current status                                         |
| Missing park metadata on `unpark`                    | Hand-edited thread; frontmatter broken                                      | refuse — suggest `verify-tree` and manual repair                       |
| Empty `reason` on `park`                             | Slipped past prompt                                                         | re-prompt — reason is not optional                                     |
| `git config user.email` empty                        | Git not configured                                                          | refuse — ask user to configure git                                     |
| Uncommitted edits to unrelated paths                 | Conflict risk                                                               | refuse — ask user to stash or commit                                   |
| Rebuild source-validation failure                    | Thread frontmatter schema violations                                        | refuse — report violating thread; user must repair before retrying     |
| Rebuild write failure                                | Filesystem / permissions issue                                             | refuse — live index files unchanged (atomic); report error             |
| `--dry-run` plan shows a precondition failure        | Any precondition failed during dry-run                                      | skill exits 1 after printing the plan and the failing precondition. The plan is still useful: the user sees both what was intended and why it wouldn't work. |

## Related skills

- **Coordinates with:** `update-thread`, `discard-thread` — the three pre-promotion thread operations; mutually exclusive per invocation.
- **Blocks:** `promote-thread-to-tree` — will refuse on a `parked` thread; unpark first.
- **Compatible with:** `verify-tree` — run after unpark to confirm the round-trip restored a clean state.
- **Mutually exclusive with:** itself — cannot be re-invoked in the same mode without an interleaving flip (no-op refuse).

## Asset dependencies

None. The skill edits existing frontmatter and index files; it does not create files from templates. The `## Park log` heading in `thread.md` is created on-demand by `unpark` when a `note` is supplied.

## Versioning

**0.2.2** — Added `--dry-run` flag specification with full semantics contract, including exit codes 0/1/2 (2 reserved for unexpected errors).

**0.2.0** — Stage 2 of v0.9.0: index-file updates moved to centralized `verify-tree --rebuild-index` final step; previous inline edits removed.

**0.1.0** — initial draft. Minor bump if a `pin`/`snooze` variant is added (e.g. a "park until <date>" that auto-unparks). Major bump if the preservation semantics around `maturity` change (e.g. a rule that parking always resets maturity to `refining` on unpark).
