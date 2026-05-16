# project-brain compatibility matrix

Where project-brain works, how well, and what's validated end-to-end. Updated whenever a new host lands or an existing row's validation status changes.

The "First-session validated" column tracks whether a real user has gone from a fresh install to a successful first roundtrip on that host. "Pending" rows have a documented install path (see `INSTALL.md`) but haven't yet been exercised end-to-end on a fresh machine.

| Host | Tier | Transport | First-session validated | Notes |
|------|------|-----------|--------------------------|-------|
| Claude Code | Pro+ | stdio | yes (week 1, day-2 smoke test) | Native plugin loader + MCP stdio. Per-project brain via cwd auto-detect; no `PROJECT_BRAIN_HOME` env required. |
| Claude Desktop | Pro | stdio | yes (week 1, day-5 demo on macOS) | `mcpServers` config edit in `claude_desktop_config.json`. `PROJECT_BRAIN_HOME` env names the project root; brain lands at `<root>/project-brain/`. |
| Claude Desktop | Free | stdio | yes (week 1, day-5 demo path) | Same config-edit path as Pro; tier limits message volume, not MCP features. |
| ChatGPT Desktop | Plus, Pro, Team, Enterprise | HTTP/SSE (via bridge) | pending (day-7) | ChatGPT only accepts remote MCP endpoints; project-brain is stdio. Bridge via `npx -y mcp-remote http://localhost:8787/sse --transport stdio --command "uvx" --args "project-brain-mcp"`, then add the URL as a custom connector in **Settings → Connectors → Developer mode**. Free tier excluded — no custom-connector UI. See INSTALL.md § "ChatGPT Desktop config". |
| ChatGPT Desktop | Free | n/a | not supported | No custom-connector UI on Free; no MCP path available. |
| OpenAI Codex CLI | (no tier gating) | stdio | pending (day-8) | TOML config at `~/.codex/config.toml` under `[mcp_servers.project-brain]`. Or `codex mcp add project-brain -- uvx project-brain-mcp`. Known limitation: Codex's MCP support advertises **Resources, Tools, Elicitation** — Prompts not surfaced (use `run_skill` tool to retrieve SKILL.md bodies). See `docs/notes/day-06-codex-mcp-support.md`. |

## Tier glossary

- **Pro+**: any paid Anthropic tier (Pro, Max, Team, Enterprise).
- **Plus / Pro / Team / Enterprise**: OpenAI paid tiers (in increasing capability order). ChatGPT custom connectors require Plus minimum.
- **Free**: zero-cost tier. MCP support is per-host; Claude Desktop Free supports MCP, ChatGPT Free does not, Codex CLI has no tier gating.

## Validation status legend

- **yes (week N, day-NN demo)**: a fresh-machine first-session demo was captured and committed under `docs/demos/`.
- **pending (day-NN)**: the install path is documented in `INSTALL.md` and the bash-side smoke test confirms the server boots, but no end-user demo on the host has run yet. Day-NN is the scheduled demo.
- **not supported**: no path exists; either the host lacks MCP support or the tier excludes it.

Future rows for community-maintained adapters (Cursor, Continue, Aider, Gemini CLI) will land in week 3 when `CONTRIBUTING.md` gets fleshed out and the contribution flow is documented.
