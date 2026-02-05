#!/bin/bash
# RAG CLI - Simple interface to OpenAI File Search
# Usage:
#   rag-cli.sh sync <notebook>         - Sync Drive folder to vector store
#   rag-cli.sh query <notebook> "question"  - Query the vector store
#   rag-cli.sh list                    - List all notebooks
#   rag-cli.sh status <notebook>       - Check notebook status

set -e

THANOS_ROOT="${THANOS_ROOT:-/Users/jeremy/Projects/Thanos}"
PYTHON="${THANOS_ROOT}/.venv/bin/python"
SCRIPT="${THANOS_ROOT}/Tools/openai_file_search.py"
ACCOUNT="jeremy@kimbleconsultancy.com"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "RAG CLI - OpenAI File Search Interface"
    echo ""
    echo "Usage:"
    echo "  rag sync <notebook>              Sync Google Drive to vector store"
    echo "  rag query <notebook> \"question\"  Query the vector store"
    echo "  rag list                         List all notebooks"
    echo "  rag upload <notebook> <file>     Upload a file to vector store"
    echo ""
    echo "Notebooks: orders_hod, versacare, drive_inbox, harry, ncdhhs_radiology"
    exit 1
}

cmd_sync() {
    local notebook="${1:-drive_inbox}"
    echo -e "${YELLOW}Syncing ${notebook} from Google Drive...${NC}"

    cd "$THANOS_ROOT"
    "$PYTHON" "$SCRIPT" sync-drive --key "$notebook" --account "$ACCOUNT" --ensure-folders

    echo -e "${GREEN}Sync complete for ${notebook}${NC}"
}

cmd_query() {
    local notebook="$1"
    local question="$2"

    if [ -z "$notebook" ] || [ -z "$question" ]; then
        echo -e "${RED}Error: Both notebook and question required${NC}"
        echo "Usage: rag query <notebook> \"your question\""
        exit 1
    fi

    cd "$THANOS_ROOT"
    "$PYTHON" "$SCRIPT" query --key "$notebook" --question "$question"
}

cmd_list() {
    cd "$THANOS_ROOT"
    "$PYTHON" "$SCRIPT" list
}

cmd_upload() {
    local notebook="$1"
    local file="$2"

    if [ -z "$notebook" ] || [ -z "$file" ]; then
        echo -e "${RED}Error: Both notebook and file required${NC}"
        echo "Usage: rag upload <notebook> <file>"
        exit 1
    fi

    cd "$THANOS_ROOT"
    "$PYTHON" "$SCRIPT" upload --key "$notebook" --path "$file"
    echo -e "${GREEN}Upload complete${NC}"
}

# Main command dispatch
case "${1:-}" in
    sync)
        cmd_sync "$2"
        ;;
    query|q)
        cmd_query "$2" "$3"
        ;;
    list|ls)
        cmd_list
        ;;
    upload)
        cmd_upload "$2" "$3"
        ;;
    *)
        usage
        ;;
esac
