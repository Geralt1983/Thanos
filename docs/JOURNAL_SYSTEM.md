# Journal Event Logging System

## Overview

The Journal is an **append-only event log** that serves as the single source of truth for "what happened" across all Thanos integrations. It provides:

- **Audit trail** - Complete history of all significant actions
- **Observability** - Real-time visibility into system behavior
- **Alerting** - Severity-based alerts with acknowledgement workflow
- **Debugging** - Searchable event history for troubleshooting

The journal stores events in a SQLite database (`State/thanos.db`) with WAL mode for performance and data integrity.

---

## Event Types by Category

The system defines **47 event types** across 9 categories:

### Task Events (5 types)
| Event Type | Description |
|------------|-------------|
| `TASK_CREATED` | New task was created |
| `TASK_UPDATED` | Task was modified |
| `TASK_COMPLETED` | Task was marked complete |
| `TASK_CANCELLED` | Task was cancelled |
| `TASK_OVERDUE` | Task passed its due date |

### Calendar Events (4 types)
| Event Type | Description |
|------------|-------------|
| `EVENT_CREATED` | Calendar event was created |
| `EVENT_UPCOMING` | Event is approaching |
| `EVENT_STARTED` | Event has begun |
| `EVENT_MISSED` | Event was missed |

### Health Events (3 types)
| Event Type | Description |
|------------|-------------|
| `HEALTH_METRIC_LOGGED` | Health metric recorded (sleep, HRV, etc.) |
| `HEALTH_ALERT` | Health metric triggered warning |
| `HEALTH_SUMMARY` | Daily health summary generated |

### Finance Events (6 types)
| Event Type | Description |
|------------|-------------|
| `BALANCE_LOGGED` | Account balance recorded |
| `BALANCE_WARNING` | Balance below warning threshold |
| `BALANCE_CRITICAL` | Balance critically low |
| `LARGE_TRANSACTION` | Large transaction detected |
| `PROJECTION_WARNING` | Cash flow projection warning |
| `RECURRING_UPCOMING` | Recurring expense approaching |

### Brain Dump Events (8 types)
| Event Type | Description |
|------------|-------------|
| `BRAIN_DUMP_RECEIVED` | Raw brain dump input received |
| `BRAIN_DUMP_PARSED` | Brain dump was parsed into components |
| `BRAIN_DUMP_THINKING` | Reflective/thinking content captured |
| `BRAIN_DUMP_VENTING` | Emotional venting captured |
| `BRAIN_DUMP_OBSERVATION` | Observation/insight captured |
| `NOTE_CAPTURED` | General note captured |
| `IDEA_CAPTURED` | Idea captured for later review |
| `IDEA_PROMOTED` | Idea promoted to actionable item |

### System Events (9 types)
| Event Type | Description |
|------------|-------------|
| `SYNC_STARTED` | Data sync initiated |
| `SYNC_COMPLETED` | Data sync completed successfully |
| `SYNC_FAILED` | Data sync failed |
| `CIRCUIT_OPENED` | Circuit breaker opened (service unavailable) |
| `CIRCUIT_CLOSED` | Circuit breaker closed (service recovered) |
| `CIRCUIT_HALF_OPEN` | Circuit breaker testing recovery |
| `DAEMON_STARTED` | Background daemon started |
| `DAEMON_STOPPED` | Background daemon stopped |
| `ERROR_OCCURRED` | System error occurred |

### Commitment Events (4 types)
| Event Type | Description |
|------------|-------------|
| `COMMITMENT_CREATED` | New commitment made |
| `COMMITMENT_COMPLETED` | Commitment fulfilled |
| `COMMITMENT_DUE_SOON` | Commitment deadline approaching |
| `COMMITMENT_OVERDUE` | Commitment past due date |

### Session Events (3 types)
| Event Type | Description |
|------------|-------------|
| `SESSION_STARTED` | Interactive session began |
| `SESSION_ENDED` | Interactive session ended |
| `COMMAND_EXECUTED` | Command was executed |

### Alert Events (5 types)
| Event Type | Description |
|------------|-------------|
| `ALERT_CREATED` | New alert generated |
| `ALERT_ACKNOWLEDGED` | Alert was acknowledged |
| `ALERT_RESOLVED` | Alert condition resolved |
| `ALERT_RAISED` | Alert escalated |
| `ALERT_CHECK_COMPLETE` | Alert check cycle completed |

---

## Severity Levels

Events have one of 5 severity levels:

| Level | Description | Use Case |
|-------|-------------|----------|
| `debug` | Detailed debugging info | Development, troubleshooting |
| `info` | Normal operations | Task completions, syncs |
| `warning` | Potential issues | Low balance, missed events |
| `alert` | Requires attention | Health warnings, overdue tasks |
| `critical` | Urgent action needed | Critical balance, system failures |

