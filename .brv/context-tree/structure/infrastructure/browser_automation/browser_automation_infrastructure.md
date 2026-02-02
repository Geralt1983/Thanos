## Relations
@structure/architecture/core_architecture_overview.md
@structure/mcp_servers/mcp_server_infrastructure.md

## Raw Concept
**Task:**
Configure multi-layered browser automation for autonomous web tasks

**Changes:**
- Established multiple browser automation paths (OpenClaw, Browser Use, Extension Relay)
- Configured persistent logins for Kimi.com and Moderato plan

**Files:**
- docs/browser-automation.md
- TOOLS.md

**Flow:**
Thanos -> Browser Tool -> OpenClaw/Cloud Browser -> Web Interaction -> Snapshot/Result

**Timestamp:** 2026-01-31

## Narrative
### Structure
- Profile: openclaw
- CDP Port: 18800
- User Data: ~/.openclaw/browser/openclaw/user-data
- Resolution insight: Resize to 1400x900 to expand sidebars
- Reliability: fresh snapshot before click, evaluate JS as fallback for stale refs

### Dependencies
- OpenClaw managed browser
- Browser Use Cloud API
- Chrome Extension Relay
- .env configuration for API keys and profile IDs

### Features
- OpenClaw Browser: Primary, managed profile (openclaw), CDP port 18800, persists logins (Kimi.com - Jeremy Kimble, Moderato)
- Browser Use: Cloud-based autonomous tasks, profile 'Thanos-Main'
- Chrome Extension Relay: Control existing Chrome tabs
- Commands: start, stop, open, snapshot, screenshot, act (click, type, evaluate)
