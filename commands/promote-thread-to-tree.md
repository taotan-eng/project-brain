---
description: Open a PR promoting one or more decisions from an active thread to the shared tree
argument-hint: "[<slug>] [--leaves=<csv>] [--base=<branch>]"
---

Run the `promote-thread-to-tree` skill. First time through this session: probe git/gh readiness (repo, user config, remote, gh auth, registry entry) and print any missing pieces with fix commands before proceeding — this is the first skill in the pack that actually needs git. Then stage leaves under `threads/<slug>/tree-staging/`, cut `promote/<slug>` branch, copy leaves into `tree/<domain>/`, update parent `NODE.md`, open the PR. Flips thread to `in-review` and appends the PR URL to `tree_prs`.
