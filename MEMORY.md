# MEMORY.md - Long-Term Memory

## Technical Lessons

### Node.js
- **Use Node 22, not 25** - Node 25 has ESM module resolution bugs that break ClawdHub and other tools

### Apify / Web Scraping
- **Free LinkedIn actor:** `supreme_coder/linkedin-post` - no rental or cookies required
- Input schema uses `urls` array (not `searchTerms`) - pass LinkedIn search URLs directly
- Many other LinkedIn actors (`curious_coder/*`, `pratikdani/*`) require rental fees

### LinkedIn Epic Scraper
- **Docs:** `docs/linkedin-epic-scraper.md`
- **"epic contract" alone is too generic** - catches construction contracts; require module/position confirmation
- **Definitive Epic keywords:** mychart, beaker, clindoc, caboodle, cogito, willow, cadence, prelude, resolute, optime (unique to Epic EHR)
- **Job phrase matching:** avoid generic phrases like "looking for a" (matches "looking for alternatives")
- **Firm abbreviations:** "EY", "CTG", "PwC" too short - cause false positives
- **Recency filter:** parse `timeSincePosted` ("1d", "2w", "1mo") - reject >1 week

### Browser Automation
- OpenClaw managed browser (`profile=openclaw`) persists logins - LinkedIn, Kimi, Amazon, etc.
- Element refs can go stale between snapshots - use JavaScript `evaluate` with `document.querySelector()` as fallback
- Browser Use cloud has issues with special characters in passwords via shell expansion
- **Amazon extraction:** Use `document.body.innerText` then parse "ORDER PLACED" blocks

### Amazon Order Matcher
- **Skill:** `skills/amazon-order-matcher/`
- **Purpose:** Match Amazon orders to Monarch transactions by amount for accurate categorization
- **Browser profile:** `openclaw` (Amazon login persisted, no MFA on repeat visits)
- **Data:** `skills/amazon-order-matcher/data/amazon_orders_2026.json`
- **Category IDs:**
  - Baby: `225123032227674020`
  - Household: `162959461244237526`
  - Business expense: `178462006985127548`
  - Jeremy Spending: `162782301949818821`
  - Transportation: `162777981853398770`
- **Cron:** Weekly Sunday 8pm ET - `amazon-weekly-reconciliation`

### Codex CLI
- **Config:** `~/.codex/config.toml`
- **Remove MCP servers** if they fail handshake - Codex works without them
- **Trust levels:** `trusted` or `untrusted` (not `full-auto`)
- **Spam skills:** Check `~/.codex/skills/` for ad-like skills (e.g., `offer-k-dense-web`)

### Graphiti Knowledge Graph
- Neo4j credentials: user=neo4j, password=graphiti_thanos_2026
- MCP endpoint: http://localhost:8000/sse
- Neo4j UI: http://localhost:7474

### Memory V2 (Vector Store)
- **Storage:** Neon PostgreSQL with pgvector
- **MCP Server:** `mcp-servers/memory-v2-mcp/` (stdio)
- **Python:** Uses `.venv/bin/python` (fixed 2026-02-01)
- **Direct call:** `.venv/bin/python -c "from Tools.memory_v2.mcp_tools import memory_search; ..."`
- **Legacy docs:** `memory/README.md` (mem0 pipeline)

#### Architecture (Updated 2026-02-01)
- **Embeddings:** Voyage AI `voyage-3` (1024 dimensions)
  - Previous: OpenAI `text-embedding-3-small` (1536 dims)
  - Fallback to OpenAI if `USE_VOYAGE=false` in .env
  - **CURRENT:** Using OpenAI (38k existing memories at 1536 dims)
  - Voyage migration blocked — table dimension mismatch
  - Future: re-embed script or dual-table approach
- **Unified Capture:** `Tools/memory_v2/unified_capture.py`
  - Single entry point for Memory V2 + Graphiti routing
  - Auto-detects content type (decision/fact/relationship/pattern)
  - Decisions + learnings → both systems
  - Facts + patterns → Memory V2 only
  - Relationships → Graphiti only
- **Heat Decay:** Advanced time + access frequency formula
  - Formula: `heat = base_score * decay_factor^days * log(access_count + 1)`
  - Tracks: created_at, access_count, last_accessed in payload
  - Cron: Daily at 3am via `apply_decay()`
  - Frequently accessed memories stay hot longer
- **Auto-Deduplication:** `Tools/memory_v2/deduplication.py`
  - Finds duplicates via cosine similarity (threshold: 0.95)
  - Merge strategy: keep recent, combine metadata, sum access counts
  - Cron: Weekly Sunday 3am (recommended)
  - Always dry-run first: `--dry-run --verbose`
