---
description: Start a new thread to capture an idea or decision in progress
argument-hint: "<slug> <title> [--purpose='<one-line purpose>']"
---

Run the `new-thread` skill to scaffold a fresh thread under `threads/<slug>/`. Derive `slug`, `title`, and `purpose` from the user's own message where possible ("start a thread about auth" → `slug=auth`, `title=Authentication`, `purpose=thread for authentication`); only ask via AskUserQuestion if the request is genuinely ambiguous. Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/new-thread.sh` with `--brain`, `--slug`, `--title`, `--purpose`. The script auto-reads `--primary-project` from `<brain>/config.yaml` — omit the flag. ~90ms, one permission prompt.
