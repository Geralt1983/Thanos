## Relations
@structure/infrastructure/browser_automation/browser_automation_infrastructure.md

## Raw Concept
**Task:**
Document Google automation reliability constraints and mitigation strategy

**Changes:**
- Documented Google automation blocking constraints (Datacenter IPs, Fingerprinting)
- Identified local `openclaw` profile as the primary reliable path for Google services
- Noted Scrapfly and Browser Use Cloud limitations for Google domains

**Files:**
- .brv/context-tree/structure/infrastructure/browser_automation/browser_automation_infrastructure.md

**Flow:**
Google Service Request -> Detect Domain -> If Google: Use Local OpenClaw Profile -> If Non-Google: Use Scrapfly/Cloud Browser

**Timestamp:** 2026-02-02

## Narrative
### Structure
- Profile: `openclaw`
- CDP Port: `18800`
- User Data: `~/.openclaw/browser/openclaw/user-data`

### Dependencies
- Local Chrome with profile `openclaw` (CDP Port 18800)
- Residential/Local IP (Datacenter IPs are blocked)

### Features
- Google Services Reliability: Local browser profile `openclaw` is the only reliable path for Google services.
- Anti-Bot Evasion: Local residential IP and device fingerprints from existing profiles bypass Google's datacenter/fingerprint blocks.
- Scrapfly: Valid only for non-Google services.
- Browser Use Cloud: Blocked by Google services due to datacenter IP usage.