- **Migration Guide:** `Tools/memory_v2/MIGRATION.md`

## LinkedIn Epic Contract Scraper

**Purpose:** Daily scraping of LinkedIn for Epic EHR consulting/contract opportunities

**Architecture:**
```
Apify Actor (supreme_coder/linkedin-post)
    ↓ (scrapes 9 search terms)
Raw Posts (~2,400)
    ↓ (filter: recency ≤7 days)
This Week (~2,100)
    ↓ (filter: Epic keywords + job phrases)
Relevant Posts (~50)
    ↓ (dedup against seen_posts.json)
New Posts (0-10)
    ↓ (save to Supabase)
Email Digest
```

**Key Files:**
- `scripts/linkedin-epic-scrape.js` - Main scraper (Apify → filter → output)
- `data/linkedin-seen-posts.json` - Persistent dedup (auto-prunes 30 days)
- `docs/linkedin-epic-scraper.md` - Full documentation

**Email sending:**
- Uses `gog gmail send --account jkimble1983@gmail.com`
- Account parameter required (fixed 2026-02-04)

**Filtering Logic:**

1. **Recency:** ≤7 days only (rejects "2w", "1mo", etc.)
2. **Epic Keywords:** Definitive terms (mychart, beaker, clindoc, etc.) OR "epic contract" + module/position
3. **Job Phrases:** Must contain hiring language + contract indicator
4. **Deduplication:** Tracks URLs, prevents re-sending same posts

**Cron Job:** `linkedin-epic-digest`
- Schedule: 8am ET Mon-Fri
- Command: `node scripts/linkedin-epic-scrape.js`
- Delivery: Email via gog to jkimble1983@gmail.com
- Fallback: Report to Telegram if no new posts

**Failure Modes:**
- Browser automation: DO NOT USE (unreliable for cron)
- Perplexity/Grok: DO NOT USE (not designed for LinkedIn posts)
- Always use Apify actor `supreme_coder/linkedin-post`

**Stats (typical run):**
- Raw scraped: ~2,400 posts
- After filters: ~50 relevant
- After dedup: 0-10 new posts
- Runtime: ~2-3 minutes

## Infrastructure

### Memory Capture (Graphiti)
- **Strategy:** Heartbeat-based capture (not nightly breathing)
- **Trigger:** Each heartbeat checks for meaningful conversation, extracts entities/facts
- **Command:** `mcporter call "http://localhost:8000/sse.add_episode" name="..." episode_body="..." --allow-http`
- **Startup:** `scripts/start-graphiti.sh` or manually via mcp-graphiti directory
- **State:** `memory/heartbeat-state.json` tracks last capture

### Location
- **Home:** King, NC
- **Timezone:** America/New_York
- **Used For:** Weather monitoring, location-based services

### Web Search

**Primary:** `.venv/bin/python Tools/web_search.py "query"` - Unified search (Perplexity + conditional Grok X)

**How it works:**
1. Always runs Perplexity (reliable, cited)
2. Auto-detects if query benefits from X pulse (AI, tech, trending, news keywords)
3. Appends Grok X findings when relevant

**Flags:**
- `--force-x` — Always include X search
- `--skip-x` — Never include X search  
- `-v` — Verbose (show tool calls)

**Individual tools (if needed):**
- `perplexity_search.py "query"` — Web only
- `grok_search.py "query"` — X/Twitter only (requires grok-4)

**Cost notes:**
- Perplexity: ~$0.005/query
- Grok-4 with tools: ~$0.05-0.15/query (only fires when relevant)

**Deprecated/Broken:**
- Gemini CLI: Rate-limited, OAuth issues
- Grok-3 API: No server-side tools, no live web access

### Active Cron Jobs
- `morning-brief` - 8am ET Mon-Fri - SITREP with energy, calendar, Monarch balances, tasks, weather
- `morning-tech-digest` - 10am ET daily - Deliver tech digest to Telegram
- `linkedin-epic-digest` - 8am ET Mon-Fri - Epic contract post scraping
- `graphiti-daily-digest` - 10pm ET daily - Knowledge graph summary
- `nightly-tech-search` - 11pm ET daily - Grok API search for OpenClaw/moltbot updates + AI news
- `memory-heat-decay` - 3am ET daily - Time + access decay on Memory V2
- `memory-deduplication` - 3am ET Sunday - Merge similar memories (>0.95 cosine)
- `monarch-weekly-reconciliation` - 9am ET Sunday - Review uncategorized transactions
- `amazon-weekly-reconciliation` - 8pm ET Sunday - Match Amazon orders to Monarch transactions

