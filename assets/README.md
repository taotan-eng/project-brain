# `assets/` — starter file set

Templates shipped with the **project-brain** plugin. Skills copy from here when scaffolding threads, leaves, debate rounds, PRs, and commits. All templates use `{{PLACEHOLDER}}` for substitutions; skills fill them in from user prompts, frontmatter, or config.

## Contents

```
assets/
  thread-template/
    thread.md                    # new-thread scaffolding
    decisions-candidates.md
    open-questions.md
  NODE-template.md               # new tree sub-node
  leaf-template.md               # new tree leaf
  impl-spec-template.md          # derive-impl-spec output shape
  thread-index-template.md       # init-project-brain: empty thread registry
  current-state-template.md      # init-project-brain: empty dashboard
  debate-round-template/
    feedback-in.md               # multi-agent-debate round kickoff
  pr-body-templates/
    promote.md                   # promote-thread-to-tree PR body
    build.md                     # ai-build PR body (in code repo)
    debate.md                    # multi-agent-debate patch round PR body
  commit-templates/
    promote.txt
    build.txt
    debate.txt
```

## Substitution placeholders

Common placeholders across templates:

| Placeholder              | Source                                  |
|--------------------------|-----------------------------------------|
| `{{SLUG}}`               | user prompt or derived from `{{TITLE}}` |
| `{{TITLE}}`              | user prompt                             |
| `{{CREATED_AT}}`         | `date -u +%Y-%m-%dT%H:%M:%SZ`           |
| `{{OWNER}}`              | `git config user.email` or user prompt  |
| `{{PRIMARY_PROJECT}}`    | `~/.ai/projects.yaml` alias             |
| `{{TREE_DOMAIN_OR_NULL}}`| user prompt; may be null                |
| `{{DOMAIN}}`             | tree path                               |
| `{{LEAF_SLUG}}`          | derived from leaf title                 |
| `{{THREAD_SLUG}}`        | thread frontmatter `id`                 |
| `{{ROUND_NUM}}`          | next unused round number under `debate/`|
| `{{PROJECT_TITLE}}`      | user prompt at `init-project-brain`     |
| `{{DOMAIN_TAXONOMY}}`    | list from user at `init-project-brain`, per § 10.1 |

Skills that substitute placeholders must:

1. Fail closed — if a required placeholder cannot be resolved, the skill refuses and reports the missing input.
2. Preserve unknown placeholders verbatim — templates may evolve faster than skills.

## Adding new templates

When a new skill needs a template that doesn't exist:

1. Add the template here with placeholders.
2. Add the skill's `assets/<template>` row to its SKILL.md § Asset dependencies (see `skill-contract-template.md`).
3. Register placeholders in the table above.
