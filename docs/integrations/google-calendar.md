# Google Calendar Integration for Thanos

## Executive Summary

This document provides comprehensive setup and usage instructions for the Google Calendar integration in Thanos. This integration enables bidirectional calendar synchronization, intelligent time-blocking, conflict detection, and calendar-aware daily briefings.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Prerequisites](#prerequisites)
4. [Google Cloud Console Setup](#google-cloud-console-setup)
5. [Environment Configuration](#environment-configuration)
6. [Initial Authentication](#initial-authentication)
7. [Calendar Filtering](#calendar-filtering)
8. [Available Tools](#available-tools)
9. [Time-Blocking Workflows](#time-blocking-workflows)
10. [Daily Briefing Integration](#daily-briefing-integration)
11. [Troubleshooting](#troubleshooting)
12. [Security Considerations](#security-considerations)
13. [Advanced Configuration](#advanced-configuration)

---

## Overview

The Google Calendar adapter (`Tools/adapters/google_calendar.py`) integrates with Google Calendar API to provide:

- **Read Operations**: Fetch events, list calendars, check availability
- **Write Operations**: Create time blocks, update events, delete events
- **Intelligence**: Conflict detection, free slot finding, availability analysis
- **Filtering**: Flexible event filtering for focused context
- **OAuth 2.0**: Secure authentication with automatic token refresh

The adapter is designed for:
- Knowledge workers who want calendar-aware task scheduling
- Users who practice time-blocking for task management
- Teams coordinating between calendars and task systems

---

## Features

### Core Capabilities

✅ **OAuth 2.0 Authentication**
- Secure authorization flow with Google
- Automatic credential storage and refresh
- Support for multiple accounts (future)

✅ **Event Management**
- List all calendars with metadata
- Fetch events for any date range
- Create, update, and delete calendar events
- Handle all-day events, recurring events, and timezones

✅ **Scheduling Intelligence**
- Find free time slots with configurable criteria
- Detect conflicts between proposed times and existing events
- Analyze daily/weekly availability with metrics
- Calculate fragmentation scores and optimal work blocks

✅ **Time-Blocking**
- Push tasks to calendar as focused work blocks
- Batch schedule multiple tasks intelligently
- Auto-populate event details from task metadata
- Track Thanos-created events via extended properties

✅ **Calendar Filtering**
- Include/exclude specific calendars
- Filter by event type (focus time, meetings, OOO)
- Pattern matching on summary and description
- Attendee-based filtering
- Time-based filters (working hours, duration, weekends)
- Multiple filter presets for different contexts

✅ **Daily Briefing Integration**
- Calendar summary in morning briefings
- Upcoming event notifications
- Back-to-back meeting warnings
- Free time analysis for task planning

---

## Prerequisites

Before setting up the Google Calendar integration, ensure you have:

1. **Google Account**: A Google account with access to Google Calendar
2. **Google Cloud Project**: Access to Google Cloud Console (free tier sufficient)
3. **Python Environment**: Python 3.9+ with pip installed
4. **Dependencies**: Required packages (installed via `requirements.txt`):
   - `google-auth` (>=2.25.0)
   - `google-auth-oauthlib` (>=1.2.0)
   - `google-api-python-client` (>=2.110.0)

To install dependencies:

```bash
pip install -r requirements.txt
```

---

## Google Cloud Console Setup

Follow these steps to create OAuth 2.0 credentials for the Google Calendar API:

### Step 1: Create a Google Cloud Project

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Enter project name (e.g., "Thanos Calendar Integration")
4. Click **Create**
5. Wait for project creation (usually <30 seconds)
6. Select your new project from the project dropdown

### Step 2: Enable Google Calendar API

1. In the Cloud Console, navigate to **APIs & Services** → **Library**
2. Search for "Google Calendar API"
3. Click on **Google Calendar API** in the results
4. Click **Enable**
5. Wait for activation (usually instant)

### Step 3: Configure OAuth Consent Screen

1. Navigate to **APIs & Services** → **OAuth consent screen**
2. Choose **User Type**:
   - **External**: For personal use or testing (recommended for most users)
   - **Internal**: Only if using Google Workspace with domain control
3. Click **Create**
4. Fill in required fields:
   - **App name**: "Thanos Calendar Integration"
   - **User support email**: Your email address
   - **Developer contact email**: Your email address
5. Click **Save and Continue**
6. **Scopes** section: Click **Add or Remove Scopes**
   - Search and add: `https://www.googleapis.com/auth/calendar.readonly`
   - Search and add: `https://www.googleapis.com/auth/calendar.events`
   - These scopes allow reading and managing calendar events
7. Click **Update** → **Save and Continue**
8. **Test users** (for External apps in testing mode):
   - Click **Add Users**
   - Enter your Google account email
   - Click **Add** → **Save and Continue**
9. Review summary and click **Back to Dashboard**

### Step 4: Create OAuth 2.0 Credentials

1. Navigate to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Application type**: **Desktop app**
   - Desktop app is recommended for local Thanos installations
   - For server deployments, consider "Web application"
4. Enter **Name**: "Thanos Desktop Client"
5. Click **Create**
6. A dialog appears with your **Client ID** and **Client Secret**
7. **IMPORTANT**: Copy both values immediately - you'll need them for environment configuration
8. Click **OK** (you can always retrieve these later from the Credentials page)

### Step 5: Note Your Credentials

You should now have:
- **Client ID**: A long string ending in `.apps.googleusercontent.com`
- **Client Secret**: A shorter alphanumeric string

⚠️ **Security Warning**: Keep these credentials secure. Never commit them to version control.

---

## Environment Configuration

### Step 1: Copy Environment Template

```bash
# From the Thanos project root
cp .env.example .env
```

### Step 2: Add Google Calendar Credentials

Edit `.env` and add your OAuth credentials:

```bash
# Google Calendar Integration
GOOGLE_CALENDAR_CLIENT_ID=123456789-abcdefghijk.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=GOCSPX-AbCdEfGhIjKlMnOpQrStUvWx
GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:8080/oauth2callback
```

**Configuration Notes**:

- **CLIENT_ID**: Paste the full Client ID from Google Cloud Console
- **CLIENT_SECRET**: Paste the Client Secret exactly as shown
- **REDIRECT_URI**:
  - Default: `http://localhost:8080/oauth2callback` (recommended for desktop use)
  - This must match the authorized redirect URIs in your OAuth client configuration
  - For web applications, use your actual callback URL

### Step 3: Verify Environment File

Ensure `.env` is in your `.gitignore`:

```bash
# Check if .env is ignored
git check-ignore .env
# Should output: .env
```

If not ignored, add it:

```bash
echo ".env" >> .gitignore
```

### Step 4: Load Environment Variables

Thanos automatically loads `.env` on startup. To verify:

```bash
# Test that credentials are accessible
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✓ CLIENT_ID found' if os.getenv('GOOGLE_CALENDAR_CLIENT_ID') else '✗ CLIENT_ID missing')"
```

---

## Initial Authentication

### Step 1: Run Authentication Flow

The first time you use the Google Calendar integration, you'll need to complete OAuth authorization:

```python
from Tools.adapters import GoogleCalendarAdapter

# Initialize adapter
adapter = GoogleCalendarAdapter()

# Check if already authenticated
if adapter.is_authenticated():
    print("Already authenticated!")
else:
    # Get authorization URL
    auth_url, state = adapter.get_authorization_url()
    print(f"Please visit this URL to authorize:\n{auth_url}")

    # User will be redirected to: http://localhost:8080/oauth2callback?code=...&state=...
    # Copy the full redirect URL from your browser
    redirect_response = input("Paste the full redirect URL here: ")

    # Complete authorization
    result = adapter.complete_authorization(redirect_response)
    if result.success:
        print("✓ Authorization successful!")
    else:
        print(f"✗ Authorization failed: {result.error}")
```

### Step 2: Authorization Flow Details

When you visit the authorization URL:

1. **Google Sign-In**: Sign in with your Google account (if not already signed in)
2. **App Verification Screen**:
   - If your app is in "Testing" mode, you'll see a warning
   - Click **Continue** to proceed (this is normal for personal use)
3. **Permission Request**: Google will show the requested permissions:
   - "See, edit, share, and permanently delete all the calendars you can access using Google Calendar"
   - Review and click **Allow**
4. **Redirect**: Browser redirects to `http://localhost:8080/oauth2callback?code=...`
   - The page may show "This site can't be reached" - this is expected
   - **Copy the entire URL from the address bar**
5. **Paste URL**: Paste the full URL back into the Thanos prompt

### Step 3: Verify Authentication

After successful authentication, credentials are stored in `State/calendar_credentials.json`:

```bash
# Check credentials file exists
ls -l State/calendar_credentials.json
# Should show: -rw------- (600 permissions for security)

# Test authentication
python3 -c "
from Tools.adapters import GoogleCalendarAdapter
adapter = GoogleCalendarAdapter()
print('✓ Authenticated' if adapter.is_authenticated() else '✗ Not authenticated')
"
```

### Step 4: Using the Setup Script (Alternative)

Thanos provides a helper script for easier setup:

```bash
python3 scripts/setup_google_calendar.py
```

This script:
- Validates environment variables
- Guides you through OAuth flow
- Tests API connectivity
- Lists your calendars to confirm access

---

## Calendar Filtering

Calendar filters allow you to focus on relevant events and exclude noise from your Thanos context.

### Filter Configuration File

Filters are configured in `config/calendar_filters.json`. The default configuration includes:

```json
{
  "enabled": true,
  "filter_mode": "exclude",
  "calendars": {
    "include": [],
    "exclude": [],
    "primary_only": false
  },
  "event_types": {
    "include_all_day_events": true,
    "include_declined_events": false,
    "include_cancelled_events": false,
    "include_tentative_events": true
  },
  "summary_patterns": {
    "exclude": [
      "^\\[Blocked\\]",
      "^\\[Hold\\]",
      "(?i)personal.*time",
      "(?i)lunch.*break"
    ],
    "include": []
  },
  "attendees": {
    "exclude_emails": [],
    "min_attendees": null,
    "max_attendees": null
  },
  "time_filters": {
    "exclude_before_hour": null,
    "exclude_after_hour": null,
    "exclude_weekends": false
  }
}
```

### Filter Types

#### 1. Calendar Filters

Control which calendars are included:

```json
{
  "calendars": {
    "include": ["work@company.com", "primary"],
    "exclude": ["birthdays@google.calendar.com"],
    "primary_only": false
  }
}
```

- **include**: Only show events from these calendar IDs (empty = all)
- **exclude**: Hide events from these calendar IDs
- **primary_only**: Only include your primary calendar

#### 2. Event Type Filters

Filter based on event status and type:

```json
{
  "event_types": {
    "include_all_day_events": true,
    "include_declined_events": false,
    "include_cancelled_events": false,
    "include_tentative_events": true,
    "event_type_filters": {
      "focus_time": {
        "enabled": true,
        "action": "include"
      },
      "out_of_office": {
        "enabled": true,
        "action": "exclude"
      }
    }
  }
}
```

#### 3. Summary Pattern Filters

Use regex to match event titles:

```json
{
  "summary_patterns": {
    "exclude": [
      "^\\[Blocked\\]",     // Exclude events starting with [Blocked]
      "(?i)lunch",          // Exclude events with "lunch" (case-insensitive)
      "1:1 with.*"          // Exclude 1:1 meetings
    ],
    "include": [
      "(?i)standup",        // Only include events with "standup"
      "Sprint Planning"     // Include sprint planning events
    ],
    "case_sensitive": false
  }
}
```

**Pattern Syntax**: Python regex (re module)
- `^` = Start of string
- `$` = End of string
- `(?i)` = Case-insensitive flag
- `.*` = Any characters
- `\\.` = Literal dot

#### 4. Attendee Filters

Filter by meeting participants:

```json
{
  "attendees": {
    "exclude_emails": ["spam@example.com"],
    "include_emails": ["team@company.com"],
    "exclude_if_organizer": ["bot@calendar.company.com"],
    "min_attendees": 2,    // Only meetings with 2+ people
    "max_attendees": 10    // Exclude large meetings
  }
}
```

#### 5. Time Filters

Filter by time criteria:

```json
{
  "time_filters": {
    "exclude_before_hour": 8,     // Ignore events before 8 AM
    "exclude_after_hour": 18,     // Ignore events after 6 PM
    "min_duration_minutes": 15,   // Skip very short events
    "max_duration_minutes": 180,  // Skip very long events
    "exclude_weekends": true      // Only weekday events
  }
}
```

#### 6. Location Filters

Filter by event location:

```json
{
  "location_filters": {
    "exclude_locations": ["Off-site", "Client Office"],
    "include_locations": ["Office", "Conference Room"],
    "exclude_virtual_only": false,
    "exclude_in_person_only": false
  }
}
```

### Filter Presets

The configuration includes presets for common scenarios:

#### Work Only Preset
```json
{
  "presets": {
    "work_only": {
      "description": "Show only work-related events during business hours",
      "summary_patterns": {
        "exclude": ["(?i)personal", "(?i)family", "(?i)lunch"]
      },
      "time_filters": {
        "exclude_before_hour": 8,
        "exclude_after_hour": 18,
        "exclude_weekends": true
      }
    }
  }
}
```

#### Focus Sessions Preset
```json
{
  "presets": {
    "focus_sessions": {
      "description": "Show only focus time and deep work blocks",
      "summary_patterns": {
        "include": ["(?i)focus", "(?i)deep work", "(?i)coding time"]
      },
      "attendees": {
        "max_attendees": 1
      }
    }
  }
}
```

#### Meetings Only Preset
```json
{
  "presets": {
    "meetings_only": {
      "description": "Show only meetings with other people",
      "attendees": {
        "min_attendees": 2
      },
      "event_types": {
        "event_type_filters": {
          "focus_time": {"action": "exclude"}
        }
      }
    }
  }
}
```

### Applying Filters

Filters are automatically applied based on context:

```json
{
  "advanced": {
    "apply_filters_to_briefing": true,        // Filter events in daily brief
    "apply_filters_to_conflict_detection": false,  // Don't filter for conflicts
    "apply_filters_to_free_slots": true,      // Filter when finding free time
    "cache_filtered_results": true,
    "cache_ttl_minutes": 15
  }
}
```

**Important**: Conflict detection typically shouldn't filter events (you want to know about ALL conflicts), while briefings should be filtered for relevance.

### Testing Filters

Use the adapter's tools to test your filter configuration:

```python
from Tools.adapters import GoogleCalendarAdapter
import asyncio

async def test_filters():
    adapter = GoogleCalendarAdapter()

    # Get today's events with filters applied
    result = await adapter.execute_tool("get_today_events", {
        "include_all_day": True,
        "max_results": 20
    })

    print(f"Found {len(result.data.get('events', []))} events after filtering")
    for event in result.data.get('events', []):
        print(f"  - {event['summary']} ({event['start']} - {event['end']})")

# Run test
asyncio.run(test_filters())
```

---

## Available Tools

The Google Calendar adapter provides the following tools (accessible via `adapter.execute_tool()`):

### Authentication Tools

#### `check_auth`
Check authentication status and credential validity.

```python
result = await adapter.execute_tool("check_auth", {})
# Returns: {"authenticated": true, "email": "user@gmail.com", "expires_at": "..."}
```

### Calendar Management Tools

#### `list_calendars`
List all calendars accessible to the authenticated user.

**Parameters**:
- `show_hidden` (bool, optional): Include hidden calendars (default: false)
- `show_deleted` (bool, optional): Include deleted calendars (default: false)

**Example**:
```python
result = await adapter.execute_tool("list_calendars", {
    "show_hidden": False
})

# Returns:
# {
#   "calendars": [
#     {
#       "id": "primary",
#       "summary": "John Doe",
#       "description": "Primary calendar",
#       "primary": true,
#       "access_role": "owner",
#       "timezone": "America/New_York"
#     },
#     {
#       "id": "work@company.com",
#       "summary": "Work Calendar",
#       "primary": false,
#       "access_role": "writer"
#     }
#   ],
#   "count": 2
# }
```

### Event Fetching Tools

#### `get_events`
Fetch events for a specific date range.

**Parameters**:
- `start_date` (str, required): Start date in YYYY-MM-DD format
- `end_date` (str, optional): End date in YYYY-MM-DD format (default: same as start_date)
- `calendar_id` (str, optional): Specific calendar ID (default: "primary")
- `max_results` (int, optional): Maximum number of events to return (default: 250)
- `include_all_day` (bool, optional): Include all-day events (default: true)
- `timezone` (str, optional): Timezone for results (default: system timezone)

**Example**:
```python
result = await adapter.execute_tool("get_events", {
    "start_date": "2026-01-15",
    "end_date": "2026-01-16",
    "calendar_id": "primary",
    "max_results": 50
})

# Returns:
# {
#   "events": [
#     {
#       "id": "abc123",
#       "summary": "Team Standup",
#       "description": "Daily sync meeting",
#       "start": "2026-01-15T09:00:00-05:00",
#       "end": "2026-01-15T09:30:00-05:00",
#       "all_day": false,
#       "location": "Zoom",
#       "attendees": ["team@company.com"],
#       "status": "confirmed",
#       "recurring": false
#     }
#   ],
#   "count": 1,
#   "date_range": "2026-01-15 to 2026-01-16"
# }
```

#### `get_today_events`
Convenience tool to fetch today's events with intelligent defaults.

**Parameters**:
- `calendar_id` (str, optional): Calendar ID (default: "primary")
- `include_all_day` (bool, optional): Include all-day events (default: true)
- `max_results` (int, optional): Maximum events (default: 100)

**Example**:
```python
result = await adapter.execute_tool("get_today_events", {})

# Returns same format as get_events, plus:
# {
#   "events": [...],
#   "summary": {
#     "total_events": 5,
#     "meetings": 3,
#     "focus_blocks": 2,
#     "all_day_events": 0,
#     "first_event": "09:00",
#     "last_event": "17:00",
#     "total_meeting_minutes": 180,
#     "free_time_minutes": 300
#   }
# }
```

### Scheduling Intelligence Tools

#### `find_free_slots`
Find available time slots for scheduling.

**Parameters**:
- `start_date` (str, required): Search start date (YYYY-MM-DD)
- `end_date` (str, optional): Search end date (default: same day)
- `duration_minutes` (int, required): Required slot duration
- `working_hours_start` (int, optional): Working hours start (24h format, default: 9)
- `working_hours_end` (int, optional): Working hours end (24h format, default: 17)
- `buffer_minutes` (int, optional): Buffer time between events (default: 0)
- `calendar_id` (str, optional): Calendar to check (default: "primary")
- `timezone` (str, optional): Timezone for results (default: system)

**Example**:
```python
result = await adapter.execute_tool("find_free_slots", {
    "start_date": "2026-01-15",
    "duration_minutes": 60,
    "working_hours_start": 9,
    "working_hours_end": 17,
    "buffer_minutes": 15
})

# Returns:
# {
#   "free_slots": [
#     {
#       "start": "2026-01-15T10:00:00-05:00",
#       "end": "2026-01-15T11:00:00-05:00",
#       "duration_minutes": 60
#     },
#     {
#       "start": "2026-01-15T14:30:00-05:00",
#       "end": "2026-01-15T15:30:00-05:00",
#       "duration_minutes": 60
#     }
#   ],
#   "count": 2,
#   "search_params": {...}
# }
```

#### `check_conflicts`
Check if a proposed time slot conflicts with existing events.

**Parameters**:
- `start_time` (str, required): Proposed start time (ISO 8601)
- `end_time` (str, required): Proposed end time (ISO 8601)
- `calendar_id` (str, optional): Calendar to check (default: "primary")
- `include_tentative` (bool, optional): Consider tentative events as conflicts (default: true)

**Example**:
```python
result = await adapter.execute_tool("check_conflicts", {
    "start_time": "2026-01-15T14:00:00",
    "end_time": "2026-01-15T15:00:00"
})

# Returns:
# {
#   "has_conflict": true,
#   "conflicts": [
#     {
#       "summary": "Project Review",
#       "start": "2026-01-15T14:30:00-05:00",
#       "end": "2026-01-15T15:30:00-05:00",
#       "overlap_minutes": 30
#     }
#   ],
#   "conflict_count": 1,
#   "proposed_slot": {
#     "start": "2026-01-15T14:00:00-05:00",
#     "end": "2026-01-15T15:00:00-05:00"
#   }
# }
```

#### `get_availability`
Analyze calendar availability with detailed metrics.

**Parameters**:
- `start_date` (str, required): Analysis start date
- `end_date` (str, optional): Analysis end date (default: same day)
- `working_hours_start` (int, optional): Working hours start (default: 9)
- `working_hours_end` (int, optional): Working hours end (default: 17)
- `calendar_id` (str, optional): Calendar ID (default: "primary")

**Example**:
```python
result = await adapter.execute_tool("get_availability", {
    "start_date": "2026-01-15",
    "working_hours_start": 9,
    "working_hours_end": 17
})

# Returns:
# {
#   "total_working_minutes": 480,
#   "busy_minutes": 180,
#   "free_minutes": 300,
#   "utilization_percent": 37.5,
#   "longest_free_block_minutes": 120,
#   "fragmentation_score": 0.35,
#   "back_to_back_meetings": 2,
#   "daily_breakdown": [
#     {
#       "date": "2026-01-15",
#       "free_minutes": 300,
#       "busy_minutes": 180,
#       "event_count": 4
#     }
#   ]
# }
```

**Fragmentation Score**: 0 = perfectly consolidated, 1 = highly fragmented

### Event Creation Tools

#### `create_event`
Create a new calendar event.

**Parameters**:
- `summary` (str, required): Event title
- `start_time` (str, required): Start time (ISO 8601 or YYYY-MM-DD for all-day)
- `end_time` (str, required): End time (ISO 8601 or YYYY-MM-DD for all-day)
- `description` (str, optional): Event description
- `location` (str, optional): Event location
- `attendees` (list, optional): List of email addresses
- `calendar_id` (str, optional): Target calendar (default: "primary")
- `timezone` (str, optional): Event timezone
- `reminders` (list, optional): Reminder configuration
- `color_id` (str, optional): Event color (1-11)

**Example**:
```python
result = await adapter.execute_tool("create_event", {
    "summary": "Deep Work: Code Review",
    "start_time": "2026-01-15T14:00:00",
    "end_time": "2026-01-15T16:00:00",
    "description": "Review PRs for project X",
    "location": "Focus Room",
    "color_id": "9"  # Blue for focus time
})

# Returns:
# {
#   "event_id": "xyz789",
#   "summary": "Deep Work: Code Review",
#   "html_link": "https://calendar.google.com/event?eid=...",
#   "created": true
# }
```

#### `block_time_for_task`
High-level tool to create a time block from task data.

**Parameters**:
- `task_title` (str, required): Task title
- `duration_minutes` (int, required): Task duration
- `start_time` (str, optional): Specific start time (ISO 8601)
- `preferred_date` (str, optional): Preferred date if no start_time (YYYY-MM-DD)
- `task_description` (str, optional): Task details
- `task_id` (str, optional): Task ID for tracking
- `priority` (str, optional): Task priority (high/medium/low)
- `calendar_id` (str, optional): Target calendar
- `auto_find_slot` (bool, optional): Automatically find free slot (default: true)

**Example**:
```python
result = await adapter.execute_tool("block_time_for_task", {
    "task_title": "Write documentation",
    "duration_minutes": 90,
    "preferred_date": "2026-01-15",
    "task_description": "Complete Google Calendar integration docs",
    "priority": "high",
    "auto_find_slot": True
})

# Returns:
# {
#   "event_id": "abc456",
#   "summary": "[Thanos] Write documentation",
#   "start": "2026-01-15T10:00:00-05:00",
#   "end": "2026-01-15T11:30:00-05:00",
#   "slot_auto_selected": true,
#   "html_link": "https://calendar.google.com/event?eid=..."
# }
```

**Note**: Events created via `block_time_for_task` are tagged with Thanos metadata in extended properties for tracking.

### Event Modification Tools

#### `update_event`
Update an existing calendar event.

**Parameters**:
- `event_id` (str, required): Event ID to update
- `calendar_id` (str, optional): Calendar ID (default: "primary")
- `summary` (str, optional): New title
- `start_time` (str, optional): New start time
- `end_time` (str, optional): New end time
- `description` (str, optional): New description
- `location` (str, optional): New location

**Example**:
```python
result = await adapter.execute_tool("update_event", {
    "event_id": "abc456",
    "start_time": "2026-01-15T11:00:00",
    "end_time": "2026-01-15T12:30:00"
})

# Returns:
# {
#   "event_id": "abc456",
#   "updated": true,
#   "changes": ["start_time", "end_time"]
# }
```

**Safety**: The adapter checks for Thanos metadata before allowing updates to prevent accidental modification of non-Thanos events (configurable).

#### `delete_event`
Delete a calendar event.

**Parameters**:
- `event_id` (str, required): Event ID to delete
- `calendar_id` (str, optional): Calendar ID (default: "primary")
- `send_updates` (str, optional): Send cancellation to attendees ("all", "none", default: "all")

**Example**:
```python
result = await adapter.execute_tool("delete_event", {
    "event_id": "abc456",
    "send_updates": "all"
})

# Returns:
# {
#   "event_id": "abc456",
#   "deleted": true
# }
```

### Utility Tools

#### `health_check`
Verify API connectivity and credential validity.

```python
result = await adapter.execute_tool("health_check", {})

# Returns:
# {
#   "status": "healthy",
#   "authenticated": true,
#   "api_accessible": true,
#   "calendar_count": 3,
#   "response_time_ms": 245
# }
```

---

## Time-Blocking Workflows

Time-blocking is the practice of scheduling dedicated time for tasks. The Google Calendar integration supports several time-blocking workflows:

### Workflow 1: Manual Time Blocking

Block time for a specific task at a specific time:

```python
from Tools.adapters import GoogleCalendarAdapter
import asyncio

async def block_specific_time():
    adapter = GoogleCalendarAdapter()

    result = await adapter.execute_tool("block_time_for_task", {
        "task_title": "Review Q1 metrics",
        "duration_minutes": 60,
        "start_time": "2026-01-16T14:00:00",
        "task_description": "Analyze revenue, user growth, and churn",
        "priority": "high"
    })

    if result.success:
        print(f"✓ Time blocked: {result.data['html_link']}")
    else:
        print(f"✗ Failed: {result.error}")

asyncio.run(block_specific_time())
```

### Workflow 2: Auto-Find Next Available Slot

Let the adapter find the best available time:

```python
async def block_next_available():
    adapter = GoogleCalendarAdapter()

    result = await adapter.execute_tool("block_time_for_task", {
        "task_title": "Code review session",
        "duration_minutes": 90,
        "preferred_date": "2026-01-16",
        "auto_find_slot": True
    })

    if result.success:
        print(f"✓ Auto-scheduled at {result.data['start']}")

asyncio.run(block_next_available())
```

### Workflow 3: Batch Time Blocking

Schedule multiple tasks in optimal slots:

```python
async def batch_time_block():
    adapter = GoogleCalendarAdapter()

    tasks = [
        {"title": "Write unit tests", "duration": 60, "priority": "high"},
        {"title": "Update documentation", "duration": 45, "priority": "medium"},
        {"title": "Team 1:1 prep", "duration": 30, "priority": "high"},
    ]

    # Find all free slots for the week
    free_slots_result = await adapter.execute_tool("find_free_slots", {
        "start_date": "2026-01-15",
        "end_date": "2026-01-19",
        "duration_minutes": 30,
        "buffer_minutes": 15
    })

    free_slots = free_slots_result.data['free_slots']

    # Schedule tasks in available slots
    for i, task in enumerate(tasks):
        if i < len(free_slots):
            slot = free_slots[i]
            result = await adapter.execute_tool("block_time_for_task", {
                "task_title": task["title"],
                "duration_minutes": task["duration"],
                "start_time": slot["start"]
            })
            print(f"✓ Scheduled: {task['title']} at {slot['start']}")

asyncio.run(batch_time_block())
```

### Workflow 4: Conflict-Aware Scheduling

Check for conflicts before scheduling:

```python
async def safe_time_block():
    adapter = GoogleCalendarAdapter()

    proposed_start = "2026-01-15T15:00:00"
    proposed_end = "2026-01-15T16:30:00"

    # Check conflicts first
    conflict_check = await adapter.execute_tool("check_conflicts", {
        "start_time": proposed_start,
        "end_time": proposed_end
    })

    if conflict_check.data['has_conflict']:
        print("✗ Conflict detected:")
        for conflict in conflict_check.data['conflicts']:
            print(f"  - {conflict['summary']} ({conflict['start']})")

        # Find alternative slot
        free_slots = await adapter.execute_tool("find_free_slots", {
            "start_date": "2026-01-15",
            "duration_minutes": 90
        })

        if free_slots.data['free_slots']:
            alternative = free_slots.data['free_slots'][0]
            print(f"✓ Alternative slot found: {alternative['start']}")
    else:
        # No conflict, proceed
        result = await adapter.execute_tool("create_event", {
            "summary": "[Thanos] Deep work session",
            "start_time": proposed_start,
            "end_time": proposed_end
        })
        print(f"✓ Event created: {result.data['event_id']}")

asyncio.run(safe_time_block())
```

### Workflow 5: Integration with Thanos Tasks

Combine with Thanos task management:

```python
# This is pseudocode showing the intended integration
async def schedule_thanos_tasks():
    from Tools.task_manager import TaskManager

    task_mgr = TaskManager()
    calendar = GoogleCalendarAdapter()

    # Get high-priority tasks without scheduled time
    tasks = task_mgr.get_tasks(priority="high", scheduled=False)

    for task in tasks:
        # Estimate duration if not set
        duration = task.get("estimated_minutes", 60)

        # Block time for task
        result = await calendar.execute_tool("block_time_for_task", {
            "task_title": task["title"],
            "duration_minutes": duration,
            "task_id": task["id"],
            "task_description": task["description"],
            "preferred_date": "tomorrow",
            "auto_find_slot": True
        })

        if result.success:
            # Update task with scheduled time
            task_mgr.update_task(task["id"], {
                "scheduled_at": result.data["start"],
                "calendar_event_id": result.data["event_id"]
            })
```

### Best Practices for Time-Blocking

1. **Buffer Time**: Always include 10-15 minute buffers between blocks for transitions
2. **Realistic Durations**: Estimate task durations conservatively (add 25-50% padding)
3. **Energy Levels**: Schedule deep work during your peak energy times
4. **Batch Similar Tasks**: Group similar tasks together for context efficiency
5. **Review and Adjust**: Review your calendar weekly and adjust time blocks as needed
6. **Protect Focus Time**: Use filters to preserve focus blocks from meeting requests
7. **Track Thanos Events**: Use Thanos metadata to distinguish your time blocks from other events

---

## Daily Briefing Integration

The Google Calendar adapter integrates with Thanos daily briefing to provide calendar-aware context.

### How It Works

When you run the daily briefing (`Tools/daily-brief.ts`), the system:

1. Fetches today's events using `get_today_events`
2. Applies calendar filters for relevance
3. Generates a human-readable calendar summary
4. Identifies upcoming events (within 2 hours)
5. Detects back-to-back meetings
6. Calculates free time for task scheduling

### Example Daily Brief Output

```markdown
# Daily Brief - Wednesday, January 15, 2026

## Calendar Overview
📅 5 events today | 🕐 3h meeting time | 🔓 4h free time

### Upcoming Events
- **9:00 AM - 9:30 AM**: Team Standup (in 45 minutes)
- **10:00 AM - 11:00 AM**: Sprint Planning

### Today's Schedule
| Time | Event | Type |
|------|-------|------|
| 9:00 - 9:30 | Team Standup | Meeting |
| 10:00 - 11:00 | Sprint Planning | Meeting |
| 11:00 - 12:30 | [Thanos] Deep Work: Code Review | Focus |
| 2:00 - 3:00 | 1:1 with Sarah | Meeting |
| 4:00 - 5:00 | [Thanos] Documentation | Focus |

⚠️ **Warning**: Back-to-back meetings from 9:00 AM - 12:30 PM

### Free Time Windows
- 12:30 PM - 2:00 PM (90 minutes)
- 3:00 PM - 4:00 PM (60 minutes)
- After 5:00 PM (open)

**Availability Score**: 62% (4h free / 6.5h working)
**Fragmentation**: Moderate (2 blocks > 60min)

## Recommended Actions
- ✅ Good focus time available this afternoon
- ⚠️ Prepare for morning meeting block (9-11 AM)
- 💡 Consider scheduling deep work in 12:30-2:00 PM slot
```

### Configuration

Briefing integration is controlled by:

```json
// config/calendar_filters.json
{
  "advanced": {
    "apply_filters_to_briefing": true,
    "cache_filtered_results": true,
    "cache_ttl_minutes": 15
  }
}
```

### Customizing Briefing Output

The calendar summary generator (`_tool_get_today_events`) provides summary data that can be customized in `Tools/daily-brief.ts`:

```typescript
// Example customization
if (calendarData.summary.back_to_back_meetings > 2) {
  brief += "\n⚠️ HIGH MEETING LOAD: Consider blocking recovery time\n";
}

if (calendarData.summary.fragmentation_score > 0.7) {
  brief += "\n💡 FRAGMENTED SCHEDULE: Few long focus blocks available\n";
}

if (calendarData.summary.free_time_minutes < 120) {
  brief += "\n⏰ LIMITED FREE TIME: Prioritize ruthlessly today\n";
}
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "CLIENT_ID not found" or "CLIENT_SECRET not found"

**Cause**: Environment variables not properly set.

**Solution**:
1. Verify `.env` file exists in project root
2. Check that variables are set:
   ```bash
   cat .env | grep GOOGLE_CALENDAR
   ```
3. Ensure no extra spaces or quotes around values
4. Reload environment:
   ```bash
   source .env  # If using bash
   ```

#### Issue 2: "Invalid credentials" or "Token has been expired or revoked"

**Cause**: OAuth token expired or invalidated.

**Solution**:
1. Delete existing credentials:
   ```bash
   rm State/calendar_credentials.json
   ```
2. Re-authenticate:
   ```python
   from Tools.adapters import GoogleCalendarAdapter
   adapter = GoogleCalendarAdapter()
   auth_url, state = adapter.get_authorization_url()
   print(auth_url)
   # Follow OAuth flow again
   ```

#### Issue 3: "Redirect URI mismatch"

**Cause**: The redirect URI in your OAuth request doesn't match the one configured in Google Cloud Console.

**Solution**:
1. Check your `.env`:
   ```bash
   grep REDIRECT_URI .env
   ```
2. Go to Google Cloud Console → APIs & Services → Credentials
3. Click on your OAuth 2.0 Client ID
4. Under "Authorized redirect URIs", ensure it matches your `.env` value exactly
5. Common value: `http://localhost:8080/oauth2callback`
6. Click **Save** and wait 5 minutes for changes to propagate

#### Issue 4: "API quota exceeded"

**Cause**: Too many API requests in a short period.

**Solution**:
1. Enable caching in `config/calendar_filters.json`:
   ```json
   {
     "advanced": {
       "cache_filtered_results": true,
       "cache_ttl_minutes": 15
     }
   }
   ```
2. Reduce polling frequency
3. Check Google Cloud Console → APIs & Services → Dashboard for quota limits
4. Request quota increase if needed (usually granted quickly for Calendar API)

#### Issue 5: "Events not showing in briefing"

**Cause**: Events filtered out by calendar filters.

**Solution**:
1. Check filter configuration:
   ```bash
   cat config/calendar_filters.json | jq '.summary_patterns.exclude'
   ```
2. Temporarily disable filters:
   ```json
   {
     "enabled": false
   }
   ```
3. Test again to see if events appear
4. Adjust filters to be less restrictive

#### Issue 6: "Permission denied" when saving credentials

**Cause**: File permission issues with `State/calendar_credentials.json`.

**Solution**:
```bash
# Check current permissions
ls -l State/calendar_credentials.json

# Fix permissions (should be 600 = rw-------)
chmod 600 State/calendar_credentials.json

# Ensure State directory exists
mkdir -p State
```

#### Issue 7: "Timezone issues" - Events showing at wrong times

**Cause**: Timezone mismatch between system, Google Calendar, and Thanos.

**Solution**:
1. Check system timezone:
   ```bash
   python3 -c "from datetime import datetime; import time; print(time.tzname)"
   ```
2. Check calendar timezone in list_calendars output
3. Explicitly set timezone in tool calls:
   ```python
   result = await adapter.execute_tool("get_events", {
       "start_date": "2026-01-15",
       "timezone": "America/New_York"
   })
   ```
4. Verify your primary calendar timezone in Google Calendar settings

#### Issue 8: "403 Forbidden" errors

**Cause**: Google Calendar API not enabled or insufficient permissions.

**Solution**:
1. Go to Google Cloud Console → APIs & Services → Library
2. Search for "Google Calendar API"
3. Ensure it shows "API Enabled" (not "Enable")
4. Check OAuth consent screen has correct scopes:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/calendar.events`
5. Re-authenticate after enabling API/scopes

#### Issue 9: "Events not updating in real-time"

**Cause**: Caching or not refreshing data.

**Solution**:
1. Reduce cache TTL:
   ```json
   {
     "advanced": {
       "cache_ttl_minutes": 5
     }
   }
   ```
2. Force refresh by passing `cache_bust=true` (if implemented)
3. Restart Thanos process to clear in-memory cache

#### Issue 10: "Cannot find free slots"

**Cause**: Working hours or duration constraints too restrictive.

**Solution**:
1. Widen working hours:
   ```python
   result = await adapter.execute_tool("find_free_slots", {
       "working_hours_start": 8,  # Start earlier
       "working_hours_end": 19,   # End later
       "duration_minutes": 30     # Shorter duration
   })
   ```
2. Reduce buffer time:
   ```python
   {
       "buffer_minutes": 0  # No buffer
   }
   ```
3. Extend date range:
   ```python
   {
       "start_date": "2026-01-15",
       "end_date": "2026-01-20"  # Look across full week
   }
   ```

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Tools.adapters.google_calendar")
logger.setLevel(logging.DEBUG)

# Now run your code
adapter = GoogleCalendarAdapter()
result = await adapter.execute_tool("get_today_events", {})
# Will output detailed API calls, responses, and errors
```

### Getting Help

If issues persist:

1. **Check logs**: Look for errors in console output or log files
2. **Health check**: Run `health_check` tool to diagnose connectivity
3. **API status**: Check [Google Workspace Status Dashboard](https://www.google.com/appsstatus/dashboard/)
4. **Documentation**: Review [Google Calendar API documentation](https://developers.google.com/calendar/api)
5. **Community**: Search for similar issues in Thanos issue tracker

---

## Security Considerations

### OAuth Credentials Storage

**Storage Location**: `State/calendar_credentials.json`

**Security Measures**:
- File permissions set to `0600` (read/write for owner only)
- Automatically added to `.gitignore` to prevent commits
- Refresh tokens stored encrypted (if encryption is enabled)
- Credentials never logged or printed to console

**Best Practices**:
1. **Never commit credentials**: Always verify `.gitignore` includes:
   ```
   State/calendar_credentials.json
   .env
   ```
2. **Rotate credentials periodically**: Generate new OAuth clients every 90 days for production
3. **Use service accounts for servers**: For deployed/server environments, use service account authentication instead of user OAuth
4. **Restrict OAuth scopes**: Only request necessary scopes (readonly if you don't need write access)

### Environment Variable Security

**Risk**: `.env` file contains sensitive credentials.

**Mitigations**:
1. Always add `.env` to `.gitignore`
2. For production, use environment variable injection (not `.env` files):
   ```bash
   export GOOGLE_CALENDAR_CLIENT_ID="..."
   export GOOGLE_CALENDAR_CLIENT_SECRET="..."
   ```
3. Consider using secret management tools:
   - AWS Secrets Manager
   - HashiCorp Vault
   - 1Password CLI
   - Azure Key Vault

### API Access Control

**Calendar Scopes**:
- `calendar.readonly`: Read-only access to calendar events
- `calendar.events`: Read/write access to events

**Principle of Least Privilege**:
- If you only need to read events (no time-blocking), use readonly scope only
- Remove write scope from OAuth consent screen
- Re-authenticate with reduced permissions

### Multi-User Considerations

**Risk**: Multiple users accessing the same Thanos instance.

**Recommendations**:
1. **Separate credentials per user**: Each user should have their own `State/` directory
2. **User-specific config**: Maintain separate `config/calendar_filters.json` per user
3. **Workspace isolation**: Consider running separate Thanos instances per user
4. **Audit logging**: Log all calendar modifications with user attribution

### Network Security

**API Communication**:
- All Google Calendar API calls use HTTPS (enforced by library)
- OAuth flow requires HTTPS in production (localhost HTTP is allowed for development)

**Recommendations**:
1. **Use HTTPS redirect URIs** for production deployments
2. **Validate SSL certificates**: Don't disable certificate validation
3. **Firewall rules**: Restrict outbound connections to Google API endpoints only

### Data Privacy

**Event Data**:
- Calendar events may contain sensitive information (meeting titles, attendees, locations)
- Events are cached temporarily for performance (see `cache_ttl_minutes`)

**Recommendations**:
1. **Clear caches regularly**: Reduce cache TTL for sensitive environments
2. **Filter sensitive events**: Use summary patterns to exclude confidential events:
   ```json
   {
     "summary_patterns": {
       "exclude": ["(?i)confidential", "(?i)private", "NDA"]
     }
   }
   ```
3. **Secure logs**: Ensure event details aren't logged in production
4. **Data retention**: Regularly clean up old session logs and cached data

### OAuth State Validation

**CSRF Protection**:
- OAuth flow includes state parameter to prevent CSRF attacks
- State is validated during callback to ensure request authenticity

**Implementation**:
```python
# State is automatically generated and validated
auth_url, state = adapter.get_authorization_url()
# State is stored in adapter._pending_state
# Validation happens in complete_authorization()
```

**Important**: Don't share authorization URLs - they contain user-specific state tokens.

### Credential Refresh Security

**Automatic Refresh**:
- Access tokens expire after ~1 hour
- Refresh tokens are used to obtain new access tokens
- Refresh happens automatically and re-stores credentials securely

**Risk**: Compromised refresh token grants long-term access.

**Mitigations**:
1. **Rotation**: Google automatically rotates refresh tokens periodically
2. **Revocation**: Revoke access via [Google Account Permissions](https://myaccount.google.com/permissions)
3. **Monitoring**: Check for unauthorized API usage in Google Cloud Console

### Production Deployment Checklist

Before deploying Thanos with Google Calendar integration to production:

- [ ] Use service account authentication (not user OAuth)
- [ ] Store credentials in secure secret management system
- [ ] Enable HTTPS for all OAuth redirect URIs
- [ ] Implement credential encryption at rest
- [ ] Set up audit logging for all calendar modifications
- [ ] Configure rate limiting and quota monitoring
- [ ] Document incident response for credential compromise
- [ ] Regular security review of OAuth applications (90-day cycle)
- [ ] Implement least-privilege access (readonly if possible)
- [ ] Set up monitoring for API errors and unauthorized access attempts

---

## Advanced Configuration

### Custom OAuth Redirect URI

For web deployments, configure a custom redirect URI:

**1. Update Google Cloud Console**:
- Go to APIs & Services → Credentials → Your OAuth Client
- Add redirect URI: `https://your-domain.com/oauth/callback`
- Save changes

**2. Update `.env`**:
```bash
GOOGLE_CALENDAR_REDIRECT_URI=https://your-domain.com/oauth/callback
```

**3. Implement callback handler** (pseudocode):
```python
from flask import Flask, request
app = Flask(__name__)

@app.route('/oauth/callback')
def oauth_callback():
    redirect_url = request.url
    adapter = GoogleCalendarAdapter()
    result = adapter.complete_authorization(redirect_url)

    if result.success:
        return "Authorization successful! You can close this window."
    else:
        return f"Authorization failed: {result.error}", 400
```

### Service Account Authentication

For server environments, use service account instead of user OAuth:

**1. Create Service Account**:
- Google Cloud Console → IAM & Admin → Service Accounts
- Create service account with Calendar API access
- Generate JSON key file

**2. Enable Domain-Wide Delegation** (Google Workspace only):
- Edit service account → Enable G Suite Domain-wide Delegation
- Note the Client ID
- In Google Workspace Admin Console, authorize scopes for the Client ID

**3. Update adapter initialization**:
```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'path/to/service-account.json',
    scopes=GoogleCalendarAdapter.SCOPES,
    subject='user@domain.com'  # Impersonate this user
)

adapter = GoogleCalendarAdapter()
adapter._credentials = credentials
```

### Multiple Calendar Accounts

To manage multiple calendar accounts:

**1. Separate credential files**:
```python
adapter_work = GoogleCalendarAdapter()
adapter_work.CREDENTIALS_FILE = "State/calendar_work.json"

adapter_personal = GoogleCalendarAdapter()
adapter_personal.CREDENTIALS_FILE = "State/calendar_personal.json"
```

**2. Authenticate each separately**:
```python
# Authenticate work account
auth_url, _ = adapter_work.get_authorization_url()
# Complete OAuth flow...

# Authenticate personal account
auth_url, _ = adapter_personal.get_authorization_url()
# Complete OAuth flow...
```

**3. Query across accounts**:
```python
# Get events from both calendars
work_events = await adapter_work.execute_tool("get_today_events", {})
personal_events = await adapter_personal.execute_tool("get_today_events", {})

# Merge results
all_events = work_events.data['events'] + personal_events.data['events']
all_events.sort(key=lambda e: e['start'])
```

### Custom Event Colors

Google Calendar supports 11 event colors. Use them to categorize time blocks:

```python
COLOR_SCHEME = {
    "focus_time": "9",      # Blue
    "meetings": "5",        # Yellow
    "admin": "8",           # Gray
    "personal": "4",        # Red
    "learning": "10",       # Green
}

# Create color-coded event
await adapter.execute_tool("create_event", {
    "summary": "[Thanos] Deep Work",
    "start_time": "2026-01-15T14:00:00",
    "end_time": "2026-01-15T16:00:00",
    "color_id": COLOR_SCHEME["focus_time"]
})
```

### Webhook Notifications (Google Calendar Push)

Set up push notifications for real-time calendar updates:

```python
# This is advanced - requires publicly accessible webhook endpoint
# See: https://developers.google.com/calendar/api/guides/push

import uuid

# Start watching for changes
watch_request = {
    "id": str(uuid.uuid4()),
    "type": "web_hook",
    "address": "https://your-domain.com/calendar-webhook",
    "token": "optional-verification-token"
}

# Implementation requires setting up webhook endpoint
# and processing incoming notifications
```

### Performance Optimization

**Batch API Requests**:
```python
# Instead of multiple individual calls
for calendar_id in calendar_ids:
    events = await adapter.execute_tool("get_events", {"calendar_id": calendar_id})

# Use batch requests (requires implementation)
# This is a future enhancement - not yet implemented
```

**Aggressive Caching**:
```json
{
  "advanced": {
    "cache_filtered_results": true,
    "cache_ttl_minutes": 60,  // Cache for 1 hour
    "cache_strategy": "aggressive"
  }
}
```

**Pagination for Large Calendars**:
```python
# If you have many events, use pagination
result = await adapter.execute_tool("get_events", {
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "max_results": 2500  # Google's maximum
})
```

### Custom Retry Logic

Override default retry behavior:

```python
adapter = GoogleCalendarAdapter()

# Customize retry parameters
adapter.MAX_RETRIES = 5
adapter.INITIAL_BACKOFF = 2.0
adapter.MAX_BACKOFF = 64.0
adapter.BACKOFF_MULTIPLIER = 2.5
```

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [Google Calendar API Docs](https://developers.google.com/calendar/api) | Official Google Calendar API documentation |
| [OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2) | Google OAuth 2.0 implementation guide |
| [Thanos Hooks Integration](../hooks-integration.md) | Integrating calendar with daily briefing hooks |
| [Thanos MCP Bridge](../mcp-bridge.md) | Using calendar via MCP protocol |

## Appendix: Example Configurations

### Configuration 1: Minimal (Personal Use)

```json
{
  "enabled": true,
  "filter_mode": "exclude",
  "event_types": {
    "include_declined_events": false,
    "include_cancelled_events": false
  },
  "summary_patterns": {
    "exclude": ["(?i)lunch", "(?i)personal"]
  }
}
```

### Configuration 2: Work Focus

```json
{
  "enabled": true,
  "calendars": {
    "include": ["work@company.com", "team@company.com"]
  },
  "time_filters": {
    "exclude_before_hour": 8,
    "exclude_after_hour": 18,
    "exclude_weekends": true
  },
  "attendees": {
    "min_attendees": 2
  },
  "summary_patterns": {
    "exclude": ["(?i)personal", "(?i)dentist", "(?i)doctor"]
  }
}
```

### Configuration 3: Deep Work Only

```json
{
  "enabled": true,
  "summary_patterns": {
    "include": [
      "(?i)focus",
      "(?i)deep work",
      "(?i)coding",
      "(?i)writing",
      "\\[Thanos\\]"
    ]
  },
  "attendees": {
    "max_attendees": 1
  }
}
```

---

*Document created: 2026-01-11*
*Last updated: 2026-01-11*
*Version: 1.0*
*Author: Thanos Calendar Integration Team*
