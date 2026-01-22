#!/bin/bash
#
# Install Operator Daemon as macOS LaunchAgent
#
# This script installs the Operator daemon to run automatically on boot
# and restart on crash.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THANOS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_FILE="com.thanos.operator.plist"
LAUNCHAGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCHAGENT_DIR/$PLIST_FILE"

echo "==================================="
echo "Operator Daemon LaunchAgent Install"
echo "==================================="
echo ""
echo "Thanos Root: $THANOS_ROOT"
echo "LaunchAgent: $PLIST_PATH"
echo ""

# Check if Python exists
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found in PATH"
    exit 1
fi

PYTHON_PATH=$(which python3)
echo "Python: $PYTHON_PATH"

# Check if daemon exists
DAEMON_PATH="$THANOS_ROOT/Operator/daemon.py"
if [ ! -f "$DAEMON_PATH" ]; then
    echo "ERROR: daemon.py not found at $DAEMON_PATH"
    exit 1
fi

# Check if config exists
CONFIG_PATH="$THANOS_ROOT/Operator/config.yaml"
if [ ! -f "$CONFIG_PATH" ]; then
    echo "ERROR: config.yaml not found at $CONFIG_PATH"
    exit 1
fi

echo "Daemon: $DAEMON_PATH"
echo "Config: $CONFIG_PATH"
echo ""

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCHAGENT_DIR"

# Create plist file
echo "Creating plist file..."
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Service Identity -->
    <key>Label</key>
    <string>com.thanos.operator</string>

    <!-- Program to Run -->
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$DAEMON_PATH</string>
        <string>--config</string>
        <string>$CONFIG_PATH</string>
    </array>

    <!-- Environment Variables -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>THANOS_ROOT</key>
        <string>$THANOS_ROOT</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>

    <!-- Working Directory -->
    <key>WorkingDirectory</key>
    <string>$THANOS_ROOT</string>

    <!-- Auto-Start Configuration -->
    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>  <!-- Restart on crash -->
        <key>Crashed</key>
        <true/>
    </dict>

    <!-- Logging -->
    <key>StandardOutPath</key>
    <string>$THANOS_ROOT/logs/operator_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>$THANOS_ROOT/logs/operator_stderr.log</string>

    <!-- Resource Limits -->
    <key>ProcessType</key>
    <string>Background</string>

    <key>Nice</key>
    <integer>5</integer>  <!-- Lower priority than user processes -->

    <!-- Throttle -->
    <key>ThrottleInterval</key>
    <integer>60</integer>  <!-- Wait 60s before restart after crash -->
</dict>
</plist>
EOF

echo "✓ Created plist file"

# Unload existing agent if running
if launchctl list | grep -q com.thanos.operator; then
    echo "Unloading existing agent..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    echo "✓ Unloaded existing agent"
fi

# Load the agent
echo "Loading LaunchAgent..."
launchctl load "$PLIST_PATH"
echo "✓ Loaded LaunchAgent"

# Wait a moment for it to start
sleep 2

# Check if it's running
if launchctl list | grep -q com.thanos.operator; then
    echo ""
    echo "==================================="
    echo "✓ Installation successful!"
    echo "==================================="
    echo ""
    echo "Status:"
    launchctl list | grep com.thanos.operator
    echo ""
    echo "Commands:"
    echo "  Start:   launchctl start com.thanos.operator"
    echo "  Stop:    launchctl stop com.thanos.operator"
    echo "  Restart: launchctl stop com.thanos.operator && launchctl start com.thanos.operator"
    echo "  Status:  launchctl list | grep com.thanos.operator"
    echo ""
    echo "Logs:"
    echo "  stdout: tail -f $THANOS_ROOT/logs/operator_stdout.log"
    echo "  stderr: tail -f $THANOS_ROOT/logs/operator_stderr.log"
    echo "  main:   tail -f $THANOS_ROOT/logs/operator.log"
    echo ""
    echo "Uninstall:"
    echo "  launchctl unload $PLIST_PATH"
    echo "  rm $PLIST_PATH"
    echo ""
else
    echo ""
    echo "WARNING: LaunchAgent loaded but not running"
    echo "Check logs for errors:"
    echo "  tail -f $THANOS_ROOT/logs/operator_stderr.log"
    exit 1
fi
