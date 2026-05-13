#!/usr/bin/env bash
# _plugin_root — host-neutral pack-root resolver.
#
# Sourced by any Layer-1 script that needs the pack root. Replaces hard-coded
# ${CLAUDE_PLUGIN_ROOT} (Cowork / Claude Code only) with a 4-tier resolver
# that works in any host.
#
# Resolution order (highest priority first):
#   1. --plugin-root=<abs-path> CLI flag passed to _plugin_root
#   2. $PROJECT_BRAIN_PACK_ROOT env var (host-neutral; canonical name)
#   3. $CLAUDE_PLUGIN_ROOT env var (Cowork / Claude Code legacy)
#   4. Auto-detect: walk up from the caller's BASH_SOURCE until a
#      CONVENTIONS.md + skills/ + scripts/ triplet is found
#
# Usage:
#   . "$(dirname "${BASH_SOURCE[0]}")/_plugin_root.sh"
#   PACK_ROOT="$(_plugin_root)" || exit 1
#
# Or with explicit override:
#   PACK_ROOT="$(_plugin_root --plugin-root=/some/abs/path)"

_plugin_root() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      --plugin-root=*) printf '%s\n' "${arg#--plugin-root=}"; return 0 ;;
    esac
  done

  if [ -n "${PROJECT_BRAIN_PACK_ROOT:-}" ]; then
    printf '%s\n' "$PROJECT_BRAIN_PACK_ROOT"
    return 0
  fi

  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    printf '%s\n' "$CLAUDE_PLUGIN_ROOT"
    return 0
  fi

  local here
  here="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" && pwd -P)"
  while [ "$here" != "/" ] && [ -n "$here" ]; do
    if [ -f "$here/CONVENTIONS.md" ] && [ -d "$here/skills" ] && [ -d "$here/scripts" ]; then
      printf '%s\n' "$here"
      return 0
    fi
    here="$(dirname "$here")"
  done

  echo "ERROR: cannot resolve pack root. Set PROJECT_BRAIN_PACK_ROOT or pass --plugin-root=<path>" >&2
  return 1
}
