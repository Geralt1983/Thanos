# StateStore API Documentation

Comprehensive API reference for the Thanos Unified State Store system.

## Overview

The StateStore is a SQLite-based unified state storage system that serves as the single source of truth for the Thanos life operating system. It consolidates all persistent data into a single database with a comprehensive 23-table schema.

### Key Features

- **SQLite-based**: Lightweight, embedded database with WAL mode for performance
- **23-table schema**: Comprehensive support for tasks, commitments, calendar, health, finances, and more
- **Domain separation**: Work vs personal context for all entities
- **Full-text search**: FTS5 indexes on notes and brain dumps
- **Event logging**: Append-only journal for audit trails
- **Multiple entry points**: Three complementary store implementations

### Architecture

```
State/
  thanos.db           # Primary database (via state_store/__init__.py)
  thanos_unified.db   # Alternative database (via unified_state.py or store.py)

Tools/
  unified_state.py              # StateStore class (original)
  state_store/
    __init__.py                 # UnifiedStateStore class (comprehensive)
    store.py                    # StateStore class (domain-focused)
    schema.sql                  # Full SQL schema definition
    summary_builder.py          # State summary utilities
```

---

## Quick Start

### Using UnifiedStateStore (Recommended)

```python
from Tools.state_store import get_db, UnifiedStateStore

# Get singleton instance
db = get_db()

# Or create with custom path
db = UnifiedStateStore(Path("./custom.db"))

# Create a task
task_id = db.create_task(
    title="Review Q4 financials",
    domain="work",
    source="manual",
    priority="high"
)

# Get active tasks
tasks = db.get_tasks(domain="work", status="pending")
```

### Using StateStore (Domain-Focused)

```python
from Tools.state_store.store import StateStore, get_store

# Get singleton instance
store = get_store()

# Create a task with domain separation
task_id = store.create_task(
    title="Call mom",
    domain="personal",
    priority="p1"
)

# Get work tasks only
work_tasks = store.get_tasks(domain="work")
```

### Using Legacy StateStore

```python
from Tools.unified_state import StateStore, get_state_store

store = get_state_store()

# Legacy method signatures
task_id = store.add_task(
    title="Budget review",
    priority="p1",
    due_date=date.today()
)
```

---

## Task Management

Tasks are the core entity representing actionable items with status, priority, and domain separation.

### Data Model

```python
@dataclass
class Task:
    id: str
    title: str
    description: Optional[str] = None
    status: str = "pending"  # pending, active, queued, backlog, done, cancelled
    priority: Optional[str] = None  # critical, high, medium, low (or p0-p3)
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    domain: str = "work"  # work, personal
    context: Optional[str] = None  # @home, @office, @errands
    energy_level: Optional[str] = None  # high, medium, low
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    source: str = "manual"  # manual, brain_dump, workos, calendar, telegram
    source_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    project_id: Optional[str] = None
    tags: Optional[List[str]] = None
    recurrence: Optional[Dict] = None  # {"frequency": "daily", "interval": 1}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[Dict] = None
```

### UnifiedStateStore Methods

```python
def create_task(
    self,
    title: str,
    domain: str,
    source: str,
    description: Optional[str] = None,
    status: str = "pending",
    priority: Optional[str] = None,
    due_date: Optional[Union[str, date]] = None,
    due_time: Optional[str] = None,
    context: Optional[str] = None,
    source_id: Optional[str] = None,
    energy_level: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict] = None,
) -> str:
    """Create a new task. Returns task ID."""

def get_task(self, task_id: str) -> Optional[Dict]:
    """Get a task by ID. Returns dict or None."""

def get_tasks(
    self,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    due_date: Optional[Union[str, date]] = None,
    limit: int = 50,
) -> List[Dict]:
    """Get tasks with optional filters. Ordered by due_date, priority."""

def update_task(self, task_id: str, **updates) -> bool:
    """Update task fields. Returns True if updated."""

def complete_task(self, task_id: str) -> bool:
    """Mark task as done with completion timestamp."""
```

### StateStore Methods (store.py)

