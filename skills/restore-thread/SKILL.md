---
name: restore-thread
description: Bring an archived thread back to active. Inverse of discard-thread. Moves archive/<slug>/ back to threads/<slug>/, flips status archived→active, restores maturity (default refining), strips archive metadata, rebuilds indexes. Use when the user says "restore this thread", "unarchive <slug>", "I want to keep working on the discarded thread", or "bring back <slug>".
version: 1.0.0-rc4
pack: project-brain
requires:
  - "read:[brain-root]"
  - "write:[brain-root]"
---

# restore-thread

Brings an archived thread back to active. The inverse of `discard-thread`. Moves `archive/<slug>/` to `threads/<slug>/`, flips frontmatter `status: archived → active`, restores `maturity` (defaults to `refining` since the thread had work in flight before discard), removes the archive metadata fields (`archived_at`, `archived_by`, `discard_reason`), rebuilds aggregate indexes. The original archive metadata is preserved in the thread body as a one-line audit comment so the restore is auditable later.

## When to invoke

- "Restore the X thread" / "unarchive X" / "bring X back"
- "I changed my mind on discarding X — keep working on it"
- "Mistakenly discarded — restore"
- After cleaning up a `discover-threads --include-archived` review and picking one to revive

## Inputs

| Name             | Source                  | Required | Description |
|------------------|-------------------------|----------|-------------|
| `slug`           | user prompt             | yes      | Thread slug to restore. Must currently exist under `archive/<slug>/`. |
| `--maturity`     | flag                    | no       | One of `exploring | refining | locking`. Default `refining` — most archived threads had been making progress before discard. |
| `--reason`       | flag                    | no       | Free-text reason for the restore. Appended as an audit comment to the thread body. |
| `--by`           | flag                    | no       | Actor email. Default `TODO@example.com` placeholder. |
| `--brain=<path>` | cwd inference           | no       | Absolute path to brain. Defaults to nearest ancestor `project-brain/` containing CONVENTIONS.md. |

## Preconditions

The skill **refuses** if any are not met:

1. Brain root reachable (`<brain>/CONVENTIONS.md` exists).
2. `archive/<slug>/thread.md` exists.
3. The thread's frontmatter has `status: archived` (defends against running on a non-archived thread that somehow ended up under `archive/`).
4. `threads/<slug>/` does NOT exist (no slug collision with an active thread).
5. `--maturity` if supplied is one of `exploring | refining | locking`.

## Process

> ### ⛔️ HARD CONSTRAINT — ONE TOOL CALL
>
> **Call `${CLAUDE_PLUGIN_ROOT}/scripts/restore-thread.sh` ONCE.** No `Read` of thread.md, no manual `mv`, no manual frontmatter edit. The script reads, validates, mutates, moves, rebuilds — all atomic.
>
> **Derive `--reason` from context** when the user provided one ("I want to bring X back because Y" → `--reason='Y'`). Use `AskUserQuestion` only if the user gave no rationale and you genuinely don't know — but for a restore the rationale is usually optional anyway.

**One call:**

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/restore-thread.sh" \
  --brain=<absolute brain path> \
  --slug=<thread-slug>          \
  [--maturity=refining]         \  # default; pass exploring or locking if known
  [--reason='<why restoring>']  \
  [--by=<email>]
```

After success, echo the script's stdout in your response message verbatim — don't rely on the Bash tool's result card to display it; the user should see the script's output as part of your reply. The script prints the new status + maturity, the optional reason, and `Done.`

## Failure modes

- `archived thread not found` → exit 1. The slug doesn't exist under `archive/`. Check spelling or run `/discover-threads --include-archived` to list archived slugs.
- `target already exists` → exit 1. An active thread with the same slug exists. Either pick a different slug or rename the existing one first.
- `cannot restore a <status> thread (expected: archived)` → exit 1. The thread under `archive/` doesn't have `status: archived` in frontmatter — the brain is half-broken. Run `verify-tree` to diagnose.

## Postconditions

- `threads/<slug>/` contains the restored thread (all sibling files moved verbatim — `transcript.md`, `decisions-candidates.md`, etc., come back too).
- `archive/<slug>/` no longer exists.
- Thread frontmatter: `status: active`, `maturity: <chosen>`, no `archived_*` fields, `last_modified_at` updated.
- Thread body has a `<!-- <ts> — restored from archive by <by> [— <reason>] -->` audit line at the bottom.
- `thread-index.md` and `current-state.md` reflect the restore.
- `verify-tree --brain <brain>` exits clean.

## Related skills

- **`discard-thread`**: the operation this undoes.
- **`discard-promotion`**: when an in-review thread's PR closed unmerged — different recovery path (thread is still in `threads/`, just stuck in `in-review`). Don't use restore-thread for that case.
- **`discover-threads --include-archived`**: lists archived threads so you can find the slug to restore.

## Compatibility

The restore appends an HTML-comment audit line to the thread body so the round-trip is visible. The original `archived_at` / `archived_by` / `discard_reason` are NOT preserved in frontmatter — they're cleaned out as part of the status flip. If the thread is later re-discarded, a fresh set of archive fields gets written; the previous archive episode lives only in the body audit comment.

## Changelog

**1.0.0-rc4** — Initial release. Closes the gap where `discard-thread` was one-way; previously the only restore path was manual file moves + frontmatter edits, which violated the pack's one-tool-call discipline.
