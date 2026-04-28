---
description: Summarize a thread — status, questions, decisions, artifacts, transcript
argument-hint: "[<slug>] [--full | --last=N | --since=<ISO8601>]"
---

Run the `review-thread` skill. Pure read-only. Derive `--slug` from cwd; derive flags from phrasing ("full transcript" → `--full`, "last 10" → `--last=10`). Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/review-thread.sh` with `--brain` and `--slug` once.

**After the bash call returns, paste the script's stdout into your reply, in full, inside a fenced code block.** The output contains clickable `computer://` links to thread.md, transcript.md, artifacts, and attachments — those links *only render when you echo the stdout in your reply.* Don't rely on the Bash tool's result card to display it for you; it collapses by default and the user would just see "Ran a command >" with no detail.

**WRONG** — empty assistant message (or one-line summary). **RIGHT** — pasted stdout in a code block, optional one-sentence follow-up. No additional commentary unless the user asks a follow-up.
