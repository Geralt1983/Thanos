#!/usr/bin/env bash
#
# uninstall_briefing.sh
#
# Uninstalls the Briefing Scheduler from cron or systemd.
# Removes all traces of the installation.
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

echo -e "${BLUE}=== Briefing Scheduler - Uninstallation ===${NC}\n"

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

# Function to uninstall from cron
uninstall_cron() {
    print_info "Checking for cron entries..."

    # Get current crontab
    CURRENT_CRONTAB=$(crontab -l 2>/dev/null || true)

    if [ -z "$CURRENT_CRONTAB" ]; then
        print_warning "No crontab found - nothing to uninstall"
        return 0
    fi

    if ! echo "$CURRENT_CRONTAB" | grep -q "briefing_scheduler"; then
        print_warning "No Briefing Scheduler cron entry found"
        return 0
    fi

    # Remove entries related to briefing_scheduler
    NEW_CRONTAB=$(echo "$CURRENT_CRONTAB" | grep -v "briefing_scheduler" | grep -v "Thanos Briefing Scheduler" || true)

    # If crontab is now empty, remove it completely
    if [ -z "$NEW_CRONTAB" ] || [ "$NEW_CRONTAB" = $'\n' ]; then
        crontab -r 2>/dev/null || true
        print_success "Crontab removed (was empty after removing scheduler entry)"
    else
        echo "$NEW_CRONTAB" | crontab -
        print_success "Cron entry removed"
    fi
}

# Function to uninstall from systemd
uninstall_systemd() {
    print_info "Checking for systemd installation..."

    SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
    SERVICE_FILE="$SYSTEMD_USER_DIR/briefing-scheduler.service"
    TIMER_FILE="$SYSTEMD_USER_DIR/briefing-scheduler.timer"

    # Check if files exist
    if [[ ! -f "$SERVICE_FILE" ]] && [[ ! -f "$TIMER_FILE" ]]; then
        print_warning "No systemd installation found"
        return 0
    fi

    # Stop and disable timer if it exists
    if systemctl --user is-active briefing-scheduler.timer &>/dev/null; then
        print_info "Stopping timer..."
        systemctl --user stop briefing-scheduler.timer
        print_success "Timer stopped"
    fi

    if systemctl --user is-enabled briefing-scheduler.timer &>/dev/null; then
        print_info "Disabling timer..."
        systemctl --user disable briefing-scheduler.timer
        print_success "Timer disabled"
    fi

    # Stop service if running
    if systemctl --user is-active briefing-scheduler.service &>/dev/null; then
        print_info "Stopping service..."
        systemctl --user stop briefing-scheduler.service
        print_success "Service stopped"
    fi

    # Remove systemd files
    if [[ -f "$SERVICE_FILE" ]]; then
        rm -f "$SERVICE_FILE"
        print_success "Service file removed: $SERVICE_FILE"
    fi

    if [[ -f "$TIMER_FILE" ]]; then
        rm -f "$TIMER_FILE"
        print_success "Timer file removed: $TIMER_FILE"
    fi

    # Reload systemd daemon
    systemctl --user daemon-reload
    print_success "Systemd daemon reloaded"
}

# Parse arguments
UNINSTALL_CRON=false
UNINSTALL_SYSTEMD=false
UNINSTALL_ALL=false

if [ $# -eq 0 ]; then
    # No arguments - detect what's installed and uninstall it
    UNINSTALL_ALL=true
else
    for arg in "$@"; do
        case $arg in
            --cron)
                UNINSTALL_CRON=true
                ;;
            --systemd)
                UNINSTALL_SYSTEMD=true
                ;;
            --all)
                UNINSTALL_ALL=true
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Uninstalls the Briefing Scheduler from cron and/or systemd."
                echo
                echo "Options:"
                echo "  --cron       Uninstall from cron only"
                echo "  --systemd    Uninstall from systemd only"
                echo "  --all        Uninstall from both (default if no option specified)"
                echo "  --help, -h   Show this help message"
                echo
                echo "Examples:"
                echo "  $0                    # Uninstall from both cron and systemd"
                echo "  $0 --cron             # Uninstall from cron only"
                echo "  $0 --systemd          # Uninstall from systemd only"
                exit 0
                ;;
            *)
                print_error "Unknown option: $arg"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
fi

# Perform uninstallation
if [ "$UNINSTALL_ALL" = true ] || [ "$UNINSTALL_CRON" = true ]; then
    uninstall_cron
fi

if [ "$UNINSTALL_ALL" = true ] || [ "$UNINSTALL_SYSTEMD" = true ]; then
    if command -v systemctl &> /dev/null; then
        uninstall_systemd
    else
        if [ "$UNINSTALL_SYSTEMD" = true ]; then
            print_warning "systemctl not found - skipping systemd uninstallation"
        fi
    fi
fi

# Optional: Offer to remove log files and run state
echo
read -p "Do you want to remove log files and run state? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Remove run state
    RUN_STATE_FILE="$PROJECT_ROOT/State/.briefing_runs.json"
    if [[ -f "$RUN_STATE_FILE" ]]; then
        rm -f "$RUN_STATE_FILE"
        print_success "Run state removed: $RUN_STATE_FILE"
    fi

    # Remove log files
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        rm -f "$PROJECT_ROOT/logs/briefing_scheduler.log"
        rm -f "$PROJECT_ROOT/logs/cron.log"
        print_success "Log files removed"
    fi
else
    print_info "Log files and run state preserved"
fi

# Display completion message
echo
echo -e "${GREEN}=== Uninstallation Complete ===${NC}"
echo
echo "The Briefing Scheduler has been uninstalled."
echo
echo "Note: The configuration file and templates remain unchanged:"
echo "  Config:     $PROJECT_ROOT/config/briefing_schedule.json"
echo "  Templates:  $PROJECT_ROOT/Templates/"
echo "  State:      $PROJECT_ROOT/State/"
echo
echo "You can reinstall at any time using:"
echo "  Cron:     ./scripts/install_briefing_cron.sh"
echo "  Systemd:  ./scripts/install_briefing_systemd.sh"
echo