```python
def create_task(
    self,
    title: str,
    description: Optional[str] = None,
    priority: Optional[str] = None,  # p0, p1, p2, p3
    due_date: Optional[date] = None,
    domain: str = "work",
    source: str = "manual",
    source_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Create a new task. Returns task ID."""

def get_task(self, task_id: str) -> Optional[Task]:
    """Get a task by ID. Returns Task dataclass."""

def get_tasks(
    self,
    domain: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    priority: Optional[str] = None,
    include_completed: bool = False,
    limit: int = 100
) -> List[Task]:
    """Get tasks with flexible filtering."""

def update_task(self, task_id: str, **updates) -> bool:
    """Update task. Allowed fields: title, description, status, priority, due_date, domain, tags, metadata."""

def complete_task(self, task_id: str) -> bool:
    """Mark task as completed."""

def count_tasks(
    self,
    domain: Optional[str] = None,
    status: Optional[str] = None,
    overdue: bool = False
) -> int:
    """Count tasks matching filters."""
```

### Legacy StateStore Methods (unified_state.py)

```python
def add_task(
    self,
    title: str,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[date] = None,
    source: str = "manual",
    source_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> str:
    """Add a new task. Returns task ID."""

def get_task(self, task_id: str) -> Optional[Task]:
    """Get task by ID."""

def get_tasks(
    self,
    status: Optional[str] = None,
    source: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100
) -> List[Task]:
    """Get tasks with optional filters."""

def get_tasks_due_today(self) -> List[Task]:
    """Get tasks due today (excluding completed/cancelled)."""

def get_overdue_tasks(self) -> List[Task]:
    """Get overdue tasks."""

def count_tasks(self, status: Optional[str] = None) -> int:
    """Count tasks, optionally by status."""
```

### Examples

```python
# Create a high-priority work task
task_id = db.create_task(
    title="Q4 budget review",
    domain="work",
    source="manual",
    priority="high",
    due_date=date.today() + timedelta(days=3),
    context="@office",
    energy_level="high",
    tags=["finance", "quarterly"],
    metadata={"stakeholder": "CFO"}
)

# Update task status
db.update_task(task_id, status="active")

# Get all pending work tasks
pending = db.get_tasks(domain="work", status="pending")

# Complete the task
db.complete_task(task_id)
```

---

## Commitment Management

Commitments track promises made to others, with ADHD-friendly accountability features.

### Data Model

```python
@dataclass
class Commitment:
    id: str
    title: str
    description: Optional[str] = None
    person: str  # Who you committed to (required)
    person_email: Optional[str] = None
    commitment_type: str  # deliverable, meeting, followup, response, review, other
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    status: str = "active"  # active, completed, broken, renegotiated, cancelled
    priority: Optional[str] = None
    context: Optional[str] = None  # Where/how committed
    reminder_sent: bool = False
    reminder_count: int = 0
    last_reminder_at: Optional[str] = None
    related_task_id: Optional[str] = None
    related_event_id: Optional[str] = None
    source: str = "manual"
    source_id: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict] = None
```

### UnifiedStateStore Methods

```python
def create_commitment(
    self,
    title: str,
    person: str,
    commitment_type: str = "deliverable",
    due_date: Optional[Union[str, date]] = None,
    description: Optional[str] = None,
    priority: str = "medium",
    source: str = "manual",
    metadata: Optional[Dict] = None,
) -> str:
    """Create a new commitment. Returns commitment ID."""

def get_active_commitments(self, person: Optional[str] = None) -> List[Dict]:
    """Get active commitments, optionally filtered by person."""
```

### StateStore Methods (store.py)

```python
def create_commitment(
    self,
    title: str,
    description: Optional[str] = None,
    stakeholder: Optional[str] = None,
    deadline: Optional[date] = None,
    priority: Optional[str] = None,
    domain: str = "work",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Create a new commitment. Returns commitment ID."""

def get_commitments(
    self,
    domain: Optional[str] = None,
    status: str = "active",
    stakeholder: Optional[str] = None,
    due_within_days: Optional[int] = None,
    limit: int = 100
) -> List[Commitment]:
    """Get commitments with flexible filtering."""

def complete_commitment(self, commitment_id: str) -> bool:
    """Mark commitment as completed."""

def count_commitments(
    self,
    domain: Optional[str] = None,
    status: str = "active"
) -> int:
    """Count commitments."""
```

