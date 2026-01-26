# Energy-Aware Routing Workflow

## Purpose
**Strictly filter** and prioritize tasks based on current energy level, ensuring cognitive load matches available capacity. This is a **hard gate** - tasks that exceed your current energy capacity are filtered out entirely, not just deprioritized.

## Trigger Conditions
- User asks "What should I work on?"
- Task list requested
- New task needs to be slotted into schedule
- Energy level changes (override or new Oura data)

## Energy-Task Matching Matrix

| Energy Level | Cognitive Load | Drain Type | Recommended |
|--------------|----------------|------------|-------------|
| **Low** | low only | admin, shallow | Yes |
| **Low** | medium | shallow | No |
| **Low** | high | deep | No |
| **Moderate** | low | admin, shallow | Yes |
| **Moderate** | medium | admin, shallow | Yes |
| **Moderate** | high | any | No |
| **High** | any | any | Yes |

## Algorithm

```python
def route_next_task(query: str) -> Task:
    # 1. Get current state
    readiness = HealthInsight.get_readiness()
    current_time = now()

    # 2. Determine complexity budget (STRICT FILTERING)
    if readiness < 60:
        max_complexity = "low"
        max_duration = 30  # minutes
    elif readiness <= 75:
        max_complexity = "medium"
        max_duration = 60
    else:
        max_complexity = "high"
        max_duration = 120

    # 3. Time-of-day adjustment
    if current_time.hour < 12 and readiness > 60:
        prefer = "creative"  # Morning = deep work
    elif current_time.hour < 17:
        prefer = "administrative"  # Afternoon = routine
    else:
        prefer = "light"  # Evening = wind down

    # 4. Filter and rank tasks
    candidates = TaskRouter.get_pending()
    filtered = [t for t in candidates
                if t.complexity <= max_complexity
                and t.estimated_duration <= max_duration]

    ranked = sort_by(filtered, [
        urgency_score,
        preference_match(prefer),
        client_priority
    ])

    return ranked[0] if ranked else None
```

## MCP Tool Integration

The `workos_get_tasks` MCP tool now supports automatic energy-based filtering:

```typescript
// Basic usage - filtering enabled
const result = await workos_get_tasks({
    status: "active",
    applyEnergyFilter: true
});

// Returns:
{
    tasks: [...],  // Only energy-appropriate tasks
    filterMetadata: {
        applied: true,
        readinessScore: 65,
        energyLevel: "moderate",
        totalCount: 15,
        filteredCount: 12,  // Tasks after filtering
        excludedCount: 3,   // Tasks filtered out
        explanation: "Readiness 65/100: Filtered out 3 high cognitive tasks..."
    }
}
```

### Readiness Thresholds (v2.0)

| Readiness Score | Energy Level | Allowed Cognitive Load |
|-----------------|--------------|------------------------|
| < 60 | low | low only |
| 60-75 | moderate | low, medium |
| > 75 | high | low, medium, high |

**Note:** Thresholds updated in spec 046 from previous values (<40, <60, etc.).

## Execution Steps

### Step 1: Determine Current Energy
```python
async def get_current_energy():
    # Check for recent manual override
    recent_energy = await workos_get_energy(limit=1)

    if recent_energy and is_recent(recent_energy[0], hours=4):
        return recent_energy[0].level

    # Otherwise, fetch from Oura
    readiness = await get_daily_readiness(
        startDate=today(),
        endDate=today()
    )

    if readiness:
        return energy_level_from_readiness(readiness.score)

    # Fallback: ask user
    return await prompt_user_energy()

def energy_level_from_readiness(score):
    """
    Map Oura readiness score to energy level.
    Updated thresholds as of v2.0 (spec 046):
    - < 60: low (recovery mode)
    - 60-75: moderate (standard capacity)
    - > 75: high (full power)
    """
    if score < 60:
        return "low"
    elif score <= 75:
        return "moderate"
    else:
        return "high"
```

