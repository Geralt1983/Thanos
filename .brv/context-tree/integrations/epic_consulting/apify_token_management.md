## Relations
@integrations/epic_consulting/linkedin_scraper_optimization.md

## Raw Concept
**Task:**
Improve Apify Token Management and Validation

**Changes:**
- Standardized Apify token validation and storage practices

**Files:**
- ~/.apify/auth.json
- .env

**Flow:**
Check Scraper Failure -> Validate Token via API -> Refresh Token if expired -> Update .env

**Timestamp:** 2026-02-03

## Narrative
### Structure
- Primary Token Location: `.env` (`APIFY_TOKEN`)
- Secondary Token Location: `~/.apify/auth.json` (Legacy/Expired)
- Validation Endpoint: `https://api.apify.com/v2/users/me`

### Dependencies
Requires a valid Apify API token. Tokens are subject to expiration and may require manual refresh.

### Features
- Token storage: Prefer `.env` as `APIFY_TOKEN` over `~/.apify/auth.json`.
- Validation method: Use `curl` to the `/v2/users/me` endpoint to verify token health.
- Error Handling: Always verify token validity before troubleshooting scraper failures.