### Legacy Methods (unified_state.py)

```python
def add_commitment(
    self,
    title: str,
    description: Optional[str] = None,
    stakeholder: Optional[str] = None,
    deadline: Optional[date] = None,
    priority: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> str:
    """Add a new commitment."""

def get_active_commitments(self) -> List[Commitment]:
    """Get all active commitments."""

def get_commitments_due_soon(self, days: int = 7) -> List[Commitment]:
    """Get commitments due within specified days."""

def complete_commitment(self, commitment_id: str) -> bool:
    """Mark commitment as completed."""

def count_active_commitments(self) -> int:
    """Count active commitments."""
```

### Examples

```python
# Create a commitment
commitment_id = db.create_commitment(
    title="Deliver Q4 report",
    person="Sarah Chen",
    commitment_type="deliverable",
    due_date=date.today() + timedelta(days=5),
    priority="high",
    metadata={"project": "quarterly-review"}
)

# Get commitments due within 7 days
due_soon = store.get_commitments(due_within_days=7)

# Complete a commitment
db.complete_commitment(commitment_id)
```

---

## Calendar Integration

Calendar events synchronized from Google Calendar or other sources.

### Data Model

```python
@dataclass
class CalendarEvent:
    id: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: str  # Required
    end_time: str  # Required
    all_day: bool = False
    calendar_id: Optional[str] = None
    calendar_name: Optional[str] = None
    event_type: Optional[str] = None  # meeting, focus, personal, travel, reminder, other
    attendees: Optional[List[Dict]] = None  # [{"email": "", "name": "", "status": ""}]
    conferencing: Optional[Dict] = None  # {"type": "zoom", "url": "..."}
    reminders: Optional[List[Dict]] = None  # [{"method": "popup", "minutes": 15}]
    recurrence_rule: Optional[str] = None  # RRULE string
    source: str = "google"
    source_id: Optional[str] = None
    status: str = "confirmed"  # confirmed, tentative, cancelled
    created_at: Optional[str] = None
    synced_at: Optional[str] = None
    metadata: Optional[Dict] = None
```

### Legacy Methods (unified_state.py)

```python
def add_calendar_event(
    self,
    title: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    location: Optional[str] = None,
    source: str = "google",
    source_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> str:
    """Add a calendar event. Returns event ID."""

def get_events_today(self) -> List[CalendarEvent]:
    """Get today's calendar events."""

def get_events_range(
    self,
    start: datetime,
    end: datetime
) -> List[CalendarEvent]:
    """Get events in a date range."""

def get_next_event(self) -> Optional[CalendarEvent]:
    """Get the next upcoming event."""

def count_events_today(self) -> int:
    """Count today's events."""
```

### Views

```sql
-- Today's agenda (tasks + events)
SELECT * FROM v_today_agenda;

-- Returns: item_type, id, title, description, time, priority, domain, status, energy_level, context
```

### Examples

```python
# Add a calendar event
event_id = store.add_calendar_event(
    title="Team standup",
    start_time=datetime(2026, 1, 20, 9, 0),
    end_time=datetime(2026, 1, 20, 9, 30),
    location="Zoom",
    metadata={"recurring": True, "attendees": ["team@company.com"]}
)

# Get today's events
today_events = store.get_events_today()

# Get this week's events
from datetime import datetime, timedelta
start = datetime.now()
end = start + timedelta(days=7)
week_events = store.get_events_range(start, end)
```

---

## Health Tracking

Health metrics from Oura ring or other sources.

### Data Model

```python
@dataclass
class HealthMetric:
    id: str
    date: str
    metric_type: str  # sleep, readiness, activity, hrv, heart_rate, spo2, stress, resilience, workout, weight
    score: Optional[int] = None  # 0-100 for Oura metrics
    value: Optional[float] = None  # Raw value (HRV in ms, weight in kg)
    unit: Optional[str] = None
    details: Optional[Dict] = None  # Full metric breakdown
    source: str = "oura"
    source_id: Optional[str] = None
    recorded_at: Optional[str] = None
    synced_at: Optional[str] = None
    metadata: Optional[Dict] = None
```

