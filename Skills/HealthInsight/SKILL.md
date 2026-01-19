# HealthInsight Skill

## Overview
Provides health insights and recommendations based on Oura ring data, with energy-aware gating for task suggestions.

## USE WHEN
- User asks about sleep, energy, readiness, or activity
- User mentions: "tired", "energy", "sleep", "readiness", "how am I doing"
- Morning briefing is requested
- Energy-based task routing is needed
- Daily planning requires health context
- System needs to: gate complex task routing, generate daily briefing

## Data Sources

### Oura MCP Tools
| Tool | Data Provided |
|------|---------------|
| `get_daily_sleep` | Sleep score, duration, efficiency |
| `get_daily_readiness` | Readiness score, HRV, resting HR |
| `get_daily_activity` | Activity score, steps, calories |
| `get_sleep` | Detailed sleep stages, timing |
| `get_daily_stress` | Stress levels throughout day |
| `get_daily_resilience` | Recovery and resilience metrics |
| `get_daily_spo2` | Blood oxygen levels |
| `get_daily_cardiovascular_age` | Cardiovascular health indicator |
| `get_vO2_max` | VO2 max estimates |

### Historical Patterns
- `history/learnings/health/` - Learned health patterns

## Key Metrics

### Readiness Score (Primary Gate)
- **0-39**: Low energy day - reduce workload
- **40-60**: Moderate energy - standard workload
- **61-100**: High energy - tackle challenging tasks

### Sleep Score Components
- Total sleep time
- Sleep efficiency
- REM sleep %
- Deep sleep %
- Sleep latency
- Timing consistency

### HRV (Heart Rate Variability)
- Higher = better recovery
- Trend matters more than absolute
- Personal baseline comparison

## Gating Rules

```
IF readiness_score < 40:
    MODE = "recovery"
    BLOCK = [complex_tasks, new_commitments]
    SUGGEST = [rest, light capture only]
    DAILY_GOAL = base_target * 0.75

IF readiness_score 40-60:
    MODE = "maintenance"
    ALLOW = [routine_tasks, review]
    SUGGEST = [defer complex work]
    DAILY_GOAL = base_target

IF readiness_score > 60:
    MODE = "productive"
    ALLOW = [all_tasks]
    PRIORITIZE = [complex, creative work]
    DAILY_GOAL = base_target * 1.15
```

## Workflows
- [DailyBriefing](workflows/DailyBriefing.md) - Morning health summary

## Tools
- `tools/oura_bridge.py` - Oura MCP wrapper

## Integration Points

### WorkOS MCP
- `workos_get_energy_aware_tasks` - Energy-filtered task list
- `workos_adjust_daily_goal` - Dynamic goal adjustment
- `workos_log_energy` - Store energy state

### Orchestrator Skill
- Provides readiness context for daily planning
- Gates task suggestions based on energy

## Response Templates

### Low Energy Day (Readiness < 40)
```
Your readiness is at {score} today - your body is asking for recovery.

Sleep: {sleep_score} ({sleep_hours}h {sleep_mins}m)
HRV: {hrv} (baseline: {hrv_baseline})

Recommendation: Light day. Focus on:
- Administrative tasks
- Low-stakes meetings
- Recovery activities

Consider rescheduling any deep work or challenging tasks.
```

### Moderate Energy Day (Readiness 40-60)
```
Readiness: {score} - Moderate energy today.

Sleep: {sleep_score} ({sleep_hours}h {sleep_mins}m)
Recovery: {recovery_status}

Pace yourself. Good for:
- Routine work
- Collaborative tasks
- Medium-complexity items

Save high-cognitive tasks for a better day if possible.
```

### High Energy Day (Readiness > 60)
```
Readiness: {score} - You're charged up today!

Sleep: {sleep_score} ({sleep_hours}h {sleep_mins}m)
HRV: {hrv} ({hrv_trend})

Great day for:
- Deep work and complex problems
- Important decisions
- Creative projects
- Challenging conversations

Your adjusted goal: {adjusted_target} points (base: {base_target})
```

## Examples

### Sleep Query
```
User: "How did I sleep?"

Response:
You slept 7h 23m with a sleep score of 82.

Breakdown:
- Deep sleep: 1h 45m (good)
- REM: 1h 52m (optimal)
- Efficiency: 91%
- Bedtime: 10:45 PM (consistent with your pattern)

This contributed to your readiness score of 78 - solid energy for today.
```

### Energy Check
```
User: "Do I have energy for deep work today?"

Response:
Your readiness is 72 - yes, you're in good shape for deep work.

Supporting factors:
- Sleep score: 79
- HRV: 45ms (above your baseline of 38ms)
- Recovery: Complete

I'd suggest tackling your most challenging task in the next few hours while your energy is peak.
```
