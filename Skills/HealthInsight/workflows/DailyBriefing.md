# Daily Health Briefing Workflow

## Purpose
Generate a comprehensive morning health briefing based on Oura data.

## Trigger
- Morning start (typically 6-9 AM)
- User asks "How am I doing?" or "Morning briefing"
- Orchestrator skill requests health context

## Data Collection

### Step 1: Fetch Oura Data
```python
# Get today's date range
today = date.today().isoformat()
yesterday = (date.today() - timedelta(days=1)).isoformat()

# Parallel data fetches
readiness = oura_bridge.get_readiness()
sleep = oura_bridge.get_sleep()
activity = oura_bridge.get_activity()
stress = oura_bridge.get_stress()
```

### Step 2: Analyze Patterns
Compare to 7-day average:
- Is today's readiness above/below baseline?
- Sleep trend direction (improving/declining)
- Activity balance (over/under recovered)

```python
metrics = {
    "readiness": {
        "score": readiness_data.score,
        "contributors": {
            "sleep_balance": readiness_data.contributors.sleep_balance,
            "previous_day_activity": readiness_data.contributors.previous_day_activity,
            "hrv_balance": readiness_data.contributors.hrv_balance,
            "recovery_index": readiness_data.contributors.recovery_index
        }
    },
    "sleep": {
        "score": sleep_data.score,
        "total_hours": sleep_data.total_sleep_duration / 3600,
        "efficiency": sleep_data.efficiency,
        "deep_sleep_mins": sleep_data.deep_sleep_duration / 60,
        "rem_sleep_mins": sleep_data.rem_sleep_duration / 60,
        "latency_mins": sleep_data.latency / 60,
        "bedtime": sleep_data.bedtime_start,
        "wake_time": sleep_data.bedtime_end
    },
    "hrv": {
        "average": readiness_data.contributors.hrv_balance,
        "trend": calculate_hrv_trend(7)  # 7-day trend
    },
    "activity_yesterday": {
        "score": activity_data.score,
        "steps": activity_data.steps,
        "active_calories": activity_data.active_calories
    }
}
```

### Step 3: Generate Recommendation

```
IF readiness >= 70 AND sleep >= 70:
    -> "Strong start. Good day for complex work."
    -> Prioritize: deep work, difficult conversations, creative tasks

IF readiness 50-70:
    -> "Moderate energy. Pace yourself."
    -> Prioritize: routine tasks, meetings, review work
    -> Avoid: new commitments, complex decisions

IF readiness < 50:
    -> "Recovery day. Keep it light."
    -> Prioritize: administrative tasks, capture only
    -> Block: new task creation, complex routing
```

### Step 4: Update State
Write to `context/current_state.md`:
- Current readiness score
- Operating mode (recovery/maintenance/productive)
- Suggested focus areas
- Any health alerts

## Output Format

```markdown
## Morning Health Briefing

### Energy Status {emoji}
Readiness: {readiness_score}/100 - {energy_level} energy

### Sleep Summary
- Total: {sleep_hours}h {sleep_mins}m (Score: {sleep_score})
- Deep: {deep_mins}m | REM: {rem_mins}m
- Efficiency: {efficiency}%
- Bedtime: {bedtime} -> Wake: {wake_time}

### Recovery Indicators
- HRV: {hrv}ms ({hrv_trend})
- Resting HR: {resting_hr} bpm
- Recovery: {recovery_status}

### Yesterday's Activity
- Steps: {steps:,}
- Active calories: {active_cal}
- Activity score: {activity_score}

### Today's Recommendation
{energy_based_recommendation}

### Suggested Focus
{task_suggestions_based_on_energy}
```

## Conditional Sections

### If Sleep Score < 70
```
Warning: Sleep Quality Alert
Your sleep was below optimal. Consider:
- Earlier bedtime tonight
- Reducing caffeine after 2 PM
- Light tasks this morning
```

### If HRV Trending Down
```
Notice: HRV Trend Notice
Your HRV has been declining over the past 3 days.
This may indicate accumulated stress or insufficient recovery.
Consider lighter workload today.
```

### If Readiness < 40
```
Alert: Low Energy Protocol
Your body needs recovery today. Automatically:
- Adjusted daily goal: {reduced_goal} points (was {base_goal})
- Filtered to low-cognitive tasks only
- High-drain tasks hidden from suggestions
```

## Integration Actions

### Log Energy State
```python
# Store in WorkOS for task filtering
workos_log_energy(
    level=energy_state["level"],
    ouraReadiness=metrics["readiness"]["score"],
    ouraSleep=metrics["sleep"]["score"],
    ouraHrv=metrics["hrv"]["average"],
    note="Auto-logged from morning briefing"
)
```

### Adjust Daily Goal
```python
# Dynamically adjust target
workos_adjust_daily_goal(
    baseTarget=18  # Will return adjusted target
)
```

### Get Energy-Aware Tasks
```python
# Fetch filtered task list
tasks = workos_get_energy_aware_tasks(
    energy_level=energy_state["level"]
)
```

## Example Output

### High Energy Day
```
## Morning Health Briefing

### Energy Status
Readiness: 82/100 - HIGH energy

### Sleep Summary
- Total: 7h 45m (Score: 85)
- Deep: 1h 52m | REM: 2h 05m
- Efficiency: 93%
- Bedtime: 10:30 PM -> Wake: 6:15 AM

### Recovery Indicators
- HRV: 48ms (trending up)
- Resting HR: 52 bpm
- Recovery: Optimal

### Yesterday's Activity
- Steps: 8,432
- Active calories: 420
- Activity score: 78

### Today's Recommendation
Excellent recovery! This is a great day for challenging work.
Tackle your most cognitively demanding tasks this morning.
```

### Low Energy Day
```
## Morning Health Briefing

### Energy Status
Readiness: 38/100 - LOW energy

### Sleep Summary
- Total: 5h 12m (Score: 52)
- Deep: 45m | REM: 58m
- Efficiency: 71%
- Bedtime: 1:15 AM -> Wake: 6:27 AM

### Recovery Indicators
- HRV: 28ms (below baseline)
- Resting HR: 61 bpm
- Recovery: Incomplete

### Yesterday's Activity
- Steps: 12,847
- Active calories: 680
- Activity score: 92 (high)

Warning: Sleep Quality Alert
Late bedtime and short sleep duration.
Your body hasn't fully recovered.

Alert: Low Energy Protocol Active
- Daily goal adjusted: 13 points (was 18)
- Showing only low-cognitive tasks
- Deep work hidden from suggestions

### Today's Recommendation
Recovery day. Your body needs rest.
Focus on:
- Administrative tasks
- Email catch-up
- Light meetings only

Avoid: Complex decisions, deep work, difficult conversations
```
