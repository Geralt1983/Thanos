# Tmux Integration Guide

Integration of tmux session management with Thanos workflow.

## Quick Start

### 1. Setup

```bash
# Install tmux (if not already)
brew install tmux  # macOS

# Link configuration
ln -sf ~/Projects/Thanos/Access/config/tmux.conf ~/.tmux.conf

# Make CLI executable
chmod +x ~/Projects/Thanos/Access/thanos-tmux

# Optional: Add to PATH
echo 'export PATH="$HOME/Projects/Thanos/Access:$PATH"' >> ~/.zshrc
```

### 2. Basic Usage

```bash
# Start Thanos in persistent session
thanos-tmux

# This is equivalent to:
thanos-tmux main
```

### 3. Inside Tmux

```bash
# Run Thanos CLI
./Tools/thanos-claude

# Detach from session
# Press: Ctrl-a, then d

# Reattach later
thanos-tmux
```

## Integration Patterns

### Pattern 1: Auto-attach on Shell Startup

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Auto-attach to Thanos tmux session
if [ -z "$TMUX" ] && command -v tmux &> /dev/null; then
    # Only auto-attach in interactive shells
    if [[ $- == *i* ]]; then
        # Check if we're in the Thanos directory
        if [[ "$PWD" == "$HOME/Projects/Thanos"* ]]; then
            ~/Projects/Thanos/Access/thanos-tmux main
        fi
    fi
fi
```

### Pattern 2: Wrapper in thanos-claude

Update `Tools/thanos-claude`:

```bash
#!/bin/bash
# Thanos CLI with tmux auto-session

THANOS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$THANOS_ROOT"

# Auto-attach to tmux if not already in a session
if [ -z "$TMUX" ] && command -v tmux &> /dev/null; then
    if [ "$1" != "--no-tmux" ]; then
        exec "$THANOS_ROOT/Access/thanos-tmux" main
    fi
fi

# Run Thanos normally
bun run "$THANOS_ROOT/Tools/thanos.ts" "$@"
```

Usage:
```bash
# Auto-attaches to tmux
./Tools/thanos-claude

# Skip tmux attachment
./Tools/thanos-claude --no-tmux
```

### Pattern 3: Session Hook Integration

Create `hooks/session-start/tmux-check.sh`:

```bash
#!/bin/bash
# Check tmux status on session start

THANOS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if command -v tmux &> /dev/null; then
    if [ -z "$TMUX" ]; then
        echo "💡 Tip: Run 'thanos-tmux' for persistent session"
    else
        echo "✓ Running in tmux session: $TMUX"
    fi
fi
```

### Pattern 4: Daemon Management

Launch background daemons in monitor session:

```bash
# Start monitor session for daemons
thanos-tmux monitor

# Inside monitor session, create windows:
# Window 1: Telegram bot
tmux new-window -t thanos-monitor:1 -n "telegram" \
  "cd ~/Projects/Thanos && python3 Tools/telegram_bot.py"

# Window 2: Alert daemon
tmux new-window -t thanos-monitor:2 -n "alerts" \
  "cd ~/Projects/Thanos && python3 Tools/daemons/alert_daemon.py"

# Window 3: Vigilance daemon
tmux new-window -t thanos-monitor:3 -n "vigilance" \
  "cd ~/Projects/Thanos && python3 Tools/daemons/vigilance_daemon.py"
```

Create script `Access/start-daemons.sh`:

```bash
#!/bin/bash
# Start all Thanos daemons in tmux monitor session

THANOS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Create or attach to monitor session
tmux new-session -d -s thanos-monitor -c "$THANOS_ROOT" 2>/dev/null || true

# Kill existing windows
tmux kill-window -t thanos-monitor:1 2>/dev/null || true
tmux kill-window -t thanos-monitor:2 2>/dev/null || true
tmux kill-window -t thanos-monitor:3 2>/dev/null || true

# Create daemon windows
tmux new-window -t thanos-monitor:1 -n "telegram" \
  "cd $THANOS_ROOT && python3 Tools/telegram_bot.py"

tmux new-window -t thanos-monitor:2 -n "alerts" \
  "cd $THANOS_ROOT && python3 Tools/daemons/alert_daemon.py"

tmux new-window -t thanos-monitor:3 -n "vigilance" \
  "cd $THANOS_ROOT && python3 Tools/daemons/vigilance_daemon.py"

echo "Daemons started in thanos-monitor session"
echo "Attach with: thanos-tmux monitor"
```

## Workflow Examples

### Development Workflow

```bash
# Window 1: Main Thanos CLI
thanos-tmux main

# Split pane for logs
Ctrl-a |  # Split horizontal

# In right pane, tail logs
tail -f logs/telegram_bot.log

# Create new window for development
Ctrl-a c

# Split for tests
Ctrl-a -  # Split vertical
```

### Multi-Session Workflow

```bash
# Session 1: Main work
thanos-tmux main
# Run Thanos CLI

# Session 2: Development
thanos-tmux dev
# Test changes, run scripts

# Session 3: Monitoring
thanos-tmux monitor
# Background daemons

