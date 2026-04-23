---
name: park-thread
description: Pause or resume an active thread without archiving it. Park flips status from active to parked, preserves the current maturity, captures parked_at plus parked_by plus parked_reason (and optionally unpark_trigger), and moves the thread row from Active to Parked in thread-index.md. Unpark (via --unpark) reverses it, restoring the preserved maturity and clearing the park metadata. Thread stays at its original threads/<slug>/ path — no file move. Use when the user says "park this thread", "pause this", "shelve this for now", "resume <slug>", "unpark this", or "bring <slug> back active".
version: 1.0.0-rc4
pack: project-brain
requires:
  - git
  - "read:~/.config/project-brain/projects.yaml"
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
| `--brain=<path>`  | user prompt or cwd inference    | no       | Absolute path to the brain root. Defaults to the nearest ancestor `project-brain/` directory.        |
| `--dry-run`       | boolean                         | no       | Print the plan (status flip, park metadata, commit message) without performing any file writes, git mutations, or audit-log writes. See Process § Dry-run semantics. |

Prompt strategy: resolve `thread_slug` from cwd. Infer `mode` from current status; if ambiguous (e.g. skill invoked without context), ask via `AskUserQuestion`. For `park`, always prompt for `reason` even if the user supplied an inline reason in their original message — parked threads are often re-read weeks later and a one-word reason is rarely enough.

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory is inside a brain root (a `project-brain/` directory containing `CONVENTIONS.md`) or an explicit `--brain=<path>` was given.
2. `project-brain/threads/[thread_slug]/thread.md` exists.
3. For `park` mode:
   - Thread `status` is `active`. Parking from `in-review` is refused (close or merge the PR first); parking from `parked` is a no-op refuse; parking from `archived` is refused.
   - `reason` is non-empty.
4. For `unpark` mode:
   - Thread `status` is `parked`.
   - `parked_at`, `parked_by`, `parked_reason` are present in frontmatter (any missing means the thread was hand-edited into a bad state; refuse and route to manual fix or `verify-tree`).
   - The preserved `maturity` value is one of `exploring | refining | locking`.
5. Working tree has no uncommitted changes to `project-brain/thread-index.md`, `project-brain/current-state.md`, or the thread's `thread.md`.
6. `parked_by` is resolvable. If `--by <email>` is supplied, use it. Otherwise write the literal placeholder `TODO@example.com` into the `parked_by` frontmatter field and append a TODO note to the thread body reminding the user to fix it. **No `git` invocation and no env-var read** — rc4 keeps park-thread shell-free. Precondition always succeeds (placeholder is always available); it never refuses.

## Process

Each step is atomic. Failure at step N leaves the tree in whatever state it was after step N-1.

1. **Resolve inputs.** Infer `thread_slug` from cwd. Determine `mode` (flag or inferred from status). Prompt for operation-specific fields.
2. **Validate preconditions.** Run the subset for the chosen mode. On any failure, stop and report the specific precondition.
3. **Compute timestamp.** Capture the current ISO-8601 timestamp for `parked_at` (park mode only).
4. **Flip frontmatter.** In `project-brain/threads/[thread_slug]/thread.md`:
    - **`park`**:
       - `status: active → parked`.
       - `maturity` field is left exactly as-is. It stays in frontmatter, unchanged, so `unpark` can restore it without a separate memo. § 4.1's "parked has no maturity progression" wording does not mean the field is deleted — it means the value is frozen.
       - Add `parked_at: <timestamp>`, `parked_by: <--by flag if supplied, else the literal `TODO@example.com` placeholder>`, `parked_reason: <reason>`. No shell invocation.
       - If `unpark_trigger` was supplied, add it as `unpark_trigger: <string>`.
    - **`unpark`**:
       - `status: parked → active`.
       - `maturity` untouched (its value was preserved at park time).
       - Remove `parked_at`, `parked_by`, `parked_reason`, and `unpark_trigger` (if present).
       - If `note` was supplied, append it under a `## Park log` heading at the bottom of `thread.md` (create the heading if absent) in the form `YYYY-MM-DD — unparked: <note>`.
5. **Append session transcript** (if `transcript_logging=on` in `<brain>/config.yaml`, default). Append this session's transcript — following the entry schema in CONVENTIONS § 2.5.1 — to `project-brain/threads/[slug]/transcript.md`.