### UnifiedStateStore Methods

```python
def store_health_metric(
    self,
    date: Union[str, date],
    metric_type: str,
    score: Optional[int] = None,
    value: Optional[float] = None,
    unit: Optional[str] = None,
    details: Optional[Dict] = None,
    source: str = "oura",
    source_id: Optional[str] = None,
) -> str:
    """Store a health metric. Returns metric ID."""

def get_health_metrics(
    self,
    start_date: Optional[Union[str, date]] = None,
    end_date: Optional[Union[str, date]] = None,
    metric_type: Optional[str] = None,
) -> List[Dict]:
    """Get health metrics with optional filters."""
```

### StateStore Methods (store.py)

```python
def log_health_metric(
    self,
    metric_type: str,
    value: float,
    metric_date: Optional[date] = None,
    source: str = "oura",
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """Log a health metric. Uses INSERT OR REPLACE for upsert behavior."""

def get_health_metrics(
    self,
    metric_date: Optional[date] = None,
    metric_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    source: Optional[str] = None,
    limit: int = 100
) -> List[HealthMetric]:
    """Get health metrics with flexible filtering."""
```

### Legacy Methods (unified_state.py)

```python
def log_health_metric(
    self,
    metric_type: str,
    value: float,
    metric_date: Optional[date] = None,
    source: str = "oura",
    metadata: Optional[Dict] = None
) -> int:
    """Log a health metric. Returns metric ID."""

def get_health_metrics(
    self,
    metric_date: Optional[date] = None,
    metric_type: Optional[str] = None
) -> List[HealthMetric]:
    """Get health metrics."""

def get_today_health(self) -> Dict[str, float]:
    """Get today's health metrics as {metric_type: value}."""
```

### Views

```sql
-- Weekly health summary
SELECT * FROM v_weekly_health;

-- Returns: date, sleep_score, readiness_score, activity_score, hrv_avg, stress_score
```

### Examples

```python
# Log Oura metrics
db.store_health_metric(
    date=date.today(),
    metric_type="sleep",
    score=85,
    details={"total_sleep": 28800, "efficiency": 92, "rem": 5400}
)

db.store_health_metric(
    date=date.today(),
    metric_type="hrv",
    value=45.5,
    unit="ms"
)

# Get last week's sleep scores
from datetime import date, timedelta
metrics = db.get_health_metrics(
    start_date=date.today() - timedelta(days=7),
    metric_type="sleep"
)
```

---

## Financial Tracking

Financial accounts, balances, and transactions.

### Data Models

```python
@dataclass
class FinanceAccount:
    id: str
    name: str
    institution: Optional[str] = None
    account_type: str  # checking, savings, credit, investment, loan, mortgage, retirement, crypto
    currency: str = "USD"
    is_active: bool = True
    source: Optional[str] = None
    source_id: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class FinanceBalance:
    id: int
    account_id: str
    balance: float
    available_balance: Optional[float] = None
    as_of_date: str
    source: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class FinanceTransaction:
    id: str
    account_id: str
    date: str
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    transaction_type: str  # debit, credit, transfer
    is_pending: bool = False
    is_recurring: bool = False
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    metadata: Optional[Dict] = None
```

### Legacy Methods (unified_state.py)

```python
def log_account_balance(
    self,
    account_id: str,
    account_name: str,
    balance: float,
    available: Optional[float] = None,
    balance_date: Optional[date] = None,
    source: str = "monarch",
    metadata: Optional[Dict] = None
) -> int:
    """Log account balance. Returns record ID."""

def get_latest_balances(self) -> List[FinanceAccount]:
    """Get most recent balance for each account."""

def get_total_available(self) -> float:
    """Get total available balance across all accounts."""
```

### Views

```sql
-- Net worth by account type
SELECT * FROM v_net_worth;

-- Returns: account_type, total_balance, account_count
```

### Examples

```python
# Log account balances
store.log_account_balance(
    account_id="checking_001",
    account_name="Main Checking",
    balance=5432.10,
    available=5232.10
)

# Get all latest balances
balances = store.get_latest_balances()

# Calculate net worth
total = store.get_total_available()
```

