# Tailscale VPN Integration for Thanos

**Zero-trust remote access to Thanos Operating System from anywhere**

## Overview

Tailscale VPN integration provides secure, encrypted remote access to your Thanos system without exposing services to the public internet. Built on WireGuard protocol, it creates a private mesh network between your authorized devices.

### Key Features

- **Zero-trust security** - Device-based authentication via WireGuard
- **No public exposure** - Services never exposed to internet
- **Encrypted by default** - All traffic encrypted end-to-end
- **MagicDNS** - Stable hostnames instead of IP memorization
- **Cross-platform** - Works on macOS, Linux, iOS, Android, Windows
- **Automatic reconnection** - Maintains connection across network changes
- **ACL-based access control** - Fine-grained permission management

## Installation

### Quick Install

```bash
# Install and configure Tailscale
cd /Users/jeremy/Projects/Thanos/Access
./install_tailscale.sh

# Follow prompts to authenticate with Tailscale account
```

### Manual Install

#### macOS

```bash
# Install via Homebrew
brew install tailscale
sudo brew services start tailscale

# Authenticate and configure
sudo tailscale up \
    --hostname="thanos-primary" \
    --advertise-tags="tag:thanos" \
    --accept-dns \
    --ssh
```

#### Linux (Ubuntu/Debian)

```bash
# Add Tailscale package repository
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/focal.noarmor.gpg | \
    sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null

curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/focal.tailscale-keyring.list | \
    sudo tee /etc/apt/sources.list.d/tailscale.list

# Install Tailscale
sudo apt-get update
sudo apt-get install -y tailscale

# Enable and start service
sudo systemctl enable --now tailscaled

# Authenticate
sudo tailscale up --hostname="thanos-primary" --ssh
```

## Configuration

### ACL Policy

Edit `Access/config/tailscale-acl.json` to define access rules:

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["group:owner"],
      "dst": ["tag:thanos:7681", "tag:thanos:22", "tag:thanos:443"]
    }
  ],
  "tagOwners": {
    "tag:thanos": ["your-email@example.com"]
  },
  "groups": {
    "group:owner": ["your-email@example.com"]
  }
}
```

**Important:** Replace `your-email@example.com` with your actual Tailscale account email.

### Apply ACL Policy

1. Go to [Tailscale Admin Console](https://login.tailscale.com/admin/acls)
2. Paste your ACL policy
3. Save and validate
4. Policy takes effect within 5 minutes

### Security Best Practices

1. **Enable MFA** on your Tailscale account
2. **Use tags** to organize devices (`tag:thanos`)
3. **Apply least privilege** - Only allow required ports
4. **Review device list** monthly and revoke unused devices
5. **Enable device posture checks** (screen lock, disk encryption)
6. **Monitor access logs** for unusual activity

## Usage

### CLI Commands

```bash
# Check connection status
thanos-vpn status

# Connect to Tailscale
thanos-vpn connect

# Disconnect from Tailscale
thanos-vpn disconnect

# List all devices in network
thanos-vpn devices

# Get web access URL
thanos-vpn url

# Get SSH command
thanos-vpn ssh

# Health check
thanos-vpn health

# Show connection information
thanos-vpn info
```

### Python API

```python
from Access.tailscale_manager import TailscaleManager

# Initialize manager
manager = TailscaleManager()

# Check if connected
if manager.is_connected():
    print("Connected to Tailscale")

# Get status
status = manager.get_status()
print(f"Backend State: {status.backend_state}")
print(f"Tailscale IP: {status.self_device.tailscale_ip}")
print(f"MagicDNS: {status.magic_dns}")

# Get web access URL
url = manager.get_web_access_url()
print(f"Access Thanos at: {url}")

# Get SSH command
ssh_cmd = manager.get_ssh_command()
print(f"SSH: {ssh_cmd}")

# List devices
devices = manager.list_devices()
for device in devices:
    print(f"{device.hostname}: {device.tailscale_ip}")

# Health check
health = manager.health_check()
if health['connected']:
    print("✓ Healthy")
else:
    print("✗ Issues:", health['issues'])
```

## Remote Access Workflows

### 1. Mobile Access (iPhone/iPad)

**Setup (one-time):**

1. Install Tailscale from App Store
2. Sign in with Tailscale account (same account as primary device)
3. Device auto-enrolled in network
4. Add bookmark: Save web terminal URL to home screen

**Daily Use:**

1. Open Safari
2. Navigate to: `https://thanos-primary:443/` (or use saved bookmark)
3. Enter ttyd credentials (auto-filled by iOS Keychain)
4. Terminal loads instantly - resume existing session

