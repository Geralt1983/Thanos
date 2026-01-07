#!/bin/bash
# Thanos Git Sync - Auto-commit and push state

set -e

THANOS_DIR="/Users/jeremy/.claude"
cd "$THANOS_DIR"

# Check if we have changes
if [[ -z $(git status -s) ]]; then
    exit 0  # No changes, nothing to sync
fi

# Commit with timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
git add State/ History/ Skills/ Context/ Inbox/ Memory/
git add CLAUDE.md COMMANDS.md FLAGS.md PRINCIPLES.md RULES.md
git add MCP.md PERSONAS.md ORCHESTRATOR.md MODES.md THANOS.md
git add -f .gitignore

# Create commit
git commit -m "Thanos sync: ${TIMESTAMP}" --quiet

# Push to remote (if configured)
if git remote get-url origin &>/dev/null; then
    git push origin main --quiet
fi

exit 0
