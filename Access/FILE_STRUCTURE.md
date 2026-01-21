# Thanos Access Layer - File Structure

**Complete Phase 4 Implementation**

## Core Files

### Python Modules
```
Access/
├── access_coordinator.py          # Main orchestration class (550 lines)
│   ├── AccessCoordinator          # Coordinates all access methods
│   ├── AccessContext (Enum)       # Context detection
│   ├── AccessMethod (Enum)        # Access method types
│   ├── AccessRecommendation       # Recommendation dataclass
│   └── ComponentHealth            # Health status dataclass
│
├── tmux_manager.py                # Tmux session manager (existing)
├── ttyd_manager.py                # Web terminal manager (existing)
└── tailscale_manager.py           # VPN manager (existing)
```

### CLI Scripts
```
Access/
├── thanos-access                  # Main access CLI (750 lines)
│   └── Commands:
│       ├── auto        - Auto-detect and recommend
│       ├── status      - Full status
│       ├── mobile      - Mobile access (QR code)
│       ├── web         - Web browser access
│       ├── ssh         - SSH information
│       ├── local       - Local terminal
│       ├── emergency   - Minimal dependencies
│       ├── health      - Health check
│       └── urls        - List access URLs
│
├── thanos-tmux                    # Tmux launcher (existing)
├── thanos-web                     # Web terminal control (existing)
└── thanos-vpn                     # VPN control (existing)

Tools/
└── thanos-cli                     # Main Thanos CLI (300 lines)
    └── Commands:
        ├── access [subcommand]    - Access layer
        ├── remote [method]        - Quick remote access
        ├── status [--full]        - System status
        ├── tasks                  - Task management (future)
        ├── habits                 - Habit tracking (future)
        └── energy                 - Energy monitoring (future)
```

### Workflow Scripts
```
Access/workflows/
├── mobile-access.sh               # Mobile/phone access (100 lines)
├── web-access.sh                  # Browser access (120 lines)
├── ssh-access.sh                  # SSH information (130 lines)
├── local-access.sh                # Local terminal (140 lines)
└── emergency-access.sh            # Emergency recovery (200 lines)
```

## State Files
```
State/
├── access_coordinator.json        # Coordinator state
├── tmux_sessions.json             # Tmux session tracking
├── ttyd_daemon.json               # Web terminal state
└── tailscale_state.json           # VPN connection state
```

## Configuration
```
Access/config/
├── ttyd.conf                      # Web terminal config
├── ttyd-credentials.json          # Auth credentials (600 perms)
├── ssl/
│   ├── ttyd-cert.pem             # SSL certificate
│   └── ttyd-key.pem              # SSL private key (600 perms)
└── tailscale-acl.json            # ACL policies
```

## Logs
```
logs/
├── access_coordinator.log         # Main coordinator logs
├── ttyd.log                       # Web terminal logs
├── ttyd_access.log                # Access logs
└── tailscale.log                  # VPN logs
```

## Documentation
```
Access/
├── ACCESS_LAYER_README.md         # Comprehensive guide (500 lines)
├── PHASE4_COMPLETION.md           # Implementation summary (400 lines)
├── FILE_STRUCTURE.md              # This file
├── ARCHITECTURE.md                # Overall architecture (existing)
├── TTYD_README.md                 # Web terminal docs (existing)
├── TAILSCALE_README.md            # VPN docs (existing)
└── IMPLEMENTATION_SUMMARY.md      # Phase summary (existing)
```

## Quick Reference

### Main Entry Points
```bash
# Primary CLI
thanos-access [command]            # Main access interface

# Thanos CLI
thanos access [subcommand]         # Via main CLI
thanos remote [method]             # Quick remote access

# Workflows
Access/workflows/mobile-access.sh  # Mobile setup
Access/workflows/web-access.sh     # Web setup
Access/workflows/ssh-access.sh     # SSH info
Access/workflows/local-access.sh   # Local tmux
Access/workflows/emergency-access.sh # Recovery
```

### Component Scripts
```bash
# Direct component access
Access/thanos-tmux                 # Tmux session
Access/thanos-web [start|stop|restart|status]
Access/thanos-vpn [up|down|status]
```

### Python Integration
```python
# Import coordinator
from Access.access_coordinator import AccessCoordinator

# Import managers
from Access.tmux_manager import TmuxManager
from Access.ttyd_manager import TtydManager
from Access.tailscale_manager import TailscaleManager
```

## File Sizes

### Implementation Code
- `access_coordinator.py`: ~25 KB
- `thanos-access`: ~30 KB
- `thanos-cli`: ~12 KB
- Workflow scripts: ~5 KB each

### Documentation
- `ACCESS_LAYER_README.md`: ~25 KB
- `PHASE4_COMPLETION.md`: ~20 KB

**Total Implementation:** ~3,000 lines across 13 files

## Permissions

### Executable Scripts
```bash
chmod +x Access/thanos-access
chmod +x Access/thanos-tmux
chmod +x Access/thanos-web
chmod +x Access/thanos-vpn
chmod +x Access/workflows/*.sh
chmod +x Tools/thanos-cli
```

### Secure Files
```bash
chmod 600 Access/config/ttyd-credentials.json
chmod 600 Access/config/ssl/ttyd-key.pem
```

## Installation

```bash
# 1. Install dependencies
pip3 install --break-system-packages psutil

# 2. Set permissions
chmod +x Access/thanos-access
chmod +x Access/workflows/*.sh
chmod +x Tools/thanos-cli

# 3. Verify installation
thanos-access health
```

## Usage Patterns

### Quick Start
```bash
thanos-access                      # Auto-detect best method
```

### Mobile Access
```bash
thanos remote mobile               # QR code + credentials
```

### Web Access
```bash
thanos access web                  # Browser URLs
```

### Emergency
```bash
thanos remote emergency            # Recovery mode
```

### Full Status
```bash
thanos status --full               # All components
```

## Architecture Flow

```
User Command
    ↓
thanos-cli
    ↓
thanos-access
    ↓
AccessCoordinator
    ↓
┌────────────┬─────────────┬─────────────┐
│            │             │             │
TmuxManager  TtydManager   TailscaleManager
│            │             │             │
tmux         ttyd          tailscale
```

## Integration Points

### CLI → Access Layer
```
thanos access [cmd] → thanos-access [cmd]
thanos remote [method] → workflows/[method]-access.sh
```

### Python → Access Layer
```python
coordinator = AccessCoordinator()
recommendations = coordinator.recommend_access_method()
```

### Shell → Access Layer
```bash
URL=$(thanos access urls | grep local_web | awk '{print $2}')
```

---

**All files created and tested. Phase 4 complete.**
