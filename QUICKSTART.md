# Quickstart — from idea to merged decision in ten minutes

You have an idea worth tracking and want to see it turn into a reviewed, merged decision in your repo. This guide walks you through the whole pipeline using a single worked example: "Should we hire a second backend engineer?" You will capture the thought, sketch candidate answers, stress-test them with AI reviewers, lock in a choice, open a PR, and merge the final decision into your tree — all while keeping a complete audit trail.

After this, you will understand what a day with the pack looks like. You do not need to run anything; this is a narrative walk-through.

---

## Prerequisites (30 seconds)

You need:
- A git repo (any language, any size). This example assumes GitHub and the `gh` CLI (version 2.0+, authenticated).
- An AI agent runtime that runs skills. Claude Code is the reference implementation; Claude Desktop with Cowork, Cursor, Gemini CLI, or Aider also work (see RUNTIME.md for compatibility notes).
- Five uninterrupted minutes.

The pack is language-agnostic and lives in `thoughts/` at your project root, so your codebase is unaffected.

---

## Install (90 seconds)

Ask your agent: "Install the `project-brain` skill pack into my current project. Use the Claude Code layout if running inside Claude Code; otherwise use the generic layout."

Your agent will clone the pack, place the skills where they belong (`.claude/skills/project-brain/` for Claude Code; `thoughts/.pack-skills/` for others), copy `CONVENTIONS.md` into `thoughts/`, and run `init-project-brain` to scaffold the scaffold. You will answer a few questions: your project alias (e.g. `myapp`), the top-level tree domains you plan to use (e.g. `engineering / product / operations`), and your git remotes. After init completes, your project gains a `thoughts/` directory with `thread-index.md`, `current-state.md`, `tree/NODE.md`, and one `NODE.md` per domain you named.

The entire setup is a single commit. No hidden files, no database.

---

## The worked example: "Should we hire a second backend engineer?"

A hiring decision is a good test case because it has clear stakes (it is costly and slow to reverse), multiple legitimate perspectives (business need, team readiness, budget), and a recognizable origin (something you thought about, and now you need to track it). The decision is also orthogonal to code, so the example generalizes to any domain.

### Step 1 — Capture the thought (`new-thread`)

You call your agent: "Start a new thread. I've been thinking about whether we should hire a second backend engineer."

Your agent prompts for a slug (you answer `hire-backend-2`), a title (`Should we hire a second backend engineer?`), and a one-line purpose (`Evaluate headcount need against budget and team capacity`). The agent also reads your git config for the owner email and asks which project this belongs to (e.g., `myapp`).

After you confirm, the agent runs `new-thread`. You now have:

```
thoughts/threads/hire-backend-2/
  thread.md                    # frontmatter + your notes
  decisions-candidates.md      # candidate decisions (empty)
  open-questions.md            # open questions (empty)
```

The `thread.md` frontmatter looks like this (realistic copy):

```yaml
---
id: hire-backend-2
title: Should we hire a second backend engineer?
created_at: 2026-04-22T14:30:00Z
owner: you@company.com
primary_project: myapp
related_projects: []
soft_links: []
status: active
maturity: exploring
tree_domain: null
tree_node_type: null
tree_prs: []
promoted_to: []
promoted_at: []
---

# Should we hire a second backend engineer?

## Context

We've been running the backend with one full-time engineer for 18 months. Recently, the feature backlog has grown and oncall rotations are getting heavy. This thread explores whether hiring a second backend engineer is the right move, or if we should invest in tooling and automation instead.
```

The thread is live. It appears in `thoughts/current-state.md` under "Active threads" immediately.

### Step 2 — Sketch the candidates (`update-thread`)

Over the next few hours, you think through three realistic options. You call your agent: "Update the thread. Add three candidate decisions to the hiring-backend-2 thread: 'Hire now', 'Hire in Q3', and 'Don't hire, invest in tooling'."

