#!/bin/bash
# Setup gog (Google OAuth Go CLI) authentication for Drive access
# This only needs to be run ONCE - after that, tokens persist in keyring

set -e

ACCOUNT="jeremy@kimbleconsultancy.com"

echo "=== GOG Authentication Setup ==="
echo ""
echo "This will authorize your Google account for Drive access."
echo "After completing this ONCE, authentication will be automatic."
echo ""

# Check if gog is installed
if ! command -v gog &> /dev/null; then
    echo "ERROR: gog is not installed"
    echo "Install with: brew install ruvnet/tap/gog"
    exit 1
fi

# Check current auth status
echo "Current auth status:"
gog auth status
echo ""

# Check if account is already authorized
if gog auth list 2>&1 | grep -q "$ACCOUNT"; then
    echo "Account $ACCOUNT is already authorized!"
    echo "Testing Drive access..."
    gog drive ls --account "$ACCOUNT" --max 5 --json 2>&1 | head -20 || echo "Drive test failed - may need to reauthorize"
    exit 0
fi

echo "Account not found in keyring. Starting authorization..."
echo ""
echo "This will open a browser window. Log in with: $ACCOUNT"
echo "Grant access to Google Drive when prompted."
echo ""

# Run auth add - this opens browser for OAuth flow
gog auth add "$ACCOUNT"

# Verify
echo ""
echo "Verifying authentication..."
if gog auth list 2>&1 | grep -q "$ACCOUNT"; then
    echo "SUCCESS: Account $ACCOUNT authorized!"
    echo ""
    echo "Testing Drive access..."
    gog drive ls --account "$ACCOUNT" --max 3 --json 2>&1 | head -10
    echo ""
    echo "GOG auth setup complete. Drive sync should now work without re-authentication."
else
    echo "WARNING: Authorization may not have completed. Try running again."
    exit 1
fi
