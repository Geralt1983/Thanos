# Operator Daemon Architecture - Thanos v2.0 Phase 3

**Design Date:** 2026-01-20
**Status:** Design
**Designer:** System Architecture Designer

---

## 1. Executive Summary

The Operator daemon is a background process that continuously monitors health metrics, task deadlines, and procrastination patterns. It provides proactive alerts via Telegram and macOS notifications while integrating with existing MCP servers (WorkOS, Oura) and the brain dump pipeline.

**Key Design Principles:**
- **Autonomy:** Runs independently of CLI sessions
- **Resilience:** Graceful degradation when services unavailable
- **Observability:** Comprehensive logging and health monitoring
- **Modularity:** Clear separation between monitors, alerters, and orchestration
- **Configuration:** YAML-driven for easy customization

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Operator Daemon Process                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Orchestration Layer                       │ │
│  │  - Config Manager (YAML)                               │ │
│  │  - Daemon State Manager (daemon_state.json)            │ │
│  │  - Check Scheduler (interval-based)                    │ │
│  │  - Alert Deduplication (1-hour window)                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                 Monitor Layer                          │ │
│  │                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │ Health       │  │ Task         │  │ Pattern     │ │ │
│  │  │ Monitor      │  │ Monitor      │  │ Monitor     │ │ │
│  │  │              │  │              │  │             │ │ │
│  │  │ • Readiness  │  │ • Deadlines  │  │ • Procrast. │ │ │
│  │  │ • Sleep      │  │ • Overdue    │  │ • Energy    │ │ │
│  │  │ • HRV        │  │ • Commitment │  │ • Trends    │ │ │
│  │  │ • Stress     │  │   tracking   │  │             │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Data Adapter Layer                        │ │
│  │                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │ Oura MCP     │  │ WorkOS MCP   │  │ State Files │ │ │
│  │  │ Adapter      │  │ Adapter      │  │ Adapter     │ │ │
│  │  │              │  │              │  │             │ │ │
│  │  │ • Cache DB   │  │ • Cache DB   │  │ • JSON      │ │ │
│  │  │ • API calls  │  │ • Postgres   │  │ • Local FS  │ │ │
│  │  │   (fallback) │  │   (primary)  │  │             │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                 Alerter Layer                          │ │
│  │                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │ Telegram     │  │ macOS        │  │ Journal     │ │ │
│  │  │ Alerter      │  │ Notification │  │ Logger      │ │ │
│  │  │              │  │              │  │             │ │ │
│  │  │ • Bot API    │  │ • osascript  │  │ • Event     │ │ │
│  │  │ • Markdown   │  │ • AppleScript│  │   logging   │ │ │
│  │  │ • Priority   │  │ • Priority   │  │ • Always on │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Circuit Breaker & Error Handling          │ │
│  │  - Exponential backoff for MCP failures                │ │
│  │  - Graceful degradation (cache → direct API → skip)    │ │
│  │  - Alert storm prevention (max 20/run)                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  LaunchAgent (macOS)  │
              │  - Auto-start on boot │
              │  - Restart on crash   │
              │  - Log rotation       │
              └───────────────────────┘
```

---

## 3. Component Interaction Flow

### 3.1. Initialization Flow

```
1. LaunchAgent starts Operator daemon
   ↓
2. Load config.yaml from Operator/config/
   ↓
3. Initialize Data Adapters
   ├─ Oura MCP Adapter → Connect to cache DB
   ├─ WorkOS MCP Adapter → Connect to Postgres
   └─ State Files Adapter → Load JSON files
   ↓
4. Initialize Monitors (Health, Task, Pattern)
   ↓
5. Initialize Alerters (Telegram, macOS, Journal)
   ↓
6. Load daemon state from daemon_state.json
   ↓
7. Enter main check loop
```

### 3.2. Check Cycle Flow

```
[Every 15 minutes - configurable]

1. Check Scheduler triggers
   ↓
2. Run each Monitor in parallel:
   ├─ Health Monitor
   │  ├─ Query Oura readiness from cache DB
   │  ├─ Check thresholds (readiness<60, HRV<baseline)
   │  └─ Generate Alert objects
   │
   ├─ Task Monitor
   │  ├─ Query WorkOS for active tasks
   │  ├─ Check deadlines (today, tomorrow, overdue)
   │  ├─ Check commitment tracking
   │  └─ Generate Alert objects
   │
   └─ Pattern Monitor
      ├─ Query State/patterns.json
      ├─ Check procrastination patterns
      ├─ Check energy trend decline
      └─ Generate Alert objects
   ↓
