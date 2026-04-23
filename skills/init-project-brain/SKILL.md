---
name: init-project-brain
description: One-time scaffold of the project-brain skeleton into the host environment's project directory. Default invocation runs with **zero interactive questions in the common case** — the skill detects the host project root (Cowork workspace folder, Codex project root, Claude Code cwd, or the nearest git repo root) and scaffolds `project-brain/` inside it. A confirmation is printed showing which source the root came from. The skill only prompts if detection falls all the way through to raw cwd with no git signal, OR if an existing brain is already scaffolded at the target (overwrite vs cancel). Alias and title are derived from the detected home's last-path-component. Owner is written as the literal placeholder `TODO@example.com` with a TODO marker in CONVENTIONS.md § 10 — the user replaces it on their first commit, or leaves it until promote-time. If an existing `project-brain/` is already scaffolded, the skill prompts "overwrite (backup and replace) or cancel?" — it never silently clobbers. Creates project-brain/ with CONVENTIONS.md, config.yaml, tree/NODE.md, empty threads/ and archive/, plus a .gitignore for transcripts and attachments. Optional --home=<path> skips detection. Optional --force skips the overwrite prompt. Optional --interactive prompts for all values (owner, domains, etc.). Optional --owner <email> sets owner explicitly without the TODO marker. Optional --init-git runs git init + scaffold commit (opts into git-based preconditions). Optional --no-registry skips appending an alias entry to ~/.config/project-brain/projects.yaml. Use when the user says "set up project brain", "install project-brain here", or adopts this pack in a new directory first time.
version: 1.0.0-rc4
pack: project-brain
requires:
  - "read:pack/CONVENTIONS.md"
  - "write:[project-root]"
  - "write:~/.config/project-brain/projects.yaml"
# Note: `git` was listed as a hard requirement pre-rc4. rc4 makes it optional —
# git is only invoked when --init-git is passed. The default flow is a plain
# `mkdir` + file-write, no git at all.
---

# init-project-brain

Turns any directory into a project-brain-enabled one. Before this skill runs, there is no place for threads to live and no tree structure for decisions to land in; after it runs, every other skill in the pack has its preconditions met. This is the first skill a user invokes when adopting the pack in a new project.

**Host-project detection (rc4):** the skill commits to a 1:1 correspondence between a project-brain project and the host environment's project concept — Cowork workspace folder, Codex project root, Claude Code cwd, or the nearest git repo root (see CONVENTIONS § 1). It calls `scripts/verify_tree/config.py::detect_host_project_root()` (pure Python — env-var probes + file-existence walk, zero shell invocation) and uses the detected path as the project home.

The detection chain, highest priority first:

1. `PROJECT_BRAIN_HOME` env override — for scripts / CI.
2. `COWORK_WORKSPACE_FOLDER` — Cowork sets this at session start.
3. `CODEX_PROJECT_ROOT` — Codex equivalent.
4. `CLAUDE_PROJECT_ROOT` — Claude Code equivalent.
5. Nearest ancestor of cwd containing `.git/` — almost all real projects hit this.
6. Raw cwd — last-resort fallback (bare directory, no git).

**Default flow: zero prompts** if detection returns any source 1–5. The skill prints a single confirmation line (`Project home: /path (detected: cowork-workspace)`) and proceeds. Users who want a different location pass `--home=<path>` to override. Users can see which source was chosen in the output to confirm it matches their expectation.

**Fallback flow: one prompt** if detection lands on source 6 (raw cwd with no git). The ambiguity is real — the agent has no idea where the project should live — so one AskUserQuestion surfaces with cwd as the default and the user can accept or type an alternative.

**Existing-brain detection:** if a `project-brain/` directory already exists at the chosen location and contains a `CONVENTIONS.md`, the skill stops and asks: **"A brain already exists at `<path>`. Overwrite (rename existing to `project-brain.bak.<timestamp>/` and scaffold fresh), or cancel?"** Default is cancel. The skill never silently clobbers existing work; the backup-rename is recoverable so mistakes cost nothing.