**Optimized for mobile:**
- 16px font size (readable without zoom)
- Touch-friendly scrollback
- Native iOS copy/paste
- Virtual keyboard triggers properly

### 2. Web Browser Access (Desktop)

**From any computer with Tailscale:**

```bash
# Ensure Tailscale is running
tailscale status

# Open browser and navigate to
https://thanos-primary:443/

# Or use Tailscale IP
https://100.64.1.10:443/
```

### 3. Direct SSH Access

**Via Tailscale SSH:**

```bash
# Using MagicDNS hostname
ssh jeremy@thanos-primary

# Using Tailscale IP
ssh jeremy@100.64.1.10
```

**SSH Config (~/.ssh/config):**

```ssh-config
Host thanos
    HostName thanos-primary
    User jeremy
    IdentityFile ~/.ssh/id_ed25519
    ForwardAgent yes
    ServerAliveInterval 60
```

Then simply:

```bash
ssh thanos
```

## Integration with Thanos Components

### ttyd Web Terminal

Tailscale URL is automatically detected and shown:

```bash
# Start web terminal
thanos-web start

# Get access URLs (local + Tailscale)
thanos-web url

# Output:
# Access URLs:
#   Local: https://localhost:7681/
#   Tailscale (Remote): https://thanos-primary:443/
#
# ✓ Tailscale VPN enabled - accessible from any authorized device
```

### tmux Sessions

Sessions persist across Tailscale connections:

```bash
# Create session locally
thanos-tmux main

# Disconnect and travel

# Reconnect from mobile via Tailscale
# Session automatically resumes - no state lost
```

## Network Architecture

### Mesh Topology

```
┌─────────────────────────────────────────┐
│      Tailscale Mesh VPN Network         │
│         (100.64.0.0/10 subnet)          │
├─────────────────────────────────────────┤
│                                         │
│  ┌────────────┐       ┌────────────┐   │
│  │ MacBook    │◄─────►│  iPhone    │   │
│  │ (Primary)  │       │  (Mobile)  │   │
│  │ 100.64.1.10│       │ 100.64.1.20│   │
│  └─────▲──────┘       └────────────┘   │
│        │                                │
│        │              ┌────────────┐   │
│        └─────────────►│  iPad      │   │
│                       │ 100.64.1.30│   │
│                       └────────────┘   │
└─────────────────────────────────────────┘
```

### Security Layers

```
Layer 1: Network Perimeter
├─ Tailscale encryption (WireGuard)
├─ Device authentication
└─ No public internet exposure

Layer 2: Transport Security
├─ TLS 1.3 (ttyd web access)
├─ SSH encryption
└─ Certificate validation

Layer 3: Application Auth
├─ ttyd HTTP Basic Auth
├─ SSH key-based auth
└─ Rate limiting (10 req/min)

Layer 4: System Authorization
├─ System user validation
├─ File permissions (0600)
└─ Process isolation (tmux)

Layer 5: Audit & Monitoring
├─ Access logging
├─ Failed auth tracking
└─ Anomaly detection
```

## Troubleshooting

### Cannot Connect to Tailscale

**Check status:**
```bash
tailscale status
```

**Common issues:**

1. **Not authenticated**
   ```bash
   sudo tailscale up
   ```

2. **Service not running (macOS)**
   ```bash
   sudo brew services restart tailscale
   ```

3. **Service not running (Linux)**
   ```bash
   sudo systemctl restart tailscaled
   ```

### No Tailscale IP Address

**Check backend state:**
```bash
thanos-vpn status
# Look for "Backend State: Running"
```

**If state is "NeedsLogin":**
```bash
sudo tailscale up --hostname="thanos-primary"
```

### MagicDNS Not Working

**Enable MagicDNS:**

1. Go to Tailscale admin console
2. DNS → Enable MagicDNS
3. Wait 5 minutes for propagation

**Verify:**
```bash
tailscale status | grep "MagicDNS"
```

### Cannot Access Web Terminal Remotely

**Checklist:**

1. Tailscale connected on both devices
   ```bash
   tailscale status  # Run on both devices
   ```

