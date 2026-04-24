---
description: Summarize a thread — status, questions, decisions, artifacts, transcript
argument-hint: "[<slug>] [--full | --last=N | --since=<ISO8601>]"
---

Run the `review-thread` skill. Pure read-only. Derive `--slug` from cwd; derive flags from phrasing ("full transcript" → `--full`, "last 10" → `--last=10`). Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/review-thread.sh` with `--brain` and `--slug` once; pass stdout through verbatim without commentary unless the user asks a follow-up.
