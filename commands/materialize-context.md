---
description: Walk soft_links on a thread/leaf and bundle resolved content as context
argument-hint: "<artifact-path> [--consumer=reviewer|author|brief|full]"
---

Run the `materialize-context` skill. Walks `soft_links` refs on the target artifact, resolves each URI per CONVENTIONS § 5.1 (project aliases, tree-internal paths, file://, http(s)://, mcp://), filters and budgets per role, and emits an aggregated `context.md` ready to hand to a subagent or reviewer.
