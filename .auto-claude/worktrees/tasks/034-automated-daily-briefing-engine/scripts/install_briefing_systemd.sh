#!/usr/bin/env bash
#
# install_briefing_systemd.sh
#
# Installs the Briefing Scheduler as a systemd user service with timer.
# The timer triggers the service at configured intervals.
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}=== Briefing Scheduler - Systemd Installation ===${NC}\n"

# Function to print colored messages
print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_error "systemd is only available on Linux"
    echo "For macOS, use the cron installation: ./scripts/install_briefing_cron.sh"
    exit 1
fi

# Check if systemd is available
if ! command -v systemctl &> /dev/null; then
    print_error "systemctl is not available"
    echo "This system does not appear to use systemd."
    echo "Try the cron installation instead: ./scripts/install_briefing_cron.sh"
    exit 1
fi

# Step 1: Validate Python installation
print_info "Validating Python installation..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7 or higher and try again."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_PATH=$(which python3)

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"; then
    print_error "Python version $PYTHON_VERSION is too old"
    echo "Python 3.7 or higher is required."
    exit 1
fi

print_success "Python $PYTHON_VERSION detected at $PYTHON_PATH"

# Step 2: Check project structure
print_info "Validating project structure..."

REQUIRED_PATHS=(
    "$PROJECT_ROOT/Tools/briefing_scheduler.py"
    "$PROJECT_ROOT/Tools/briefing_engine.py"
    "$PROJECT_ROOT/config/briefing_schedule.json"
    "$PROJECT_ROOT/State"
    "$PROJECT_ROOT/Templates"
)

for path in "${REQUIRED_PATHS[@]}"; do
    if [[ ! -e "$path" ]]; then
        print_error "Required file/directory not found: $path"
        echo "Please ensure you're running this from the correct project directory."
        exit 1
    fi
done

print_success "Project structure validated"

# Step 3: Check optional dependencies
print_info "Checking optional dependencies..."

if python3 -c "import jinja2" 2>/dev/null; then
    print_success "Jinja2 is installed (template rendering will work)"
else
    print_warning "Jinja2 is not installed (templates will be skipped)"
    echo "  To enable template rendering: pip3 install jinja2"
fi

# Step 4: Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"
print_success "Logs directory created/verified"

# Step 5: Test the scheduler can be imported
print_info "Testing scheduler import..."

if ! python3 -c "import sys; sys.path.insert(0, '$PROJECT_ROOT'); from Tools.briefing_scheduler import BriefingScheduler" 2>/dev/null; then
    print_error "Failed to import BriefingScheduler"
    echo "There may be dependency issues. Please check:"
    echo "  cd $PROJECT_ROOT"
    echo "  python3 -c 'from Tools.briefing_scheduler import BriefingScheduler'"
    exit 1
fi

print_success "Scheduler import successful"

# Step 6: Create systemd user directory
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"
print_success "Systemd user directory created/verified"

# Step 7: Create systemd service file
print_info "Creating systemd service file..."

SERVICE_FILE="$SYSTEMD_USER_DIR/briefing-scheduler.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Thanos Briefing Scheduler
Documentation=file://$PROJECT_ROOT/docs/SCHEDULER_GUIDE.md
After=network.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PYTHON_PATH -m Tools.briefing_scheduler --mode once
StandardOutput=append:$PROJECT_ROOT/logs/briefing_scheduler.log
StandardError=append:$PROJECT_ROOT/logs/briefing_scheduler.log

# Restart on failure
Restart=on-failure
RestartSec=60

[Install]
WantedBy=default.target
EOF

print_success "Service file created: $SERVICE_FILE"

# Step 8: Create systemd timer file
print_info "Creating systemd timer file..."

TIMER_FILE="$SYSTEMD_USER_DIR/briefing-scheduler.timer"

cat > "$TIMER_FILE" << EOF
[Unit]
Description=Thanos Briefing Scheduler Timer
Documentation=file://$PROJECT_ROOT/docs/SCHEDULER_GUIDE.md
Requires=briefing-scheduler.service

[Timer]
# Run every minute
OnCalendar=*:0/1
# Run immediately if missed
Persistent=true
# Randomize start by up to 10 seconds to avoid load spikes
RandomizedDelaySec=10

[Install]
WantedBy=timers.target
EOF

print_success "Timer file created: $TIMER_FILE"

# Step 9: Reload systemd daemon
print_info "Reloading systemd daemon..."
systemctl --user daemon-reload
print_success "Systemd daemon reloaded"

# Step 10: Enable and start the timer
print_info "Enabling and starting timer..."

systemctl --user enable briefing-scheduler.timer
systemctl --user start briefing-scheduler.timer

print_success "Timer enabled and started"

# Step 11: Display installation summary
echo
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo
echo "The Briefing Scheduler is now installed as a systemd user service."
echo
echo "Configuration:"
echo "  Project root:   $PROJECT_ROOT"
echo "  Config file:    $PROJECT_ROOT/config/briefing_schedule.json"
echo "  Log file:       $PROJECT_ROOT/logs/briefing_scheduler.log"
echo "  Service file:   $SERVICE_FILE"
echo "  Timer file:     $TIMER_FILE"
echo
echo "The timer will trigger every minute to check if briefings are due."
echo "Edit $PROJECT_ROOT/config/briefing_schedule.json to configure times."
echo
echo "Useful commands:"
echo "  View timer status:       systemctl --user status briefing-scheduler.timer"
echo "  View service status:     systemctl --user status briefing-scheduler.service"
echo "  View logs:               journalctl --user -u briefing-scheduler.service -f"
echo "  View log file:           tail -f $PROJECT_ROOT/logs/briefing_scheduler.log"
echo "  Stop timer:              systemctl --user stop briefing-scheduler.timer"
echo "  Start timer:             systemctl --user start briefing-scheduler.timer"
echo "  Disable timer:           systemctl --user disable briefing-scheduler.timer"
echo "  Test manually:           systemctl --user start briefing-scheduler.service"
echo "  Uninstall:               ./scripts/uninstall_briefing.sh --systemd"
echo
print_warning "Note: The first briefing will run at the configured time(s) in the config file."
echo

# Display current timer status
print_info "Current timer status:"
systemctl --user list-timers briefing-scheduler.timer
