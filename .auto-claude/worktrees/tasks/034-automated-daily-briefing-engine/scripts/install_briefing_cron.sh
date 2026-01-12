#!/usr/bin/env bash
#
# install_briefing_cron.sh
#
# Installs the Briefing Scheduler as a cron job.
# The scheduler runs in "once" mode every minute to check if briefings are due.
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

echo -e "${BLUE}=== Briefing Scheduler - Cron Installation ===${NC}\n"

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

# Check if running on supported OS
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    print_error "Windows is not supported. Please use Windows Subsystem for Linux (WSL) or use systemd on Linux."
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
REQUIRED_VERSION="3.7"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"; then
    print_error "Python version $PYTHON_VERSION is too old"
    echo "Python 3.7 or higher is required."
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

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

# Step 6: Check if cron entry already exists
print_info "Checking for existing cron entries..."

CRON_COMMENT="# Thanos Briefing Scheduler"
CRON_COMMAND="* * * * * cd $PROJECT_ROOT && python3 -m Tools.briefing_scheduler --mode once >> $PROJECT_ROOT/logs/cron.log 2>&1"

# Get current crontab (may be empty)
CURRENT_CRONTAB=$(crontab -l 2>/dev/null || true)

if echo "$CURRENT_CRONTAB" | grep -q "briefing_scheduler"; then
    print_warning "Existing cron entry found"
    echo
    echo "Current cron entry:"
    echo "$CURRENT_CRONTAB" | grep -A1 "briefing_scheduler"
    echo
    read -p "Do you want to replace it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    # Remove old entries
    CURRENT_CRONTAB=$(echo "$CURRENT_CRONTAB" | grep -v "briefing_scheduler" || true)
fi

# Step 7: Add cron entry
print_info "Adding cron entry..."

# Add new entry
NEW_CRONTAB="${CURRENT_CRONTAB}
${CRON_COMMENT}
${CRON_COMMAND}
"

# Install new crontab
echo "$NEW_CRONTAB" | crontab -

print_success "Cron entry added successfully"

# Step 8: Display installation summary
echo
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo
echo "The Briefing Scheduler is now installed as a cron job."
echo
echo "Configuration:"
echo "  Project root: $PROJECT_ROOT"
echo "  Config file:  $PROJECT_ROOT/config/briefing_schedule.json"
echo "  Log file:     $PROJECT_ROOT/logs/briefing_scheduler.log"
echo "  Cron log:     $PROJECT_ROOT/logs/cron.log"
echo
echo "The scheduler will check every minute if briefings are due."
echo "Edit $PROJECT_ROOT/config/briefing_schedule.json to configure times."
echo
echo "Useful commands:"
echo "  View cron entries:       crontab -l"
echo "  View scheduler logs:     tail -f $PROJECT_ROOT/logs/briefing_scheduler.log"
echo "  View cron logs:          tail -f $PROJECT_ROOT/logs/cron.log"
echo "  Test manually:           cd $PROJECT_ROOT && python3 -m Tools.briefing_scheduler --mode once"
echo "  Uninstall:               ./scripts/uninstall_briefing.sh --cron"
echo
print_warning "Note: The first briefing will run at the configured time(s) in the config file."
