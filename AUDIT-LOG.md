# Audit-log specification

> Stub specification for v1.0. Not yet wired into mutating skills.

## Purpose

- Independent record of every mutation a skill performs.
- Complements git history (which records the outcome) with per-skill-invocation detail (which records the call: flags, user, exit status, paths touched).
- Enables retrospective analysis: "which threads did this reviewer debate last month?", "how often did finalize-promotion hit the concurrent-finalize guard?", "did anyone use --allow-secrets in the last 90 days?"

## Non-goals

- Not a replacement for git history.
- Not a distributed log — one JSONL file per brain root, tracked per project preference.
- Not a policy-enforcement mechanism — just a record.

## Location

`project-brain/.audit-log.jsonl` at the brain root. Tracked in git by default; project can `.gitignore` it if they prefer it ephemeral. Never rotated by the pack; projects that want rotation wire it externally.

## Format

One JSON object per line (JSONL). Fields:

- `schema_version` (int) — always `1` for v1.0. Break glass if v2 needs to change the shape.
- `ts` (string, ISO-8601 UTC) — invocation completion time.
- `skill` (string) — skill name, e.g. `promote-thread-to-tree`.
- `skill_version` (string) — skill SKILL.md version at invocation.
- `op` (string) — short operation tag the skill declares in its SKILL.md. Single skill can declare multiple ops (e.g. `park-thread` → `park` | `unpark`).
- `actor` (string) — whoever the skill resolved as the user (from `git config user.email`, frontmatter owner field, or CLI flag).
- `dry_run` (bool) — whether `--dry-run` was set.
- `exit` (int) — skill's exit code (0 success, 1 expected failure e.g. precondition failed, 2 unexpected error).
- `artifacts` (array of strings) — paths (relative to brain root) the skill touched. Empty on dry-run or pre-flight exit.
- `commit` (string | null) — git commit SHA the skill's writes were bundled into, if any. Null on dry-run, pre-flight exit, or no-write skills.
- `flags` (object) — the resolved flag map the skill ran with, redacted for secrets (values matching common secret patterns replaced with `***`).
- `details` (object, optional, skill-specific) — skill-defined extras (e.g. `finalize-promotion` includes `merged_pr_url`; `multi-agent-debate` includes `round_number`).

## Example entries

```jsonl
{"schema_version": 1, "ts": "2026-04-22T14:23:15Z", "skill": "new-thread", "skill_version": "0.2.0", "op": "create", "actor": "alice@example.com", "dry_run": false, "exit": 0, "artifacts": ["threads/qa-flow-redesign/thread.md", "thread-index.md", "current-state.md"], "commit": "a3c7f2e9d1b4c8a6", "flags": {"slug": "qa-flow-redesign"}, "details": {}}
{"schema_version": 1, "ts": "2026-04-22T15:07:42Z", "skill": "promote-thread-to-tree", "skill_version": "0.3.0", "op": "promote", "actor": "bob@example.com", "dry_run": false, "exit": 0, "artifacts": ["threads/qa-flow-redesign/tree-staging/ux/decision-flow.md", "tree/ux/decision-flow.md", "tree/ux/NODE.md", "threads/qa-flow-redesign/thread.md", "thread-index.md", "current-state.md"], "commit": "f5a2e8c1d9b4a7c3", "flags": {"thread_slug": "qa-flow-redesign", "allow_secrets": false}, "details": {"promoted_leaves": 1, "target_domain": "ux", "pr_url": "https://github.com/org/repo/pull/142"}}
{"schema_version": 1, "ts": "2026-04-22T16:12:33Z", "skill": "finalize-promotion", "skill_version": "0.2.0", "op": "finalize", "actor": "carol@example.com", "dry_run": false, "exit": 1, "artifacts": [], "commit": null, "flags": {"thread_slug": "qa-flow-redesign"}, "details": {"reason": "concurrent_finalize_guard_tripped", "pr_url": "https://github.com/org/repo/pull/142"}}
{"schema_version": 1, "ts": "2026-04-22T17:45:20Z", "skill": "assign-thread", "skill_version": "0.1.0", "op": "assign", "actor": "dave@example.com", "dry_run": true, "exit": 0, "artifacts": [], "commit": null, "flags": {"thread_slug": "qa-flow-redesign", "add": ["eve@example.com"]}, "details": {"new_assigned_to": ["eve@example.com"]}}
{"schema_version": 1, "ts": "2026-04-22T18:30:55Z", "skill": "multi-agent-debate", "skill_version": "0.3.0", "op": "debate", "actor": "frank@example.com", "dry_run": false, "exit": 0, "artifacts": ["tree/ux/decision-flow/debate/round-01/feedback-in.md", "tree/ux/decision-flow/debate/round-01/personas.yaml", "tree/ux/decision-flow/debate/round-01/tryouts/fresh-eyes.md", "tree/ux/decision-flow/debate/round-01/defender.md", "tree/ux/decision-flow/debate/index.md"], "commit": "b8e2f1a9c4d7e3c5", "flags": {"artifact_path": "tree/ux/decision-flow.md", "reviewers": 2}, "details": {"round_number": 1, "close_verdict": "open"}}
```

