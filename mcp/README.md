# project-brain-mcp

MCP server for [project-brain](https://github.com/ai-project-brain/project-brain) — a markdown-in-git decision-tracking skill pack.

Exposes the pack's skills as MCP tools, prompts, and resources so any MCP-aware client (Claude Desktop, Claude Code, future ChatGPT/Codex integrations) can use them without the host-specific affordances the original Cowork integration relied on.

## Install

```bash
pip install -e ./mcp
```

## Run

```bash
project-brain-mcp
```

The server speaks MCP over stdio. Point your MCP client at the binary as a stdio-launched server.

## What it exposes

- **Tools** — thin wrappers over Layer-1 bash scripts. Each tool validates input through a Pydantic schema before invoking the script via `subprocess.run` with `shell=False`. v1.0 ships `new_thread`, `list_threads`, `verify_tree`, plus a `run_skill(name)` fallback for clients with weak prompt support.
- **Prompts** — the body of each `skills/<slug>/SKILL.md` (with YAML frontmatter stripped). v1.0 ships `new-thread`, `list-threads`, `verify-tree`.
- **Resources** — current file content for `<brain>/thread-index.md`, `<brain>/current-state.md`, `<brain>/CONVENTIONS.md`. Resolved from `$PROJECT_BRAIN_HOME` at request time.

## Pack root resolution

The server finds the project-brain pack on disk by walking up from its own location until it finds a `CONVENTIONS.md` + `skills/` + `scripts/` triplet. Override with `$PROJECT_BRAIN_PACK_ROOT` if the auto-detect can't find it.
