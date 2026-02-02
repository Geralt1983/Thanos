# Apify Skill

Run Apify actors (web scrapers) via their REST API.

## Setup

1. Get API token from https://console.apify.com/account/integrations
2. Set environment variable: `export APIFY_TOKEN=your_token`

## Usage

### Run an Actor
```bash
curl -X POST "https://api.apify.com/v2/acts/ACTOR_ID/runs?token=$APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": {...}}'
```

### Get Run Results
```bash
curl "https://api.apify.com/v2/actor-runs/RUN_ID/dataset/items?token=$APIFY_TOKEN"
```

### Popular LinkedIn Actors
- `curious_coder/linkedin-post-search-scraper` - Search LinkedIn posts
- `anchor/linkedin-people-search` - Search LinkedIn people
- `bebity/linkedin-profile-scraper` - Scrape profiles

## Example: LinkedIn Post Search

```bash
# Start the scraper
RUN_ID=$(curl -s -X POST "https://api.apify.com/v2/acts/curious_coder~linkedin-post-search-scraper/runs?token=$APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"searchTerms": ["Epic EHR contract"], "maxResults": 20}' | jq -r '.data.id')

# Wait for completion (poll status)
sleep 30

# Get results
curl -s "https://api.apify.com/v2/actor-runs/$RUN_ID/dataset/items?token=$APIFY_TOKEN"
```

## Notes
- Actors are billed per compute unit
- LinkedIn scrapers may require cookies/session for best results
- Check actor docs for specific input schemas
