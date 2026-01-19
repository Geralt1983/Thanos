# Thanos Personal Productivity System - Architecture

## System Overview

Thanos is a personal productivity system built on **four architectural pillars** that work together to create a trusted, resilient system for capturing thoughts, managing tasks, and maintaining clarity.

```
                           +---------------------------+
                           |      User Interfaces      |
                           |  CLI | Telegram | Voice   |
                           +-------------+-------------+
                                         |
         +-------------------------------+--------------------------------+
         |                               |                                |
         v                               v                                v
+------------------+          +-------------------+           +-------------------+
|     CAPTURE      |          |      CLARITY      |           |    RESILIENCE     |
|                  |          |                   |           |                   |
| Brain Dump       |          | Alert Checker     |           | Circuit Breaker   |
| - Classifier     |          | - Commitments     |           | - State Tracking  |
| - Router         |          | - Tasks           |           | - Auto-Fallback   |
|                  |          | - Health (Oura)   |           | - File Cache      |
| (9 Types)        |          | - Habits          |           |                   |
+--------+---------+          +---------+---------+           +----------+--------+
         |                              |                                |
         +------------------------------+--------------------------------+
                                        |
                                        v
                           +---------------------------+
                           |         TRUST             |
                           |                           |
                           |  Unified State Store      |
                           |  (SQLite - 8 Tables)      |
                           |                           |
                           |  Event Journal            |
                           |  (47 Event Types)         |
                           +---------------------------+
                                        |
                                        v
                           +---------------------------+
                           |    External Services      |
                           | Oura | WorkOS | Calendar  |
                           +---------------------------+
```

## The Four Pillars

### 1. TRUST - Single Source of Truth

The foundation of Thanos is a **unified SQLite state store** that consolidates all data into a single, reliable database. This eliminates the complexity of managing multiple data sources and provides consistent, trustworthy data.

**Core Components:**
- `Tools/unified_state.py` - StateStore class (8 core tables)
- `Tools/journal.py` - Event Journal (47 event types, 5 severity levels)

**Design Principles:**
- Single database file for all state
- WAL mode for concurrent access
- Foreign key enforcement
- Automatic timestamps on all mutations

### 2. CAPTURE - Intelligent Input Processing

The brain dump system provides **zero-friction capture** of any thought, with AI-powered classification that distinguishes thinking from actionable items. This prevents task pollution while ensuring nothing important is lost.

**Core Components:**
- `Tools/brain_dump/classifier.py` - AI-powered classification (9 types)
- `Tools/brain_dump/router.py` - Intelligent routing to destinations

**Design Principles:**
- Default to NOT creating tasks
- All input archived regardless of classification
- Empathetic acknowledgments for venting/thinking
- Clear routing rules per classification

### 3. CLARITY - Proactive Alerting

The alert system provides **proactive visibility** into commitments, tasks, health metrics, and habits. It surfaces what needs attention before it becomes urgent.

**Core Components:**
- `Tools/alert_checker.py` - AlertManager with 4 specialized checkers
- Integration with Journal for alert logging

**Design Principles:**
- Priority-based sorting (critical first)
- Acknowledgment tracking
- Domain-specific thresholds (health, commitments, habits)
- Non-blocking async checks

### 4. RESILIENCE - Graceful Degradation

The circuit breaker pattern provides **resilience for fragile APIs** (like unofficial Oura/Monarch integrations). When external services fail, the system automatically falls back to cached data.

**Core Components:**
- `Tools/circuit_breaker.py` - CircuitBreaker, FileCache, ResilientAdapter

**Design Principles:**
- Three states: CLOSED (normal), OPEN (failing), HALF_OPEN (testing)
- Automatic recovery attempts after timeout
- File-based cache with TTL
- Transparent fallback (caller gets metadata about staleness)

---

## Database Schema

### StateStore Tables (8 Tables)

