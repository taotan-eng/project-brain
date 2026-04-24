# Porting project-brain to a new agent runtime

This document explains what a runtime adapter (Claude Code, Codex, a
custom CLI, or anything else) needs to do to expose project-brain's
skills to its users.

The short version: **nothing about the pack's internals is tied to
Claude Code.** The bash scripts under `scripts/` and the Python
validator under `scripts/verify_tree/` are pure POSIX / stdlib. Every
runtime-specific detail lives in one thin wrapper layer — in this repo,
that's the `.claude-plugin/` manifest plus the `skills/*/SKILL.md`
descriptors. Adding a second adapter means replacing that wrapper
layer, not rewriting anything below it.

## The layer model

```
┌───────────────────────────────────────────────────────────────┐
│  Runtime adapter (Claude Code / Codex / CLI / …)              │
│    • Skill descriptor format (SKILL.md for Claude Code)       │
│    • Plugin manifest (.claude-plugin/plugin.json for CC)      │
│    • How the runtime routes user intent → script invocation   │
│  THIS LAYER IS RUNTIME-SPECIFIC.                              │
└────────────────┬──────────────────────────────────────────────┘
                 │  bash <script> --flag=value
                 ▼
┌───────────────────────────────────────────────────────────────┐
│  Scripts layer (scripts/*.sh)                                 │
│    • Pure POSIX bash                                          │
│    • Self-locates via $0 — no env vars required               │
│    • Reads config.yaml, writes frontmatter, runs validator    │
│  THIS LAYER IS PORTABLE.                                      │
└────────────────┬──────────────────────────────────────────────┘
                 │
                 ▼
┌───────────────────────────────────────────────────────────────┐
│  Data + schema layer (CONVENTIONS.md, assets/, verify_tree/)  │
│    • Markdown templates with `{{PLACEHOLDER}}` substitution   │
│    • Python validator (stdlib only when PyYAML absent)        │
│  THIS LAYER IS PORTABLE.                                      │
└───────────────────────────────────────────────────────────────┘
```

A new adapter writes the top layer only. The bottom two layers stay
identical.

## What an adapter has to provide

### 1. A way to invoke each script with the right flags

Every mutating operation in the pack is a single bash script. Full list,
with their input contracts:

| Script                        | Typical invocation                                               |
|-------------------------------|------------------------------------------------------------------|
| `init-brain.sh`               | zero flags in the common case; auto-detects host project         |
| `new-thread.sh`               | `--brain --slug --title --purpose` (primary-project auto-read)   |
| `record-artifact.sh`          | `--brain --slug --title --content \| --file \| --stdin`          |
| `review-thread.sh`            | `--brain --slug` (read-only)                                     |
| `update-thread.sh`            | `--brain --slug --operation [--target / --url / --merge-into-slug]` |
| `assign-thread.sh`            | `--brain --slug --add \| --remove \| --set \| --clear`           |
| `park-thread.sh`              | `--brain --slug --reason` or `--brain --slug --unpark`           |
| `discard-thread.sh`           | `--brain --slug --reason`                                        |
| `verify-tree.py`              | `--brain <path>` (read-only; or `--rebuild-index` to regen)      |

All scripts take `--help` for full flag lists. Every script exits 0 on
success, 1 on operational failure with a specific error message to
stdout/stderr, and 2 on invocation errors (bad flags, missing paths).

Your adapter's job is to translate user intent ("I want a new thread
about X") into the right flag combo, invoke the script once, and pass
its stdout back to the user verbatim. Nothing more.

### 2. A way to surface skills to the user

Claude Code uses `skills/<name>/SKILL.md` frontmatter files that get
loaded as slash-menu commands. The SKILL.md contains:

- A name + description for routing ("use this when user says X, Y, Z")
- A Process section telling the LLM how to call the script
- Related-skills pointers

Your adapter should expose the same information in whatever format your
runtime expects — Codex tool configs, OpenAI function schemas, MCP
tool manifests, etc. The 16 SKILL.md files under `skills/` are the
authoritative source for what each skill does; translate, don't
re-author.

### 3. A way to resolve the pack root at invocation time

When the adapter invokes a script, it needs an absolute path. The
scripts themselves handle everything else — they self-locate via `$0`
to find siblings and templates. The adapter only needs to know:

> *where on disk is this pack installed?*

Options, in order of preference:

- **Env var set by the runtime.** Claude Code sets `CLAUDE_PLUGIN_ROOT`.
  Codex likely has an equivalent. Use whichever env var your runtime
  already exports for plugin/extension roots, plus an optional
  `PROJECT_BRAIN_PLUGIN_ROOT` override for users who want to point at a
  custom checkout.
