# LinkedIn Epic Contract Scraper

Created: 2026-02-01

## Overview

Scrapes LinkedIn for Epic EHR consulting/contract job opportunities, filters for relevance, deduplicates across runs, and sends email digests.

## Components

| File | Purpose |
|------|---------|
| `scripts/linkedin-epic-scrape.js` | Full Apify scraper (search → filter → output) |
| `scripts/process-linkedin-epic.js` | Process existing Apify datasets |
| `scripts/format-epic-email.js` | Format results as email with summary |
| `data/linkedin-seen-posts.json` | Persistent dedup (auto-prunes 30 days) |

## Apify Actor

**Actor:** `supreme_coder/linkedin-post`
- Free, no rental or cookies required
- Input: `{ "urls": [...] }` - pass LinkedIn search URLs directly
- Timeout: 180 seconds recommended

**Search terms:**
```
Epic EHR consultant, Epic implementation analyst, Epic go-live contract,
Epic Beaker analyst, Epic Radiant contract, Epic ClinDoc consultant,
Epic Orders analyst, Epic Inpatient consultant, Epic Ambulatory contract
```

## Filtering Logic

### 1. Recency Filter
Only posts ≤7 days old (based on `timeSincePosted`):
- Reject: "2w", "3w", "1mo", "1y"
- Accept: "1d", "5d", "1w", hours

### 2. Epic Keyword Filter

**Definitive keywords** (match instantly - unique to Epic EHR):
```
mychart, beaker, clindoc, caboodle, cogito, willow, cadence, prelude,
resolute, optime, hyperspace, care everywhere, epic orders, epic inpatient,
epic ambulatory, epic radiant, epic asap, epic bridges, epic certified,
epic certification, epic analyst, epic consultant, epic go-live,
epic implementation, epic build, epic trainer, epic support, epic ehr,
epic emr, epic systems
```

**"epic contract" requires additional validation:**
Must also contain a module OR position name to avoid false positives (e.g., construction contracts):
- Modules: orders, clindoc, beaker, radiant, willow, cadence, etc.
- Positions: analyst, consultant, trainer, certified, implementation, etc.

### 3. Job Posting Filter

**Must have job phrase:**
```
now hiring, we're hiring, #hiring, we're looking for, dm me, reach out if,
contract opportunity, contract needs, epic contract, apply now,
send your resume, immediate need, urgent need, currently seeking,
opportunities available, certification required
```

**Must also have contract indicator:**
```
contract, consultant, consulting, c2c, w2, 1099, month, duration
```

### 4. Persistent Dedup
- Tracks seen post URLs in `data/linkedin-seen-posts.json`
- Auto-prunes entries older than 30 days
- Second run shows "0 new posts (X already seen)"

## Email Format

**Summary section:**
- Total opportunities
- Priority count (Orders/ClinDoc/Inpatient)
- Hot modules breakdown

**Priority section (⭐):**
Posts mentioning Orders, ClinDoc, or Inpatient first

**Other modules section (📋):**
Everything else

## Cron Job

**Job:** `linkedin-epic-digest`
**Schedule:** 8am ET, Mon-Fri
**Session:** isolated (agentTurn)

## False Positive Lessons

| Problem | Solution |
|---------|----------|
| "epic" as adjective ("epic journey") | Require "epic + module" compounds |
| "EY" matching random posts | Removed short firm abbreviations |
| "orders" in supply chain posts | Require definitive Epic context |
| "epic contract" in construction | Require module/position confirmation |
| "looking for alternatives" | Tightened job phrases to specific patterns |
| Industry analysis posts | Require actual job posting language |

## Usage

```bash
# Full scrape (Apify → filter → output)
node scripts/linkedin-epic-scrape.js

# Process existing dataset
node scripts/process-linkedin-epic.js <dataset-id>
node scripts/process-linkedin-epic.js <dataset-id> --no-dedup

# Format as email
node scripts/format-epic-email.js <dataset-id>

# Send email
node scripts/format-epic-email.js | gog gmail send --to EMAIL --subject "..." --body-file -
```

## Stats (typical run)

| Stage | Count |
|-------|-------|
| Raw scraped | ~475 |
| This week only | ~196 |
| Epic + job filter | ~24 |
| After dedup | varies |
