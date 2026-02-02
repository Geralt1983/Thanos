#!/bin/bash
# Thanos CLI Tools Restoration Script
# Generated: 2026-02-02
# Run with: bash scripts/restore-cli-tools.sh

set -e

echo "🔧 Thanos CLI Tools Restoration Script"
echo "======================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✓${NC} $1"; }
warning() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }
info() { echo -e "  $1"; }

# 1. Create python symlink
echo "1. Checking python symlink..."
if command -v python &> /dev/null; then
    success "python command already exists"
else
    if [ -f /opt/homebrew/bin/python3 ]; then
        ln -sf /opt/homebrew/bin/python3 /opt/homebrew/bin/python
        success "Created python -> python3 symlink"
    else
        warning "python3 not found at expected location"
    fi
fi
echo ""

# 2. Clean up broken miniconda
echo "2. Checking miniconda installation..."
if [ -d "$HOME/miniconda3" ]; then
    # Check if it's a broken installation (only _conda file)
    if [ ! -f "$HOME/miniconda3/bin/conda" ]; then
        echo "   Found broken miniconda installation"
        read -p "   Remove broken miniconda3? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$HOME/miniconda3"
            success "Removed broken miniconda3"
        else
            info "Skipped miniconda removal"
        fi
    else
        success "miniconda appears intact"
    fi
else
    success "No miniconda to clean up"
fi
echo ""

# 3. Fix uv tool symlinks
echo "3. Checking uv tools..."
if command -v uv &> /dev/null; then
    # Check if claude-code-tools symlinks are broken
    if [ -L "$HOME/.local/bin/env-safe" ] && [ ! -e "$HOME/.local/bin/env-safe" ]; then
        warning "Found broken symlinks in ~/.local/bin"
        echo "   Reinstalling claude-code-tools..."
        uv tool install claude-code-tools --force 2>/dev/null && success "Reinstalled claude-code-tools" || warning "Failed to reinstall"
    else
        success "uv tool symlinks appear OK"
    fi
else
    warning "uv not found - skipping tool check"
fi
echo ""

# 4. Verify key tools
echo "4. Verifying key tools..."
tools=("python3" "pip3" "node" "npm" "bun" "todoist" "uv" "claude")
for tool in "${tools[@]}"; do
    if command -v "$tool" &> /dev/null; then
        version=$($tool --version 2>/dev/null | head -1 || echo "installed")
        success "$tool: $version"
    else
        warning "$tool: NOT FOUND"
    fi
done
echo ""

# 5. Check Oura/Monarch status
echo "5. Checking Thanos integrations..."
if [ -f "$HOME/.oura-cache/oura-health.db" ]; then
    size=$(ls -lh "$HOME/.oura-cache/oura-health.db" | awk '{print $5}')
    success "Oura data cache: $size"
else
    warning "Oura data cache not found"
fi

if [ -d "$HOME/Projects/Thanos/skills/monarch-money" ]; then
    success "Monarch Money skill installed"
else
    warning "Monarch Money skill not found"
fi
echo ""

# 6. Environment check
echo "6. Environment variables..."
if [ -f "$HOME/Projects/Thanos/.env" ]; then
    source "$HOME/Projects/Thanos/.env" 2>/dev/null
    [ -n "$OURA_PERSONAL_ACCESS_TOKEN" ] && success "OURA_PERSONAL_ACCESS_TOKEN set" || warning "OURA_PERSONAL_ACCESS_TOKEN missing"
    [ -n "$TELEGRAM_BOT_TOKEN" ] && success "TELEGRAM_BOT_TOKEN set" || warning "TELEGRAM_BOT_TOKEN missing"
else
    warning ".env file not found"
fi
echo ""

# 7. Optional: Clean up .zshrc duplicates
echo "7. .zshrc cleanup..."
if [ -f "$HOME/.zshrc" ]; then
    duplicates=$(grep -c 'export PATH="\$HOME/bin:\$PATH"' "$HOME/.zshrc" 2>/dev/null || echo "0")
    if [ "$duplicates" -gt 1 ]; then
        warning "Found $duplicates duplicate PATH entries in .zshrc"
        info "Manual cleanup recommended"
    else
        success ".zshrc appears clean"
    fi
fi
echo ""

echo "======================================="
echo "Restoration complete!"
echo ""
echo "Next steps:"
echo "  - Run 'source ~/.zshrc' to reload shell"
echo "  - Oura data: Access via ~/.oura-cache/oura-health.db"
echo "  - Monarch: node skills/monarch-money/dist/cli/index.js"
echo "  - View full report: cat memory/system-diagnostic-2026-02-02.md"
