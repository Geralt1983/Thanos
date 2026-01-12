---
allowed-tools: [Read, Bash, Glob, TodoWrite, Task]
description: "Manage calendar events, sync data, and check availability"
---

# /sc:calendar - Calendar Management

## Purpose
Manage calendar events, sync calendar data from Google Calendar, view schedules, and check availability for meetings and focus time.

## Usage
```
/sc:calendar [action] [--today|--week|--month] [--sync] [--format text|json]
```

## Arguments
- `action` - Calendar action to perform (view, sync, find, available)
  - `view` - View calendar events (default)
  - `sync` - Sync calendar data from Google Calendar
  - `find` - Find available time slots
  - `available` - Check availability for specific time
- `--today` - Focus on today's events (default)
- `--week` - Show week view
- `--month` - Show month view
- `--sync` - Force sync calendar data before viewing
- `--format` - Output format (text, json)
- `--timezone` - Specify timezone (default: America/New_York)

## Execution
1. Parse calendar action and time scope
2. Sync calendar data if requested or stale
3. Load calendar events from State/calendar_today.json or State/calendar_week.json
4. Process and format calendar information
5. Present calendar view or availability information

## Claude Code Integration
- Uses Bash to execute Tools/calendar_sync.py for data synchronization
- Leverages Read to access synced calendar data from State/ directory
- Applies Glob for discovering calendar-related configuration files
- Uses Task tool for complex multi-step calendar operations
- Maintains structured calendar data in JSON format

## Examples
```
/sc:calendar view --today
/sc:calendar sync --week
/sc:calendar find --duration 2h
/sc:calendar available --time 2pm
```

## Data Sources
- **State/calendar_today.json** - Today's synced calendar events
- **State/calendar_week.json** - This week's synced calendar events
- **GoogleCalendarAdapter** - Primary calendar data provider via Tools/adapters/google_calendar.py

## Related Commands
- `/pa:daily` - Daily briefing with calendar integration
- `/pa:schedule` - Schedule management and time blocking
