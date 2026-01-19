# Orchestrator Skill

## Overview
Coordinates daily planning and task management by integrating health data with work priorities. Acts as the central hub for morning routines and energy-aware scheduling.

## USE WHEN
- User mentions: "plan", "prioritize", "what should I", "today", "this week"
- User requests morning briefing or daily planning
- Start of work day (automatic trigger option)
- User asks "What should I work on?"
- Energy-based task prioritization needed
- Session starts (via hook)

## Dependencies

### Required Skills
- **HealthInsight** - Provides readiness and energy context
- **TaskRouter** - Handles task classification and routing
- **Finance** - For relevant alerts (future)

### Required MCP Tools
- Oura MCP (via HealthInsight)
- WorkOS MCP (task management)

## Orchestration Flow

```
+-------------------------------------------------------------+
|                    MORNING START                            |
+-------------------------------------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|  1. HEALTH CHECK (HealthInsight)                            |
|     - Fetch Oura data                                       |
|     - Calculate readiness score                             |
|     - Determine energy state (low/moderate/high)            |
+-------------------------------------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|  2. GOAL ADJUSTMENT                                         |
|     - Adjust daily point target based on energy             |
|     - Set cognitive load filters                            |
|     - Configure task visibility                             |
+-------------------------------------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|  3. TASK ASSEMBLY                                           |
|     - Fetch active tasks from WorkOS                        |
|     - Apply energy-based filtering                          |
|     - Prioritize by client touch and value                  |
+-------------------------------------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|  4. DAILY BRIEF GENERATION                                  |
|     - Combine health + tasks into briefing                  |
|     - Include streak and progress info                      |
|     - Provide actionable recommendations                    |
+-------------------------------------------------------------+
```

## Workflows
- [MorningStart](workflows/MorningStart.md) - Complete morning briefing
- [EnergyAwareRouting](workflows/EnergyAwareRouting.md) - Task filtering by energy
- `workflows/WeeklyReview.md` - Pattern analysis and planning (future)

## Tools
- `tools/state_manager.py` - Read/write current_state.md

## Morning Briefing Structure
1. Readiness score and energy recommendation
2. High-priority pending tasks (max 3)
3. Calendar conflicts or deadlines
4. Financial alerts (if any)
5. Suggested focus for the day

## Decision Framework
When asked "what should I do?":
1. Check readiness score -> Set available task complexity
2. Pull pending tasks from TaskRouter
3. Filter by energy-appropriate complexity
4. Present top 1-3 options with rationale
5. DO NOT overwhelm with full list

## Configuration

### Default Settings
```yaml
morning_brief:
  auto_trigger: false  # Set true for automatic morning activation
  trigger_time: "07:00"
  include_health: true
  include_tasks: true
  include_habits: true
  max_tasks_shown: 5

energy_routing:
  low_energy_max_tasks: 3
  moderate_energy_max_tasks: 5
  high_energy_max_tasks: null  # No limit

goal_adjustment:
  base_target: 18
  low_energy_multiplier: 0.75
  high_energy_multiplier: 1.15
```

## Integration Points

### Input Triggers
| Trigger | Source | Action |
|---------|--------|--------|
| "Morning briefing" | User | Full MorningStart workflow |
| "What should I work on?" | User | EnergyAwareRouting workflow |
| Schedule (07:00) | System | Auto MorningStart (if enabled) |
| Energy query | HealthInsight | Provide task context |

### Output Consumers
| Consumer | Data Provided |
|----------|---------------|
| User | Formatted briefing |
| WorkOS | Updated energy state, goal adjustment |
| TaskRouter | Energy context for new task routing |

## State Management

### Session State
```python
orchestrator_state = {
    "morning_brief_completed": False,
    "current_energy_level": None,  # low/moderate/high
    "adjusted_daily_goal": None,
    "tasks_suggested": [],
    "last_health_check": None
}
```

### Persistence
- Energy state logged to WorkOS
- Daily goal adjustment persisted
- Briefing completion tracked

## Response Formats

### Full Morning Briefing
```
Good morning! Here's your daily briefing:

## Health & Energy
{HealthInsight.DailyBriefing output}

## Today's Focus
{Energy-filtered task list}

## Progress
- Streak: {streak_days} days
- Yesterday: {yesterday_points}/{yesterday_goal} points
- Today's goal: {adjusted_goal} points

## Quick Actions
- [Start first task]
- [Log energy override]
- [View all tasks]
```

### Quick Task Suggestion
```
Based on your {energy_level} energy today:

Suggested next task:
{top_task_title}
- Client: {client_name}
- Value: {value_tier}
- Est. cognitive load: {cognitive_load}

{3-4 alternative tasks if available}
```

## Error Handling

### Missing Oura Data
```python
if not oura_data_available:
    return {
        "fallback": "manual_energy_prompt",
        "message": "Couldn't fetch Oura data. How's your energy today?",
        "options": ["low", "moderate", "high"]
    }
```

### No Active Tasks
```python
if not active_tasks:
    return {
        "message": "No active tasks. Would you like to:",
        "options": [
            "Pull from queued tasks",
            "Review backlog",
            "Create new task"
        ]
    }
```

## Mode-Specific Behavior

### Recovery Mode (readiness < 50)
- Show only 1 task max
- Emphasize rest recommendation
- Block new task creation prompts

### Maintenance Mode (readiness 50-70)
- Show 2 tasks
- Prefer routine over complex
- Gentle pacing reminders

### Productive Mode (readiness > 70)
- Full 3 tasks
- Suggest tackling hardest first
- Enable all capabilities

## Examples

### Morning Trigger
```
User: "Good morning"

Orchestrator detects morning greeting, initiates:
1. HealthInsight.DailyBriefing
2. WorkOS task fetch with energy filter
3. Goal adjustment
4. Combined briefing output
```

### Task Request
```
User: "What should I work on?"

Orchestrator:
1. Check cached energy state (or fetch fresh)
2. Get energy-aware tasks
3. Return prioritized suggestions
```

### Mid-Day Energy Check
```
User: "I'm feeling more energetic now"

Orchestrator:
1. Log energy override via WorkOS
2. Recalculate task suggestions
3. Optionally readjust daily goal
```
