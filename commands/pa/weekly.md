# /pa:weekly - Weekly Review Command

Comprehensive weekly review for reflection, planning, and continuous improvement.

## Usage
```
/pa:weekly [phase]
```

## Phases

### review (default)
Full weekly review workflow.

### reflect
Just the reflection phase.

### plan
Just the planning phase.

### metrics
Weekly metrics summary only.

## Weekly Review Workflow

### 1. Clear the Decks (5 min)
- Process inbox to zero
- Review and close completed tasks
- Update task statuses
- Archive or defer stale items

### 2. Review Calendar (5 min)
- Review past week's meetings
- Note key decisions and outcomes
- Check upcoming week's schedule
- Identify prep needs

### 3. Reflect on Progress (10 min)
- What got done?
- What didn't get done? Why?
- What went well?
- What could be improved?
- Key learnings?

### 4. Review Projects (10 min)
- Check each active project status
- Update project notes
- Identify blocked items
- Note next actions per project

### 5. Review Goals (5 min)
- Progress toward monthly/quarterly goals
- Adjust priorities if needed
- Celebrate wins

### 6. Plan Next Week (10 min)
- Identify top 3 priorities
- Schedule focus time
- Plan key meetings
- Set weekly intention

### 7. Capture & Organize (5 min)
- Process any loose notes
- Update reference materials
- Archive completed projects

## Output Format
```markdown
## Weekly Review - Week of [Date]

### Accomplishments
- [Major win 1]
- [Major win 2]
- [Other completions]

### Incomplete Items
| Task | Reason | Next Step |
|------|--------|-----------|
| [Task] | [Why] | [Action] |

### Metrics
- Tasks completed: [X]
- Meetings attended: [Y]
- Focus hours: [Z]
- Email processed: [N]

### Project Status
| Project | Status | Next Action |
|---------|--------|-------------|
| [Name] | [On track/Behind/Ahead] | [Action] |

### Reflections
**Went well:** [Observation]
**Improve:** [Observation]
**Learning:** [Insight]

### Next Week Priorities
1. [Priority 1] - [Why important]
2. [Priority 2] - [Why important]
3. [Priority 3] - [Why important]

### Weekly Intention
[Theme or focus for the week]
```

## Integration Points
- Pull task completion data
- Calendar analysis
- Email volume metrics
- Project status updates

## Flags
- `--quick`: Abbreviated 15-min review
- `--deep`: Extended 60-min deep review
- `--export [notion|markdown]`: Export format
- `--metrics-only`: Just the numbers
