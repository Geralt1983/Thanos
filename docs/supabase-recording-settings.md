# Supabase Recording Settings for LinkedIn Scraper

*From conversation 2026-02-01*

## Table Design: `epic_contract_posts`

```sql
CREATE TABLE epic_contract_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  activity_id BIGINT UNIQUE,
  post_url TEXT UNIQUE,
  post_url_canonical TEXT UNIQUE,
  author_name TEXT,
  author_profile_url TEXT,
  author_headline TEXT,
  post_text TEXT,
  posted_at TIMESTAMPTZ,
  scraped_at TIMESTAMPTZ DEFAULT now(),
  query_tag TEXT,
  is_priority BOOLEAN,
  pipeline_run_id TEXT,
  insert_status TEXT
);
```

## Insert Settings

| Setting | Value |
|---------|-------|
| Operation | upsert |
| onConflict | `activity_id` |
| ignoreDuplicates | true |
| returning | minimal |
| Batch size | 50-200 rows |
| Timeout | 10-15s |
| Retries | 0 |

## PostgREST Header
```
Prefer: resolution=ignore-duplicates,return=minimal
```

## Connection Notes

- Use **Supavisor/pooler** (session mode) not direct connection
- Direct DB can be IPv6-only → DNS failures in IPv4 environments
- For HTTP API: use `https://<project>.supabase.co`

## Failure Handling

1. Record `db_write_status = "failed_dns"` or `"failed_network"`
2. Save pending inserts to `pending_inserts.json`
3. Next run: attempt flush pending first, no retries within run

## Status Monitoring

- RSS feed: https://status.supabase.com/history.rss

## TODO

- [ ] Get Supabase project URL and anon key
- [ ] Create table in Supabase
- [ ] Configure MCP server in `.mcp.json`
- [ ] Add recording step to `linkedin-epic-scrape.js`
