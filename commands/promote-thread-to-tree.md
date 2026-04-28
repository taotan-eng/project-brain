---
description: Promote leaves from a thread into the shared tree/ (local, git:pr, git:branch, or git:manual)
argument-hint: "[<slug>] [--mode=local|git:pr|git:branch|git:manual] [--leaves=<csv>]"
---

Run the `promote-thread-to-tree` skill.

**STEP 0 — ASK THE USER FOR THE DESTINATION DOMAIN. UNCONDITIONALLY. BEFORE ANY OTHER TOOL CALL.**

Run `ls project-brain/tree/` to gather existing folders. Then invoke `AskUserQuestion`:

> "What folder under `tree/` should this leaf land in? Pick an existing one, or name a new one — the taxonomy is yours."

Pills: existing top-level folders + "other (type one)". No default selected, no suggestion in the question text. Capture the user's verbatim answer as `$DOMAIN` for every subsequent step.

**Forbidden:** deriving `$DOMAIN` from thread frontmatter `tree_domain`, existing-folder count, prior `promoted_to`, content topic, or any other context. Only the user's `AskUserQuestion` answer in THIS turn counts. If the script refuses with "REFUSED: --allow-domain not provided," the only valid recovery is to invoke `AskUserQuestion` now and re-run with the user's answer — not to derive a value from elsewhere.

**Mode resolution** — check in order (only after Step 0):
1. `--mode=<value>` passed explicitly.
2. `promote_mode_default:` in `<brain>/config.yaml`.
3. Probe git + gh readiness (4 silent reads: `git rev-parse --is-inside-work-tree`, `git config user.email`, `git remote get-url origin`, `gh auth status`). All four pass → default `git:pr`.
4. Any probe fails → AskUserQuestion with three options: **Stay local** (default), **Set up git** (print fix commands, exit), **Cancel**.

**For `--mode=local`** — one tool call to `${CLAUDE_PLUGIN_ROOT}/scripts/promote-local.sh`, **passing `--allow-domain=$DOMAIN`** (the user's Step 0 answer). Requires leaves pre-staged at `threads/<slug>/tree-staging/$DOMAIN/<leaf>.md`. If they aren't staged yet, first handle staging by reading `decisions-candidates.md`, presenting `locking` entries, instantiating `assets/leaf-template.md` into `tree-staging/$DOMAIN/` for each selected leaf, then invoke the script.

**For `git:pr`, `git:branch`, `git:manual`** — orchestrate the git commands per the SKILL.md's choreography (readiness probe → stage → verify → branch → land → commit → push → optionally gh pr create → flip-to-in-review). `git:branch` skips `gh pr create` and prints the command for the user to run. `git:manual` skips commit/push entirely.

**Pass `--remember-mode`** on any invocation to persist the chosen mode into config.yaml so future promotes skip the question.