Your agent runs `update-thread` three times (or once with a batch operation, depending on the runtime). Each time, it appends a new H2 section to `decisions-candidates.md`:

```markdown
## Hire now

Start the search immediately. Hire within 6–8 weeks, ramping the new hire in parallel to Q2 planning.

### Pros
- Reduces oncall load immediately
- Gives us 4+ months of ramp-up time before the busy Q3 season

### Cons
- Adds hiring overhead during active sprint work
- New hire may not be productive for first 3 months

### Open questions
- Budget has room, but what is the impact on headcount planning for the rest of the year?

---

## Hire in Q3

Wait until post-Q2 planning. Clean slate for onboarding and focus.

### Pros
- More time to evaluate if automation can reduce load
- Cleaner onboarding after Q2 push is done

### Cons
- Oncall pressure continues through Q2
- Competitive talent may already be off the market

---

## Don't hire, invest in tooling

Instead of headcount, spend the Q2 budget on automation: better observability, self-healing alerts, deploy tooling.

### Pros
- Same headcount gives us more leverage per engineer
- Competitive advantage in engineering velocity

### Cons
- Oncall still heavy in the near term
- Tool selection takes time upfront
```

You also update the thread maturity to `refining` (the candidates are now on paper, so you are narrowing scope). The agent updates the frontmatter and regenerates `thread-index.md` and `current-state.md` in the same commit. The thread moves from `exploring` to `refining` in the index.

You add a soft_link to your Q2 planning doc (a Google Doc or internal wiki page) so context is preserved: `soft_links: [{uri: "https://docs.google.com/document/d/...", role: "prior-decision"}]`.

### Step 3 — Pressure-test with a debate (`multi-agent-debate --scope=thread`)

You want reviewers to poke holes before you lock in. You call your agent: "Run a debate on the hire-backend-2 thread. I want three reviewers: red-team, fresh-eyes-reader, and a financial-realist who thinks we should maximize engineering-per-dollar."

Your agent runs `multi-agent-debate --scope=thread --reviewers=3 --personas="red-team,fresh-eyes-reader,financial-realist:thinks we should maximize engineering velocity per dollar spent; challenges arguments that don't account for cost-benefit"`.

The skill:
1. Creates `thoughts/threads/hire-backend-2/debate/round-01/` and writes `feedback-in.md` with your brief.
2. Spawns three reviewer subagents (in Claude Code, these run in parallel). Each reads the thread, the decisions-candidates.md file, and the soft-linked Q2 planning doc.
3. Red-team returns: "Hiring now is risky — what if the new hire doesn't work out? You're locked into 18+ months of severance liability. The tooling option hedges better."
4. Fresh-eyes-reader returns: "I don't see any analysis of team velocity before/after. You need a concrete number for 'oncall is too heavy'."
5. Financial-realist returns: "Hiring is 150k + ramp time. The tooling option is 30k but takes 3 months to measure. Neither decision is defensible without cost data."

Each reviewer's analysis lands in `debate/round-01/tryouts/<persona>.md`. The skill also spawns a defender subagent who rebuts:

```markdown
## Defender rebuttal

- **Red-team oncall-liability claim:** Oncall pressure is measurable (we have logs). I'd rather absorb hiring risk than let engineers burn out. Severance is a known cost; burned-out turnover is not.
- **Fresh-eyes velocity claim:** Conceded in part. We should add a metrics section before locking in. (Deferred to next round if the thread stays active.)
- **Financial-realist cost concern:** Fair point. The tooling budget includes automation, but the ROI window is longer. I think the real lever is: can we unblock velocity without adding headcount? We don't know yet. That's why we're thinking.

Verdict: **CONCEDE-IN-PART** on fresh-eyes (metrics needed). **DEFER** on financial-realist (we'll get better cost data). **REJECT** red-team's severance framing (it's real but not a blocker).
```

A synthesizer (optional for large rounds) reads all three analyses plus the defender rebuttal and writes:

