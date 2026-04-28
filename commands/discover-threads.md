---
description: Query threads by status, owner, domain, staleness, or PR state
argument-hint: "[--status=... --owner=... --assigned=... --domain=... --modified-before=... --limit=N --format=table|json|csv|yaml|paths]"
---

Run the `discover-threads` skill — pure read-only thread query. Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/discover-threads.sh` once with `--brain=<path>` plus filter flags derived from the user's question. Examples:

- "what threads are assigned to alice" → `--assigned=alice`
- "stale threads in `<a domain the user has actually used>`" → `--domain=<that-domain> --modified-before=<30-days-ago>`
- "parked threads needing attention" → `--status=parked --unpark-trigger-set`
- "what's in review with an open PR" → `--status=in-review --has-pr`

Default behavior (no flags) returns all non-archived threads sorted by `modified-desc`, in `table` format.

**Paste the script's stdout into your reply as Markdown — NOT inside a fenced code block** (the default `table` format is a Markdown table whose `slug` cells are clickable `file://` links; a `` ``` `` wrapper would prevent it from rendering). For `--format=json|csv|yaml|paths` outputs, fencing is fine — those aren't meant to render as Markdown. Don't rely on the Bash tool's result card to display it for you; it collapses by default. No additional commentary unless the user asks a follow-up.