3. Collect all alerts
   ↓
4. Deduplication
   ├─ Check dedup_key against cache (1-hour window)
   ├─ Filter out duplicates
   └─ Record new alerts in cache
   ↓
5. Alert Storm Prevention
   ├─ Count alerts this cycle
   ├─ If > max_alerts_per_run: prioritize by severity
   └─ Truncate to max
   ↓
6. Quiet Hours Check
   ├─ If quiet hours (10pm-7am)
   └─ Filter to critical only
   ↓
7. Route to Alerters
   ├─ Telegram → High/Critical
   ├─ macOS Notification → Medium/High
   └─ Journal Logger → All
   ↓
8. Update daemon state
   ├─ last_run timestamp
   ├─ run_count increment
   └─ Save to daemon_state.json
```

### 3.3. Error Recovery Flow

```
MCP Adapter Failure
   ↓
1. Circuit Breaker detects failure
   ↓
2. Exponential backoff retry (3 attempts)
   ↓
3. Fallback Strategy
   ├─ Oura: Cache DB → Direct API → Skip health checks
   └─ WorkOS: Cache DB → Direct Postgres → Skip task checks
   ↓
4. Log error to Journal
   ↓
5. Send alert (if critical threshold reached)
   ↓
6. Continue with remaining monitors
```

---

## 4. Configuration Schema

**File:** `Operator/config/operator.yaml`

```yaml
# Operator Daemon Configuration
version: "1.0"

# Check intervals (seconds)
intervals:
  health_check: 900      # 15 minutes
  task_check: 900        # 15 minutes
  pattern_check: 1800    # 30 minutes

# Quiet hours (no non-critical alerts)
quiet_hours:
  enabled: true
  start: 22              # 10 PM
  end: 7                 # 7 AM
  timezone: "America/Chicago"

# Alert deduplication
deduplication:
  window_seconds: 3600   # 1 hour
  max_alerts_per_run: 20

# Monitor Configuration
monitors:
  health:
    enabled: true
    thresholds:
      readiness_critical: 50
      readiness_warning: 65
      hrv_critical_deviation: -25  # % below 30-day average
      hrv_warning_deviation: -15
      sleep_hours_critical: 5.0
      sleep_hours_warning: 6.0
      stress_high: 75
      stress_critical: 85

  tasks:
    enabled: true
    checks:
      - overdue_tasks
      - due_today
      - due_tomorrow
      - commitment_violations
    commitment_check_hours: [9, 14, 18]  # Check at 9am, 2pm, 6pm

  patterns:
    enabled: true
    lookback_days: 7
    thresholds:
      procrastination_count: 3       # Same task punted 3+ times
      energy_decline_percent: 20     # 20% decline in weekly avg
      overcommitment_ratio: 1.5      # Tasks created vs completed

# Data Adapters
adapters:
  oura:
    type: "mcp_cache"
    cache_db_path: "${HOME}/.oura-cache/oura-health.db"
    fallback_api: true
    api_timeout_seconds: 10

  workos:
    type: "mcp_postgres"
    database_url: "${WORKOS_DATABASE_URL}"
    cache_enabled: true
    cache_ttl_seconds: 300

  state_files:
    type: "json"
    base_path: "${THANOS_ROOT}/State"
    files:
      - "patterns.json"
      - "daemon_state.json"
      - "CurrentFocus.md"

# Alerters
alerters:
  telegram:
    enabled: true
    token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"
    min_priority: "medium"           # low, medium, high, critical
    retry_attempts: 3
    timeout_seconds: 10

  macos:
    enabled: true
    min_priority: "high"
    sound: "Glass"                   # macOS system sound

  journal:
    enabled: true
    min_priority: "info"             # Always log everything
    log_path: "${THANOS_ROOT}/logs/operator.log"

# Circuit Breaker
circuit_breaker:
  failure_threshold: 3
  timeout_seconds: 60
  half_open_attempts: 1

# Logging
logging:
  level: "INFO"                      # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  rotation:
    max_bytes: 10485760              # 10 MB
    backup_count: 5
