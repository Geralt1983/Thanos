#!/usr/bin/env bash
#
# Ttyd Installation and Setup Script for Thanos
#
# This script:
# 1. Checks and installs ttyd via Homebrew
# 2. Generates SSL certificates for HTTPS
# 3. Creates authentication credentials
# 4. Sets up LaunchAgent for auto-start
# 5. Validates the installation
#
# Usage:
#   ./install_ttyd.sh [--auto-start] [--port PORT]
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$SCRIPT_DIR/config"
SSL_DIR="$CONFIG_DIR/ssl"
LAUNCHAGENT_DIR="$SCRIPT_DIR/LaunchAgent"
STATE_DIR="$PROJECT_ROOT/State"
LOGS_DIR="$PROJECT_ROOT/logs"

# Defaults
AUTO_START=false
PORT=7681

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto-start)
            AUTO_START=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--auto-start] [--port PORT]"
            echo ""
            echo "Options:"
            echo "  --auto-start    Setup LaunchAgent for auto-start on login"
            echo "  --port PORT     Set custom port (default: 7681)"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Create directories
create_directories() {
    log_info "Creating required directories..."

    mkdir -p "$CONFIG_DIR"
    mkdir -p "$SSL_DIR"
    mkdir -p "$LAUNCHAGENT_DIR"
    mkdir -p "$STATE_DIR"
    mkdir -p "$LOGS_DIR"

    log_success "Directories created"
}

# Check and install ttyd
install_ttyd() {
    log_info "Checking for ttyd..."

    if check_command ttyd; then
        TTYD_VERSION=$(ttyd --version 2>&1 | head -n1 || echo "unknown")
        log_success "ttyd already installed: $TTYD_VERSION"
        return 0
    fi

    log_info "ttyd not found, installing via Homebrew..."

    # Check if Homebrew is installed
    if ! check_command brew; then
        log_error "Homebrew not found. Please install Homebrew first:"
        log_error "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi

    # Install ttyd
    if brew install ttyd; then
        TTYD_VERSION=$(ttyd --version 2>&1 | head -n1 || echo "unknown")
        log_success "ttyd installed successfully: $TTYD_VERSION"
    else
        log_error "Failed to install ttyd"
        exit 1
    fi
}

# Generate SSL certificate
generate_ssl_cert() {
    log_info "Generating SSL certificate..."

    CERT_FILE="$SSL_DIR/ttyd-cert.pem"
    KEY_FILE="$SSL_DIR/ttyd-key.pem"

    # Check if certificates already exist
    if [[ -f "$CERT_FILE" && -f "$KEY_FILE" ]]; then
        log_warning "SSL certificates already exist"
        read -p "Regenerate? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing certificates"
            return 0
        fi
    fi

    # Check for openssl
    if ! check_command openssl; then
        log_error "openssl not found. Please install openssl"
        exit 1
    fi

    # Generate self-signed certificate (valid for 1 year)
    if openssl req -x509 -newkey rsa:4096 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -days 365 \
        -nodes \
        -subj "/CN=localhost/O=Thanos/C=US" \
        2>/dev/null; then

        # Set secure permissions
        chmod 600 "$KEY_FILE"
        chmod 644 "$CERT_FILE"

        log_success "SSL certificate generated (valid for 365 days)"
        log_info "Certificate: $CERT_FILE"
        log_info "Private Key: $KEY_FILE"
    else
        log_error "Failed to generate SSL certificate"
        exit 1
    fi
}

# Generate authentication credentials
generate_credentials() {
    log_info "Generating authentication credentials..."

    CREDS_FILE="$CONFIG_DIR/ttyd-credentials.json"

    # Check if credentials already exist
    if [[ -f "$CREDS_FILE" ]]; then
        log_warning "Credentials already exist"
        read -p "Regenerate? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing credentials"
            return 0
        fi
    fi

    # Generate random password
    USERNAME="thanos"
    PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-32)

    # Save credentials to JSON file
    cat > "$CREDS_FILE" <<EOF
{
  "username": "$USERNAME",
  "password": "$PASSWORD",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

    # Secure permissions
    chmod 600 "$CREDS_FILE"

    log_success "Credentials generated"
    log_info "Username: $USERNAME"
    log_info "Password: $PASSWORD"
    log_warning "Credentials saved to: $CREDS_FILE (keep secure!)"
}

