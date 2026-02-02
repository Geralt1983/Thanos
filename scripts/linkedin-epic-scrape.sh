#!/bin/bash
# LinkedIn Epic Contract Scraper
# Uses OpenClaw browser automation - no npm required

set -e

SEARCH_QUERY="Epic EHR contract"
OUTPUT_FILE="/tmp/linkedin-epic-posts.json"

echo "LinkedIn Epic scraper running at $(date)"
echo "Note: This script is triggered by OpenClaw cron, which handles the browser automation"
echo "See HEARTBEAT.md or cron job 'linkedin-epic-digest' for the actual workflow"
