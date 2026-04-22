---
round: {{ROUND_NUM}}
created_at: {{CREATED_AT}}
owner: {{OWNER}}
leaf: {{LEAF_PATH}}
baseline_sha: {{BASELINE_SHA_OR_HEAD}}
---

# Round {{ROUND_NUM}} — feedback in

What this round is trying to answer. Kept short — reviewers read this first.

## Seed context

- **Baseline under review:** `{{LEAF_PATH}}` at commit `{{BASELINE_SHA_OR_HEAD}}`
- **Prior rounds:** {{PRIOR_ROUNDS_SUMMARY_OR_NONE}}
- **Open issues carried forward:** see `../round-{{PREV_ROUND}}/open-issues.md`

## What reviewers should focus on

<!-- One paragraph. Narrow the scope; don't ask for a re-review of the whole artifact every round. -->

## Personas dispatched

<!-- List from CONVENTIONS.md § 10.2. -->

- `<persona-a>` — <one-line charter>
- `<persona-b>` — <one-line charter>
- `defender` — rebuts reviewer claims; produces CONCEDE / CONCEDE-IN-PART / DEFER / REJECT verdicts
- `synthesizer` (optional, for large rounds) — integrates defender verdicts into patch proposals

## Success criteria for this round

<!-- What does "done" look like? e.g. "all P0 defects caught or confirmed absent", "phase isolation structurally enforced". -->

## Out of scope for this round

<!-- What reviewers should NOT spend cycles on — usually things already landed in a prior round. -->
