#!/bin/bash
# ============================================================================
# Thanos MCP Integration - Setup Script
# ============================================================================
# This script sets up MCP infrastructure for production deployment
# Run this script after cloning the repository and before first use
# ============================================================================

set -e  # Exit on error
# set -x  # Uncomment for debug output

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Thanos MCP Integration - Setup Script${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_success "$1 is installed"
        return 0
    else
        log_error "$1 is not installed"
        return 1
    fi
}

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================

echo -e "${BLUE}Step 1: Checking Prerequisites${NC}"
echo "---"

MISSING_DEPS=0

# Check Python
if check_command python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "Python version: $PYTHON_VERSION"
else
    MISSING_DEPS=1
fi

# Check Node.js (required for many MCP servers)
if check_command node; then
    NODE_VERSION=$(node --version)
    log_info "Node.js version: $NODE_VERSION"
else
    log_warning "Node.js not found. Required for WorkOS and third-party MCP servers."
    log_info "Install from: https://nodejs.org/"
    MISSING_DEPS=1
fi

# Check npm
if check_command npm; then
    NPM_VERSION=$(npm --version)
    log_info "npm version: $NPM_VERSION"
else
    log_warning "npm not found. Required for installing MCP server dependencies."
    MISSING_DEPS=1
fi

# Check npx
if check_command npx; then
    log_success "npx is available"
else
    log_warning "npx not found. Some MCP servers may not work."
fi

# Check git
if check_command git; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    log_info "Git version: $GIT_VERSION"
else
    log_warning "Git not found. May be needed for some server installations."
fi

echo ""

if [ $MISSING_DEPS -eq 1 ]; then
    log_error "Some prerequisites are missing. Please install them and run this script again."
    exit 1
fi

# ============================================================================
# Step 2: Setup Python Environment
# ============================================================================

echo -e "${BLUE}Step 2: Setting Up Python Environment${NC}"
echo "---"

cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    log_info "Creating Python virtual environment..."
    python3 -m venv .venv
    log_success "Virtual environment created"
else
    log_success "Virtual environment already exists"
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
log_info "Upgrading pip..."
python -m pip install --upgrade pip --quiet

# Install Python dependencies
log_info "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    log_success "Python dependencies installed"
else
    log_error "requirements.txt not found!"
    exit 1
fi

# Verify MCP SDK installation
log_info "Verifying MCP SDK installation..."
if python -c "import mcp" 2>/dev/null; then
    MCP_VERSION=$(python -c "import mcp; print(getattr(mcp, '__version__', 'unknown'))")
    log_success "MCP Python SDK installed (version: $MCP_VERSION)"
else
    log_error "MCP Python SDK not installed correctly"
    exit 1
fi

echo ""

# ============================================================================
# Step 3: Setup Configuration Files
# ============================================================================

echo -e "${BLUE}Step 3: Setting Up Configuration Files${NC}"
echo "---"

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        log_info "Creating .env from .env.example..."
        cp .env.example .env
        log_warning ".env file created. Please edit it with your actual credentials."
        log_warning "Required variables: ANTHROPIC_API_KEY, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, OPENAI_API_KEY"
    else
        log_error ".env.example not found. Cannot create .env file."
        exit 1
    fi
else
    log_success ".env file already exists"
fi

# Check for .mcp.json
if [ ! -f ".mcp.json" ]; then
    if [ -f ".mcp.json.example" ]; then
        log_info "Creating .mcp.json from .mcp.json.example..."
        cp .mcp.json.example .mcp.json
        log_success ".mcp.json file created"
    else
        log_warning ".mcp.json.example not found. Skipping MCP configuration."
    fi
else
    log_success ".mcp.json file already exists"
fi

# Check for ~/.claude.json (global config)
if [ -f "$HOME/.claude.json" ]; then
    log_info "Global MCP config found at ~/.claude.json"
else
    log_info "No global MCP config at ~/.claude.json (optional)"
fi

echo ""

# ============================================================================
# Step 4: Install WorkOS MCP Server
# ============================================================================

echo -e "${BLUE}Step 4: Installing WorkOS MCP Server${NC}"
echo "---"

WORKOS_PATH="$PROJECT_ROOT/mcp-servers/workos-mcp"