---

## Logging Events

### Basic Logging

```python
from Tools.journal import Journal, EventType, get_journal

# Get singleton instance
journal = get_journal()

# Log a basic event
journal.log(
    event_type=EventType.TASK_COMPLETED,
    source="workos",
    title="Completed: Review Q4 financials",
    data={"task_id": "abc123", "duration_hours": 2.5}
)
```

### Log Method Signature

```python
def log(
    self,
    event_type: EventType,      # Required: Event type enum
    source: str,                 # Required: Source system (workos, oura, monarch, etc.)
    title: str,                  # Required: Human-readable summary
    content: str = None,         # Optional: Body content (merged into data)
    data: Dict = None,           # Optional: Structured metadata
    severity: str = "info",      # Optional: debug/info/warning/alert/critical
    session_id: str = None,      # Optional: Associated session
    agent: str = None            # Optional: Agent that triggered event
) -> int:                        # Returns: Event ID
```

### Convenience Functions

The module provides helper functions for common patterns:

```python
from Tools.journal import (
    log_task_event,
    log_health_alert,
    log_finance_warning,
    log_sync_event,
    log_circuit_event
)

# Log task events
log_task_event(
    EventType.TASK_COMPLETED,
    task_id="task123",
    title="Finished code review",
    duration_minutes=45
)

# Log health alerts
log_health_alert(
    title="Low sleep score: 62",
    metrics={"sleep_score": 62, "hrv": 35},
    recommendations=["Earlier bedtime", "Reduce caffeine"]
)

# Log finance warnings
log_finance_warning(
    title="Checking account low",
    account="Primary Checking",
    balance=450.00,
    threshold=500.00
)

# Log sync events
log_sync_event(
    source="oura",
    success=True,
    message="Synced 7 days of health data",
    details={"records": 7}
)

# Log circuit breaker changes
log_circuit_event(
    source="monarch_api",
    state="open",  # open, closed, half_open
    reason="Connection timeout"
)
```

---

## Querying Events

### Basic Query

```python
from datetime import datetime, timedelta
from Tools.journal import get_journal, EventType

journal = get_journal()

# Query with filters
entries = journal.query(
    event_types=[EventType.TASK_COMPLETED, EventType.TASK_CREATED],
    sources=["workos"],
    severity_min="info",
    since=datetime.now() - timedelta(days=7),
    until=datetime.now(),
    limit=100,
    offset=0
)

for entry in entries:
    print(f"{entry.timestamp}: {entry.title}")
```

### Query Method Signature

```python
def query(
    self,
    event_types: List[EventType] = None,  # Filter by event types
    sources: List[str] = None,             # Filter by sources
    severity_min: str = None,              # Minimum severity level
    since: datetime = None,                # Events after this time
    until: datetime = None,                # Events before this time
    acknowledged: bool = None,             # Filter by ack status
    limit: int = 100,                      # Max results
    offset: int = 0                        # Skip first N results
) -> List[JournalEntry]:
```

### Specialized Query Methods

```python
# Get today's events
today_events = journal.get_today(source="workos")

# Get recent alerts
alerts = journal.get_recent_alerts(limit=5)

# Get unacknowledged alerts only
unacked = journal.get_alerts(
    since=datetime.now() - timedelta(hours=24),
    unacknowledged_only=True
)

# Get thinking/reflection entries
reflections = journal.get_thinking_entries(
    since=datetime.now() - timedelta(days=7)
)

# Get a specific entry by ID
entry = journal.get_entry(entry_id=123)
```

---

## Alert Integration

### How Alerts Work

Alerts are journal entries with severity of `warning`, `alert`, or `critical`. They have an acknowledgement workflow:

1. **Created** - Alert logged with elevated severity
2. **Unacknowledged** - Appears in alert queries
3. **Acknowledged** - Marked as seen, with timestamp
4. **Resolved** - (Optional) Logged when condition clears

### Querying Alerts

```python
# Get all unacknowledged alerts
alerts = journal.get_alerts(unacknowledged_only=True)

# Count alerts
total_alerts = journal.count_alerts()
unacked_count = journal.count_alerts(acknowledged=False)
acked_count = journal.count_alerts(acknowledged=True)
```

### Acknowledging Alerts

```python
# Acknowledge a single alert
success = journal.acknowledge_alert(entry_id=123)

# Acknowledge all alerts at once
count = journal.acknowledge_all_alerts()
print(f"Acknowledged {count} alerts")
```

### Alert Data Structure

