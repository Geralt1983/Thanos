# Energy-Aware Routing Workflow

## Purpose
Filter and prioritize tasks based on current energy level, ensuring cognitive load matches available capacity.

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

    # 2. Determine complexity budget
    if readiness < 40:
        max_complexity = "low"
        max_duration = 15  # minutes
    elif readiness < 60:
        max_complexity = "medium"
        max_duration = 45
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
    if score < 40:
        return "low"
    elif score < 60:
        return "moderate"
    else:
        return "high"
```

### Step 2: Fetch and Filter Tasks
```python
async def get_filtered_tasks(energy_level):
    # Get all non-completed tasks
    all_tasks = await workos_get_tasks(status="active")
    queued_tasks = await workos_get_tasks(status="queued")

    combined = all_tasks + queued_tasks

    # Apply energy filter
    filtered = filter_by_energy(combined, energy_level)

    # Sort by priority
    prioritized = prioritize_tasks(filtered, energy_level)

    return prioritized

def filter_by_energy(tasks, energy_level):
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

    return [
        t for t in tasks
        if t.cognitive_load in allowed["cognitive_load"]
        and t.drain_type in allowed["drain_type"]
    ]
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
- Oura readiness: 78
- Level: high

Filtered Tasks: 12 tasks (all cognitive levels)

Response:
## What to Work On

**Energy: High**

### Recommended
**Memphis API architecture review**
- Client: Memphis (not touched today)
- Points: 6 (deliverable)
- Why: High-value task, optimal for your energy, client needs attention

### Alternatives
1. Orlando dashboard fix (4 pts)
2. Raleigh proposal draft (6 pts)
3. Auth module deep dive (4 pts)
4. Code review backlog (2 pts)

### Quick Actions
- Start "Memphis API architecture review"
- See all 12 tasks
```

### Low Energy Request
```
User: "What should I work on?"

Energy Detection:
- Oura readiness: 35
- Level: low

Filtered Tasks: 4 tasks (low cognitive only)
Hidden: 8 tasks

Response:
## What to Work On

**Energy: Low**

### Recommended
**Email follow-ups**
- Points: 2 (checkbox)
- Why: Low cognitive load, good for recovery day

### Alternatives
1. Update time tracking (2 pts)
2. File organization (2 pts)
3. Slack catch-up (2 pts)

*8 tasks hidden - Hiding medium/high cognitive tasks due to low energy*

### Quick Actions
- Start "Email follow-ups"
- See hidden tasks
- Override energy level
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