```markdown
## Synthesizer summary

Three concerns surfaced:
1. **Cost trade-offs are not quantified.** Red-team, fresh-eyes, and financial-realist all point to missing data. Before locking in, this thread should have concrete numbers (oncall volume, projected new-hire ramp, tooling ROI timeline).
2. **Hiring risk is underexplored.** If hiring fails, the org is worse off. The thread should document failure modes and mitigation.
3. **Tooling option is underspecified.** What exactly would the 30k buy? How long to measure impact?

Recommendation: Don't lock in yet. Address the cost and risk sections in the next update, then re-open for a second round if the team changes their answer.
```

All of this lands in `thoughts/threads/hire-backend-2/debate/round-01/` as permanent artifacts. The thread's frontmatter picks up `last_debate_round: debate/round-01`. The thread **does not change status** — it stays `active/refining`. Debate is feedback, not a decision. You can ignore it, agree with it, or refine based on it.

### Step 4 — Lock in (`update-thread maturity --set locking`)

After reading the feedback, you realize the financial-realist is right: you need cost data. You spend an hour modeling both options, add a "Cost and Risk Analysis" section to `thread.md`, and narrow `decisions-candidates.md` to your top choice: "Hire in Q3". You keep the other two as historical context (not actively considered, but documented).

You call your agent: "Update the thread maturity to locking. We've done the analysis and narrowed down."

Your agent updates `thread.md` frontmatter: `maturity: refining → locking`. The thread is now ready to promote. The index files update to show it in "Locking" rather than "Refining".

### Step 5 — Promote (`promote-thread-to-tree`)

You call your agent: "Promote the hire-backend-2 thread to the tree. It belongs under operations/hiring."

