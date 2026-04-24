---
description: Query threads by status, owner, domain, staleness, or PR state
argument-hint: "[--status=... --owner=... --domain=... --modified-after=... --limit=N]"
---

Run the `discover-threads` skill. Read-only. Derive filter flags from the user's question ("parked threads assigned to me" → `--status=parked --assigned=<user-handle>`; "stale threads in engineering" → `--status=active --domain=engineering --modified-before=<30-days-ago>`). Walk `threads/*/thread.md` + optionally `archive/*/thread.md` with `--include-archived`, apply filters, render the matching threads.
