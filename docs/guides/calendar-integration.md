# Calendar Integration Guide

## Overview

The Calendar Integration feature brings your Google Calendar directly into your Thanos daily workflow, enabling calendar-aware task scheduling, automated daily briefings with calendar context, and seamless calendar management through slash commands.

**Key Benefits:**
- 📅 **Automatic Calendar Sync**: Your calendar data syncs automatically into daily briefings
- 🎯 **Context-Aware Scheduling**: See your availability when planning tasks
- ⚡ **Quick Access**: View and manage calendar through simple `/pa:calendar` commands
- 🤖 **LLM-Enhanced**: Claude analyzes your calendar to provide insights and recommendations

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start](#quick-start)
3. [Components](#components)
4. [Daily Workflow Integration](#daily-workflow-integration)
5. [Command Reference](#command-reference)
6. [State Files](#state-files)
7. [Calendar Sync](#calendar-sync)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Usage](#advanced-usage)

---

## Architecture Overview

The calendar integration is built on a layered architecture following the established BaseAdapter pattern:

```
┌─────────────────────────────────────────┐
│    User Commands (/pa:daily, etc.)     │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│     Daily Briefing + BriefingEngine     │
│   (Auto-syncs & includes calendar)      │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│        Calendar Sync Utility            │
│     (Tools/calendar_sync.py)            │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│      CalendarAdapter (Unified)          │
│   (Tools/adapters/calendar_adapter.py)  │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│     GoogleCalendarAdapter               │
│  (Tools/adapters/google_calendar.py)    │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│      Google Calendar API                │
└─────────────────────────────────────────┘
```

**Data Flow:**
1. Calendar events are fetched from Google Calendar via the GoogleCalendarAdapter
2. CalendarAdapter provides a unified interface (supports future providers like Apple Calendar)
3. Calendar sync utility (`calendar_sync.py`) fetches events and saves to State/ directory
4. Daily briefing automatically syncs calendar and includes events in context
5. User commands (`/pa:calendar`) provide quick access to calendar operations

---

## Quick Start

### Prerequisites

1. **Google Calendar API Setup**: Follow the [Google Calendar Integration Guide](../integrations/google-calendar.md) to:
   - Create a Google Cloud project
   - Enable Google Calendar API
   - Set up OAuth credentials
   - Configure environment variables

2. **Environment Configuration**: Ensure your `.env` file contains:
   ```bash
   GOOGLE_CALENDAR_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CALENDAR_CLIENT_SECRET=GOCSPX-YourClientSecret
   GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:8080/oauth2callback
   ```

3. **Authentication**: Complete OAuth flow (one-time):
   ```bash
   python scripts/setup_google_calendar.py
   ```

### Verify Setup

Test that everything is working:

```bash
# Sync today's calendar
python Tools/calendar_sync.py --today

# Check that State/calendar_today.json was created
ls -l State/calendar_today.json

# View calendar via command
python -m commands.pa.calendar view --today
```

If all steps succeed, you're ready to use the calendar integration!

---

## Components

### 1. GoogleCalendarAdapter
**Location:** `Tools/adapters/google_calendar.py`

The core adapter that communicates with Google Calendar API. Provides tools for:
- Fetching events for date ranges
- Getting today's events with summary
- Creating, updating, and deleting events
- Finding free time slots
- Checking availability and conflicts

**Usage:**
```python
from Tools.adapters import GoogleCalendarAdapter

adapter = GoogleCalendarAdapter()

# Get today's events
result = await adapter.call_tool("google_calendar.get_today_events", {
    "calendar_id": "primary",
    "timezone": "America/New_York"
})
```

See [Google Calendar Integration Guide](../integrations/google-calendar.md) for complete tool reference.

### 2. CalendarAdapter (Unified Wrapper)
**Location:** `Tools/adapters/calendar_adapter.py`

A unified wrapper that provides a consistent interface across calendar providers. Currently wraps GoogleCalendarAdapter, with future support planned for Apple Calendar and other providers.

**Purpose:**
- Abstraction layer for multi-provider support
- Consistent tool naming across providers
- Easy provider switching

**Usage:**
```python
from Tools.adapters import CalendarAdapter

# Uses Google Calendar by default
adapter = CalendarAdapter(provider="google")

# Future: Switch to Apple Calendar
# adapter = CalendarAdapter(provider="apple")
```

### 3. Calendar Sync Utility
**Location:** `Tools/calendar_sync.py`

A standalone script that fetches calendar events and saves them to the State/ directory for use in daily briefings and other commands.

**Features:**
- Syncs today's events to `State/calendar_today.json`
- Syncs week's events to `State/calendar_week.json`
- CLI interface with timezone support
- Proper error handling and logging

**Usage:**
```bash
# Sync today's events
python Tools/calendar_sync.py --today

# Sync this week's events
python Tools/calendar_sync.py --week

# Sync both
python Tools/calendar_sync.py --all

# Specify timezone
python Tools/calendar_sync.py --today --timezone "America/Los_Angeles"
```

### 4. Calendar Command
**Location:** `commands/pa/calendar.py`

Personal assistant command for calendar management. Provides actions for viewing, syncing, finding available time, and checking availability.

**Actions:**
- `view`: View calendar events (default)
- `sync`: Force sync from Google Calendar
- `find`: Find available time slots
- `available`: Check availability for specific time

**Usage:**
```bash
# View today's calendar
/pa:calendar view --today

# View week calendar with forced sync
/pa:calendar view --week --sync

# Find available time
/pa:calendar find 60 minutes for meeting

# Check availability
/pa:calendar available tomorrow at 2pm
```

### 5. Daily Briefing Integration
**Location:** `commands/pa/daily.py`, `Tools/briefing_engine.py`

The daily briefing command automatically syncs today's calendar and includes events in the briefing context.

**Features:**
- Auto-sync on daily briefing run
- Calendar summary in briefing output
- Events included in LLM context
- Silent background sync (no interruption)

**Flow:**
1. Daily command runs (`/pa:daily`)
2. Auto-sync triggered via `sync_calendar_quietly()`
3. BriefingEngine reads `State/calendar_today.json`
4. Calendar data included in briefing context
5. LLM generates briefing with calendar awareness

---

## Daily Workflow Integration

### Morning Briefing

When you run `/pa:daily`, the calendar integration enhances your briefing:

```bash
/pa:daily
```

**What Happens:**
1. ✅ Calendar auto-syncs today's events
2. 📅 Events are loaded into briefing context
3. 🤖 LLM analyzes your schedule
4. 📊 Briefing includes calendar summary

**Example Briefing Output:**
```markdown
# Daily Brief - Friday, January 12, 2026

## Today's Schedule
📅 5 events | 🕐 3h meeting time | 🔓 4h free time

### Upcoming Events
- **9:00 AM**: Team Standup (in 45 min)
- **11:00 AM**: Client Review
- **2:00 PM**: 1:1 with Sarah

### Focus Windows
- 10:00 AM - 11:00 AM (60 min)
- 12:00 PM - 2:00 PM (120 min)
- 3:00 PM onwards (open)

⚠️ Back-to-back meetings: 9-11 AM
```

### Throughout the Day

Quick calendar checks:

```bash
# Quick view
/pa:calendar view --today

# Check if time is available
/pa:calendar available 2pm for 30 minutes

# Find time for a task
/pa:calendar find 90 minutes for deep work
```

### End of Day

The weekly schedule command also uses calendar data:

```bash
# View tomorrow's schedule
/pa:schedule view tomorrow

# Plan next week
/pa:schedule view next-week
```

---

## Command Reference

### `/pa:calendar` Command

**Syntax:**
```bash
/pa:calendar [action] [options]
```

**Actions:**

#### `view` - View Calendar Events (Default)
```bash
# Today's calendar (default)
/pa:calendar view
/pa:calendar view --today

# Week view
/pa:calendar view --week

# Force sync before viewing
/pa:calendar view --today --sync
```

**Output:**
- Events in chronological order
- Time formatting (12-hour with AM/PM)
- Location and attendee info
- Scheduling conflicts highlighted
- Available focus time blocks

#### `sync` - Sync Calendar Data
```bash
# Sync today's events
/pa:calendar sync

# Sync week's events
/pa:calendar sync --week
```

**What It Does:**
- Fetches latest events from Google Calendar
- Updates State/calendar_today.json or State/calendar_week.json
- Shows sync summary (event count, status)
- Provides brief schedule analysis

#### `find` - Find Available Time
```bash
# Find time with details
/pa:calendar find 60 minutes for client meeting

# Find time (minimal)
/pa:calendar find 30m
```

**Analysis Includes:**
- Available time slots
- Optimal focus times (mornings preferred)
- Buffer time consideration
- 2-3 specific slot suggestions

#### `available` - Check Availability
```bash
# Check specific time
/pa:calendar available tomorrow at 2pm for 1 hour

# Check today
/pa:calendar available 3pm
```

**Analysis Includes:**
- Conflict detection
- Adjacent meeting warnings
- Quality assessment (focus time vs. fragmented)
- Alternative suggestions if needed

**Options:**
- `--today`: Focus on today (default for view/sync/available)
- `--week`: Week view (used for view/sync/find)
- `--sync`: Force sync before action

---

## State Files

Calendar data is stored in the State/ directory as JSON files.

### State/calendar_today.json

**Format:**
```json
{
  "synced_at": "2026-01-12T08:30:00-05:00",
  "date": "2026-01-12",
  "timezone": "America/New_York",
  "events": [
    {
      "id": "event_id_123",
      "summary": "Team Standup",
      "description": "Daily sync meeting",
      "start": {
        "dateTime": "2026-01-12T09:00:00-05:00",
        "timeZone": "America/New_York"
      },
      "end": {
        "dateTime": "2026-01-12T09:30:00-05:00",
        "timeZone": "America/New_York"
      },
      "location": "Zoom",
      "attendees": [
        {"email": "team@company.com"}
      ],
      "status": "confirmed"
    }
  ],
  "summary": {
    "total_events": 5,
    "meetings": 3,
    "focus_blocks": 2,
    "all_day_events": 0,
    "first_event": "09:00",
    "last_event": "17:00",
    "total_meeting_minutes": 180,
    "free_time_minutes": 300
  }
}
```

**Used By:**
- Daily briefing (`/pa:daily`)
- Calendar command (`/pa:calendar view --today`)
- Schedule command (`/pa:schedule`)

### State/calendar_week.json

**Format:**
```json
{
  "synced_at": "2026-01-12T08:30:00-05:00",
  "week_start": "2026-01-13",
  "week_end": "2026-01-19",
  "timezone": "America/New_York",
  "events": [
    {
      "id": "event_id_456",
      "summary": "Sprint Planning",
      "start": {"dateTime": "2026-01-13T10:00:00-05:00"},
      "end": {"dateTime": "2026-01-13T11:30:00-05:00"}
    }
  ],
  "event_count": 18
}
```

**Used By:**
- Calendar command (`/pa:calendar view --week`)
- Calendar command (`/pa:calendar find`)
- Schedule command (`/pa:schedule view next-week`)

**File Management:**
- Files are automatically created/updated by calendar sync
- Files are safe to delete (will be recreated on next sync)
- JSON format for easy parsing and debugging
- Timestamps in ISO 8601 format with timezone

---

## Calendar Sync

### Automatic Sync

Calendar data is automatically synced in these scenarios:

1. **Daily Briefing**: When you run `/pa:daily`, today's calendar syncs automatically
   - Runs silently in the background
   - Does not interrupt briefing flow
   - Fails gracefully if sync unavailable

2. **Manual Sync**: When you run `/pa:calendar sync`
   - Shows sync progress
   - Reports event count
   - Provides schedule summary

### Manual Sync

Run the sync utility directly:

```bash
# Sync today's events
python Tools/calendar_sync.py --today

# Sync this week's events
python Tools/calendar_sync.py --week

# Sync both today and week
python Tools/calendar_sync.py --all

# Specify timezone
python Tools/calendar_sync.py --all --timezone "America/Los_Angeles"
```

**Output:**
```
🔄 Starting calendar sync...
📅 Syncing today's calendar events...
✅ Saved 5 events to /path/to/State/calendar_today.json
📅 Syncing this week's calendar events...
✅ Saved 18 events to /path/to/State/calendar_week.json

✅ Calendar sync completed successfully
```

### Sync Frequency

**Recommendations:**
- **Daily briefing**: Syncs automatically every morning
- **Ad-hoc checks**: Use `/pa:calendar view --sync` to force refresh
- **Before scheduling**: Sync before finding available time slots

**Performance Notes:**
- Sync typically takes 2-5 seconds
- Google Calendar API has rate limits (plenty for personal use)
- State files cache data to minimize API calls
- Failed syncs don't prevent commands from running (uses cached data)

### Timezone Handling

Calendar sync respects timezones:

**Default Timezone:** `America/New_York` (configurable)

**Specify Timezone:**
```bash
python Tools/calendar_sync.py --today --timezone "America/Los_Angeles"
```

**Supported Timezones:**
- Any IANA timezone (e.g., "America/New_York", "Europe/London", "Asia/Tokyo")
- Uses Python's `zoneinfo` module
- All timestamps in State files include timezone info

---

## Troubleshooting

### Issue 1: "Calendar sync script not found"

**Cause:** Calendar sync utility is not at expected path.

**Solution:**
```bash
# Verify file exists
ls -l Tools/calendar_sync.py

# If missing, check you're in project root
pwd
```

### Issue 2: "No calendar data found. Run sync first."

**Cause:** State/calendar_today.json or State/calendar_week.json doesn't exist.

**Solution:**
```bash
# Run manual sync
python Tools/calendar_sync.py --today

# Or use sync command
/pa:calendar sync
```

### Issue 3: "Google Calendar adapter not available"

**Cause:** Google Calendar dependencies not installed.

**Solution:**
```bash
# Install required packages
pip install google-auth google-auth-oauthlib google-api-python-client

# Verify installation
python -c "from Tools.adapters import GoogleCalendarAdapter; print('✓ OK')"
```

### Issue 4: Sync timeout (>30s)

**Cause:** Network issues or API slowness.

**Solution:**
- Check internet connection
- Retry sync
- If persistent, check [Google Workspace Status](https://www.google.com/appsstatus/dashboard/)

### Issue 5: Events not showing in briefing

**Possible Causes:**
1. Calendar not synced
2. State file empty or invalid
3. BriefingEngine not reading calendar

**Debug Steps:**
```bash
# 1. Check State file exists and has content
cat State/calendar_today.json | jq '.events | length'

# 2. Run sync manually
python Tools/calendar_sync.py --today

# 3. Verify briefing engine integration
grep -r "calendar" Tools/briefing_engine.py

# 4. Check daily.py has sync integration
grep -r "sync_calendar" commands/pa/daily.py
```

### Issue 6: "Invalid JSON in calendar file"

**Cause:** Corrupted State file.

**Solution:**
```bash
# Remove corrupted file
rm State/calendar_today.json

# Re-sync
python Tools/calendar_sync.py --today

# Verify JSON is valid
cat State/calendar_today.json | jq '.'
```

### Issue 7: OAuth authentication issues

**Cause:** Expired or invalid credentials.

**Solution:**
See the [Google Calendar Integration Guide](../integrations/google-calendar.md#troubleshooting) for OAuth troubleshooting.

Quick fix:
```bash
# Remove credentials
rm State/calendar_credentials.json

# Re-authenticate
python scripts/setup_google_calendar.py
```

---

## Advanced Usage

### Custom Timezone Configuration

Set default timezone for all calendar operations:

**Option 1: Environment Variable**
```bash
# Add to .env
export CALENDAR_DEFAULT_TIMEZONE="America/Los_Angeles"
```

**Option 2: Command Line**
```bash
python Tools/calendar_sync.py --today --timezone "Europe/London"
```

### Filtering Calendar Events

Use calendar filters to focus on relevant events in briefings:

**Location:** `config/calendar_filters.json`

**Example: Work Hours Only**
```json
{
  "enabled": true,
  "time_filters": {
    "exclude_before_hour": 8,
    "exclude_after_hour": 18,
    "exclude_weekends": true
  },
  "summary_patterns": {
    "exclude": ["(?i)personal", "(?i)lunch"]
  }
}
```

See [Google Calendar Integration Guide - Calendar Filtering](../integrations/google-calendar.md#calendar-filtering) for complete filter reference.

### Programmatic Access

Use the calendar sync utility in your own scripts:

```python
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.calendar_sync import sync_today_events, sync_week_events
from Tools.adapters import get_default_manager

async def main():
    manager = await get_default_manager()

    # Sync today
    result = await sync_today_events(manager, timezone="America/New_York")

    if result["success"]:
        print(f"✅ Synced {result['event_count']} events")
        print(f"📁 Saved to {result['file']}")
    else:
        print(f"❌ Error: {result['error']}")

    await manager.close_all()

if __name__ == "__main__":
    asyncio.run(main())
```

### Integration with Task Management

Combine calendar data with task scheduling:

```python
# Pseudocode showing integration pattern
from Tools.calendar_sync import sync_today_events
from Tools.adapters import get_default_manager

async def schedule_task_intelligently(task):
    # Get calendar data
    manager = await get_default_manager()
    cal_result = await sync_today_events(manager)

    # Find free slots
    free_slots = await manager.call_tool(
        "google_calendar.find_free_slots",
        {
            "start_date": "2026-01-12",
            "duration_minutes": task["estimated_minutes"],
            "working_hours_start": 8,
            "working_hours_end": 17
        }
    )

    # Pick optimal slot (prefer mornings)
    best_slot = free_slots.data["free_slots"][0]

    # Block time on calendar
    await manager.call_tool(
        "google_calendar.create_event",
        {
            "summary": f"[Thanos] {task['title']}",
            "start_time": best_slot["start"],
            "end_time": best_slot["end"],
            "description": task["description"]
        }
    )
```

### Multi-Calendar Support

While the current implementation focuses on primary calendar, you can extend it:

```python
from Tools.adapters import GoogleCalendarAdapter

async def sync_multiple_calendars():
    adapter = GoogleCalendarAdapter()

    # List all calendars
    calendars_result = await adapter.call_tool("google_calendar.list_calendars", {})

    for cal in calendars_result.data["calendars"]:
        # Sync each calendar
        events = await adapter.call_tool("google_calendar.get_events", {
            "calendar_id": cal["id"],
            "start_date": "2026-01-12",
            "end_date": "2026-01-12"
        })

        print(f"Calendar: {cal['summary']}")
        print(f"Events: {len(events.data['events'])}")
```

### Webhook Integration (Future)

The architecture supports real-time calendar updates via webhooks:

**Planned Features:**
- Push notifications for calendar changes
- Automatic re-sync on event updates
- Real-time conflict detection

See [Google Calendar API - Push Notifications](https://developers.google.com/calendar/api/guides/push) for implementation details.

---

## Best Practices

### 1. Sync Before Important Actions

Always sync before:
- Scheduling meetings
- Finding available time
- Planning your day

```bash
/pa:calendar view --sync
```

### 2. Use Week View for Planning

When planning ahead, use week view:

```bash
/pa:calendar view --week
```

### 3. Leverage Filters

Configure calendar filters to reduce noise:
- Exclude personal events from work briefings
- Filter out lunch blocks
- Hide declined meetings

### 4. Check Availability Before Committing

Before accepting meeting invites:

```bash
/pa:calendar available tomorrow at 2pm for 1 hour
```

### 5. Regular Daily Briefings

Make `/pa:daily` part of your morning routine:
- Auto-syncs calendar
- Provides schedule context
- Helps plan your day

### 6. Monitor State Files

Occasionally check State files to ensure sync is working:

```bash
# View today's events
cat State/calendar_today.json | jq '.events[] | "\(.summary) - \(.start.dateTime)"'

# Check sync timestamp
cat State/calendar_today.json | jq '.synced_at'
```

### 7. Timezone Awareness

When working across timezones:
- Always specify timezone in sync commands
- Verify event times in State files
- Use ISO 8601 format for clarity

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [Google Calendar Integration](../integrations/google-calendar.md) | Complete Google Calendar API setup and tool reference |
| [Personal Assistant Commands](../../commands/pa/README.md) | Overview of all `/pa:*` commands |
| [Architecture Guide](../architecture.md) | Thanos system architecture and patterns |
| [Hooks Integration](../hooks-integration.md) | Calendar hooks for automation |

---

## Appendix: File Structure

```
Thanos/
├── Tools/
│   ├── adapters/
│   │   ├── google_calendar.py       # Google Calendar adapter
│   │   ├── calendar_adapter.py      # Unified calendar wrapper
│   │   └── __init__.py              # Adapter registration
│   ├── calendar_sync.py             # Sync utility (standalone)
│   └── briefing_engine.py           # Daily briefing with calendar
├── commands/
│   ├── pa/
│   │   ├── calendar.py              # /pa:calendar command
│   │   ├── daily.py                 # /pa:daily (auto-syncs calendar)
│   │   └── schedule.py              # /pa:schedule (uses calendar data)
│   └── sc/
│       └── calendar.md              # Slash command definition
├── State/
│   ├── calendar_today.json          # Today's events (auto-generated)
│   ├── calendar_week.json           # Week's events (auto-generated)
│   └── calendar_credentials.json    # OAuth credentials
├── config/
│   └── calendar_filters.json        # Event filtering rules
├── tests/
│   ├── unit/
│   │   ├── test_google_calendar_adapter.py
│   │   ├── test_calendar_adapter.py
│   │   └── test_calendar_sync.py
│   └── integration/
│       └── test_daily_calendar_integration.py
└── docs/
    ├── guides/
    │   └── calendar-integration.md  # This guide
    └── integrations/
        └── google-calendar.md       # Google Calendar API reference
```

---

## Support and Feedback

For issues, questions, or feature requests:

1. **Check Troubleshooting** section above
2. **Review** [Google Calendar Integration Guide](../integrations/google-calendar.md)
3. **Search** existing issues in the Thanos repository
4. **Create** a new issue with:
   - Description of the problem
   - Steps to reproduce
   - Error messages and logs
   - Your environment details

---

*Guide created: 2026-01-12*
*Last updated: 2026-01-12*
*Version: 1.0*
*Feature: Calendar Integration (Task #001)*
