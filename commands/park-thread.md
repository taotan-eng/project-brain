---
description: Pause (or resume) a thread without archiving it
argument-hint: "[<slug>] '<reason>' | --unpark [--trigger='<text>']"
---

Run the `park-thread` skill. Derive mode + reason from language: "park this for now, waiting on X" → `--reason='waiting on X'`; "pick this back up, X just landed" → `--unpark --trigger='X landed'`. Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/park-thread.sh` with `--brain` and `--slug`, plus either `--reason=<text>` or `--unpark`. ~100ms.
