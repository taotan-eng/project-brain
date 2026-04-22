---
id: {{LEAF_SLUG}}-impl
title: {{LEAF_TITLE}} — Implementation Spec
created_at: {{CREATED_AT}}
owner: {{OWNER}}
primary_project: {{PRIMARY_PROJECT}}
kind: impl-spec
source_leaf: {{LEAF_PATH}}
source_debate: {{DEBATE_PATH_OR_NULL}}
soft_links: []
status: draft
---

# {{LEAF_TITLE}} — Implementation Spec

This spec translates the decision at [`{{LEAF_PATH}}`](./) into buildable instructions for an AI agent or human engineer. It is derived via the `derive-impl-spec` skill and is kept in sync with the decision — if either drifts, re-run the skill.

This spec is **not** the decision doc. The decision answers *what* and *why*. This spec answers *how to construct it* and *how we know it works*.

---

## 1. Scope

Scope is the single most important section. Unclear scope is the #1 cause of AI-build drift.

### In

What this build delivers. One bullet per observable capability. Be concrete enough that a test could be written for each.

- <capability>
- <capability>

### Out

Explicitly excluded. Call these out whenever a reader of the decision doc might reasonably assume they are included.

- <excluded capability> — <why out>

### Deferred

Related work intentionally postponed, with a pointer to where it is tracked.

- <deferred item> — tracked at <tree-path or thread slug>

---

## 2. Interfaces

Concrete signatures an implementer writes against. Use the format that fits: type signatures, endpoints, schemas, CLI flags, file contracts, wire formats.

```<language>
<signature>
<signature>
```

For each interface, note:

- **Purpose** — one sentence.
- **Preconditions** — what must be true for this to be callable.
- **Postconditions** — what is guaranteed after a successful call.
- **Error modes** — tie to rejection codes, exception types, or status values defined in the decision doc.

---

## 3. Acceptance tests

Observable behaviors that prove the build works. Write these **before** the code; they are the contract.

Each test has:

- **Given** — setup state.
- **When** — action.
- **Then** — observable outcome.

Group tests by interface from § 2. Tag each test:

- `canary` — must pass first; if this fails, nothing else is meaningful.
- `core` — primary behaviors covered by § 1 (In).
- `edge` — edge-case coverage drawn from § 5.

Tests that cannot be automated are flagged `manual` and scheduled explicitly in § 4.

---

## 4. Build order

A topological build plan that keeps the system runnable at each step. Each step produces a running artifact — no step leaves the system broken for more than one commit.

1. **<step name>** — <incremental capability at this point; which canary/core tests pass>.
2. **<step name>** — <…>.
3. …

Flag any step that requires external coordination:

- Schema migrations.
- Third-party credentials or feature flags.
- Cross-team sequencing.

---

## 5. Known edge cases

Drawn from the debate log's `open-issues.md`, red-team tryouts, and historical bug patterns. Each entry notes its origin and whether § 3 covers it.

| Edge case | Source | Covered by |
|-----------|--------|------------|
| <case>    | `debate/round-03/open-issues.md#OI-3` | T-core-07 |
| <case>    | red-team round 4 | *not yet — add T-edge-12* |

Uncovered edge cases are either added to § 3 before construction begins, or explicitly deferred with a pointer to a follow-up thread.

---

## 6. Context refs

URI-typed pointers into material the builder should pull in via `materialize-context`. Uses the shared `soft_links` field (see CONVENTIONS.md § 5). Roles guide context budget — `spec` and `prior-decision` are read fully; `related-work` is skimmed; `external-reference` is fetched on demand.

Populate this list here in-section for readability, and mirror it into the top-of-file `soft_links` frontmatter so `verify-tree` can check resolution.

```yaml
- uri: {{LEAF_PATH}}
  role: spec
- uri: {{LEAF_PATH}}/debate/index.md
  role: prior-decision
- uri: <adjacent tree node>
  role: related-work
- uri: <upstream PR or doc URL>
  role: external-reference
```

Cite, do not duplicate. Do not paste decision text into this spec; link it. If the decision moves or is superseded, `verify-tree` will surface the broken ref.

---

## Derivation notes (remove before flipping status to `ready`)

Guidance for the author running `derive-impl-spec`:

- **Scope discipline.** If you cannot write a one-line acceptance test for an "In" bullet, it is too vague. Break it up or move it to Deferred.
- **Interfaces before internals.** § 2 is the external-facing contract. Internal module decomposition is an implementation detail — do not put it here; it belongs in the build thread.
- **Build order matters more than you think.** An AI builder given a flat list of work will interleave in ways that break the system. A topological order keeps each checkpoint meaningful.
- **Edge cases come from the debate, not imagination.** If there was no debate round (§ 7 of CONVENTIONS.md), be more conservative with scope and more paranoid with tests.
- **Context refs are load-bearing.** A builder that can't resolve its refs will reinvent and drift. Audit every ref resolves before flipping `status: ready`.
