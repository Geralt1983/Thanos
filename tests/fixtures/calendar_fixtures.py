"""
Test fixtures and mock data for Google Calendar adapter tests.

Provides realistic mock data for calendar events, credentials, and API responses.
"""

from datetime import datetime, timedelta
from typing import Any


def get_mock_credentials_data() -> dict[str, Any]:
    """Get mock OAuth credentials data."""
    return {
        "token": "mock_access_token_abc123",
        "refresh_token": "mock_refresh_token_xyz789",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "mock_client_id.apps.googleusercontent.com",
        "client_secret": "mock_client_secret",
        "scopes": [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        "expiry": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
    }


def get_mock_event(
    summary: str = "Test Event",
    start_time: datetime | None = None,
    duration_minutes: int = 60,
    all_day: bool = False,
    event_id: str = "event_123",
    **kwargs,
) -> dict[str, Any]:
    """
    Create a mock Google Calendar event.

    Args:
        summary: Event title
        start_time: Event start time (defaults to now)
        duration_minutes: Event duration in minutes
        all_day: Whether this is an all-day event
        event_id: Unique event identifier
        **kwargs: Additional event properties

    Returns:
        Mock event dictionary matching Google Calendar API format
    """
    if start_time is None:
        start_time = datetime.now()

    if all_day:
        event = {
            "id": event_id,
            "summary": summary,
            "start": {"date": start_time.strftime("%Y-%m-%d")},
            "end": {
                "date": (start_time + timedelta(days=1)).strftime("%Y-%m-%d")
            },
            "status": "confirmed",
        }
    else:
        end_time = start_time + timedelta(minutes=duration_minutes)
        event = {
            "id": event_id,
            "summary": summary,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "America/Los_Angeles",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "America/Los_Angeles",
            },
            "status": "confirmed",
        }

    # Add optional fields
    event.update(kwargs)
    return event


def get_mock_calendar(
    calendar_id: str = "primary",
    summary: str = "My Calendar",
    primary: bool = True,
) -> dict[str, Any]:
    """Create a mock calendar object."""
    return {
        "id": calendar_id,
        "summary": summary,
        "primary": primary,
        "accessRole": "owner",
        "timeZone": "America/Los_Angeles",
        "backgroundColor": "#9fc6e7",
        "foregroundColor": "#000000",
    }


def get_mock_calendar_list() -> dict[str, Any]:
    """Get a mock calendar list response."""
    return {
        "kind": "calendar#calendarList",
        "items": [
            get_mock_calendar("primary", "My Calendar", True),
            get_mock_calendar("work@example.com", "Work Calendar", False),
            get_mock_calendar("personal@example.com", "Personal", False),
        ],
    }


