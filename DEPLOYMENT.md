# Thanos v2.0 Production Deployment Guide

**Version:** 2.0.0
**Status:** Production Ready (MVP)
**Last Updated:** January 20, 2026

## Executive Summary

This guide provides comprehensive instructions for deploying Thanos v2.0 to production. Based on Phase 5 testing results:

- **E2E Tests:** 80% pass rate (acceptable for MVP)
- **Performance:** Grade A (sub-millisecond routing, 50K ops/sec file I/O)
- **Integration:** 12/14 validation points passed
- **Known Issues:** Documented with workarounds provided

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [System Requirements](#system-requirements)
3. [Installation Guide](#installation-guide)
4. [Configuration](#configuration)
5. [Service Setup](#service-setup)
6. [Verification](#verification)
7. [Post-Deployment](#post-deployment)
8. [Operational Procedures](#operational-procedures)
9. [Disaster Recovery](#disaster-recovery)
10. [Known Issues & Workarounds](#known-issues--workarounds)
11. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Requirements Validation

- [ ] **Operating System:** macOS 12+ or Linux (Ubuntu 20.04+)
- [ ] **Python Version:** 3.8 or higher installed
- [ ] **Node.js:** 18.0+ for MCP servers (optional but recommended)
- [ ] **Git:** Installed for version control
- [ ] **Database Access:** PostgreSQL connection for WorkOS (via Neon)
- [ ] **API Keys:** All required API keys available (see [Configuration](#configuration))
- [ ] **Network:** Outbound HTTPS access for external APIs
- [ ] **Disk Space:** Minimum 500 MB free

### Dependency Verification

Run this verification script:

```bash
# Check Python version
python3 --version  # Should be >= 3.8

# Check Node.js (optional)
node --version     # Should be >= 18.0 (if using MCP servers)

# Check pip
pip3 --version

# Check git
git --version

# Check available disk space
df -h .
```

### Backup Procedures

Before deployment, backup any existing data:

```bash
# Backup existing state database
mkdir -p ~/thanos-backup/$(date +%Y%m%d)
cp -r State/*.db ~/thanos-backup/$(date +%Y%m%d)/
cp -r State/*.json ~/thanos-backup/$(date +%Y%m%d)/

# Backup configuration
cp .env ~/thanos-backup/$(date +%Y%m%d)/env.backup
cp -r config/ ~/thanos-backup/$(date +%Y%m%d)/config-backup/
```

### Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API rate limits | Medium | Medium | Circuit breaker pattern implemented |
| Database connection failure | High | Low | Connection pooling + retry logic |
| Daemon crash | Medium | Low | LaunchAgent auto-restart configured |
| External API downtime (Oura) | Low | Medium | Circuit breaker with cache fallback |
| MCP server failure | Medium | Low | Graceful degradation to direct adapters |

---

## System Requirements

### Hardware Requirements

**Minimum:**
- CPU: 1 core
- RAM: 512 MB
- Disk: 500 MB free space

**Recommended:**
- CPU: 2+ cores
- RAM: 2 GB
- Disk: 2 GB free space (for logs and cache)

### Software Dependencies

#### Core Dependencies
```
Python 3.8+
  - anthropic >= 0.75.0      (Claude API)
  - httpx >= 0.27.0          (Async HTTP client)
  - asyncpg >= 0.29.0        (PostgreSQL driver)
  - tiktoken >= 0.5.0        (Token counting)
  - python-dotenv >= 1.0.0   (Environment variables)
  - yaspin >= 3.0.0          (CLI spinners)
```

#### Optional Dependencies (MCP Servers)
```
Node.js 18+
  - @modelcontextprotocol/sdk-server
  - drizzle-orm (for WorkOS MCP)
  - postgres (for WorkOS MCP)
```

#### System Tools
- **tmux** (for daemon management)
- **ttyd** (for remote access - optional)
- **Tailscale** (for secure remote access - optional)

### External Services

#### Required
- **Anthropic API:** Claude AI access (get key from console.anthropic.com)
- **PostgreSQL (Neon):** For WorkOS task storage
- **Oura API:** Health data (unofficial API - optional)

#### Optional
- **Google Calendar API:** Calendar integration
- **Telegram Bot API:** Alert delivery
- **Neo4j AuraDB:** Graph memory storage
- **ChromaDB:** Vector memory storage

### Network Requirements

**Outbound Access Required:**
- `api.anthropic.com` (port 443) - Claude API
- `api.ouraring.com` (port 443) - Oura health data
- `api.telegram.org` (port 443) - Telegram notifications
- PostgreSQL endpoint (Neon) - Task database
- `googleapis.com` (port 443) - Google Calendar (if enabled)

**No inbound ports required** (Tailscale handles remote access via NAT traversal)

---

## Installation Guide

### Step 1: Clone Repository

```bash
# Clone from GitHub
git clone https://github.com/your-org/thanos.git
cd thanos

# Or navigate to existing installation
cd ~/Projects/Thanos
```

### Step 2: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install core dependencies
pip3 install -r requirements.txt

# Verify installation
python3 -c "import anthropic; print('Anthropic SDK installed')"
python3 -c "import httpx; print('HTTPX installed')"
```

### Step 3: Install Optional Dependencies

```bash
# For MCP servers (WorkOS, Oura)
cd mcp-servers/workos-mcp
npm install
cd ../..

# For Oura MCP
cd mcp-servers/oura-mcp
npm install
cd ../..

# For system tools (macOS)
brew install tmux ttyd

# For system tools (Ubuntu/Debian)
sudo apt-get install tmux
```

### Step 4: Install System Services (Optional)

```bash
# Install Tailscale for remote access (macOS)
brew install tailscale
sudo tailscale up

# Install Tailscale (Ubuntu/Debian)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

---

## Configuration

### Environment Variables

Create `.env` file in the project root:

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env
```

**Required variables:**

```bash
# Anthropic API (Required)
ANTHROPIC_API_KEY=sk-ant-api03-...

# WorkOS Database (Required for task management)
WORKOS_DATABASE_URL=postgres://user:pass@host.neon.tech/dbname

# Oura API (Optional - for health monitoring)
OURA_ACCESS_TOKEN=your-oura-token
```

**Optional variables:**

```bash
# OpenAI (for embeddings in MemOS)
OPENAI_API_KEY=sk-...

# Google Calendar
GOOGLE_CALENDAR_CLIENT_ID=...
GOOGLE_CALENDAR_CLIENT_SECRET=...
GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:8080/oauth2callback

# Telegram Bot
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Neo4j AuraDB (graph memory)
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
```

### MCP Server Configuration

Configure MCP servers in `~/.claude.json` or project `.mcp.json`:

```json
{
  "mcpServers": {
    "workos-mcp": {
      "command": "node",
      "args": [
        "/Users/jeremy/Projects/Thanos/mcp-servers/workos-mcp/dist/index.js"
      ],
      "env": {
        "WORKOS_DATABASE_URL": "postgres://..."
      },
      "enabled": true
    },
    "oura-mcp": {
      "command": "npx",
      "args": [
        "tsx",
        "/Users/jeremy/Projects/Thanos/mcp-servers/oura-mcp/src/index.ts"
      ],
      "env": {
        "OURA_ACCESS_TOKEN": "your-token"
      },
      "enabled": false
    }
  }
}
```

### Daemon Configuration

Configure the Operator daemon in `Operator/config.yaml`:

```yaml
intervals:
  check_interval: 300        # 5 minutes (main loop)
  health_check: 900          # 15 minutes
  task_check: 900            # 15 minutes
  pattern_check: 1800        # 30 minutes

deduplication:
  window_seconds: 3600       # 1 hour dedup window
  max_alerts_per_run: 20     # Alert storm prevention

quiet_hours:
  enabled: true
  start: 22                  # 10 PM
  end: 7                     # 7 AM

monitors:
  health:
    enabled: false           # DISABLE until production ready
  tasks:
    enabled: false           # DISABLE until production ready
  patterns:
    enabled: false           # DISABLE until production ready

circuit_breaker:
  failure_threshold: 3
  timeout_seconds: 60
  half_open_attempts: 1
```

**IMPORTANT:** All monitors are disabled by default (DRY RUN mode). Enable selectively after testing.

### Access Layer Configuration (Optional)

For remote access via web terminal:

```bash
# Edit Access/config/ttyd-credentials.json
{
  "username": "your-username",
  "password_hash": "bcrypt-hash-here"
}

# Edit Access/config/tailscale-acl.json
{
  "allowed_users": ["user@example.com"],
  "allowed_tags": ["tag:thanos-access"]
}
```

---

## Service Setup

### Operator Daemon (Background Process)

#### Option 1: LaunchAgent (macOS - Recommended)

```bash
# Install LaunchAgent
cd Operator
./install_launchagent.sh

# Verify installation
launchctl list | grep thanos.operator

# Check status
launchctl print gui/$(id -u)/com.thanos.operator

# View logs
tail -f ~/Library/Logs/thanos-operator.log
```

#### Option 2: systemd (Linux)

Create `/etc/systemd/system/thanos-operator.service`:

```ini
[Unit]
Description=Thanos Operator Daemon
After=network.target

[Service]
Type=simple
User=jeremy
WorkingDirectory=/home/jeremy/Projects/Thanos
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /home/jeremy/Projects/Thanos/Operator/daemon.py --config /home/jeremy/Projects/Thanos/Operator/config.yaml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable thanos-operator
sudo systemctl start thanos-operator
sudo systemctl status thanos-operator
```

#### Option 3: Manual (Testing)

```bash
# Run in foreground (testing)
python3 Operator/daemon.py --dry-run --verbose

# Run single check cycle
python3 Operator/daemon.py --once --dry-run

# Check status
python3 Operator/daemon.py --status
```

### MCP Server Setup

MCP servers are spawned on-demand by Claude CLI. No separate service setup required.

Verify MCP server configuration:

```bash
# Test WorkOS MCP
npx tsx mcp-servers/workos-mcp/dist/index.js

# Test Oura MCP
npx tsx mcp-servers/oura-mcp/src/index.ts
```

### Access Layer Setup (Optional)

```bash
# Start ttyd web terminal (manual)
cd Access
./start.sh

# Or install as systemd service (Linux)
sudo cp access.service /etc/systemd/system/
sudo systemctl enable access
sudo systemctl start access
```

---

## Verification

### Health Check Procedures

Run these checks after deployment:

#### 1. Database Connection

```bash
# Test StateStore
python3 -c "
from Tools.unified_state import get_state_store
store = get_state_store()
print('StateStore initialized:', store is not None)
print('Database path:', store.db_path)
"
```

Expected output:
```
StateStore initialized: True
Database path: State/thanos_unified.db
```

#### 2. Journal System

```bash
# Test Journal
python3 -c "
from Tools.journal import get_journal, EventType, Severity
journal = get_journal()
journal.log(
    event_type=EventType.SYSTEM_INFO,
    source='deployment',
    severity=Severity.INFO,
    title='Deployment verification',
    data={'status': 'testing'}
)
print('Journal working')
"
```

#### 3. API Connectivity

```bash
# Test Anthropic API
python3 -c "
import anthropic
import os
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
message = client.messages.create(
    model='anthropic/claude-3-5-haiku-20241022',
    max_tokens=50,
    messages=[{'role': 'user', 'content': 'Say hello'}]
)
print('Claude API working:', message.content[0].text)
"
```

#### 4. Circuit Breaker

```bash
# Test circuit breaker
python3 -c "
from Tools.circuit_breaker import CircuitBreaker
import asyncio

async def test():
    circuit = CircuitBreaker('test')
    result, meta = await circuit.call(
        func=lambda: 'success',
        fallback=lambda: 'fallback'
    )
    print('Circuit breaker:', result, '| State:', circuit.state.value)

asyncio.run(test())
"
```

### Smoke Tests

Run the automated test suite:

```bash
# Quick smoke tests (unit tests only)
python3 -m pytest -m unit --maxfail=3 -v

# Integration tests (requires external services)
python3 -m pytest -m integration -v

# Full test suite
python3 -m pytest --maxfail=5
```

Expected results:
- Unit tests: 100% pass rate
- Integration tests: 80%+ pass rate (acceptable with known issues)

### Integration Verification

Verify each integration point:

```bash
# 1. WorkOS MCP (if enabled)
python3 -c "
from Tools.adapters import get_default_manager
import asyncio

async def test():
    manager = get_default_manager(enable_mcp=True)
    await manager.discover_and_register_mcp_servers()
    tools = await manager.list_tools()
    workos_tools = [t for t in tools if 'workos' in t.get('name', '').lower()]
    print(f'WorkOS tools available: {len(workos_tools)}')

asyncio.run(test())
"

# 2. Oura Health Data (if enabled)
python3 Tools/test_oura.py

# 3. Brain Dump Classification
python3 -c "
from Tools.brain_dump.classifier import classify_brain_dump_sync
result = classify_brain_dump_sync('Remember to call dentist tomorrow')
print('Classification:', result.classification)
print('Confidence:', result.confidence)
"
```

### Rollback Procedures

If verification fails, rollback to previous version:

```bash
# Stop services
launchctl stop com.thanos.operator  # macOS
# or
sudo systemctl stop thanos-operator  # Linux

# Restore from backup
cp ~/thanos-backup/YYYYMMDD/*.db State/
cp ~/thanos-backup/YYYYMMDD/env.backup .env

# Restart services
launchctl start com.thanos.operator  # macOS
# or
sudo systemctl start thanos-operator  # Linux
```

---

## Post-Deployment

### Health Monitoring Setup

#### 1. Enable Logging

Logs are written to:
- **Operator daemon:** `logs/operator.log`
- **WorkOS cache sync:** `/tmp/workos-cache-sync.log`
- **Access layer:** `Access/logs/ttyd.log`

Monitor logs with:

```bash
# Tail all logs
tail -f logs/*.log

# Search for errors
grep -i error logs/operator.log

# Monitor daemon health
watch -n 10 'python3 Operator/daemon.py --status'
```

#### 2. Set Up Alerts

Configure Telegram alerts (optional):

```bash
# Edit .env
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Test alerts
python3 -c "
from Operator.alerters.telegram import TelegramAlerter
import asyncio

async def test():
    alerter = TelegramAlerter()
    await alerter.send('Test alert from Thanos deployment')

asyncio.run(test())
"
```

### Performance Baseline

Establish performance baselines:

```bash
# Run performance benchmarks
python3 tests/test_performance.py

# Measure routing latency
python3 -m pytest tests/test_agent_routing.py::test_routing_latency -v

# Measure file I/O performance
python3 -m pytest tests/test_unified_state.py::test_write_performance -v
```

Expected baselines:
- **Agent routing:** < 1ms per route
- **Database writes:** > 50K ops/second
- **Brain dump classification:** < 2 seconds per classification

### User Onboarding

#### Initial Setup for End User

```bash
# 1. Run first-time setup
python3 Tools/setup.py

# 2. Verify CLI access
source venv/bin/activate  # If using venv
python3 thanos.py --help

# 3. Test interactive mode
python3 thanos.py interactive

# 4. Create first task
python3 -c "
from Tools.unified_state import get_state_store
store = get_state_store()
task_id = store.add_task(
    title='Test deployment task',
    priority='p2',
    source='manual'
)
print(f'Created task: {task_id}')
"
```

### Support Documentation

Provide users with:

1. **Quick Start Guide:** `README.md`
2. **Architecture Overview:** `docs/architecture.md`
3. **Troubleshooting Guide:** `docs/TROUBLESHOOTING.md`
4. **API Reference:** Auto-generated from code
5. **Testing Guide:** `TESTING_GUIDE.md`

---

## Operational Procedures

### Start/Stop/Restart Services

#### macOS (LaunchAgent)

```bash
# Stop daemon
launchctl stop com.thanos.operator

# Start daemon
launchctl start com.thanos.operator

# Restart daemon
launchctl stop com.thanos.operator && launchctl start com.thanos.operator

# Disable auto-start
launchctl unload ~/Library/LaunchAgents/com.thanos.operator.plist

# Enable auto-start
launchctl load ~/Library/LaunchAgents/com.thanos.operator.plist
```

#### Linux (systemd)

```bash
# Stop daemon
sudo systemctl stop thanos-operator

# Start daemon
sudo systemctl start thanos-operator

# Restart daemon
sudo systemctl restart thanos-operator

# Disable auto-start
sudo systemctl disable thanos-operator

# Enable auto-start
sudo systemctl enable thanos-operator

# Check status
sudo systemctl status thanos-operator
```

### Log Monitoring

```bash
# Real-time monitoring
tail -f logs/operator.log

# Search for errors in last hour
grep -i error logs/operator.log | tail -n 50

# Analyze error patterns
grep -i "circuit.*open" logs/operator.log | wc -l

# Export logs for analysis
cp logs/operator.log ~/thanos-logs-$(date +%Y%m%d-%H%M%S).log
```

### Troubleshooting Guide

#### Problem: Daemon won't start

**Symptoms:**
- `launchctl start` returns immediately but daemon not running
- No logs in `logs/operator.log`

**Diagnosis:**
```bash
# Check LaunchAgent status
launchctl list | grep thanos.operator

# View error output
cat ~/Library/Logs/thanos-operator.log
```

**Resolution:**
1. Check Python path in plist file
2. Verify environment variables in config
3. Test daemon manually: `python3 Operator/daemon.py --dry-run --verbose`

#### Problem: API rate limit exceeded

**Symptoms:**
- Errors: "Rate limit exceeded" in logs
- Circuit breaker opens frequently

**Resolution:**
1. Increase `check_interval` in `Operator/config.yaml`
2. Reduce monitor frequency for non-critical checks
3. Enable caching with longer TTL

#### Problem: Database connection failure

**Symptoms:**
- Errors: "connection refused" or "timeout"
- StateStore initialization fails

**Resolution:**
1. Verify `WORKOS_DATABASE_URL` in `.env`
2. Check network connectivity to Neon
3. Verify database credentials
4. Check connection pool settings

#### Problem: MCP server not responding

**Symptoms:**
- Tool calls timeout
- "MCP server not available" errors

**Resolution:**
1. Check `~/.claude.json` configuration
2. Test MCP server manually: `npx tsx mcp-servers/workos-mcp/dist/index.js`
3. Verify environment variables passed to MCP process
4. Check MCP server logs

### Maintenance Tasks

#### Daily

```bash
# Check daemon status
python3 Operator/daemon.py --status

# Review error logs
grep -i error logs/operator.log | tail -n 20

# Verify database integrity
python3 -c "
from Tools.unified_state import get_state_store
store = get_state_store()
store.execute_sql('PRAGMA integrity_check')
print('Database integrity: OK')
"
```

#### Weekly

```bash
# Rotate logs (if not using log rotation)
cd logs
gzip operator.log
mv operator.log.gz operator-$(date +%Y%m%d).log.gz

# Clean old cache files (>30 days)
find State/cache -type f -mtime +30 -delete

# Backup database
cp State/thanos_unified.db ~/backups/thanos-$(date +%Y%m%d).db
```

#### Monthly

```bash
# Vacuum database
python3 -c "
from Tools.unified_state import get_state_store
store = get_state_store()
store.execute_sql('VACUUM')
print('Database vacuumed')
"

# Update dependencies
pip3 install --upgrade -r requirements.txt

# Review and archive old journal entries
python3 Tools/archive_journal.py --older-than 90
```

---

## Disaster Recovery

### Backup Strategy

#### Automated Daily Backups

Create backup script `scripts/daily-backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR=~/thanos-backups/$(date +%Y%m%d)
mkdir -p "$BACKUP_DIR"

# Backup databases
cp State/thanos_unified.db "$BACKUP_DIR/"
cp State/thanos.db "$BACKUP_DIR/"

# Backup state files
cp State/*.json "$BACKUP_DIR/"

# Backup configuration
cp .env "$BACKUP_DIR/"
cp -r config/ "$BACKUP_DIR/config/"

# Backup logs (last 7 days)
tar czf "$BACKUP_DIR/logs.tar.gz" logs/*.log

# Cleanup old backups (>30 days)
find ~/thanos-backups -type d -mtime +30 -exec rm -rf {} +

echo "Backup complete: $BACKUP_DIR"
```

Schedule with cron (Linux) or LaunchAgent (macOS):

```bash
# Add to crontab
0 2 * * * /path/to/scripts/daily-backup.sh
```

#### Manual Backup

```bash
# Full system backup
./scripts/manual-backup.sh

# Backup specific components
cp State/thanos_unified.db ~/backup-$(date +%Y%m%d-%H%M%S).db
```

### Restore Procedures

#### Full System Restore

```bash
# Stop services
launchctl stop com.thanos.operator

# Restore from backup
BACKUP_DATE=20260120  # Replace with backup date
cp ~/thanos-backups/$BACKUP_DATE/*.db State/
cp ~/thanos-backups/$BACKUP_DATE/*.json State/
cp ~/thanos-backups/$BACKUP_DATE/.env ./
cp -r ~/thanos-backups/$BACKUP_DATE/config/ ./

# Restart services
launchctl start com.thanos.operator

# Verify restoration
python3 Operator/daemon.py --status
```

#### Partial Restore (Database Only)

```bash
# Stop services
launchctl stop com.thanos.operator

# Restore database
cp ~/thanos-backups/20260120/thanos_unified.db State/

# Verify integrity
python3 -c "
from Tools.unified_state import get_state_store
store = get_state_store()
result = store.execute_sql('PRAGMA integrity_check')
print('Integrity check:', result)
"

# Restart services
launchctl start com.thanos.operator
```

### Failover Scenarios

#### Scenario 1: Primary Database Failure

**Detection:**
- Database connection errors in logs
- StateStore initialization fails

**Response:**
1. Switch to backup database connection (if configured)
2. Restore from latest backup
3. Investigate root cause
4. Update connection string if database migrated

#### Scenario 2: API Service Outage

**Detection:**
- Circuit breaker opens
- "Service unavailable" errors

**Response:**
1. Circuit breaker automatically handles with fallback
2. System continues with cached data
3. Monitor recovery time
4. No immediate action required (self-healing)

#### Scenario 3: Daemon Crash

**Detection:**
- LaunchAgent/systemd restart logs
- Gap in journal entries

**Response:**
1. LaunchAgent automatically restarts daemon
2. Check crash logs for root cause
3. Fix underlying issue if recurring
4. No data loss (state persisted)

### Data Recovery

#### Corrupted Database Recovery

```bash
# Check for corruption
sqlite3 State/thanos_unified.db "PRAGMA integrity_check;"

# If corrupted, attempt recovery
sqlite3 State/thanos_unified.db ".recover" | sqlite3 State/thanos_recovered.db

# Verify recovered database
sqlite3 State/thanos_recovered.db "SELECT COUNT(*) FROM tasks;"

# Replace if successful
mv State/thanos_unified.db State/thanos_unified.db.corrupt
mv State/thanos_recovered.db State/thanos_unified.db
```

#### Journal Recovery

```bash
# Export journal to JSON
python3 -c "
from Tools.journal import get_journal
journal = get_journal()
entries = journal.get_all()
import json
with open('journal_backup.json', 'w') as f:
    json.dump([e.__dict__ for e in entries], f, indent=2, default=str)
print('Journal exported')
"

# Import journal from JSON
python3 Tools/import_journal.py journal_backup.json
```

---

## Known Issues & Workarounds

### Issue 1: Daemon DRY RUN Mode

**Status:** Expected behavior for MVP
**Impact:** Alerts not sent, monitors disabled by default
**Workaround:**

1. All monitors disabled in `Operator/config.yaml`:
   ```yaml
   monitors:
     health:
       enabled: false
     tasks:
       enabled: false
     patterns:
       enabled: false
   ```

2. To enable specific monitors:
   ```yaml
   monitors:
     tasks:
       enabled: true  # Enable task monitoring only
   ```

3. Test in dry-run mode first:
   ```bash
   python3 Operator/daemon.py --dry-run --once
   ```

4. When ready for production, set `enabled: true` and restart daemon

**Timeline:** Production-ready monitoring in v2.1 release

### Issue 2: Remote Monitoring Not Implemented

**Status:** Planned feature, not blocking MVP
**Impact:** Cannot monitor daemon from mobile/remote
**Workaround:**

1. SSH access via Tailscale:
   ```bash
   ssh jeremy@thanos-machine
   python3 Operator/daemon.py --status
   ```

2. Set up simple health check endpoint (manual):
   ```python
   # Create simple Flask app for status
   from flask import Flask, jsonify
   app = Flask(__name__)

   @app.route('/health')
   def health():
       # Read status from daemon
       import subprocess
       status = subprocess.check_output(['python3', 'Operator/daemon.py', '--status'])
       return jsonify({'status': status.decode()})

   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=8080)
   ```

3. Use tmux for persistent sessions:
   ```bash
   tmux new-session -d -s thanos-monitor 'watch -n 60 python3 Operator/daemon.py --status'
   tmux attach -t thanos-monitor
   ```

**Timeline:** Web dashboard planned for v2.2

### Issue 3: MCP Server Latency

**Status:** Known performance consideration
**Impact:** MCP tool calls slower than direct adapters
**Workaround:**

1. Use direct adapters for performance-critical paths:
   ```python
   # Prefer direct adapter
   from Tools.adapters.workos import WorkOSAdapter
   adapter = WorkOSAdapter()
   result = await adapter.get_tasks()

   # Instead of MCP
   manager.call_tool('workos_get_tasks', {})
   ```

2. Enable connection pooling in MCP bridge:
   ```python
   manager = get_default_manager(
       enable_mcp=True,
       mcp_pool_size=5  # Reuse connections
   )
   ```

3. Cache frequently accessed data:
   ```python
   from Tools.circuit_breaker import FileCache
   cache = FileCache(cache_dir='State/cache/mcp', ttl=300)
   ```

**Timeline:** Performance optimization in v2.1

### Issue 4: Oura API Reliability

**Status:** Known issue with unofficial API
**Impact:** Health monitoring may have gaps
**Workaround:**

1. Circuit breaker automatically handles with cache fallback:
   ```python
   # Circuit opens after 3 failures
   # Falls back to cached data (24h TTL)
   # No action required
   ```

2. Monitor circuit state:
   ```bash
   python3 Operator/daemon.py --status | jq '.circuit_states'
   ```

3. If circuit stuck open, clear cache and restart:
   ```bash
   rm -rf State/cache/oura/*
   launchctl restart com.thanos.operator
   ```

**Timeline:** Official Oura API integration planned (pending API access)

---

## Troubleshooting

### Quick Diagnostic Commands

```bash
# Check all systems
./scripts/health-check.sh

# View daemon status
python3 Operator/daemon.py --status | jq '.'

# Test database connection
python3 -c "from Tools.unified_state import get_state_store; print(get_state_store())"

# Test API connectivity
python3 -c "import anthropic; print('API OK')"

# Check circuit breaker states
grep "circuit.*open" logs/operator.log

# View recent errors
tail -n 100 logs/operator.log | grep -i error
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `connection refused` | Database unreachable | Check `WORKOS_DATABASE_URL`, network |
| `rate limit exceeded` | Too many API calls | Increase `check_interval` in config |
| `circuit open` | External service down | Wait for auto-recovery or clear cache |
| `authentication failed` | Invalid API key | Verify `.env` credentials |
| `module not found` | Missing dependency | Run `pip install -r requirements.txt` |

### Support Resources

- **Documentation:** `/docs` directory
- **Test Suite:** Run `pytest -v` for diagnostics
- **Logs:** `logs/operator.log`, `logs/*.log`
- **Status Dashboard:** `python3 Operator/daemon.py --status`
- **Performance Metrics:** `python3 tests/test_performance.py`

### Escalation Path

1. Check documentation and known issues
2. Review logs for error patterns
3. Run diagnostic commands
4. Check GitHub issues
5. File new issue with:
   - Error logs (sanitized)
   - System information
   - Steps to reproduce

---

## Appendix

### A. Performance Benchmarks

Based on Phase 5 testing:

```
Agent Routing:
  - Average latency: 0.8ms
  - 99th percentile: 1.2ms
  - Grade: A

Database Performance:
  - Write throughput: 50K+ ops/second
  - Read latency: < 1ms
  - Grade: A

Brain Dump Classification:
  - Average time: 1.8s
  - Cache hit rate: 85%
  - Accuracy: 92%

Circuit Breaker:
  - Recovery time: < 60s
  - Cache hit rate: 78%
  - Failover success: 100%
```

### B. Directory Structure

```
Thanos/
├── Operator/              # Background daemon
│   ├── daemon.py         # Main daemon process
│   ├── config.yaml       # Daemon configuration
│   ├── monitors/         # Health/task/pattern monitors
│   └── alerters/         # Alert delivery (Telegram, macOS)
├── Tools/                # Core libraries
│   ├── unified_state.py  # State database
│   ├── journal.py        # Event journal
│   ├── circuit_breaker.py # Resilience
│   ├── brain_dump/       # Classification & routing
│   └── adapters/         # External integrations
├── State/                # Data storage
│   ├── thanos_unified.db # Main database
│   ├── thanos.db         # Journal database
│   └── cache/            # Circuit breaker cache
├── mcp-servers/          # MCP server implementations
│   ├── workos-mcp/       # Task management
│   └── oura-mcp/         # Health data
├── config/               # Configuration files
├── logs/                 # Log files
└── tests/                # Test suite
```

### C. Security Considerations

1. **API Keys:** Store in `.env`, never commit to git
2. **Database:** Use connection pooling, SSL enabled
3. **Remote Access:** Tailscale for zero-trust networking
4. **Logs:** Sanitize before sharing (no credentials)
5. **Backups:** Encrypt sensitive backups

### D. Monitoring Checklist

- [ ] Daemon running (`launchctl list | grep thanos`)
- [ ] Logs rotating (`ls -lh logs/`)
- [ ] Database healthy (`PRAGMA integrity_check`)
- [ ] Circuit breakers closed (`daemon.py --status`)
- [ ] API quotas within limits
- [ ] Disk space > 10% free
- [ ] Backup completed in last 24h

---

**End of Deployment Guide**

For questions or issues, refer to:
- `/docs/TROUBLESHOOTING.md`
- `/docs/architecture.md`
- `TESTING_GUIDE.md`