---

## Brain Dump Operations

Capture raw thoughts for later processing.

### Data Model

```python
@dataclass
class BrainDump:
    id: str
    content: str
    content_type: str = "text"  # text, voice, photo
    category: Optional[str] = None  # thought, task, idea, worry, note, question
    context: Optional[str] = None  # work, personal
    priority: Optional[str] = None
    source: str = "manual"  # manual, telegram, cli, web
    source_context: Optional[Dict] = None  # {"chat_id": "", "message_id": ""}
    processed: bool = False
    archived: bool = False
    promoted_to_task_id: Optional[str] = None
    promoted_to_idea_id: Optional[str] = None
    sentiment: Optional[str] = None  # positive, neutral, negative, mixed
    urgency: Optional[str] = None  # immediate, today, soon, someday
    domain: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None
    processed_at: Optional[str] = None
    processing_result: Optional[Dict] = None
    metadata: Optional[Dict] = None
```

### UnifiedStateStore Methods

```python
def create_brain_dump(
    self,
    content: str,
    source: str,
    category: Optional[str] = None,
    source_context: Optional[Dict] = None,
    domain: Optional[str] = None,
    urgency: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> str:
    """Create a new brain dump entry. Returns dump ID."""

def get_unprocessed_brain_dumps(self, limit: int = 20) -> List[Dict]:
    """Get unprocessed brain dump entries."""

def process_brain_dump(
    self,
    dump_id: str,
    result: Optional[Dict] = None,
) -> bool:
    """Mark a brain dump as processed."""
```

### StateStore Methods (store.py)

```python
def create_brain_dump(
    self,
    content: str,
    content_type: str = "text",
    category: Optional[str] = None,
    context: Optional[str] = None,
    priority: Optional[str] = None,
    source: str = "manual",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Create a brain dump entry. Returns dump ID."""

def get_brain_dumps(
    self,
    processed: Optional[bool] = None,
    archived: bool = False,
    context: Optional[str] = None,
    limit: int = 100
) -> List[BrainDump]:
    """Get brain dump entries with filtering."""

def archive_brain_dump(self, dump_id: str) -> bool:
    """Archive a brain dump entry (marks as processed too)."""

def count_brain_dumps(
    self,
    processed: Optional[bool] = None,
    archived: bool = False
) -> int:
    """Count brain dump entries."""
```

### Full-Text Search

Brain dumps have FTS5 indexing for content search:

```sql
-- Search brain dumps
SELECT * FROM brain_dumps
WHERE id IN (
    SELECT rowid FROM brain_dumps_fts
    WHERE brain_dumps_fts MATCH 'search query'
);
```

### Examples

```python
# Capture a brain dump from Telegram
dump_id = db.create_brain_dump(
    content="Need to call the accountant about Q4 taxes",
    source="telegram",
    category="task",
    domain="work",
    urgency="soon",
    source_context={"chat_id": "12345", "message_id": "67890"}
)

# Get unprocessed dumps
unprocessed = db.get_unprocessed_brain_dumps(limit=10)

# Process and convert to task
task_id = db.create_task(
    title="Call accountant re: Q4 taxes",
    domain="work",
    source="brain_dump",
    source_id=dump_id
)

db.process_brain_dump(dump_id, result={
    "action": "converted_to_task",
    "task_id": task_id
})
```

---

## Ideas (Someday/Maybe)

Capture ideas that may become tasks later.

### Data Model

```python
@dataclass
class Idea:
    id: str
    title: str
    content: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None  # project, feature, content, business, personal, learning
    domain: str = "work"
    status: str = "captured"  # captured, researching, planned, rejected, converted
    potential_value: Optional[str] = None  # high, medium, low, unknown
    effort_estimate: Optional[str] = None  # trivial, small, medium, large, huge, unknown
    related_focus_id: Optional[str] = None
    converted_to_task_id: Optional[str] = None
    promoted_to_task_id: Optional[str] = None
    source: str = "brain_dump"
    tags: Optional[List[str]] = None
    links: Optional[List[Dict]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    metadata: Optional[Dict] = None
```

### StateStore Methods (store.py)

