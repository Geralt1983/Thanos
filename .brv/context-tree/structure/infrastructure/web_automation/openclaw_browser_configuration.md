## Relations
@structure/infrastructure/web_automation/browser_automation_strategy_decision.md
@structure/infrastructure/web_automation/google_automation_constraints.md

## Raw Concept
**Task:**
Document OpenClaw Browser CDP Access, Configuration, and Autonomy Rules

**Changes:**
- Standardized CDP connection endpoint for local OpenClaw browser
- Defined user data directory for profile persistence
- Established browser autonomy rules and metaprompt location

**Files:**
- ~/Library/LaunchAgents/com.openclaw.browser.plist
- ~/.openclaw/browser/openclaw/user-data
- docs/browser-autonomy-metaprompt.md

**Flow:**
Tool Call -> Browser Action -> CDP Request to 127.0.0.1:18800 -> Local Chrome (profile=openclaw) Execution -> Follow Autonomy Rules (Ask for purchases/posts)

**Timestamp:** 2026-02-02

## Narrative
### Structure
- CDP Endpoint: `http://127.0.0.1:18800`
- User Data Path: `~/.openclaw/browser/openclaw/user-data`
- Service Manager: LaunchAgent (`com.openclaw.browser.plist`)
- Metaprompt: docs/browser-autonomy-metaprompt.md

### Dependencies
LaunchAgent at `~/Library/LaunchAgents/com.openclaw.browser.plist` ensures the browser remains active. Requires the browser to be running on the host machine for CDP access.

### Features
- Provides CDP access at `http://127.0.0.1:18800`
- Supports `action=snapshot` for accessibility tree extraction
- Supports `action=act` for UI interactions
- Uses persistent user data storage at `~/.openclaw/browser/openclaw/user-data`
- Profile 'openclaw' has persistent Google/Amazon auth.
- Autonomy Rules: no permission for browsing/reading/clicking, only ask for purchases/external messages/public posts.
