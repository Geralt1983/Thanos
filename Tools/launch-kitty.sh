#!/bin/bash
# Launch Kitty with remote control explicitly enabled
# This ensures wallpaper system works on macOS

# Kill existing Kitty instances (optional - comment out if you want)
# pkill -9 kitty

# Launch Kitty with remote control enabled
/opt/homebrew/bin/kitty \
  --listen-on=unix:/tmp/kitty-${USER} \
  -o allow_remote_control=yes \
  &

echo "Kitty launched with remote control enabled"
echo "Socket: /tmp/kitty-${USER}"
