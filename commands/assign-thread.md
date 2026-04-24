---
description: Manage the assigned_to list on a thread
argument-hint: "[<slug>] --add|--remove|--set|--clear <handles>"
---

Run the `assign-thread` skill. Derive operation from language: "assign X to bob" → `--add bob`, "unassign bob from X" → `--remove bob`, "only alice owns X now" → `--set alice`, "clear assignments on X" → `--clear`. Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/assign-thread.sh` with `--brain`, `--slug`, and exactly one of `--add`/`--remove`/`--set`/`--clear`. The script handles frontmatter edits + audit-trail line + index rebuild in ~110ms.
