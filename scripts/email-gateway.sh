#!/bin/bash
# Email Gateway for Thanos
# Checks for emails to jkimble1983+thanos@gmail.com and processes them

set -e

# Check for new unread emails with +thanos tag
EMAILS=$(gog gmail list --account jkimble1983@gmail.com --query "to:jkimble1983+thanos@gmail.com is:unread" --limit 5 --json 2>/dev/null || echo "[]")

if [ "$EMAILS" = "[]" ] || [ -z "$EMAILS" ]; then
    echo "No new Thanos emails"
    exit 0
fi

echo "$EMAILS"
