# Promote to tree: {{LEAF_TITLE}}

Promotes `{{SOURCE_THREAD}}` → `tree/{{DOMAIN}}/{{LEAF_SLUG}}.md`.

## Decision

{{DECISION_SUMMARY}}

## Why

Promoted from thread `{{SOURCE_THREAD}}` after {{ROUND_COUNT}} debate round(s). See the thread for the full deliberation history.

## Files changed

- `thoughts/tree/{{DOMAIN}}/{{LEAF_SLUG}}.md` — new leaf (status=`in-review`)
- `thoughts/threads/{{SOURCE_THREAD}}/thread.md` — adds this leaf to `promoted_to` / `promoted_at`, sets status to `in-review`
{{NODE_CHANGES}}

## After merge

Run `finalize-promotion` to flip the leaf to `decided` and the thread back to `active` (or archive it if this was its only candidate).

## Checklist

- [ ] Decision body is self-contained (new engineer should understand without reading the thread)
- [ ] Alternatives considered are documented
- [ ] `domain` frontmatter matches the path under `tree/`
- [ ] `source_thread` points to the source thread slug
- [ ] `verify-tree --thread {{SOURCE_THREAD}}` exits 0 locally