# Create configuration file
create_config() {
    log_info "Creating ttyd configuration..."

    CONFIG_FILE="$CONFIG_DIR/ttyd.conf"

    cat > "$CONFIG_FILE" <<EOF
{
  "port": $PORT,
  "ssl_cert": "$SSL_DIR/ttyd-cert.pem",
  "ssl_key": "$SSL_DIR/ttyd-key.pem",
  "credential_file": "$CONFIG_DIR/ttyd-credentials.json",
  "writable": true,
  "max_clients": 5,
  "check_origin": true,
  "interface": "0.0.0.0",
  "reconnect_timeout": 10,
  "client_timeout": 0,
  "terminal_type": "xterm-256color"
}
EOF

    log_success "Configuration created: $CONFIG_FILE"
}

# Setup LaunchAgent
setup_launchagent() {
    if [[ "$AUTO_START" != true ]]; then
        log_info "Skipping LaunchAgent setup (use --auto-start to enable)"
        return 0
    fi

    log_info "Setting up LaunchAgent for auto-start..."

    PLIST_FILE="$LAUNCHAGENT_DIR/com.thanos.ttyd.plist"
    USER_LAUNCHAGENT_DIR="$HOME/Library/LaunchAgents"

    mkdir -p "$USER_LAUNCHAGENT_DIR"

    # Create LaunchAgent plist
    cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.thanos.ttyd</string>

    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_DIR/thanos-web</string>
        <string>start</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>$LOGS_DIR/ttyd.log</string>

    <key>StandardErrorPath</key>
    <string>$LOGS_DIR/ttyd_error.log</string>

    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>

    <key>ProcessType</key>
    <string>Background</string>

    <key>ThrottleInterval</key>
    <integer>60</integer>
</dict>
</plist>
EOF

    # Link to user LaunchAgents
    ln -sf "$PLIST_FILE" "$USER_LAUNCHAGENT_DIR/com.thanos.ttyd.plist"

    log_success "LaunchAgent created: $PLIST_FILE"
    log_info "To enable auto-start:"
    log_info "  launchctl load ~/Library/LaunchAgents/com.thanos.ttyd.plist"
    log_info "To disable auto-start:"
    log_info "  launchctl unload ~/Library/LaunchAgents/com.thanos.ttyd.plist"
}

# Validate installation
validate_installation() {
    log_info "Validating installation..."

    local errors=0

    # Check ttyd
    if ! check_command ttyd; then
        log_error "ttyd not found in PATH"
        ((errors++))
    else
        log_success "ttyd found in PATH"
    fi

    # Check SSL certificates
    if [[ -f "$SSL_DIR/ttyd-cert.pem" && -f "$SSL_DIR/ttyd-key.pem" ]]; then
        log_success "SSL certificates present"
    else
        log_error "SSL certificates missing"
        ((errors++))
    fi

    # Check credentials
    if [[ -f "$CONFIG_DIR/ttyd-credentials.json" ]]; then
        log_success "Credentials file present"
    else
        log_error "Credentials file missing"
        ((errors++))
    fi

    # Check config
    if [[ -f "$CONFIG_DIR/ttyd.conf" ]]; then
        log_success "Configuration file present"
    else
        log_error "Configuration file missing"
        ((errors++))
    fi

    # Check thanos-web CLI
    if [[ -f "$SCRIPT_DIR/thanos-web" ]]; then
        log_success "thanos-web CLI present"
    else
        log_warning "thanos-web CLI not found (create it to manage ttyd)"
    fi

    if [[ $errors -eq 0 ]]; then
        log_success "Installation validation passed"
        return 0
    else
        log_error "Installation validation failed with $errors error(s)"
        return 1
    fi
}

# Print next steps
print_next_steps() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Installation Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Start ttyd daemon:"
    echo -e "   ${BLUE}./thanos-web start${NC}"
    echo ""
    echo "2. Get access URL and credentials:"
    echo -e "   ${BLUE}./thanos-web url${NC}"
    echo ""
    echo "3. View status:"
    echo -e "   ${BLUE}./thanos-web status${NC}"
    echo ""

    if [[ "$AUTO_START" == true ]]; then
        echo "4. Enable auto-start (LaunchAgent):"
        echo -e "   ${BLUE}launchctl load ~/Library/LaunchAgents/com.thanos.ttyd.plist${NC}"
        echo ""
    fi

    echo "Access your terminal in browser at:"
    echo -e "   ${BLUE}https://localhost:$PORT${NC}"
    echo ""
    echo -e "${YELLOW}Note: Browser will warn about self-signed certificate (safe to proceed)${NC}"
    echo ""
}

# Main installation flow
main() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║                                                       ║"
    echo "║          Thanos Ttyd Installation Script             ║"
    echo "║                                                       ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""

    create_directories
    install_ttyd
    generate_ssl_cert
    generate_credentials
    create_config
    setup_launchagent

    echo ""

    if validate_installation; then
        print_next_steps
        exit 0
    else
        log_error "Installation completed with errors"
        exit 1
    fi
}

# Run main
main
