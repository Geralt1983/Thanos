# Thanos Access Layer

Terminal session management and remote access control for Thanos.

## Overview

The Access layer provides:
- **Tmux Session Management** - Persistent terminal sessions with auto-recovery
- **Web Terminal Access** - HTTPS browser-based terminal via ttyd
- **Session State Tracking** - Track session lifecycle and metadata
- **Security & Authentication** - SSL/TLS encryption and credential management
- **Graceful Degradation** - Works with or without tmux installed

## Components

### 1. Web Terminal Access (ttyd)

Secure browser-based terminal access to Thanos tmux sessions.

**Quick Start:**
```bash
# Install ttyd and setup
./install_ttyd.sh

# Start web terminal
./thanos-web start

# Access in browser at https://localhost:7681
```

**Features:**
- HTTPS-only with SSL/TLS encryption
- Authentication required (username/password)
- Multi-client support (up to 5 simultaneous)
- Health monitoring and auto-restart
- LaunchAgent for auto-start on login
- Integration with Thanos tmux sessions

See [TTYD_README.md](TTYD_README.md) for complete documentation.

### 2. TmuxManager (`tmux_manager.py`)

Python class for programmatic tmux session management.

```python
from Access.tmux_manager import TmuxManager

manager = TmuxManager()

# Create or attach to session
manager.attach_or_create("thanos-main")

# List all sessions
sessions = manager.list_sessions()

# Get session info
info = manager.get_session_info("thanos-main")

# Kill a session
manager.kill_session("thanos-dev")

# Cleanup orphaned state
manager.cleanup_orphaned_state()
```

**Features:**
- Named session creation and attachment
- Session lifecycle management (create, attach, detach, kill)
- Auto-recovery from crashed sessions
- State persistence in `State/tmux_sessions.json`
- Comprehensive error handling and logging

### 3. CLI Wrapper (`thanos-tmux`)

User-friendly command-line interface for session management.

```bash
# Auto-attach to main session
thanos-tmux

# Attach to specific session
thanos-tmux dev
thanos-tmux monitor

# List all sessions
thanos-tmux list

# Show status
thanos-tmux status

# Kill a session
thanos-tmux kill thanos-dev

# Cleanup orphaned state
thanos-tmux cleanup
```

### 4. Tmux Configuration (`config/tmux.conf`)

Optimized tmux configuration with Thanos theme.

**Key Features:**
- Thanos-themed status bar (purple/gold)
- Mouse support enabled
- Vi-style copy mode
- Clipboard integration (macOS/Linux)
- Productivity key bindings
- Session persistence ready

**Key Bindings:**
```
Prefix: Ctrl-a

Windows:
  c            New window
  S-Left/Right Quick switch (no prefix)
  |            Split horizontal
  -            Split vertical

Panes:
  M-Arrow      Navigate (no prefix)
  Arrow        Resize pane
  x            Kill pane
  y            Sync panes toggle

Copy Mode:
  [            Enter copy mode
  v            Begin selection
  y            Copy to clipboard
  p            Paste
```

## Standard Sessions

Thanos uses three standard session names:

1. **thanos-main** - Primary work session
2. **thanos-dev** - Development and testing
3. **thanos-monitor** - Background monitoring/daemons

## Installation

### 1. Install tmux

```bash
# macOS
brew install tmux

# Ubuntu/Debian
sudo apt install tmux

# Arch Linux
sudo pacman -S tmux
```

### 2. Link tmux configuration

```bash
# Link Thanos tmux config
ln -sf ~/Projects/Thanos/Access/config/tmux.conf ~/.tmux.conf

# Reload tmux configuration
tmux source-file ~/.tmux.conf
```

### 3. Make CLI executable

```bash
chmod +x ~/Projects/Thanos/Access/thanos-tmux

# Optional: Add to PATH
echo 'export PATH="$HOME/Projects/Thanos/Access:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Usage Examples

### Basic Workflow

```bash
# Start Thanos in a persistent session
thanos-tmux main

# Inside tmux, run Thanos
./Tools/thanos-claude

# Detach (Ctrl-a, d)
# Later, reattach
thanos-tmux main
```

### Development Workflow

```bash
# Main session for work
thanos-tmux main

# Dev session for testing
thanos-tmux dev

# Monitor session for daemons
thanos-tmux monitor

# List all sessions
thanos-tmux list
```

### Session Management

```bash
# Check status
thanos-tmux status