def get_mock_events_response(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap events in a Google Calendar API response format."""
    return {
        "kind": "calendar#events",
        "items": events,
        "summary": "Primary Calendar",
        "updated": datetime.utcnow().isoformat() + "Z",
        "timeZone": "America/Los_Angeles",
    }


def get_workday_events() -> list[dict[str, Any]]:
    """Get a realistic set of workday events."""
    base_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    return [
        get_mock_event(
            "Morning Standup",
            base_date,
            30,
            event_id="standup_1",
            description="Daily team sync",
        ),
        get_mock_event(
            "Deep Work Block",
            base_date + timedelta(hours=1),
            120,
            event_id="deep_work_1",
            extendedProperties={
                "private": {"thanos_created": "true", "task_id": "task_123"}
            },
        ),
        get_mock_event(
            "Lunch",
            base_date + timedelta(hours=3, minutes=30),
            60,
            event_id="lunch_1",
            transparency="transparent",  # Free/busy status
        ),
        get_mock_event(
            "Client Meeting",
            base_date + timedelta(hours=5),
            60,
            event_id="meeting_1",
            location="Conference Room A",
            attendees=[
                {"email": "client@example.com", "responseStatus": "accepted"},
                {"email": "me@example.com", "responseStatus": "accepted"},
            ],
        ),
        get_mock_event(
            "Code Review",
            base_date + timedelta(hours=6, minutes=30),
            45,
            event_id="review_1",
            status="tentative",
        ),
    ]


def get_conflicting_event() -> dict[str, Any]:
    """Get an event that would conflict with typical working hours."""
    conflict_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    return get_mock_event(
        "Conflicting Meeting",
        conflict_time,
        90,
        event_id="conflict_1",
    )


def get_all_day_event() -> dict[str, Any]:
    """Get an all-day event."""
    return get_mock_event(
        "Company Holiday",
        datetime.now(),
        all_day=True,
        event_id="holiday_1",
    )


def get_recurring_event() -> dict[str, Any]:
    """Get a recurring event."""
    start_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
    event = get_mock_event(
        "Weekly Team Meeting",
        start_time,
        60,
        event_id="recurring_1",
    )
    event["recurrence"] = ["RRULE:FREQ=WEEKLY;BYDAY=MO"]
    return event


def get_mock_filter_config() -> dict[str, Any]:
    """Get mock calendar filter configuration."""
    return {
        "enabled": True,
        "filter_mode": "exclude",
        "calendars": {
            "include": [],
            "exclude": ["spam@group.calendar.google.com"],
            "primary_only": False,
        },
        "event_types": {
            "include_all_day_events": True,
            "include_declined_events": False,
            "include_cancelled_events": False,
            "include_tentative_events": True,
        },
        "summary_patterns": {
            "exclude": ["^\\[SPAM\\]", "(?i)canceled"],
            "include": [],
            "case_sensitive": False,
        },
        "attendees": {
            "exclude_emails": ["spammer@example.com"],
            "include_emails": [],
            "exclude_if_organizer": [],
            "exclude_if_not_organizer": False,
            "min_attendees": None,
            "max_attendees": None,
        },
        "description_patterns": {"exclude": [], "include": [], "case_sensitive": False},
        "time_filters": {
            "exclude_before_hour": None,
            "exclude_after_hour": None,
            "min_duration_minutes": None,
            "max_duration_minutes": None,
            "exclude_weekends": False,
        },
        "metadata_filters": {
            "exclude_by_color": [],
            "include_by_color": [],
            "exclude_recurring": False,
            "exclude_private": False,
            "thanos_created_only": False,
        },
        "location_filters": {
            "exclude_locations": [],
            "include_locations": [],
            "exclude_virtual_only": False,
            "exclude_in_person_only": False,
        },
        "advanced": {
            "apply_filters_to_briefing": True,
            "apply_filters_to_conflict_detection": False,
            "apply_filters_to_free_slots": True,
        },
    }


def get_mock_free_slots() -> list[dict[str, Any]]:
    """Get mock free time slots."""
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    return [
        {
            "start": base.isoformat(),
            "end": (base + timedelta(hours=1)).isoformat(),
            "duration_minutes": 60,
        },
        {
            "start": (base + timedelta(hours=2)).isoformat(),
            "end": (base + timedelta(hours=4)).isoformat(),
            "duration_minutes": 120,
        },
        {
            "start": (base + timedelta(hours=6)).isoformat(),
            "end": (base + timedelta(hours=8)).isoformat(),
            "duration_minutes": 120,
        },
    ]


def get_mock_availability_response() -> dict[str, Any]:
    """Get mock availability analysis response."""
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_minutes": 480,  # 8 hours
        "busy_minutes": 180,  # 3 hours
        "free_minutes": 300,  # 5 hours
        "busy_percentage": 37.5,
        "free_percentage": 62.5,
        "event_count": 4,
        "longest_free_block_minutes": 120,
        "fragmentation_score": 0.3,
        "working_hours": {"start": "09:00", "end": "17:00"},
        "events": [],
    }


def get_mock_task_data() -> dict[str, Any]:
    """Get mock task data for time-blocking."""
    return {
        "id": "task_456",
        "title": "Implement feature X",
        "description": "Add new calendar integration feature",
        "estimated_duration_minutes": 90,
        "priority": "high",
        "project": "Thanos",
    }


def get_mock_http_error(status_code: int = 403, reason: str = "Forbidden") -> dict[str, Any]:
    """Get mock HTTP error response."""
    return {
        "error": {
            "code": status_code,
            "message": reason,
            "errors": [
                {
                    "message": reason,
                    "domain": "global",
                    "reason": "forbidden",
                }
            ],
        }
    }


def get_mock_created_event_response() -> dict[str, Any]:
    """Get mock response for successfully created event."""
    now = datetime.now()
    event = get_mock_event(
        "New Event",
        now,
        60,
        event_id="new_event_123",
    )
    event.update({
        "created": (now - timedelta(seconds=1)).isoformat() + "Z",
        "updated": now.isoformat() + "Z",
        "creator": {"email": "user@example.com"},
        "organizer": {"email": "user@example.com"},
        "htmlLink": "https://calendar.google.com/calendar/event?eid=abc123",
    })
    return event
