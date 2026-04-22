# Contributing to project-brain

## What this pack is

project-brain is a skill pack, not a product. It exports a portable set of fourteen skills that cooperate to move an idea from thread to decision tree. Conventions over configuration: CONVENTIONS.md is the single source of truth. Everything else — skill behavior, validator invariants, naming rules — follows from it. When you change something here, change CONVENTIONS.md first.

## How to propose a change

1. Fork the repo and create a feature branch.
2. Branch names follow CONVENTIONS § 11.4:
   - `chore/<description>` for hygiene, docs, or tooling.
   - `promote/<slug>` for thread promotions (reserved for the pack itself; other repos use this for publishing thoughts).
   - `feature/<description>` for new skills or substantial capability changes.
   - `fix/<description>` for bug fixes or invariant adjustments.
3. Make your changes, then open a PR to `main`.
4. All PRs must pass `verify-tree exit 0` (see Testing changes locally, below).

## The skill contract

Every SKILL.md in this pack has 12 sections:

1. Frontmatter (id, name, description, version, pack, requires)
2. When to invoke
3. Inputs
4. Preconditions
5. Process
6. Side effects
7. Outputs
8. Frontmatter flips
9. Postconditions
10. Failure modes
11. Related skills
12. Asset dependencies

When adding a new skill:
- Copy `skill-contract-template.md` to `skills/<slug>/SKILL.md`.
- Fill in all 12 sections.
- Ensure your preconditions and postconditions align with existing skills.
- Include a related-skills reference pointing back to skills that call you or whose outputs you depend on.

## The invariant contract

The `scripts/verify-tree.py` shim (delegating to the `scripts/verify_tree/` package) enforces invariants V-01 through V-21, defined in CONVENTIONS § 9. Each invariant addresses:

- Frontmatter consistency (V-01 through V-06).
- Lifecycle state validity (V-07 through V-10).
- Cross-references and soft_links resolution (V-11 through V-13).
- Promotion monotonicity and debate sequencing (V-14 through V-16).
- Naming and reserved-filename rules (V-17 through V-21).

If you add a schema field to CONVENTIONS § 3 or § 4, you usually need to add a corresponding V-NN invariant under `scripts/verify_tree/` (the appropriate `invariants_*.py` mixin, wired into `checker.check_all()`) to cover validation of that field.

## The naming contract

CONVENTIONS § 11 defines:
- **Slugs** (thread and leaf identifiers): lowercase, alphanumeric + hyphens, max 64 chars.
- **Reserved filenames**: `NODE.md`, `CONVENTIONS.md`, `thread-index.md`, `current-state.md` are case-sensitive and error if renamed.
- **Directory names**: slug format enforcement.
- **Branch names**: follow the patterns listed above.
- **PR titles**: `chore:`, `promote:`, `feature:`, `fix:` prefixes match branch convention.
- **Commit messages**: short present-tense description, optionally followed by motivation or rationale.

The validator (`verify-tree`) enforces reserved names as errors and slug style as warnings (upgradeable to errors with `--warnings-as-errors`).

## Testing changes locally

Before opening a PR:

1. Run `python3 scripts/verify-tree.py` at the pack root if the pack has a `thoughts/` directory (it may not during development).
2. If you're adding a skill or changing schema, create a minimal test project with the pack installed, add a few test threads to `thoughts/`, then run `verify-tree` on that project.
3. The skill's preconditions and postconditions should be testable: does my skill refuse correctly when preconditions aren't met? Does it invoke `verify-tree --rebuild-index` as its final step?

Exit code 0 is success. Non-zero means validation failed; fix violations and try again.

## What makes a good first contribution

- Small skill improvements (fixing typos in descriptions, clarifying process steps).
- Documentation fixes (README, CONVENTIONS, INSTALL.md).
- New persona charters in `assets/persona-charters/` for domain-specific debate templates.
- New V-NN invariants in `scripts/verify_tree/invariants_*.py` for existing schema fields that lack validation.

## What to discuss before writing code

Open an issue first if you're proposing:

- Schema changes (anything touching CONVENTIONS § 3, § 4, or § 9): describe your motivation and propose a changelog entry. Schema churn breaks existing projects, so we keep it minimal.
- New lifecycle states or state transitions.
- Changes to how the pack resolves addresses (e.g., the project alias registry format).

## Code of conduct

Be kind. File issues in good faith. Assume the other contributor is trying to help.

## Release process

Versions are defined in:
- CONVENTIONS.md frontmatter: `version` field (e.g., `0.9.0-alpha.3`).
- Appendix A of CONVENTIONS.md: changelog entry per release.

Use semantic versioning:
- Major.minor.patch for stable releases.
- Alpha/beta suffixes for in-progress work (e.g., `0.9.0-alpha.3`).

Skills version independently (see README "Versioning and status"). When you ship a new skill or update an existing one, bump its version in its SKILL.md frontmatter and note the change in CONVENTIONS Appendix A. Pack version changes only when multiple skills ship together or the schema changes.
