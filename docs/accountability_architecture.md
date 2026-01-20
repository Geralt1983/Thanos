# Accountability Architecture v1.0

## Overview

The Accountability Architecture transforms Thanos from a reactive task manager into a proactive life operating system. It processes brain dumps through an intelligent pipeline that categorizes, prioritizes, and enforces daily planning with consequences.

**The Four Stones of Impact:**
1. **Health** - Physical and mental wellbeing
2. **Stress** - Anxiety and cognitive load reduction
3. **Financials** - Money, wealth, security
4. **Relationships** - Family, friends, professional connections

---

## System Components

### 1. Brain Dump Processor

Transforms raw brain dumps into actionable items through classification and routing.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BRAIN DUMP PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [Raw Input]                                                            │
│      │                                                                   │
│      ▼                                                                   │
│  ┌────────────────┐                                                     │
│  │  CLASSIFIER    │  Determine: thought | project | task | worry        │
│  └───────┬────────┘                                                     │
│          │                                                               │
│    ┌─────┴─────┬─────────────┬─────────────┐                            │
│    ▼           ▼             ▼             ▼                            │
│ [THOUGHT]   [PROJECT]     [TASK]       [WORRY]                          │
│    │           │             │             │                            │
│    ▼           ▼             ▼             ▼                            │
│ Store for   Decompose    Route to      Convert to                       │
│ patterns    into tasks   work/personal manageable task                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. Impact Scoring Engine

Categorizes personal tasks by their potential impact across the four stones.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        IMPACT SCORING                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Personal Task → Impact Analysis                                        │
│                                                                          │
│  ┌────────────┬────────────┬────────────┬────────────┐                  │
│  │  HEALTH    │  STRESS    │ FINANCIALS │ RELATIONS  │                  │
│  │  (0-10)    │  (0-10)    │  (0-10)    │  (0-10)    │                  │
│  └─────┬──────┴─────┬──────┴─────┬──────┴─────┬──────┘                  │
│        │            │            │            │                          │
│        └────────────┴────────────┴────────────┘                          │
│                         │                                                │
│                         ▼                                                │
│              ┌──────────────────┐                                       │
│              │  COMPOSITE SCORE  │                                       │
│              │  (weighted sum)   │                                       │
│              └──────────────────┘                                       │
│                                                                          │
│  Impact Keywords:                                                        │
│  - Health: doctor, gym, exercise, sleep, medication, diet              │
│  - Stress: deadline, overdue, urgent, overwhelmed, anxiety             │
│  - Financial: payment, bill, invoice, money, budget, tax               │
│  - Relationships: call, visit, birthday, anniversary, family           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Work Prioritization Engine

Prioritizes work tasks using three lenses:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      WORK PRIORITIZATION                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Work Task → Priority Score                                             │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│  │   PILE SIZE     │  │  CLIENT NEGLECT │  │  ENERGY MATCH   │          │
│  │   (task count)  │  │  (days silent)  │  │  (readiness %)  │          │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘          │
│           │                    │                    │                    │
│           ▼                    ▼                    ▼                    │
│      Count tasks          Days since          Compare task              │
│      per client          last touch          cognitiveLoad             │
│                                               to readiness              │
│           │                    │                    │                    │
│           └────────────────────┴────────────────────┘                    │
│                              │                                           │
│                              ▼                                           │
│                    ┌──────────────────┐                                 │
│                    │  PRIORITY ORDER   │                                 │
│                    │  (mode-dependent) │                                 │
│                    └──────────────────┘                                 │
│                                                                          │
│  Modes:                                                                  │
│  - "biggest_pile": Sort by task count (most backlogged client first)   │
│  - "most_ignored": Sort by days since last interaction                 │
│  - "energy_match": Filter to current readiness level                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4. Daily Planning Enforcer