```

---

## 5. Error Handling Strategy

### 5.1. Error Categories

| Category | Examples | Strategy |
|----------|----------|----------|
| **Transient** | Network timeout, MCP busy | Retry with exponential backoff |
| **Configuration** | Missing env vars, invalid YAML | Fail fast, log critical error |
| **Data** | Corrupted cache, invalid JSON | Skip check, log warning, fallback |
| **Service Unavailable** | MCP down, Postgres offline | Circuit breaker, graceful degradation |
| **Alert Delivery** | Telegram API down | Retry, fallback to macOS, always log |

### 5.2. Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Prevent cascading failures when services are down."""

    states = ["closed", "open", "half_open"]

    def __init__(self, failure_threshold=3, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "closed"

    def call(self, func):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = func()
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        self.failure_count = 0
        self.state = "closed"

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
```

### 5.3. Graceful Degradation

**Oura Health Checks:**
```
1. Try Oura MCP cache DB (fast, local)
   ↓ FAIL
2. Try direct Oura API call (slow, requires token)
   ↓ FAIL
3. Skip health checks this cycle, log warning
   ↓
4. Continue with task and pattern checks
```

**WorkOS Task Checks:**
```
1. Try WorkOS MCP cache DB (fast, local)
   ↓ FAIL
2. Try direct Postgres connection (requires network)
   ↓ FAIL
3. Skip task checks this cycle, log warning
   ↓
4. Continue with health and pattern checks
```

### 5.4. Alert Delivery Resilience

```python
async def send_alert(alert: Alert) -> bool:
    """Send alert with fallback chain."""

    # Try Telegram (primary for high/critical)
    if alert.priority in ['high', 'critical']:
        try:
            await telegram_alerter.send(alert)
            return True
        except Exception as e:
            logger.error(f"Telegram failed: {e}")

    # Fallback to macOS notification
    try:
        await macos_alerter.send(alert)
        return True
    except Exception as e:
        logger.error(f"macOS notification failed: {e}")

    # Always log to Journal (cannot fail)
    journal_logger.log(alert)
    return False  # Alert sent to journal only
```

---

## 6. Monitoring Intervals and Thresholds

### 6.1. Check Intervals

| Monitor | Default Interval | Configurable Range | Rationale |
|---------|-----------------|-------------------|-----------|
| Health | 15 minutes | 5-60 min | Oura data updates hourly, 15 min catches changes |
| Tasks | 15 minutes | 5-60 min | Real-time enough for deadline alerts |
| Patterns | 30 minutes | 15-120 min | Longer lookback, less urgent |

### 6.2. Health Thresholds

| Metric | Warning | Critical | Source |
|--------|---------|----------|--------|
| Readiness Score | < 65 | < 50 | Oura MCP |
| HRV Deviation | -15% | -25% | Oura MCP (vs 30-day avg) |
| Sleep Hours | < 6.0h | < 5.0h | Oura MCP |
| Stress Level | > 75 | > 85 | Oura MCP |
| Recovery Index | < 60 | < 40 | Oura MCP |

**Alert Examples:**
- **Warning:** "Your readiness is 62 (Low). Consider lighter tasks today."
- **Critical:** "Your readiness is 48 (Very Low). You're at risk of burnout. Rest today."

### 6.3. Task Thresholds

| Check Type | Condition | Priority | Frequency |
|------------|-----------|----------|-----------|
| Overdue | Any active task past deadline | High | Every check |
| Due Today | Active task due today | Medium | Morning (9am) + afternoon (2pm) |
| Due Tomorrow | Active task due tomorrow | Low | Evening (6pm) |
| Commitment Violation | Commitment past due by 2+ days | Critical | Every check |
| Task Pile-Up | 10+ active tasks | Medium | Daily (9am) |

**Alert Examples:**
- **High:** "3 tasks overdue: [Memphis report, Raleigh follow-up, Orlando documentation]"
- **Medium:** "Due today: [Kentucky ScottCare integration call notes]"
- **Critical:** "Commitment violated: You promised Ashley to schedule date night 3 days ago."

### 6.4. Pattern Thresholds

| Pattern Type | Lookback | Threshold | Priority |
|--------------|----------|-----------|----------|
| Procrastination | 7 days | Same task punted 3+ times | Medium |
| Energy Decline | 7 days | 20% drop in weekly avg readiness | High |
| Overcommitment | 7 days | Created/Completed ratio > 1.5 | Medium |
| Sleep Debt | 3 days | 3+ consecutive days < 7h | High |
| Context Switching | 1 day | 5+ different clients in one day | Low |

