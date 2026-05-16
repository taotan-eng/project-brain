# Day-5 Claude Desktop Install Demo

- **Date:** _<fill in>_
- **Tester:** Tom (taotan6@gmail.com)
- **Claude Desktop version:** _<fill in>_
- **macOS / OS version:** _<fill in>_
- **MCP SDK version** (`pip show project-brain-mcp`): _<fill in>_

## Steps performed

1. Pasted the `mcpServers` config from `INSTALL.md` § "Claude Desktop config" into `~/Library/Application Support/Claude/claude_desktop_config.json`.
2. Set `PROJECT_BRAIN_HOME` in the config to: `_<absolute path you used>_`.
3. Quit Claude Desktop and re-launched.
4. Opened a new chat and prompted: **"Using project-brain, list my threads."**
5. Prompted: **"Create a new thread called 'mcp demo' with purpose 'Day-5 install verification.'"**

## Evidence

### Step 4 — list_threads call

Thread day-5-gate created. Three active threads now:

day-5-gate — Close out day 5
mcp-demo — Day 5 installation verification
test-mcp-brain — UX testing

### Step 5 — new_thread call



list_threads
list_threads
slug	status	maturity	modified
mcp-demo	active	exploring	2026-05-16 14:34
test-mcp-brain	active	exploring	2026-05-16 14:17
### After-state directory listing

```
$ ls $PROJECT_BRAIN_HOME/threads/mcp-demo/
<paste output here>
```
decisions-candidates.md	open-questions.md	thread.md
## Issues observed

_If any. If none, write "None.";_

## Verdict

_MERGE-READY-aligned: did the agent successfully use the MCP server end-to-end? Yes / No / Partial — with one sentence on why._