```
+-------------------+     +--------------------+     +-------------------+
|      tasks        |     |  calendar_events   |     |   commitments     |
+-------------------+     +--------------------+     +-------------------+
| id (PK)           |     | id (PK)            |     | id (PK)           |
| title             |     | title              |     | title             |
| description       |     | start_time         |     | description       |
| status            |     | end_time           |     | stakeholder       |
| priority          |     | location           |     | deadline          |
| due_date          |     | source             |     | status            |
| source            |     | source_id          |     | priority          |
| source_id         |     | created_at         |     | created_at        |
| created_at        |     | metadata (JSON)    |     | completed_at      |
| updated_at        |     +--------------------+     | metadata (JSON)   |
| completed_at      |                               +-------------------+
| metadata (JSON)   |
+-------------------+

+-------------------+     +--------------------+     +-------------------+
|   focus_areas     |     |  health_metrics    |     |     finances      |
+-------------------+     +--------------------+     +-------------------+
| id (PK)           |     | id (PK, AUTO)      |     | id (PK, AUTO)     |
| title             |     | date               |     | date              |
| description       |     | metric_type        |     | account_id        |
| is_active         |     | value              |     | account_name      |
| started_at        |     | source             |     | balance           |
| ended_at          |     | recorded_at        |     | available         |
| metadata (JSON)   |     | metadata (JSON)    |     | source            |
+-------------------+     | UNIQUE(date,type,  |     | recorded_at       |
                          |        source)     |     | metadata (JSON)   |
                          +--------------------+     +-------------------+

+------------------------+     +-------------------+
| finance_transactions   |     |  schema_version   |
+------------------------+     +-------------------+
| id (PK)                |     | version (PK)      |
| date                   |     | applied_at        |
| amount                 |     +-------------------+
| merchant               |
| category               |
| account_id             |
| is_recurring           |
| source                 |
| metadata (JSON)        |
+------------------------+
```

### Indexes (Performance Optimization)

```sql
-- Tasks
idx_tasks_status      ON tasks(status)
idx_tasks_due_date    ON tasks(due_date)
idx_tasks_source      ON tasks(source)

-- Calendar
idx_calendar_start    ON calendar_events(start_time)

-- Commitments
idx_commitments_deadline ON commitments(deadline)
idx_commitments_status   ON commitments(status)

-- Health
idx_health_date       ON health_metrics(date)
idx_health_type       ON health_metrics(metric_type)

-- Finances
idx_finances_date     ON finances(date)
idx_transactions_date ON finance_transactions(date)
```

### Journal Table

```
+-------------------------+
|        journal          |
+-------------------------+
| id (PK, AUTO)           |
| timestamp               |
| event_type              |
| source                  |
| severity                |
| title                   |
| data (JSON)             |
| session_id              |
| agent                   |
| acknowledged            |
| acknowledged_at         |
+-------------------------+

Indexes:
- idx_journal_timestamp
- idx_journal_event_type
- idx_journal_severity
- idx_journal_source
- idx_journal_acknowledged
```

---

## Event Types (47 Types)

### Task Events (5)
| Event | Description |
|-------|-------------|
| `task_created` | New task added to system |
| `task_updated` | Task modified |
| `task_completed` | Task marked complete |
| `task_cancelled` | Task cancelled |
| `task_overdue` | Task past due date |

### Calendar Events (4)
| Event | Description |
|-------|-------------|
| `event_created` | Calendar event added |
| `event_upcoming` | Event starting soon |
| `event_started` | Event has begun |
| `event_missed` | Event passed without attendance |

### Health Events (3)
| Event | Description |
|-------|-------------|
| `health_metric_logged` | Health data recorded |
| `health_alert` | Health threshold exceeded |
| `health_summary` | Daily health summary |

### Finance Events (6)
| Event | Description |
|-------|-------------|
| `balance_logged` | Account balance recorded |
| `balance_warning` | Balance below threshold |
| `balance_critical` | Balance critically low |
| `large_transaction` | Unusually large transaction |
| `projection_warning` | Projected shortfall |
| `recurring_upcoming` | Recurring charge approaching |

### Brain Dump Events (8)
| Event | Description |
|-------|-------------|
| `brain_dump_received` | Raw input received |
| `brain_dump_parsed` | Classification complete |
| `brain_dump_thinking` | Classified as thinking |
| `brain_dump_venting` | Classified as venting |
| `brain_dump_observation` | Classified as observation |
| `note_captured` | Note saved |
| `idea_captured` | Idea recorded |
| `idea_promoted` | Idea promoted to task |

