#!/usr/bin/env bash
# Renamed — use scripts/migrate-brain-dir.sh instead.
#
# This file existed briefly under the old name when the rc4 rename was first
# drafted as a v2 release. The rename is now shipping inside the v1.0.0-rc4
# release; the real migration script is `scripts/migrate-brain-dir.sh`.
exec "$(dirname "$0")/migrate-brain-dir.sh" "$@"
