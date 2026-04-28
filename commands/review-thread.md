---
description: Summarize a thread — status, questions, decisions, artifacts, transcript
argument-hint: "[<slug>] [--full | --last=N | --since=<ISO8601>]"
---

Run the `review-thread` skill. Pure read-only. Derive `--slug` from cwd; derive flags from phrasing ("full transcript" → `--full`, "last 10" → `--last=10`). Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/review-thread.sh` with `--brain` and `--slug` once.

**After the bash call returns, paste the script's stdout into your reply, in full, as Markdown — NOT inside a fenced code block.** The output IS Markdown (H1/H2 headers, bullet lists, `file://` links); wrapping it in `` ``` ... ``` `` would prevent any of it from rendering. Don't rely on the Bash tool's result card either — it collapses by default and the user would just see "Ran a command >" with no detail.

**WRONG** — empty assistant message, OR pasted inside `` ``` ``: both kill rendering. **RIGHT** — pasted stdout directly as the body of the reply, optional one-sentence follow-up. No additional commentary unless the user asks a follow-up.