### Step 2: Fetch and Filter Tasks
```python
async def get_filtered_tasks(energy_level):
    # OPTION 1: Use MCP tool with built-in filtering (RECOMMENDED)
    result = await workos_get_tasks(
        status="active",
        applyEnergyFilter=True  # Uses current Oura readiness automatically
    )

    # Result includes filterMetadata with explanation
    filtered_tasks = result.tasks
    filter_info = result.filterMetadata

    # OPTION 2: Manual filtering for custom logic
    all_tasks = await workos_get_tasks(status="active")
    queued_tasks = await workos_get_tasks(status="queued")

    combined = all_tasks + queued_tasks

    # Apply energy filter (strict)
    filtered = filter_by_energy(combined, energy_level)

    # Sort by priority
    prioritized = prioritize_tasks(filtered, energy_level)

    return prioritized

def filter_by_energy(tasks, energy_level):
    """
    STRICT filtering based on energy level.
    Tasks that don't match are EXCLUDED, not just deprioritized.
    """
    filters = {
        "low": {
            "cognitive_load": ["low"],
            "drain_type": ["admin", "shallow"]
        },
        "moderate": {
            "cognitive_load": ["low", "medium"],
            "drain_type": ["admin", "shallow"]
        },
        "high": {
            "cognitive_load": ["low", "medium", "high"],
            "drain_type": ["admin", "shallow", "deep"]
        }
    }

    allowed = filters[energy_level]

    allowed_tasks = []
    filtered_out_tasks = []

    for task in tasks:
        # Default to "medium" if cognitive_load not set
        cognitive_load = task.cognitive_load or "medium"
        drain_type = task.drain_type or "shallow"

        if (cognitive_load in allowed["cognitive_load"] and
            drain_type in allowed["drain_type"]):
            allowed_tasks.append(task)
        else:
            filtered_out_tasks.append(task)

    return {
        "allowed": allowed_tasks,
        "filtered_out": filtered_out_tasks,
        "explanation": generate_filter_explanation(
            energy_level,
            len(allowed_tasks),
            len(filtered_out_tasks)
        )
    }

def generate_filter_explanation(energy_level, allowed_count, filtered_count):
    """
    Generate human-readable explanation of why tasks were filtered.
    """
    if filtered_count == 0:
        return f"All {allowed_count} tasks match your {energy_level} energy level."

    explanations = {
        "low": f"Filtered out {filtered_count} medium/high cognitive tasks to protect your energy. Showing {allowed_count} low-cognitive tasks only.",
        "moderate": f"Filtered out {filtered_count} high cognitive tasks. Showing {allowed_count} low/medium cognitive tasks.",
        "high": f"Full energy: All {allowed_count} tasks available (no filtering applied)."
    }

    return explanations.get(energy_level, f"{allowed_count} tasks available.")
```

### Step 3: Prioritization
```python
def prioritize_tasks(tasks, energy_level):
    """
    Priority scoring:
    1. Client touch bonus (haven't touched today)
    2. Value tier (milestone > deliverable > progress > checkbox)
    3. Energy match (optimal cognitive load for current energy)
    4. Age (older tasks get slight priority)
    """

    today_clients = get_clients_touched_today()

    for task in tasks:
        score = 0

        # Client touch bonus (+10 if client not touched today)
        if task.client_id and task.client_id not in today_clients:
            score += 10

        # Value tier scoring
        value_scores = {
            "milestone": 8,
            "deliverable": 6,
            "progress": 4,
            "checkbox": 2
        }
        score += value_scores.get(task.value_tier, 2)

        # Energy match bonus
        # On high energy, prioritize high cognitive tasks
        if energy_level == "high" and task.cognitive_load == "high":
            score += 5
        # On low energy, prioritize easiest tasks
        elif energy_level == "low" and task.cognitive_load == "low":
            score += 5

        # Age factor (up to +3 for tasks older than 3 days)
        age_days = (today() - task.created_at).days
        score += min(age_days, 3)

        task.priority_score = score

    return sorted(tasks, key=lambda t: t.priority_score, reverse=True)
```

