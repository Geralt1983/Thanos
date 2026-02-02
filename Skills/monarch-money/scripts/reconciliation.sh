#!/bin/bash
# Monarch Money Weekly Reconciliation Script
# Uses the TypeScript CLI which has the updated API endpoints

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "MONARCH MONEY - WEEKLY RECONCILIATION"
echo "Date: $(date '+%Y-%m-%d %H:%M')"
echo "=============================================="

# Navigate to CLI directory
cd "$CLI_DIR"

# Check auth
echo -e "\n${YELLOW}Checking authentication...${NC}"
if ! node dist/cli/index.js doctor 2>&1 | grep -q "session loaded"; then
    echo -e "${RED}Not authenticated. Please run: monarch-money auth login${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Authenticated${NC}"

# Get recent transactions
echo -e "\n${YELLOW}Fetching recent transactions...${NC}"
TRANSACTIONS=$(node dist/cli/index.js tx search --limit 50 --json 2>/dev/null || echo "[]")

# Count transactions
TX_COUNT=$(echo "$TRANSACTIONS" | jq 'length' 2>/dev/null || echo "0")
echo "Found $TX_COUNT transactions"

# Get categories for reference
echo -e "\n${YELLOW}Available categories for review:${NC}"
node dist/cli/index.js cat list 2>&1 | head -40

echo -e "\n=============================================="
echo "RECONCILIATION COMPLETE"
echo "=============================================="
echo ""
echo "To categorize a transaction:"
echo "  node dist/cli/index.js tx categorize <transaction_id> <category_id>"
echo ""
echo "To search by merchant:"
echo "  node dist/cli/index.js tx search --merchant 'Amazon'"
echo ""
