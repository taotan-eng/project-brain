## What this PR builds

- **Decision:** [`{{LEAF_PATH}}`]({{LEAF_URL}})
- **Impl-spec:** [`{{IMPL_SPEC_PATH}}`]({{IMPL_SPEC_URL}})
- **Build thread:** [`{{BUILD_THREAD_SLUG}}`](../project-brain/threads/{{BUILD_THREAD_SLUG}}/thread.md)

## Stages completed

<!-- From impl-spec § 4 (build order). Check off as each stage lands. -->

- [ ] Stage 1 — {{STAGE_1_NAME}}
- [ ] Stage 2 — {{STAGE_2_NAME}}
- [ ] …

## Acceptance tests

<!-- From impl-spec § 3. Report pass/fail. -->

- canary: {{N}}/{{M}} passing
- core: {{N}}/{{M}} passing
- edge: {{N}}/{{M}} passing
- manual: <status>

## Discoveries fed back to decision

<!-- Design questions surfaced during build that belong in the source leaf's open-issues.md. -->

- <discovery> — pushed to `<source leaf>/open-issues.md`

## Out of scope

- …

## Post-merge checklist

- [ ] Leaf frontmatter `built_in` populated
- [ ] Impl-spec `status` → `built`
- [ ] Build thread `status` → `archived` or `active/refining` (if follow-up)