### Step 4: Generate Recommendations
```python
def generate_recommendations(filtered_tasks, energy_level, limit=5):
    if not filtered_tasks:
        return {
            "type": "no_tasks",
            "message": f"No {energy_level}-appropriate tasks available.",
            "suggestions": [
                "Pull tasks from backlog",
                "Override energy level",
                "Create new task"
            ]
        }

    top_tasks = filtered_tasks[:limit]

    return {
        "type": "task_list",
        "energy_level": energy_level,
        "primary_recommendation": top_tasks[0],
        "alternatives": top_tasks[1:],
        "hidden_count": len(filtered_tasks) - limit,
        "skipped_reason": get_skip_reason(energy_level)
    }

def get_skip_reason(energy_level):
    if energy_level == "low":
        return "Hiding medium/high cognitive tasks due to low energy"
    elif energy_level == "moderate":
        return "Hiding high cognitive tasks to preserve energy"
    else:
        return None
```

## Response Templates

### Has Task
```
Given your energy ({readiness}/100) and it being {time_of_day},
I'd suggest: **{task.title}**

{task.context}

This should take about {task.duration} minutes.
Want to start, or see other options?
```

### Task Recommendations
```markdown
## What to Work On

**Energy: {energy_level}** {energy_emoji}

### Recommended
**{primary_task.title}**
- Client: {primary_task.client_name}
- Points: {primary_task.points} ({primary_task.value_tier})
- Why: {recommendation_reason}

### Alternatives
1. {task.title} ({task.points} pts)
2. {task.title} ({task.points} pts)
3. {task.title} ({task.points} pts)

*{hidden_count} tasks hidden - {skip_reason}*

### Quick Actions
- Start "{primary_task.title}"
- See hidden tasks
- Change energy level
```

### No Suitable Task
```
Your energy is at {readiness}/100 - {mode} mode.
{mode_specific_message}

Nothing urgent matches your current state.
Options:
- Rest and check back later
- Do some light capture/journaling
- Review what's coming up this week
```

### No Appropriate Tasks
```markdown
## No Tasks Match Your Energy

Your energy is **{energy_level}** but there are no appropriate tasks.

### Options
1. **Pull from backlog** - Review and promote tasks
2. **Override energy** - If you're feeling better than metrics suggest
3. **Create quick task** - Capture something small

### Hidden Tasks
You have {hidden_count} tasks that don't match your current energy:
- {task.title} (cognitive: {task.cognitive_load})
- {task.title} (cognitive: {task.cognitive_load})
- {task.title} (cognitive: {task.cognitive_load})

Want to see them anyway?
```

## Energy Override Flow

```python
async def handle_energy_override(new_level, reason):
    """
    User wants to override detected energy level
    """

    # Log the override
    await workos_override_energy_suggestion(
        energyLevel=new_level,
        reason=reason,
        adjustDailyGoal=True
    )

    # Recalculate tasks with new energy
    new_tasks = await get_filtered_tasks(new_level)

    return {
        "acknowledged": True,
        "new_energy": new_level,
        "updated_goal": await workos_adjust_daily_goal(),
        "new_recommendations": generate_recommendations(new_tasks, new_level)
    }
```

If user says "I feel fine" or "I can handle it":
```
-> Note the override in history/decisions/
-> Allow higher complexity this once
-> Set reminder to check in after 1 hour
-> Learn from outcome for future calibration
```

## Example Scenarios