### Calendar Management
- **Work Calendar ID:** `6138b022643cdc3f3c35656282ef4b2bc67e76bf3be77e403fe12f42524724aa@group.calendar.google.com`
- **Correct gog Calendar CLI Syntax:**
  - List events: `gog calendar events list --account jeremy@kimbleconsultancy.com`
  - Add event: TO BE CONFIRMED (current method unknown)
- **Critical Rule:** Always add work meetings to the work calendar

### Credentials
- Apify: user `knightly_issue`, ID `XzsBgZyeigzCTboMd` (paid plan)
- Supabase: project `dmanuzntzlreurhtdcdd`, table `epic_contract_opportunities`
- **gog CLI accounts:**
  - `jkimble1983@gmail.com` - Personal (calendar, contacts, drive, gmail)
  - `jeremy@kimbleconsultancy.com` - Work/Client (full suite: gmail, calendar, chat, drive, docs, sheets, etc.)
- 1Password Google creds: Item ID `kpowkgmnqbsrmyivy43bqjkp5y`

### Monthly Budgets (Monarch)
Based on January 2026 spending analysis (zero-based):
- **Total monthly:** $29,750/month
- **Fixed (housing/debt):** $8,050
- **Variable:** $21,700

Key variable categories:
- Groceries: $2,700 (Walmart goes here)
- Food Out: $3,000 (restaurants + coffee)
- Business/Work: $3,300
- Baby: $1,000
- Household: $950
- Transportation: $950
- Variable/Discretionary: $6,050

See `skills/Productivity/references/budgets.md` for category IDs.

### Financial Forecasting
- **Tool:** `Tools/financial_forecasting.py`
- **Docs:** `skills/Productivity/references/financial-forecasting.md`
- **Features:**
  - Velocity-based spending detection (daily burn rate)
  - Cash runway calculation
  - End-of-month balance projection
  - ADHD impulse cluster detection
  - Category budget tracking
- **Warning levels:**
  - 🔴 CRITICAL: Runway <15 days, projected negative
  - ⚠️ WARNING: Category >100%, high burn rate
  - ℹ️ INFO: Impulse patterns, approaching limits

### Synapse OpenClaw Integration ✅ WORKING
- **Agent:** `synapse` (separate from main, think, sonnet)
- **Workspace:** `~/.openclaw/workspaces/synapse` (minimal, no Thanos files)
- **Model:** Haiku with Sonnet fallback
- **Key fix:** The `main` agent's workspace (AGENTS.md, SOUL.md, HEARTBEAT.md) contains "reply HEARTBEAT_OK" instructions that were overriding Synapse's system prompt
- **Solution:** Created dedicated synapse agent with empty workspace
- **Fallback:** HEARTBEAT_OK detection in Synapse converts heartbeat responses to friendly chat

### Synapse Workspace Files (Critical)
The synapse workspace must explicitly override OpenClaw's silent reply behavior:
- **AGENTS.md:** "NEVER use NO_REPLY or HEARTBEAT_OK, ALWAYS respond"
- **HEARTBEAT.md:** "This is a CHAT interface, you MUST respond to every message"
- Without these overrides, OpenClaw's base system prompt causes NO_REPLY → "No response from OpenClaw."

### WorkOS MCP Server (Full CRUD Access) ✅ VERIFIED WORKING
- **Location:** `/Users/jeremy/Projects/WorkOS-v3/mcp-server/`
- **Start script:** `/Users/jeremy/Projects/WorkOS-v3/mcp-server/start.sh` (loads .env.local)
- **Tools:** get_all_client_pipelines, search_tasks, create_task, update_task, complete_task, delete_task, promote_task, demote_task, suggest_next_task, get_avoidance_report, get_task_history
- **Call via mcporter:** `mcporter call --stdio "/Users/jeremy/Projects/WorkOS-v3/mcp-server/start.sh" <tool_name> <args>`
- **Example:** `mcporter call --stdio "/Users/jeremy/Projects/WorkOS-v3/mcp-server/start.sh" create_task title="Test task" client_name="Raleigh"`
- **Synapse Integration:** When responding through OpenClaw to Synapse, I call this MCP server for full CRUD

### WorkOS Tasks (Work Management)
- **Adapter:** `Tools/adapters/workos.py`
- **Point System (Fibonacci-ish):**
  - **1 point:** Trivial — quick reply, lookup, < 15 min
  - **2 points:** Low complexity — simple task, 15-30 min
  - **4 points:** Moderate complexity — multi-step, requires thought, 30-90 min
  - **7 points:** High complexity — significant effort, multiple components, 2+ hours
- **Daily targets:** Minimum 12 pts, target 18 pts
- **My role:** Create tasks with appropriate points, track completion, surface priorities