### System Events (9)
| Event | Description |
|-------|-------------|
| `sync_started` | Data sync initiated |
| `sync_completed` | Sync successful |
| `sync_failed` | Sync failed |
| `circuit_opened` | Circuit breaker tripped |
| `circuit_closed` | Circuit recovered |
| `circuit_half_open` | Testing recovery |
| `daemon_started` | Background service started |
| `daemon_stopped` | Background service stopped |
| `error_occurred` | System error |

### Commitment Events (4)
| Event | Description |
|-------|-------------|
| `commitment_created` | Promise recorded |
| `commitment_completed` | Commitment fulfilled |
| `commitment_due_soon` | Deadline approaching |
| `commitment_overdue` | Deadline passed |

### Session Events (3)
| Event | Description |
|-------|-------------|
| `session_started` | User session began |
| `session_ended` | Session concluded |
| `command_executed` | Command processed |

### Alert Events (5)
| Event | Description |
|-------|-------------|
| `alert_created` | Alert generated |
| `alert_acknowledged` | User acknowledged |
| `alert_resolved` | Alert cleared |
| `alert_raised` | Alert surfaced |
| `alert_check_complete` | Check cycle done |

### Severity Levels (5)
```python
DEBUG    = "debug"     # Diagnostic info
INFO     = "info"      # Normal operations
WARNING  = "warning"   # Attention needed
ALERT    = "alert"     # Action required
CRITICAL = "critical"  # Immediate action
```

---

## Brain Dump Classification System

### Classification Types (9)

```
+------------------+     +------------------+     +------------------+
|    REFLECTIVE    |     |     CAPTURE      |     |    ACTIONABLE    |
|  (Journal Only)  |     |  (State Store)   |     |  (Tasks/Commits) |
+------------------+     +------------------+     +------------------+
| thinking         |     | note             |     | personal_task    |
| venting          |     | idea             |     | work_task        |
| observation      |     |                  |     | commitment       |
+------------------+     +------------------+     +------------------+
                               |
                               v
                         +----------+
                         |  mixed   |
                         | (multi)  |
                         +----------+
```

### Classification Rules

**1. THINKING** (Default)
- Internal reflection, musing, pondering
- Phrases: "I've been thinking about...", "I wonder if...", "Maybe I need to..."
- Action: Journal only, empathetic acknowledgment

**2. VENTING**
- Emotional release, frustration, stress
- Indicators: Exclamation points, emotional language, complaints
- Action: Journal only, validating acknowledgment

**3. OBSERVATION**
- Noting something without action needed
- Phrases: "I noticed that...", "It seems like..."
- Action: Journal only

**4. NOTE**
- Information to remember, not act on
- Phrases: "Remember that...", facts, references
- Action: Store in state, log to journal

**5. PERSONAL_TASK**
- Clear, specific personal action
- Requirements: Specific verb + clear object + feasibility
- Examples: "Call dentist", "Buy groceries", "Pay electric bill"
- Action: Create task (personal domain), log to journal

**6. WORK_TASK**
- Clear, specific work action
- Indicators: Client/project mentions, code/PR references
- Examples: "Review the PR", "Send report to client"
- Action: Create task (work domain), sync to WorkOS, log to journal

**7. IDEA**
- Creative thought worth capturing
- Phrases: "What if we built...", "A cool feature would be..."
- Action: Store idea, log to journal

**8. COMMITMENT**
- Promise made to someone
- Requirements: Another person + promise
- Phrases: "I told X I would...", "I promised to..."
- Action: Create commitment with stakeholder, log to journal

**9. MIXED**
- Contains multiple distinct items
- Action: Process each segment independently, merge results

### Classifier Response Format

```json
{
  "classification": "work_task",
  "confidence": 0.95,
  "reasoning": "Clear action (review PR) + specific target (auth changes)",
  "acknowledgment": "Work task created.",
  "task": {
    "title": "Review Sarah's auth PR",
    "description": "Review Sarah's PR for the auth changes",
    "context": "work",
    "priority": "medium",
    "estimated_effort": "medium"
  }
}
```

### Routing Flow

```
Raw Input
    |
    v
+-------------------+
| BrainDumpClassifier |
| (Claude API)       |
+-------------------+
    |
    v
ClassifiedBrainDump
    |
    v
+-------------------+
| BrainDumpRouter    |
+-------------------+
    |
    +---> Archive (always)
    |
    +---> Classification Check
          |
          +---> thinking/venting/observation --> Journal only
          |
          +---> note --> State Store + Journal
          |
          +---> idea --> State Store + Journal
          |
          +---> personal_task --> Task (personal) + Journal
          |
          +---> work_task --> Task (work) + WorkOS + Journal
          |
          +---> commitment --> Commitment + Journal
          |
          +---> mixed --> Route each segment recursively
```

