---
description: Validate the brain — check invariants V-01..V-22
argument-hint: "[--rebuild-index] [--thread=<slug> | --path=<subpath>]"
---

Run the `verify-tree` skill. Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/verify-tree.py --brain=<path>` to check invariants, or add `--rebuild-index` to regenerate `thread-index.md` and `current-state.md` from per-thread frontmatter. Read-only in default mode; deterministic. Exit 0 = clean, 1 = violations found (stderr lists them), 2 = invocation error.