```python
def create_idea(
    self,
    content: str,
    category: Optional[str] = None,
    domain: str = "work",
    source: str = "manual",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Create a new idea. Returns idea ID."""

def get_ideas(
    self,
    domain: Optional[str] = None,
    status: str = "captured",
    category: Optional[str] = None,
    limit: int = 100
) -> List[Idea]:
    """Get ideas with optional filters."""

def promote_idea_to_task(
    self,
    idea_id: str,
    title: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[date] = None
) -> Optional[str]:
    """Promote an idea to a task. Returns task ID or None."""
```

### Examples

```python
# Capture an idea
idea_id = store.create_idea(
    content="Build a CLI dashboard for daily metrics",
    category="feature",
    domain="work"
)

# Later, promote to task
task_id = store.promote_idea_to_task(
    idea_id,
    title="Build CLI metrics dashboard",
    priority="p2",
    due_date=date.today() + timedelta(days=14)
)
```

---

## Focus Areas

Track current priorities and goals.

### Data Model

```python
@dataclass
class FocusArea:
    id: str
    title: str
    description: Optional[str] = None
    domain: str  # work, personal, health, relationship, financial, growth
    timeframe: Optional[str] = None  # daily, weekly, monthly, quarterly, yearly
    status: str = "active"  # active, paused, completed, abandoned
    priority: int = 0
    progress_percent: int = 0
    target_date: Optional[str] = None
    success_criteria: Optional[str] = None
    key_results: Optional[List[Dict]] = None  # OKR-style
    parent_focus_id: Optional[str] = None
    is_active: bool = True
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[Dict] = None
```

### StateStore Methods (store.py)

```python
def set_focus(
    self,
    title: str,
    description: Optional[str] = None,
    domain: str = "work",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Set a new focus area (deactivates existing ones in same domain). Returns focus ID."""

def get_active_focus(
    self,
    domain: Optional[str] = None
) -> List[FocusArea]:
    """Get active focus areas, optionally filtered by domain."""
```

### Legacy Methods (unified_state.py)

```python
def add_focus_area(
    self,
    title: str,
    description: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> str:
    """Add a new focus area."""

def get_active_focus_areas(self) -> List[FocusArea]:
    """Get all active focus areas."""
```

### Views

```sql
-- Focus progress tracking
SELECT * FROM v_focus_progress;

-- Returns: id, title, domain, timeframe, progress_percent, target_date, health
-- health: overdue, complete, on_track, at_risk, behind
```

### Examples

```python
# Set work focus (auto-deactivates previous work focus)
focus_id = store.set_focus(
    title="Ship v2.0 release",
    description="Complete all v2 features and launch",
    domain="work"
)

# Get all active focus areas
active = store.get_active_focus()

# Get work focus only
work_focus = store.get_active_focus(domain="work")
```

---

## Notes

Reference material and documentation.

### Data Model

```python
@dataclass
class Note:
    id: str
    title: str
    content: Optional[str] = None
    content_type: str = "markdown"  # markdown, plain, html, json
    category: Optional[str] = None  # reference, meeting, project, person, process, learning
    domain: str = "personal"
    tags: Optional[List[str]] = None
    related_task_id: Optional[str] = None
    related_event_id: Optional[str] = None
    related_person: Optional[str] = None
    source: str = "manual"
    source_id: Optional[str] = None
    pinned: bool = False
    archived: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict] = None
```

### StateStore Methods (store.py)

```python
def create_note(
    self,
    content: str,
    title: Optional[str] = None,
    category: Optional[str] = None,
    domain: str = "personal",
    tags: Optional[List[str]] = None,
    source: str = "manual",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Create a new note. Returns note ID."""

def search_notes(
    self,
    query: str,
    domain: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
) -> List[Note]:
    """Search notes by content (uses LIKE on title and content)."""
```

### Full-Text Search

Notes have FTS5 indexing:

```sql
-- Search notes with FTS
SELECT n.* FROM notes n
WHERE n.rowid IN (
    SELECT rowid FROM notes_fts
    WHERE notes_fts MATCH 'search query'
);
```

---

## Habits

Track recurring habits with streak counting.

### Data Model

