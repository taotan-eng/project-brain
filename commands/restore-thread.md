---
description: Bring an archived thread back to active (inverse of discard-thread)
argument-hint: "<slug> [--maturity=refining|exploring|locking] [--reason='<why>']"
---

Run the `restore-thread` skill. Inverse of discard-thread. Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/restore-thread.sh` with `--brain` and `--slug`. The script moves `archive/<slug>/` back to `threads/<slug>/`, flips status archived→active, restores maturity (default `refining`), strips archive metadata, rebuilds indexes. Pass `--reason` if the user explained why they're restoring; the script appends it as an audit line.

If the user invokes this without a slug, run `/discover-threads --include-archived --status=archived` first so they can pick from the list.
