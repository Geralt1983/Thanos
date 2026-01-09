#!/bin/bash
# Setup script for Thanos Claude API Integration
# Run this once to configure direct API access

set -e

THANOS_DIR="${THANOS_DIR:-$HOME/Projects/Thanos}"
cd "$THANOS_DIR"

echo "🔧 Thanos API Setup"
echo "==================="

# Check Python version
echo "📦 Checking Python..."
python3 --version || { echo "❌ Python 3 required"; exit 1; }

# Check/install anthropic package
echo "📦 Checking Anthropic SDK..."
VENV_PYTHON="$HOME/.venv/bin/python"
if [ -f "$VENV_PYTHON" ] && $VENV_PYTHON -c "import anthropic" 2>/dev/null; then
    echo "✅ Anthropic SDK already installed in venv"
elif python3 -c "import anthropic" 2>/dev/null; then
    echo "✅ Anthropic SDK already installed"
else
    echo "Installing anthropic package..."
    if command -v uv &> /dev/null; then
        uv pip install anthropic
    else
        pip3 install --user anthropic || pip3 install anthropic
    fi
fi

# Create required directories
echo "📁 Creating directories..."
mkdir -p config State Memory/cache scripts

# Check for API key
echo ""
echo "🔑 API Key Configuration"
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY not set in environment"
    echo ""
    echo "To set your API key, add to your shell config (~/.zshrc or ~/.bashrc):"
    echo ""
    echo '  export ANTHROPIC_API_KEY="your-api-key-here"'
    echo ""
    echo "Get your API key from: https://console.anthropic.com/settings/keys"
    echo ""
    read -p "Enter your API key now (or press Enter to skip): " api_key
    if [ -n "$api_key" ]; then
        # Add to current session
        export ANTHROPIC_API_KEY="$api_key"

        # Offer to add to shell config
        echo ""
        read -p "Add to ~/.zshrc for persistence? (y/n): " add_to_rc
        if [ "$add_to_rc" = "y" ]; then
            echo "" >> ~/.zshrc
            echo "# Anthropic API Key for Thanos" >> ~/.zshrc
            echo "export ANTHROPIC_API_KEY=\"$api_key\"" >> ~/.zshrc
            echo "✅ Added to ~/.zshrc"
        fi
    fi
else
    echo "✅ ANTHROPIC_API_KEY is set"
fi

# Verify config file exists
echo ""
echo "📋 Checking configuration..."
if [ -f "config/api.json" ]; then
    echo "✅ config/api.json exists"
else
    echo "⚠️  config/api.json not found - creating default..."
    cat > config/api.json << 'EOF'
{
  "anthropic": {
    "api_key_env": "ANTHROPIC_API_KEY",
    "default_model": "claude-opus-4.5",
    "fallback_model": "claude-3-5-sonnet-20241022",
    "max_tokens": 4096,
    "temperature": 1.0,
    "timeout": 600,
    "max_retries": 3,
    "retry_delay": 1.0
  },
  "usage_tracking": {
    "enabled": true,
    "storage_path": "State/usage.json",
    "alert_threshold": 100000
  },
  "caching": {
    "enabled": true,
    "ttl_seconds": 3600,
    "storage_path": "Memory/cache/"
  }
}
EOF
    echo "✅ Created config/api.json"
fi

# Initialize usage tracking file
echo ""
echo "📊 Initializing usage tracking..."
if [ ! -f "State/usage.json" ]; then
    cat > State/usage.json << 'EOF'
{
  "sessions": [],
  "daily_totals": {},
  "last_updated": null
}
EOF
    echo "✅ Created State/usage.json"
else
    echo "✅ State/usage.json exists"
fi

# Test API connection
echo ""
echo "🧪 Testing API connection..."
if [ -n "$ANTHROPIC_API_KEY" ]; then
    if python3 Tools/claude_api_client.py test 2>/dev/null; then
        echo "✅ API connection successful!"
    else
        echo "⚠️  API test failed - check your API key and try again"
    fi
else
    echo "⚠️  Skipping test - API key not set"
fi

echo ""
echo "==================="
echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  from Tools.claude_api_client import init_client, claude_client"
echo "  client = init_client()"
echo "  response = client.chat('Hello!')"
echo ""
echo "Check usage: python3 Tools/claude_api_client.py usage"
