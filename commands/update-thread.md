---
description: Change a thread's maturity, soft_links, or prep it for promotion
argument-hint: "[<slug>] <operation> [flags]"
---

Run the `update-thread` skill. Derive `--operation` from phrasing:
- "lock this" / "bump to locking" → `--operation=refine --target=locking`
- "link thread X to Y" → `--operation=soft-link-add --url=<uri>`
- "merge this into Y" → `--operation=merge-into --merge-into-slug=y`
- "prep for promotion" → `--operation=promote-prep`

Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/update-thread.sh` with `--brain`, `--slug`, `--operation`, plus operation-specific flags. ~120ms.
