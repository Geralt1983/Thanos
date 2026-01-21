#!/usr/bin/env bash
#
# Tailscale Installation and Configuration Script for Thanos
#
# This script:
# - Installs Tailscale on macOS or Linux
# - Configures authentication and device naming
# - Sets up ACL policies for secure access
# - Configures firewall rules
# - Validates installation and connectivity
#
# Usage:
#   ./install_tailscale.sh [--hostname HOSTNAME] [--tags TAGS]
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THANOS_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$SCRIPT_DIR/config"
ACL_FILE="$CONFIG_DIR/tailscale-acl.json"
STATE_DIR="$THANOS_ROOT/State"

# Default values
DEFAULT_HOSTNAME="thanos-primary"
DEFAULT_TAGS="tag:thanos"
HOSTNAME="${1:-$DEFAULT_HOSTNAME}"
TAGS="${2:-$DEFAULT_TAGS}"

# Logging functions
log() {
    echo -e "${GREEN}[Thanos VPN]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[Warning]${NC} $*"
}

error() {
    echo -e "${RED}[Error]${NC} $*" >&2
}

success() {
    echo -e "${GREEN}[Success]${NC} $*"
}

info() {
    echo -e "${BLUE}[Info]${NC} $*"
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Check if Tailscale is already installed
check_tailscale_installed() {
    if command -v tailscale &> /dev/null; then
        return 0
    fi
    return 1
}

# Install Tailscale on macOS
install_tailscale_macos() {
    log "Installing Tailscale on macOS..."

    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        error "Homebrew is required but not installed"
        info "Install Homebrew from https://brew.sh"
        return 1
    fi

    # Install Tailscale
    if brew list tailscale &> /dev/null; then
        info "Tailscale already installed via Homebrew"
    else
        log "Installing Tailscale via Homebrew..."
        brew install tailscale
    fi

    # Start Tailscale service
    log "Starting Tailscale service..."
    sudo brew services start tailscale

    success "Tailscale installed on macOS"
    return 0
}

# Install Tailscale on Linux
install_tailscale_linux() {
    log "Installing Tailscale on Linux..."

    # Detect Linux distribution
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        DISTRO=$ID
    else
        error "Cannot detect Linux distribution"
        return 1
    fi

    case $DISTRO in
        ubuntu|debian)
            log "Installing on Debian/Ubuntu..."
            curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/focal.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
            curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/focal.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list
            sudo apt-get update
            sudo apt-get install -y tailscale
            ;;
        fedora|centos|rhel)
            log "Installing on Fedora/CentOS/RHEL..."
            sudo dnf config-manager --add-repo https://pkgs.tailscale.com/stable/fedora/tailscale.repo
            sudo dnf install -y tailscale
            ;;
        arch)
            log "Installing on Arch Linux..."
            sudo pacman -S --noconfirm tailscale
            ;;
        *)
            error "Unsupported Linux distribution: $DISTRO"
            info "Visit https://tailscale.com/download for manual installation"
            return 1
            ;;
    esac

    # Enable and start Tailscale service
    log "Enabling Tailscale service..."
    sudo systemctl enable --now tailscaled

    success "Tailscale installed on Linux"
    return 0
}

# Authenticate with Tailscale
authenticate_tailscale() {
    log "Authenticating with Tailscale..."

    # Check if already authenticated
    if tailscale status &> /dev/null; then
        info "Already authenticated with Tailscale"
        return 0
    fi

    # Bring Tailscale up with device naming and tags
    log "Bringing up Tailscale connection..."
    log "Hostname: $HOSTNAME"
    log "Tags: $TAGS"

    sudo tailscale up \
        --hostname="$HOSTNAME" \
        --advertise-tags="$TAGS" \
        --accept-dns \
        --ssh

    success "Tailscale authenticated successfully"

    # Display status
    info "Tailscale status:"
    tailscale status

    return 0
}

# Generate ACL policy template
generate_acl_template() {
    log "Generating ACL policy template..."

    mkdir -p "$CONFIG_DIR"

    # Check if ACL file already exists
    if [[ -f "$ACL_FILE" ]]; then
        warn "ACL policy file already exists: $ACL_FILE"
        read -p "Overwrite? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Skipping ACL generation"
            return 0
        fi
    fi

    # Create ACL policy
    cat > "$ACL_FILE" <<'EOF'
{
  "acls": [
    {
      "action": "accept",
      "comment": "Allow owner full access to Thanos services",
      "src": ["group:owner"],
      "dst": [
        "tag:thanos:7681",
        "tag:thanos:22"
      ]
    }
  ],
  "tagOwners": {
    "tag:thanos": ["YOUR-EMAIL@example.com"]
  },
  "hosts": {
    "thanos-primary": "100.64.1.10"
  },
  "ssh": [
    {
      "action": "accept",
      "src": ["group:owner"],
      "dst": ["tag:thanos"],
      "users": ["jeremy"]
    }
  ],
  "groups": {
    "group:owner": ["YOUR-EMAIL@example.com"]
  }
}
EOF

    success "ACL policy template created: $ACL_FILE"
    warn "IMPORTANT: Edit $ACL_FILE and replace YOUR-EMAIL@example.com with your actual Tailscale account email"

    return 0
}

# Configure firewall rules for macOS
configure_firewall_macos() {
    log "Configuring macOS firewall..."

    # Note: macOS firewall is application-based, not port-based like pf
    # We'll document the security model instead

    info "macOS Firewall Notes:"
    info "  - Tailscale creates a virtual network interface (utun)"
    info "  - Traffic over Tailscale is encrypted by default"
    info "  - ttyd should bind to Tailscale IP only (not 0.0.0.0)"
    info "  - Use macOS Firewall settings to allow Tailscale app"

    # Check if macOS firewall is enabled
    if sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate | grep -q "enabled"; then
        info "macOS firewall is enabled"
    else
        warn "macOS firewall is disabled - consider enabling for security"
    fi

    return 0
}

