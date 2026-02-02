## Relations
@structure/memory_system/sync/session_watcher_daemon.md
@structure/architecture/core_architecture_overview.md

## Raw Concept
**Task:**
Automate startup and persistence of Thanos backend services on macOS

**Changes:**
- Configured macOS LaunchAgents for critical system components to ensure high availability

**Files:**
- ~/Library/LaunchAgents/*.plist

**Flow:**
macOS Boot -> launchd -> RunAtLoad (plist) -> Thanos Services (Gateway, BRV, Watcher) -> KeepAlive (auto-restart)

**Timestamp:** 2026-01-31

## Narrative
### Structure
- Path: ~/Library/LaunchAgents/ai.openclaw.gateway.plist
- Path: ~/Library/LaunchAgents/dev.byterover.brv.plist
- Path: ~/Library/LaunchAgents/ai.thanos.session-watcher.plist

### Dependencies
- macOS launchd system
- ~/Library/LaunchAgents/
- ~/.openclaw/logs/ for service logs

### Features
- ai.openclaw.gateway: Manages the OpenClaw MCP gateway
- dev.byterover.brv: Manages the ByteRover server (working dir: /Users/jeremy/Projects/Thanos)
- ai.thanos.session-watcher: Manages the real-time conversation sync daemon
- All services configured with KeepAlive=true and RunAtLoad=true for persistence
