# Security Policy

## Disclaimer

**This software is provided "as is", without warranty of any kind. Use it at your own risk.**

`project-brain` is pre-1.0 alpha software that orchestrates LLM agents to read and write files, open pull requests, and resolve third-party URIs on your behalf. The authors and contributors assume no responsibility and accept no liability for any direct, indirect, incidental, or consequential damages — including data loss, leaked secrets, corrupted trees, incorrect decisions, or downstream business loss — arising out of the use of this software. You are responsible for reviewing every change the pack produces before merge, for protecting your branches and credentials, and for auditing materialized context before it enters version control. The defense-in-depth mitigations documented below (envelope framing, path-traversal guards, secret-pattern scans) are mitigations, not guarantees. The legally operative terms are in the [LICENSE](LICENSE) (Apache License, Version 2.0); this paragraph is a plain-English summary and in any conflict the LICENSE controls.

## Supported versions

The v0.9.x series is the current supported branch. Pre-0.9 alpha releases (v0.1 through v0.8) are not maintained; users should upgrade to v0.9.0 or later for all security updates.

## Reporting a vulnerability

If you discover a security vulnerability, please email **security@project-brain.invalid** with:
- A clear description of the vulnerability and its impact.
- Steps to reproduce (if applicable).
- Proposed fix or mitigation (if you have one).

Do NOT open a public GitHub issue for security vulnerabilities. We will acknowledge your report within 5 business days and coordinate a fix with you before any public disclosure.

Note: Replace `security@project-brain.invalid` with the actual project contact before public release.

## Known threat surface

project-brain is a skill-based agent orchestration system designed for portable thinking and decision-tree management. The threat model differs from a typical library:

### Prompt injection via persona charters and soft_links content

Persona charters in `assets/persona-charters/` and soft_links content are free-form text that influence multi-agent debate. A malicious or compromised persona could attempt to manipulate debate outcomes or extract secrets.

**Mitigations:**
- `multi-agent-debate` wraps persona context in envelope framing to reduce injection surface.
- `materialize-context` applies envelope wrapping before rendering context to skills.
- A persona-charter linter (forthcoming) will flag suspicious patterns.
- This is defense-in-depth, not a guarantee. Personas remain free-form per project policy.

**Recommendation:** Review personas during PR review with the same scrutiny as code.

### Path traversal

Skills that accept `--artifact-path`, `--out`, or `--persist` flags (notably `debate`, `materialize-context`, and `promote`) must refuse paths outside the brain root.

**Validation:** `verify-tree` V-21 checks that all path references are within `thoughts/` and reports violations. Skills should fail fast if a user attempts `--artifact-path=../../sensitive-file.md`.

### Secret exfiltration via promotion

`promote-thread-to-tree` could leak secrets if a thread contains API keys or credentials in its notes. Similarly, `materialize-context --persist` could capture third-party secrets in the audit snapshot.

**Mitigations:**
- `promote-thread-to-tree` runs a secret-pattern precondition scan (regex for common secret formats) and refuses with an actionable file list.
- `--allow-secrets` is an expert escape hatch; it emits a loud warning and should be used only with human review.
- `materialize-context --persist` carries a privacy warning and requires explicit user confirmation.
- `--strict` mode escalates to refusal if MCP connectors are detected.

### Finalize races

`finalize-promotion` could be bypassed if a second promote PR lands between branch push and merge. The skill re-reads thread frontmatter at commit time and refuses if the PR already appears in `promoted_to`. It also verifies that the leaf's `status: in-review` on the merge commit (not the branch HEAD), preventing stale promotions.

### MCP connector content

`materialize-context --persist` with `mcp://` URIs writes third-party connector responses directly to the audit snapshot. A compromised connector or MITM could inject malicious content.

**Mitigations:**
- `--persist` carries a privacy warning.
- `--strict` mode refusal if MCP connectors are detected.
- Audit snapshots are version-controlled; changes are visible in PR diffs.

## What the pack does NOT defend against

Be explicit about boundaries:

- **Malicious SKILL.md content:** The pack assumes skills themselves are trusted. A compromised or hostile skill in the pack can do anything. Review PRs that modify or add skills.
- **Compromised git remote:** If the git remote is rewritten after a promote PR is opened, the pack cannot detect replay or history rewriting.
- **Attacker with commit access to thoughts/:** An actor with write access to the brain repo can modify threads, leaves, and promote decisions without the skill-chain constraints.
- **LLM jailbreaks:** Personas are free-form text. A sufficiently adversarial persona might cause an LLM to ignore envelope framing and behave unexpectedly. This is a general LLM safety problem, not specific to the pack.

## Defense-in-depth expected of users

- **PR review:** The pack is designed for review. Review skill changes, persona charters, and thread promotions in PRs before merging.
- **Gitignore sensitive audit artifacts:** If you don't want materialized context or audit logs in git, add `.context/` and `thoughts/.audit-log.jsonl` to `.gitignore`.
- **Branch protection and CODEOWNERS:** Wire CODEOWNERS + branch protection to enforce review policy. The pack's `review_requirement` frontmatter field is unenforced by design — it is advisory. Actual enforcement lives in git settings.
- **Audit snapshot review:** When `materialize-context --persist` is used, review the audit snapshot in the PR before merge. It may contain secrets, logs, or third-party data.

## Changelog

- **0.9.0-alpha.3:** Initial security policy. Path traversal checks in V-21. Secret pattern scanning in `promote-thread-to-tree`. Privacy warnings for `materialize-context --persist`.
