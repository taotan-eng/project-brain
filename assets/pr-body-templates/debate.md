## What this PR lands

- **Artifact under debate:** [`{{LEAF_PATH}}`]({{LEAF_URL}})
- **Round:** {{ROUND_NUM}}
- **Debate dir:** [`{{LEAF_PATH}}/debate/round-{{ROUND_NUM}}/`]({{DEBATE_URL}})

## Patches applied

<!-- From proposed-patches.md. List each with a one-liner. -->

- **{{PATCH_ID}}** — <title>

## Defender verdicts summary

- CONCEDE: {{N}}
- CONCEDE-IN-PART: {{N}}
- DEFER: {{N}}
- REJECT: {{N}}

## Open issues carried forward

- OI-{{ROUND_NUM}}-{{N}} — <title>

## Post-merge checklist

- [ ] `debate/index.md` round-{{ROUND_NUM}} block marked merged
- [ ] Leaf status returns to `decided` (or `specified` if impl-spec still valid)
- [ ] If impl-spec exists and was invalidated by patches: impl-spec `status` → `stale`; leaf status → `decided`
