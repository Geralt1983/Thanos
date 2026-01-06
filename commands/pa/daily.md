# /pa:daily - Morning Briefing Command

Generate a comprehensive morning briefing to start the day with clarity and focus.

## Usage
```
/pa:daily [focus]
```

## Parameters
- `focus` (optional): Specific area to emphasize (work | personal | epic | all)

## Workflow

### 1. Calendar Review
- Fetch today's calendar events
- Identify meetings, deadlines, and time blocks
- Flag conflicts or back-to-back meetings
- Highlight preparation needed for key meetings

### 2. Task Prioritization
- Review pending tasks from ClickUp/task system
- Apply Eisenhower matrix (urgent/important)
- Identify top 3 priorities for the day
- Surface any overdue items

### 3. Email Triage
- Summarize unread emails by priority
- Flag items requiring immediate response
- Identify FYI vs action-required messages
- Note any Epic-related communications

### 4. Context Loading
- Review yesterday's progress and notes
- Surface any blocked items
- Check project deadlines approaching

### 5. Daily Intention Setting
- Suggest optimal time blocking based on energy patterns
- Recommend focus periods for deep work
- Identify buffer time for reactive work

## Output Format
```markdown
## Daily Briefing - [Date]

### Today's Schedule
[Calendar summary with prep notes]

### Top Priorities
1. [Priority 1] - [context/deadline]
2. [Priority 2] - [context/deadline]
3. [Priority 3] - [context/deadline]

### Action Required
- [Urgent emails/messages]
- [Deadlines today]

### Time Blocks Suggested
- [Deep work recommendation]
- [Meeting prep windows]
- [Buffer time]

### Quick Wins
- [Low-effort high-impact tasks]
```

## Integration Points
- Google Calendar via MCP
- Gmail via MCP
- ClickUp/task system
- Previous day's notes

## Flags
- `--verbose`: Include full email previews
- `--epic`: Focus on Epic consulting work
- `--quick`: Abbreviated 2-minute version