# Switch between sessions
tmux switch-client -t thanos-main
tmux switch-client -t thanos-dev
tmux switch-client -t thanos-monitor
```

### Debugging Workflow

```bash
# Main session with split panes
thanos-tmux main

# Top pane: Thanos CLI
./Tools/thanos-claude

# Split horizontal (Ctrl-a |)
# Right pane: Python debugger
python3 -m pdb Tools/some_script.py

# Split vertical (Ctrl-a -)
# Bottom pane: Logs
tail -f logs/thanos.log
```

## Programmatic Usage

### From Python Scripts

```python
#!/usr/bin/env python3
from Access.tmux_manager import TmuxManager

def main():
    manager = TmuxManager()

    # Ensure session exists
    if not manager.session_exists("thanos-main"):
        manager.create_session("thanos-main", detached=True)

    # Get status
    info = manager.get_session_info("thanos-main")
    if info:
        print(f"Session: {info.name}")
        print(f"Windows: {info.window_count}")
        print(f"Attached: {info.is_attached}")

if __name__ == "__main__":
    main()
```

### From Shell Scripts

```bash
#!/bin/bash
# Check if in tmux session

if [ -z "$TMUX" ]; then
    echo "Not in tmux session"
    echo "Starting new session..."
    exec ~/Projects/Thanos/Access/thanos-tmux main
else
    echo "Already in tmux: $TMUX"
fi
```

## Advanced Features

### Custom Layouts

Create window layouts for different tasks:

```bash
# Development layout
tmux new-session -d -s dev -c ~/Projects/Thanos
tmux split-window -h -t dev:1
tmux split-window -v -t dev:1.2
tmux select-pane -t dev:1.1
tmux send-keys -t dev:1.1 "vim" C-m
tmux send-keys -t dev:1.2 "pytest --watch" C-m
tmux send-keys -t dev:1.3 "tail -f logs/test.log" C-m
```

### Session Templates

Create reusable session templates:

```python
# In tmux_manager.py
def create_dev_session(self, name: str = "thanos-dev") -> bool:
    """Create development session with standard layout."""
    if not self.create_session(name, detached=True):
        return False

    # Create standard windows
    self._run_tmux("new-window", "-t", f"{name}:2", "-n", "tests")
    self._run_tmux("new-window", "-t", f"{name}:3", "-n", "logs")

    # Split first window
    self._run_tmux("split-window", "-h", "-t", f"{name}:1")

    return True
```

### Session Snapshot/Restore

Save current session layout:

```bash
# Save layout
tmux list-windows -t thanos-main > ~/Projects/Thanos/State/session-layout.txt

# Restore layout (manual)
# Read layout file and recreate windows
```

## Tips and Tricks

### Quick Session Switching

Add aliases to `~/.zshrc`:

```bash
alias tm='thanos-tmux main'
alias td='thanos-tmux dev'
alias tmon='thanos-tmux monitor'
alias tls='thanos-tmux list'
alias ts='thanos-tmux status'
```

### Mouse Usage

With mouse enabled (default in Thanos config):
- Click panes to switch
- Click-drag pane borders to resize
- Scroll to navigate history
- Double-click to select words
- Triple-click to select lines

### Copy/Paste

```bash
# Enter copy mode
Ctrl-a [

# Navigate with vi keys (h,j,k,l)
# Start selection
v

# Copy selection
y

# Paste
Ctrl-a p
```

### Session Persistence Across Reboots

With tmux-resurrect plugin:

```bash
# Save session
Prefix + Ctrl-s

# Restore session
Prefix + Ctrl-r
```

## Troubleshooting

### "Session already exists"

```bash
# Kill and recreate
thanos-tmux kill thanos-main
thanos-tmux main
```

### Orphaned state

```bash
# Cleanup
thanos-tmux cleanup
```

### Configuration not loading

```bash
# Reload config
tmux source-file ~/.tmux.conf

# Or inside tmux
Prefix + r
```

### Colors not working

```bash
# Check terminal
echo $TERM
# Should be: screen-256color or xterm-256color

# Set in shell config
export TERM=xterm-256color
```

## Best Practices

1. **Use named sessions** - Stick to thanos-main, thanos-dev, thanos-monitor
2. **Detach, don't kill** - Preserve sessions with Ctrl-a d
3. **Regular cleanup** - Run `thanos-tmux cleanup` weekly
4. **Backup important work** - Sessions can crash
5. **Use status bar** - Monitor time, load, active windows
6. **Name windows** - `Ctrl-a ,` to rename windows descriptively
7. **Synchronize panes** - `Ctrl-a y` to send commands to all panes

## Integration Checklist

- [ ] Install tmux
- [ ] Link configuration file
- [ ] Test basic session creation
- [ ] Add to shell startup (optional)
- [ ] Create daemon startup script
- [ ] Setup aliases for quick access
- [ ] Test session persistence
- [ ] Configure clipboard integration
- [ ] Setup monitoring session for daemons
- [ ] Document custom workflows

## Related Documentation

- `Access/README.md` - Access layer overview
- `config/tmux.conf` - Configuration reference
- Phase 3 daemon documentation
- Hooks system documentation
