---
description: Capture a debate result, benchmark, analysis, or file into a thread
argument-hint: "[<slug>] '<title>' [--kind=debate|analysis|benchmark|reference|sketch] [--append]"
---

Run the `record-artifact` skill. Derive `--slug` from cwd (nearest `threads/<slug>/` ancestor), `--title` from the user's framing, and `--artifact-kind` from language ("debate result" → `debate`, "benchmark" → `benchmark`, etc.). Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/record-artifact.sh` with `--brain`, `--slug`, `--title`, and ONE of `--content='...'` / `--file=<path>` / `--stdin`. Markdown routes to `artifacts/`, non-markdown to `attachments/`, transcript gets a breadcrumb either way. Pass `--append` when the user wants the content in transcript.md directly instead of a separate file.