- **Hard-coded install path.** A CLI distribution can use `/usr/local/
  share/project-brain` or similar.
- **Path relative to the adapter manifest.** If the adapter ships
  alongside the pack (monorepo-style), derive from its own location.

**Do not** require users to cd into the pack directory before invoking
— the scripts don't care about cwd.

### 4. A way to handle clarifying questions

Several skills (`new-thread`, `record-artifact`, `assign-thread`) can
ask the user for missing inputs. In Claude Code this goes through the
`AskUserQuestion` tool. In your adapter, use whatever clarification
primitive your runtime offers — an inline prompt, a form, a
multiple-choice dialog.

**Important**: the SKILL.md files explicitly discourage asking
unnecessarily. The LLM is expected to **derive slug/title/reason/etc.
from the user's own language first**, and only ask when truly
ambiguous. Preserve this discipline in your adapter's equivalent
instructions — it's the primary reason operations take 20s instead of
2 minutes.

## The portability contract (what the scripts promise)

Any adapter can rely on these guarantees from the scripts layer:

1. **POSIX bash.** No bashisms beyond what `#!/usr/bin/env bash` with
   `set -euo pipefail` covers. Tested on macOS (bash 3.2) and Linux
   (bash 5+).
2. **Self-locating.** Scripts derive their sibling paths from `$0` —
   they don't read `CLAUDE_PLUGIN_ROOT` or any adapter-specific env var.
3. **Pure file I/O.** No network calls, no daemon dependencies. The
   validator uses stdlib only when PyYAML is absent (falls back to a
   vendored mini-parser).
4. **Atomic operations.** Each mutating script is write-once per
   invocation; on mid-operation failure, the tree is either fully
   updated or fully unchanged.
5. **Deterministic output.** The aggregate-index rebuild produces
   byte-stable output regardless of walk order, so script invocations
   from different adapters produce the same files.
6. **Stable exit codes.** 0 = success, 1 = operational failure, 2 =
   invocation error. Adapters can switch on this without parsing
   messages.

## The adapter contract (what the scripts expect from the runtime)

In the other direction, the scripts assume the adapter:

1. **Invokes them exactly as documented.** Flags passed as shown in
   each `--help`; no re-interpretation.
2. **Does not wrap them in a sandbox that blocks file writes** under
   the host project's `project-brain/` directory.
3. **Sets env vars the scripts probe** — specifically
   `PROJECT_BRAIN_HOME`, `COWORK_WORKSPACE_FOLDER`, `CODEX_PROJECT_ROOT`,
   or `CLAUDE_PROJECT_ROOT` if the host defines a "project root"
   concept. The scripts probe these in priority order via
   `init-brain.sh`'s auto-detect logic.
4. **Respects exit codes.** On exit 1, surface the script's stderr to
   the user so they can diagnose.

## Worked example: a minimal CLI adapter

A CLI adapter is the smallest possible runtime wrapper. It takes user
subcommands and routes them to the scripts. See `bin/project-brain` in
this repo for a ~100-line example that lets you drive the pack from
any shell without Claude Code installed.

```bash
project-brain init                              # init-brain.sh (zero flags)
project-brain new-thread auth "Auth design" \
  --purpose="JWT vs session"                    # new-thread.sh
project-brain review auth                       # review-thread.sh
project-brain record auth "Debate result" \
  --kind=debate --content='JWT vs session...'   # record-artifact.sh
```

The CLI itself is a ~100-line bash case-statement that forwards flags.
No plugin manifest, no SKILL.md, no `CLAUDE_PLUGIN_ROOT`. It exists as
a second adapter to prove the scripts layer is genuinely portable.

## Non-goals

This porting guide **does not** promise:

- **Cross-runtime skill discovery.** A project-brain install in Claude
  Code won't show up in a Codex project and vice versa. Each runtime
  has its own plugin registry and install path.
- **Shared state across runtimes on the same machine.** If you init a
  brain from the Claude Code CLI and then invoke via a Codex adapter,
  both will operate on the same on-disk files — that's by design. But
  there's no shared "active thread" pointer or session.
- **Automatic adapter generation.** Translating SKILL.md into Codex
  config or MCP tool schemas is manual work; the 16 skill descriptors
  are not machine-extractable into arbitrary formats.

## When to revisit directory layout

The current layout (`scripts/`, `assets/`, `skills/`, `.claude-plugin/`
at the repo root) stays as-is **until a second adapter is actually
being built**. At that point, move adapter-specific files to
`adapters/<name>/`. Until then, avoid the breaking change; the layer
model documented here is what maintainers need, not folder hierarchy.

Questions? File an issue with the tag `porting`.