```python
@dataclass
class Habit:
    id: str
    name: str
    description: Optional[str] = None
    emoji: Optional[str] = None
    frequency: str = "daily"  # daily, weekly, weekdays
    time_of_day: Optional[str] = None  # morning, evening, anytime
    target_count: int = 1
    category: Optional[str] = None  # health, productivity, relationship, personal
    current_streak: int = 0
    longest_streak: int = 0
    is_active: bool = True
    source: str = "workos"
    source_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class HabitCompletion:
    id: int
    habit_id: str
    completed_at: str
    date: str
    count: int = 1
    note: Optional[str] = None
    source: str = "manual"
    metadata: Optional[Dict] = None
```

### Schema Tables

```sql
-- Habits
CREATE TABLE habits (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    emoji TEXT,
    frequency TEXT DEFAULT 'daily',
    time_of_day TEXT,
    target_count INTEGER DEFAULT 1,
    category TEXT,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    ...
);

-- Completions
CREATE TABLE habit_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id TEXT NOT NULL REFERENCES habits(id),
    date DATE NOT NULL,
    count INTEGER DEFAULT 1,
    note TEXT,
    UNIQUE(habit_id, date)
);
```

---

## Contacts (CRM)

Track relationships and contact frequency.

### Data Model

```python
@dataclass
class Contact:
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    relationship_type: Optional[str] = None  # client, colleague, friend, family, acquaintance
    importance: Optional[str] = None  # high, medium, low
    last_contact_date: Optional[str] = None
    next_contact_date: Optional[str] = None
    contact_frequency: Optional[str] = None  # daily, weekly, biweekly, monthly, quarterly, yearly
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    source: str = "manual"
    source_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict] = None
```

---

## Query Methods

### Raw SQL Execution

```python
def execute_sql(self, sql: str, params: tuple = ()) -> List[Dict]:
    """Execute raw SQL and return results as list of dicts."""
```

### Built-in Views

```python
# Today's agenda (tasks + events)
agenda = db.get_today_agenda()

# Overdue items
overdue = db.get_overdue_items()
```

### Available Views

| View | Description |
|------|-------------|
| `v_today_agenda` | Today's tasks and events combined |
| `v_overdue` | Overdue tasks and commitments |
| `v_weekly_health` | Last 7 days health metrics |
| `v_commitments_by_person` | Commitment counts by person |
| `v_focus_progress` | Focus areas with progress health |
| `v_net_worth` | Net worth by account type |

### Custom Queries

```python
# Get high-priority work tasks due this week
results = db.execute_sql("""
    SELECT * FROM tasks
    WHERE domain = 'work'
      AND priority IN ('high', 'critical')
      AND due_date BETWEEN date('now') AND date('now', '+7 days')
      AND status NOT IN ('done', 'cancelled')
    ORDER BY due_date, priority DESC
""")

# Get commitment summary by stakeholder
summary = db.execute_sql("""
    SELECT person, COUNT(*) as total,
           SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active
    FROM commitments
    GROUP BY person
    ORDER BY active DESC
""")
```

---

## Event Logging (Journal)

All state changes are logged to an append-only journal.

### UnifiedStateStore Methods

```python
def log_event(
    self,
    event_type: str,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor: str = "system",
    changes: Optional[Dict] = None,
    context: Optional[Dict] = None,
    session_id: Optional[str] = None,
) -> None:
    """Log an event to the journal."""

def get_journal_events(
    self,
    event_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 100,
) -> List[Dict]:
    """Get journal events with optional filters."""
```

### Event Types

- `task_created`, `task_updated`, `task_completed`
- `commitment_created`, `commitment_completed`
- `brain_dump_created`, `brain_dump_processed`
- `health_metric_logged`
- `focus_updated`

---

## State Key-Value Store

Simple key-value storage for application state.

```python
def get_state(self, key: str, default: Any = None) -> Any:
    """Get a state value by key. Values are JSON-decoded."""

def set_state(self, key: str, value: Any) -> None:
    """Set a state value. Values are JSON-encoded."""

def get_state_size(self) -> int:
    """Get total size of stored state in bytes."""
```

### Examples

