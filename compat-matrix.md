# project-brain compatibility matrix

Where project-brain works, how well, and what's validated end-to-end. Updated whenever a new host lands or an existing row's validation status changes.

The "First-session validated" column tracks whether a real user has gone from a fresh install to a successful first roundtrip on that host. "Pending" rows have a documented install path (see `INSTALL.md`) but haven't yet been exercised end-to-end on a fresh machine.

| Host | Tier | Transport | First-session validated | Notes |
|------|------|-----------|--------------------------|-------|
| Claude Code | Pro+ | stdio | yes (week 1, day-2 smoke test) | Native plugin loader + MCP stdio. Per-project brain via cwd auto-detect; no `PROJECT_BRAIN_HOME` env required. Install via `brew install project-brain-mcp` on macOS. |
| Claude Desktop | Pro | stdio | yes (week 1, day-5 demo on macOS) | `mcpServers` config edit in `claude_desktop_config.json`. `PROJECT_BRAIN_HOME` env names the project root; brain lands at `<root>/project-brain/`. Install via `brew install project-brain-mcp` on macOS. |
| Claude Desktop | Free | stdio | pending (MCP support documented by Anthropic; demo not yet captured) | Same `mcpServers` config path as Pro per Anthropic docs; tier limits message volume, not MCP feature access. Validation pending — Tom tested Pro on day-5 but not Free. Install via `brew install project-brain-mcp` on macOS. |
| OpenAI Codex CLI | (no tier gating) | stdio | yes (week 2, day-9) | TOML config at `~/.codex/config.toml` under `[mcp_servers.project-brain]`. Or `codex mcp add project-brain -- uvx project-brain-mcp`. Known limitation: Codex's MCP support advertises **Resources, Tools, Elicitation** — Prompts not surfaced (use `run_skill` tool to retrieve SKILL.md bodies). See `docs/notes/day-06-codex-mcp-support.md`. |
| OpenAI Codex GUI | (no tier gating) | stdio | yes (week 2, day-9) | Shares `~/.codex/config.toml` with Codex CLI. Same `[mcp_servers.project-brain]` block; no separate config. Same Prompts limitation as Codex CLI. |

> **ChatGPT Desktop** is deferred to v1.1. ChatGPT's MCP connectors run from OpenAI's
> infrastructure and can't reach a self-hosted MCP server on localhost; a public tunnel
> (ngrok / Cloudflare Tunnel) is required, which is out of scope for v1.0's target
> audience. The open question for v1.1: whether any ChatGPT tier supports local-connector
> access without a tunnel. Tracked in the project's meta-brain
> (`chatgpt-desktop-validation` thread, parked).

## Tier glossary

- **Pro+**: any paid Anthropic tier (Pro, Max, Team, Enterprise).
- **Free**: zero-cost tier. MCP support is per-host; Claude Desktop Free supports MCP, Codex CLI/GUI have no tier gating.

## Validation status legend

- **yes (week N, day-NN demo)**: a fresh-machine first-session demo was captured and committed under `docs/demos/`.
- **pending (day-NN)**: the install path is documented in `INSTALL.md` and the bash-side smoke test confirms the server boots, but no end-user demo on the host has run yet. Day-NN is the scheduled demo.
- **not supported**: no path exists; either the host lacks MCP support or the tier excludes it.

Future rows for community-maintained adapters (Cursor, Continue, Aider, Gemini CLI) will land in week 3 when `CONTRIBUTING.md` gets fleshed out and the contribution flow is documented.