**Alert Examples:**
- **Medium:** "You've rescheduled 'Memphis optimization report' 4 times this week. Block time now?"
- **High:** "Your average readiness dropped from 78 to 62 this week. Overcommitted?"
- **Medium:** "You created 12 tasks and completed 5 this week. Ratio: 2.4 (healthy: <1.5)"

### 6.5. Deduplication Windows

| Alert Type | Dedup Window | Rationale |
|------------|--------------|-----------|
| Health warnings | 4 hours | Don't nag about same metric repeatedly |
| Task deadlines | 24 hours | One reminder per day is enough |
| Pattern alerts | 7 days | Weekly pattern checks |
| Critical health | 1 hour | More urgent, but still prevent spam |

---

## 7. LaunchAgent Integration

**File:** `~/Library/LaunchAgents/com.thanos.operator.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Service Identity -->
    <key>Label</key>
    <string>com.thanos.operator</string>

    <!-- Program to Run -->
    <key>ProgramArguments</key>
    <array>
        <string>/Users/jeremy/Projects/Thanos/.venv/bin/python3</string>
        <string>/Users/jeremy/Projects/Thanos/Operator/daemon.py</string>
        <string>--config</string>
        <string>/Users/jeremy/Projects/Thanos/Operator/config/operator.yaml</string>
    </array>

    <!-- Environment Variables -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>THANOS_ROOT</key>
        <string>/Users/jeremy/Projects/Thanos</string>
        <key>HOME</key>
        <string>/Users/jeremy</string>
        <!-- Secrets loaded from .env file by daemon -->
    </dict>

    <!-- Working Directory -->
    <key>WorkingDirectory</key>
    <string>/Users/jeremy/Projects/Thanos/Operator</string>

    <!-- Auto-Start Configuration -->
    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>  <!-- Restart on crash -->
        <key>Crashed</key>
        <true/>
    </dict>

    <!-- Logging -->
    <key>StandardOutPath</key>
    <string>/Users/jeremy/Projects/Thanos/logs/operator_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/jeremy/Projects/Thanos/logs/operator_stderr.log</string>

    <!-- Resource Limits -->
    <key>ProcessType</key>
    <string>Background</string>

    <key>Nice</key>
    <integer>5</integer>  <!-- Lower priority than user processes -->

    <!-- Throttle -->
    <key>ThrottleInterval</key>
    <integer>60</integer>  <!-- Wait 60s before restart after crash -->
</dict>
</plist>
```

**Installation Commands:**

```bash
# Copy plist to LaunchAgents directory
cp Operator/launchd/com.thanos.operator.plist ~/Library/LaunchAgents/

# Load the agent
launchctl load ~/Library/LaunchAgents/com.thanos.operator.plist

# Start the agent
launchctl start com.thanos.operator

# Check status
launchctl list | grep thanos.operator

# View logs
tail -f ~/Projects/Thanos/logs/operator_stdout.log

# Unload (for updates)
launchctl unload ~/Library/LaunchAgents/com.thanos.operator.plist
```

---

## 8. Graceful Shutdown Handling

### 8.1. Signal Handling

```python
import signal
import sys
import asyncio

class OperatorDaemon:
    def __init__(self):
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()

    async def run(self):
        """Main daemon loop with graceful shutdown."""
        self.running = True

        try:
            while self.running and not self.shutdown_event.is_set():
                # Run check cycle
                await self.check_cycle()

                # Wait for next interval or shutdown signal
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=self.config.check_interval
                    )
                except asyncio.TimeoutError:
                    # Normal - timeout means time for next check
                    pass

        finally:
            await self.cleanup()

    async def cleanup(self):
        """Graceful cleanup on shutdown."""
        logger.info("Starting cleanup...")

        # Save daemon state
        self.state_manager.save()

        # Close database connections
        await self.oura_adapter.close()
        await self.workos_adapter.close()

        # Flush logs
        for handler in logger.handlers:
            handler.flush()

        logger.info("Shutdown complete.")
        sys.exit(0)
```

### 8.2. Shutdown Sequence