2. ttyd daemon running
   ```bash
   thanos-web status
   ```

3. Firewall allows Tailscale interface
   ```bash
   # macOS: Check System Preferences → Security → Firewall
   # Linux: sudo ufw status
   ```

4. Correct port in URL
   ```bash
   thanos-vpn url  # Shows correct URL
   ```

### Slow Connection

**Check network conditions:**
```bash
tailscale ping thanos-primary
```

**Enable DERP relay if needed:**
- Tailscale automatically uses DERP relays when direct connection fails
- Check relay status: `tailscale netcheck`

## Health Monitoring

### Automatic Health Checks

Create a monitoring script:

```bash
#!/bin/bash
# File: ~/cron/tailscale-health.sh

cd /Users/jeremy/Projects/Thanos/Access

# Run health check
if ! ./thanos-vpn health &>/dev/null; then
    echo "Tailscale health check failed" | \
        mail -s "Thanos VPN Alert" your-email@example.com

    # Attempt reconnection
    sudo tailscale up
fi
```

### Cron Schedule

```cron
# Check Tailscale health every 15 minutes
*/15 * * * * /Users/jeremy/cron/tailscale-health.sh
```

## State Management

### State Files

| File | Purpose | Location |
|------|---------|----------|
| `tailscale_state.json` | Connection state and config | `State/tailscale_state.json` |
| `tailscale_install.json` | Installation metadata | `State/tailscale_install.json` |
| `tailscale.log` | Activity logs | `logs/tailscale.log` |
| `tailscale-acl.json` | ACL policy template | `Access/config/tailscale-acl.json` |

### State Schema

**tailscale_state.json:**
```json
{
  "last_connected": "2026-01-20T19:45:23Z",
  "last_disconnected": "2026-01-20T18:30:00Z",
  "accept_routes": false,
  "accept_dns": true,
  "last_updated": "2026-01-20T19:45:23Z"
}
```

## Performance

### Connection Times

| Metric | Target | Typical |
|--------|--------|---------|
| Tailscale handshake | <500ms | ~300ms |
| Direct peer connection | <100ms | ~50ms |
| DERP relay latency | <200ms | ~150ms |
| Web page load (ttyd) | <3s | ~2s |
| SSH connection | <1s | ~800ms |

### Bandwidth Usage

- **Idle connection:** ~1 KB/s (keep-alive)
- **Web terminal:** 5-20 KB/s (active typing)
- **File transfer (scp):** Line speed (no overhead)

## Advanced Configuration

### Custom Device Tags

```bash
sudo tailscale up \
    --hostname="thanos-backup" \
    --advertise-tags="tag:thanos,tag:backup"
```

### Exit Nodes

Use Tailscale as VPN exit node:

```bash
# Advertise as exit node
sudo tailscale up --advertise-exit-node

# Use another device as exit node
sudo tailscale up --exit-node=thanos-primary
```

### Subnet Routing

Share local network via Tailscale:

```bash
sudo tailscale up --advertise-routes=192.168.1.0/24
```

## FAQ

**Q: Is Tailscale free?**
A: Yes, for personal use (up to 100 devices, 1 user). Team plans available.

**Q: Can I use Tailscale with other VPNs?**
A: Yes, Tailscale works alongside other VPNs.

**Q: What happens if Tailscale is down?**
A: Local access still works. Remote access unavailable until reconnected.

**Q: How secure is Tailscale?**
A: Uses WireGuard (audited, modern crypto). No plaintext traffic ever.

**Q: Can family members access my Thanos?**
A: Yes, with proper ACL configuration. Add to `group:family` with restricted access.

**Q: Does it work on cellular networks?**
A: Yes, Tailscale works on any network (WiFi, cellular, etc.).

**Q: How much battery does it use on mobile?**
A: Minimal. Tailscale is optimized for mobile battery life.

## References

- [Tailscale Documentation](https://tailscale.com/docs)
- [WireGuard Protocol](https://www.wireguard.com/)
- [ACL Policy Reference](https://tailscale.com/kb/1018/acls)
- [MagicDNS Guide](https://tailscale.com/kb/1081/magicdns)
- [Tailscale SSH](https://tailscale.com/kb/1193/tailscale-ssh)

---

**Implementation Date:** 2026-01-20
**Version:** 1.0
**Status:** Production Ready
**Maintained By:** Thanos Hive Mind
