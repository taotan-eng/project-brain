---
description: Scaffold a project-brain into this project (one-time setup)
---

Run the `init-project-brain` skill to scaffold a project-brain directory into the current project. Invoke `${CLAUDE_PLUGIN_ROOT}/scripts/init-brain.sh` directly — the script auto-detects the project home via Cowork/Codex/Claude env vars or `.git` walk, derives alias and title from the directory basename, and writes the scaffold in ~100ms. Pass `--force` only if the user explicitly wants to replace an existing brain (the script will refuse otherwise with a clear exit-1 message). No other tool calls needed before the script invocation.