# Kill a session
thanos-tmux kill thanos-dev

# Cleanup orphaned state
thanos-tmux cleanup
```

## Integration with Thanos

### Startup Hook

Add to `hooks/session-start/`:

```bash
#!/bin/bash
# Auto-attach to tmux session on startup

if command -v tmux &> /dev/null; then
    if [ -z "$TMUX" ]; then
        # Not in tmux, attach or create
        ~/Projects/Thanos/Access/thanos-tmux main
    fi
fi
```

### CLI Integration

Modify `Tools/thanos-claude` to auto-use tmux:

```bash
#!/bin/bash
# Check if in tmux, if not, start session
if [ -z "$TMUX" ] && command -v tmux &> /dev/null; then
    exec ~/Projects/Thanos/Access/thanos-tmux main
else
    # Run normally
    exec bun run ~/Projects/Thanos/Tools/thanos.ts "$@"
fi
```

## State File

Session state is tracked in `State/tmux_sessions.json`:

```json
{
  "thanos-main": {
    "name": "thanos-main",
    "created_at": "2026-01-20T21:00:00",
    "last_attached": "2026-01-20T21:30:00",
    "window_count": 3,
    "is_attached": true,
    "metadata": {
      "start_directory": "/Users/jeremy/Projects/Thanos"
    }
  }
}
```

## Advanced Configuration

### Session Persistence (Optional)

For automatic session save/restore, install TPM:

```bash
# Install TPM
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Uncomment plugin lines in tmux.conf:
# set -g @plugin 'tmux-plugins/tmux-resurrect'
# set -g @plugin 'tmux-plugins/tmux-continuum'

# Install plugins (inside tmux)
# Prefix + I
```

### Custom Status Bar

Edit `config/tmux.conf` to customize:

```bash
# Add custom indicators
set -g status-right "#[fg=colour220]#(~/Projects/Thanos/Tools/get-status.sh)"
```

## Troubleshooting

### Tmux not found

```bash
# Check if installed
which tmux

# Install if missing
brew install tmux  # macOS
```

### Configuration not loading

```bash
# Reload manually
tmux source-file ~/.tmux.conf

# Or inside tmux
# Prefix + r
```

### Session state out of sync

```bash
# Cleanup orphaned states
thanos-tmux cleanup

# Or manually
rm ~/Projects/Thanos/State/tmux_sessions.json
```

### Clipboard not working

```bash
# macOS: Should work out of box
# Linux: Install xclip
sudo apt install xclip  # Ubuntu
```

## Architecture

```
Access/
├── ttyd_manager.py           # Web terminal daemon manager
├── tmux_manager.py           # Core session management
├── thanos-web                # Web terminal CLI
├── thanos-tmux               # Tmux CLI wrapper
├── install_ttyd.sh           # Ttyd installation script
├── config/
│   ├── tmux.conf             # Tmux configuration
│   ├── ttyd.conf             # Ttyd configuration
│   ├── ttyd-credentials.json # Auth credentials (secure)
│   └── ssl/
│       ├── ttyd-cert.pem     # SSL certificate
│       └── ttyd-key.pem      # SSL private key (secure)
├── LaunchAgent/
│   └── com.thanos.ttyd.plist # Auto-start configuration
├── README.md                 # This file
└── TTYD_README.md            # Web terminal docs

State/
├── tmux_sessions.json        # Session state tracking
├── ttyd_daemon.json          # Daemon state
└── ttyd.pid                  # Process ID file

logs/
├── ttyd.log                  # Daemon logs
└── ttyd_access.log           # Access logs
```

## Future Enhancements

### Tmux Enhancements
- [ ] Auto-launch daemons in monitor session
- [ ] Session templates for different workflows
- [ ] Integration with hooks system for auto-attach
- [ ] Window layout presets
- [ ] Session recording/replay
- [ ] Multi-machine session sync

### Web Terminal Enhancements
- [ ] Tailscale integration for remote access (Phase 4.3)
- [ ] Multi-user authentication system
- [ ] Rate limiting and DDoS protection
- [ ] Web UI for session management
- [ ] Real-time session sharing
- [ ] Custom themes and mobile optimization
- [ ] Session recording/playback via web interface

## Related

- **LaunchAgent** - macOS daemon management
- **Tools/thanos-claude** - Main Thanos CLI
- **hooks/** - Session lifecycle hooks
