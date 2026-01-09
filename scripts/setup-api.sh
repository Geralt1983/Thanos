#!/bin/bash
# Thanos API Setup Script
# Sets up the Python environment and configures the Anthropic API

set -e

THANOS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$THANOS_DIR"

echo "🔱 Thanos API Setup"
echo "==================="
echo ""

# 1. Create/verify virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
    echo "   ✅ Created .venv"
else
    echo "📦 Virtual environment exists"
fi

# 2. Activate and install dependencies
echo ""
echo "📚 Installing dependencies..."
source .venv/bin/activate
pip install --quiet anthropic
echo "   ✅ anthropic package installed"

# 3. Check for API key
echo ""
echo "🔑 API Key Configuration"

if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "   ✅ ANTHROPIC_API_KEY is set (${#ANTHROPIC_API_KEY} chars)"
else
    echo "   ⚠️  ANTHROPIC_API_KEY not found in environment"
    echo ""
    echo "   To set your API key, add this to your shell profile:"
    echo "   export ANTHROPIC_API_KEY='your-key-here'"
    echo ""
    echo "   Or create a .env file in this directory:"
    echo "   ANTHROPIC_API_KEY=your-key-here"

    # Prompt for key
    read -p "   Enter your Anthropic API key (or press Enter to skip): " api_key
    if [ -n "$api_key" ]; then
        echo "ANTHROPIC_API_KEY=$api_key" > .env
        echo "   ✅ Saved to .env file"
        export ANTHROPIC_API_KEY="$api_key"
    fi
fi

# 4. Test the connection
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "🧪 Testing API connection..."
    if python Tools/claude_api_client.py test 2>&1; then
        echo ""
        echo "✅ Setup complete! Thanos API is ready."
    else
        echo ""
        echo "❌ API test failed. Check your API key."
    fi
else
    echo ""
    echo "⏭️  Skipping API test (no key configured)"
    echo ""
    echo "To complete setup:"
    echo "  1. Set ANTHROPIC_API_KEY in your environment"
    echo "  2. Run: source .venv/bin/activate"
    echo "  3. Run: python Tools/claude_api_client.py test"
fi

echo ""
echo "📁 Quick Reference:"
echo "   Activate env:  source .venv/bin/activate"
echo "   Test API:      python Tools/claude_api_client.py test"
echo "   Check usage:   python Tools/claude_api_client.py usage"
echo "   Run Thanos:    python Tools/thanos_orchestrator.py"