### High Energy Request
```
User: "What should I work on?"

Energy Detection:
- Oura readiness: 82
- Level: high (> 75)

MCP Call:
workos_get_tasks(status="active", applyEnergyFilter=true)

Filter Result:
- Allowed: 12 tasks (all cognitive levels)
- Filtered out: 0 tasks
- Explanation: "Readiness 82/100: Full energy - all 12 tasks available (no filtering applied)."

Response:
## What to Work On

**Energy: High** (Readiness: 82/100) ⚡

🔥 **Full Power Mode**
All cognitive levels available. Perfect time for deep work.

### Recommended
**Memphis API architecture review**
- Client: Memphis (not touched today)
- Points: 6 (deliverable)
- Cognitive: High
- Why: High-value deep work, optimal for your energy, client needs attention

### Alternatives
1. Orlando dashboard fix (4 pts, medium)
2. Raleigh proposal draft (6 pts, high)
3. Auth module deep dive (4 pts, high)
4. Code review backlog (2 pts, low)

Showing all 12 tasks - no energy filtering applied.

### Quick Actions
- Start "Memphis API architecture review"
- See all 12 tasks
```

### Low Energy Request
```
User: "What should I work on?"

Energy Detection:
- Oura readiness: 52
- Level: low (< 60)

MCP Call:
workos_get_tasks(status="active", applyEnergyFilter=true)

Filter Result:
- Allowed: 4 tasks (low cognitive only)
- Filtered out: 8 tasks (medium/high cognitive)
- Explanation: "Readiness 52/100: Filtered out 8 medium/high cognitive tasks to protect your energy. Showing 4 low-cognitive tasks only."

Response:
## What to Work On

**Energy: Low** (Readiness: 52/100)

⚠️ **Recovery Mode Active**
Filtered out 8 medium/high cognitive tasks to protect your energy.

### Recommended
**Email follow-ups**
- Points: 2 (checkbox)
- Why: Low cognitive load, good for recovery day

### Alternatives
1. Update time tracking (2 pts)
2. File organization (2 pts)
3. Slack catch-up (2 pts)

*Showing 4 low-cognitive tasks. 8 tasks hidden until energy improves.*

### Quick Actions
- Start "Email follow-ups"
- See hidden tasks (override required)
- Log energy override if you're feeling better
```

### Override Request
```
User: "I'm actually feeling pretty good despite the low readiness"

Response:
Energy override noted. Adjusting recommendations...

**New Energy: Moderate**
**Updated Goal: 18 points** (restored from 13)

Now showing medium cognitive tasks too:

### Recommended
**Client sync prep** (4 pts, medium cognitive)

Want me to show high cognitive tasks as well?
```

## When to Apply Energy Filtering

### Always Use Filtering (Default)
- User asks "What should I work on?"
- Morning briefing / daily planning
- After completing a task (suggesting next task)
- When user seems overwhelmed or mentions low energy

### Show All Tasks (Override)
- User explicitly requests to see all tasks
- User mentions feeling better than metrics suggest
- Planning/review sessions (not execution)
- User says "show me everything" or "I can handle it"

### MCP Call Patterns

```python
# Standard task suggestion (USE FILTERING)
tasks = await workos_get_tasks(status="active", applyEnergyFilter=True)

# User override or planning session (NO FILTERING)
all_tasks = await workos_get_tasks(status="active", applyEnergyFilter=False)

# Check what was filtered
if tasks.filterMetadata.excludedCount > 0:
    print(f"Note: {tasks.filterMetadata.explanation}")
    print("Say 'show hidden tasks' to see what was filtered out.")
```

## Filter Explanation Examples

The system generates contextual explanations for why tasks were filtered:

**Low Energy (< 60):**
> "Readiness 52/100: Filtered out 8 medium/high cognitive tasks to protect your energy. Showing 4 low-cognitive tasks only."

**Moderate Energy (60-75):**
> "Readiness 68/100: Filtered out 3 high cognitive tasks. Showing 9 low/medium cognitive tasks."

**High Energy (> 75):**
> "Readiness 82/100: Full energy - all 12 tasks available (no filtering applied)."

**Detailed Breakdown (when multiple categories filtered):**
> "Readiness 55/100: Filtering to low-cognitive tasks only.
> - Excluded: 5 high cognitive tasks, 3 medium cognitive tasks
> - Available: 4 low cognitive tasks"