if [ -d "$WORKOS_PATH" ]; then
    log_info "WorkOS MCP server directory found"

    cd "$WORKOS_PATH"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        log_info "Installing WorkOS MCP dependencies..."
        npm install --quiet
        log_success "Dependencies installed"
    else
        log_success "Dependencies already installed"
    fi

    # Build the server
    log_info "Building WorkOS MCP server..."
    if npm run build --quiet; then
        log_success "WorkOS MCP server built successfully"
    else
        log_error "Failed to build WorkOS MCP server"
        exit 1
    fi

    # Check if dist/index.js exists
    if [ -f "dist/index.js" ]; then
        log_success "WorkOS MCP server is ready at: $WORKOS_PATH/dist/index.js"
    else
        log_error "Build succeeded but dist/index.js not found"
        exit 1
    fi

    cd "$PROJECT_ROOT"
else
    log_warning "WorkOS MCP server not found at: $WORKOS_PATH"
    log_info "If you want to use WorkOS MCP server, clone it to: $WORKOS_PATH"
fi

echo ""

# ============================================================================
# Step 5: Install Third-Party MCP Servers (Optional)
# ============================================================================

echo -e "${BLUE}Step 5: Installing Third-Party MCP Servers (Optional)${NC}"
echo "---"

log_info "Third-party MCP servers are installed on-demand via npx"
log_info "The following servers are available:"
echo "  - @modelcontextprotocol/server-sequential-thinking"
echo "  - @modelcontextprotocol/server-filesystem"
echo "  - @modelcontextprotocol/server-playwright"
echo "  - @modelcontextprotocol/server-fetch"
echo ""
log_info "They will be automatically installed when first used"

# Optional: Pre-install Playwright browsers
read -p "$(echo -e ${YELLOW}"Do you want to install Playwright browsers now? (y/N): "${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Installing Playwright browsers..."
    npx -y playwright install chromium
    log_success "Playwright browsers installed"
fi

echo ""

# ============================================================================
# Step 6: Validate Configuration
# ============================================================================

echo -e "${BLUE}Step 6: Validating Configuration${NC}"
echo "---"

log_info "Running configuration validation..."

if [ -f "$SCRIPT_DIR/validate-mcp-config.py" ]; then
    python "$SCRIPT_DIR/validate-mcp-config.py" || {
        log_error "Configuration validation failed"
        log_info "Please review the errors above and fix your configuration"
        exit 1
    }
else
    log_warning "validate-mcp-config.py not found. Skipping validation."
fi

echo ""

# ============================================================================
# Step 7: Test MCP Integration
# ============================================================================

echo -e "${BLUE}Step 7: Testing MCP Integration${NC}"
echo "---"

log_info "Testing MCP imports..."

python -c "
from Tools.adapters import get_default_manager
import asyncio

async def test_mcp():
    try:
        manager = await get_default_manager(enable_mcp=False)
        print('✓ AdapterManager imports successfully')
        return True
    except Exception as e:
        print(f'✗ Error importing AdapterManager: {e}')
        return False

result = asyncio.run(test_mcp())
exit(0 if result else 1)
" && log_success "MCP integration test passed" || log_error "MCP integration test failed"

echo ""

# ============================================================================
# Setup Complete
# ============================================================================

echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Edit .env file with your actual credentials:"
echo "   ${YELLOW}nano .env${NC}"
echo ""
echo "2. Edit .mcp.json to enable desired MCP servers:"
echo "   ${YELLOW}nano .mcp.json${NC}"
echo ""
echo "3. Run configuration validation:"
echo "   ${YELLOW}./scripts/validate-mcp-config.py${NC}"
echo ""
echo "4. Test MCP server connection:"
echo "   ${YELLOW}python -c 'from Tools.adapters import get_default_manager; import asyncio; asyncio.run(get_default_manager(enable_mcp=True))'${NC}"
echo ""
echo "5. Review documentation:"
echo "   - ${BLUE}docs/deployment-guide.md${NC} - Production deployment guide"
echo "   - ${BLUE}docs/mcp-integration-guide.md${NC} - MCP integration guide"
echo "   - ${BLUE}docs/third-party-mcp-servers.md${NC} - Third-party servers guide"
echo ""
echo -e "${GREEN}For help and troubleshooting, see docs/deployment-guide.md${NC}"
echo ""
