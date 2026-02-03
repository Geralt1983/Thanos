## Relations
@structure/infrastructure/web_automation/google_automation_constraints.md
@structure/infrastructure/persistence/macos_auto_start_services.md

## Raw Concept
**Task:**
Standardize Browser Automation Decision for Google vs Non-Google services

**Changes:**
- Pinned Google service automation to local browser instances only
- Configured Browserbase for non-Google targets (Amazon, LinkedIn)
- Implemented LaunchAgent for persistent browser availability

**Files:**
- ~/Library/LaunchAgents/com.openclaw.browser.plist

**Flow:**
Automation Request -> Target Check (Google?) -> If Google: Connect to local Chrome via CDP (profile=openclaw) -> Else: Use Browserbase Cloud

**Timestamp:** 2026-02-02

## Narrative
### Structure
- Local Browser: Chrome (profile=openclaw)
- Cloud Browser: Browserbase (for non-Google services)
- Persistent Service: LaunchAgent (com.openclaw.browser.plist)

### Dependencies
LaunchAgent installed at ~/Library/LaunchAgents/com.openclaw.browser.plist for auto-start on macOS. Requires laptop to be on 24/7 for reliable CDP connection.

### Features
- Uses local Chrome with `profile=openclaw` for Google services (Keep, etc.)
- Bypasses Google's session/IP/fingerprint blocking
- Utilizes CDP connection via OpenClaw
- Distinguishes between local automation (Google) and cloud automation (Browserbase for Amazon, LinkedIn)
