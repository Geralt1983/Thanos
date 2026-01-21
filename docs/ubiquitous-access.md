# Ubiquitous Access System

**Phase 4 of Thanos v2.0 Architecture**

> "Reality is often disappointing. That is, it was. Now reality can be whatever I want."
> — Access Thanos from anywhere.

## Overview

The Ubiquitous Access layer provides secure, cross-device terminal access to Thanos using:
- **tmux**: Persistent terminal sessions
- **ttyd**: Web-based terminal over HTTPS
- **Tailscale Funnel**: Secure remote access from anywhere

## Architecture

```
┌─────────────────────────────────────────────┐
│         Any Device (Phone/Tablet/Laptop)    │
│              https://thanos.ts.net           │
└────────────────┬────────────────────────────┘
                 │ Tailscale Funnel (HTTPS)
                 ▼
┌─────────────────────────────────────────────┐
│         ttyd Web Terminal Server            │
│              Port 7681 (auth required)       │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│         tmux Session: "thanos"              │
│  ┌───────────┬──────────┬─────────┬───────┐ │
│  │  main     │  logs    │  state  │ tools │ │
│  │  CLI      │  tailing │ monitor │ utils │ │
│  └───────────┴──────────┴─────────┴───────┘ │
└─────────────────────────────────────────────┘
```

## Components

### 1. Tmux Session Manager

**File:** `Access/thanos-session.sh`

Creates or attaches to a persistent "thanos" tmux session with 4 windows:

1. **main**: Thanos CLI interface
2. **logs**: Log file surveillance
3. **state**: CurrentFocus.md monitoring
4. **tools**: Quick access to utilities

**Usage:**
```bash
cd ~/Projects/Thanos
./Access/thanos-session.sh
```

**Features:**
- Persistent sessions survive terminal closes
- Thanos-themed status bar (purple/gold)
- Auto-initializes CLI on startup
- Custom window layouts

**tmux Key Bindings:**
```
Ctrl+b c       Create new window
Ctrl+b n       Next window
Ctrl+b p       Previous window
Ctrl+b 0-9     Switch to window number
Ctrl+b d       Detach from session
Ctrl+b [       Enter scroll mode (q to quit)
```

### 2. ttyd Web Terminal Server

**File:** `Access/ttyd-server.sh`

Serves a web-based terminal over HTTPS with authentication.

**Commands:**
```bash
# Start server
./Access/ttyd-server.sh start

# Stop server
./Access/ttyd-server.sh stop

# Restart server
./Access/ttyd-server.sh restart

# Check status
./Access/ttyd-server.sh status

# Show credentials
./Access/ttyd-server.sh credentials

# Generate new credentials
./Access/ttyd-server.sh regenerate
```

**Configuration:**
- Port: 7681 (configurable via TTYD_PORT env var)
- Authentication: username/password required
- Theme: Thanos purple/dark theme
- Font: Monaco (macOS) / JetBrains Mono (fallback)

**Credentials:**
- Username: `thanos`
- Password: Auto-generated 24-character secure string
- Stored in: `~/.thanos/ttyd-credentials`

**PID Tracking:**
- PID file: `State/ttyd.pid`
- State file: `State/ttyd_daemon.json`
- Logs: `logs/ttyd.log`

### 3. LaunchAgent Auto-Start

**File:** `Access/LaunchAgent/com.thanos.ttyd.plist`

Automatically starts ttyd server on macOS boot.

**Installation:**
```bash
# Install LaunchAgent
./Access/install-launchagent.sh

# Manual commands
launchctl start com.thanos.ttyd    # Start now
launchctl stop com.thanos.ttyd     # Stop
launchctl unload ~/Library/LaunchAgents/com.thanos.ttyd.plist  # Uninstall
```

**Features:**
- Auto-starts on login
- Auto-restarts on crash
- Throttle protection (30s between restarts)
- Environment variables configured

### 4. Tailscale Funnel (Remote Access)

**Purpose:** Expose ttyd over public HTTPS for access from anywhere.

**Prerequisites:**
```bash
# Install Tailscale
brew install tailscale

# Login to Tailscale
sudo tailscale up

# Enable HTTPS certificates
tailscale cert $(hostname)
```

**Setup Funnel:**
```bash
# Start Funnel (exposes port 7681 as HTTPS)
tailscale funnel --bg --https=443 7681

# Check status
tailscale funnel status

# Stop Funnel
tailscale funnel --bg off
```

**Access URL:**
```
https://<machine-name>.<tailnet>.ts.net
```

Example: `https://macbookair.jeremy-tailnet.ts.net`

**Security:**
- End-to-end encryption via Tailscale
- Additional authentication via ttyd credentials
- Access controlled by Tailscale ACLs
- All traffic encrypted

**Tailscale ACL Configuration:**
```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["*:7681"]
    }
  ]
}
```

## Quick Start

### 1. Start Local tmux Session

```bash
cd ~/Projects/Thanos
./Access/thanos-session.sh
```

You'll be in a tmux session with Thanos CLI ready.

### 2. Start Web Terminal

```bash
# Start ttyd server
./Access/ttyd-server.sh start

# Note the credentials
./Access/ttyd-server.sh credentials
```

Access at: `http://localhost:7681`

### 3. Enable Remote Access

```bash
# Start Tailscale Funnel
tailscale funnel --bg --https=443 7681

# Get your access URL
tailscale funnel status
```

Access from anywhere: `https://<your-machine>.ts.net`

### 4. Enable Auto-Start

```bash
# Install LaunchAgent
./Access/install-launchagent.sh
```

