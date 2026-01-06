# /pa:schedule - Calendar Management Command

Smart calendar management with conflict detection and optimal scheduling.

## Usage
```
/pa:schedule [action] [options]
```

## Actions

### view (default)
Display schedule overview.
```
/pa:schedule view --range today
/pa:schedule view --range week
```

### add
Create calendar events with smart suggestions.
```
/pa:schedule add "Meeting with Epic team" --duration 1h --attendees "team@epic.com"
```

### find
Find optimal meeting times.
```
/pa:schedule find --duration 30m --timeframe "this week" --preference "morning"
```

### prep
Generate meeting preparation materials.
```
/pa:schedule prep --meeting "1pm sync"
```

### reschedule
Suggest optimal times for rescheduling.
```
/pa:schedule reschedule --meeting "standup"
```

## Smart Features

### Conflict Detection
- Identify overlapping events
- Flag double-bookings
- Warn about back-to-back meetings without breaks

### Energy-Aware Scheduling
- Suggest deep work blocks in high-energy periods
- Schedule routine tasks in low-energy windows
- Protect focus time from meetings

### Travel Time
- Account for commute between locations
- Add buffer for virtual meeting transitions

### Meeting Prep Time
- Auto-suggest prep blocks before important meetings
- Generate prep checklists based on meeting type

## Output Format - View
```markdown
## Schedule - [Date/Range]

### [Time Block]
**[Event Name]**
- Duration: [X mins/hours]
- Location: [Virtual/Physical]
- Attendees: [List]
- Prep needed: [Yes/No - details]

### Available Slots
- [Time]: [Duration] - [Suggested use]

### Alerts
- [Conflicts or concerns]
```

## Output Format - Find
```markdown
## Available Times for [Duration] Meeting

### Best Options (Energy-optimized)
1. [Day, Time] - [Reason: after focus block]
2. [Day, Time] - [Reason: minimal context switch]

### Acceptable Options
- [Additional times]

### Avoid
- [Times with conflicts or concerns]
```

## Flags
- `--range [today|tomorrow|week|month]`: Time range
- `--type [focus|meeting|break]`: Event type
- `--duration [Xm|Xh]`: Event length
- `--priority [low|medium|high]`: Event importance
- `--recurring [daily|weekly|monthly]`: Recurrence pattern
