"""
Calendar Event Filtering Logic.
Handles filtering of calendar events based on configuration.
"""

import json
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def load_filter_config(config_file: str = "config/calendar_filters.json") -> Dict[str, Any]:
    """
    Load calendar filter configuration.

    Returns:
        Dictionary containing filter configuration. Returns default config if file doesn't exist.
    """
    filters_path = Path(config_file)

    # Return default config if file doesn't exist
    if not filters_path.exists():
        return {
            "enabled": False,
            "filter_mode": "exclude",
            "calendars": {"include": [], "exclude": [], "primary_only": False},
            "event_types": {
                "include_all_day_events": True,
                "include_declined_events": False,
                "include_cancelled_events": False,
                "include_tentative_events": True,
            },
            "summary_patterns": {"exclude": [], "include": [], "case_sensitive": False},
            "attendees": {
                "exclude_emails": [],
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

    try:
        with open(filters_path, "r") as f:
            return json.load(f)
    except Exception:
        # Return default config if file is invalid
        return {"enabled": False}


def apply_event_filters(
    events: List[Dict[str, Any]], 
    filter_context: str = "briefing", 
    calendar_id: str = "primary",
    config_file: str = "config/calendar_filters.json"
) -> List[Dict[str, Any]]:
    """
    Apply filtering rules to a list of events.

    Args:
        events: List of formatted event dictionaries
        filter_context: Context for filtering ('briefing', 'conflict_detection', 'free_slots')
        calendar_id: Calendar ID for calendar-level filtering
        config_file: Path to config file

    Returns:
        Filtered list of events
    """
    # Load filter configuration
    filters = load_filter_config(config_file)

    # Check if filters are enabled
    if not filters.get("enabled", False):
        return events

    # Check if filters apply to this context
    advanced = filters.get("advanced", {})
    context_map = {
        "briefing": "apply_filters_to_briefing",
        "conflict_detection": "apply_filters_to_conflict_detection",
        "free_slots": "apply_filters_to_free_slots",
    }
    context_setting = context_map.get(filter_context, "apply_filters_to_briefing")
    if not advanced.get(context_setting, True):
        return events

    filtered_events = []

    for event in events:
        # Skip if event should be excluded
        if should_exclude_event(event, filters, calendar_id):
            continue

        filtered_events.append(event)

    return filtered_events


def should_exclude_event(event: Dict[str, Any], filters: Dict[str, Any], calendar_id: str = "primary") -> bool:
    """
    Determine if an event should be excluded based on filter rules.

    Args:
        event: Formatted event dictionary
        filters: Filter configuration
        calendar_id: Calendar ID that this event belongs to

    Returns:
        True if event should be excluded, False if it should be included
    """
    # Calendar-level filters
    calendars_config = filters.get("calendars", {})

    # Check if only primary calendar should be included
    if calendars_config.get("primary_only", False):
        if calendar_id != "primary":
            return True

    # Check calendar include list (if specified, only these calendars are allowed)
    calendar_include = calendars_config.get("include", [])
    if calendar_include:
        if calendar_id not in calendar_include:
            return True

    # Check calendar exclude list
    calendar_exclude = calendars_config.get("exclude", [])
    if calendar_id in calendar_exclude:
        return True

    # Event type filters
    event_types = filters.get("event_types", {})

    # Check all-day events
    if event.get("is_all_day") and not event_types.get("include_all_day_events", True):
        return True

    # Check cancelled events
    if event.get("status") == "cancelled" and not event_types.get("include_cancelled_events", False):
        return True

    # Check tentative events
    if event.get("status") == "tentative" and not event_types.get("include_tentative_events", True):
        return True

    # Check declined events (user's response status)
    if not event_types.get("include_declined_events", False):
        for attendee in event.get("attendees", []):
            if attendee.get("self", False) and attendee.get("response_status") == "declined":
                return True

    # Check special event type filters (focus_time, out_of_office, working_location, etc.)
    event_type_filters = event_types.get("event_type_filters", {})
    event_type = event.get("event_type")  # Google Calendar API eventType field

    # Process each event type filter
    for filter_name, filter_config in event_type_filters.items():
        if not filter_config.get("enabled", True):
            continue

        action = filter_config.get("action", "include")  # "include" or "exclude"

        # Check if this event matches the filter type
        is_match = False
        if event_type == filter_name:
            # Direct match with Google Calendar event type
            is_match = True
        elif filter_name == "focus_time" and event_type in ["focusTime", "focus_time"]:
            is_match = True
        elif filter_name == "out_of_office" and event_type in ["outOfOffice", "out_of_office"]:
            is_match = True
        elif filter_name == "working_location" and event_type in ["workingLocation", "working_location"]:
            is_match = True

        # Apply the filter action
        if is_match:
            if action == "exclude":
                return True
            # If action is "include", we continue processing other filters
            # The event will only be excluded if it fails other filters

    # Summary pattern filters
    summary_patterns = filters.get("summary_patterns", {})
    case_sensitive = summary_patterns.get("case_sensitive", False)
    event_summary = event.get("summary", "")

    # Check exclude patterns
    for pattern in summary_patterns.get("exclude", []):
        flags = 0 if case_sensitive else re.IGNORECASE
        if re.search(pattern, event_summary, flags):
            return True

    # Check include patterns (if any specified)
    include_patterns = summary_patterns.get("include", [])
    if include_patterns:
        matched = False
        for pattern in include_patterns:
            flags = 0 if case_sensitive else re.IGNORECASE
            if re.search(pattern, event_summary, flags):
                matched = True
                break
        if not matched:
            return True

    # Description pattern filters
    description_patterns = filters.get("description_patterns", {})
    case_sensitive_desc = description_patterns.get("case_sensitive", False)
    event_description = event.get("description", "") or ""

    # Check exclude patterns in description
    for pattern in description_patterns.get("exclude", []):
        flags = 0 if case_sensitive_desc else re.IGNORECASE
        if re.search(pattern, event_description, flags):
            return True

    # Check include patterns in description (if any specified)
    include_desc_patterns = description_patterns.get("include", [])
    if include_desc_patterns:
        matched = False
        for pattern in include_desc_patterns:
            flags = 0 if case_sensitive_desc else re.IGNORECASE
            if re.search(pattern, event_description, flags):
                matched = True
                break
        if not matched:
            return True

    # Attendee filters
    attendees_config = filters.get("attendees", {})
    event_attendees = event.get("attendees", [])
    attendee_count = len(event_attendees)

    # Check attendee count limits
    min_attendees = attendees_config.get("min_attendees")
    if min_attendees is not None and attendee_count < min_attendees:
        return True

    max_attendees = attendees_config.get("max_attendees")
    if max_attendees is not None and attendee_count > max_attendees:
        return True

    # Check excluded attendee emails
    exclude_emails = attendees_config.get("exclude_emails", [])
    for attendee in event_attendees:
        if attendee.get("email") in exclude_emails:
            return True

    # Check included attendee emails (if any specified)
    include_emails = attendees_config.get("include_emails", [])
    if include_emails:
        matched = False
        for attendee in event_attendees:
            if attendee.get("email") in include_emails:
                matched = True
                break
        if not matched:
            return True

    # Check organizer filters
    organizer_email = event.get("organizer", {}).get("email")
    exclude_if_organizer = attendees_config.get("exclude_if_organizer", [])
    if organizer_email in exclude_if_organizer:
        return True

    # Exclude if not organizer (when enabled)
    if attendees_config.get("exclude_if_not_organizer", False):
        if not event.get("organizer", {}).get("is_self", False):
            return True

    # Time filters
    time_filters = filters.get("time_filters", {})

    # Check time of day filters (for non-all-day events)
    if not event.get("is_all_day"):
        start_time = event.get("start")
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

                exclude_before = time_filters.get("exclude_before_hour")
                if exclude_before is not None and start_dt.hour < exclude_before:
                    return True

                exclude_after = time_filters.get("exclude_after_hour")
                if exclude_after is not None and start_dt.hour >= exclude_after:
                    return True

                # Check weekend exclusion
                if time_filters.get("exclude_weekends", False):
                    if start_dt.weekday() >= 5:  # Saturday=5, Sunday=6
                        return True

                # Check duration filters
                end_time = event.get("end")
                if end_time:
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    duration_minutes = (end_dt - start_dt).total_seconds() / 60

                    min_duration = time_filters.get("min_duration_minutes")
                    if min_duration is not None and duration_minutes < min_duration:
                        return True

                    max_duration = time_filters.get("max_duration_minutes")
                    if max_duration is not None and duration_minutes > max_duration:
                        return True

            except (ValueError, TypeError):
                # Skip time filtering if time parsing fails
                pass

    # Metadata filters
    metadata_filters = filters.get("metadata_filters", {})

    # Check color filters
    event_color = event.get("color_id")
    exclude_colors = metadata_filters.get("exclude_by_color", [])
    if event_color and str(event_color) in [str(c) for c in exclude_colors]:
        return True

    include_colors = metadata_filters.get("include_by_color", [])
    if include_colors:
        if not event_color or str(event_color) not in [str(c) for c in include_colors]:
            return True

    # Check recurring event filter
    if metadata_filters.get("exclude_recurring", False):
        if event.get("is_recurring", False):
            return True

    # Check private event filter
    if metadata_filters.get("exclude_private", False):
        if event.get("visibility") in ["private", "confidential"]:
            return True

    # Check Thanos-created filter
    if metadata_filters.get("thanos_created_only", False):
        # Check for Thanos metadata in extended properties (to be implemented)
        pass

    # Location filters
    location_filters = filters.get("location_filters", {})
    event_location = event.get("location", "") or ""

    # Check excluded locations
    exclude_locations = location_filters.get("exclude_locations", [])
    for excluded_loc in exclude_locations:
        if excluded_loc.lower() in event_location.lower():
            return True

    # Check included locations (if any specified)
    include_locations = location_filters.get("include_locations", [])
    if include_locations:
        matched = False
        for included_loc in include_locations:
            if included_loc.lower() in event_location.lower():
                matched = True
                break
        if not matched:
            return True

    # Check virtual/in-person filters
    has_conference_data = bool(event.get("conference_data"))
    if location_filters.get("exclude_virtual_only", False) and has_conference_data and not event_location:
        return True

    if location_filters.get("exclude_in_person_only", False) and event_location and not has_conference_data:
        return True

    # If we made it here, the event passes all filters
    return False