Your agent runs `promote-thread-to-tree`. The skill:
1. Asks which base branch to cut from (defaults to `main` from your project's `projects.yaml` entry, but always prompts). You say `main`.
2. Creates the promotion branch `promote/hire-backend-2`.
3. Lands three commits on the branch:
   - Commit 1: `promote(hire-backend-2): stage leaves` — stages the leaf under `tree-staging/hire-backend-2.md` with `status: draft`.
   - Commit 2: `promote(hire-backend-2): land leaves` — moves it to its final path `tree/operations/hiring/hire-backend-2.md`, still `status: draft`.
   - Commit 3: `promote(hire-backend-2): flip to in-review` — flips the leaf to `status: in-review` and appends the PR URL to the thread's `tree_prs` list.
4. Lands one bookkeeping commit on `main`: `promote(hire-backend-2): open PR` — flips the thread from `active/locking` to `in-review/locking`.
5. Opens the promotion PR via `gh pr create` with the title `promote: Should we hire a second backend engineer? → operations/hiring`. The PR body includes a summary extracted from the thread's context.

The PR URL gets printed to stdout. You now have a reviewable PR with three commits inside. The thread's frontmatter is synced with a `tree_prs: ["https://github.com/.../pull/1234"]` entry.

### Step 6 — Review and merge

Your PM, your CTO, and an ops lead review the PR. The CTO comments: "Good analysis. I'd add a 'Success metrics' section to nail down what we'll measure in Q3 to know if the hire was right." You add a brief section to the leaf file in the PR, commit, and push. The PR gets approved.

You merge the PR via GitHub (or `gh pr merge`). The commits land on `main`. The leaf is now `status: in-review` on `main`, waiting for finalize to flip it to `decided`.

### Step 7 — Finalize (`finalize-promotion`)

You call your agent: "Finalize the promotion. The PR merged."

Your agent runs `finalize-promotion`. The skill:
1. Checks the PR state via `gh pr view` — it is `MERGED`.
2. Diffs the merge commit to find which leaves landed. (Just `tree/operations/hiring/hire-backend-2.md`.)
3. Flips the leaf from `in-review` to `decided`.
4. Appends entries to the thread's `promoted_to: ["operations/hiring/hire-backend-2"]` and `promoted_at: ["2026-04-22T17:45:00Z"]` lists.
5. Asks: "Archive the thread or keep it active for follow-up work?" You answer: `archive`.
6. Flips the thread from `in-review` to `archived`, writes `archived_at: 2026-04-22T17:45:00Z` and `archived_by: you@company.com`, and `git mv`s the thread directory from `threads/hire-backend-2/` to `archive/hire-backend-2/`.
7. Commits and pushes: `chore(hire-backend-2): finalize promotion — 1 leaf decided (archive)`.

The thread is now complete. It is no longer in `current-state.md` (only active and parked threads are listed there). The leaf at `tree/operations/hiring/hire-backend-2.md` is the single source of truth going forward, status `decided`, ready for hardening (if you wanted to stress-test it further) or implementation.

---

## Where to look next

`thoughts/thread-index.md` now shows the hiring thread in the "Archived" table, with columns for slug, title, owner, created_at, and promotion history.

`thoughts/current-state.md` no longer lists it (only active and parked threads).

Run `skill: discover-threads --status=archived --owner=you@company.com` to find all your archived threads — good for "what did I decide on hiring?" queries six months from now.

Open `thoughts/tree/operations/hiring/NODE.md`. It now lists `hire-backend-2.md` as a leaf. The tree is growing.

---

## A week later: the team uses the brain

One short scenario per cross-cutting skill:

**discover-threads:** Your engineering lead asks: "What am I assigned to?" She runs `skill: discover-threads --assigned="sarah@company.com" --status=active`. The output is a table of 5 threads she owns, with maturity and review status. One is `design-graphql-caching` in `locking` maturity, ready to promote. Another is `api-rate-limits` in `parked` with a trigger "after Q2 launches". No agent conversation needed — it's a fast query.

**assign-thread:** Your manager says: "Can you own the observability roadmap thread?" You run `skill: assign-thread --thread=observability-v2 --add="you@company.com"`. The thread's `assigned_to` list grows (multiple people can own one thread). An audit line is appended to the thread body.

**review-parked-threads:** Friday afternoon, you run `skill: review-parked-threads --stale-days=30`. The output partitions the parked threads into three buckets: "actionable" (trigger is set), "stale" (parked > 30 days), and "no trigger" (hygiene warning). One thread is stale and has no trigger — you decide to either set a trigger or discard it.

**park-thread:** Work on `api-rate-limits` stalls while the infrastructure team decides on a new RPC layer. You run `skill: park-thread --reason="blocking on RPC design" --trigger="when RPC design lands"`. The thread flips from `active` to `parked`, the maturity is preserved, and the trigger is recorded. When the time comes, `park-thread --unpark` restores it to `active` at the same maturity.

**materialize-context:** You are starting a new thread on "how should we deprecate v1 API?" and you want to pull in context from three prior decisions. You create the thread, add soft_links to them, then run `skill: materialize-context --artifact-path=threads/deprecate-v1-api/thread.md`. The skill fetches the three prior leaves, budgets their content by role, and writes `context.md` and `context.json` sidecar. No manual copy-paste.

**verify-tree:** Before you open a promotion PR, you run `skill: verify-tree` from the brain root. It checks all 21 built-in invariants (title-vs-H1 mismatch, soft_links validity, frontmatter completeness, status consistency, etc.) and exits 0 or reports violations. You fix any errors and promote cleanly.

---

## What you didn't do

You didn't write any project-specific skill code. The pack is generic and handles the pipeline.

You didn't configure a database. Everything is files in `thoughts/`.

You didn't set up any infrastructure. The tree is reviewable as code in a PR, and that's the whole point.

---

## Next steps

- Read `INSTALL.md` if you want the authoritative step-by-step install procedure for a different runtime.
- Read `CONVENTIONS.md` § 10 if you want to customize the domain taxonomy, debate personas, or build toolchain for your project.
- Read `CONTRIBUTING.md` if you want to write a new skill or extend the pack.
- Run `skill: discover-threads` and `skill: review-parked-threads` to start querying your brain once it has threads.