## Integration contract (for v1.0 implementation)

Each mutating skill, as its final post-commit step:

1. Reads `project-brain/.audit-log.jsonl` (creates empty if absent).
2. Appends ONE line — the whole JSON object, no pretty-printing, newline-terminated.
3. `fsync`s the file (best-effort) to survive crashes.
4. Optionally commits the updated file in the same commit as its other changes. Default: `.audit-log.jsonl` is excluded from the skill's automatic commit and the user decides whether to track it.

## Failure modes

- Audit-log write failure MUST NOT abort the skill's primary operation. Log a warning to stderr and continue.
- Secret redaction is best-effort. Users handling sensitive credentials should audit the log before committing.

## Projects that want enforcement

- Pre-commit hook that checks every commit modifying `project-brain/` has a corresponding audit-log append.
- CI job that verifies audit-log consistency (every `promote-thread-to-tree` entry has a matching merged PR, every `finalize-promotion` entry is after its `promote-thread-to-tree` entry, etc.).
- External log aggregator: `tail -f project-brain/.audit-log.jsonl | jq` or ship to Loki / Vector / Datadog.

## What this does NOT solve

- Cross-project audit (each project has its own log).
- Git history verification (commit SHA + PR URL already cover this).
- Skill-level signing (future enhancement; out of scope for v1.0).

## Implementation plan for v1.0

**In-scope skills for the initial rollout:**

- Write (8): `new-thread`, `update-thread`, `park-thread`, `discard-thread`, `promote-thread-to-tree`, `finalize-promotion`, `discard-promotion`, `assign-thread`.
- Augment (2): `multi-agent-debate` (debate rounds are writes), `materialize-context --persist` (persisting context is a write).

**Implementation pattern:**

- Shared helper at `scripts/audit-log.py` that accepts a JSON payload on stdin and appends to `project-brain/.audit-log.jsonl`. Each skill shells out to it.
- Schema versioning: `schema_version: 1` is the first field in every record; v2 breaks glass if needed.

## Open questions (document; do not answer)

1. **Secret redaction scope.** Do we redact the body of `flags` that includes `--persona="name:charter"` when the charter might contain sensitive project context? Current plan: no — charters are authored by the project team, not external, and live in `CONVENTIONS.md` § 10.2 already under version control. But if a charter does slip in a credential, the log's secret-pattern redaction may not catch it.

2. **Audit-log entries on skill refusal.** Should audit-log entries be emitted on skill refusal (precondition fail, exit 1)? Current plan: yes — a refusal is still a resolved invocation with interesting metadata (which precondition, which flags, which actor). Omitting failures would blind audit to access patterns and attack surface. The `exit: 1` field signals the distinction.

3. **Log file growth.** What is the right behavior when the log file grows beyond 100 MB? Current plan: no action by the pack; projects wire rotation externally (e.g. a `chore/rotate-audit-log` skill that gzips and moves the current log, then resets to empty). The pack keeps the log simple so external tools can easily parse and manipulate it.

4. **Skill-level signing.** Future v1.1 or v2.0 feature: HMAC-SHA256 or Ed25519 signatures per entry so users can cryptographically verify that an audit entry wasn't tampered with after the fact. Out of scope for v1.0 but reserve space in the spec (optional `signature` field).