---

## Circuit Breaker Pattern

### State Diagram

```
                     failure_threshold
                        reached
    +--------+       +----------+       +--------+
    | CLOSED | ----> |   OPEN   | ----> | HALF_  |
    | (Normal)|      | (Failing)|       | OPEN   |
    +--------+       +----------+       +--------+
        ^                |                  |
        |                | recovery_        |
        |                | timeout          |
        +----------------+                  |
              success in                    |
              half_open                     |
                                           |
        +----------------------------------+
                    failure in
                    half_open
```

### Configuration Options

```python
CircuitBreaker(
    name="oura",                    # Identifier for logging
    failure_threshold=3,           # Failures before opening
    recovery_timeout=3600,         # Seconds before testing recovery
    half_open_max_calls=1,         # Successes needed to close
    success_threshold=2,           # Consecutive successes to reset
    log_events=True                # Log state changes to journal
)
```

### Metadata Returned

```python
@dataclass
class CircuitMetadata:
    circuit_state: CircuitState    # CLOSED, OPEN, or HALF_OPEN
    is_fallback: bool              # True if using cached data
    failure_count: int             # Current failure count
    last_error: Optional[str]      # Most recent error
    cache_age: Optional[float]     # Seconds since cache created
```

### ResilientAdapter Pattern

```python
class OuraAdapter(ResilientAdapter):
    def __init__(self):
        super().__init__(
            name="oura",
            cache_dir=Path("State/cache/oura"),
            failure_threshold=3,
            recovery_timeout=3600,
            cache_ttl=86400  # 24 hours
        )

    async def get_sleep_data(self, date: str):
        return await self.fetch_with_fallback(
            cache_key=f"sleep_{date}",
            fetch_func=lambda: self._api_call(f"/sleep/{date}"),
            cache_ttl=3600
        )
```

---

## Alert System

### Alert Types (17)

#### Commitment Alerts
| Type | Priority | Trigger |
|------|----------|---------|
| `COMMITMENT_OVERDUE` | HIGH/CRITICAL | Past deadline |
| `COMMITMENT_DUE_SOON` | MEDIUM | Within 48 hours |

#### Task Alerts
| Type | Priority | Trigger |
|------|----------|---------|
| `TASK_OVERDUE` | MEDIUM/HIGH | Past due date |
| `TASK_DUE_TODAY` | MEDIUM | Due today |
| `TASK_BLOCKED` | MEDIUM | Blocked status |

#### Health Alerts (Oura)
| Type | Priority | Threshold |
|------|----------|-----------|
| `HEALTH_LOW_SLEEP` | MEDIUM | Score < 70 |
| `HEALTH_LOW_READINESS` | MEDIUM | Score < 65 |
| `HEALTH_HIGH_STRESS` | HIGH | Score > 80 |
| `HEALTH_LOW_HRV` | HIGH | HRV < 30ms |

#### Habit Alerts
| Type | Priority | Trigger |
|------|----------|---------|
| `HABIT_STREAK_AT_RISK` | MEDIUM/HIGH | Not done today, streak >= 3 |
| `HABIT_MISSED` | LOW | Missed 2+ days |

#### Focus Alerts
| Type | Priority | Trigger |
|------|----------|---------|
| `FOCUS_STALLED` | MEDIUM | No progress on active focus |
| `FOCUS_NO_PROGRESS` | LOW | Focus area dormant |

#### System Alerts
| Type | Priority | Trigger |
|------|----------|---------|
| `SYSTEM_SYNC_FAILED` | WARNING | Sync error |
| `SYSTEM_ERROR` | HIGH | System failure |

### Alert Priority Levels

```python
class AlertPriority(Enum):
    LOW = "low"         # Informational
    MEDIUM = "medium"   # Attention needed
    HIGH = "high"       # Action required soon
    CRITICAL = "critical"  # Immediate action
```

### AlertManager Architecture