```python
@dataclass
class JournalEntry:
    id: int
    timestamp: str
    event_type: str
    source: str
    severity: str
    title: str
    data: Optional[Dict]
    session_id: Optional[str]
    agent: Optional[str]
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
```

---

## Statistics and Reporting

### Get Journal Stats

```python
from datetime import datetime, timedelta

# Get stats for last 24 hours (default)
stats = journal.get_stats()

# Get stats for specific period
stats = journal.get_stats(since=datetime.now() - timedelta(days=7))

print(stats)
# {
#     'total_events': 156,
#     'by_severity': {'info': 140, 'warning': 14, 'critical': 2},
#     'by_source': {'workos': 80, 'oura': 40, 'monarch': 36},
#     'top_event_types': {'task_completed': 45, 'sync_completed': 30, ...},
#     'unacknowledged_alerts': 5,
#     'period_start': '2024-01-15T10:30:00'
# }
```

### Formatted Output

```python
# Format a single entry for display
formatted = journal.format_entry(entry)
# "⚠️ [14:30] Low sleep score: 62 (oura)"

# Get formatted daily summary
summary = journal.format_today_summary()
print(summary)
# 📊 Today's Activity (42 events)
#
# 🚨 Alerts:
#    ⚠️ [08:15] Low sleep score: 62 (oura)
#    ⚠️ [10:30] Checking account low (monarch)
#
# 📋 Recent Activity:
#    ℹ️ [14:30] Completed: Review PR (workos)
#    ℹ️ [14:15] Synced health data (oura)
```

---

## Use Cases

### 1. Debugging Issues

```python
# Find all errors in the last hour
errors = journal.query(
    event_types=[EventType.ERROR_OCCURRED, EventType.SYNC_FAILED],
    since=datetime.now() - timedelta(hours=1)
)

# Check circuit breaker history
circuits = journal.query(
    event_types=[
        EventType.CIRCUIT_OPENED,
        EventType.CIRCUIT_CLOSED,
        EventType.CIRCUIT_HALF_OPEN
    ],
    sources=["monarch_api"]
)
```

### 2. Activity Tracking

```python
# Weekly productivity report
week_ago = datetime.now() - timedelta(days=7)

completed = journal.query(
    event_types=[EventType.TASK_COMPLETED],
    since=week_ago
)
print(f"Tasks completed this week: {len(completed)}")

# Track brain dump activity
brain_dumps = journal.query(
    event_types=[EventType.BRAIN_DUMP_RECEIVED],
    since=week_ago
)
```

### 3. Compliance/Audit Trail

```python
# Export all events for audit
all_events = journal.query(
    since=datetime(2024, 1, 1),
    limit=10000
)

# Convert to audit format
audit_log = []
for entry in all_events:
    audit_log.append({
        'timestamp': entry.timestamp,
        'event_type': entry.event_type,
        'source': entry.source,
        'severity': entry.severity,
        'title': entry.title,
        'data': entry.data,
        'acknowledged': entry.acknowledged,
        'acknowledged_at': entry.acknowledged_at
    })

# Export to JSON
import json
with open('audit_export.json', 'w') as f:
    json.dump(audit_log, f, indent=2)
```

### 4. Health Monitoring Dashboard

```python
# Get health events for dashboard
health_events = journal.query(
    event_types=[
        EventType.HEALTH_METRIC_LOGGED,
        EventType.HEALTH_ALERT,
        EventType.HEALTH_SUMMARY
    ],
    sources=["oura"],
    since=datetime.now() - timedelta(days=30)
)

# Separate alerts from normal logging
alerts = [e for e in health_events if e.severity != 'info']
metrics = [e for e in health_events if e.event_type == 'health_metric_logged']
```

---

## Database Schema

The journal uses a single table with indexes for fast queries:

```sql
CREATE TABLE journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    severity TEXT DEFAULT 'info',
    title TEXT NOT NULL,
    data JSON,
    session_id TEXT,
    agent TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_journal_timestamp ON journal(timestamp);
CREATE INDEX idx_journal_event_type ON journal(event_type);
CREATE INDEX idx_journal_severity ON journal(severity);
CREATE INDEX idx_journal_source ON journal(source);
CREATE INDEX idx_journal_acknowledged ON journal(acknowledged);
```

---

## Best Practices

1. **Use appropriate severity** - Reserve `critical` for truly urgent issues
2. **Include context in data** - Store IDs, metrics, and details for debugging
3. **Be consistent with sources** - Use standard source names (workos, oura, monarch, system)
4. **Acknowledge alerts promptly** - Keep the alert queue clean
5. **Query with filters** - Always use `since` to avoid scanning entire history
6. **Use convenience functions** - They ensure consistent logging patterns
