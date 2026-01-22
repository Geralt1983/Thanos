# /pa:daily - Morning Briefing Skill

## Overview

The `/pa:daily` skill generates a comprehensive morning briefing combining:
- Oura Ring readiness/energy data
- WorkOS tasks and habits
- Energy-matched task recommendations
- Thanos-themed output formatting

## Usage

```bash
/pa:daily           # Full morning briefing
/pa:daily epic      # Focus on Epic consulting work
/pa:daily --quick   # Abbreviated version
```

## What It Does

### Step 1: Get Readiness Data

Fetches Oura Ring data for current day:
- Readiness score (0-100)
- Sleep score
- HRV balance
- Energy level classification (high/medium/low)

### Step 2: Get WorkOS Summary

Retrieves comprehensive daily summary:
- Points earned vs target
- Active tasks with clients
- Streak information
- Energy-aware recommendations

### Step 3: Get Active Tasks

Lists today's active tasks with:
- Client association
- Value tier (checkbox/progress/deliverable/milestone)
- Point values

### Step 4: Check Morning Habits

Shows habits due for morning check-in:
- Current streak
- Completion status
- Habit category

### Step 5: Energy-Matched Recommendations

Based on readiness score, suggests tasks that match current energy:
- High energy → Complex/deep work tasks
- Medium energy → Standard work tasks
- Low energy → Admin/simple tasks

## Output Format

```markdown
### DESTINY // [TIME]
[Time of day message]

## Readiness: [SCORE]/100
[Energy level and recommendation]

## Today's Sacrifices (Active Tasks)
| Client | Task | Value |
|--------|------|-------|
| ... | ... | ... |

## Morning Rituals
| Habit | Status |
|-------|--------|
| ... | ... |

## Energy-Matched Recommendations
1. [Task] ([Client]) - [Match %]
2. ...

## The Path Forward
[Single focus recommendation]
```

## Integration Points

### Oura Ring MCP

```javascript
mcp__oura__get_daily_readiness({
  startDate: "2026-01-20",
  endDate: "2026-01-20"
})
```

### WorkOS MCP

```javascript
// Daily summary
mcp__workos__workos_daily_summary()

// Active tasks
mcp__workos__workos_get_tasks({ status: 'active' })

// Habits
mcp__workos__workos_habit_checkin({ timeOfDay: 'morning' })

// Energy-aware tasks
mcp__workos__workos_get_energy_aware_tasks()
```

## Skill File Location

```
.claude/commands/pa/daily.md
```

## Related Commands

| Command | Purpose |
|---------|---------|
| `/pa:weekly` | Weekly review and planning |
| `/pa:tasks` | Task management |
| `/pa:process` | Brain dump processing |
| `/pa:schedule` | Calendar management |

## Customization

Edit `.claude/commands/pa/daily.md` to modify:
- Output format
- Data sources
- Energy thresholds
- Thanos personality elements

## Troubleshooting

### No Oura data?

- Check Oura MCP server is running
- Verify API token is configured
- Data may not be synced yet (check Oura app)

### No tasks showing?

- Verify WorkOS MCP is running
- Check if tasks exist with `active` status
- Run `workos_get_tasks` manually to debug

### Skill not found?

- Restart Claude Code session
- Verify file exists at `.claude/commands/pa/daily.md`
- Check file has correct markdown format
