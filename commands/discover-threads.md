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

**Echo the script's stdout in your response message verbatim** — don't rely on the Bash tool's result card to display it; the user should see the script's output as part of your reply. No additional commentary unless the user asks a follow-up.