```
1. Receive SIGTERM or SIGINT
   ↓
2. Set shutdown_event
   ↓
3. Wait for current check cycle to complete
   ↓
4. Save daemon state to daemon_state.json
   ↓
5. Close Oura MCP adapter connection
   ↓
6. Close WorkOS MCP adapter connection
   ↓
7. Close all file handles
   ↓
8. Flush all log handlers
   ↓
9. Exit with code 0 (clean shutdown)
```

---

## 9. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
- [ ] Config YAML schema and loader
- [ ] Daemon state manager (daemon_state.json)
- [ ] LaunchAgent plist creation
- [ ] Basic logging and journal integration
- [ ] Signal handling for graceful shutdown

### Phase 2: Data Adapters (Week 2)
- [ ] Oura MCP Adapter (cache DB + API fallback)
- [ ] WorkOS MCP Adapter (cache DB + Postgres fallback)
- [ ] State Files Adapter (patterns.json, CurrentFocus.md)
- [ ] Circuit breaker implementation

### Phase 3: Monitors (Week 3)
- [ ] Health Monitor (readiness, sleep, HRV, stress)
- [ ] Task Monitor (deadlines, commitments)
- [ ] Pattern Monitor (procrastination, energy trends)
- [ ] Alert deduplication logic

### Phase 4: Alerters (Week 4)
- [ ] Telegram Alerter (with retry and formatting)
- [ ] macOS Notification Alerter (osascript)
- [ ] Journal Logger (always-on)
- [ ] Alert storm prevention

### Phase 5: Integration & Testing (Week 5)
- [ ] End-to-end integration tests
- [ ] LaunchAgent installation and testing
- [ ] Error injection and recovery testing
- [ ] Performance and resource usage optimization
- [ ] Documentation and user guide

---

## 10. Architecture Decision Records (ADR)

### ADR-001: SQLite Cache vs Direct MCP Calls

**Decision:** Use local SQLite cache databases as primary data source, with MCP calls as fallback.

**Rationale:**
- **Performance:** Cache reads are 10-100x faster than MCP calls
- **Reliability:** Daemon continues working even if MCP servers are down
- **Resource Efficiency:** Reduces network I/O and MCP server load
- **Staleness Acceptable:** 5-15 minute staleness is fine for monitoring

**Trade-offs:**
- Data may be slightly stale (mitigated by 5-minute cache TTL)
- Additional storage required (negligible - <10 MB)

### ADR-002: Quiet Hours Implementation

**Decision:** Suppress non-critical alerts during quiet hours (10pm-7am), but still log to journal.

**Rationale:**
- **Sleep Protection:** Prevents midnight alerts from disrupting sleep
- **Critical Override:** Critical alerts (readiness <40, commitment violations) still trigger
- **Audit Trail:** All alerts logged regardless of quiet hours

**Trade-offs:**
- May miss medium-priority issues overnight (acceptable - reviewed in morning)

### ADR-003: Alert Deduplication Strategy

**Decision:** Use dedup_key (alert_type:entity_id) with 1-hour sliding window.

**Rationale:**
- **Prevents Spam:** Same alert won't trigger repeatedly
- **Appropriate Window:** 1 hour balances responsiveness with noise reduction
- **Entity Granularity:** Different tasks/metrics tracked separately

**Trade-offs:**
- May miss rapid state changes within 1 hour (rare, acceptable)

### ADR-004: YAML Configuration vs Code

**Decision:** Use YAML for all thresholds and intervals, not hardcoded in Python.

**Rationale:**
- **User Customization:** Jeremy can tune without editing code
- **Environment-Specific:** Different configs for dev/production
- **Version Control:** Config changes tracked separately from code

**Trade-offs:**
- Slight complexity in config validation (mitigated by schema validation)

### ADR-005: Python vs TypeScript

**Decision:** Implement daemon in Python 3, not TypeScript.

**Rationale:**
- **Existing Ecosystem:** Alert checkers, journal, state store already in Python
- **System Integration:** Easier access to macOS osascript, signals
- **Async Support:** asyncio mature and well-supported

**Trade-offs:**
- Not consistent with MCP servers (TypeScript), but appropriate for system daemon

---

## 11. Security Considerations

### 11.1. Credential Management

- **Environment Variables:** Secrets loaded from `.env` file, never hardcoded
- **File Permissions:** `daemon_state.json` and logs set to `0600` (owner read/write only)
- **API Tokens:** Telegram token and database URLs stored securely
- **No Logging of Secrets:** Ensure logs never contain API tokens or credentials

