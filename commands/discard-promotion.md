---
description: Close out a promote PR that was closed without merging
---

Run the `discard-promotion` skill. Verifies the PR closed unmerged via `gh`, reverts the thread on main from `in-review` back to `active/refining` without touching `tree_prs` (the closed URL stays as audit per CONVENTIONS § 4.1), updates indexes, optionally deletes the promote branch on the remote.
