#!/usr/bin/env python3
"""analyze-cycles.py — measure tool-call cost per skill invocation from a Cowork session log.

Reads a Claude Code / Cowork JSONL session transcript (typically at
~/.claude/projects/<host>/<session-id>.jsonl), identifies user turns that
invoked a project-brain skill (via slash command or natural-language match),
counts the tool calls between that user message and the next user message,
and emits a per-skill breakdown.

Diagnostic tool, not a user-facing skill. Use to ground bug #3 ("wasted
LLM cycles") with measurement instead of speculation.

Usage:
    python3 scripts/diagnostics/analyze-cycles.py <path-to-session.jsonl>

Output:
    Per-skill table with:
      - invocation count
      - average total tool calls per invocation
      - breakdown by tool type (bash, Read, AskUserQuestion, Edit, etc.)
      - sample tool-call sequences (the actual order of calls per invocation)

What to look for:
    - Skills with avg tool-call count > 1.5 — likely have speculative pre-script
      reads or multi-bash patterns.
    - Skills with non-zero AskUserQuestion average — the LLM is hedging when
      it could derive from context.
    - Skills with non-zero Read average — the LLM is reading files before
      invoking the script when the script could have done it itself.

Limits:
    - Only catches slash-command invocations and a few natural-language
      patterns. Pure natural-language skill invocations ("start a thread on
      X") may not be classified to the right skill.
    - The "tool calls per invocation" count is from user-message to next
      user-message, which can include LLM follow-up commentary tools that
      aren't strictly part of the skill's hot path.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Slash-command pattern. Matches either:
#   1. A <command-name>/project-brain:<skill></command-name> tag (Cowork
#      wraps slash commands in this; previous classifier version was being
#      thrown by the leading "/" in the closing </command-message> tag).
#   2. A bare "/project-brain:<skill>" or "/<skill>" elsewhere in prose.
COMMAND_TAG_RE = re.compile(
    r"<command-name>/(?:project-brain:)?([a-z][a-z0-9-]+)</command-name>"
)
SLASH_RE = re.compile(r"(?:^|\s)/(?:project-brain:)?([a-z][a-z0-9-]+)\b")

# Natural-language skill signals (rough — used only when slash command is absent).
NL_SKILL_HINTS = {
    "init-project-brain": [r"\binit project[- ]?brain\b", r"\bset up project[- ]?brain\b",
                           r"\bscaffold (a |the )?(project[- ]?brain|brain)\b"],
    "new-thread": [r"\bnew thread\b", r"\bstart a thread\b", r"\bcapture (an? )?(idea|thought)\b"],
    "record-artifact": [r"\blog (this|that|to)\b", r"\brecord (an? )?artifact\b",
                        r"\bappend to transcript\b", r"\battach (this|that)\b"],
    "review-thread": [r"\breview (the |this )?thread\b", r"\bshow (me )?the transcript\b",
                      r"\bwhat'?s in (this )?thread\b"],
    "discover-threads": [r"\bdiscover threads\b", r"\bwhat threads\b",
                         r"\b(stale|parked|active) threads\b"],
    "update-thread": [r"\bupdate (the )?thread\b", r"\b(bump|lock) maturity\b",
                      r"\b(add|remove|rename) (a )?candidate\b"],
    "park-thread": [r"\bpark (this|the) thread\b", r"\bpause (this|that) thread\b"],
    "discard-thread": [r"\bdiscard (this|the) thread\b", r"\barchive (this|the) thread\b"],
    "restore-thread": [r"\brestore (this|the) thread\b", r"\bunarchive\b"],
    "promote-thread-to-tree": [r"\bpromote (this|the) thread\b", r"\bland (the )?(decision|leaf)\b"],
    "verify-tree": [r"\bverify (the )?(tree|brain)\b", r"\bvalidate (the )?(tree|brain)\b"],
    "multi-agent-debate": [r"\b(run|do) (a )?(multi[- ]?agent )?debate\b"],
}
NL_SKILL_PATTERNS = {
    skill: [re.compile(p, re.I) for p in pats]
    for skill, pats in NL_SKILL_HINTS.items()
}


def classify_user_turn(text: str) -> str | None:
    """Return the skill name if the user message looks like a skill invocation, else None."""
    if not text:
        return None
    # 1. Cowork's <command-name> tag — most reliable, exact slash invocation.
    m = COMMAND_TAG_RE.search(text)
    if m:
        cand = m.group(1)
        if cand in NL_SKILL_HINTS:
            return cand
        if cand == "init":
            return "init-project-brain"
    # 2. Bare slash command in prose (anchored to start-of-string or whitespace
    #    so we don't capture closing XML tags like </command-message>).
    m = SLASH_RE.search(text)
    if m:
        cand = m.group(1)
        if cand in NL_SKILL_HINTS or cand == "init-project-brain":
            return cand
        if cand == "init":
            return "init-project-brain"
    # 3. Natural-language hints — loosest, only used when no slash signal at all.
    for skill, patterns in NL_SKILL_PATTERNS.items():
        for p in patterns:
            if p.search(text):
                return skill
    return None


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    log_path = Path(argv[1])
    if not log_path.is_file():
        print(f"error: not a file: {log_path}", file=sys.stderr)
        return 2

    # Walk the JSONL, group into user-turns with their following tool calls.
    turns = []  # list of (user_msg_text, [tool_call_names])
    current_user_msg: str | None = None
    current_tools: list[str] = []

    with log_path.open() as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            evt_type = d.get("type")
            if evt_type == "user":
                msg = d.get("message", {})
                content = msg.get("content")
                # tool_result events also have type=user; skip those.
                if not isinstance(content, str):
                    continue
                # Save previous turn, start new
                if current_user_msg is not None:
                    turns.append((current_user_msg, current_tools))
                current_user_msg = content
                current_tools = []
            elif evt_type == "assistant":
                if current_user_msg is None:
                    continue
                msg = d.get("message", {})
                content = msg.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            current_tools.append(item.get("name", "?"))
        # Final turn
        if current_user_msg is not None:
            turns.append((current_user_msg, current_tools))

    # Bucket by classified skill
    skill_invocations: dict[str, list[list[str]]] = defaultdict(list)
    unclassified_count = 0
    for user_msg, tools in turns:
        skill = classify_user_turn(user_msg)
        if skill:
            skill_invocations[skill].append(tools)
        else:
            unclassified_count += 1

    # Render
    print(f"=== Cycle analysis from {log_path.name} ===")
    print(f"Total user turns: {len(turns)}")
    print(f"Skill-classified: {sum(len(v) for v in skill_invocations.values())}")
    print(f"Unclassified:     {unclassified_count}")
    print()

    if not skill_invocations:
        print("(no skill invocations detected)")
        return 0

    # Per-skill summary
    print(f"{'skill':<28} {'invocations':>11} {'avg tools':>10} {'bash':>5} {'Read':>5} {'Edit':>5} {'Write':>5} {'Ask':>4} {'other':>5}")
    print("-" * 90)
    rows = []
    for skill, seqs in sorted(skill_invocations.items()):
        n = len(seqs)
        all_tools = [t for s in seqs for t in s]
        total = len(all_tools)
        avg = total / n if n else 0.0
        c = Counter(all_tools)
        bash_n = c.get("mcp__workspace__bash", 0) + c.get("Bash", 0)
        read_n = c.get("Read", 0)
        edit_n = c.get("Edit", 0)
        write_n = c.get("Write", 0)
        ask_n = c.get("AskUserQuestion", 0)
        other_n = total - bash_n - read_n - edit_n - write_n - ask_n
        rows.append((skill, n, avg, bash_n, read_n, edit_n, write_n, ask_n, other_n))
        print(f"{skill:<28} {n:>11} {avg:>10.2f} {bash_n/n:>5.2f} {read_n/n:>5.2f} {edit_n/n:>5.2f} {write_n/n:>5.2f} {ask_n/n:>4.2f} {other_n/n:>5.2f}")

    # Sample sequences (the most expensive 1-2 invocations per skill)
    print()
    print("=== sample tool-call sequences (most expensive 2 invocations per skill) ===")
    for skill, seqs in sorted(skill_invocations.items()):
        ordered = sorted(seqs, key=len, reverse=True)[:2]
        if not any(s for s in ordered):
            continue
        print(f"\n{skill}:")
        for i, seq in enumerate(ordered, 1):
            if not seq:
                print(f"  invocation {i}: (no tool calls — possibly answered from context only)")
                continue
            # Compress consecutive duplicates
            compressed = []
            last = None
            count = 0
            for t in seq:
                if t == last:
                    count += 1
                else:
                    if last is not None:
                        compressed.append(f"{last}{f'×{count}' if count > 1 else ''}")
                    last = t
                    count = 1
            if last is not None:
                compressed.append(f"{last}{f'×{count}' if count > 1 else ''}")
            print(f"  invocation {i} ({len(seq)} tools): {' → '.join(compressed)}")

    # Highlight overhead targets
    print()
    print("=== overhead targets (avg non-bash tools > 0.5) ===")
    overhead = [r for r in rows if (r[4] + r[5] + r[6] + r[7]) / r[1] > 0.5]
    if overhead:
        for skill, n, _, _, read_n, edit_n, write_n, ask_n, _ in overhead:
            extras = read_n + edit_n + write_n + ask_n
            print(f"  {skill}: {extras/n:.2f} non-bash tools per invocation "
                  f"(Read={read_n/n:.2f}, Edit={edit_n/n:.2f}, Write={write_n/n:.2f}, Ask={ask_n/n:.2f})")
    else:
        print("  (none — every classified skill is at or below 0.5 non-bash tools per invocation)")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
