---
description: Summarize a thread — status, questions, decisions, artifacts, transcript
argument-hint: "[<slug>] [--full | --last=N | --since=<ISO8601>]"
---

Run the `review-thread` skill. Pure read-only. Derive `--slug` from cwd; derive flags from phrasing ("full transcript" → `--full`, "last 10" → `--last=10`). Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/review-thread.sh` with `--brain` and `--slug` once. **Echo the script's stdout in your response message verbatim** — don't rely on the Bash tool's result card to display it; the user should see the script's output as part of your reply. No additional commentary unless the user asks a follow-up.
