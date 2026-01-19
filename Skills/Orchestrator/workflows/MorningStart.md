# Morning Start Workflow

## Purpose
Generate a comprehensive morning briefing combining health data, task priorities, and daily planning.

## Trigger Conditions
- User says "morning", "good morning", "daily briefing"
- Scheduled trigger at configured time (if enabled)
- User asks "How should I start my day?"

## Execution Steps

### Step 1: Health Check
```python
readiness = HealthInsight.get_readiness()
mode = determine_mode(readiness)
```

### Step 2: Task Inventory
```python
tasks = TaskRouter.get_pending()
urgent = filter(tasks, deadline < 24h)
high_priority = filter(tasks, priority == "high")
```

### Step 3: Calendar Scan
```python
events = calendar.get_today()
conflicts = detect_conflicts(events, tasks)
```

### Step 4: Financial Pulse (if enabled)
```python
alerts = Finance.get_alerts()
cash_flow = Finance.get_weekly_projection()
```

### Step 5: Goal Adjustment
```python
# Adjust daily goal based on energy
goal_result = await workos_adjust_daily_goal(baseTarget=18)
adjusted_goal = goal_result.adjusted_target
```

### Step 6: Task Assembly
```python
# Get energy-filtered tasks
energy_tasks = await workos_get_energy_aware_tasks(
    energy_level=energy_state.level
)

# Get today's metrics for context
today_metrics = await workos_get_today_metrics()

# Get streak info
streak_info = await workos_get_streak()

# Get habits due this morning
morning_habits = await workos_habit_checkin(timeOfDay="morning")
```

### Step 7: Client Touch Analysis
```python
# Get clients not touched recently
clients = await workos_get_clients()
tasks_by_client = group_tasks_by_client(energy_tasks)

# Identify clients needing attention
clients_to_touch = [
    c for c in clients
    if c.id not in today_metrics.clients_touched
    and has_active_tasks(c, tasks_by_client)
]
```

### Step 8: Synthesize Briefing

```markdown
# Good Morning, Jeremy

## Energy: {readiness}/100 - {mode} Mode
{energy_recommendation}

## Top 3 Today
1. {task_1} - {context}
2. {task_2} - {context}
3. {task_3} - {context}

## Calendar
{time} - {event}
{warnings_if_any}

## Alerts
{financial_or_deadline_alerts}

## Progress
- Streak: {streak_days} days
- Today's goal: {adjusted_goal} points

## Clients to Touch Today
- {client_1}: {pending_tasks} pending tasks
- {client_2}: {pending_tasks} pending tasks

## Morning Habits
- [ ] {habit_1} (Streak: {streak})
- [ ] {habit_2} (Streak: {streak})

---
Ready when you are. What would you like to tackle first?
```

## Mode-Specific Behavior

### Recovery Mode (readiness < 50)
- Show only 1 task max
- Emphasize rest recommendation
- Block new task creation prompts
```
Warning: Low Energy Day

Your body is signaling it needs recovery. Today:
- Goal reduced to {adjusted_goal} points
- Only showing low-cognitive tasks
- Consider rescheduling important meetings

Take care of yourself - sustainable productivity matters more than one day's output.
```

### Maintenance Mode (readiness 50-70)
- Show 2 tasks
- Prefer routine over complex
- Gentle pacing reminders

### Productive Mode (readiness > 70)
- Full 3 tasks
- Suggest tackling hardest first
- Enable all capabilities

## Conditional Sections

### Streak at Risk
```
Alert: Streak Alert

You're at {streak_days} days! To keep it alive:
- Complete at least one task today
- Minimum: {min_points} points

Your easiest win: "{easiest_task.title}" ({easiest_task.points} pts)
```

### No Oura Data Fallback
```
## Energy Check

I couldn't get your Oura data this morning.

How are you feeling?
- Low energy (light day)
- Moderate (normal day)
- High energy (bring it on!)
```

## State Updates

### After Briefing Completion
```python
# Mark briefing as done
orchestrator_state.morning_brief_completed = True
orchestrator_state.current_energy_level = energy_state.level
orchestrator_state.adjusted_daily_goal = adjusted_goal
orchestrator_state.tasks_suggested = [t.id for t in energy_tasks[:5]]
orchestrator_state.last_health_check = datetime.now()

# Log to WorkOS
await workos_log_energy(
    level=energy_state.level,
    ouraReadiness=readiness_score,
    ouraSleep=sleep_summary.score,
    note="Morning briefing auto-log"
)
```

## Example Output

### High Energy Morning
```
# Good Morning, Jeremy

## Energy: 82/100 - Productive Mode
Great sleep last night (7h 45m, score 85). HRV trending up.
Your body is recovered and ready for challenges.

## Top 3 Today
1. Memphis API architecture review - High value, deep work
2. Orlando dashboard performance fix - Client follow-up needed
3. Raleigh weekly sync prep - Meeting at 2pm

## Today's Goal
21 points (boosted from 18 due to high energy)
Streak: 12 days

## Clients to Touch Today
- Memphis: 3 pending tasks
- Raleigh: 2 pending tasks

## Morning Habits
- [ ] Drink water (Streak: 8)
- [ ] Journal (Streak: 5)
- [ ] Morning stretch (Streak: 12)

---
Ready when you are. What would you like to tackle first?
```

### Low Energy Morning
```
# Good Morning, Jeremy

## Energy: 35/100 - Recovery Mode
Short sleep (5h 12m) and incomplete recovery.
Your HRV is below baseline - your body needs rest.

Warning: Low Energy Day
- Goal reduced to 13 points
- Only showing low-cognitive tasks
- Consider rescheduling important meetings

## Today's Focus (Light Tasks Only)
1. Email follow-ups (2 pts)
2. Update time tracking (2 pts)
3. File organization (2 pts)

Streak: 12 days - Complete at least one task to keep it alive!

---
Take it easy today. What feels manageable?
```