**Git is optional (rc4).** The default flow is a plain directory scaffold — no `git init`, no commit, no repo required. Pass `--init-git` if you want init to run `git init` and commit the scaffold. Users who already have a git repo and just want the brain scaffolded without an auto-commit run the skill without any flag; they can `git add && git commit` themselves when ready.

The skill is deliberately opinionated at a few points: it pre-scaffolds top-level domain directories from § 10.1, it always copies a fresh `CONVENTIONS.md` (so the project starts on the pack's current version, not a stale one), and it writes a single bootstrap commit so the entire scaffold lands as one reviewable unit. Sub-domains and the leaves inside them emerge later via `promote-thread-to-tree`.

## When to invoke

- "Set up project brain" / "install project-brain here" / "init the brain"
- First-time adoption of the pack in a repository
- After a team votes to standardize on this pack and needs the baseline scaffolded
- **Do not use** to repair or migrate an existing brain — that's a separate skill (not yet drafted: `repair-brain` / `migrate-brain`).

## Inputs

| Name                | Source                          | Required | Description                                                                               |
|---------------------|---------------------------------|----------|-------------------------------------------------------------------------------------------|
| `project_alias`     | user prompt                     | yes      | Kebab-case key for `~/.config/project-brain/projects.yaml` (§ 11.1). Must not already exist in the registry. |
| `project_title`     | user prompt                     | yes      | Human-readable name used in `thread-index.md` and `current-state.md` headers.             |
| `project_home`      | **detected** via `detect_host_project_root()` (see preamble); falls through to one AskUserQuestion only when detection returns the raw-cwd source | yes | Absolute path to the directory the brain will live **inside** (i.e., parent of `project-brain/`). Detection chain consults env vars (`PROJECT_BRAIN_HOME`, `COWORK_WORKSPACE_FOLDER`, `CODEX_PROJECT_ROOT`, `CLAUDE_PROJECT_ROOT`), then walks for `.git/`, then cwd. Override with `--home=<path>`. |
| `brain_path`        | derived from `project_home`     | yes      | Computed as `<project_home>/project-brain`. |
| `remotes`           | **`--init-git` only** — `git remote -v` + user prompt | conditional | List of remotes the brain repo may push to. Only collected when `--init-git` is passed. In the default flow the registry entry (if written at all) omits the `remotes:` block and promote-time fills it in. |
| `default_remote`    | **`--init-git` only** — user prompt | conditional | Required when `remotes` has >1 entry; defaults to the sole entry otherwise. Default flow skips. |
| `default_base_per_remote` | **`--init-git` only** — user prompt | conditional | Per-remote default base branch (usually `main` or `master`). Default flow skips.   |
| `domain_taxonomy`   | user prompt                     | yes      | § 10.1 top-level domains as a line-separated list (e.g. `engineering / product / operations`). 1–8 entries. |
| `debate_personas`   | user prompt                     | no       | § 10.2 reviewer personas. Default empty — easy to add later by hand-editing `CONVENTIONS.md`. |
| `build_toolchain`   | user prompt                     | no       | § 10.3 test/lint/build commands. Default empty.                                           |
| `owner`             | `--owner <email>` flag, else the literal placeholder `TODO@example.com` (with a visible TODO marker in CONVENTIONS § 10). If `--init-git` is set, `$EMAIL` and `git config user.email` are also consulted as intermediate fallbacks. **No shell invocation in the default flow.** | yes      | Who ran init; recorded as thread owner, registry entry, etc.                              |

**Zero-Q&A defaults (new in v1.0.0-rc4):**
- `project_home`: **detected**, not asked. Resolution chain: `--home=<path>` flag > `PROJECT_BRAIN_HOME` env > `COWORK_WORKSPACE_FOLDER` > `CODEX_PROJECT_ROOT` > `CLAUDE_PROJECT_ROOT` > nearest `.git/` ancestor > raw cwd. The skill calls `scripts/verify_tree/config.py::detect_host_project_root()` which is pure Python (env reads + file-existence walk, no shell). The *only* case that triggers an interactive prompt is the raw-cwd fallback (source = `cwd`) — everywhere else the skill prints a confirmation line and proceeds.
- `project_alias`: kebab-case slug of the chosen `project_home`'s last-path-component (e.g., `/Users/alice/workspace/My App` → `my-app`). **Derive this from the chosen-path string in memory — do NOT run `basename`, `pwd`, or any shell command to discover it.** Validated per § 11.1.
- `project_title`: title-cased form of the same last-path-component (e.g., `my-app` → `My App`). Same no-shell rule.
- `owner` (default flow): the **literal placeholder string `TODO@example.com`**. A visible TODO marker is prepended to CONVENTIONS.md § 10 naming what needs to change (see Process step 4). **The default flow does NOT invoke `git`, does NOT read `$EMAIL`, does NOT read `$USER`, does NOT run any shell command to guess who the user is.** The user fixes the placeholder when they feel like it — at first commit, or at first promote (where a real identity is needed anyway and the promote-time heads-up will remind them). Rationale: even reading env vars requires a `bash` invocation in agentic IDEs, which triggers a permission prompt. The user's mental model for install is "setup → Done, no questions, no prompts." We honor that by not trying to be smart about identity.
- `owner` (with `--owner <email>`): use the supplied email verbatim. No TODO marker in § 10.
- `owner` (with `--init-git`): `$EMAIL` → `git config user.email` → `TODO@example.com` TODO fallback. Env var and git consultation are OK here because `--init-git` is already invoking the shell and git for `init` + `commit`.
- `domain_taxonomy`: `engineering`. A single default domain. User adds more by hand-editing CONVENTIONS.md § 10.1 or re-runs with `--interactive`.

**Prompt strategy:** Default invocation asks zero interactive questions AND runs zero shell commands. With `--interactive` flag, one call collects `project_alias` + `project_title` + `owner` + `domain_taxonomy`. Remote/base confirmation and persona/toolchain setup happen only with `--interactive`.

## Preconditions

The skill **refuses** if any of these are not met. Preconditions 1, 3, 6 apply **only when `--init-git` is set** — rc4 makes git entirely optional and the default install creates a plain directory with no git involvement.

1. (Only if `--init-git`) Current working directory is inside a git repository (`git rev-parse --is-inside-work-tree` returns `true`). Without `--init-git` the skill does not care — the brain is just a directory full of markdown.
2. The target `brain_path` does not already contain a brain (`<brain_path>/CONVENTIONS.md` doesn't exist). **Handling:**
    - If `brain_path` does not exist at all: proceed silently.
    - If `brain_path` exists but is empty or has no `CONVENTIONS.md`: proceed silently (treating as a partial / abandoned scaffold).
    - If `brain_path/CONVENTIONS.md` exists: prompt via AskUserQuestion: `"A project-brain already exists at <brain_path>. Overwrite (rename existing to project-brain.bak.<YYYYMMDD-HHMMSS>/ and scaffold fresh) or cancel?"` — default is **cancel**. If the user picks overwrite, rename the existing directory to `<brain_path>.bak.<timestamp>` (with seconds precision to avoid collisions on rapid re-invocation) and continue. If the user picks cancel, exit cleanly with a one-line report (`Brain already exists at <path>; no changes made.`). Skip this prompt if `--force` is set (auto-overwrite) or abort immediately if neither flag is set and the prompt can't be shown.
3. (Only if `--init-git`) Working tree is clean on `main` (or the project's default branch). Init's `--init-git` commits directly to that branch; uncommitted changes would be swept into the bootstrap commit.
4. The `owner` field is seeded from the `--owner <email>` flag if given. Otherwise it's written as the literal placeholder `TODO@example.com` and a visible TODO marker is prepended to CONVENTIONS.md § 10 (see Process step 4). **The default flow does NOT invoke any shell command to guess the user's identity** — no `git config`, no `echo $EMAIL`, no `whoami`. Every shell invocation in agentic IDEs triggers a permission prompt, and the user's mental model for init is "setup → Done, no questions." Only when `--init-git` is set does the skill optionally consult `$EMAIL` then `git config user.email` as fallbacks — that path is already invoking the shell and git for `init` + `commit`, so one more read is no additional friction. This precondition is always best-effort — it never refuses.
5. `~/.config/project-brain/projects.yaml`, if it exists, does **not** already contain `project_alias`. If it does, prompt — suggest a suffixed alias (`<alias>-2`) or ask the user to pick a different one. (Skipped entirely if `--no-registry` is set.)
6. (Only if `--init-git` AND the user wants a registry entry with remote info) `git remote -v` returns at least one remote, OR the user explicitly confirms offline-only scaffolding. Without `--init-git`, the registry entry omits the `remotes:` block regardless.
7. Each entry in `domain_taxonomy` matches the slug rules of § 11.1 (kebab-case, no sub-paths — sub-nesting emerges through promotion, not init).

## Process

Each step is atomic. A failure at step N leaves the filesystem in whatever state it was after step N-1; no partial scaffolds are left committed.

1. **Resolve inputs.**
    - **Step 1a — detect project home (zero prompts in the common case).** Call `detect_host_project_root()` from `scripts/verify_tree/config.py`. It returns `(path, source)` where `source` is one of: `env:PROJECT_BRAIN_HOME`, `cowork-workspace`, `codex-project`, `claude-project`, `git-root`, `cwd`. Decision tree:
        - If `--home=<path>` flag is supplied: use it verbatim. No prompt. `source = "flag:--home"`.
        - Else call `detect_host_project_root()`:
            - If `source ∈ {env:PROJECT_BRAIN_HOME, cowork-workspace, codex-project, claude-project, git-root}` — **proceed silently**. Do not prompt. Emit a single confirmation line in the terse report: `Project home: <path> (detected: <source>)`.
            - If `source == "cwd"` — detection fell all the way through. The ambiguity is real. Present one AskUserQuestion: `"No host project root detected. Project home directory?"` with `<cwd>` as the default. User accepts default or types an alternative absolute path.
        - With `--interactive`: fold this into the full prompt set; still show the detected value as the default.
    - From the resolved `project_home`, compute `brain_path = <project_home>/project-brain`. This is pure string manipulation — no shell call.
    - **Step 1b — derive from `project_home` (no shell):** `brain_path = <project_home>/project-brain`. `project_alias` = kebab-case slug of the last path component of `project_home`. `project_title` = title-cased form of that same component. `domain_taxonomy` = `[engineering]` unless `--interactive`. Every derivation is pure string manipulation on `project_home` — **do NOT run `basename`, `pwd`, or any shell command.**
    - **Step 1c — resolve `owner`:**
        - If `--owner <email>` flag is set: use it verbatim. No TODO marker.
        - Else (default flow): use the **literal placeholder `TODO@example.com`** and set a flag to emit the TODO marker in step 4. **Do NOT run any shell command to discover a better default** — no `git config`, no `echo $EMAIL`, no `whoami`. Every shell call prompts the user for permission in agentic IDEs, and the whole point of rc4's default flow is that install is silent after the one home-dir question.
        - Exception: if `--init-git` is set, the shell is already being invoked downstream for `git init` + `commit`, so it's consistent to additionally consult `$EMAIL` then `git config user.email` as fallbacks between `--owner` and the TODO placeholder.
2. **Validate preconditions.** Run only the preconditions that apply to the current invocation:
    - ALWAYS check: #2 (existing-brain detection — see next step for the overwrite/cancel flow), #4 (owner-source best-effort — in the default flow this is just "did the user pass `--owner <email>`?" with no shell-side fallback; never refuses), #5 (registry alias collision, skip if `--no-registry`), #7 (domain_taxonomy slug rules).
    - ONLY if `--init-git` is set: also check #1 (inside a git repo), #3 (working tree clean), #6 (remotes, if the user wants them in the registry entry).
    - **Do NOT run `git rev-parse --is-inside-work-tree` unless `--init-git` is set.** The default flow is pure file ops — probing for a git repo is out of scope and triggers noisy permission prompts in agentic IDEs for no reason.
    - On failure (other than the existing-brain case, handled in step 2.5), stop and report the specific precondition. Do not offer to `git init` unless the user passed `--init-git`; without that flag, git is irrelevant.
2.5. **Existing-brain check + overwrite prompt.** Read-only file test on `<brain_path>/CONVENTIONS.md`:
    - If absent: `<brain_path>` has no brain. Proceed to step 3.
    - If present: a brain is already scaffolded here. Behavior depends on flags:
        - `--force` was passed: rename `<brain_path>` → `<brain_path>.bak.<YYYYMMDD-HHMMSS>` using the file tool (no shell invocation — the agent's file-move primitive), then proceed.
        - No flag: present an AskUserQuestion: `"A project-brain is already scaffolded at <brain_path>. Options:"` with choices `overwrite` (rename existing to .bak.<timestamp>/ and scaffold fresh) and `cancel` (exit cleanly, no changes). Default = cancel. If user picks overwrite → rename then proceed. If cancel → exit with one-line report: `Brain already exists at <brain_path>; no changes made. Pass --force to overwrite non-interactively.`
    - The existing-brain backup is always recoverable: users can `rm -rf` the `.bak.<timestamp>` directory themselves if they want to free the space, or restore it by reversing the rename. The skill never deletes.
3. **Create brain directory.** Use file-tool `mkdir`-equivalent to create `<brain_path>/tree`, `<brain_path>/threads`, `<brain_path>/archive`. No shell `mkdir -p`.
4. **Write `CONVENTIONS.md`.** Read the pack's canonical `CONVENTIONS.md` (the one this pack ships). Splice § 10 subsections with the user's answers:
    - § 10.1 Tree domain taxonomy — replaced with the `domain_taxonomy` list as a fenced-block outline.
    - § 10.2 Debate personas — replaced with `debate_personas` if provided; otherwise keep the placeholder with a "— TBD; add personas before invoking `multi-agent-debate`" comment.
    - § 10.3 Build toolchain — replaced with `build_toolchain` if provided; otherwise leave as commented placeholders.
    - § 10.4 — untouched unless `role_extensions` was volunteered (rare at init time).
    - **Owner TODO marker (v1.0.0-rc4).** If the resolved `owner` is the `TODO@example.com` placeholder (default flow without `--owner`, or `--init-git` flow where all fallbacks were empty), prepend a visible HTML comment block to § 10 that reads:
      ```
      <!-- TODO(project-brain init): The brain was scaffolded with owner = "TODO@example.com"
           because no email was supplied. When you're ready — typically before your first
           commit, or at latest when you run promote-thread-to-tree — replace every
           `owner: TODO@example.com` reference in this brain with your real email:
             CONVENTIONS.md (this file)
             any thread.md you've created
             ~/.config/project-brain/projects.yaml (if registry was written)
           Then delete this TODO block. The skill intentionally did not try to guess your
           email — doing so requires a shell invocation, which would defeat the "setup →
           Done" mental model rc4 is built around. -->
      ```
      When the owner is a real email (from `--owner <email>` or, under `--init-git`, from `$EMAIL` / `git config user.email`), do NOT emit this block. The marker must be impossible to miss: first thing inside § 10, before § 10.1.
   Write to `<brain_path>/CONVENTIONS.md`. Do not modify the sections above § 10 — those are the pack's shared contract.
5. **Scaffold the root NODE.md.** Copy `assets/NODE-template.md` to `<brain_path>/tree/NODE.md`. Fill placeholders: `{{TITLE}}` = `"<project_title> — Knowledge Tree"`, `{{DOMAIN}}` = `/`, `{{PRIMARY_PROJECT}}` = `project_alias`. Populate the `## Sub-nodes` section with one bullet per entry in `domain_taxonomy`, each linked to the sub-directory's `NODE.md`.
6. **Scaffold per-domain NODE.md.** For each `<domain>` in `domain_taxonomy`:
    - `mkdir -p <brain_path>/tree/<domain>/`
    - Copy `assets/NODE-template.md` to `<brain_path>/tree/<domain>/NODE.md`. Fill placeholders: `{{TITLE}}` = humanized `<domain>`, `{{DOMAIN}}` = `<domain>`, `{{PRIMARY_PROJECT}}` = `project_alias`. Leave `## Leaves` section with the placeholder `*(none yet — use `promote-thread-to-tree` to land the first decision)*`.
7. **Write `thread-index.md`.** Copy `assets/thread-index-template.md` to `<brain_path>/thread-index.md`. Fill `{{PRIMARY_PROJECT}}` and `{{PROJECT_TITLE}}`.
8. **Write `current-state.md`.** Copy `assets/current-state-template.md` to `<brain_path>/current-state.md`. Fill `{{PRIMARY_PROJECT}}` and `{{PROJECT_TITLE}}`.
9. **Place `.gitkeep`** in `<brain_path>/threads/` and `<brain_path>/archive/` so empty directories stay tracked.
10. **Write `config.yaml` (per-project).** Create `<brain_path>/config.yaml` with:
    ```yaml
    primary_project: <project_alias>
    verbosity: terse
    transcript_logging: on
    aliases: {}
    ```
    See CONVENTIONS § 2.1 for the full schema. The `aliases:` block stays empty at init; cross-project references are added by hand later if needed.

11. **Write `.gitignore`.** Create `<brain_path>/.gitignore` with entries for `transcript.md` and `attachments/` directories (per CONVENTIONS § 2.5).

12. **Update `~/.config/project-brain/projects.yaml`** (skip entirely if `--no-registry`). Create the file if it does not exist (with a top-level comment explaining what it is). Append an entry keyed by `<project_alias>`:
    - **Default flow (no `--init-git`)** — write a minimal entry WITHOUT a `remotes:` block:
      ```yaml
      <project_alias>:
        root: <path to repo root>
        brain: <brain_path>
      ```
      Do NOT invoke `git remote -v` or `git remote get-url` to discover remotes — the default flow is git-free and the registry entry can grow a `remotes:` section later (users edit by hand, or re-run with `--init-git`, or fill it in at first promote).
    - **With `--init-git`** — also include `remotes:` + `default_remote:` as collected from `git remote -v`:
      ```yaml
      <project_alias>:
        root: <path to repo root>
        brain: <brain_path>
        remotes:
          - name: <remote-name>
            url: <git remote get-url output>
            default_base: <default_base>
        default_remote: <default_remote>
      ```
    Do not touch other projects' entries in either case.

13. **Conditional git commit.** If `--init-git` is set, run `git add <brain_path>/ <brain_path>/.gitignore && git commit -m "chore(brain): scaffold project-brain for <project_alias>"`. If `--init-git` is NOT set, the skill DOES NOT commit — the user runs `git commit` themselves if (and when) they want to.

14. **Report.** At verbosity=terse (default), emit two lines:

    ```
    Project home: <project_home>  (detected: <source>)
    Initialized project-brain in <project_home>/project-brain/ (alias: <alias>). Done.
    ```

    (If `<source>` is `flag:--home`, phrase as "specified" rather than "detected".)

    If the TODO placeholder was used for owner, append one more line:

    ```
    owner = TODO@example.com (no --owner flag; no shell lookup by design). Fix in CONVENTIONS § 10 before committing.
    ```

    If `--init-git` was NOT set (default), append one more line:

    ```
    Not committed — run `git add . && git commit` yourself when ready.
    ```

    At verbosity=normal or verbose, expand with file list / registry entry / next-step suggestions as before.

## Side effects

### Files written or modified

| Path (relative to repo root)        | Operation | Notes                                                             |
|-------------------------------------|-----------|-------------------------------------------------------------------|
| `project-brain/`                         | create    | Directory; all subsequent paths live under this.                  |
| `project-brain/CONVENTIONS.md`           | create    | Copied from pack, § 10 spliced with user answers. TODO marker prepended if the `TODO@example.com` owner placeholder was used (default flow without `--owner`). |
| `project-brain/config.yaml`              | create    | rc4 per-project config with `primary_project`, default `verbosity: terse`, `transcript_logging: on`, empty `aliases: {}`. |
| `project-brain/.gitignore`               | create    | Defaults for `transcript.md` + `attachments/` per CONVENTIONS § 2.5. |
| `project-brain/tree/NODE.md`             | create    | Root node; `## Sub-nodes` lists every domain.                     |
| `project-brain/tree/<domain>/NODE.md`    | create    | One per entry in `domain_taxonomy`; empty `## Leaves`.            |
| `project-brain/threads/.gitkeep`         | create    | Keeps empty directory in git.                                     |
| `project-brain/archive/.gitkeep`         | create    | Keeps empty directory in git.                                     |
| `project-brain/thread-index.md`          | create    | From `assets/thread-index-template.md`.                           |
| `project-brain/current-state.md`         | create    | From `assets/current-state-template.md`.                          |

### User-global files

| Path                        | Operation        | Notes                                                           |
|-----------------------------|------------------|-----------------------------------------------------------------|
| `~/.config/project-brain/projects.yaml`       | create or append | Top-level mapping; one new entry keyed by `project_alias`. Skipped entirely when `--no-registry` is set. |
| `~/.config/project-brain/` (directory)        | create           | Only if missing; mode 0755. Skipped when `--no-registry` is set. |

### Git operations

**Default flow (no `--init-git`): zero git operations.** Listed below for the `--init-git` flow only.

| Operation                        | Trigger                               | Notes                                                          |
|----------------------------------|---------------------------------------|----------------------------------------------------------------|
| `git init`                       | `--init-git` + not-yet-a-git-repo     | Creates a fresh git repo in the project root.                  |
| `git add project-brain/`         | `--init-git`, Process step 12         | Stages the entire brain scaffold + its `.gitignore`.           |
| `git commit -m …`                | `--init-git`, Process step 12         | Single bootstrap commit on the current branch (usually main).  |
| `git push <remote> <branch>`     | *never automatic* — user runs manually | The skill does not push. Users push themselves when ready.    |

### External calls

Default flow (no `--init-git`): **truly zero external calls.** The skill does `mkdir` + `read/write` of markdown/yaml files via the file tool. No shell invocation of any kind — no `git`, no `gh`, no `basename`, no `pwd`, no `echo $EMAIL`, no `whoami`, no network. The cwd string comes from the agent's invocation context (already known without calling `pwd`); the owner is a literal placeholder. This is what "setup → Done, no questions" means at the tool-call level.

With `--init-git`:

- **`git init`** — only if the directory is not already a git repo. User confirms before running.
- **`echo $EMAIL`** — env-var read, consulted as a fallback owner source between `--owner <email>` and `git config user.email`.
- **`git config user.email`** — read-only, consulted as a fallback owner source between `$EMAIL` and the `TODO@example.com` placeholder.
- **`git add` + `git commit`** — bootstrap commit of the scaffolded brain.
- **`git remote -v`** (optional) — consulted when the registry entry should record remotes.

## Outputs

**User-facing summary.** A short message with:

- The brain path (as a `computer://` link to `project-brain/`).
- The bootstrap commit SHA.
- The list of scaffolded domains, each as a link to its `NODE.md`.
- The `~/.config/project-brain/projects.yaml` path (note that it's user-global, not project-local).
- Push status (pushed / local only).
- A next-step suggestion: "Run `new-thread` to start capturing ideas; run `promote-thread-to-tree` when a thread matures."

**State passed forward.**

- `brain_path` — absolute path to `project-brain/`.
- `bootstrap_commit` — SHA of the scaffolding commit.
- `project_alias` — alias registered in `projects.yaml`.
- `scaffolded_domains` — list of paths like `tree/engineering/NODE.md`.

## Frontmatter flips

This skill only creates files; it does not flip any existing frontmatter. New files are written with their final field values directly — no intermediate states, no subsequent flips within the skill.

## Postconditions

- `<brain_path>/` exists with the directory layout from § 1.
- `<brain_path>/CONVENTIONS.md` is valid — sections 1–9 and 11 match the pack's canonical copy exactly; § 10 is populated from user answers (or explicitly placeholder-marked).
- `<brain_path>/tree/NODE.md` and one `<brain_path>/tree/<domain>/NODE.md` per entry in `domain_taxonomy` exist and have valid frontmatter.
- `<brain_path>/thread-index.md` and `<brain_path>/current-state.md` exist with scaffolded but empty content.
- `~/.config/project-brain/projects.yaml` contains a `project_alias` entry with `brain`, `remotes`, and `default_remote` set.
- A single commit on the current branch contains all brain files.
- All preconditions of `new-thread` and `promote-thread-to-tree` are now satisfied for this project.
- `verify-tree` (if installed) passes on the newly-scaffolded brain.

### Verbosity contract

Reads `verbosity` from `<brain>/config.yaml` (env override: `PROJECT_BRAIN_VERBOSITY`). Defaults to `terse`.

- **terse** (default): one acknowledgement line naming the action + target, then `Done.` No tool-output echo, no "let me..." preamble.
  - Example output: `Initialized project-brain in ./project-brain/ (alias: my-app, owner: alice@example.com).`
- **normal**: structured summary of what changed (file paths, artifact counts), no conversational framing.
- **verbose**: full narration (pre-rc4 default). Use for debugging.

## Failure modes

| Failure                                | Cause                                                        | Response                                      |
|----------------------------------------|--------------------------------------------------------------|-----------------------------------------------|
| Brain already scaffolded at target     | `<brain_path>/CONVENTIONS.md` exists                        | prompt via AskUserQuestion — `overwrite` renames existing to `.bak.<timestamp>/` and proceeds; `cancel` (default) exits cleanly. `--force` skips the prompt and overwrites. `--force` + already-scaffolded always overwrites. |
| Empty `<brain_path>` directory exists  | `<brain_path>/` exists but has no `CONVENTIONS.md`          | proceed silently, treating as an abandoned partial scaffold. Files in the existing dir are overwritten by the fresh scaffold; pre-existing unrelated files are preserved. |
| Alias collision in `projects.yaml`     | `project_alias` already registered                           | prompt — suggest `<alias>-2` or new alias (or pass `--no-registry` to skip the registry step) |
| Invalid domain slug                    | One of `domain_taxonomy` fails § 11.1                        | refuse — name the offending slug and the rule it violated |
| Not in a git repo *(only with `--init-git`)* | `git rev-parse --is-inside-work-tree` returns false    | refuse — ask user to `git init` first, or drop the `--init-git` flag to scaffold a plain directory |
| Dirty working tree *(only with `--init-git`)* | Uncommitted changes on the current branch             | refuse — ask user to stash or commit, or drop `--init-git` |
| No remotes and offline not confirmed *(only with `--init-git`)* | `git remote -v` empty, user did not opt in to offline mode | refuse — ask user to add a remote, confirm offline, or drop `--init-git` |
| Slug validation fails on a domain      | One of `domain_taxonomy` violates § 11.1                     | prompt — re-ask for the offending domain      |
| Pack's `CONVENTIONS.md` not found      | Pack installation broken                                     | refuse — report broken pack                   |
| Write to `~/.config/project-brain/projects.yaml` fails   | Permissions or disk issue                                    | refuse — leave `project-brain/` uncommitted, tell user to fix and re-run |

## Related skills

- **Precedes:** `new-thread` — requires `project-brain/CONVENTIONS.md` and a `projects.yaml` entry, both produced here.
- **Precedes:** `promote-thread-to-tree` — requires the tree scaffold and the `remotes` list from `projects.yaml`.
- **Precedes:** `verify-tree` — the scaffold it produces is the validator's first meaningful input.
- **Compatible with:** `repair-brain` / `migrate-brain` *(not yet drafted)* — what init is not: those handle existing-brain mutations.

## Asset dependencies

- `assets/NODE-template.md` — root + per-domain NODE.md (steps 5, 6).
- `assets/thread-index-template.md` — initial `thread-index.md` (step 7).
- `assets/current-state-template.md` — initial `current-state.md` (step 8).
- `pack/CONVENTIONS.md` — the canonical conventions doc, read at step 4 and spliced with § 10 answers.

## Versioning

**0.1.0** — initial draft. Major bump if the bootstrap-commit shape changes (e.g. split into multiple commits), if pre-scaffolded domain directories become optional, or if the `projects.yaml` schema moves elsewhere.
