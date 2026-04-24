---
description: Run a structured multi-agent review round against a thread or leaf
argument-hint: "<target> [--reviewers=N] [--review-mode=full|delta]"
---

Run the `multi-agent-debate` skill. Creates `debate/round-NN/` under the artifact per CONVENTIONS § 7, spawns per-persona reviewer subagents in parallel, runs a defender + synthesizer, emits `proposed-patches.md` + `open-issues.md`. On leaf scope, toggles status between `decided|specified` and `hardening`. On thread scope, just updates `last_debate_round`.
