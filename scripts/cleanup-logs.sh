#!/usr/bin/env bash
# cleanup-logs.sh — prune old OpenCode logs (plugin + core)

set -euo pipefail

LOG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/opencode"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

[[ -d "$LOG_DIR" ]] || exit 0

deleted_plugin=$(find "$LOG_DIR" -maxdepth 1 -name 'oh-my-opencode-slim.*.log' -mtime "+${RETENTION_DAYS}" -print -delete 2>/dev/null | wc -l)
deleted_core=0
if [[ -d "$LOG_DIR/log" ]]; then
  deleted_core=$(find "$LOG_DIR/log" -maxdepth 1 -type f -mtime "+${RETENTION_DAYS}" -print -delete 2>/dev/null | wc -l)
fi

if [[ "$deleted_plugin" -gt 0 || "$deleted_core" -gt 0 ]]; then
  echo "[$(date +%Y-%m-%dT%H:%M:%S)] cleanup-logs: removed plugin=$deleted_plugin core=$deleted_core (older than ${RETENTION_DAYS} days)"
fi
