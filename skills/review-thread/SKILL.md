---
name: review-thread
description: Print a read-only summary of a thread — status/maturity, open questions, decisions-candidates counts, artifacts list, attachments list, and recent transcript entries. Pass --full to dump the entire transcript, --last=N for the last N entries, --since=<ISO8601> to filter by date. Use when the user says "review this thread", "show me the transcript", "what's in thread X", "read the log".
version: 1.0.0-rc4
pack: project-brain
requires:
  - "read:<brain>/threads/<slug>/"
---

# review-thread

Prints a terse summary of a thread so you can catch up on it without reading ten files. Shows frontmatter highlights (status, maturity, owner, dates, purpose), counts of open-questions and decisions-candidates, a listing of artifacts and attachments, and the most recent transcript entries. `--full` dumps the entire transcript. `--last=N` controls the recent-entry window (default 3). `--since=<ISO8601>` filters to entries at or after a timestamp.

This is the counterpart to `record-artifact`. Where `record-artifact` grows the thread, `review-thread` shows you what's in it.

## When to invoke

- "Review thread <slug>" / "show me thread X"
- "What's in this thread?" (when cwd is inside a thread)
- "Read the transcript"
- "What have I decided on <topic>?" — first step before deeper queries
- Catching up after a parked thread is resumed

## Inputs

| Name             | Source                  | Required | Description |
|------------------|-------------------------|----------|-------------|
| `slug`           | cwd inference or user   | yes      | Target thread. Looked up in `threads/` then `archive/`. |
| `--full`         | flag                    | no       | Append the entire transcript after the summary. Default: last 3 entries. |
| `--last=<N>`     | flag                    | no       | Show the last N transcript entries. Default 3. Ignored with `--full`. |
| `--since=<ts>`   | flag                    | no       | Show transcript entries at or after this ISO8601 timestamp. Combined with `--last` as an upper bound. |
| `--brain=<path>` | cwd inference           | no       | Absolute path to brain. Defaults to nearest ancestor containing `CONVENTIONS.md`. |

Prompt strategy: infer `slug` from cwd. Ask via `AskUserQuestion` only if the cwd is outside any thread dir and the user didn't name one.

## Preconditions

1. Brain root reachable.
2. `threads/<slug>/` or `archive/<slug>/` exists.
3. `threads/<slug>/thread.md` exists and is readable.

Skill is pure read-only — no writes, no shell spawns beyond awk/sed/find — so it's safe to call freely. Single bash permission prompt; ~120ms even on thick threads.

## Process

> ### ⛔️ HARD CONSTRAINT — ONE TOOL CALL + VERBATIM ECHO AS MARKDOWN
>
> **Call `${CLAUDE_PLUGIN_ROOT}/scripts/review-thread.sh` ONCE.** No `Read` of thread.md, transcript.md, or artifacts — the script parses and renders everything.
>
> **After the bash call returns, paste the script's stdout into your assistant message in full as Markdown — do NOT wrap it in a fenced code block.** The script outputs Markdown (H1/H2 headers, bullet lists, `file://` links, *italics*); a `` ``` `` wrapper would prevent every part of it from rendering. Do not summarize. Do not transform. Do not rely on the Bash tool's result card to display it for you — the result card collapses by default, so an empty (or fenced) assistant message means the user sees only "Ran a command >" with no detail.
>
> **WRONG** — empty assistant message, OR pasting inside `` ``` ... ``` ``: both kill rendering.
> **RIGHT** — paste the stdout directly as the body of your reply, then optionally one short follow-up sentence.
>
> **Derive `--full` / `--last` / `--since` from phrasing:** "show me the full transcript" → `--full`. "what happened last week" → `--since=<computed>`. Otherwise default (summary + last 3 entries).

**One call:**

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/review-thread.sh" \
  --brain=<absolute brain path> \
  --slug=<thread-slug>          \
  [--full]                      \
  [--last=<N>]                  \
  [--since=<ISO8601>]
```

Infer `--slug` from cwd; only ask if the user is outside any thread dir and didn't name one. After success, **paste the script's stdout into your reply as Markdown — NOT inside a fenced code block** (the output is Markdown and won't render inside `` ``` ``). The output contains clickable `file://` links that only render when echoed unfenced. Don't rely on the Bash tool's result card. No additional commentary unless the user asks a follow-up.

### Dry-run semantics

None needed. `review-thread` is read-only.

## Failure modes

- `thread '<slug>' not found` → exit 2. Invoke `discover-threads` or ask for correct slug.
- `<thread>/thread.md does not exist` → exit 2. Thread dir is malformed; likely a partial `new-thread` failure. Re-run `verify-tree` to diagnose.

## Postconditions

- Stdout contains the summary (and optional transcript dump).
- No files modified anywhere.

## Related skills

- **`record-artifact`**: the write-side counterpart.
- **`discover-threads`**: lists all threads, doesn't drill into one.
- **`new-thread`**: creates threads that `review-thread` reads.
- **`verify-tree`**: if `review-thread` shows stale counts, `verify-tree --rebuild-index` resyncs `thread-index.md` and `current-state.md`.

## Changelog

**1.0.0-rc4** — Initial release.
