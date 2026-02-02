# Mac Mini M4 Migration Plan

**Created:** 2026-02-02  
**Current:** MacBook Air (Ashley's)  
**Target:** Mac Mini M4  
**Status:** Pre-arrival planning

---

## 1. Pre-Migration Checklist

### Data Inventory

| Item | Location | Size | Method |
|------|----------|------|--------|
| Thanos workspace | `~/Projects/Thanos` | ~500MB | Git + Manual |
| OpenClaw config | `~/.openclaw/` | ~50MB | Manual copy |
| Environment files | `~/Projects/Thanos/.env` | <1MB | Secure transfer |
| Browser profiles | `~/.openclaw/browser/` | Varies | Manual copy |
| SQLite databases | `*.db` | <10MB | Git backup |
| Scripts | `~/Projects/Thanos/scripts/` | <10MB | Git |
| Skills | `~/Projects/Thanos/skills/` | ~100MB | Git |
| Credentials | 1Password | N/A | Already synced |

### Service Dependencies

| Service | Auth Method | Transfer Method |
|---------|-------------|-----------------|
| OpenClaw | Token in config | Copy `~/.openclaw/openclaw.json` |
| Anthropic | API key in .env | Transfer .env securely |
| Perplexity | API key in .env | Transfer .env securely |
| xAI/Grok | API key in .env | Transfer .env securely |
| Apify | API key in .env | Transfer .env securely |
| Supabase | Env vars | Transfer .env securely |
| Neon DB (WorkOS) | Connection string | Transfer .env securely |
| Neon DB (Memory V2) | Connection string | Transfer .env securely |
| Gmail/Calendar (gog) | OAuth tokens | Re-authenticate |
| Monarch Money | Credentials in .env | Transfer .env securely |
| Neo4j (Graphiti) | Docker container | Recreate on M4 |

---

## 2. Migration Steps

### Phase 1: Prepare Mac Mini M4 (Day 1)

1. **macOS Setup**
   ```bash
   # Initial setup
   - Create user account (jeremy)
   - Enable FileVault encryption
   - Configure Touch ID
   - Install Xcode Command Line Tools:
   xcode-select --install
   ```

2. **Install Homebrew**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # Add to PATH
   echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
   eval "$(/opt/homebrew/bin/brew shellenv)"
   ```

3. **Install Core Tools**
   ```bash
   # Node.js 22 (required for OpenClaw)
   brew install node@22
   brew link node@22
   
   # Python 3.13 (for Thanos tools)
   brew install python@3.13
   
   # Git
   brew install git
   
   # Other essentials
   brew install jq curl wget
   ```

4. **Install OpenClaw**
   ```bash
   npm install -g openclaw
   openclaw version
   ```

### Phase 2: Transfer Workspace (Day 1-2)

1. **Clone Thanos Repository**
   ```bash
   cd ~/Projects
   git clone git@github.com:Geralt1983/Thanos.git
   cd Thanos
   ```

2. **Create Python Virtual Environment**
   ```bash
   cd ~/Projects/Thanos
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Transfer Environment Files**
   ```bash
   # Securely transfer .env from old Mac
   # Option A: AirDrop
   # Option B: 1Password Secure Notes
   # Option C: USB drive with encryption
   
   # Verify .env is NOT tracked by git
   git check-ignore .env
   ```

4. **Install Node Dependencies**
   ```bash
   cd ~/Projects/Thanos
   npm install
   ```

### Phase 3: Configure Services (Day 2)

1. **OpenClaw Gateway**
   ```bash
   # Copy config from old Mac
   mkdir -p ~/.openclaw
   # Transfer ~/.openclaw/openclaw.json
   
   # Start gateway
   openclaw gateway start
   ```

2. **Docker Setup (for Neo4j/Graphiti)**
   ```bash
   # Install Docker Desktop for Mac
   # Or use Orbstack (lighter alternative)
   brew install --cask orbstack
   
   # Start Neo4j container
   docker run -d \
     --name neo4j-graphiti \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/graphiti_thanos_2026 \
     -v $HOME/neo4j/data:/data \
     neo4j:latest
   ```

3. **OAuth Re-authentication**
   ```bash
   # gog CLI (Google Calendar/Gmail)
   gog gmail list  # Will trigger OAuth flow
   
   # Gemini CLI
   gemini --help  # Will trigger OAuth on first use
   ```

4. **Test Core Services**
   ```bash
   # Test Perplexity search
   cd ~/Projects/Thanos
   .venv/bin/python Tools/perplexity_search.py "test query"
   
   # Test Grok search
   .venv/bin/python Tools/grok_search.py "test query"
   
   # Test morning brief
   .venv/bin/python Tools/morning-brief/morning_brief.py
   
   # Test WorkOS connection
   .venv/bin/python -c "from Tools.adapters.workos import WorkOSAdapter; import asyncio; asyncio.run(WorkOSAdapter().call_tool('get_clients', {}))"
   ```

### Phase 4: Restore Cron Jobs (Day 2)

```bash
# List all cron jobs on old Mac
openclaw cron list --json > ~/Desktop/cron-backup.json

# On new Mac, recreate via OpenClaw gateway
# Jobs are stored in config, should auto-restore if config copied correctly
```

### Phase 5: Browser Automation (Day 2-3)

1. **Install Chrome**
   ```bash
   brew install --cask google-chrome
   ```

2. **Setup OpenClaw Browser Profile**
   ```bash
   # Transfer browser profile data
   # Copy ~/.openclaw/browser/ from old Mac
   
   # Start managed browser
   openclaw browser start profile=openclaw
   ```

3. **Re-login to Key Sites**
   - LinkedIn (for Epic scraper)
   - Amazon (for order matching)
   - Any other authenticated sessions

### Phase 6: Validation & Testing (Day 3)

**Smoke Tests:**

```bash
# 1. Morning brief
.venv/bin/python Tools/morning-brief/morning_brief.py

# 2. Web search
.venv/bin/python Tools/web_search.py "test query"

# 3. LinkedIn Epic scraper
node scripts/linkedin-epic-scrape.js

# 4. Energy-aware tasks
.venv/bin/python Tools/energy_aware_tasks.py

# 5. Financial forecasting
.venv/bin/python Tools/financial_forecasting.py

# 6. WorkOS tasks
.venv/bin/python -c "from Tools.adapters.workos import WorkOSAdapter; import asyncio; print(asyncio.run(WorkOSAdapter().call_tool('get_tasks', {'status': 'active'})))"
```

**Integration Tests:**

1. Send test Telegram message → verify response
2. Trigger afternoon Twitter brief manually
3. Run LinkedIn scraper and verify email delivery
4. Check Graphiti knowledge graph connection
5. Verify Memory V2 search

---

## 3. Rollback Plan

**If migration fails:**

1. Keep Ashley's MacBook Air running until M4 is fully validated
2. Don't delete old data until 7-day validation period
3. Keep .env backup in 1Password Secure Notes

**Recovery procedure:**
```bash
# On old Mac, ensure latest git push
cd ~/Projects/Thanos
git add -A
git commit -m "Pre-migration backup $(date +%Y-%m-%d)"
git push origin main
```

---

## 4. Post-Migration Cleanup

**After 7 days of successful M4 operation:**

1. Wipe Thanos workspace from Ashley's MacBook Air
2. Remove sensitive .env files
3. Clear browser profiles
4. Uninstall OpenClaw: `npm uninstall -g openclaw`

---

## 5. Performance Optimizations for M4

**Take advantage of M4 performance:**

1. **Enable all cron jobs** - M4 can handle more concurrent tasks
2. **Increase subagent concurrency** in OpenClaw config:
   ```json
   "agents": {
     "defaults": {
       "subagents": {
         "maxConcurrent": 12  // Up from 8
       }
     }
   }
   ```

3. **Run local models** (if desired):
   - Ollama for local LLMs
   - Whisper for local transcription

4. **Database tuning:**
   - Neo4j heap size adjustments
   - SQLite performance settings

---

## 6. Troubleshooting Guide

### Common Issues

| Issue | Solution |
|-------|----------|
| OpenClaw won't start | Check node version: `node -v` (must be 22+) |
| Python imports fail | Activate venv: `source .venv/bin/activate` |
| gog auth fails | Clear tokens: `rm -rf ~/.config/gog/` and re-auth |
| Neo4j connection fails | Check Docker: `docker ps \| grep neo4j` |
| Cron jobs not firing | Check gateway status: `openclaw gateway status` |
| Browser profile missing | Recreate: `openclaw browser start profile=openclaw` |

### Validation Checklist

- [ ] OpenClaw gateway running
- [ ] Telegram messages working
- [ ] Morning brief generates successfully
- [ ] Web search (Perplexity + Grok) working
- [ ] WorkOS task CRUD operations
- [ ] Monarch Money connection
- [ ] Calendar/Gmail via gog
- [ ] LinkedIn Epic scraper
- [ ] All cron jobs firing on schedule
- [ ] Neo4j/Graphiti accessible
- [ ] Memory V2 search working
- [ ] Browser automation functional

---

## 7. Timeline Estimate

| Phase | Duration | Blocker Risk |
|-------|----------|--------------|
| Phase 1: Mac Mini setup | 2-3 hours | Low |
| Phase 2: Workspace transfer | 1-2 hours | Low |
| Phase 3: Service config | 2-4 hours | Medium (OAuth) |
| Phase 4: Cron jobs | 30 min | Low |
| Phase 5: Browser automation | 1-2 hours | Medium (logins) |
| Phase 6: Validation | 1-2 hours | Low |
| **Total** | **8-14 hours** | **Medium** |

**Recommended approach:** Spread over 2-3 days, don't rush.

---

## 8. Emergency Contacts

**If stuck:**
- OpenClaw Discord: https://discord.com/invite/clawd
- Thanos GitHub Issues: https://github.com/Geralt1983/Thanos/issues

---

**Status:** Ready to execute when Mac Mini M4 arrives.