# Configure firewall rules for Linux
configure_firewall_linux() {
    log "Configuring Linux firewall..."

    # Detect firewall system
    if command -v ufw &> /dev/null; then
        log "Using UFW firewall..."

        # Allow Tailscale interface
        sudo ufw allow in on tailscale0

        # Allow specific ports only from Tailscale subnet
        sudo ufw allow from 100.64.0.0/10 to any port 7681 comment "ttyd web terminal"
        sudo ufw allow from 100.64.0.0/10 to any port 22 comment "SSH"

        success "UFW firewall configured"

    elif command -v firewall-cmd &> /dev/null; then
        log "Using firewalld..."

        # Add Tailscale interface to trusted zone
        sudo firewall-cmd --permanent --zone=trusted --add-interface=tailscale0

        # Allow ports from Tailscale subnet
        sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="100.64.0.0/10" port protocol="tcp" port="7681" accept'
        sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="100.64.0.0/10" port protocol="tcp" port="22" accept'

        sudo firewall-cmd --reload
        success "firewalld configured"

    else
        warn "No supported firewall detected (ufw or firewalld)"
        info "Manually configure firewall to allow:"
        info "  - Port 7681/tcp from 100.64.0.0/10 (ttyd)"
        info "  - Port 22/tcp from 100.64.0.0/10 (SSH)"
    fi

    return 0
}

# Validate installation
validate_installation() {
    log "Validating Tailscale installation..."

    # Check if tailscale command is available
    if ! command -v tailscale &> /dev/null; then
        error "Tailscale command not found in PATH"
        return 1
    fi

    # Check if Tailscale is running
    if ! tailscale status &> /dev/null; then
        error "Tailscale is not running"
        return 1
    fi

    # Get Tailscale status
    local status_output
    status_output=$(tailscale status 2>&1)

    # Check for backend state
    if echo "$status_output" | grep -q "stopped\|logged out"; then
        error "Tailscale is not connected"
        info "Run: sudo tailscale up"
        return 1
    fi

    # Get IP address
    local tailscale_ip
    tailscale_ip=$(tailscale ip -4 2>/dev/null | head -n1)

    if [[ -z "$tailscale_ip" ]]; then
        error "Could not get Tailscale IP address"
        return 1
    fi

    success "Tailscale validation passed"
    info "Tailscale IP: $tailscale_ip"

    # Save installation info to state
    mkdir -p "$STATE_DIR"
    cat > "$STATE_DIR/tailscale_install.json" <<EOF
{
  "installed_at": "$(date -Iseconds)",
  "hostname": "$HOSTNAME",
  "tags": "$TAGS",
  "tailscale_ip": "$tailscale_ip",
  "os": "$(detect_os)",
  "version": "$(tailscale version 2>/dev/null | head -n1 || echo 'unknown')"
}
EOF

    return 0
}

# Display access instructions
show_access_instructions() {
    local tailscale_ip
    tailscale_ip=$(tailscale ip -4 2>/dev/null | head -n1)

    log "Tailscale Installation Complete!"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Thanos Remote Access via Tailscale"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo "Device Information:"
    echo "  Hostname: $HOSTNAME"
    echo "  Tailscale IP: $tailscale_ip"
    echo "  Tags: $TAGS"
    echo
    echo "Access Methods:"
    echo "  Web Terminal: https://$tailscale_ip:443/"
    echo "  SSH: ssh jeremy@$tailscale_ip"
    echo
    echo "Next Steps:"
    echo "  1. Install Tailscale on your mobile device/laptop"
    echo "  2. Log in with the same Tailscale account"
    echo "  3. Edit ACL policy: $ACL_FILE"
    echo "  4. Apply ACL policy in Tailscale admin console"
    echo "  5. Start ttyd: ./Access/thanos-web start"
    echo "  6. Access from any device on your Tailscale network"
    echo
    echo "Security Notes:"
    echo "  ✓ Zero-trust encryption (WireGuard)"
    echo "  ✓ No public internet exposure"
    echo "  ✓ Device-based authentication"
    echo "  ✓ ACL-based access control"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
}

# Main installation flow
main() {
    echo
    log "Starting Tailscale installation for Thanos..."
    echo

    # Detect OS
    local os_type
    os_type=$(detect_os)
    info "Detected OS: $os_type"

    # Check if already installed
    if check_tailscale_installed; then
        warn "Tailscale is already installed"
        read -p "Continue with configuration? (Y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            info "Exiting"
            exit 0
        fi
    else
        # Install Tailscale
        case $os_type in
            macos)
                install_tailscale_macos || exit 1
                ;;
            linux)
                install_tailscale_linux || exit 1
                ;;
            *)
                error "Unsupported operating system: $os_type"
                exit 1
                ;;
        esac
    fi

    # Authenticate
    authenticate_tailscale || exit 1

    # Generate ACL template
    generate_acl_template

    # Configure firewall
    case $os_type in
        macos)
            configure_firewall_macos
            ;;
        linux)
            configure_firewall_linux
            ;;
    esac

    # Validate installation
    validate_installation || exit 1

    # Show instructions
    show_access_instructions

    success "Installation complete! Thanos is now accessible via Tailscale."
    echo
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --hostname)
            HOSTNAME="$2"
            shift 2
            ;;
        --tags)
            TAGS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --hostname HOSTNAME    Set device hostname (default: thanos-primary)"
            echo "  --tags TAGS            Set device tags (default: tag:thanos)"
            echo "  --help                 Show this help message"
            echo
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main installation
main
