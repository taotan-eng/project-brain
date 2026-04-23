---
name: promote-thread-to-tree
description: Promote one or more decisions from an active thread into the shared knowledge tree via a pull request. Stages the leaves under project-brain/threads/[slug]/tree-staging/, cuts a promote/[slug] branch from the chosen base, copies the staged files into project-brain/tree/[domain]/, updates the parent NODE.md, opens a PR using assets/pr-body-templates/promote.md, and flips the thread to in-review while appending the PR URL to tree_prs. Use when the user says "promote this thread", "land these decisions", "open a promotion PR", or similar.
version: 1.0.0-rc4
pack: project-brain
requires:
  - git
  - gh
  - "read:~/.config/project-brain/projects.yaml"
  - "write:[brain-root]"
---

# promote-thread-to-tree

Takes a thread that has ripened (candidates tagged `locking` in `decisions-candidates.md`) and moves the agreed-upon leaves into the shared tree through a reviewable pull request. The skill is the bridge between private ideation and team-visible decisions: before it runs, the thread is a scratchpad; after the PR merges, the decisions are part of the tree's permanent record.

The skill is split across three commits on the promote branch, in this order: **stage** (copy the leaves into the thread's `tree-staging/` area for eyeballing), **land** (move staged files into the real tree; leaves stay `status: draft`), and **flip-to-in-review** (once the PR URL is known, flip the landed leaves from `draft → in-review` and sync the thread frontmatter). The three-commit split preserves § 4.2's invariant that an `in-review` leaf always has a populated `tree_prs` on its parent thread — the flip commit is the first moment both conditions can be true atomically.

## When to invoke

- "Promote this thread" / "land these decisions" / "open a promotion PR"
- "Take the locking candidates to the tree"
- "Open a PR for thread [slug]"
- At the end of a thread's `locking` maturity phase
- When `decisions-candidates.md` has at least one entry tagged `maturity: locking`

## Inputs

| Name               | Source                              | Required | Description                                                                              |
|--------------------|-------------------------------------|----------|------------------------------------------------------------------------------------------|
| `thread_slug`      | user prompt or cwd inference        | yes      | Slug of the source thread. If cwd is inside `threads/[slug]/`, default to that.          |
| `leaves`           | user prompt                         | yes      | One or more decisions to promote. Default set = all `locking`-tagged entries in `decisions-candidates.md`. |
| `target_remote`    | `~/.config/project-brain/projects.yaml` + user prompt | yes      | Remote name (§ 2). Implicit if the project has one `remotes` entry; prompted otherwise.  |
| `base_branch`      | `--base` flag or user prompt        | yes      | PR base branch. Defaults to the selected remote's `default_base`; always confirmed.      |
| `branch_suffix`    | user prompt                         | no       | Extra suffix for split promotions (e.g. `runtime-contract`). Nullable. See § 11.4.       |
| `wave_number`      | derived                             | no       | If the thread has prior entries in `tree_prs`, computed as the next integer. Else 1.     |

Prompt strategy: one `AskUserQuestion` call collects `leaves` (multi-select from candidate list) + `base_branch` (free-text with `default_base` as the preview value) + `target_remote` (only if multi-remote). `branch_suffix` and `wave_number` are asked only if the common-case defaults don't apply.

## Flags

| Flag                     | Description                                                                        |
|--------------------------|------------------------------------------------------------------------------------|
| `--allow-secrets`        | Skip the secret-file precondition (expert mode). Emit a warning if used. Use with care when promoting files known to be non-sensitive but matching secret patterns. |
| `--dry-run`              | Print the plan (leaves, target tree domains, three planned commits on the promote branch, the branch name that would be created, the rendered PR body, and the bookkeeping commit on main) without performing any file writes, git mutations, branch creation, pushes, PR opens, or audit-log writes. See Process § Dry-run semantics. |
| `--skip-readiness-check` | Skip the Step 0 environment heads-up that names any missing git/gh/remote/registry setup before proceeding. Expert mode — the § Preconditions still enforce the same requirements, but without the friendly up-front summary. Use when you've seen the heads-up before and just want the skill to proceed or refuse at the precondition step. |

## Preconditions

The skill **refuses** if any of these are not met.

1. Current working directory resolves to a brain root per § 1 (a `project-brain/` directory containing `CONVENTIONS.md`).
2. No potentially sensitive files are present in the thread directory or its `tree-staging/` area (unless `--allow-secrets` is set). Scans for files matching (case-insensitive glob): `.env`, `.env.*`, `*.key`, `*.pem`, `*.p12`, `*.pfx`, `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`, `secrets.yaml`, `secrets.yml`, `secrets.json`, `credentials.json`, `credentials.yaml`, `*.gpg`, `*.enc`. These files should not be in version control under `project-brain/threads/` — see CONVENTIONS § 1 (threads are tracked in git). If any match, refuse with a list and suggest adding to `.gitignore` or removing before promoting. Cross-reference README noting that threads are version-controlled.
3. `~/.config/project-brain/projects.yaml` has an entry for the thread's `primary_project` with a `remotes` list and resolvable `default_remote` (§ 2).
4. `git` and `gh` are on PATH; `gh auth status` reports authenticated for the target remote's host.
5. Working tree is clean on `main`. No uncommitted changes anywhere in the repository (full `git status --porcelain` with no pathspec). Scoped checks are insufficient because stray staging in unrelated paths can leak into the promote branch. Error message includes the full `git status --porcelain` output for user diagnosis.
6. Source thread exists at `project-brain/threads/[thread_slug]/thread.md` with `status: active`. Threads in `in-review` or `archived` cannot be promoted without cycling first.
7. Each selected leaf has a target `tree_domain` resolvable inside `project-brain/tree/`. If a leaf needs a new sub-tree, the skill creates the directory and a scaffolded `NODE.md` in the same commit.
8. `project-brain/tree/[domain]/[leaf-slug].md` does not already exist. If it does, the skill offers `-2`, `-3` suffixes or points the user at `supersede-leaf` (separate skill, not in this pack yet).
9. No branch named `promote/[thread_slug]` exists locally or on the target remote. If it does, the skill resolves with `-wave_number` suffix and asks the user to confirm.

## Process

Each step is atomic. Failure at any step leaves the repo in a recoverable state — either on `main` with nothing changed, or on the promote branch with a committed staging snapshot the user can inspect.

0. **Environment readiness heads-up (rc4+).** Before running *any* git or gh command, probe the environment non-invasively and — if the user hasn't hit the promote path before — surface a summary of what's about to happen and what's missing. This step exists because rc4's pre-promote skills are git-free; the promote triad is the first time git / gh / a remote actually need to work, and users deserve a warning before the permission prompts start.

    Checks to run (each is a single read — no mutation):
    - `git rev-parse --is-inside-work-tree` → is this a git repo?
    - `git config user.name` / `git config user.email` → set?
    - `git remote -v` → at least one remote?
    - `gh --version` → installed on PATH?
    - `gh auth status` → authenticated for the target remote's host?
    - `~/.config/project-brain/projects.yaml` → has an entry for the thread's `primary_project` with `remotes` listed?

    If **all** checks pass, skip straight to step 1 — no prompt, the user already has a working setup. Otherwise, print a single heads-up block naming each missing piece AND the exact command the user should run to fix it, and ask for confirmation before continuing. Example:

    ```
    Heads-up: promoting to a shared tree needs git + gh set up. Here's what I found:

      ✓ this directory is a git repo
      ✓ gh CLI is installed
      ✗ git user.email is not set   →  git config --global user.email you@example.com
      ✗ gh is not authenticated     →  gh auth login
      ✗ no remote configured        →  git remote add origin git@github.com:you/repo.git
      ✗ project-brain registry has no `remotes:` entry for 'my-app'
                                    →  edit ~/.config/project-brain/projects.yaml and
                                       add a `remotes:` list with at least one entry
                                       under the `my-app:` key (see CONVENTIONS § 2.2)

    These are one-time setup steps. After you run them, re-invoke promote-thread-to-tree
    and I'll proceed. No files have been written yet; you can safely stop here.

    Set everything up now? [yes — I'll pause while you run the commands / no — cancel and re-invoke later]
    ```

    Refuse to proceed if any check is failing, even if the user says "yes" — the follow-on steps need git/gh/remote to be operational. The heads-up is diagnostic, not self-healing: the skill does NOT run any of the suggested fix commands itself. Users run setup themselves; the skill only resumes after a clean re-invocation.

    Skip this step entirely with `--skip-readiness-check` (expert mode — the preconditions in § 2 will still enforce the same requirements but without the friendly summary).

1. **Resolve inputs.** Infer `thread_slug` from cwd if possible. Read `decisions-candidates.md`, present `locking` entries to the user via `AskUserQuestion` for leaf selection. Read `~/.config/project-brain/projects.yaml` and resolve `target_remote`. Prompt for `base_branch` with the resolved remote's `default_base` as the preview value.
2. **Validate preconditions.** Run checks 1–9 above. On any failure, stop and report the specific precondition.
3. **Stage leaves (commit 1 of 3).** For each selected leaf:
   - Copy `assets/leaf-template.md` into `project-brain/threads/[thread_slug]/tree-staging/[domain]/[leaf-slug].md`.
   - Fill frontmatter: `node_type: leaf`, `domain: [domain]`, `source_thread: [thread_slug]`, `status: draft`, `created_at` from `date -u`, `owner` from `git config user.email`, `primary_project` inherited.
   - Extract body content from the corresponding entry in `decisions-candidates.md` (§ Context / § Decision / § Consequences / § Alternatives sections). Leave any section the thread did not populate as the template placeholder — the review cycle fills the gaps.
   - Stage and commit: `git checkout -b promote/[thread_slug][-wave-suffix]` from `[target_remote]/[base_branch]`, then `git add project-brain/threads/[thread_slug]/tree-staging/ && git commit -m "promote([thread_slug]): stage [N] leaves for [domain]"`.
4. **Run `verify-tree --staging`** (if installed). This catches obvious frontmatter issues before the files move into the tree proper. If the validator fails, stop — user must fix in `tree-staging/` and re-invoke.
5. **Land leaves into the tree (commit 2 of 3).** Move each staged file from `project-brain/threads/[thread_slug]/tree-staging/[domain]/[leaf-slug].md` to `project-brain/tree/[domain]/[leaf-slug].md`. For each landed leaf:
   - Keep `status: draft` in its frontmatter. Do not flip to `in-review` yet — the PR URL isn't known, so `tree_prs` on the thread is still empty, and § 4.2 forbids `in-review` without a populated `tree_prs`.
   - Append the leaf to the parent `NODE.md`'s `## Leaves` section. Create `NODE.md` from `assets/NODE-template.md` if it doesn't exist.
   - If a new sub-tree was created, insert it into the grandparent `NODE.md`'s `## Sub-nodes` section as well.
6. **Sync thread maturity on the promote branch.** In `project-brain/threads/[thread_slug]/thread.md`, flip `maturity: refining → locking` (if not already). Leave `status: active` — it flips to `in-review` only after PR URL is known.
7. **Commit landing.** `git add project-brain/tree/ project-brain/threads/[thread_slug]/ && git commit -m "promote([thread_slug]): land [N] leaves into [domain]"`. Use `assets/commit-templates/promote.txt` as the template.
8. **Push branch.** `git push -u [target_remote] promote/[thread_slug][-wave-suffix]`.
9. **Open PR.** `gh pr create --base [base_branch] --head promote/[thread_slug][-wave-suffix] --repo [origin-from-remote-url] --title "promote: [Thread Title] → [domain]" --body-file [rendered-from-assets/pr-body-templates/promote.md]`. Render the template with leaf list, source thread link, and debate-readiness notes.
10. **Parse PR URL.** Capture the URL printed by `gh pr create` (or query `gh pr view --json url`).
11. **Flip-to-in-review (commit 3 of 3 on promote branch).** In a single commit on the promote branch:
    - For each landed leaf, flip `status: draft → in-review`.
    - In `project-brain/threads/[thread_slug]/thread.md`, flip `status: active → in-review` and append the PR URL to `tree_prs`.

    Commit: `promote([thread_slug]): open review (PR [url])`. Push. This is the first commit on which § 4.2's `in-review` invariant is satisfied — leaves and thread are synchronized before verify-tree could ever see an inconsistent state on this branch.
12. **Sync main (bookkeeping commit).** `git checkout main`. In `project-brain/threads/[thread_slug]/thread.md`, flip `status: active → in-review` and `maturity: refining → locking`, append the PR URL to `tree_prs`. Stage the thread directory: `git add project-brain/threads/[slug]/`. Then invoke `verify-tree --rebuild-index` to regenerate `project-brain/thread-index.md` and `project-brain/current-state.md`.
    - If the rebuild returns exit 0: stage both index files and commit: `git add project-brain/ && git commit -m "chore([thread_slug]): link promote PR [url]"`. Push `main`. Main now mirrors the thread's PR-open state even though the leaves themselves don't reach main until merge.
    - If the rebuild returns exit 1 or 2: abort and report the error; the thread frontmatter is in an inconsistent state and requires manual repair.
13. **Report.** Return the PR URL, all three promote-branch commit SHAs, the bookkeeping commit SHA on main, and a suggestion to begin review.

### Dry-run semantics

When `--dry-run` is set:

1. **Run all preconditions** (checks 1–9 above), including the secret-pattern scan, full-repo cleanliness check, `gh` auth status, projects.yaml resolution, thread-status validation, target-domain resolvability, leaf-name collision checks, and branch-name collision checks (local + remote). Exit 1 if any precondition fails.
2. **Compute the full plan:** the promote branch name (with any `-N` wave or topic suffix), the three commits that would be made on the promote branch (stage / land / flip-to-in-review) including each commit's message and the files each would touch, the bookkeeping commit that would land on main, and the rendered PR body (from `assets/pr-body-templates/promote.md`).
3. **Write NOTHING to disk:** no `tree-staging/` population, no tree leaves created, no `NODE.md` edits, no thread.md or index file edits, no audit-log writes, no temp files.
4. **Invoke NO git mutations:** no `git checkout -b`, no `git commit`, no `git push`, no `gh pr create`. Read-only git operations (`git status`, `git rev-parse`, `git remote get-url`, `git ls-remote` for the branch-name collision precondition, `gh auth status`) are allowed.
5. **Invoke `verify-tree --rebuild-index --dry-run`** to surface any index-rebuild failures before committing (step 12). If that fails, print the rebuild error and exit 1.
6. **Carve-out on PR preview.** Because `gh pr create` has no dry-run mode of its own, the plan output includes the rendered PR body and the exact `gh pr create` command line that would run — but the skill does not contact GitHub. The actual PR is only opened on a non-dry-run invocation.
7. **Exit 0** if the plan would succeed end-to-end, **exit 1** if any precondition or rebuild-dry-run check failed, **exit 2** on unexpected error.

Print the plan to stdout as a numbered list of steps in the same order as `## Process`. Under future audit-log wiring (per `AUDIT-LOG.md`), a record with `"dry_run": true` is appended; the v0.9.0-alpha.4 stub is spec-only, so no audit write happens either way.

## Side effects

### Files written or modified

| Path (relative to brain root)              | Operation | Notes                                                                 |
|--------------------------------------------|-----------|------------------------------------------------------------------------|
| `threads/[slug]/tree-staging/[domain]/[leaf].md` | create | From `assets/leaf-template.md`, filled from `decisions-candidates.md`. |
| `tree/[domain]/[leaf].md`                  | create    | Moved from staging at step 5.                                          |
| `tree/[domain]/NODE.md`                    | edit or create | `## Leaves` section gets the new entry.                          |
| `tree/[parent-domain]/NODE.md`             | edit      | `## Sub-nodes` if a new sub-tree was created.                          |
| `threads/[slug]/thread.md`                 | edit      | `maturity` flipped on promote branch; `status` + `tree_prs` on main.   |
| `thread-index.md`                          | edit      | Row updated to `in-review` with PR URL cell.                           |
| `current-state.md`                         | edit      | Entry moves from "Active threads" to "Threads in review".              |

Paths are relative to the brain root (`project-brain/`). Shell commands in § Process retain the `project-brain/` prefix because they run from project root.

### Git operations

| Operation                              | Trigger | Notes                                                                             |
|----------------------------------------|---------|-----------------------------------------------------------------------------------|
| `git checkout -b promote/[slug][-N]`   | step 3  | Base is `[target_remote]/[base_branch]`, not hard-coded `origin/main` (§ 11.4).   |
| `git commit` (staging)                 | step 3  | `promote([slug]): stage N leaves for [domain]`                                    |
| `git commit` (landing)                 | step 7  | `promote([slug]): land N leaves into [domain]` — see `assets/commit-templates/promote.txt` |
| `git push -u [remote] promote/[slug][-N]` | step 8 | Sets upstream for the promote branch.                                             |
| `gh pr create`                         | step 9  | Body rendered from `assets/pr-body-templates/promote.md`.                         |
| `git commit` (flip-to-in-review)       | step 11 | `promote([slug]): open review (PR [url])` — synchronizes leaf + thread status.   |
| `git push` (promote branch)            | step 11 | Pushes the flip commit so the PR diff reflects the final state.                   |
| `git checkout main` + commit + push    | step 12 | Bookkeeping commit that syncs thread frontmatter and indexes on main.             |

### External calls

- **`gh`** — PR creation and URL retrieval. Handling when unavailable: refuse at precondition 3. Suggest the user authenticate via `gh auth login` or install the GitHub CLI.

## Outputs

**User-facing summary.** A short message with:

- The PR URL (as a clickable link).
- The three promote-branch commit SHAs (stage, land, flip-to-in-review).
- The main-branch bookkeeping commit SHA.
- A next-step suggestion: "Invite reviewers on the PR; once merged, run `finalize-promotion` to advance leaves from `in-review` to `decided` and update `promoted_to`."

**State passed forward.**

- `pr_url` — URL of the promotion PR.
- `promote_branch` — branch name (`promote/[slug][-N]`).
- `landed_leaves` — list of tree paths for the leaves now in `tree/[domain]/`.
- `wave_number` — 1 for first promotion, N for subsequent cycles.

## Frontmatter flips

| File                                                    | Field           | Before       | After                               |
|---------------------------------------------------------|-----------------|--------------|-------------------------------------|
| `threads/[slug]/thread.md` (promote branch, step 6)     | `maturity`      | `refining`   | `locking`                           |
| `tree/[domain]/[leaf].md` (promote branch, step 5)      | `status`        | *(new file)* | `draft`                             |
| `tree/[domain]/[leaf].md` (promote branch, step 5)      | `domain`        | *(new file)* | `[domain]`                          |
| `tree/[domain]/[leaf].md` (promote branch, step 5)      | `source_thread` | *(new file)* | `[thread_slug]`                     |
| `tree/[domain]/[leaf].md` (promote branch, step 11)     | `status`        | `draft`      | `in-review`                         |
| `threads/[slug]/thread.md` (promote branch, step 11)    | `status`        | `active`     | `in-review`                         |
| `threads/[slug]/thread.md` (promote branch, step 11)    | `tree_prs`      | `[…]`        | `[…, <new PR URL>]`                 |
| `threads/[slug]/thread.md` (main, step 12)              | `status`        | `active`     | `in-review`                         |
| `threads/[slug]/thread.md` (main, step 12)              | `maturity`      | `refining`   | `locking`                           |
| `threads/[slug]/thread.md` (main, step 12)              | `tree_prs`      | `[…]`        | `[…, <new PR URL>]`                 |

The promote branch and main are kept in sync on the thread frontmatter by step 12's mirror commit. The leaves' `draft → in-review` flip lives on the promote branch only — main never sees `in-review` leaves (they only reach main as `decided` via `finalize-promotion` on merge).

## Postconditions

- A promote branch exists on the target remote with three commits (stage, land, flip-to-in-review).
- An open PR references all three commits, with body rendered from the promote template.
- On the promote branch: `project-brain/tree/[domain]/` contains one new leaf file per promoted decision, each in `status: in-review`, each listed in the domain's `NODE.md`. Thread is `status: in-review, maturity: locking` with the PR URL in `tree_prs`.
- On main: thread is `status: in-review, maturity: locking` with the PR URL in `tree_prs`. The tree itself is unchanged on main until the PR merges.
- `thread-index.md` and `current-state.md` on main reflect the in-review state (autogenerated by step 12).
- `verify-tree` passes on both branches — on main (no leaves yet, thread consistent) and on the promote branch (leaves in-review with thread's tree_prs populated).

### Verbosity contract

Reads `verbosity` from `<brain>/config.yaml` (env override: `PROJECT_BRAIN_VERBOSITY`). Defaults to `terse`.

- **terse** (default): one acknowledgement line naming the action + target, then `Done.` No tool-output echo, no "let me..." preamble.
  - Example output: `Promoting thread alpha to tree-staging and opening PR. Done.`
- **normal**: structured summary of what changed (file paths, artifact counts), no conversational framing.
- **verbose**: full narration (pre-rc4 default). Use for debugging.

## Failure modes

| Failure                                      | Cause                                                               | Response                                                 |
|----------------------------------------------|---------------------------------------------------------------------|----------------------------------------------------------|
| Sensitive file(s) detected                    | Pattern match against secret-file glob list in thread or tree-staging | refuse — list offending files; suggest `.gitignore` or removal; hint at `--allow-secrets` for known non-sensitive files |
| Dirty working tree (full repo)                | Uncommitted changes anywhere in the repo (not just `project-brain/`)    | refuse — show full `git status --porcelain` output; ask user to stash or commit |
| No `locking` candidates                       | Thread hasn't matured enough                                        | refuse — suggest `multi-agent-debate` or more refinement |
| Leaf slug collision in tree                   | `tree/[domain]/[leaf].md` already exists                            | prompt — offer `-2`/`-3` or direct to `supersede-leaf`    |
| Branch name collision                         | `promote/[slug]` exists locally or on remote                        | prompt — offer wave-suffix or direct to a cleanup flow   |
| `gh` not authenticated                        | `gh auth status` fails                                              | refuse — link to `gh auth login`                         |
| `gh pr create` fails mid-flow                 | Network issue, permission problem                                   | refuse — leave promote branch in place for retry         |
| `verify-tree --staging` fails                 | Malformed frontmatter in staged leaves                              | refuse — user fixes in `tree-staging/` and re-invokes    |
| Base branch doesn't exist on remote           | Typo'd or stale `default_base`                                      | prompt — re-ask for base branch                          |
| Multi-remote ambiguity with no `default_remote` | `remotes` has >1 entry and `default_remote` not set               | refuse — direct user to fix `projects.yaml`              |
| Rebuild source-validation failure (step 12) | Thread frontmatter schema violations on main                       | refuse — report violating thread; user must repair before retrying  |
| Rebuild write failure (step 12)              | Filesystem / permissions issue on main                            | refuse — live index files unchanged (atomic); report error         |

## Related skills

- **Follows:** `new-thread` — produces the thread this skill promotes.
- **Follows:** `multi-agent-debate` *(optional)* — harder thread candidates run through debate before promotion.
- **Precedes:** `finalize-promotion` *(separate skill, not yet drafted)* — runs on PR merge to flip leaves `in-review → decided`, populate `promoted_to`/`promoted_at`, and return thread to `active` or `archived`.
- **Precedes:** `derive-impl-spec` — eventually consumes the landed leaves to produce impl specs.
- **Compatible with:** `verify-tree` — invoked at step 4 and expected to pass on main post-step 11.

## Asset dependencies

- `assets/leaf-template.md` — base template for each staged leaf (step 3).
- `assets/NODE-template.md` — scaffold when a new sub-tree's `NODE.md` must be created (step 5).
- `assets/pr-body-templates/promote.md` — PR body (step 9).
- `assets/commit-templates/promote.txt` — commit message template (step 7).

## Versioning

**0.3.2** — Added `--dry-run` flag specification with contract carve-out for `gh pr create --dry-run` (not supported).

**0.3.0** — Stage 2 of v0.9.0: bookkeeping commit (step 12) index-file updates moved to centralized `verify-tree --rebuild-index` call; previous inline edits removed.

**0.2.0** — Stage 1 (prior stream): safety hardening for leaf status validation on merge commit.

**0.1.0** — initial draft. Major bump if the three-commit (stage, land, flip-to-in-review) shape changes, if the promote-branch base-selection rule changes (§ 11.4), or if any frontmatter flip is added/removed.
