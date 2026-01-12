# Commitment Accountability System - Architecture & Developer Guide

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Data Model](#data-model)
4. [Core Components](#core-components)
5. [API Reference](#api-reference)
6. [Integration Points](#integration-points)
7. [Extension Points](#extension-points)
8. [Code Examples](#code-examples)
9. [Testing](#testing)
10. [Performance Considerations](#performance-considerations)

---

## System Overview

The Commitment Accountability System is a comprehensive tracking and accountability framework designed to help users with ADHD maintain consistent follow-through on habits, goals, and tasks. The system provides automatic follow-ups, streak tracking, empathetic accountability through Coach persona integration, and weekly performance reviews.

### Design Philosophy

1. **Proactive, not reactive**: The system automatically prompts users rather than relying on them to remember
2. **ADHD-friendly**: Built with executive function challenges in mind
3. **Data-driven empathy**: Coach integration uses pattern analysis for contextual accountability
4. **Separation of concerns**: Clear boundaries between data, logic, presentation, and scheduling

### Key Features

- **Three commitment types**: Habits (recurring), Goals (milestone-based), Tasks (one-time)
- **Automatic streak tracking**: Maintains current streak, longest streak, and completion rate
- **Flexible recurrence patterns**: Daily, weekly, weekdays, weekends, custom
- **Follow-up scheduling**: Configurable reminders with escalation
- **Coach integration**: Empathetic accountability with escalating intervention levels
- **Weekly reviews**: Performance analytics with trends and insights
- **Multiple interfaces**: CLI commands, Python API, session hooks

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
├─────────────────────────────────────────────────────────────┤
│  CLI Commands          │  Session Hooks    │  Coach Persona  │
│  - commitment_add.py   │  - init.ts        │  - Coach.md     │
│  - commitment_update.py│                   │                 │
│  - commitment_list.py  │                   │                 │
└────────────┬───────────┴─────────┬─────────┴────────┬────────┘
             │                     │                  │
             ▼                     ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
├─────────────────────────────────────────────────────────────┤
│  Tools/                                                      │
│  - commitment_tracker.py    (CRUD + streak logic)           │
│  - commitment_scheduler.py  (scheduling + prompts)          │
│  - commitment_analytics.py  (performance metrics)           │
│  - commitment_review.py     (weekly reviews)                │
│  - coach_checkin.py         (Coach integration)             │
│  - commitment_check.py      (check-in orchestration)        │
│  - commitment_digest.py     (daily summaries)               │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
├─────────────────────────────────────────────────────────────┤
│  State/                                                      │
│  - CommitmentData.json      (enhanced metadata)             │
│  - Commitments.md           (user-facing view)              │
│                                                              │
│  Tools/                                                      │
│  - state_reader.py          (read operations)               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Creation Flow**:
   - User → CLI Command → CommitmentTracker.create_commitment() → JSON + Markdown

2. **Update Flow**:
   - User → CLI Command → CommitmentTracker.mark_completed() → Streak calculation → JSON + Markdown

3. **Check-in Flow**:
   - Session start → Hook → commitment_check.py → CommitmentScheduler → Display prompts

4. **Coach Flow**:
   - Commitment missed → coach_checkin.py detects pattern → Coach persona → Empathetic check-in

5. **Review Flow**:
   - Weekly trigger → commitment_review.py → CommitmentAnalytics → Generate insights → Output

### File Organization

```
.
├── Tools/
│   ├── commitment_tracker.py       # Core data model and CRUD
│   ├── commitment_scheduler.py     # Scheduling and prompts
│   ├── commitment_analytics.py     # Performance metrics
│   ├── commitment_review.py        # Weekly reviews
│   ├── coach_checkin.py            # Coach integration
│   ├── commitment_check.py         # Check-in orchestration
│   ├── commitment_digest.py        # Daily summaries
│   └── state_reader.py             # Read operations
│
├── commands/
│   ├── commitment_add.py           # Add commitments
│   ├── commitment_update.py        # Update/complete commitments
│   └── commitment_list.py          # List/filter commitments
│
├── hooks/
│   └── session-start/
│       └── init.ts                 # Session start integration
│
├── Agents/
│   └── Coach.md                    # Coach accountability protocols
│
├── State/
│   ├── CommitmentData.json         # Primary data store
│   └── Commitments.md              # User-facing view
│
├── Templates/
│   └── commitment_report.md        # Weekly review template
│
├── config/
│   └── commitment_schedule.json    # Scheduling configuration
│
├── tests/
│   ├── test_commitment_tracker.py  # Unit tests
│   └── test_commitment_integration.py  # Integration tests
│
└── docs/
    ├── commitment-system.md        # User guide
    └── commitment-system-architecture.md  # This file
```

---

## Data Model

### Core Data Structures

The system uses Python dataclasses for type safety and clarity. All data structures support JSON serialization.

#### Commitment

The primary data structure representing a commitment:

```python
@dataclass
class Commitment:
    """Core commitment data model."""

    # Identity
    id: str                          # UUID
    title: str                       # Display name
    type: str                        # CommitmentType enum

    # Status
    status: str                      # CommitmentStatus enum
    created_date: str                # ISO format
    due_date: Optional[str]          # ISO format

    # Recurrence
    recurrence_pattern: str          # RecurrencePattern enum

    # Tracking
    streak_count: int                # Current streak
    longest_streak: int              # Personal record
    completion_rate: float           # Percentage (0-100)
    completion_history: List[CompletionRecord]

    # Scheduling
    follow_up_schedule: FollowUpSchedule

    # Organization
    domain: str                      # work, personal, health, learning
    priority: int                    # 1 (highest) to 5 (lowest)
    tags: List[str]
    notes: str

    # Extensibility
    metadata: Dict[str, Any]
```

#### Enums

```python
class CommitmentType(str, Enum):
    """Types of commitments."""
    HABIT = "habit"      # Recurring behaviors
    GOAL = "goal"        # Milestone-based achievements
    TASK = "task"        # One-time actions

class CommitmentStatus(str, Enum):
    """Status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"

class RecurrencePattern(str, Enum):
    """Recurrence patterns."""
    DAILY = "daily"
    WEEKLY = "weekly"
    WEEKDAYS = "weekdays"    # Monday-Friday
    WEEKENDS = "weekends"    # Saturday-Sunday
    CUSTOM = "custom"        # Custom interval
    NONE = "none"           # One-time commitment
```

#### CompletionRecord

Tracks individual completion events:

```python
@dataclass
class CompletionRecord:
    """Record of a single completion event."""
    timestamp: str              # ISO format
    status: str                 # 'completed' or 'missed'
    notes: Optional[str]        # User notes
```

#### FollowUpSchedule

Manages reminder scheduling:

```python
@dataclass
class FollowUpSchedule:
    """Follow-up scheduling configuration."""
    enabled: bool
    next_check: Optional[str]        # ISO timestamp
    frequency_hours: int             # How often to check
    escalation_count: int            # Times escalated
    last_reminded: Optional[str]     # Last reminder timestamp
```

### Analytics Data Structures

#### WeeklyStats

```python
@dataclass
class WeeklyStats:
    """Statistics for a single week."""
    week_start: str
    week_end: str
    total_commitments: int
    completed_count: int
    missed_count: int
    completion_rate: float
    by_type: Dict[str, Dict[str, Any]]
    streak_milestones: List[Dict[str, Any]]
```

#### TrendAnalysis

```python
@dataclass
class TrendAnalysis:
    """Trend analysis comparing multiple weeks."""
    current_week: WeeklyStats
    previous_weeks: List[WeeklyStats]
    trend_direction: str              # 'improving', 'stable', 'declining'
    completion_rate_change: float
    streak_trends: Dict[str, Any]
    insights: List[str]
```

### Coach Integration Data Structures

#### CoachCheckinContext

```python
@dataclass
class CoachCheckinContext:
    """Comprehensive context for Coach check-in."""
    commitment_id: str
    commitment_title: str
    commitment_type: str

    # Status
    consecutive_misses: int
    should_trigger_coach: bool
    escalation_level: str
    escalation_reason: str

    # Pattern analysis
    total_misses: int
    miss_rate: float
    miss_by_weekday: Dict[str, int]
    completion_by_weekday: Dict[str, int]

    # Context
    current_streak: int
    longest_streak: int
    completion_rate: float

    # Coaching
    coach_suggestion: str
    suggested_approach: str
```

### Database Schema (JSON)

The `State/CommitmentData.json` file structure:

```json
{
  "version": "1.0",
  "updated_at": "ISO timestamp",
  "commitments": [
    {
      "id": "uuid",
      "title": "string",
      "type": "habit|goal|task",
      "status": "pending|in_progress|completed|missed|cancelled",
      "created_date": "ISO date",
      "due_date": "ISO date or null",
      "recurrence_pattern": "daily|weekly|weekdays|weekends|custom|none",
      "streak_count": 0,
      "longest_streak": 0,
      "completion_rate": 0.0,
      "completion_history": [
        {
          "timestamp": "ISO timestamp",
          "status": "completed|missed",
          "notes": "string or null"
        }
      ],
      "follow_up_schedule": {
        "enabled": true,
        "next_check": "ISO timestamp or null",
        "frequency_hours": 24,
        "escalation_count": 0,
        "last_reminded": "ISO timestamp or null"
      },
      "notes": "string",
      "domain": "work|personal|health|learning|general",
      "priority": 1-5,
      "tags": ["string"],
      "metadata": {}
    }
  ]
}
```

---

## Core Components

### 1. CommitmentTracker (`Tools/commitment_tracker.py`)

**Purpose**: Core data model and CRUD operations for commitments.

**Responsibilities**:
- Create, read, update, delete commitments
- Maintain JSON persistence (atomic writes)
- Calculate streaks and completion rates
- Detect misses and trigger Coach integration
- Provide filtering and querying capabilities

**Key Features**:
- Automatic streak calculation on completion
- Support for all recurrence patterns
- Thread-safe atomic file writes
- Graceful error handling for corrupted data
- JSON serialization/deserialization

**State Management**:
- In-memory dictionary of commitments (keyed by ID)
- Lazy loading on initialization
- Immediate persistence on modifications

### 2. CommitmentScheduler (`Tools/commitment_scheduler.py`)

**Purpose**: Determine when to prompt users about commitments.

**Responsibilities**:
- Identify commitments needing attention
- Calculate next check times
- Respect quiet hours configuration
- Escalate reminders for overdue items
- Generate structured prompts with urgency levels

**Key Features**:
- Configurable quiet hours (e.g., 22:00-07:00)
- Escalating reminder frequency (halving intervals)
- Priority-based urgency calculation
- Support for multiple follow-up frequencies
- Handles overnight quiet hours correctly

**Urgency Levels**:
1. Critical (overdue 7+ days)
2. High (overdue 3-6 days)
3. Medium (overdue 1-2 days)
4. Normal (due today)
5. Low (habit reminder)

### 3. CommitmentAnalytics (`Tools/commitment_analytics.py`)

**Purpose**: Calculate performance metrics and trends.

**Responsibilities**:
- Calculate weekly completion rates
- Track streak statistics and milestones
- Perform trend analysis across weeks
- Generate actionable insights
- Export analytics data for reporting

**Key Features**:
- Weekly statistics with type breakdown
- Multi-week trend comparison
- Completion rate trending (improving/stable/declining)
- Streak milestone detection
- Insight generation (success/warning/pattern/suggestion)

**Analytics Calculations**:
- **Completion rate**: (completed / (completed + missed)) × 100
- **Trend direction**: Based on rate change > ±5%
- **Average streak**: Sum of all active streaks / count
- **Milestone detection**: 3, 7, 14, 21, 30, 60, 90, 100+ day streaks

### 4. CommitmentReview (`Tools/commitment_review.py`)

**Purpose**: Generate weekly performance reviews.

**Responsibilities**:
- Create comprehensive weekly reports
- Generate Coach-style reflection prompts
- Calculate letter grades (A+ to F)
- Extract wins and areas for improvement
- Format output for multiple channels

**Key Features**:
- Letter grade system based on completion rate
- Coach-style summary messages
- 5 reflection prompt categories
- Multiple output formats (text, markdown, JSON)
- Integration with analytics engine

**Grading Scale**:
- A+ (95-100%), A (90-94%), A- (85-89%)
- B+ (80-84%), B (75-79%), B- (70-74%)
- C+ (65-69%), C (60-64%), C- (55-59%)
- D (50-54%), F (<50%)

### 5. CoachCheckin (`Tools/coach_checkin.py`)

**Purpose**: Enable Coach persona accountability check-ins.

**Responsibilities**:
- Detect commitments needing Coach intervention
- Generate comprehensive check-in context
- Provide pattern analysis (weekday breakdowns)
- Suggest appropriate Coach approaches
- Format prompts for Coach persona

**Key Features**:
- 6 escalation levels (celebrate → values alignment)
- Temporal pattern analysis (weekday miss/completion tracking)
- Consecutive miss detection
- Coach approach suggestions
- Multiple output formats (brief/detailed/prompt/JSON)

**Escalation Levels**:
1. **celebrate_or_encourage**: No misses, active streak
2. **gentle_curiosity**: 1-2 consecutive misses
3. **pattern_acknowledgment**: 3-4 consecutive misses
4. **direct_confrontation**: 5-7 consecutive misses
5. **commitment_redesign**: Low completion rate (<50%)
6. **values_alignment_check**: 8+ consecutive misses (chronic)

### 6. CommitmentCheck (`Tools/commitment_check.py`)

**Purpose**: Orchestrate check-ins and generate prompts.

**Responsibilities**:
- Check all commitments for due/overdue status
- Generate natural language prompts
- Output structured data for integration
- Support dry-run mode for testing
- Provide summary statistics

**Key Features**:
- CLI and module interfaces
- Natural language formatting with emoji
- JSON output for programmatic use
- Dry-run mode (no timestamp updates)
- Quiet hours support
- Exit codes for scripting (0=success, 1=overdue items)

### 7. CommitmentDigest (`Tools/commitment_digest.py`)

**Purpose**: Generate daily morning digests.

**Responsibilities**:
- Summarize today's commitments
- Highlight active streaks
- Show overdue items prominently
- Provide encouragement messaging
- Analyze completion trends

**Key Features**:
- Categorized sections (overdue/due today/habits)
- Streak milestone highlighting
- Context-aware encouragement
- Trend analysis (improving/stable/declining)
- Multiple output modes (standard/detailed/JSON)

**Encouragement Logic**:
- Based on overdue count, active streaks, day of week
- Randomized messages to maintain freshness
- Growth-oriented framing
- No shame-based language

---

## API Reference

### CommitmentTracker API

#### Initialization

```python
tracker = CommitmentTracker(state_dir: Optional[Path] = None)
```

**Parameters**:
- `state_dir`: Path to State directory (defaults to `../State` relative to module)

**Returns**: CommitmentTracker instance with loaded commitments

#### Create Commitment

```python
commitment = tracker.create_commitment(
    title: str,
    commitment_type: str,
    recurrence_pattern: str = "none",
    due_date: Optional[str] = None,
    domain: str = "general",
    priority: int = 3,
    tags: List[str] = None,
    notes: str = ""
) -> Commitment
```

**Parameters**:
- `title`: Commitment title
- `commitment_type`: "habit", "goal", or "task"
- `recurrence_pattern`: "daily", "weekly", "weekdays", "weekends", "custom", "none"
- `due_date`: ISO format date string (required for goals/tasks)
- `domain`: "work", "personal", "health", "learning", "general"
- `priority`: 1 (highest) to 5 (lowest)
- `tags`: List of tag strings
- `notes`: Additional notes

**Returns**: Created Commitment object

**Side Effects**: Persists to JSON, updates Commitments.md

#### Retrieve Commitment

```python
commitment = tracker.get_commitment(commitment_id: str) -> Optional[Commitment]
```

**Returns**: Commitment object or None if not found

#### Filter Commitments

```python
commitments = tracker.get_commitments(
    commitment_type: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> List[Commitment]
```

**Returns**: List of commitments matching all specified filters

#### Update Commitment

```python
success = tracker.update_commitment(
    commitment_id: str,
    **updates
) -> bool
```

**Parameters**:
- `commitment_id`: ID of commitment to update
- `**updates`: Keyword arguments for fields to update

**Returns**: True if successful, False if commitment not found

**Side Effects**: Persists changes, updates Commitments.md

#### Mark as Completed

```python
success = tracker.mark_completed(
    commitment_id: str,
    notes: Optional[str] = None
) -> bool
```

**Side Effects**:
- Adds CompletionRecord to history
- Recalculates streak (increments if consecutive)
- Updates completion rate
- Updates status
- Persists changes

**Returns**: True if successful

#### Mark as Missed

```python
success = tracker.mark_missed(
    commitment_id: str,
    notes: Optional[str] = None
) -> bool
```

**Side Effects**:
- Adds CompletionRecord with 'missed' status
- Breaks current streak (resets to 0)
- Updates completion rate
- Updates status
- Persists changes

**Returns**: True if successful

#### Delete Commitment

```python
success = tracker.delete_commitment(commitment_id: str) -> bool
```

**Returns**: True if deleted, False if not found

**Side Effects**: Removes from JSON and Commitments.md

#### Streak Calculation

```python
tracker.recalculate_streaks(commitment_id: str) -> None
```

**Purpose**: Recalculate streak for a specific commitment

**Algorithm**:
1. Sort completion history by timestamp (newest first)
2. Determine expected dates based on recurrence pattern
3. Count consecutive completions from today backward
4. Stop at first gap in expected dates
5. Update current_streak, longest_streak, completion_rate

**Recurrence Logic**:
- **Daily**: Every day
- **Weekly**: Same day of week
- **Weekdays**: Monday-Friday
- **Weekends**: Saturday-Sunday
- **None**: No recurrence (one-time)

```python
tracker.recalculate_all_streaks() -> None
```

**Purpose**: Recalculate streaks for all commitments (batch operation)

#### Miss Detection & Coach Integration

```python
consecutive = tracker.get_consecutive_miss_count(commitment_id: str) -> int
```

**Returns**: Number of consecutive expected occurrences that were missed

**Logic**:
- For recurring: Count missed expected dates from today backward
- For one-time: 1 if overdue and not completed, 0 otherwise
- Does not count today if not yet due

```python
trigger_info = tracker.should_trigger_coach(commitment_id: str) -> Dict
```

**Returns**:
```python
{
    'should_trigger': bool,
    'escalation_level': str,  # See escalation levels above
    'reason': str,
    'consecutive_misses': int
}
```

```python
pattern = tracker.get_miss_pattern_analysis(commitment_id: str) -> Dict
```

**Returns**:
```python
{
    'total_misses': int,
    'total_completions': int,
    'miss_rate': float,  # Percentage
    'miss_by_weekday': {
        'Monday': int,
        'Tuesday': int,
        ...
    },
    'completion_by_weekday': {
        'Monday': int,
        ...
    }
}
```

```python
context = tracker.get_coach_context(commitment_id: str) -> Dict
```

**Returns**: Comprehensive dict with all Coach-relevant information:
- Commitment details
- Consecutive misses
- Escalation level
- Pattern analysis
- Streak history
- Follow-up info
- Coach suggestion

#### Export/Import

```python
data = tracker.export_data() -> Dict
```

**Returns**: Complete data structure for export

```python
tracker.import_data(data: Dict) -> None
```

**Purpose**: Import commitment data (replaces existing)

### CommitmentScheduler API

#### Initialization

```python
scheduler = CommitmentScheduler(
    state_dir: Optional[Path] = None,
    quiet_hours_start: str = "22:00",
    quiet_hours_end: str = "07:00"
)
```

#### Get Commitments Needing Prompt

```python
prompts = scheduler.get_commitments_needing_prompt(
    respect_quiet_hours: bool = True
) -> List[ScheduledPrompt]
```

**Returns**: List of ScheduledPrompt objects with:
- commitment_id
- title
- reason (overdue/due_today/habit_reminder)
- urgency (1-5)
- next_prompt_time (ISO timestamp)

#### Check Quiet Hours

```python
is_quiet = scheduler.is_quiet_hours() -> bool
```

**Returns**: True if current time is within quiet hours

#### Calculate Next Check Time

```python
next_time = scheduler.calculate_next_check(
    commitment: Commitment
) -> Optional[str]
```

**Returns**: ISO timestamp for next check, respecting quiet hours

#### Mark as Prompted

```python
scheduler.mark_prompted(commitment_id: str) -> None
```

**Side Effects**:
- Updates last_reminded timestamp
- Increments escalation_count
- Persists changes

### CommitmentAnalytics API

#### Initialization

```python
analytics = CommitmentAnalytics(state_dir: Optional[Path] = None)
```

#### Get Weekly Stats

```python
stats = analytics.get_weekly_stats(
    week_offset: int = 0
) -> WeeklyStats
```

**Parameters**:
- `week_offset`: 0 for current week, 1 for last week, etc.

**Returns**: WeeklyStats object

#### Get Trend Analysis

```python
trend = analytics.get_trend_analysis(
    weeks_to_compare: int = 4
) -> TrendAnalysis
```

**Returns**: TrendAnalysis object with multi-week comparison

#### Get Insights

```python
insights = analytics.get_insights() -> List[CommitmentInsight]
```

**Returns**: List of actionable insights (success/warning/pattern/suggestion)

#### Get Commitment Performance

```python
performance = analytics.get_commitment_performance(
    commitment_id: str,
    weeks: int = 4
) -> Dict
```

**Returns**: Performance history for specific commitment

### CoachCheckin API

#### Initialization

```python
coach = CoachCheckin(state_dir: Optional[Path] = None)
```

#### Get Check-in Context

```python
context = coach.get_checkin_context(
    commitment_id: str
) -> CoachCheckinContext
```

**Returns**: Complete context for Coach check-in

#### Get Commitments Needing Coach

```python
commitments = coach.get_commitments_needing_coach() -> List[CoachCheckinContext]
```

**Returns**: All commitments requiring Coach intervention, sorted by urgency

#### Format Check-in

```python
# Brief format
brief = coach.format_checkin_brief(context: CoachCheckinContext) -> str

# Detailed format
detailed = coach.format_checkin_detailed(context: CoachCheckinContext) -> str

# Coach prompt format
prompt = coach.format_coach_prompt(context: CoachCheckinContext) -> str
```

---

## Integration Points

### 1. Session Start Hook

**File**: `hooks/session-start/init.ts`

**Integration**: TypeScript hook calls Python commitment_check.py

```typescript
// Check commitments and display prompts
const result = await checkCommitments();
if (result) {
  displayCommitmentPrompts(result.prompts);
}
```

**Configuration**:
- 5-second timeout for non-blocking
- Graceful fallback to legacy method if tool not found
- Uses `--json` and `--dry-run` flags

### 2. Command Router

**File**: `Tools/command_router.py`

**Registered Commands**:
- `/commitment:add` - Add new commitment
- `/commitment:new` - Alias for add
- `/commitment:update <id>` - Update commitment
- `/commitment:complete <id>` - Quick complete
- `/commitment:list` - List commitments
- `/commitment:ls` - Alias for list

**Integration Pattern**:
```python
def _cmd_commitment_add(self, args: str) -> str:
    result = subprocess.run(
        ['python3', 'commands/commitment_add.py'] + args.split(),
        capture_output=True,
        text=True
    )
    return result.stdout
```

### 3. Coach Persona

**File**: `Agents/Coach.md`

**Integration Points**:
- Commitment Accountability Protocols section
- Missed commitment check-in style
- Escalation patterns
- Streak celebration protocols
- Pattern analysis queries

**Coach Access**:
Coach persona can invoke `coach_checkin.py` to get comprehensive context for accountability conversations.

### 4. State Reader

**File**: `Tools/state_reader.py`

**Extension Methods**:
- `get_commitment_data()` - Load CommitmentData.json
- `get_commitments()` - Filter commitments
- `get_due_today()` - Due today
- `get_overdue_commitments()` - Overdue items
- `get_commitment_streaks()` - Active streaks
- `get_commitment_summary()` - Statistics

**Integration**: Provides read-only access for quick context

### 5. Weekly Review Scheduling

**File**: `config/commitment_schedule.json`

**Configuration**:
```json
{
  "reviews": {
    "weekly_review": {
      "enabled": true,
      "schedule": {
        "day_of_week": "sunday",
        "time": "20:00",
        "alternative": {
          "day_of_week": "monday",
          "time": "08:00"
        }
      }
    }
  }
}
```

**Integration**: Scheduled task runner can use this config to trigger weekly reviews

---

## Extension Points

### 1. Custom Recurrence Patterns

**Current**: Daily, weekly, weekdays, weekends, custom, none

**Extension Point**: `RecurrencePattern` enum and streak calculation logic

**How to Extend**:
```python
# 1. Add enum value
class RecurrencePattern(str, Enum):
    # ... existing patterns ...
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"

# 2. Update streak calculation in CommitmentTracker._calculate_expected_dates()
def _calculate_expected_dates(self, commitment: Commitment) -> List[date]:
    pattern = commitment.recurrence_pattern

    if pattern == RecurrencePattern.BIWEEKLY:
        # Generate dates every 2 weeks
        pass
    elif pattern == RecurrencePattern.MONTHLY:
        # Generate monthly dates
        pass
```

### 2. Additional Commitment Types

**Current**: Habit, Goal, Task

**Extension Point**: `CommitmentType` enum

**How to Extend**:
```python
class CommitmentType(str, Enum):
    HABIT = "habit"
    GOAL = "goal"
    TASK = "task"
    PROJECT = "project"  # New type
    ROUTINE = "routine"  # New type

# Update analytics to handle new types
# Update CLI commands to accept new types
# Update Coach protocols for type-specific approaches
```

### 3. Custom Analytics

**Extension Point**: `CommitmentAnalytics` class

**How to Extend**:
```python
class CommitmentAnalytics:
    # ... existing methods ...

    def get_productivity_score(self) -> float:
        """Calculate custom productivity score."""
        # Your logic here
        pass

    def get_domain_breakdown(self) -> Dict[str, Any]:
        """Analyze performance by domain."""
        # Your logic here
        pass
```

### 4. Integration with External Systems

**Extension Point**: Metadata field in Commitment

**Example - Todoist Integration**:
```python
commitment = tracker.create_commitment(
    title="Review PRs",
    commitment_type="task",
    metadata={
        "todoist_id": "12345",
        "todoist_project": "Work",
        "sync_enabled": True
    }
)

# Create sync module
class TodoistSync:
    def sync_commitment(self, commitment: Commitment):
        todoist_id = commitment.metadata.get("todoist_id")
        if todoist_id:
            # Sync logic
            pass
```

### 5. Custom Coach Escalation Logic

**Extension Point**: `should_trigger_coach()` method

**How to Extend**:
```python
def should_trigger_coach(self, commitment_id: str) -> Dict:
    # ... existing logic ...

    # Add custom triggers
    if commitment.priority == 1 and consecutive_misses >= 2:
        return {
            'should_trigger': True,
            'escalation_level': 'priority_override',
            'reason': 'High priority commitment missed twice',
            'consecutive_misses': consecutive_misses
        }
```

### 6. Notification Channels

**Current**: CLI output, file export

**Extension Point**: Delivery configuration in `commitment_schedule.json`

**How to Extend**:
```python
class NotificationService:
    def send_to_slack(self, message: str):
        # Slack integration
        pass

    def send_push_notification(self, message: str):
        # Push notification
        pass

    def send_email_digest(self, review: WeeklyReview):
        # Email integration
        pass
```

### 7. Custom Insight Generation

**Extension Point**: `get_insights()` method in CommitmentAnalytics

**How to Extend**:
```python
def get_insights(self) -> List[CommitmentInsight]:
    insights = []  # ... existing insights ...

    # Add custom insight
    if self._detect_burnout_pattern():
        insights.append(CommitmentInsight(
            type='warning',
            category='wellbeing',
            message='Detected potential burnout pattern',
            data={'recommendation': 'Consider reducing commitment load'}
        ))

    return insights
```

---

## Code Examples

### Example 1: Creating and Tracking a Habit

```python
from Tools.commitment_tracker import CommitmentTracker

# Initialize tracker
tracker = CommitmentTracker()

# Create a daily meditation habit
meditation = tracker.create_commitment(
    title="Morning meditation",
    commitment_type="habit",
    recurrence_pattern="daily",
    domain="health",
    priority=1,
    tags=["mindfulness", "morning-routine"],
    notes="10 minutes of guided meditation"
)

print(f"Created habit: {meditation.id}")

# Mark as completed for today
tracker.mark_completed(meditation.id, notes="Felt very focused today")

# Check streak
updated = tracker.get_commitment(meditation.id)
print(f"Current streak: {updated.streak_count} days")
print(f"Completion rate: {updated.completion_rate}%")
```

### Example 2: Checking What's Due

```python
from Tools.commitment_scheduler import CommitmentScheduler

scheduler = CommitmentScheduler()

# Get all prompts (respecting quiet hours)
prompts = scheduler.get_commitments_needing_prompt()

for prompt in prompts:
    print(f"[Urgency {prompt.urgency}] {prompt.title}")
    print(f"  Reason: {prompt.reason}")
    print(f"  Next check: {prompt.next_prompt_time}")
```

### Example 3: Generating Weekly Review

```python
from Tools.commitment_review import CommitmentReview

review = CommitmentReview()

# Generate current week review
weekly = review.generate_weekly_review()

print(f"Grade: {weekly.completion_grade} {weekly.grade_emoji}")
print(f"Completion Rate: {weekly.overall_completion_rate}%")
print(f"\nCoach's Message:\n{weekly.coach_message}")

# Show insights
for insight in weekly.key_insights:
    print(f"[{insight.type}] {insight.message}")

# Save to file
review.save_review(weekly, "History/CommitmentReviews/week-2026-01-11.md")
```

### Example 4: Coach Check-in

```python
from Tools.coach_checkin import CoachCheckin

coach = CoachCheckin()

# Get all commitments needing Coach
needing_attention = coach.get_commitments_needing_coach()

for context in needing_attention:
    if context.should_trigger_coach:
        print(f"\n{context.commitment_title}")
        print(f"Escalation: {context.escalation_level}")
        print(f"Consecutive misses: {context.consecutive_misses}")

        # Generate Coach prompt
        prompt = coach.format_coach_prompt(context)
        print(prompt)
```

### Example 5: Analytics and Trends

```python
from Tools.commitment_analytics import CommitmentAnalytics

analytics = CommitmentAnalytics()

# Get current week stats
stats = analytics.get_weekly_stats()
print(f"This week: {stats.completion_rate}% completion rate")

# Get trend analysis
trend = analytics.get_trend_analysis(weeks_to_compare=4)
print(f"Trend: {trend.trend_direction}")
print(f"Change: {trend.completion_rate_change:+.1f}%")

# Get insights
insights = analytics.get_insights()
for insight in insights:
    if insight.type == 'success':
        print(f"✅ {insight.message}")
    elif insight.type == 'warning':
        print(f"⚠️  {insight.message}")
```

### Example 6: Filtering and Querying

```python
from Tools.commitment_tracker import CommitmentTracker

tracker = CommitmentTracker()

# Get all active habits
habits = tracker.get_commitments(
    commitment_type="habit",
    status="in_progress"
)

# Get high-priority work commitments
work_priorities = [
    c for c in tracker.get_commitments(domain="work")
    if c.priority <= 2
]

# Get commitments with specific tag
fitness = [
    c for c in tracker.get_all_commitments()
    if "fitness" in c.tags
]

# Get overdue commitments
overdue = [
    c for c in tracker.get_all_commitments()
    if c.is_overdue()
]
```

### Example 7: Pattern Analysis

```python
from Tools.commitment_tracker import CommitmentTracker

tracker = CommitmentTracker()

# Analyze miss patterns for a commitment
pattern = tracker.get_miss_pattern_analysis(commitment_id)

print(f"Miss rate: {pattern['miss_rate']:.1f}%")
print("\nMisses by weekday:")
for day, count in pattern['miss_by_weekday'].items():
    if count > 0:
        print(f"  {day}: {count} misses")

# Check if Coach should be triggered
trigger = tracker.should_trigger_coach(commitment_id)
if trigger['should_trigger']:
    print(f"\nCoach intervention recommended:")
    print(f"  Level: {trigger['escalation_level']}")
    print(f"  Reason: {trigger['reason']}")
```

### Example 8: Custom Metadata Usage

```python
from Tools.commitment_tracker import CommitmentTracker

tracker = CommitmentTracker()

# Create commitment with custom metadata
gym = tracker.create_commitment(
    title="Gym workout",
    commitment_type="habit",
    recurrence_pattern="weekdays",
    metadata={
        "location": "LA Fitness",
        "duration_minutes": 60,
        "workout_type": "strength",
        "tracking_app": "Strong",
        "reminders": ["07:00", "18:00"]
    }
)

# Later, retrieve and use metadata
commitment = tracker.get_commitment(gym.id)
duration = commitment.metadata.get("duration_minutes", 30)
print(f"Expected duration: {duration} minutes")
```

---

## Testing

### Test Structure

The commitment system has comprehensive test coverage:

#### Unit Tests (`tests/test_commitment_tracker.py`)

**Coverage**: 62 tests covering:
- Commitment creation and validation (6 tests)
- Retrieval and filtering (10 tests)
- Updates and CRUD operations (7 tests)
- Streak calculation logic (7 tests)
- Recurrence pattern handling (5 tests)
- Data persistence (9 tests)
- Miss detection and Coach integration (9 tests)
- Instance methods (5 tests)
- JSON serialization (4 tests)

**Run Tests**:
```bash
pytest tests/test_commitment_tracker.py -v
```

#### Integration Tests (`tests/test_commitment_integration.py`)

**Coverage**: 25 tests covering:
- Complete workflows (3 tests)
- Coach integration scenarios (3 tests)
- Scheduler integration (4 tests)
- Weekly review generation (4 tests)
- Data consistency (4 tests)
- Multi-component integration (4 tests)
- Edge cases (3 tests)

**Run Tests**:
```bash
pytest tests/test_commitment_integration.py -v
```

### Testing Best Practices

#### 1. Use Temporary Directories

```python
import tempfile
from pathlib import Path

def test_commitment_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = CommitmentTracker(state_dir=Path(tmpdir))
        # Test code here
        # Cleanup is automatic
```

#### 2. Test Temporal Logic

```python
from datetime import datetime, timedelta

def test_streak_calculation():
    tracker = CommitmentTracker()
    commitment = tracker.create_commitment(
        title="Test habit",
        commitment_type="habit",
        recurrence_pattern="daily"
    )

    # Simulate completions over multiple days
    for i in range(5):
        date = (datetime.now() - timedelta(days=4-i)).isoformat()
        tracker.mark_completed(commitment.id)

    # Verify streak
    updated = tracker.get_commitment(commitment.id)
    assert updated.streak_count == 5
```

#### 3. Test Error Handling

```python
def test_corrupted_data_handling():
    with tempfile.TemporaryDirectory() as tmpdir:
        data_file = Path(tmpdir) / "CommitmentData.json"
        data_file.write_text("invalid json {")

        # Should not crash, should handle gracefully
        tracker = CommitmentTracker(state_dir=Path(tmpdir))
        assert len(tracker.get_all_commitments()) == 0
```

#### 4. Test Integration Points

```python
def test_coach_integration():
    tracker = CommitmentTracker()

    # Create and miss multiple times
    commitment = tracker.create_commitment(
        title="Test",
        commitment_type="habit",
        recurrence_pattern="daily"
    )

    for _ in range(3):
        tracker.mark_missed(commitment.id)

    # Verify Coach trigger
    trigger = tracker.should_trigger_coach(commitment.id)
    assert trigger['should_trigger'] == True
    assert trigger['escalation_level'] == 'pattern_acknowledgment'
```

### Manual Testing

**CLI Command Testing**:
```bash
# Test add command
python3 commands/commitment_add.py --title "Test" --type habit --recurrence daily

# Test list command
python3 commands/commitment_list.py --streaks

# Test update command
python3 commands/commitment_update.py <id> --complete

# Test analytics
python3 Tools/commitment_analytics.py --trend

# Test review
python3 Tools/commitment_review.py --detailed
```

---

## Performance Considerations

### File I/O Optimization

**Current Approach**: Load all on init, persist on modification

**Considerations**:
- Atomic writes prevent corruption
- In-memory cache avoids repeated file reads
- JSON serialization is reasonably fast for <1000 commitments

**Scaling Strategy**:
```python
# For very large datasets, consider lazy loading
class LazyCommitmentTracker(CommitmentTracker):
    def get_commitment(self, commitment_id: str) -> Optional[Commitment]:
        if commitment_id not in self.commitments:
            self._load_commitment(commitment_id)
        return self.commitments.get(commitment_id)
```

### Streak Calculation Performance

**Current**: O(n) where n = completion history length

**Optimization**: Cache calculated streaks, recalculate only on new completions

```python
# Already implemented - streaks stored in Commitment object
# Only recalculated when mark_completed() or mark_missed() is called
```

### Analytics Performance

**Current**: Analyzes all commitments for weekly stats

**For large datasets**:
```python
# Consider caching weekly stats
class CachedAnalytics(CommitmentAnalytics):
    def __init__(self):
        super().__init__()
        self._stats_cache = {}

    def get_weekly_stats(self, week_offset: int = 0) -> WeeklyStats:
        cache_key = f"week_{week_offset}"
        if cache_key in self._stats_cache:
            return self._stats_cache[cache_key]

        stats = super().get_weekly_stats(week_offset)
        self._stats_cache[cache_key] = stats
        return stats
```

### Query Performance

**Current**: In-memory filtering (fast for <10,000 commitments)

**For very large datasets**:
- Consider SQLite backend
- Implement indexing on frequently queried fields
- Use connection pooling

**Example SQLite Migration**:
```python
import sqlite3

class SQLiteCommitmentTracker:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS commitments (
                id TEXT PRIMARY KEY,
                title TEXT,
                type TEXT,
                status TEXT,
                domain TEXT,
                priority INTEGER,
                -- ... other fields
                INDEX idx_type_status (type, status),
                INDEX idx_due_date (due_date)
            )
        """)
```

### Memory Usage

**Current**: All commitments loaded in memory

**Typical Usage**:
- 100 commitments × ~2KB each = ~200KB
- Negligible for modern systems

**For mobile/embedded**:
- Implement pagination
- Load only active commitments
- Use streaming JSON parser

---

## Future Enhancements

### Planned Features

1. **Smart Scheduling**
   - ML-based optimal reminder times
   - Learn user's productive hours
   - Adaptive frequency based on response patterns

2. **Social Accountability**
   - Share commitments with accountability partners
   - Group challenges (e.g., "30-day meditation challenge")
   - Leaderboards and friendly competition

3. **Advanced Analytics**
   - Correlation analysis (sleep × workout completion)
   - Predictive modeling (likelihood to miss)
   - Energy level tracking integration

4. **Integration Ecosystem**
   - Calendar sync (Google Calendar, iCal)
   - Task manager integration (Todoist, Things)
   - Health app integration (Apple Health, Google Fit)
   - Time tracking (Toggl, RescueTime)

5. **Voice Interface**
   - Voice commands via Siri/Google Assistant
   - Voice check-ins and updates
   - Audio daily digest

6. **Gamification**
   - Achievement badges
   - Experience points and levels
   - Streak competitions
   - Reward unlocks

### Research Questions

1. **Optimal Reminder Frequency**: What's the sweet spot between helpful and annoying?
2. **Coach Tone**: Which escalation approach is most effective for ADHD users?
3. **Streak Pressure**: Do streaks motivate or create anxiety?
4. **Commitment Load**: What's the optimal number of active commitments?

---

## Contributing

### Code Style

- Follow PEP 8 for Python code
- Use type hints wherever possible
- Write descriptive docstrings for all public methods
- Keep functions focused (single responsibility)

### Adding New Features

1. **Design**: Document the feature in this architecture guide first
2. **Test**: Write tests before implementation (TDD)
3. **Implement**: Follow existing patterns
4. **Document**: Update both user guide and architecture guide
5. **Test**: Ensure all tests pass
6. **Commit**: Use descriptive commit messages

### Pull Request Checklist

- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] No breaking changes (or documented if necessary)
- [ ] Performance impact considered
- [ ] User guide updated if user-facing

---

## Appendix

### A. File Format Specifications

#### CommitmentData.json Schema

See [Data Model](#data-model) section for complete schema.

#### Commitments.md Format

```markdown
# Commitments

## Work
- [ ] ⚡ Complete quarterly report (Due: 2026-01-15) #high-priority
- [ ] 🔄 Daily Review team PRs #recurring

## Health
- [x] 🔥 Morning workout (7-day streak!) #habit
- [ ] Schedule annual checkup (Due: 2026-02-01)

## Learning
- [ ] Master Python programming (Due: 2026-01-25) #goal #python
```

### B. Emoji Reference

**Status**:
- ✅ Completed
- ⬜ Pending
- 🔄 In Progress
- ❌ Missed
- 🚫 Cancelled

**Priority**:
- ⚡ P1 (Highest)
- 🔴 P2 (High)
- 🟡 P3 (Medium)
- 🟢 P4 (Low)
- ⚪ P5 (Lowest)

**Recurrence**:
- 🔄 Recurring
- 📅 Weekly
- 💼 Weekdays
- 🌴 Weekends

**Streaks**:
- 🔥 Active streak
- 💯 100+ day streak
- 🌟 30+ day milestone
- ⭐ 7+ day milestone

**Urgency**:
- 🚨 Critical (7+ days overdue)
- ⚠️  Warning (overdue)
- 📅 Due today
- ⏰ Due soon

### C. Glossary

**Commitment**: A trackable promise to oneself (habit, goal, or task)

**Streak**: Number of consecutive expected completions

**Completion Rate**: Percentage of expected completions actually completed

**Recurrence Pattern**: Schedule defining when a habit should occur

**Follow-up Schedule**: Configuration for automatic reminders

**Escalation**: Progressive increase in reminder urgency

**Coach Intervention**: Empathetic accountability check-in when patterns indicate struggle

**Weekly Review**: Summary of commitment performance with trends and insights

**Miss Pattern**: Analysis of which days/times commitments are typically missed

**Quiet Hours**: Time range when non-urgent reminders are suppressed

---

## Version History

- **v1.0** (2026-01-12): Initial architecture documentation
  - Complete system overview
  - Data model documentation
  - API reference
  - Integration and extension points
  - Code examples and testing guide

---

## License

This commitment system is part of the Thanos project. See main project license for details.

---

## Contact & Support

For questions, issues, or contributions related to the commitment system architecture, refer to the main Thanos project documentation and contribution guidelines.