```
AlertManager
    |
    +---> CommitmentAlertChecker
    |         |
    |         +---> state.get_active_commitments()
    |         +---> Check deadlines
    |
    +---> TaskAlertChecker
    |         |
    |         +---> state.execute_sql(tasks query)
    |         +---> Check due dates
    |
    +---> OuraAlertChecker
    |         |
    |         +---> state.get_health_metrics()
    |         +---> Compare against thresholds
    |
    +---> HabitAlertChecker
              |
              +---> Query habits + completions
              +---> Check streaks
```

---

## API Examples

### StateStore Usage

```python
from Tools.unified_state import get_state_store

store = get_state_store()

# Task operations
task_id = store.add_task(
    title="Review Q4 financials",
    priority="p1",
    due_date=date.today() + timedelta(days=7)
)

tasks = store.get_tasks_due_today()
overdue = store.get_overdue_tasks()
store.complete_task(task_id)

# Commitment operations
commit_id = store.add_commitment(
    title="Deliver project proposal",
    stakeholder="Mike",
    deadline=date(2026, 1, 25)
)

commitments = store.get_commitments_due_soon(days=7)
store.complete_commitment(commit_id)

# Health metrics
store.log_health_metric(
    metric_type="sleep_score",
    value=78,
    source="oura"
)

health = store.get_today_health()
# Returns: {"sleep_score": 78, "readiness": 82, ...}

# Export
snapshot = store.export_snapshot()
store.save_daily_snapshot()
```

### Journal Usage

```python
from Tools.journal import get_journal, EventType

journal = get_journal()

# Log events
journal.log(
    event_type=EventType.TASK_COMPLETED,
    source="workos",
    title="Completed: Review Q4 financials",
    data={"task_id": "abc123", "duration_hours": 2.5}
)

# Query events
events = journal.get_today()
alerts = journal.get_alerts(unacknowledged_only=True)
stats = journal.get_stats(since=datetime.now() - timedelta(hours=24))

# Acknowledge alerts
journal.acknowledge_alert(entry_id=42)
count = journal.acknowledge_all_alerts()
```

### Brain Dump Usage

```python
from Tools.brain_dump.classifier import classify_brain_dump_sync
from Tools.brain_dump.router import route_brain_dump

# Classify
result = classify_brain_dump_sync(
    "I told Sarah I'd review her PR by Friday",
    source="telegram"
)

print(result.classification)  # "commitment"
print(result.commitment)      # {"to_whom": "Sarah", "deadline": "Friday"}

# Route (with dependencies)
from Tools.unified_state import get_state_store
from Tools.journal import get_journal

routing_result = await route_brain_dump(
    dump=result,
    state=get_state_store(),
    journal=get_journal()
)

print(routing_result.commitment_created)  # UUID
print(routing_result.summary())           # "commitment created, logged to journal"
```

### Circuit Breaker Usage

```python
from Tools.circuit_breaker import CircuitBreaker, ResilientAdapter

# Direct usage
circuit = CircuitBreaker(name="external_api", failure_threshold=3)

result, metadata = await circuit.call(
    func=fetch_from_api,
    fallback=get_cached_data
)

if metadata.is_fallback:
    print(f"Using cached data from {metadata.cache_age}s ago")

# Decorator usage
@circuit_protected("monarch", fallback=get_cached_accounts)
async def fetch_accounts():
    return await api.get_accounts()

# ResilientAdapter pattern
adapter = ResilientAdapter(name="oura", cache_ttl=86400)
data, meta = await adapter.fetch_with_fallback(
    cache_key="sleep_2026-01-18",
    fetch_func=fetch_sleep_data
)
```

### Alert Checker Usage

```python
from Tools.alert_checker import AlertManager, run_alert_check

# Full check
alerts = await run_alert_check()
for alert in alerts:
    print(f"{alert.priority.value}: {alert.title}")

# Custom manager
manager = AlertManager()
alerts = await manager.check_all()
active = manager.get_active_alerts(limit=10)
manager.acknowledge_alert("alert_id_123")
```

---

## Data Flow Diagrams

### Brain Dump Flow

