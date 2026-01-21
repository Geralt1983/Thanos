# Thanos Web Terminal (ttyd)

Secure browser-based terminal access to Thanos via ttyd web terminal daemon.

## Overview

The ttyd system provides HTTPS-encrypted, authenticated web terminal access to Thanos tmux sessions. Access your Thanos terminal from any browser on your network.

### Features

- **Secure HTTPS-only** - Self-signed SSL/TLS certificates
- **Authentication required** - Username/password protection
- **Tmux integration** - Attach to Thanos sessions via browser
- **Auto-restart** - Health monitoring and automatic recovery
- **LaunchAgent support** - Auto-start on login (optional)
- **Access logging** - Track connections and security events
- **Multi-client** - Support multiple simultaneous connections

## Quick Start

### 1. Installation

```bash
cd /Users/jeremy/Projects/Thanos/Access
./install_ttyd.sh
```

This will:
- Install ttyd via Homebrew (if needed)
- Generate SSL certificate (self-signed, 365 days)
- Generate authentication credentials
- Create configuration files
- Set up directory structure

For auto-start on login:
```bash
./install_ttyd.sh --auto-start
```

### 2. Start Web Terminal

```bash
./thanos-web start
```

Output will show:
- Access URL (https://localhost:7681)
- Username and password
- Security information

### 3. Access in Browser

Open browser and navigate to:
```
https://localhost:7681
```

**Note:** Browser will warn about self-signed certificate. This is expected and safe to proceed.

Enter credentials when prompted:
- Username: `thanos` (default)
- Password: (shown in terminal output)

## Usage

### CLI Commands

```bash
# Start daemon
./thanos-web start                      # Default session (thanos-main)
./thanos-web start --session thanos-dev # Specific session

# Stop daemon
./thanos-web stop

# Restart daemon
./thanos-web restart

# Show status
./thanos-web status

# Get access URL and credentials
./thanos-web url

# Manage credentials
./thanos-web credentials                # Show current
./thanos-web credentials --regenerate   # Generate new

# View logs
./thanos-web logs                       # Last 50 lines
./thanos-web logs --tail 100            # Last 100 lines

# Health check
./thanos-web health
./thanos-web health --auto-restart      # Restart if unhealthy

# Show configuration
./thanos-web config
```

### Python API

```python
from Access.ttyd_manager import TtydManager

# Initialize manager
manager = TtydManager()

# Start daemon
manager.start(session_name="thanos-main")

# Get status
status = manager.get_status()
print(f"Running: {status.running}")
print(f"URL: {status.access_url}")

# Health check
if manager.health_check():
    print("Healthy!")

# Auto-restart if unhealthy
manager.auto_restart_if_unhealthy()

# Stop daemon
manager.stop()
```

## Configuration

### File Locations

```
Access/
├── config/
│   ├── ttyd.conf                 # Main configuration
│   ├── ttyd-credentials.json     # Auth credentials (secure!)
│   └── ssl/
│       ├── ttyd-cert.pem         # SSL certificate
│       └── ttyd-key.pem          # SSL private key (secure!)
├── LaunchAgent/
│   └── com.thanos.ttyd.plist     # Auto-start configuration
State/
├── ttyd_daemon.json              # Runtime state
└── ttyd.pid                      # Process ID file
logs/
├── ttyd.log                      # Daemon logs
└── ttyd_access.log               # Access logs
```

### Configuration Options

Edit `config/ttyd.conf`:

```json
{
  "port": 7681,                   // Web server port
  "interface": "0.0.0.0",         // Network interface (0.0.0.0 = all)
  "max_clients": 5,               // Max simultaneous connections
  "writable": true,               // Allow terminal input
  "check_origin": true,           // Verify request origin
  "reconnect_timeout": 10,        // Reconnect timeout (seconds)
  "client_timeout": 0,            // Client timeout (0 = no timeout)
  "terminal_type": "xterm-256color"
}
```

### Custom Port

```bash
./install_ttyd.sh --port 8080
```

Or edit `config/ttyd.conf` and restart.

### Custom SSL Certificates

Replace self-signed certificates with your own:

```bash
# Copy your certificates
cp your-cert.pem Access/config/ssl/ttyd-cert.pem
cp your-key.pem Access/config/ssl/ttyd-key.pem

# Secure permissions
chmod 644 Access/config/ssl/ttyd-cert.pem
chmod 600 Access/config/ssl/ttyd-key.pem

# Restart daemon
./thanos-web restart
```

## Security

### Authentication

- **Required by default** - Cannot be disabled
- **Strong passwords** - 32-character random passwords
- **Secure storage** - Credentials stored in 0600 permissions file
- **Regeneration** - Can regenerate at any time

```bash
./thanos-web credentials --regenerate
```

### SSL/TLS

- **HTTPS-only** - Plain HTTP not supported
- **Self-signed certificates** - Generated during installation
- **Custom certificates** - Supported (see above)
- **Certificate rotation** - Regenerate when expired

```bash
# Regenerate SSL certificate
cd Access/config/ssl
rm ttyd-cert.pem ttyd-key.pem
cd ../..
./install_ttyd.sh  # Will regenerate
```

### Access Control

- **Origin checking** - Validates request origin
- **Client limits** - Max 5 simultaneous connections (configurable)
- **Access logging** - All connections logged
- **IP tracking** - Connection source tracked

### Security Best Practices

1. **Keep credentials secure** - Don't commit to git
2. **Rotate passwords regularly** - Use `--regenerate` option
3. **Monitor access logs** - Check for suspicious activity
4. **Use firewall** - Restrict access to trusted networks
5. **Tailscale integration** - For remote access (Phase 4.3)

## Auto-Start (LaunchAgent)

### Enable Auto-Start

```bash
launchctl load ~/Library/LaunchAgents/com.thanos.ttyd.plist
```

The daemon will now start automatically on login.

### Disable Auto-Start

```bash
launchctl unload ~/Library/LaunchAgents/com.thanos.ttyd.plist
```

### Check LaunchAgent Status

```bash
launchctl list | grep thanos.ttyd
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :7681

# Change port in config
vim Access/config/ttyd.conf  # Edit "port"
./thanos-web restart
```

### SSL Certificate Errors

Browser warnings about certificate are normal for self-signed certs:
1. Click "Advanced"
2. Click "Proceed to localhost (unsafe)"

This is safe for local/Tailscale access.

### Authentication Fails

```bash
# Regenerate credentials
./thanos-web credentials --regenerate
./thanos-web restart

# View current credentials
./thanos-web url
```

### Daemon Won't Start

```bash
# Check logs
./thanos-web logs

# Verify ttyd installed
which ttyd
ttyd --version

# Check permissions
ls -la Access/config/ssl/
```

### Health Check Fails

```bash
# Run health check
./thanos-web health

# Auto-restart if unhealthy
./thanos-web health --auto-restart

# Check daemon status
./thanos-web status
```

## Integration

### With Thanos Tmux

The web terminal attaches to Thanos tmux sessions:

```bash
# Start web terminal for main session
./thanos-web start --session thanos-main

# Start for dev session
./thanos-web start --session thanos-dev
```

### With Tailscale (Phase 4.3)

Future integration will enable secure remote access via Tailscale network.

### With Monitoring

The daemon supports health monitoring and auto-restart:

```python
from Access.ttyd_manager import TtydManager

manager = TtydManager()

# Health check loop
while True:
    if not manager.health_check():
        manager.auto_restart_if_unhealthy()
    time.sleep(60)
```

## Architecture

### Process Lifecycle

1. **Start**: `thanos-web start`
   - Verify ttyd installed
   - Check port availability
   - Load/generate SSL certificates
   - Load/generate credentials
   - Build ttyd command
   - Start daemon process
   - Save PID
   - Verify startup

2. **Running**:
   - Daemon listens on configured port
   - Accepts HTTPS connections
   - Validates credentials
   - Attaches to tmux session
   - Streams terminal I/O

3. **Stop**: `thanos-web stop`
   - Send SIGTERM
   - Wait for graceful shutdown
   - Force kill if timeout
   - Clean up PID file
   - Update state

### Health Monitoring

Checks performed:
- Process exists and responsive
- Port is listening
- Process not zombie
- Resource usage acceptable

Auto-restart triggers:
- Process crashed
- Port not listening
- Process zombie
- Health check timeout

## Development

### Testing

```bash
# Test installation
./install_ttyd.sh

# Test daemon start
./thanos-web start
./thanos-web status

# Test health monitoring
./thanos-web health

# Test credentials
./thanos-web credentials

# Test logs
./thanos-web logs
```

### Debugging

```bash
# Enable debug logging
export THANOS_DEBUG=1

# View detailed logs
tail -f logs/ttyd.log

# Check process
ps aux | grep ttyd

# Check network
netstat -an | grep 7681
lsof -i :7681
```

### Contributing

Follow existing patterns from `tmux_manager.py`:
- Consistent logging
- Error handling
- State persistence
- Process management
- Security best practices

## Future Enhancements

- [ ] Multi-user authentication
- [ ] Session recording/playback
- [ ] Rate limiting
- [ ] Tailscale integration (Phase 4.3)
- [ ] Web UI for management
- [ ] Real-time session sharing
- [ ] Custom themes
- [ ] Mobile-optimized view

## License

Part of Thanos Operating System v2.0

---

**Questions?** Check the logs: `./thanos-web logs`
