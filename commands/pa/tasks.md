# /pa:tasks - Task Management Command

Intelligent task management with prioritization, context switching, and progress tracking.

## Usage
```
/pa:tasks [action] [options]
```

## Actions

### list (default)
Display tasks with smart filtering.
```
/pa:tasks list --status active
/pa:tasks list --project "Epic Implementation"
```

### focus
Get the next best task to work on.
```
/pa:tasks focus --energy high
/pa:tasks focus --duration 30m
```

### add
Create tasks with intelligent categorization.
```
/pa:tasks add "Review orderset specifications" --project epic --priority high
```

### complete
Mark task done with optional notes.
```
/pa:tasks complete "task-id" --notes "Completed with modifications"
```

### review
Weekly/daily task review and cleanup.
```
/pa:tasks review --type weekly
```

### blocked
Surface and manage blocked tasks.
```
/pa:tasks blocked --suggest-unblock
```

## Prioritization Framework

### Eisenhower Matrix
- **Do First**: Urgent + Important
- **Schedule**: Important, Not Urgent
- **Delegate**: Urgent, Not Important
- **Eliminate**: Neither

### Energy Matching
- **High Energy Tasks**: Complex problem solving, creative work, important meetings
- **Medium Energy Tasks**: Routine decisions, communication, planning
- **Low Energy Tasks**: Administrative, simple follow-ups, reading

### Context Batching
- Group similar tasks to reduce context switching
- Batch by: tool, location, energy level, project

## Output Format - List
```markdown
## Tasks - [Filter Applied]

### Do Now (Urgent + Important)
- [ ] [Task] | [Project] | Due: [Date] | Est: [Time]

### Schedule (Important)
- [ ] [Task] | [Project] | Due: [Date] | Est: [Time]

### Quick Wins (< 5 min)
- [ ] [Task] - [Context]

### Blocked
- [ ] [Task] - Blocked by: [Reason]

### Stats
- Active: [X] | Completed today: [Y] | Overdue: [Z]
```

## Output Format - Focus
```markdown
## Next Task Recommendation

**Task:** [Task name]
**Project:** [Project]
**Why now:**
- [Energy match reason]
- [Context efficiency reason]
- [Deadline proximity reason]

**Estimated time:** [X minutes]
**What you need:** [Resources/context]

**After this:** [Suggested next task]
```

## Integration Points
- ClickUp API
- Notion databases
- Calendar for deadline context
- Email for task-related communications

## Flags
- `--status [active|completed|blocked|all]`: Filter by status
- `--project [name]`: Filter by project
- `--priority [p1|p2|p3|p4]`: Filter by priority
- `--energy [high|medium|low]`: Match to current energy
- `--duration [Xm]`: Tasks fitting time window
- `--context [calls|computer|errands]`: Context-based filtering
- `--epic`: Only Epic consulting tasks
