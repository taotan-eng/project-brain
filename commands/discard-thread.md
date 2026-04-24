---
description: Archive a thread that was never promoted (kill an active or parked thread)
argument-hint: "[<slug>] '<reason>'"
---

Run the `discard-thread` skill. Derive `--reason` from the user's stated motivation ("this approach didn't pan out", "dupe of X"); only ask if absent. Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/discard-thread.sh` with `--brain`, `--slug`, `--reason`. If the script exits non-zero citing `tree_prs`, route to `discard-promotion` instead.