```
User Input (Telegram/CLI/Voice)
         |
         v
+-------------------+
| Brain Dump Entry  |
| (raw text)        |
+-------------------+
         |
         v
+-------------------+
| BrainDumpClassifier|
| (Claude API)      |
+-------------------+
         |
    Classification
         |
    +----+----+----+----+----+----+----+
    |    |    |    |    |    |    |    |
    v    v    v    v    v    v    v    v
  think vent obs note idea p_task w_task commit
    |    |    |    |    |    |    |    |
    +----+----+    +----+    +----+----+
         |              |         |
         v              v         v
    +--------+    +--------+  +--------+
    | Journal|    | State  |  | WorkOS |
    | (log)  |    | (store)|  | (sync) |
    +--------+    +--------+  +--------+
         |              |         |
         +------+-------+---------+
                |
                v
        +---------------+
        | RoutingResult |
        | (summary)     |
        +---------------+
```

### Alert Check Flow

```
Scheduled Trigger / Manual
         |
         v
+-------------------+
|   AlertManager    |
+-------------------+
         |
    +----+----+----+----+
    |    |    |    |    |
    v    v    v    v    v
+------+ +------+ +------+ +------+
|Commit| |Task  | |Oura  | |Habit |
|Check | |Check | |Check | |Check |
+------+ +------+ +------+ +------+
    |        |        |        |
    +--------+--------+--------+
             |
             v
    +-------------------+
    | Aggregate Alerts  |
    | Sort by Priority  |
    +-------------------+
             |
             v
    +-------------------+
    |   Journal Log     |
    | (alert_raised)    |
    +-------------------+
             |
             v
    +-------------------+
    |  Return Alerts    |
    +-------------------+
```

### Circuit Breaker Flow

```
API Call Request
         |
         v
+-------------------+
|  CircuitBreaker   |
+-------------------+
         |
    Check State
         |
    +----+----+
    |         |
    v         v
 CLOSED     OPEN
    |         |
    v         |
  Try API     |
    |         |
+---+---+     |
|       |     |
v       v     v
Success Fail  Check Recovery Timeout
  |       |         |
  v       v         v
Reset   Count   +---+---+
Failures Fail   |       |
  |       |    No      Yes
  |       |     |       |
  |       v     v       v
  |   Threshold? Return HALF_OPEN
  |       |     Cached    |
  |       v       |       v
  |   Open       |    Test API
  |   Circuit    |       |
  |       |      |   +---+---+
  |       v      |   |       |
  |   Use Fallback   v       v
  |       |      Success   Fail
  +-------+        |         |
          |        v         v
          |     CLOSED    OPEN
          |        |         |
          +--------+---------+
                   |
                   v
            Return Result
            + Metadata
```

---

## File Structure

```
Thanos/
+-- Tools/
|   +-- unified_state.py      # StateStore (Trust pillar)
|   +-- journal.py            # Event Journal (Trust pillar)
|   +-- circuit_breaker.py    # Resilience pillar
|   +-- alert_checker.py      # Clarity pillar
|   +-- brain_dump/
|   |   +-- classifier.py     # AI classification (Capture pillar)
|   |   +-- router.py         # Routing logic (Capture pillar)
|   +-- adapters/
|       +-- base.py           # BaseAdapter interface
|       +-- oura.py           # Health data adapter
|       +-- workos.py         # Task management adapter
|       +-- ...               # Other adapters
|
+-- State/
|   +-- thanos_unified.db     # Main SQLite database
|   +-- thanos.db             # Journal database
|   +-- cache/                # Circuit breaker cache
|       +-- oura/
|       +-- monarch/
|
+-- docs/
    +-- ARCHITECTURE.md       # This document
    +-- architecture.md       # MCP-focused architecture
```

---

## Summary

Thanos achieves reliable personal productivity through four integrated pillars:

| Pillar | Component | Purpose |
|--------|-----------|---------|
| **Trust** | StateStore + Journal | Single source of truth, full audit trail |
| **Capture** | Brain Dump Classifier + Router | Zero-friction input, intelligent routing |
| **Clarity** | Alert Checker | Proactive visibility into what matters |
| **Resilience** | Circuit Breaker + Cache | Graceful degradation when APIs fail |

Each pillar reinforces the others:
- **Trust** provides the data foundation for all other pillars
- **Capture** feeds data into the trust layer with proper classification
- **Clarity** queries the trust layer to surface important information
- **Resilience** protects the trust layer from external failures

This architecture enables a productivity system that is both powerful and forgiving - capturing everything, surfacing what matters, and continuing to work even when external services don't.