### 11.2. Input Validation

- **YAML Schema Validation:** All config files validated against schema before use
- **Database Queries:** Parameterized queries to prevent SQL injection
- **File Paths:** Sanitize all file paths to prevent directory traversal

### 11.3. Resource Limits

- **Memory:** Monitor daemon memory usage, restart if exceeds threshold
- **Disk:** Log rotation to prevent disk fill-up
- **CPU:** Nice value of 5 to prevent hogging system resources

---

## 12. Monitoring and Observability

### 12.1. Health Check Endpoint (Optional)

```python
# Simple HTTP server for health checks (optional)
from aiohttp import web

async def health_check(request):
    """Health check endpoint for monitoring."""
    status = {
        "status": "healthy" if daemon.running else "stopped",
        "last_run": daemon.state.last_run,
        "run_count": daemon.state.run_count,
        "monitors": {
            "health": daemon.health_monitor.enabled,
            "tasks": daemon.task_monitor.enabled,
            "patterns": daemon.pattern_monitor.enabled,
        },
        "adapters": {
            "oura": daemon.oura_adapter.is_connected(),
            "workos": daemon.workos_adapter.is_connected(),
        }
    }
    return web.json_response(status)

# Start health check server on localhost:8765
app = web.Application()
app.router.add_get('/health', health_check)
web.run_app(app, host='127.0.0.1', port=8765)
```

### 12.2. Metrics Collection

```python
@dataclass
class DaemonMetrics:
    """Metrics for monitoring daemon performance."""
    total_checks: int = 0
    total_alerts: int = 0
    alerts_by_priority: Dict[str, int] = field(default_factory=dict)
    average_check_duration: float = 0.0
    failed_checks: int = 0
    circuit_breaker_trips: int = 0
    last_error: Optional[str] = None
```

### 12.3. Log Levels

```
DEBUG: Detailed diagnostics (config loading, adapter initialization)
INFO: Normal operations (check cycles, alert sent)
WARNING: Non-critical issues (cache stale, fallback used)
ERROR: Recoverable failures (MCP timeout, alert delivery failed)
CRITICAL: Fatal errors (config invalid, shutdown required)
```

---

## 13. Future Enhancements

### 13.1. Machine Learning Patterns

- **Personalized Thresholds:** Learn optimal readiness thresholds based on historical performance
- **Predictive Alerts:** "Based on your patterns, you're likely to miss this deadline"
- **Smart Scheduling:** "Your readiness is usually higher on Tuesday mornings - schedule important work then"

### 13.2. Advanced Pattern Detection

- **Burnout Risk Score:** Combine readiness decline + overcommitment + sleep debt
- **Client Balance:** Alert if one client consuming >50% of weekly hours
- **Energy-Task Matching:** "You're doing high-cognitive work on low-energy days"

### 13.3. Integration Enhancements

- **Calendar Integration:** Cross-reference tasks with Google Calendar availability
- **Commitment Tracking:** Integrate with commitment_tracker.py for unified view
- **Brain Dump Pipeline:** Auto-process brain dumps into tasks if patterns detected

---

## 14. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Uptime** | 99.9% (8.7h downtime/year) | LaunchAgent logs |
| **Alert Accuracy** | <5% false positives | User feedback + journal audit |
| **Response Time** | <1 second per check cycle | Performance logs |
| **Resource Usage** | <50 MB memory, <5% CPU | macOS Activity Monitor |
| **User Satisfaction** | Actionable alerts 90%+ of time | Qualitative feedback |

---

## 15. Conclusion

The Operator daemon provides a robust, autonomous monitoring system that integrates seamlessly with Thanos v2.0's existing architecture. Its modular design allows for easy extension while maintaining reliability through circuit breakers, graceful degradation, and comprehensive error handling.

**Key Differentiators:**
- **Proactive, not reactive:** Alerts before problems become critical
- **Context-aware:** Integrates health, tasks, and patterns for holistic view
- **Resilient:** Continues operating even when services are degraded
- **Configurable:** YAML-driven for easy customization
- **Observable:** Comprehensive logging and optional health check endpoint

**Next Steps:**
1. Review this architecture design with Jeremy
2. Prioritize Phase 1 implementation (core infrastructure)
3. Create detailed implementation tasks in `/task` or TodoWrite
4. Begin development following the 5-week roadmap