### Todoist (Task Management)
- **CLI:** `todoist` (todoist-ts-cli)
- **Config:** `~/.config/todoist-cli/config.json`
- **Projects:** Inbox, Personal, Someday (personal only — work uses separate system)
- **My role:** Full management — capture, prioritize, review, remind
- **Daily:** Surface top 3 priorities each morning
- **Weekly:** Sunday review — clear inbox, plan week

### Energy-Aware Task System
- **Location:** `Tools/energy_aware_tasks.py`
- **Purpose:** Automatically weights tasks against Oura energy levels
- **Integration:** Morning briefs, heartbeats, on-demand
- **Command:** `.venv/bin/python Tools/energy_aware_tasks.py`
- **Sources:** WorkOS (work tasks) + Todoist (personal tasks) + Oura (energy state)
- **Logic:** Classifies tasks by complexity, matches to readiness score, defers complex tasks on low-energy days
- **Always active:** Tasks are ALWAYS weighted against energy - no manual prioritization

### Model Selection Strategy (Updated 2026-02-03)

**Architecture:**
- **Default:** Haiku (cheap, fast) — `agents.defaults.model.primary`
- **Fallbacks:** Sonnet → Opus (auto-failover)
- **Per-task override:** Cron jobs can specify `model` in payload

**Interactive (Main Session):**
- Start on Haiku
- Dynamic escalation via `session_status(model=X)` when complexity detected
- Thresholds: 0-0.25 Haiku, 0.25-0.75 Sonnet, 0.75-1.0 Opus

**Cron Job Model Assignments:**
| Model | Jobs |
|-------|------|
| **Opus** | nightly-scaling-brainstorm (strategic thinking) |
| **Sonnet** | linkedin-epic-digest, morning-brief, overnight-openclaw-scout, nightly-moonshot-research, weekly-analysis, weekly-cash-forecast-email, monarch-weekly-reconciliation |
| **Haiku** | Calendar briefs, todoist tasks, memory decay, simple alerts |

**Why not agents.list?**
- `agents.list` is for multi-agent setups (named workers)
- Single main agent with dynamic needs → model payload + session_status
- Current approach is optimal for cost/capability tradeoff

### ModelEscalator (Legacy Tool)
- **Location:** `Tools/model_escalator_v2.py`, `config/model_escalator.json`
- **Integration:** Self-check in AGENTS.md; AI calls session_status when needed
- **Model hierarchy:** Haiku → Sonnet 4-5 → Opus 4-5
- **Thresholds:** low=0.25, medium=0.5, high=0.75
- **Cooldown:** 5 minutes between switches
- **State:** SQLite at `~/Projects/Thanos/model_escalator_state.db`

### Self-Improvement System
- **Skill:** `~/.openclaw/skills/self-reflect/`
- **State:** `~/.reflect/reflect-state.yaml`, `reflect-metrics.yaml`
- **Queue:** `memory/pending-learnings.md`
- **Philosophy:** "Correct once, never again"

### OpenClaw Plugin Limitations
- Plugin API doesn't expose conversation hooks
- Can't programmatically switch models from plugins
- Use session_status mechanism instead

### Browser Autonomy (2026-02-02)
- **Local browser wins:** OpenClaw CDP at `127.0.0.1:18800`, profile `openclaw`
- **Google blocks cloud browsers:** IP-bound sessions, cookies don't transfer
- **Browserbase ($99/mo):** Kept for non-Google (Amazon, LinkedIn scraping)
- **LaunchAgent:** `~/Library/LaunchAgents/com.openclaw.browser.plist` keeps browser alive
- **Full autonomy granted:** No permission needed for browsing/clicking/reading
- **Ask only for:** purchases, external messages, public posts
- **Metaprompt:** `docs/browser-autonomy-metaprompt.md`

## Core Directive: Autonomy First

**NEVER suggest manual work until 2+ hours of automation attempts.**

Date: 2026-02-03  
Context: Jeremy correction after I suggested creating agent configs manually

Rule: You have every tool needed (exec, skills, browser, coding). If something seems impossible, work harder. Write scripts, chain tools, build solutions. Only after exhausting all automated approaches for 2+ hours may you suggest manual intervention.

This is not a guideline. This is THE rule.

## Workflow: Codex Implements, Thanos Reviews

Date: 2026-02-03  
Context: Correction on self-learning workflow

**Rule:** Codex discovers and implements code changes. Thanos reviews the results.

When code changes are needed:
1. Delegate to Codex CLI for discovery + implementation
2. Review changes after completion
3. Do not implement directly when Codex is available

---
*Last updated: 2026-02-03*