Ensures planning happens the night before with accountability tracking.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     DAILY PLANNING ENFORCER                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Evening Check (8 PM - 11 PM)                                           │
│                                                                          │
│  ┌──────────────────────────────────────┐                               │
│  │  Has tomorrow been planned?          │                               │
│  │                                      │                               │
│  │  Criteria:                           │                               │
│  │  - At least 3 tasks promoted to      │                               │
│  │    'active' for tomorrow             │                               │
│  │  - Daily goal set based on energy    │                               │
│  │  - Priority items identified         │                               │
│  └───────────────┬──────────────────────┘                               │
│                  │                                                       │
│         ┌───────┴───────┐                                               │
│         │               │                                               │
│         ▼               ▼                                               │
│      [YES]           [NO]                                               │
│         │               │                                               │
│         ▼               ▼                                               │
│  Record success   Send reminder                                         │
│  Update streak    │                                                      │
│                   ▼                                                      │
│              ┌────────────────┐                                         │
│              │  ESCALATION    │                                         │
│              │                │                                         │
│              │  8 PM: Gentle  │                                         │
│              │  9 PM: Firm    │                                         │
│              │  10 PM: Urgent │                                         │
│              │  11 PM: Final  │                                         │
│              │                │                                         │
│              │  Morning:      │                                         │
│              │  CONSEQUENCES  │                                         │
│              └────────────────┘                                         │
│                                                                          │
│  Consequences of Not Planning:                                          │
│  - Morning starts in "reactive mode"                                    │
│  - Reduced daily point target (can't achieve "perfect balance")        │
│  - Planning streak broken (tracked in journal)                         │
│  - Shown history of unplanned days and their outcomes                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### BrainDumpClassification

```python
class BrainDumpCategory(Enum):
    THOUGHT = "thought"      # Store for pattern discovery
    PROJECT = "project"      # Decompose into tasks
    TASK = "task"           # Route to work/personal
    WORRY = "worry"         # Convert to actionable task
    OBSERVATION = "observation"  # Log for later
```

### ImpactScore

```python
@dataclass
class ImpactScore:
    health: float      # 0-10: Impact on physical/mental wellbeing
    stress: float      # 0-10: Reduction in anxiety/cognitive load
    financial: float   # 0-10: Money/wealth impact
    relationship: float # 0-10: Connection quality impact

    @property
    def composite(self) -> float:
        """Weighted composite score."""
        weights = {
            'health': 1.5,      # Prioritize health
            'stress': 1.2,      # High weight on stress reduction
            'financial': 1.0,
            'relationship': 1.3  # Relationships matter
        }
        total = (
            self.health * weights['health'] +
            self.stress * weights['stress'] +
            self.financial * weights['financial'] +
            self.relationship * weights['relationship']
        )
        return total / sum(weights.values())
```

### WorkPriority

```python
@dataclass
class WorkPriority:
    client_id: int
    client_name: str
    task_count: int          # Pile size
    days_since_touch: int    # Neglect score
    oldest_task_age: int     # How old is oldest task
    energy_match: float      # 0-1 match to current energy

    def score(self, mode: str) -> float:
        """Calculate priority score based on mode."""
        if mode == "biggest_pile":
            return self.task_count * 10
        elif mode == "most_ignored":
            return self.days_since_touch * 5
        elif mode == "energy_match":
            return self.energy_match * 100
        return self.task_count + self.days_since_touch
```

### PlanningRecord

```python
@dataclass
class PlanningRecord:
    date: date
    planned_at: Optional[datetime]  # When planning was done
    tasks_planned: int              # Number of tasks set
    goal_set: int                   # Daily point goal
    was_planned: bool               # Did they plan night before?
    reminder_count: int             # How many reminders sent

    # Outcome tracking (filled next day)
    tasks_completed: int = 0
    goal_achieved: bool = False
    notes: str = ""
```

---

## Alert Integration

New alert types for the Accountability Architecture:

```python
class AlertType(Enum):
    # Existing...

    # New - Brain Dump Alerts
    BRAIN_DUMP_QUEUE_FULL = "brain_dump_queue_full"
    BRAIN_DUMP_UNPROCESSED = "brain_dump_unprocessed"

    # New - Impact Alerts
    IMPACT_HIGH_PRIORITY = "impact_high_priority"
    IMPACT_DEADLINE_RISK = "impact_deadline_risk"

    # New - Planning Alerts
    PLANNING_REMINDER = "planning_reminder"
    PLANNING_MISSED = "planning_missed"
    PLANNING_STREAK_BROKEN = "planning_streak_broken"

    # New - Work Priority Alerts
    WORK_CLIENT_NEGLECTED = "work_client_neglected"
    WORK_PILE_GROWING = "work_pile_growing"
```

---

## Processing Pipeline

### Automatic Processing Schedule

| Time | Process | Action |
|------|---------|--------|
| Every 15 min | Brain Dump Queue | Process unclassified items |
| 8 PM | Planning Check | First reminder if unplanned |
| 9 PM | Planning Escalation | Second reminder |
| 10 PM | Planning Urgent | Third reminder |
| 11 PM | Planning Final | Last chance warning |
| 7 AM | Morning Review | Report consequences if unplanned |
| Ongoing | Alert Daemon | Check all accountability alerts |

### Brain Dump Processing Steps

1. **Ingest** - Raw text enters queue via Telegram, voice, or direct input
2. **Classify** - Determine category (thought/project/task/worry)
3. **Extract** - Pull entities, deadlines, blockers, energy hints
4. **Route** - Send to appropriate handler:
   - Thoughts → Vector store for pattern discovery
   - Projects → Task decomposition engine
   - Tasks → Work/Personal categorization
   - Worries → Convert to concrete next action
5. **Score** - Apply impact scoring (personal) or work prioritization
6. **Queue** - Add to appropriate processing queue
7. **Notify** - Alert user of high-priority items

---

## Implementation Files

| File | Purpose |
|------|---------|
| `Tools/accountability/processor.py` | Brain dump processing pipeline |
| `Tools/accountability/impact_scorer.py` | Impact categorization engine |
| `Tools/accountability/work_prioritizer.py` | Work task prioritization |
| `Tools/accountability/planning_enforcer.py` | Daily planning enforcement |
| `Tools/accountability/models.py` | Data models and schemas |
| `Tools/accountability/alerts.py` | New alert checkers |

---

## Integration Points

### WorkOS MCP
- Create tasks from processed brain dumps
- Update task priorities based on scoring
- Track client touch timestamps

### Alert Daemon
- New checkers for planning enforcement
- Brain dump queue alerts
- Client neglect warnings

### Telegram Bot
- Receive brain dumps
- Send planning reminders
- Report consequences

### State Store
- Planning records table
- Impact scores table
- Processing audit trail

---

## Success Metrics

1. **Brain Dump Processing Time** - < 60 seconds from input to categorized
2. **Planning Compliance** - % of days planned the night before
3. **Planning Streak** - Consecutive days of planning
4. **Impact Coverage** - % of personal tasks with impact scores
5. **Client Balance** - Standard deviation of client attention

---

## Thanos Philosophical Alignment

This architecture embodies the core Thanos philosophy:

- **Balance** - Equal attention across the four stones
- **Inevitability** - Consequences are certain and tracked
- **Sacrifice** - Each task is a sacrifice toward the goal
- **Clarity** - Clear priorities remove decision fatigue
- **The Snap** - Daily planning as the decisive moment

*"The work must be done. Not because it is easy, but because it is inevitable."*
