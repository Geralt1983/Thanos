#!/bin/bash
# Wrapper for Oura morning readiness data
# Ensures a stable entry point for cron jobs

set -o pipefail

CLAUDE_SCRIPT="$HOME/.claude/Tools/oura-morning.sh"

if [ -x "$CLAUDE_SCRIPT" ]; then
  exec "$CLAUDE_SCRIPT"
fi

cat << JSON
{
  "available": false,
  "error": "oura-morning.sh not found in ~/.claude/Tools",
  "sleep_score": null,
  "readiness_score": null,
  "sleep_duration_hours": null,
  "recommendations": ["Oura script missing - check ~/.claude/Tools/oura-morning.sh"]
}
JSON
