## Relations
@structure/infrastructure/web_automation/browser_automation_strategy_decision.md

## Raw Concept
**Task:**
Document Google Auth limitations in cloud environments

**Changes:**
- Formalized the limitation of cloud browsers for Google authentication

**Files:**
- .brv/context-tree/structure/infrastructure/web_automation/google_automation_constraints.md

**Flow:**
Auth Request -> If Google: Must use Local IP -> Else: Cloud IP acceptable

**Timestamp:** 2026-02-02

## Narrative
### Structure
- Target: Google Authentication
- Constraint: IP + Fingerprint binding
- Invalid Workaround: Cookie migration
- Valid Workaround: Local browser + Residential IP

### Dependencies
Requires residential/home IP address for session validity. Cloud-based datacenter IPs are flagged and blocked by Google.

### Features
- Identifies Google's IP-bound session security
- Explicitly notes that cookie export/import is insufficient due to IP binding
- Recommends local browser workaround for all Google authentication flows
