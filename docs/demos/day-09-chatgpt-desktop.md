# Day-9 ChatGPT Desktop Install Demo

- **Date:** 2026-05-17
- **Tester:** Tom (taotan6@gmail.com)
- **ChatGPT Desktop version:** <fill in>
- **ChatGPT account tier:** Plus / Pro / Team / Enterprise (circle one)
- **macOS / OS version:** <fill in>
- **project-brain-mcp version:** v1.0.0-rc.6 (from brew)
- **PROJECT_BRAIN_HOME:** <fill in>

## Steps performed

1. `brew install ai-project-brain/project-brain/project-brain-mcp`
2. `brew services start project-brain-mcp` — confirmed `started` status
3. `curl http://localhost:8787/sse` — confirmed HTTP 200 + text/event-stream
4. ChatGPT Settings → Connectors → Developer mode → Add custom connector → URL: `http://localhost:8787/sse` → Saved
5. Prompted "Using project-brain, list my threads."
6. Prompted "Using project-brain, create a new thread called 'chatgpt demo' with purpose 'Day-9 install verification.'"

## Evidence

### Step 1-3 — Service health

```
$ brew services list | grep project-brain-mcp
<paste output>

$ curl -sS --max-time 2 -o /dev/null -w "HTTP %{http_code} (%{content_type})\n" http://localhost:8787/sse
<paste output>
```

### Step 4 — Connector add

<Describe what you saw. Did the save succeed immediately? Did ChatGPT show any status / connection indicator? Did it list the project-brain tools anywhere?>

### Step 5 — list_threads round-trip

<Paste the ChatGPT prompt + response. Confirm: tools/call hit list_threads; response data matches actual thread index.>

### Step 6 — new_thread round-trip

<Paste the ChatGPT prompt + response. Confirm: tools/call hit new_thread; response confirms creation; slug used.>

### After-state directory

```
$ ls $PROJECT_BRAIN_HOME/project-brain/threads/chatgpt-demo/
<paste>

$ head -20 $PROJECT_BRAIN_HOME/project-brain/threads/chatgpt-demo/thread.md
<paste>
```

## Issues observed

<Anything that surprised you. INSTALL.md inaccuracies, menu paths that have shifted, error messages, things that worked but felt clunky. Or "None." if it went smoothly.>

## Verdict

**MERGE-READY** / **NOT-READY (escalation)** — circle one, with a one-sentence reason.