```python
# Store session state
db.set_state("current_session", {
    "started_at": datetime.now().isoformat(),
    "focus": "Deep work mode"
})

# Retrieve state
session = db.get_state("current_session", default={})
```

---

## Export & Snapshot

### Export Summary

```python
# StateStore (store.py)
def export_summary(self) -> Dict[str, Any]:
    """Export summary with counts for all entity types."""

# Returns:
{
    "exported_at": "2026-01-18T10:00:00",
    "tasks": {
        "total": 45,
        "pending": 12,
        "overdue": 3,
        "work": 30,
        "personal": 15
    },
    "commitments": {
        "active": 8,
        "work": 6,
        "personal": 2
    },
    "brain_dumps": {
        "unprocessed": 5,
        "total": 42
    },
    "focus_areas": [...]
}
```

### Legacy Export (unified_state.py)

```python
def export_snapshot(self) -> Dict[str, Any]:
    """Export current state as JSON snapshot."""

def save_daily_snapshot(self, snapshot_dir: Optional[Path] = None) -> Path:
    """Save daily snapshot to file. Returns filepath."""

def export_today_markdown(self) -> str:
    """Generate Today.md equivalent from DB state."""

def export_commitments_markdown(self) -> str:
    """Generate Commitments.md equivalent from DB state."""
```

---

## Summary Builder

Utility for building formatted state summaries.

```python
from Tools.state_store.summary_builder import SummaryBuilder, StateSummary

builder = SummaryBuilder(max_chars=2000)

# Build state summary
summary = builder.build_state_summary({
    "today": {"focus": "Deep work", "energy": "high", "top3": ["A", "B", "C"]},
    "daily_plan": ["Item 1", "Item 2"],
    "scoreboard": {"wins": 5, "misses": 1, "streak": 3},
    "reminders": ["Call mom", "Submit report"],
    "tool_summaries": [{"tool_name": "calendar", "summary": "Synced 12 events"}]
})

print(summary.text)  # Formatted markdown
print(summary.char_count)  # Character count
print(summary.truncated)  # Whether truncated to fit limit

# Build context summary
context_text = builder.build_context_summary([
    {"title": "Task 1", "description": "Do something"},
    {"title": "Task 2", "description": "Do something else"}
], max_items=5)
```

---

## Database Configuration

### Pragmas

The database uses these SQLite pragmas for optimal performance:

```sql
PRAGMA foreign_keys = ON;   -- Enforce foreign key constraints
PRAGMA journal_mode = WAL;  -- Write-ahead logging for concurrency
```

### Schema Version

Track schema migrations:

```python
version = db.get_schema_version()
```

### Sync State

Track external sync status:

```sql
CREATE TABLE sync_state (
    id TEXT PRIMARY KEY,  -- 'google_calendar', 'workos', 'oura'
    last_sync_at TIMESTAMP,
    last_sync_status TEXT,  -- 'success', 'partial', 'failed'
    last_sync_error TEXT,
    sync_cursor TEXT,
    items_synced INTEGER DEFAULT 0,
    next_sync_at TIMESTAMP,
    config JSON
);
```

---

## Best Practices

### Domain Separation

Always specify domain for work/personal separation:

```python
# Work task
db.create_task(title="Review PR", domain="work", source="manual")

# Personal task
db.create_task(title="Buy groceries", domain="personal", source="manual")
```

### Source Tracking

Track where data originates:

```python
# From Telegram brain dump
db.create_brain_dump(content="...", source="telegram", source_context={"chat_id": "..."})

# From WorkOS sync
db.create_task(title="...", source="workos", source_id="workos_task_123")
```

### Use Transactions

For multi-step operations, use the connection context manager:

```python
with db.connection() as conn:
    cursor = conn.cursor()
    # Multiple operations
    cursor.execute("INSERT INTO tasks ...")
    cursor.execute("INSERT INTO journal ...")
    # Auto-commits on success, auto-rollbacks on error
```

### Metadata for Extensibility

Use the metadata JSON field for custom data:

```python
db.create_task(
    title="Review contract",
    domain="work",
    source="manual",
    metadata={
        "client": "Acme Corp",
        "contract_value": 50000,
        "urgency_reason": "Deadline from legal"
    }
)
```