6. **Final step — rebuild indexes**

Invoke `verify-tree --rebuild-index` to regenerate `project-brain/thread-index.md` and `project-brain/current-state.md` from the now-updated per-thread frontmatter.

- If the rebuild returns exit 0: proceed; stage both index files along with the thread directory.
- If the rebuild returns exit 1 (source validation failure): abort. Report the thread(s) that failed source validation. Fix before retrying.
- If the rebuild returns exit 2 (write / verify failure): abort. The live index files are unchanged (atomic write). Report the error.

**Git deferred:** This skill does NOT invoke git. The user runs `git add` and `git commit` themselves.

7. **Report.** Return the new status + maturity and a next-step suggestion.

### Dry-run semantics

When `--dry-run` is set:

1. **Run all preconditions** (steps 1–2 above), including brain-root existence, thread existence, status checks. Exit 1 if any fail.
2. **Compute the full plan:** print the mode (park or unpark), the frontmatter changes, any body append for unpark note, and the rebuild step.
3. **Invoke `verify-tree --rebuild-index --dry-run`** to surface any index-rebuild failures. If that fails, print the error and exit 1.
4. **Write NOTHING to disk:** neither frontmatter edits, nor body appends, nor the transcript.
5. **Exit 0** if the plan would succeed end-to-end, **exit 1** if any check failed, **exit 2** on unexpected error.

Print the plan to stdout as a numbered list. When exiting 1, also print the failing precondition or rebuild error.

## Side effects

### Files written or modified

| Path (relative to brain root)    | Operation         | Mode       | Notes                                                                        |
|----------------------------------|-------------------|------------|-------------------------------------------------------------------------------|
| `threads/[slug]/thread.md`       | edit (frontmatter + optional body append) | both       | Frontmatter flip; `unpark` optionally appends a `## Park log` entry           |
| `threads/[slug]/transcript.md`   | append             | both       | If `transcript_logging=on` (default)                                         |
| `thread-index.md`                | regenerate         | both       | By `verify-tree --rebuild-index` from per-thread frontmatter                 |
| `current-state.md`               | regenerate         | both       | By `verify-tree --rebuild-index` from per-thread frontmatter                 |

No file moves. The thread directory stays at `threads/[slug]/` in both directions. This is deliberate — parking is not archiving.

### Git operations

**None.** This skill performs file operations only. The user runs `git add` and `git commit` themselves (§ Git deferred).

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
- `mode` — `park` or `unpark` (the one that ran).
- `thread_status` — resulting status (`parked` or `active`).
- `preserved_maturity` — the maturity value carried through (always present in both directions).
- `parked_reason` — present if `mode == park`.

### Verbosity contract

Reads `verbosity` from `<brain>/config.yaml` (env override: `PROJECT_BRAIN_VERBOSITY`). Defaults to `terse`.

- **terse** (default): one acknowledgement line naming the operation + thread, then `Done.`
  - Example output: `Parking project-brain/threads/alpha/ (reason: blocked on ADP). Done.`
- **normal**: structured summary of frontmatter changes (status flip, metadata added/removed).
- **verbose**: full narration (pre-rc4 default). Use for debugging.

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
| Brain root not found                                 | No `project-brain/CONVENTIONS.md` up the tree; no `--brain` given                | refuse — prompt user to `init-project-brain`                           |
| Thread slug does not resolve                         | Typo; wrong cwd                                                             | refuse — list nearby slugs                                             |
| `park` on already-`parked` thread                    | Mode mismatch                                                               | refuse — suggest `--unpark` instead                                    |
| `park` on `in-review` thread                         | PR is live                                                                  | refuse — tell user to close, merge, or discard the PR first            |
| `park` on `archived` thread                          | Terminal state                                                              | refuse — no action                                                     |
| `unpark` on non-`parked` thread                      | Mode mismatch                                                               | refuse — report current status                                         |
| Missing park metadata on `unpark`                    | Hand-edited thread; frontmatter broken                                      | refuse — suggest `verify-tree` and manual repair                       |
| Empty `reason` on `park`                             | Slipped past prompt                                                         | re-prompt — reason is not optional                                     |
| (retired in rc4 — `parked_by` defaults to `TODO@example.com` when `--by` not supplied)                        | Git not configured                                                          | refuse — ask user to configure git                                     |
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
