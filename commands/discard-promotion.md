---
description: Revert a promote PR back to active (handles both closed-unmerged PRs and user-canceled OPEN PRs)
---

Run the `discard-promotion` skill. Two cases:

1. **PR was closed without merging** (rejected by reviewers, abandoned, etc.) — verify state via `gh pr view`, revert thread frontmatter on main from `in-review` back to `active/refining` without touching `tree_prs` (the closed URL stays as audit per CONVENTIONS § 4.1).

2. **User wants to cancel an OPEN PR mid-review** to keep editing the thread — this is the canonical edit-mid-review escape hatch. The skill closes the PR itself via `gh pr close --delete-branch`, then proceeds with the same revert. The closed URL still stays in `tree_prs` for audit. Reviewers' comments persist on the now-closed PR for later reference.

Either way: thread becomes locally editable again, re-promote when ready.

If the user said "I want to update the in-review thread" or `update-thread` errored with `cannot update a in-review thread`, this is the right next skill.