ttyd will now start automatically on boot.

## Access from Mobile

### iOS/Android Setup

1. **Install Tailscale App**
   - iOS: App Store
   - Android: Play Store

2. **Login to Same Tailnet**
   - Use same account as your Mac

3. **Open Browser**
   - Navigate to: `https://<your-machine>.ts.net`
   - Login with ttyd credentials

4. **Full Terminal Access**
   - Same tmux session as desktop
   - All Thanos CLI commands available
   - State persists across devices

### Browser Compatibility

**Recommended:**
- Safari (iOS/macOS)
- Chrome (Android/macOS)
- Firefox

**Mobile Tips:**
- Landscape mode for better visibility
- External keyboard for easier typing
- Tmux prefix (Ctrl+b) works on mobile keyboards

## Security Best Practices

### Credential Management

```bash
# Rotate credentials monthly
./Access/ttyd-server.sh regenerate
./Access/ttyd-server.sh restart

# Store credentials in password manager
./Access/ttyd-server.sh credentials | pbcopy
```

### Tailscale Security

1. **Enable MFA** on Tailscale account
2. **Use ACLs** to restrict access
3. **Review devices** regularly in Tailscale admin
4. **Expire old devices** when decommissioned

### Network Security

- **Never expose ttyd directly to internet** (always use Tailscale)
- **Use strong credentials** (auto-generated recommended)
- **Rotate credentials** after any suspected compromise
- **Monitor logs** for suspicious access patterns

### Access Logs

```bash
# View ttyd access logs
tail -f ~/Projects/Thanos/logs/ttyd.log

# Check who's connected
ps aux | grep ttyd

# Audit recent connections
grep "connection" ~/Projects/Thanos/logs/ttyd.log | tail -20
```

## Troubleshooting

### ttyd Won't Start

**Check if port is in use:**
```bash
lsof -i :7681
```

**Check logs:**
```bash
tail -f ~/Projects/Thanos/logs/ttyd.log
```

**Try different port:**
```bash
TTYD_PORT=7682 ./Access/ttyd-server.sh start
```

### Tailscale Funnel Not Working

**Check Tailscale status:**
```bash
tailscale status
```

**Verify Funnel is running:**
```bash
tailscale funnel status
```

**Check certificate:**
```bash
tailscale cert $(hostname)
```

**Restart Funnel:**
```bash
tailscale funnel --bg off
tailscale funnel --bg --https=443 7681
```

### tmux Session Issues

**List all sessions:**
```bash
tmux ls
```

**Kill stuck session:**
```bash
tmux kill-session -t thanos
```

**Attach to different session:**
```bash
tmux attach-session -t <session-name>
```

### Authentication Failing

**Verify credentials:**
```bash
cat ~/.thanos/ttyd-credentials
```

**Regenerate if corrupted:**
```bash
./Access/ttyd-server.sh regenerate
./Access/ttyd-server.sh restart
```

## Advanced Configuration

### Custom tmux Layout

Edit `Access/thanos-session.sh`:
```bash
# Add more windows
tmux new-window -t "$SESSION_NAME" -n "custom" -c "/path"
tmux send-keys -t "$SESSION_NAME:custom" "your-command" C-m
```

### Custom ttyd Theme

Edit `Access/ttyd-server.sh`:
```bash
--client-option theme='{"background": "#your-color", ...}'
```

### Multiple Instances

Run multiple ttyd servers on different ports:
```bash
TTYD_PORT=7682 ./Access/ttyd-server.sh start
TTYD_PORT=7683 ./Access/ttyd-server.sh start
```

## Performance Optimization

### Reduce Latency

1. **Use regional Tailscale exit nodes**
2. **Enable Tailscale DERP** for faster routing
3. **Close unused tmux windows**

### Bandwidth Management

```bash
# Limit ttyd bandwidth (via tc on Linux)
tc qdisc add dev eth0 root tbf rate 1mbit burst 32kbit latency 400ms
```

### Battery Optimization (Mobile)

- Use Tailscale "Exit Node" for local access
- Disable auto-reconnect when on cellular
- Close browser tab when not actively using

## Integration with Other Phases

### With Shell Identity (Phase 2)

Visual state transitions visible in web terminal:
- Wallpapers show through tmux
- Voice feedback plays on remote device

### With Operator Daemon (Phase 3)

View operator alerts via web terminal:
- Monitor logs window shows real-time alerts
- Telegram notifications reach mobile

### With PAI Skills (Phase 1)

Execute skills from any device:
- TaskRouter works via web terminal
- HealthInsight shows Oura data remotely

## Files Reference

```
Access/
├── thanos-session.sh           # tmux session manager
├── ttyd-server.sh              # web terminal server
├── install-launchagent.sh      # LaunchAgent installer
└── LaunchAgent/
    └── com.thanos.ttyd.plist   # auto-start configuration

State/
├── ttyd.pid                    # server process ID
└── ttyd_daemon.json            # server state

logs/
└── ttyd.log                    # server access logs

~/.thanos/
└── ttyd-credentials            # authentication credentials
```

## Status

**Phase 4 Status:** ✓ Complete

**Components:**
- ✓ Tmux session manager
- ✓ ttyd web terminal server
- ✓ LaunchAgent auto-start
- ✓ Credentials management
- ⚠️ Tailscale Funnel (requires manual setup)

**Next Steps:**
1. Test remote access from mobile device
2. Configure Tailscale ACLs
3. Set up credential rotation schedule
4. Document mobile usage patterns

---

**The universe awaits your command from any device.**
