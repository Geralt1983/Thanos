## Relations
@integrations/epic_consulting/linkedin_scraper_optimization.md
@integrations/epic_consulting/epic_consulting_strategy_tools.md

## Raw Concept
**Task:**
Define LinkedIn Scraper Email Digest Format

**Changes:**
- Standardized LinkedIn scraper email digest format requirements

**Files:**
- data/linkedin-seen-posts.json

**Flow:**
Extract data from scraper -> Retrieve URLs from seen-posts.json -> Compile full details (recruiter, modules, URLs) -> Send Digest

**Timestamp:** 2026-02-03

## Narrative
### Structure
- Input source: `data/linkedin-seen-posts.json`
- Output requirement: Detailed email digest with specific metadata fields.

### Features
- Required fields: Full opportunity data, clickable LinkedIn URLs, recruiter contact info, and module lists.
- Source for URLs: `data/linkedin-seen-posts.json`.
- Constraint: Summaries are insufficient; full details must always be included in the digest.
