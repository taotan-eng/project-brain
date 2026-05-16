# project-brain handoff docs

This folder holds operational handoff documents — self-contained briefs that an
agent (Claude Code, Cowork, Codex, etc.) or a human collaborator can pick up
cold and execute against the project-brain repo with no back-and-forth.

## Naming

- `day-NN-<short-slug>.md` for daily v1.0 execution handoffs (e.g., `day-01-license-rename-audit.md`)
- `milestone-<name>.md` for cross-week milestone handoffs (e.g., `milestone-v1.0-release.md`)
- `audit-report-<YYYY-MM-DD>-<topic>.md` for one-off audit outputs

## Structure of a handoff doc

Every handoff has the same skeleton — agents and humans both rely on the
shape to know where to look. Sections in order:

1. **TL;DR** — one paragraph summary of what gets done.
2. **Context** — pointers to the planning artifact and any prior handoffs.
3. **Goal** — the day/milestone outcome in plain language.
4. **PR-merge criteria** — the concrete, programmatically-checkable criteria a reviewer (human or CI) uses to decide whether this day's work is ready to merge. Stated up front so the rest of the doc is anchored to merge-readiness.
5. **Development loop** — the test-fix-retest pattern the executor is expected to follow.
6. **Pre-flight checks** — preconditions that must be true before starting, as a single bash block that exits non-zero on failure.
7. **Tasks** — numbered, each with file paths, exact commands, and a **validation script** that exits 0 on success.
8. **Common failure modes and fixes** — predictable failures + in-loop fixes so the executor self-recovers instead of escalating.
9. **End-of-day evaluation** — a single bash script that generates the evaluation report (see below) and returns a final pass/fail exit code.
10. **Exit gate** — the procedural close-out (status update, execution-log entry, commit).
11. **Out of scope** — explicit list of what NOT to touch, to prevent scope creep.
12. **Escalation conditions** — when to stop and ask the human (judgment-only; mechanical failures stay in-loop).

## Audience

The primary audience is an agent operating on the repo without prior session
context. Treat each doc as if you're handing the work to a smart but
uninformed engineer: include every file path, every command, every validation
step. The handoff doc itself IS the context.

## Development methodology — test-fix-retest loop

Handoff docs assume the executing agent runs a **test-fix-retest loop**
autonomously per task. The human's job is to read the execution log at the
end of the day, not to run manual checks during the day.

The loop per task:

1. Read the task spec.
2. Execute the task.
3. Run the task's **validation script** — a single bash block that exits 0 on success, non-zero on failure.
4. If validation fails, diagnose using the "Common failure modes" section, apply the fix, re-run validation. Repeat up to **~5 attempts per task**.
5. If validation still fails after ~5 attempts, OR the failure isn't in "Common failure modes," **escalate** to the human.

Implications for handoff-doc authors:

- **Every task must have a programmatic validation script that returns exit-0 on success.** Manual "look at the file and check" steps are not acceptable.
- **List predictable failures and their fixes** in a "Common failure modes" section so the executing agent can self-recover.
- **Reserve escalation for human-judgment calls only** — license interpretation, unexpected file types appearing in audit results, scope ambiguity, irrecoverable pre-flight failures. Mechanical failures (typos, missed cross-references, wrong sed expression) should be handled in-loop.
- **End-of-day**: a single end-of-day-validation script that proves the exit gate. The human reads that script's output, not the individual task outputs.

## Workflow — feature branches and PRs

Every handoff executes on a **fresh feature branch** branched from `main`.
No direct commits to `main` (day-1 was a one-time exception while the
convention was being bootstrapped; from day-2 onward the rule is strict).

**Branch naming**: `day-NN/<short-slug>` matching the handoff filename
(`day-NN-<short-slug>.md` → branch `day-NN/<short-slug>`).

**The exit gate of every handoff is**: evaluation report says
`MERGE-READY` + branch is pushed + a PR is open against `main` whose body
IS the evaluation report. The reviewer (human or future CI) reads the PR
body to decide whether to merge — no separate document to chase down.

Concretely, the executor:

1. At pre-flight: `git checkout main && git pull --ff-only && git checkout -b day-NN/<slug>`.
2. Commits during the day land on the feature branch (default once checked out).
3. After the end-of-day evaluation passes:
    - Push: `git push -u origin day-NN/<slug>`.
    - Open PR: `gh pr create --base main --head day-NN/<slug> --title "Day NN — <theme>" --body-file docs/handoff/day-NN-evaluation-report.md`.
4. Report the PR URL to the human. Stop. Human reviews and merges via GitHub UI.

If the evaluation returns `NOT-READY`, do **not** push or open the PR — return to the failing task's test-fix-retest loop. Only push when MERGE-READY. This means a half-done day never produces a PR; the absence of a PR is itself a signal.

Prerequisite: the `gh` CLI must be installed and authed. If `gh auth status` reports unauthed, escalate (the executor cannot configure auth credentials autonomously).

**Smoke test naming**: smoke tests live in `scripts/` but **must NOT** start with `test_` (that's reserved for files picked up by `python3 -m unittest discover -s scripts -p 'test_*.py'`, which the CI workflow runs and which depends only on `PyYAML`). Use `scripts/smoke_<thing>.sh` or `scripts/smoke_<thing>.py` instead. A smoke test named `test_*.py` will be auto-discovered as a unit test, get imported in CI, and fail if it pulls in dependencies CI doesn't install (e.g. the `mcp` SDK).

## PR-merge criteria and evaluation reports

Every handoff defines its own **PR-merge criteria** — the explicit,
programmatic predicates that determine whether this day's work is ready
to merge. The criteria are stated near the top of the handoff so the
entire doc is anchored to a merge-readiness target.

The end-of-day evaluation script then evaluates each criterion and produces
an **evaluation report** at `docs/handoff/day-NN-evaluation-report.md` with
this shape:

```markdown
# Day-NN Evaluation Report

- Generated: <ISO timestamp>
- Plan reference: <link to plan artifact + section>

## Merge criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | <criterion>  | ✓ | <programmatic evidence: file sizes, counts, exit codes> |
| ... |

## Files changed

<git diff --stat output>

## Commits

<git log --oneline output for this day's commits>

## Verdict: **MERGE-READY** | **NOT-READY**

<one-sentence summary; if NOT-READY, name the failed criterion>
```

The evaluation report IS the artifact the human (or a reviewer/CI) reads at
end-of-day to decide whether to merge. The executor never asks the human
"did this pass?" — the report answers that question programmatically. If
verdict is MERGE-READY, the human merges (or pushes); if NOT-READY, the
human sees exactly which criterion failed and can decide whether to
re-engage the executor or fix manually.

This means the executor's end-of-day deliverable is two things:

1. The actual code/file changes (committed).
2. The evaluation report (committed to `docs/handoff/`).

Both must be in place before status transitions to `done`.

**Canonical shape lives in `_evaluation-report-template.md`** — the template
file documents the required structure, naming convention, what
`MERGE-READY` formally means, a skeleton bash generator script, and a list
of anti-patterns to avoid. Every handoff's End-of-day evaluation script is
a parameterized customization of that skeleton. Treat the template as the
source of truth; if you find yourself re-deriving the report shape from a
prior day's eval script, you're working from a stale model — read the
template instead. The underscore prefix in the filename keeps it sorted
separately from the actual daily report files (`day-NN-evaluation-report.md`)
so it's never mistaken for a real report.

## Source of truth

The plan that handoffs implement lives in the project-brain thread:

- Plan artifact: `project-brain/threads/project-brain-cross-harness/artifacts/0003-v1.0-implementation-plan-(3-week-compressed).md`
- Round-01 debate (for context on why decisions were made): `project-brain/threads/project-brain-cross-harness/debate/round-01/`

Handoffs cite the plan for "why" decisions; do not re-litigate plan decisions
inside a handoff. If the plan needs to change, edit the plan artifact and
note the change in a new handoff — never silently diverge.

## Status taxonomy

Each handoff has a `Status:` field in its header:

- `draft` — being written; do not execute.
- `ready` — fully specified, awaiting an agent or human to pick up.
- `in-progress` — execution started; the executor should write progress notes in a `## Execution log` section.
- `done` — exit gate satisfied; closing summary appended at the bottom.
- `blocked` — execution halted; reason and unblock conditions recorded.
