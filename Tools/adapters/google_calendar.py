"""
Google Calendar API adapter for Thanos.

Provides OAuth 2.0 authentication and access to Google Calendar API
for calendar integration, event management, and scheduling intelligence.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base import BaseAdapter, ToolResult


class GoogleCalendarAdapter(BaseAdapter):
    """
    Direct adapter for Google Calendar API with OAuth 2.0 authentication.

    Security Features:
    - OAuth credentials stored in State/calendar_credentials.json with 0600 permissions
    - File is automatically gitignored to prevent accidental commits
    - Supports environment variable fallback for client_id, client_secret, redirect_uri
    - Automatic token refresh with secure re-storage

    Environment Variables:
    - GOOGLE_CALENDAR_CLIENT_ID: OAuth 2.0 client ID from Google Cloud Console
    - GOOGLE_CALENDAR_CLIENT_SECRET: OAuth 2.0 client secret
    - GOOGLE_CALENDAR_REDIRECT_URI: OAuth redirect URI (optional, defaults to localhost)
    """

    # OAuth 2.0 scopes for Google Calendar
    SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",  # Read calendar events
        "https://www.googleapis.com/auth/calendar.events",  # Manage calendar events
    ]

    # Credentials storage location
    CREDENTIALS_FILE = "State/calendar_credentials.json"

    # Filter configuration location
    FILTERS_CONFIG_FILE = "config/calendar_filters.json"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        """
        Initialize the Google Calendar adapter.

        Args:
            client_id: OAuth 2.0 client ID. Falls back to GOOGLE_CALENDAR_CLIENT_ID env var.
            client_secret: OAuth 2.0 client secret. Falls back to GOOGLE_CALENDAR_CLIENT_SECRET env var.
            redirect_uri: OAuth redirect URI. Falls back to GOOGLE_CALENDAR_REDIRECT_URI env var
                         or defaults to http://localhost:8080/oauth2callback
        """
        self.client_id = client_id or os.environ.get("GOOGLE_CALENDAR_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("GOOGLE_CALENDAR_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.environ.get(
            "GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:8080/oauth2callback"
        )

        self._credentials: Optional[Credentials] = None
        self._service = None
        self._pending_state: Optional[str] = None  # Track OAuth state for validation

        # Load existing credentials if available
        self._load_credentials()

    @property
    def name(self) -> str:
        """Adapter identifier used for routing."""
        return "google_calendar"

    def _get_credentials_path(self) -> Path:
        """Get the full path to the credentials file."""
        return Path(self.CREDENTIALS_FILE)

    def _load_credentials(self) -> None:
        """Load OAuth credentials from storage if they exist."""
        creds_path = self._get_credentials_path()

        if not creds_path.exists():
            return

        try:
            self._credentials = Credentials.from_authorized_user_file(
                str(creds_path), self.SCOPES
            )
        except Exception:
            # Credentials file is corrupted or invalid
            # We'll need to re-authenticate
            # Silently ignore and allow re-authentication
            pass

    def _save_credentials(self) -> None:
        """
        Save OAuth credentials to storage with secure permissions.

        Security measures:
        - Credentials stored in State/calendar_credentials.json
        - File permissions set to 0600 (owner read/write only)
        - File is gitignored via State/.gitignore
        - For production deployments, consider additional encryption at rest

        The credentials file contains OAuth 2.0 tokens (access token, refresh token)
        which must be protected from unauthorized access.
        """
        if not self._credentials:
            return

        creds_path = self._get_credentials_path()

        # Ensure the State directory exists
        creds_path.parent.mkdir(parents=True, exist_ok=True)

        # Save credentials to file
        with open(creds_path, "w") as f:
            f.write(self._credentials.to_json())

        # Set restrictive permissions (0600 - owner read/write only)
        # This prevents other users on the system from reading the credentials
        os.chmod(creds_path, 0o600)

    def _refresh_credentials(self) -> bool:
        """
        Refresh expired credentials if possible.

        Returns:
            True if credentials were refreshed successfully, False otherwise.
        """
        if not self._credentials:
            return False

        if not self._credentials.expired:
            return True

        if not self._credentials.refresh_token:
            return False

        try:
            self._credentials.refresh(Request())
            self._save_credentials()
            # Clear cached service to use refreshed credentials
            self._service = None
            return True
        except Exception:
            # Token refresh failed - credentials may have been revoked
            return False

    def _load_filter_config(self) -> dict[str, Any]:
        """
        Load calendar filter configuration from config/calendar_filters.json.

        Returns:
            Dictionary containing filter configuration. Returns default config if file doesn't exist.
        """
        filters_path = Path(self.FILTERS_CONFIG_FILE)

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

    def _apply_event_filters(
        self, events: list[dict[str, Any]], filter_context: str = "briefing", calendar_id: str = "primary"
    ) -> list[dict[str, Any]]:
        """
        Apply filtering rules to a list of events based on calendar_filters.json configuration.

        Args:
            events: List of formatted event dictionaries
            filter_context: Context for filtering ('briefing', 'conflict_detection', 'free_slots')
            calendar_id: Calendar ID for calendar-level filtering

        Returns:
            Filtered list of events
        """
        # Load filter configuration
        filters = self._load_filter_config()

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
            if self._should_exclude_event(event, filters, calendar_id):
                continue

            filtered_events.append(event)

        return filtered_events

    def _should_exclude_event(self, event: dict[str, Any], filters: dict[str, Any], calendar_id: str = "primary") -> bool:
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
            # For now, we'll skip this filter as extended properties aren't in the event data yet
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

    def _get_service(self):
        """
        Get or create the Google Calendar API service.

        Returns:
            Google Calendar API service instance.

        Raises:
            ValueError: If credentials are not configured or have expired.
        """
        # Try to refresh credentials if they exist but are expired
        if self._credentials and self._credentials.expired:
            if not self._refresh_credentials():
                raise ValueError(
                    "Google Calendar credentials have expired and cannot be refreshed. "
                    "Please re-authenticate using the authorize tool."
                )

        # Check if we have valid credentials
        if not self._credentials or not self._credentials.valid:
            raise ValueError(
                "No valid Google Calendar credentials found. "
                "Please authenticate using the authorize tool first."
            )

        # Build or return existing service
        if self._service is None:
            self._service = build("calendar", "v3", credentials=self._credentials)

        return self._service

    def is_authenticated(self) -> bool:
        """
        Check if the adapter has valid credentials.

        Returns:
            True if authenticated and credentials are valid, False otherwise.
        """
        if not self._credentials:
            return False

        if self._credentials.expired:
            return self._refresh_credentials()

        return self._credentials.valid

    def revoke_credentials(self) -> ToolResult:
        """
        Revoke and clear stored credentials.

        This will:
        1. Revoke the access token with Google (if possible)
        2. Delete the stored credentials file
        3. Clear in-memory credentials

        Returns:
            ToolResult indicating success or failure
        """
        revoked = False
        errors = []

        # Try to revoke the token with Google
        if self._credentials and self._credentials.token:
            try:
                import httpx
                response = httpx.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": self._credentials.token},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
                if response.status_code == 200:
                    revoked = True
            except Exception as e:
                errors.append(f"Failed to revoke token with Google: {str(e)}")

        # Delete credentials file
        creds_path = self._get_credentials_path()
        if creds_path.exists():
            try:
                creds_path.unlink()
            except Exception as e:
                errors.append(f"Failed to delete credentials file: {str(e)}")

        # Clear in-memory credentials
        self._credentials = None
        self._service = None
        self._pending_state = None

        if errors:
            return ToolResult.ok(
                {
                    "status": "partially_revoked",
                    "revoked_with_google": revoked,
                    "local_credentials_cleared": True,
                    "warnings": errors,
                }
            )
        else:
            return ToolResult.ok(
                {
                    "status": "revoked",
                    "revoked_with_google": revoked,
                    "local_credentials_cleared": True,
                    "message": "Google Calendar credentials have been revoked and cleared.",
                }
            )

    def get_authorization_url(self) -> tuple[str, str]:
        """
        Generate OAuth 2.0 authorization URL.

        Returns:
            Tuple of (authorization_url, state) for the OAuth flow.

        Raises:
            ValueError: If client_id or client_secret are not configured.
        """
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Google Calendar OAuth credentials not configured. "
                "Set GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET environment variables."
            )

        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )

        authorization_url, state = flow.authorization_url(
            access_type="offline",  # Request refresh token
            include_granted_scopes="true",
            prompt="consent",  # Force consent screen to get refresh token
        )

        # Store state for validation during callback
        self._pending_state = state

        return authorization_url, state

    def complete_authorization(self, authorization_response: str, state: str) -> ToolResult:
        """
        Complete OAuth 2.0 authorization flow.

        Args:
            authorization_response: The full callback URL with auth code
            state: The state parameter from get_authorization_url

        Returns:
            ToolResult indicating success or failure
        """
        if not self.client_id or not self.client_secret:
            return ToolResult.fail(
                "Google Calendar OAuth credentials not configured. "
                "Set GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET environment variables."
            )

        # Validate state parameter to prevent CSRF attacks
        if self._pending_state and state != self._pending_state:
            return ToolResult.fail(
                "Invalid state parameter. This may indicate a security issue. "
                "Please restart the authorization flow."
            )

        try:
            # Create OAuth flow
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri],
                    }
                },
                scopes=self.SCOPES,
                state=state,
                redirect_uri=self.redirect_uri,
            )

            # Exchange authorization code for credentials
            flow.fetch_token(authorization_response=authorization_response)

            # Store credentials
            self._credentials = flow.credentials
            self._save_credentials()

            # Clear any cached service to force rebuild with new credentials
            self._service = None
            self._pending_state = None  # Clear pending state after successful auth

            return ToolResult.ok(
                {
                    "status": "authenticated",
                    "scopes": self.SCOPES,
                    "expires_at": (
                        self._credentials.expiry.isoformat()
                        if self._credentials.expiry
                        else None
                    ),
                    "has_refresh_token": bool(self._credentials.refresh_token),
                }
            )

        except Exception as e:
            self._pending_state = None  # Clear pending state on error
            return ToolResult.fail(f"Authorization failed: {str(e)}")

    def list_tools(self) -> list[dict[str, Any]]:
        """
        Return list of available Google Calendar tools.

        Returns:
            List of tool schemas with names, descriptions, and parameters.
        """
        return [
            {
                "name": "authorize",
                "description": "Start OAuth 2.0 authorization flow to connect Google Calendar",
                "parameters": {},
            },
            {
                "name": "complete_auth",
                "description": "Complete OAuth 2.0 authorization with callback URL",
                "parameters": {
                    "authorization_response": {
                        "type": "string",
                        "description": "Full callback URL from OAuth redirect",
                        "required": True,
                    },
                    "state": {
                        "type": "string",
                        "description": "State parameter from authorization URL",
                        "required": True,
                    },
                },
            },
            {
                "name": "check_auth",
                "description": "Check if Google Calendar is authenticated and credentials are valid",
                "parameters": {},
            },
            {
                "name": "revoke_auth",
                "description": "Revoke and clear Google Calendar credentials. Requires re-authentication to use calendar features again.",
                "parameters": {},
            },
            {
                "name": "list_calendars",
                "description": "List all user's calendars with metadata (name, ID, primary status, access role)",
                "parameters": {
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Include hidden calendars in results. Defaults to False.",
                        "required": False,
                    },
                    "min_access_role": {
                        "type": "string",
                        "description": "Filter by minimum access role: 'freeBusyReader', 'reader', 'writer', 'owner'. Defaults to None (all roles).",
                        "required": False,
                    },
                    "primary_only": {
                        "type": "boolean",
                        "description": "Return only the primary calendar. Defaults to False.",
                        "required": False,
                    },
                },
            },
            {
                "name": "get_events",
                "description": "Fetch events for a date range. Supports all-day vs timed events, recurring events, event status, attendees, and location.",
                "parameters": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Required.",
                        "required": True,
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Required.",
                        "required": True,
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID to fetch events from. Use 'primary' for primary calendar. Defaults to 'primary'.",
                        "required": False,
                    },
                    "include_cancelled": {
                        "type": "boolean",
                        "description": "Include cancelled events in results. Defaults to False.",
                        "required": False,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to return. Defaults to 250.",
                        "required": False,
                    },
                    "single_events": {
                        "type": "boolean",
                        "description": "Expand recurring events into individual instances. Defaults to True.",
                        "required": False,
                    },
                },
            },
            {
                "name": "get_today_events",
                "description": "Convenience tool to fetch today's events with intelligent filtering. Excludes declined events, handles timezone correctly, sorts by start time, and calculates free/busy status.",
                "parameters": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID to fetch events from. Use 'primary' for primary calendar. Defaults to 'primary'.",
                        "required": False,
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for 'today' calculation (e.g., 'America/New_York', 'UTC'). Defaults to system timezone.",
                        "required": False,
                    },
                },
            },
            {
                "name": "find_free_slots",
                "description": "Find available time slots within a date range. Considers working hours, minimum slot duration, buffer time between events, and calendar preferences. Useful for scheduling tasks or finding meeting times.",
                "parameters": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Required.",
                        "required": True,
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Required.",
                        "required": True,
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID to check for conflicts. Use 'primary' for primary calendar. Defaults to 'primary'.",
                        "required": False,
                    },
                    "min_duration_minutes": {
                        "type": "integer",
                        "description": "Minimum slot duration in minutes to consider as available. Defaults to 30.",
                        "required": False,
                    },
                    "working_hours_start": {
                        "type": "integer",
                        "description": "Start of working hours (0-23). If specified, only slots during working hours are returned. Defaults to None (all day).",
                        "required": False,
                    },
                    "working_hours_end": {
                        "type": "integer",
                        "description": "End of working hours (0-23). If specified, only slots during working hours are returned. Defaults to None (all day).",
                        "required": False,
                    },
                    "buffer_minutes": {
                        "type": "integer",
                        "description": "Buffer time in minutes to add before and after each event. Defaults to 0.",
                        "required": False,
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for working hours and slot times (e.g., 'America/New_York', 'UTC'). Defaults to system timezone.",
                        "required": False,
                    },
                    "exclude_weekends": {
                        "type": "boolean",
                        "description": "Exclude Saturday and Sunday from free slots. Defaults to False.",
                        "required": False,
                    },
                },
            },
            {
                "name": "check_conflicts",
                "description": "Check if a proposed time slot conflicts with existing calendar events. Includes support for tentative events, travel time buffer, and flexible boundaries. Useful for scheduling validation and double-booking prevention.",
                "parameters": {
                    "start_time": {
                        "type": "string",
                        "description": "Start time of proposed slot in ISO 8601 format (YYYY-MM-DDTHH:MM:SS). Required.",
                        "required": True,
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time of proposed slot in ISO 8601 format (YYYY-MM-DDTHH:MM:SS). Required.",
                        "required": True,
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID to check for conflicts. Use 'primary' for primary calendar. Defaults to 'primary'.",
                        "required": False,
                    },
                    "buffer_minutes": {
                        "type": "integer",
                        "description": "Buffer time in minutes to add before and after existing events (travel time). Defaults to 0.",
                        "required": False,
                    },
                    "consider_tentative": {
                        "type": "boolean",
                        "description": "Include tentative events when checking for conflicts. Defaults to True.",
                        "required": False,
                    },
                    "flexibility_minutes": {
                        "type": "integer",
                        "description": "Allow this many minutes of overlap tolerance (flexible boundaries). Defaults to 0.",
                        "required": False,
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for time calculations (e.g., 'America/New_York', 'UTC'). Defaults to system timezone.",
                        "required": False,
                    },
                },
            },
            {
                "name": "get_availability",
                "description": "Analyze calendar availability and return daily/weekly summary. Provides metrics including total free time, longest continuous block, fragmentation score, busy/free ratio, and scheduling insights. Useful for understanding workload distribution and finding optimal scheduling windows.",
                "parameters": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Required.",
                        "required": True,
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Required.",
                        "required": True,
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID to analyze. Use 'primary' for primary calendar. Defaults to 'primary'.",
                        "required": False,
                    },
                    "working_hours_start": {
                        "type": "integer",
                        "description": "Start of working hours (0-23) to limit analysis. If specified, only hours during working time are counted. Defaults to None (all day).",
                        "required": False,
                    },
                    "working_hours_end": {
                        "type": "integer",
                        "description": "End of working hours (0-23) to limit analysis. If specified, only hours during working time are counted. Defaults to None (all day).",
                        "required": False,
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for availability calculations (e.g., 'America/New_York', 'UTC'). Defaults to system timezone.",
                        "required": False,
                    },
                    "exclude_weekends": {
                        "type": "boolean",
                        "description": "Exclude Saturday and Sunday from availability analysis. Defaults to False.",
                        "required": False,
                    },
                    "min_slot_duration_minutes": {
                        "type": "integer",
                        "description": "Minimum duration in minutes to count as a usable free slot (affects fragmentation calculation). Defaults to 15.",
                        "required": False,
                    },
                },
            },
            {
                "name": "create_event",
                "description": "Create a new calendar event. Supports summary, description, start/end time, all-day events, location, attendees, reminders, and color coding. Returns the created event details including event ID and link.",
                "parameters": {
                    "summary": {
                        "type": "string",
                        "description": "Event title/summary. Required.",
                        "required": True,
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS) for timed events, or (YYYY-MM-DD) for all-day events. Required.",
                        "required": True,
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS) for timed events, or (YYYY-MM-DD) for all-day events. Required.",
                        "required": True,
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID to create event in. Use 'primary' for primary calendar. Defaults to 'primary'.",
                        "required": False,
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description/notes. Defaults to empty string.",
                        "required": False,
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location (address, meeting room, virtual link, etc.). Defaults to empty string.",
                        "required": False,
                    },
                    "attendees": {
                        "type": "array",
                        "description": "List of attendee email addresses. Each item should be a string email. Defaults to empty list.",
                        "required": False,
                    },
                    "color_id": {
                        "type": "string",
                        "description": "Calendar color ID (1-11). See Google Calendar API docs for color meanings. Defaults to None (calendar default color).",
                        "required": False,
                    },
                    "reminders": {
                        "type": "object",
                        "description": "Reminder settings. Format: {'useDefault': False, 'overrides': [{'method': 'email'|'popup', 'minutes': int}]}. If not specified, uses calendar default reminders.",
                        "required": False,
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for event times (e.g., 'America/New_York', 'UTC'). Only used for timed events. Defaults to system timezone.",
                        "required": False,
                    },
                    "transparency": {
                        "type": "string",
                        "description": "Event transparency: 'opaque' (busy) or 'transparent' (free). Defaults to 'opaque'.",
                        "required": False,
                    },
                    "visibility": {
                        "type": "string",
                        "description": "Event visibility: 'default', 'public', 'private', or 'confidential'. Defaults to 'default'.",
                        "required": False,
                    },
                },
            },
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """
        Execute a Google Calendar tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool parameters

        Returns:
            ToolResult with success status and data/error
        """
        try:
            if tool_name == "authorize":
                return await self._tool_authorize()
            elif tool_name == "complete_auth":
                return await self._tool_complete_auth(arguments)
            elif tool_name == "check_auth":
                return await self._tool_check_auth()
            elif tool_name == "revoke_auth":
                return await self._tool_revoke_auth()
            elif tool_name == "list_calendars":
                return await self._tool_list_calendars(arguments)
            elif tool_name == "get_events":
                return await self._tool_get_events(arguments)
            elif tool_name == "get_today_events":
                return await self._tool_get_today_events(arguments)
            elif tool_name == "find_free_slots":
                return await self._tool_find_free_slots(arguments)
            elif tool_name == "check_conflicts":
                return await self._tool_check_conflicts(arguments)
            elif tool_name == "get_availability":
                return await self._tool_get_availability(arguments)
            elif tool_name == "create_event":
                return await self._tool_create_event(arguments)
            elif tool_name == "block_time_for_task":
                return await self._tool_block_time_for_task(arguments)
            else:
                return ToolResult.fail(f"Unknown tool: {tool_name}")

        except HttpError as e:
            return ToolResult.fail(f"Google Calendar API error: {e}")
        except Exception as e:
            return ToolResult.fail(f"Error executing {tool_name}: {e}")

    async def _tool_authorize(self) -> ToolResult:
        """Tool: Start OAuth 2.0 authorization flow."""
        try:
            auth_url, state = self.get_authorization_url()
            return ToolResult.ok(
                {
                    "authorization_url": auth_url,
                    "state": state,
                    "instructions": (
                        "1. Open the authorization_url in your browser\n"
                        "2. Sign in and grant permissions\n"
                        "3. You'll be redirected to a URL - copy the entire URL\n"
                        "4. Call complete_auth with the URL and state parameter"
                    ),
                }
            )
        except ValueError as e:
            return ToolResult.fail(str(e))

    async def _tool_complete_auth(self, arguments: dict[str, Any]) -> ToolResult:
        """Tool: Complete OAuth 2.0 authorization."""
        authorization_response = arguments.get("authorization_response")
        state = arguments.get("state")

        if not authorization_response:
            return ToolResult.fail("Missing required parameter: authorization_response")
        if not state:
            return ToolResult.fail("Missing required parameter: state")

        return self.complete_authorization(authorization_response, state)

    async def _tool_check_auth(self) -> ToolResult:
        """Tool: Check authentication status."""
        is_authed = self.is_authenticated()

        if is_authed:
            return ToolResult.ok(
                {
                    "authenticated": True,
                    "expires_at": (
                        self._credentials.expiry.isoformat()
                        if self._credentials and self._credentials.expiry
                        else None
                    ),
                    "scopes": self.SCOPES,
                }
            )
        else:
            return ToolResult.ok(
                {
                    "authenticated": False,
                    "message": "Not authenticated. Use the 'authorize' tool to connect Google Calendar.",
                }
            )

    async def _tool_revoke_auth(self) -> ToolResult:
        """Tool: Revoke credentials."""
        return self.revoke_credentials()

    async def _tool_list_calendars(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Tool: List all user's calendars with metadata.

        Args:
            arguments: Tool parameters including optional filters:
                - show_hidden: Include hidden calendars (default: False)
                - min_access_role: Minimum access role filter (default: None)
                - primary_only: Return only primary calendar (default: False)

        Returns:
            ToolResult containing list of calendars with metadata
        """
        try:
            # Get authenticated service
            service = self._get_service()

            # Extract parameters with defaults
            show_hidden = arguments.get("show_hidden", False)
            min_access_role = arguments.get("min_access_role")
            primary_only = arguments.get("primary_only", False)

            # Define access role hierarchy for filtering
            access_role_hierarchy = {
                "freeBusyReader": 0,
                "reader": 1,
                "writer": 2,
                "owner": 3,
            }

            # Fetch all calendars from Google Calendar API
            calendar_list_result = service.calendarList().list().execute()
            calendars = calendar_list_result.get("items", [])

            # Apply filters
            filtered_calendars = []
            for calendar in calendars:
                # Filter by hidden status
                if not show_hidden and calendar.get("hidden", False):
                    continue

                # Filter by primary status
                if primary_only and not calendar.get("primary", False):
                    continue

                # Filter by minimum access role
                if min_access_role:
                    calendar_role = calendar.get("accessRole", "")
                    if calendar_role not in access_role_hierarchy:
                        continue

                    min_role_level = access_role_hierarchy.get(min_access_role, 0)
                    calendar_role_level = access_role_hierarchy.get(calendar_role, 0)

                    if calendar_role_level < min_role_level:
                        continue

                # Extract relevant metadata
                calendar_data = {
                    "id": calendar.get("id"),
                    "summary": calendar.get("summary", ""),
                    "description": calendar.get("description"),
                    "primary": calendar.get("primary", False),
                    "access_role": calendar.get("accessRole", ""),
                    "selected": calendar.get("selected", False),
                    "background_color": calendar.get("backgroundColor"),
                    "foreground_color": calendar.get("foregroundColor"),
                    "time_zone": calendar.get("timeZone"),
                }

                filtered_calendars.append(calendar_data)

            # Sort calendars: primary first, then by summary
            filtered_calendars.sort(
                key=lambda c: (not c["primary"], c["summary"].lower())
            )

            return ToolResult.ok(
                {
                    "calendars": filtered_calendars,
                    "total_count": len(filtered_calendars),
                    "filters_applied": {
                        "show_hidden": show_hidden,
                        "min_access_role": min_access_role,
                        "primary_only": primary_only,
                    },
                }
            )

        except ValueError as e:
            # Handle authentication errors from _get_service()
            return ToolResult.fail(str(e))

    async def _tool_get_events(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Tool: Fetch events for a date range.

        Args:
            arguments: Tool parameters including:
                - start_date: Start date in ISO 8601 format (required)
                - end_date: End date in ISO 8601 format (required)
                - calendar_id: Calendar ID (default: 'primary')
                - include_cancelled: Include cancelled events (default: False)
                - max_results: Maximum number of events (default: 250)
                - single_events: Expand recurring events (default: True)

        Returns:
            ToolResult containing list of events with detailed information
        """
        try:
            # Get authenticated service
            service = self._get_service()

            # Extract and validate required parameters
            start_date_str = arguments.get("start_date")
            end_date_str = arguments.get("end_date")

            if not start_date_str:
                return ToolResult.fail("Missing required parameter: start_date")
            if not end_date_str:
                return ToolResult.fail("Missing required parameter: end_date")

            # Parse dates - support both date-only and datetime formats
            try:
                # Try parsing as datetime first
                if "T" in start_date_str:
                    start_datetime = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                else:
                    # Date only - start of day
                    start_datetime = datetime.fromisoformat(f"{start_date_str}T00:00:00")

                if "T" in end_date_str:
                    end_datetime = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                else:
                    # Date only - end of day
                    end_datetime = datetime.fromisoformat(f"{end_date_str}T23:59:59")

            except ValueError as e:
                return ToolResult.fail(f"Invalid date format: {str(e)}. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

            # Validate date range
            if end_datetime < start_datetime:
                return ToolResult.fail("end_date must be after start_date")

            # Extract optional parameters with defaults
            calendar_id = arguments.get("calendar_id", "primary")
            include_cancelled = arguments.get("include_cancelled", False)
            max_results = arguments.get("max_results", 250)
            single_events = arguments.get("single_events", True)

            # Build API request parameters
            # Convert to RFC3339 format required by Google Calendar API
            time_min = start_datetime.isoformat() + "Z" if not start_datetime.tzinfo else start_datetime.isoformat()
            time_max = end_datetime.isoformat() + "Z" if not end_datetime.tzinfo else end_datetime.isoformat()

            request_params = {
                "calendarId": calendar_id,
                "timeMin": time_min,
                "timeMax": time_max,
                "maxResults": max_results,
                "singleEvents": single_events,
                "orderBy": "startTime" if single_events else None,
            }

            # Remove None values
            request_params = {k: v for k, v in request_params.items() if v is not None}

            # Fetch events from Google Calendar API
            events_result = service.events().list(**request_params).execute()
            raw_events = events_result.get("items", [])

            # Process and format events
            formatted_events = []
            for event in raw_events:
                # Filter cancelled events if requested
                event_status = event.get("status", "confirmed")
                if not include_cancelled and event_status == "cancelled":
                    continue

                # Determine if event is all-day or timed
                start = event.get("start", {})
                end = event.get("end", {})

                is_all_day = "date" in start and "dateTime" not in start

                # Extract start and end times
                if is_all_day:
                    start_time = start.get("date")
                    end_time = end.get("date")
                else:
                    start_time = start.get("dateTime")
                    end_time = end.get("dateTime")

                # Extract attendees information
                attendees = []
                for attendee in event.get("attendees", []):
                    attendees.append({
                        "email": attendee.get("email"),
                        "display_name": attendee.get("displayName"),
                        "response_status": attendee.get("responseStatus"),  # accepted, declined, tentative, needsAction
                        "organizer": attendee.get("organizer", False),
                        "optional": attendee.get("optional", False),
                    })

                # Check if event is recurring
                is_recurring = "recurringEventId" in event or "recurrence" in event
                recurring_event_id = event.get("recurringEventId")
                recurrence_rules = event.get("recurrence", [])

                # Build formatted event data
                formatted_event = {
                    "id": event.get("id"),
                    "summary": event.get("summary", "(No title)"),
                    "description": event.get("description"),
                    "location": event.get("location"),
                    "start": start_time,
                    "end": end_time,
                    "start_timezone": start.get("timeZone"),
                    "end_timezone": end.get("timeZone"),
                    "is_all_day": is_all_day,
                    "status": event_status,  # confirmed, tentative, cancelled
                    "attendees": attendees,
                    "attendees_count": len(attendees),
                    "organizer": {
                        "email": event.get("organizer", {}).get("email"),
                        "display_name": event.get("organizer", {}).get("displayName"),
                        "is_self": event.get("organizer", {}).get("self", False),
                    },
                    "is_recurring": is_recurring,
                    "recurring_event_id": recurring_event_id,
                    "recurrence_rules": recurrence_rules,
                    "html_link": event.get("htmlLink"),
                    "created": event.get("created"),
                    "updated": event.get("updated"),
                    "creator": {
                        "email": event.get("creator", {}).get("email"),
                        "display_name": event.get("creator", {}).get("displayName"),
                    },
                    "visibility": event.get("visibility", "default"),  # default, public, private, confidential
                    "transparency": event.get("transparency", "opaque"),  # opaque (busy), transparent (free)
                    "color_id": event.get("colorId"),
                    "event_type": event.get("eventType", "default"),  # default, outOfOffice, focusTime, workingLocation
                    "reminders": event.get("reminders"),
                    "conference_data": event.get("conferenceData"),
                }

                formatted_events.append(formatted_event)

            # Sort events by start time (for non-single-event queries)
            if not single_events:
                formatted_events.sort(key=lambda e: e["start"] or "")

            # Apply event filters based on configuration
            formatted_events = self._apply_event_filters(formatted_events, filter_context="briefing", calendar_id=calendar_id)

            # Generate summary statistics
            total_events = len(formatted_events)
            all_day_count = sum(1 for e in formatted_events if e["is_all_day"])
            timed_count = total_events - all_day_count
            recurring_count = sum(1 for e in formatted_events if e["is_recurring"])

            status_counts = {}
            for event in formatted_events:
                status = event["status"]
                status_counts[status] = status_counts.get(status, 0) + 1

            return ToolResult.ok(
                {
                    "events": formatted_events,
                    "summary": {
                        "total_count": total_events,
                        "all_day_events": all_day_count,
                        "timed_events": timed_count,
                        "recurring_events": recurring_count,
                        "status_breakdown": status_counts,
                        "date_range": {
                            "start": start_date_str,
                            "end": end_date_str,
                        },
                        "calendar_id": calendar_id,
                    },
                }
            )

        except ValueError as e:
            # Handle authentication errors from _get_service()
            return ToolResult.fail(str(e))

    async def _tool_get_today_events(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Tool: Fetch today's events with intelligent filtering and free/busy calculation.

        This convenience tool:
        - Fetches all events for today (midnight to midnight in specified timezone)
        - Excludes events the user has declined
        - Sorts events by start time
        - Calculates free/busy status with time breakdown
        - Handles all-day events appropriately

        Args:
            arguments: Tool parameters including:
                - calendar_id: Calendar ID (default: 'primary')
                - timezone: Timezone name for 'today' calculation (default: system timezone)

        Returns:
            ToolResult containing filtered events and free/busy analysis
        """
        try:
            # Get authenticated service
            service = self._get_service()

            # Extract parameters
            calendar_id = arguments.get("calendar_id", "primary")
            timezone_str = arguments.get("timezone")

            # Determine timezone for "today" calculation
            if timezone_str:
                try:
                    tz = ZoneInfo(timezone_str)
                except Exception:
                    return ToolResult.fail(
                        f"Invalid timezone: {timezone_str}. Use IANA timezone names like 'America/New_York' or 'UTC'."
                    )
            else:
                # Use system local timezone
                try:
                    tz = ZoneInfo("localtime")
                except Exception:
                    # Fallback to UTC if local timezone cannot be determined
                    tz = ZoneInfo("UTC")

            # Calculate today's date range in the specified timezone
            now = datetime.now(tz)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Convert to RFC3339 format required by Google Calendar API
            time_min = today_start.isoformat()
            time_max = today_end.isoformat()

            # Fetch events from Google Calendar API
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=250,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            raw_events = events_result.get("items", [])

            # Filter and format events
            filtered_events = []
            for event in raw_events:
                # Skip cancelled events
                if event.get("status") == "cancelled":
                    continue

                # Check if user has declined this event
                user_declined = False

                # Check if user is organizer (can't decline own events)
                if not event.get("organizer", {}).get("self", False):
                    # User is not organizer - check if they declined as attendee
                    for attendee in event.get("attendees", []):
                        # Check if this attendee is the current user and has declined
                        if attendee.get("self", False) and attendee.get("responseStatus") == "declined":
                            user_declined = True
                            break

                # Skip declined events
                if user_declined:
                    continue

                # Format event (similar to _tool_get_events)
                start = event.get("start", {})
                end = event.get("end", {})
                is_all_day = "date" in start and "dateTime" not in start

                if is_all_day:
                    start_time = start.get("date")
                    end_time = end.get("date")
                else:
                    start_time = start.get("dateTime")
                    end_time = end.get("dateTime")

                # Format attendees
                attendees = []
                for attendee in event.get("attendees", []):
                    attendees.append({
                        "email": attendee.get("email"),
                        "display_name": attendee.get("displayName"),
                        "response_status": attendee.get("responseStatus"),
                        "organizer": attendee.get("organizer", False),
                        "optional": attendee.get("optional", False),
                    })

                formatted_event = {
                    "id": event.get("id"),
                    "summary": event.get("summary", "(No title)"),
                    "description": event.get("description"),
                    "location": event.get("location"),
                    "start": start_time,
                    "end": end_time,
                    "start_timezone": start.get("timeZone"),
                    "end_timezone": end.get("timeZone"),
                    "is_all_day": is_all_day,
                    "status": event.get("status", "confirmed"),
                    "attendees": attendees,
                    "attendees_count": len(attendees),
                    "organizer": {
                        "email": event.get("organizer", {}).get("email"),
                        "display_name": event.get("organizer", {}).get("displayName"),
                        "is_self": event.get("organizer", {}).get("self", False),
                    },
                    "transparency": event.get("transparency", "opaque"),
                    "event_type": event.get("eventType", "default"),
                    "html_link": event.get("htmlLink"),
                    "created": event.get("created"),
                    "updated": event.get("updated"),
                }

                filtered_events.append(formatted_event)

            # Sort events by start time (should already be sorted by API, but ensure it)
            filtered_events.sort(key=lambda e: e.get("start", ""))

            # Apply event filters based on configuration
            filtered_events = self._apply_event_filters(filtered_events, filter_context="briefing", calendar_id=calendar_id)

            # Calculate free/busy status
            # Track busy time (events that block time)
            busy_minutes = 0
            free_slots = []
            last_event_end = today_start

            for event in filtered_events:
                # Skip all-day events for busy time calculation
                if event.get("is_all_day"):
                    continue

                # Parse event times
                start_str = event.get("start")
                end_str = event.get("end")

                if not start_str or not end_str:
                    continue

                try:
                    # Parse ISO 8601 datetime strings
                    event_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    event_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                    # Convert to the target timezone for consistent calculation
                    if event_start.tzinfo:
                        event_start = event_start.astimezone(tz)
                    if event_end.tzinfo:
                        event_end = event_end.astimezone(tz)

                    # Only count events that fall within today
                    if event_end <= today_start or event_start >= today_end:
                        continue

                    # Clip event times to today's boundaries
                    clipped_start = max(event_start, today_start)
                    clipped_end = min(event_end, today_end)

                    # Check transparency - skip "transparent" (free) events
                    if event.get("transparency") == "transparent":
                        continue

                    # Add to busy time
                    duration = (clipped_end - clipped_start).total_seconds() / 60
                    busy_minutes += duration

                    # Track free slot before this event
                    if last_event_end < clipped_start:
                        free_slot_duration = (clipped_start - last_event_end).total_seconds() / 60
                        if free_slot_duration > 0:
                            free_slots.append({
                                "start": last_event_end.isoformat(),
                                "end": clipped_start.isoformat(),
                                "duration_minutes": int(free_slot_duration),
                            })

                    # Update last event end time
                    last_event_end = max(last_event_end, clipped_end)

                except (ValueError, TypeError):
                    # Skip events with invalid time data
                    continue

            # Add final free slot (from last event to end of day)
            if last_event_end < today_end:
                free_slot_duration = (today_end - last_event_end).total_seconds() / 60
                if free_slot_duration > 0:
                    free_slots.append({
                        "start": last_event_end.isoformat(),
                        "end": today_end.isoformat(),
                        "duration_minutes": int(free_slot_duration),
                    })

            # Calculate total time in a day (in minutes)
            total_minutes = 24 * 60
            free_minutes = total_minutes - busy_minutes

            # Calculate percentages
            busy_percentage = (busy_minutes / total_minutes) * 100 if total_minutes > 0 else 0
            free_percentage = (free_minutes / total_minutes) * 100 if total_minutes > 0 else 0

            # Count event types
            all_day_events = [e for e in filtered_events if e.get("is_all_day")]
            timed_events = [e for e in filtered_events if not e.get("is_all_day")]

            # Build result
            return ToolResult.ok(
                {
                    "events": filtered_events,
                    "summary": {
                        "date": today_start.date().isoformat(),
                        "timezone": str(tz),
                        "total_events": len(filtered_events),
                        "all_day_events": len(all_day_events),
                        "timed_events": len(timed_events),
                        "calendar_id": calendar_id,
                    },
                    "free_busy": {
                        "busy_minutes": int(busy_minutes),
                        "busy_hours": round(busy_minutes / 60, 2),
                        "busy_percentage": round(busy_percentage, 1),
                        "free_minutes": int(free_minutes),
                        "free_hours": round(free_minutes / 60, 2),
                        "free_percentage": round(free_percentage, 1),
                        "free_slots": free_slots,
                        "free_slots_count": len(free_slots),
                    },
                }
            )

        except ValueError as e:
            # Handle authentication errors from _get_service()
            return ToolResult.fail(str(e))

    async def _tool_find_free_slots(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Tool: Find available time slots within a date range.

        This tool analyzes the calendar to find free time slots that meet specified criteria.
        It considers:
        - Existing events and their busy/free status (transparency)
        - Working hours (optional) to limit slots to business hours
        - Minimum slot duration to filter out very short gaps
        - Buffer time around events to prevent back-to-back scheduling
        - Weekend exclusion (optional)
        - Calendar filtering preferences

        Algorithm:
        1. Fetch all events in the date range
        2. For each day in the range:
           - Define the available time window (working hours or full day)
           - Identify busy periods from events (with buffer time)
           - Find gaps between busy periods
           - Filter by minimum duration
        3. Return sorted list of free slots

        Args:
            arguments: Tool parameters including:
                - start_date: Start date (required)
                - end_date: End date (required)
                - calendar_id: Calendar to check (default: 'primary')
                - min_duration_minutes: Minimum slot duration (default: 30)
                - working_hours_start: Working hours start hour 0-23 (default: None)
                - working_hours_end: Working hours end hour 0-23 (default: None)
                - buffer_minutes: Buffer time around events (default: 0)
                - timezone: Timezone for calculations (default: system timezone)
                - exclude_weekends: Skip Saturday/Sunday (default: False)

        Returns:
            ToolResult containing list of free slots with metadata
        """
        try:
            # Get authenticated service
            service = self._get_service()

            # Extract and validate required parameters
            start_date_str = arguments.get("start_date")
            end_date_str = arguments.get("end_date")

            if not start_date_str:
                return ToolResult.fail("Missing required parameter: start_date")
            if not end_date_str:
                return ToolResult.fail("Missing required parameter: end_date")

            # Extract optional parameters with defaults
            calendar_id = arguments.get("calendar_id", "primary")
            min_duration_minutes = arguments.get("min_duration_minutes", 30)
            working_hours_start = arguments.get("working_hours_start")
            working_hours_end = arguments.get("working_hours_end")
            buffer_minutes = arguments.get("buffer_minutes", 0)
            timezone_str = arguments.get("timezone")
            exclude_weekends = arguments.get("exclude_weekends", False)

            # Validate parameters
            if min_duration_minutes < 1:
                return ToolResult.fail("min_duration_minutes must be at least 1")

            if buffer_minutes < 0:
                return ToolResult.fail("buffer_minutes must be non-negative")

            if working_hours_start is not None:
                if not (0 <= working_hours_start <= 23):
                    return ToolResult.fail("working_hours_start must be between 0 and 23")

            if working_hours_end is not None:
                if not (0 <= working_hours_end <= 23):
                    return ToolResult.fail("working_hours_end must be between 0 and 23")

            if working_hours_start is not None and working_hours_end is not None:
                if working_hours_end <= working_hours_start:
                    return ToolResult.fail("working_hours_end must be after working_hours_start")

            # Determine timezone
            if timezone_str:
                try:
                    tz = ZoneInfo(timezone_str)
                except Exception:
                    return ToolResult.fail(
                        f"Invalid timezone: {timezone_str}. Use IANA timezone names like 'America/New_York' or 'UTC'."
                    )
            else:
                # Use system local timezone
                try:
                    tz = ZoneInfo("localtime")
                except Exception:
                    # Fallback to UTC if local timezone cannot be determined
                    tz = ZoneInfo("UTC")

            # Parse dates - support both date-only and datetime formats
            try:
                if "T" in start_date_str:
                    range_start = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                    if not range_start.tzinfo:
                        range_start = range_start.replace(tzinfo=tz)
                else:
                    # Date only - start of day in the specified timezone
                    range_start = datetime.fromisoformat(f"{start_date_str}T00:00:00").replace(tzinfo=tz)

                if "T" in end_date_str:
                    range_end = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                    if not range_end.tzinfo:
                        range_end = range_end.replace(tzinfo=tz)
                else:
                    # Date only - end of day in the specified timezone
                    range_end = datetime.fromisoformat(f"{end_date_str}T23:59:59").replace(tzinfo=tz)

            except ValueError as e:
                return ToolResult.fail(
                    f"Invalid date format: {str(e)}. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )

            # Validate date range
            if range_end <= range_start:
                return ToolResult.fail("end_date must be after start_date")

            # Fetch events from Google Calendar API for the entire date range
            time_min = range_start.isoformat()
            time_max = range_end.isoformat()

            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=2500,  # Higher limit for comprehensive conflict detection
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            raw_events = events_result.get("items", [])

            # Format events (reuse logic from get_events)
            formatted_events = []
            for event in raw_events:
                # Skip cancelled events
                if event.get("status") == "cancelled":
                    continue

                # Parse event data
                start = event.get("start", {})
                end = event.get("end", {})
                is_all_day = "date" in start and "dateTime" not in start

                if is_all_day:
                    start_time = start.get("date")
                    end_time = end.get("date")
                else:
                    start_time = start.get("dateTime")
                    end_time = end.get("dateTime")

                # Format attendees
                attendees = []
                for attendee in event.get("attendees", []):
                    attendees.append({
                        "email": attendee.get("email"),
                        "response_status": attendee.get("responseStatus"),
                        "self": attendee.get("self", False),
                    })

                formatted_event = {
                    "id": event.get("id"),
                    "summary": event.get("summary", "(No title)"),
                    "description": event.get("description"),
                    "location": event.get("location"),
                    "start": start_time,
                    "end": end_time,
                    "is_all_day": is_all_day,
                    "status": event.get("status", "confirmed"),
                    "attendees": attendees,
                    "organizer": {
                        "email": event.get("organizer", {}).get("email"),
                        "is_self": event.get("organizer", {}).get("self", False),
                    },
                    "transparency": event.get("transparency", "opaque"),
                    "color_id": event.get("colorId"),
                    "event_type": event.get("eventType", "default"),
                    "conference_data": event.get("conferenceData"),
                    "visibility": event.get("visibility", "default"),
                    "is_recurring": "recurringEventId" in event or "recurrence" in event,
                }

                formatted_events.append(formatted_event)

            # Apply event filters (configured in calendar_filters.json)
            filtered_events = self._apply_event_filters(
                formatted_events, filter_context="free_slots", calendar_id=calendar_id
            )

            # Build list of busy periods
            # A busy period is a time range when the user is unavailable
            busy_periods = []

            for event in filtered_events:
                # Skip all-day events - they don't block specific times
                if event.get("is_all_day"):
                    continue

                # Skip events marked as "transparent" (free time)
                if event.get("transparency") == "transparent":
                    continue

                # Skip events the user has declined
                user_declined = False
                if not event.get("organizer", {}).get("is_self", False):
                    for attendee in event.get("attendees", []):
                        if attendee.get("self", False) and attendee.get("response_status") == "declined":
                            user_declined = True
                            break

                if user_declined:
                    continue

                # Parse event times
                start_str = event.get("start")
                end_str = event.get("end")

                if not start_str or not end_str:
                    continue

                try:
                    event_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    event_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                    # Convert to target timezone for consistent calculation
                    if event_start.tzinfo:
                        event_start = event_start.astimezone(tz)
                    else:
                        event_start = event_start.replace(tzinfo=tz)

                    if event_end.tzinfo:
                        event_end = event_end.astimezone(tz)
                    else:
                        event_end = event_end.replace(tzinfo=tz)

                    # Apply buffer time
                    from datetime import timedelta
                    if buffer_minutes > 0:
                        event_start = event_start - timedelta(minutes=buffer_minutes)
                        event_end = event_end + timedelta(minutes=buffer_minutes)

                    busy_periods.append({
                        "start": event_start,
                        "end": event_end,
                        "event_summary": event.get("summary", "(No title)"),
                    })

                except (ValueError, TypeError):
                    # Skip events with invalid time data
                    continue

            # Sort busy periods by start time
            busy_periods.sort(key=lambda p: p["start"])

            # Merge overlapping busy periods to avoid double-counting conflicts
            merged_busy_periods = []
            for period in busy_periods:
                if not merged_busy_periods:
                    merged_busy_periods.append(period)
                else:
                    last_period = merged_busy_periods[-1]
                    # If this period overlaps or touches the last one, merge them
                    if period["start"] <= last_period["end"]:
                        last_period["end"] = max(last_period["end"], period["end"])
                        # Update summary to include both events
                        if period["event_summary"] not in last_period["event_summary"]:
                            last_period["event_summary"] = f"{last_period['event_summary']} + {period['event_summary']}"
                    else:
                        merged_busy_periods.append(period)

            # Find free slots by analyzing gaps between busy periods
            free_slots = []

            # Generate list of days to check
            from datetime import timedelta
            current_date = range_start.date()
            end_date = range_end.date()

            while current_date <= end_date:
                # Skip weekends if requested
                if exclude_weekends and current_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                    current_date = current_date + timedelta(days=1)
                    continue

                # Define the available time window for this day
                if working_hours_start is not None and working_hours_end is not None:
                    # Use working hours
                    day_start = datetime.combine(current_date, datetime.min.time()).replace(
                        hour=working_hours_start, minute=0, second=0, microsecond=0, tzinfo=tz
                    )
                    day_end = datetime.combine(current_date, datetime.min.time()).replace(
                        hour=working_hours_end, minute=0, second=0, microsecond=0, tzinfo=tz
                    )
                else:
                    # Use full day
                    day_start = datetime.combine(current_date, datetime.min.time()).replace(
                        hour=0, minute=0, second=0, microsecond=0, tzinfo=tz
                    )
                    day_end = datetime.combine(current_date, datetime.min.time()).replace(
                        hour=23, minute=59, second=59, microsecond=0, tzinfo=tz
                    )

                # Clip to overall date range
                day_start = max(day_start, range_start)
                day_end = min(day_end, range_end)

                # Find busy periods for this day
                day_busy_periods = [
                    p for p in merged_busy_periods
                    if p["end"] > day_start and p["start"] < day_end
                ]

                # Find free gaps
                cursor = day_start
                for busy in day_busy_periods:
                    # Clip busy period to day boundaries
                    busy_start = max(busy["start"], day_start)
                    busy_end = min(busy["end"], day_end)

                    # Check if there's a free gap before this busy period
                    if cursor < busy_start:
                        gap_duration_minutes = (busy_start - cursor).total_seconds() / 60

                        # Only include if it meets minimum duration
                        if gap_duration_minutes >= min_duration_minutes:
                            free_slots.append({
                                "start": cursor.isoformat(),
                                "end": busy_start.isoformat(),
                                "duration_minutes": int(gap_duration_minutes),
                                "date": current_date.isoformat(),
                                "day_of_week": current_date.strftime("%A"),
                            })

                    # Move cursor to end of busy period
                    cursor = max(cursor, busy_end)

                # Check if there's a free slot at the end of the day
                if cursor < day_end:
                    gap_duration_minutes = (day_end - cursor).total_seconds() / 60

                    if gap_duration_minutes >= min_duration_minutes:
                        free_slots.append({
                            "start": cursor.isoformat(),
                            "end": day_end.isoformat(),
                            "duration_minutes": int(gap_duration_minutes),
                            "date": current_date.isoformat(),
                            "day_of_week": current_date.strftime("%A"),
                        })

                # Move to next day
                current_date = current_date + timedelta(days=1)

            # Calculate summary statistics
            total_free_slots = len(free_slots)
            total_free_minutes = sum(slot["duration_minutes"] for slot in free_slots)
            total_free_hours = round(total_free_minutes / 60, 2)

            # Find longest slot
            longest_slot = max(free_slots, key=lambda s: s["duration_minutes"]) if free_slots else None

            # Group by day
            slots_by_day = {}
            for slot in free_slots:
                day = slot["date"]
                if day not in slots_by_day:
                    slots_by_day[day] = []
                slots_by_day[day].append(slot)

            return ToolResult.ok(
                {
                    "free_slots": free_slots,
                    "summary": {
                        "total_slots": total_free_slots,
                        "total_free_minutes": total_free_minutes,
                        "total_free_hours": total_free_hours,
                        "longest_slot": longest_slot,
                        "days_with_availability": len(slots_by_day),
                        "date_range": {
                            "start": start_date_str,
                            "end": end_date_str,
                        },
                        "filters_applied": {
                            "min_duration_minutes": min_duration_minutes,
                            "working_hours": f"{working_hours_start or 0}:00-{working_hours_end or 24}:00" if working_hours_start is not None or working_hours_end is not None else "all day",
                            "buffer_minutes": buffer_minutes,
                            "exclude_weekends": exclude_weekends,
                            "calendar_id": calendar_id,
                            "timezone": str(tz),
                        },
                    },
                    "slots_by_day": slots_by_day,
                }
            )

        except ValueError as e:
            # Handle authentication errors from _get_service()
            return ToolResult.fail(str(e))

    async def _tool_check_conflicts(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Tool: Check if a proposed time slot conflicts with existing calendar events.

        This tool validates whether a proposed time slot is available or conflicts
        with existing calendar events. It provides intelligent conflict detection with:
        - Tentative event handling (optional inclusion)
        - Travel time buffer (adds buffer before/after existing events)
        - Flexible boundaries (allows minor overlap tolerance)
        - Detailed conflict information for decision-making

        Conflict Detection Logic:
        1. Fetch all events in the proposed time range (plus buffer)
        2. Filter out declined events and cancelled events
        3. Optionally include/exclude tentative events based on parameter
        4. Apply buffer time around existing events (travel time)
        5. Check for overlaps considering flexibility tolerance
        6. Return detailed conflict list with recommendations

        Args:
            arguments: Tool parameters including:
                - start_time: Proposed slot start time (required)
                - end_time: Proposed slot end time (required)
                - calendar_id: Calendar to check (default: 'primary')
                - buffer_minutes: Buffer around existing events (default: 0)
                - consider_tentative: Include tentative events (default: True)
                - flexibility_minutes: Overlap tolerance (default: 0)
                - timezone: Timezone for calculations (default: system timezone)

        Returns:
            ToolResult containing conflict analysis and recommendations
        """
        try:
            # Get authenticated service
            service = self._get_service()

            # Extract and validate required parameters
            start_time_str = arguments.get("start_time")
            end_time_str = arguments.get("end_time")

            if not start_time_str:
                return ToolResult.fail("Missing required parameter: start_time")
            if not end_time_str:
                return ToolResult.fail("Missing required parameter: end_time")

            # Extract optional parameters with defaults
            calendar_id = arguments.get("calendar_id", "primary")
            buffer_minutes = arguments.get("buffer_minutes", 0)
            consider_tentative = arguments.get("consider_tentative", True)
            flexibility_minutes = arguments.get("flexibility_minutes", 0)
            timezone_str = arguments.get("timezone")

            # Validate parameters
            if buffer_minutes < 0:
                return ToolResult.fail("buffer_minutes must be non-negative")

            if flexibility_minutes < 0:
                return ToolResult.fail("flexibility_minutes must be non-negative")

            # Determine timezone
            if timezone_str:
                try:
                    tz = ZoneInfo(timezone_str)
                except Exception:
                    return ToolResult.fail(
                        f"Invalid timezone: {timezone_str}. Use IANA timezone names like 'America/New_York' or 'UTC'."
                    )
            else:
                # Use system local timezone
                try:
                    tz = ZoneInfo("localtime")
                except Exception:
                    # Fallback to UTC if local timezone cannot be determined
                    tz = ZoneInfo("UTC")

            # Parse proposed slot times
            try:
                proposed_start = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                if not proposed_start.tzinfo:
                    proposed_start = proposed_start.replace(tzinfo=tz)

                proposed_end = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                if not proposed_end.tzinfo:
                    proposed_end = proposed_end.replace(tzinfo=tz)

            except ValueError as e:
                return ToolResult.fail(
                    f"Invalid time format: {str(e)}. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
                )

            # Validate time range
            if proposed_end <= proposed_start:
                return ToolResult.fail("end_time must be after start_time")

            # Calculate proposed slot duration
            proposed_duration_minutes = (proposed_end - proposed_start).total_seconds() / 60

            # Expand search window to account for buffer time
            # We need to check events that might conflict when buffer is applied
            from datetime import timedelta
            search_start = proposed_start - timedelta(minutes=buffer_minutes)
            search_end = proposed_end + timedelta(minutes=buffer_minutes)

            # Fetch events from Google Calendar API
            time_min = search_start.isoformat()
            time_max = search_end.isoformat()

            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=100,  # Should be sufficient for conflict checking
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            raw_events = events_result.get("items", [])

            # Format and filter events
            formatted_events = []
            for event in raw_events:
                # Skip cancelled events
                if event.get("status") == "cancelled":
                    continue

                # Parse event data
                start = event.get("start", {})
                end = event.get("end", {})
                is_all_day = "date" in start and "dateTime" not in start

                # Skip all-day events - they don't block specific times
                if is_all_day:
                    continue

                start_time = start.get("dateTime")
                end_time = end.get("dateTime")

                if not start_time or not end_time:
                    continue

                # Format attendees
                attendees = []
                for attendee in event.get("attendees", []):
                    attendees.append({
                        "email": attendee.get("email"),
                        "response_status": attendee.get("responseStatus"),
                        "self": attendee.get("self", False),
                    })

                formatted_event = {
                    "id": event.get("id"),
                    "summary": event.get("summary", "(No title)"),
                    "description": event.get("description"),
                    "location": event.get("location"),
                    "start": start_time,
                    "end": end_time,
                    "is_all_day": False,
                    "status": event.get("status", "confirmed"),
                    "attendees": attendees,
                    "organizer": {
                        "email": event.get("organizer", {}).get("email"),
                        "is_self": event.get("organizer", {}).get("self", False),
                    },
                    "transparency": event.get("transparency", "opaque"),
                    "color_id": event.get("colorId"),
                    "event_type": event.get("eventType", "default"),
                    "conference_data": event.get("conferenceData"),
                    "visibility": event.get("visibility", "default"),
                }

                formatted_events.append(formatted_event)

            # Apply event filters but use conflict_detection context
            # This ensures we check all relevant events unless explicitly filtered
            filtered_events = self._apply_event_filters(
                formatted_events, filter_context="conflict_detection", calendar_id=calendar_id
            )

            # Check for conflicts
            conflicts = []
            near_conflicts = []  # Events that are close but not actual conflicts

            for event in filtered_events:
                # Skip tentative events if not considering them
                if event.get("status") == "tentative" and not consider_tentative:
                    continue

                # Skip events marked as "transparent" (free time)
                if event.get("transparency") == "transparent":
                    continue

                # Skip events the user has declined
                user_declined = False
                if not event.get("organizer", {}).get("is_self", False):
                    for attendee in event.get("attendees", []):
                        if attendee.get("self", False) and attendee.get("response_status") == "declined":
                            user_declined = True
                            break

                if user_declined:
                    continue

                # Parse event times
                try:
                    event_start = datetime.fromisoformat(event.get("start").replace("Z", "+00:00"))
                    event_end = datetime.fromisoformat(event.get("end").replace("Z", "+00:00"))

                    # Convert to target timezone for consistent calculation
                    if event_start.tzinfo:
                        event_start = event_start.astimezone(tz)
                    else:
                        event_start = event_start.replace(tzinfo=tz)

                    if event_end.tzinfo:
                        event_end = event_end.astimezone(tz)
                    else:
                        event_end = event_end.replace(tzinfo=tz)

                    # Apply buffer time to existing event
                    # Buffer represents travel time or preparation time needed
                    buffered_event_start = event_start - timedelta(minutes=buffer_minutes)
                    buffered_event_end = event_end + timedelta(minutes=buffer_minutes)

                    # Check for overlap considering flexibility
                    # Flexibility allows for minor overlaps (e.g., ending 5 min late is acceptable)
                    # An overlap occurs when: proposed_start < buffered_event_end AND proposed_end > buffered_event_start

                    # Apply flexibility tolerance to proposed slot
                    flexible_proposed_start = proposed_start + timedelta(minutes=flexibility_minutes)
                    flexible_proposed_end = proposed_end - timedelta(minutes=flexibility_minutes)

                    # Check for hard conflict (overlap even with flexibility)
                    has_conflict = (
                        flexible_proposed_start < buffered_event_end and
                        flexible_proposed_end > buffered_event_start
                    )

                    # Calculate overlap amount
                    overlap_start = max(proposed_start, buffered_event_start)
                    overlap_end = min(proposed_end, buffered_event_end)
                    overlap_minutes = max(0, (overlap_end - overlap_start).total_seconds() / 60)

                    if has_conflict:
                        # Calculate time until/since event
                        minutes_until_event = (buffered_event_start - proposed_end).total_seconds() / 60
                        minutes_since_event = (proposed_start - buffered_event_end).total_seconds() / 60

                        conflict_info = {
                            "event_id": event.get("id"),
                            "event_summary": event.get("summary"),
                            "event_start": event.get("start"),
                            "event_end": event.get("end"),
                            "event_start_with_buffer": buffered_event_start.isoformat(),
                            "event_end_with_buffer": buffered_event_end.isoformat(),
                            "event_status": event.get("status"),
                            "event_location": event.get("location"),
                            "overlap_minutes": round(overlap_minutes, 1),
                            "conflict_type": self._determine_conflict_type(
                                proposed_start, proposed_end,
                                buffered_event_start, buffered_event_end
                            ),
                            "is_tentative": event.get("status") == "tentative",
                        }
                        conflicts.append(conflict_info)
                    else:
                        # Check if it's a near conflict (within 30 minutes before or after)
                        minutes_until_event = (buffered_event_start - proposed_end).total_seconds() / 60
                        minutes_since_event = (proposed_start - buffered_event_end).total_seconds() / 60

                        if 0 <= minutes_until_event <= 30:
                            near_conflicts.append({
                                "event_summary": event.get("summary"),
                                "event_start": event.get("start"),
                                "minutes_until": round(minutes_until_event, 1),
                                "direction": "after",
                            })
                        elif 0 <= minutes_since_event <= 30:
                            near_conflicts.append({
                                "event_summary": event.get("summary"),
                                "event_end": event.get("end"),
                                "minutes_since": round(minutes_since_event, 1),
                                "direction": "before",
                            })

                except (ValueError, TypeError):
                    # Skip events with invalid time data
                    continue

            # Determine overall conflict status
            has_conflicts = len(conflicts) > 0
            has_hard_conflicts = any(not c["is_tentative"] for c in conflicts)
            has_tentative_conflicts = any(c["is_tentative"] for c in conflicts)

            # Generate recommendation
            if has_hard_conflicts:
                recommendation = "NOT_AVAILABLE"
                recommendation_reason = f"Conflicts with {len([c for c in conflicts if not c['is_tentative']])} confirmed event(s)"
            elif has_tentative_conflicts:
                recommendation = "TENTATIVE"
                recommendation_reason = f"Conflicts with {len([c for c in conflicts if c['is_tentative']])} tentative event(s)"
            elif near_conflicts:
                recommendation = "AVAILABLE_WITH_WARNING"
                recommendation_reason = f"Available but {len(near_conflicts)} event(s) nearby - may be tight"
            else:
                recommendation = "AVAILABLE"
                recommendation_reason = "No conflicts detected"

            return ToolResult.ok(
                {
                    "has_conflicts": has_conflicts,
                    "is_available": not has_hard_conflicts,
                    "recommendation": recommendation,
                    "recommendation_reason": recommendation_reason,
                    "proposed_slot": {
                        "start": start_time_str,
                        "end": end_time_str,
                        "duration_minutes": round(proposed_duration_minutes, 1),
                        "timezone": str(tz),
                    },
                    "conflicts": conflicts,
                    "conflict_summary": {
                        "total_conflicts": len(conflicts),
                        "hard_conflicts": len([c for c in conflicts if not c["is_tentative"]]),
                        "tentative_conflicts": len([c for c in conflicts if c["is_tentative"]]),
                        "total_overlap_minutes": round(sum(c["overlap_minutes"] for c in conflicts), 1),
                    },
                    "near_conflicts": near_conflicts,
                    "settings": {
                        "buffer_minutes": buffer_minutes,
                        "consider_tentative": consider_tentative,
                        "flexibility_minutes": flexibility_minutes,
                        "calendar_id": calendar_id,
                    },
                }
            )

        except ValueError as e:
            # Handle authentication errors from _get_service()
            return ToolResult.fail(str(e))

    async def _tool_get_availability(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Tool: Analyze calendar availability and return daily/weekly summary.

        This tool provides a comprehensive analysis of calendar availability,
        calculating key metrics to understand workload distribution and identify
        optimal scheduling windows. It's particularly useful for:
        - Daily/weekly capacity planning
        - Identifying fragmentation and context-switching overhead
        - Finding the best times for deep work
        - Understanding overall schedule health

        Metrics Calculated:
        1. Total Free Time: Cumulative available hours across the date range
        2. Total Busy Time: Cumulative scheduled hours
        3. Longest Continuous Block: Maximum uninterrupted free time slot
        4. Fragmentation Score: Measure of how fragmented the schedule is
           - Lower score = fewer, longer blocks (better for deep work)
           - Higher score = many small gaps (more context switching)
           - Formula: (number_of_free_slots / total_free_hours) * 100
        5. Busy/Free Ratio: Percentage of time scheduled vs available
        6. Average Free Slot Duration: Mean duration of free time blocks
        7. Daily Breakdown: Per-day analysis with key insights

        Args:
            arguments: Tool parameters including:
                - start_date: Start date (required)
                - end_date: End date (required)
                - calendar_id: Calendar to analyze (default: 'primary')
                - working_hours_start: Working hours start hour 0-23 (default: None)
                - working_hours_end: Working hours end hour 0-23 (default: None)
                - timezone: Timezone for calculations (default: system timezone)
                - exclude_weekends: Skip Saturday/Sunday (default: False)
                - min_slot_duration_minutes: Minimum duration to count as usable slot (default: 15)

        Returns:
            ToolResult containing comprehensive availability analysis
        """
        try:
            # Get authenticated service
            service = self._get_service()

            # Extract and validate required parameters
            start_date_str = arguments.get("start_date")
            end_date_str = arguments.get("end_date")

            if not start_date_str:
                return ToolResult.fail("Missing required parameter: start_date")
            if not end_date_str:
                return ToolResult.fail("Missing required parameter: end_date")

            # Extract optional parameters with defaults
            calendar_id = arguments.get("calendar_id", "primary")
            working_hours_start = arguments.get("working_hours_start")
            working_hours_end = arguments.get("working_hours_end")
            timezone_str = arguments.get("timezone")
            exclude_weekends = arguments.get("exclude_weekends", False)
            min_slot_duration_minutes = arguments.get("min_slot_duration_minutes", 15)

            # Validate parameters
            if min_slot_duration_minutes < 1:
                return ToolResult.fail("min_slot_duration_minutes must be at least 1")

            if working_hours_start is not None:
                if not (0 <= working_hours_start <= 23):
                    return ToolResult.fail("working_hours_start must be between 0 and 23")

            if working_hours_end is not None:
                if not (0 <= working_hours_end <= 23):
                    return ToolResult.fail("working_hours_end must be between 0 and 23")

            if working_hours_start is not None and working_hours_end is not None:
                if working_hours_end <= working_hours_start:
                    return ToolResult.fail("working_hours_end must be after working_hours_start")

            # Determine timezone
            if timezone_str:
                try:
                    tz = ZoneInfo(timezone_str)
                except Exception:
                    return ToolResult.fail(
                        f"Invalid timezone: {timezone_str}. Use IANA timezone names like 'America/New_York' or 'UTC'."
                    )
            else:
                # Use system local timezone
                try:
                    tz = ZoneInfo("localtime")
                except Exception:
                    # Fallback to UTC if local timezone cannot be determined
                    tz = ZoneInfo("UTC")

            # Parse dates - support both date-only and datetime formats
            from datetime import timedelta
            try:
                if "T" in start_date_str:
                    range_start = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                    if not range_start.tzinfo:
                        range_start = range_start.replace(tzinfo=tz)
                else:
                    # Date only - start at beginning of day
                    date_obj = datetime.fromisoformat(start_date_str)
                    range_start = datetime(date_obj.year, date_obj.month, date_obj.day, tzinfo=tz)

                if "T" in end_date_str:
                    range_end = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                    if not range_end.tzinfo:
                        range_end = range_end.replace(tzinfo=tz)
                else:
                    # Date only - end at end of day
                    date_obj = datetime.fromisoformat(end_date_str)
                    range_end = datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, 59, tzinfo=tz)

            except ValueError as e:
                return ToolResult.fail(
                    f"Invalid date format: {str(e)}. Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                )

            # Validate date range
            if range_end <= range_start:
                return ToolResult.fail("end_date must be after start_date")

            # Convert to UTC for API calls
            api_start = range_start.astimezone(ZoneInfo("UTC")).isoformat()
            api_end = range_end.astimezone(ZoneInfo("UTC")).isoformat()

            # Fetch all events in the date range
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=api_start,
                    timeMax=api_end,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=2500,
                )
                .execute()
            )

            events = events_result.get("items", [])

            # Format events and apply filters
            formatted_events = []
            for event in events:
                # Skip cancelled events
                if event.get("status") == "cancelled":
                    continue

                # Parse event data
                start = event.get("start", {})
                end = event.get("end", {})
                is_all_day = "date" in start and "dateTime" not in start

                # Get event times
                if is_all_day:
                    # All-day events don't block specific times for availability analysis
                    # but we'll track them separately
                    start_time = start.get("date")
                    end_time = end.get("date")
                    formatted_events.append({
                        "summary": event.get("summary", "(No title)"),
                        "start": start_time,
                        "end": end_time,
                        "is_all_day": True,
                        "status": event.get("status", "confirmed"),
                        "transparency": event.get("transparency", "opaque"),
                        "event_type": event.get("eventType", "default"),
                    })
                else:
                    start_time = start.get("dateTime")
                    end_time = end.get("dateTime")

                    if start_time and end_time:
                        formatted_events.append({
                            "summary": event.get("summary", "(No title)"),
                            "start": start_time,
                            "end": end_time,
                            "is_all_day": False,
                            "status": event.get("status", "confirmed"),
                            "transparency": event.get("transparency", "opaque"),
                            "event_type": event.get("eventType", "default"),
                        })

            # Apply event filters
            filtered_events = self._apply_event_filters(
                formatted_events, filter_context="availability_analysis", calendar_id=calendar_id
            )

            # Build list of busy periods (only from non-all-day, opaque events)
            busy_periods = []
            all_day_events_count = 0
            for event in filtered_events:
                # Skip all-day events for time-based analysis
                if event.get("is_all_day"):
                    all_day_events_count += 1
                    continue

                # Skip events marked as "transparent" (free time)
                if event.get("transparency") == "transparent":
                    continue

                try:
                    event_start = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
                    event_end = datetime.fromisoformat(event["end"].replace("Z", "+00:00"))

                    # Convert to target timezone
                    if event_start.tzinfo:
                        event_start = event_start.astimezone(tz)
                    else:
                        event_start = event_start.replace(tzinfo=tz)

                    if event_end.tzinfo:
                        event_end = event_end.astimezone(tz)
                    else:
                        event_end = event_end.replace(tzinfo=tz)

                    busy_periods.append({
                        "start": event_start,
                        "end": event_end,
                        "summary": event.get("summary", "(No title)"),
                    })

                except (ValueError, TypeError):
                    # Skip events with invalid time data
                    continue

            # Sort busy periods by start time
            busy_periods.sort(key=lambda x: x["start"])

            # Merge overlapping busy periods to get accurate busy time calculation
            merged_busy_periods = []
            for period in busy_periods:
                if not merged_busy_periods:
                    merged_busy_periods.append(period)
                else:
                    last = merged_busy_periods[-1]
                    if period["start"] <= last["end"]:
                        # Overlapping or adjacent - merge
                        last["end"] = max(last["end"], period["end"])
                    else:
                        merged_busy_periods.append(period)

            # Analyze availability day by day
            daily_analysis = []
            current_date = range_start.date()
            end_date = range_end.date()

            while current_date <= end_date:
                # Skip weekends if requested
                if exclude_weekends and current_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                    current_date = current_date + timedelta(days=1)
                    continue

                # Define the analysis window for this day
                if working_hours_start is not None and working_hours_end is not None:
                    day_start = datetime(
                        current_date.year, current_date.month, current_date.day,
                        working_hours_start, 0, 0, tzinfo=tz
                    )
                    day_end = datetime(
                        current_date.year, current_date.month, current_date.day,
                        working_hours_end, 0, 0, tzinfo=tz
                    )
                else:
                    # Full day (00:00 to 23:59:59)
                    day_start = datetime(
                        current_date.year, current_date.month, current_date.day,
                        0, 0, 0, tzinfo=tz
                    )
                    day_end = datetime(
                        current_date.year, current_date.month, current_date.day,
                        23, 59, 59, tzinfo=tz
                    )

                # Adjust day boundaries if they're outside the requested range
                if day_start < range_start:
                    day_start = range_start
                if day_end > range_end:
                    day_end = range_end

                # Find busy periods for this day
                day_busy_periods = []
                for period in merged_busy_periods:
                    # Check if busy period overlaps with this day
                    if period["start"] < day_end and period["end"] > day_start:
                        # Clip to day boundaries
                        busy_start = max(period["start"], day_start)
                        busy_end = min(period["end"], day_end)
                        day_busy_periods.append({
                            "start": busy_start,
                            "end": busy_end,
                        })

                # Calculate free slots for this day
                day_free_slots = []
                cursor = day_start

                for busy in day_busy_periods:
                    busy_start = busy["start"]
                    busy_end = busy["end"]

                    # Check if there's a gap before this busy period
                    if cursor < busy_start:
                        gap_duration_minutes = (busy_start - cursor).total_seconds() / 60

                        day_free_slots.append({
                            "start": cursor,
                            "end": busy_start,
                            "duration_minutes": gap_duration_minutes,
                        })

                    # Move cursor to end of busy period
                    cursor = max(cursor, busy_end)

                # Check if there's a free slot at the end of the day
                if cursor < day_end:
                    gap_duration_minutes = (day_end - cursor).total_seconds() / 60
                    day_free_slots.append({
                        "start": cursor,
                        "end": day_end,
                        "duration_minutes": gap_duration_minutes,
                    })

                # Calculate day metrics
                total_day_minutes = (day_end - day_start).total_seconds() / 60
                busy_minutes = sum((p["end"] - p["start"]).total_seconds() / 60 for p in day_busy_periods)
                free_minutes = total_day_minutes - busy_minutes

                # Count usable free slots (meeting minimum duration)
                usable_free_slots = [s for s in day_free_slots if s["duration_minutes"] >= min_slot_duration_minutes]
                usable_free_minutes = sum(s["duration_minutes"] for s in usable_free_slots)

                # Find longest continuous block
                longest_block_minutes = max(
                    (s["duration_minutes"] for s in day_free_slots), default=0
                )

                # Calculate fragmentation score for this day
                # Formula: (number_of_usable_slots / total_free_hours) * 100
                # Lower is better (fewer, longer blocks)
                if usable_free_minutes > 0:
                    day_fragmentation = (len(usable_free_slots) / (usable_free_minutes / 60)) * 100
                else:
                    day_fragmentation = 0

                # Calculate busy/free ratio
                busy_ratio = (busy_minutes / total_day_minutes * 100) if total_day_minutes > 0 else 0

                daily_analysis.append({
                    "date": current_date.isoformat(),
                    "day_of_week": current_date.strftime("%A"),
                    "total_hours": round(total_day_minutes / 60, 2),
                    "busy_hours": round(busy_minutes / 60, 2),
                    "free_hours": round(free_minutes / 60, 2),
                    "usable_free_hours": round(usable_free_minutes / 60, 2),
                    "busy_percentage": round(busy_ratio, 1),
                    "longest_block_hours": round(longest_block_minutes / 60, 2),
                    "number_of_events": len(day_busy_periods),
                    "number_of_free_slots": len(usable_free_slots),
                    "fragmentation_score": round(day_fragmentation, 2),
                    "quality_rating": self._calculate_day_quality(
                        busy_ratio, day_fragmentation, longest_block_minutes
                    ),
                })

                # Move to next day
                current_date = current_date + timedelta(days=1)

            # Calculate overall statistics
            total_hours = sum(d["total_hours"] for d in daily_analysis)
            total_busy_hours = sum(d["busy_hours"] for d in daily_analysis)
            total_free_hours = sum(d["free_hours"] for d in daily_analysis)
            total_usable_free_hours = sum(d["usable_free_hours"] for d in daily_analysis)
            total_events = sum(d["number_of_events"] for d in daily_analysis)
            total_free_slots = sum(d["number_of_free_slots"] for d in daily_analysis)

            # Overall busy percentage
            overall_busy_percentage = (
                (total_busy_hours / total_hours * 100) if total_hours > 0 else 0
            )

            # Overall fragmentation score
            overall_fragmentation = (
                (total_free_slots / total_usable_free_hours * 100)
                if total_usable_free_hours > 0
                else 0
            )

            # Find longest continuous block across all days
            longest_block_overall = max(
                (d["longest_block_hours"] for d in daily_analysis), default=0
            )

            # Average free slot duration
            avg_free_slot_duration = (
                (total_usable_free_hours / total_free_slots)
                if total_free_slots > 0
                else 0
            )

            # Identify best and worst days
            best_day = None
            worst_day = None
            if daily_analysis:
                # Best day = most usable free time with low fragmentation
                best_day = max(
                    daily_analysis,
                    key=lambda d: d["usable_free_hours"] - (d["fragmentation_score"] / 100)
                )
                # Worst day = highest busy percentage or highest fragmentation
                worst_day = max(
                    daily_analysis,
                    key=lambda d: d["busy_percentage"] + d["fragmentation_score"]
                )

            return ToolResult.ok(
                {
                    "summary": {
                        "date_range": {
                            "start": start_date_str,
                            "end": end_date_str,
                            "days_analyzed": len(daily_analysis),
                        },
                        "total_hours": round(total_hours, 2),
                        "busy_hours": round(total_busy_hours, 2),
                        "free_hours": round(total_free_hours, 2),
                        "usable_free_hours": round(total_usable_free_hours, 2),
                        "busy_percentage": round(overall_busy_percentage, 1),
                        "total_events": total_events,
                        "all_day_events": all_day_events_count,
                    },
                    "availability_metrics": {
                        "longest_continuous_block_hours": round(longest_block_overall, 2),
                        "fragmentation_score": round(overall_fragmentation, 2),
                        "fragmentation_interpretation": self._interpret_fragmentation(overall_fragmentation),
                        "average_free_slot_hours": round(avg_free_slot_duration, 2),
                        "total_usable_free_slots": total_free_slots,
                    },
                    "daily_breakdown": daily_analysis,
                    "insights": {
                        "best_day_for_deep_work": {
                            "date": best_day["date"] if best_day else None,
                            "day_of_week": best_day["day_of_week"] if best_day else None,
                            "usable_free_hours": best_day["usable_free_hours"] if best_day else None,
                            "fragmentation_score": best_day["fragmentation_score"] if best_day else None,
                        } if best_day else None,
                        "busiest_day": {
                            "date": worst_day["date"] if worst_day else None,
                            "day_of_week": worst_day["day_of_week"] if worst_day else None,
                            "busy_percentage": worst_day["busy_percentage"] if worst_day else None,
                        } if worst_day else None,
                        "schedule_health": self._calculate_schedule_health(
                            overall_busy_percentage, overall_fragmentation, longest_block_overall
                        ),
                    },
                    "settings": {
                        "calendar_id": calendar_id,
                        "timezone": str(tz),
                        "working_hours": (
                            f"{working_hours_start or 0}:00-{working_hours_end or 24}:00"
                            if working_hours_start is not None or working_hours_end is not None
                            else "all day"
                        ),
                        "exclude_weekends": exclude_weekends,
                        "min_slot_duration_minutes": min_slot_duration_minutes,
                    },
                }
            )

        except ValueError as e:
            # Handle authentication errors from _get_service()
            return ToolResult.fail(str(e))

    async def _tool_create_event(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Tool: Create a new calendar event.

        This tool creates a new event in the specified calendar with full support for:
        - Timed events with specific start/end times
        - All-day events (when date format is YYYY-MM-DD)
        - Event description and location
        - Attendee list with automatic invitation emails
        - Custom reminders (email or popup)
        - Color coding for visual organization
        - Transparency (busy/free status)
        - Visibility settings (default/public/private/confidential)

        The created event is immediately visible in Google Calendar and synced
        across all devices. Attendees (if specified) will receive invitation emails.

        Args:
            arguments: Tool parameters including:
                - summary: Event title (required)
                - start_time: Start time in ISO format (required)
                - end_time: End time in ISO format (required)
                - calendar_id: Target calendar ID (default: 'primary')
                - description: Event description (optional)
                - location: Event location (optional)
                - attendees: List of attendee emails (optional)
                - color_id: Color ID 1-11 (optional)
                - reminders: Reminder configuration object (optional)
                - timezone: Timezone for timed events (optional)
                - transparency: 'opaque' or 'transparent' (default: 'opaque')
                - visibility: Visibility setting (default: 'default')

        Returns:
            ToolResult containing created event details including:
            - Event ID (for future updates/deletions)
            - HTML link to view in Google Calendar
            - Event summary, times, location, attendees
            - All configured properties
        """
        try:
            # Get authenticated service
            service = self._get_service()

            # Extract and validate required parameters
            summary = arguments.get("summary")
            start_time_str = arguments.get("start_time")
            end_time_str = arguments.get("end_time")

            if not summary:
                return ToolResult.fail("Missing required parameter: summary")
            if not start_time_str:
                return ToolResult.fail("Missing required parameter: start_time")
            if not end_time_str:
                return ToolResult.fail("Missing required parameter: end_time")

            # Extract optional parameters with defaults
            calendar_id = arguments.get("calendar_id", "primary")
            description = arguments.get("description", "")
            location = arguments.get("location", "")
            attendees_list = arguments.get("attendees", [])
            color_id = arguments.get("color_id")
            reminders = arguments.get("reminders")
            timezone_str = arguments.get("timezone")
            transparency = arguments.get("transparency", "opaque")
            visibility = arguments.get("visibility", "default")

            # Validate transparency
            if transparency not in ["opaque", "transparent"]:
                return ToolResult.fail(
                    "Invalid transparency value. Must be 'opaque' (busy) or 'transparent' (free)."
                )

            # Validate visibility
            if visibility not in ["default", "public", "private", "confidential"]:
                return ToolResult.fail(
                    "Invalid visibility value. Must be 'default', 'public', 'private', or 'confidential'."
                )

            # Validate color_id if provided
            if color_id is not None:
                # Color IDs are strings "1" through "11"
                if color_id not in [str(i) for i in range(1, 12)]:
                    return ToolResult.fail(
                        "Invalid color_id. Must be a string from '1' to '11'."
                    )

            # Determine timezone
            if timezone_str:
                try:
                    tz = ZoneInfo(timezone_str)
                except Exception:
                    return ToolResult.fail(
                        f"Invalid timezone: {timezone_str}. Use IANA timezone names like 'America/New_York' or 'UTC'."
                    )
            else:
                # Use system local timezone
                try:
                    tz = ZoneInfo("localtime")
                except Exception:
                    tz = ZoneInfo("UTC")

            # Parse start and end times to determine if this is an all-day event
            # All-day events use date format (YYYY-MM-DD)
            # Timed events use datetime format (YYYY-MM-DDTHH:MM:SS)
            is_all_day = False

            # Check if the time strings are date-only format (YYYY-MM-DD)
            # Simple heuristic: if no 'T' separator and length is 10, it's likely a date
            if len(start_time_str) == 10 and "T" not in start_time_str:
                is_all_day = True

            if len(end_time_str) == 10 and "T" not in end_time_str:
                if not is_all_day:
                    return ToolResult.fail(
                        "Start and end times must both be dates (YYYY-MM-DD) or both be datetimes (YYYY-MM-DDTHH:MM:SS)"
                    )
                is_all_day = True
            elif is_all_day:
                return ToolResult.fail(
                    "Start and end times must both be dates (YYYY-MM-DD) or both be datetimes (YYYY-MM-DDTHH:MM:SS)"
                )

            # Build the event object
            event_body = {
                "summary": summary,
                "description": description,
            }

            # Add location if provided
            if location:
                event_body["location"] = location

            # Configure start and end times based on event type
            if is_all_day:
                # All-day event - use date format
                event_body["start"] = {
                    "date": start_time_str,
                }
                event_body["end"] = {
                    "date": end_time_str,
                }
            else:
                # Timed event - use dateTime format with timezone
                # Parse and validate datetime strings
                try:
                    # Try to parse the datetime to validate format
                    start_dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

                    # Ensure end is after start
                    if end_dt <= start_dt:
                        return ToolResult.fail("end_time must be after start_time")

                except ValueError as e:
                    return ToolResult.fail(
                        f"Invalid datetime format: {e}. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
                    )

                event_body["start"] = {
                    "dateTime": start_time_str,
                    "timeZone": str(tz),
                }
                event_body["end"] = {
                    "dateTime": end_time_str,
                    "timeZone": str(tz),
                }

            # Add attendees if provided
            if attendees_list:
                event_body["attendees"] = [{"email": email} for email in attendees_list]

            # Add color if provided
            if color_id:
                event_body["colorId"] = color_id

            # Add reminders if provided
            if reminders:
                event_body["reminders"] = reminders
            # Otherwise, use calendar default reminders (Google's default behavior)

            # Add transparency
            event_body["transparency"] = transparency

            # Add visibility
            event_body["visibility"] = visibility

            # Create the event using Google Calendar API
            created_event = (
                service.events()
                .insert(calendarId=calendar_id, body=event_body, sendUpdates="all")
                .execute()
            )

            # Format the response with all relevant event details
            event_data = {
                "event_id": created_event.get("id"),
                "html_link": created_event.get("htmlLink"),
                "summary": created_event.get("summary"),
                "description": created_event.get("description", ""),
                "location": created_event.get("location", ""),
                "created": created_event.get("created"),
                "updated": created_event.get("updated"),
                "creator": {
                    "email": created_event.get("creator", {}).get("email"),
                    "display_name": created_event.get("creator", {}).get("displayName"),
                },
                "organizer": {
                    "email": created_event.get("organizer", {}).get("email"),
                    "display_name": created_event.get("organizer", {}).get("displayName"),
                },
                "is_all_day": is_all_day,
                "transparency": created_event.get("transparency", "opaque"),
                "visibility": created_event.get("visibility", "default"),
                "status": created_event.get("status", "confirmed"),
                "calendar_id": calendar_id,
            }

            # Add time information based on event type
            if is_all_day:
                event_data["start_date"] = created_event.get("start", {}).get("date")
                event_data["end_date"] = created_event.get("end", {}).get("date")
            else:
                event_data["start_time"] = created_event.get("start", {}).get("dateTime")
                event_data["end_time"] = created_event.get("end", {}).get("dateTime")
                event_data["timezone"] = created_event.get("start", {}).get("timeZone")

            # Add attendees information if present
            if "attendees" in created_event:
                event_data["attendees"] = [
                    {
                        "email": attendee.get("email"),
                        "display_name": attendee.get("displayName"),
                        "response_status": attendee.get("responseStatus", "needsAction"),
                        "organizer": attendee.get("organizer", False),
                    }
                    for attendee in created_event.get("attendees", [])
                ]
                event_data["attendees_count"] = len(event_data["attendees"])
            else:
                event_data["attendees"] = []
                event_data["attendees_count"] = 0

            # Add color information if present
            if "colorId" in created_event:
                event_data["color_id"] = created_event.get("colorId")

            # Add reminders information
            if "reminders" in created_event:
                event_data["reminders"] = created_event.get("reminders")

            return ToolResult.ok(
                event_data,
                message=f"Successfully created event: {summary}",
            )

        except HttpError as e:
            # Handle specific Google Calendar API errors
            if e.resp.status == 404:
                return ToolResult.fail(f"Calendar not found: {calendar_id}")
            elif e.resp.status == 403:
                return ToolResult.fail(
                    f"Permission denied. Check that you have write access to calendar: {calendar_id}"
                )
            else:
                return ToolResult.fail(f"Google Calendar API error: {e}")
        except ValueError as e:
            # Handle authentication errors from _get_service()
            return ToolResult.fail(str(e))
        except Exception as e:
            return ToolResult.fail(f"Error creating event: {e}")

    async def _tool_block_time_for_task(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Tool: Create a calendar time block for a task with Thanos metadata.

        This high-level tool creates a calendar block optimized for task time-blocking.
        It intelligently formats the event description with task details, applies color
        coding based on priority, and embeds Thanos metadata in extended properties for
        future synchronization and tracking.

        Features:
        - Auto-populates event description with task details (project, priority, tags, URL)
        - Applies color scheme based on task priority
        - Adds Thanos metadata to extended properties for tracking
        - Can automatically find a free slot if no time is specified
        - Sets appropriate transparency (marks calendar as busy)
        - Formats event title with task prefix for easy identification

        Args:
            arguments: Tool parameters including:
                - task_id: Unique task identifier (required)
                - task_title: Task title/summary (required)
                - start_time: Start time in ISO format (optional - uses find_free_slots if not provided)
                - end_time: End time in ISO format (optional - calculated from duration if not provided)
                - estimated_duration_minutes: Task duration in minutes (default: 60)
                - calendar_id: Target calendar ID (default: 'primary')
                - task_description: Detailed task description (optional)
                - project: Project name (optional)
                - priority: Priority level: 'high', 'medium', 'low' (optional, default: 'medium')
                - tags: List of task tags (optional)
                - url: URL to task details (optional)
                - location: Event location (optional)
                - timezone: Timezone for the event (optional)
                - auto_schedule: If true and no start_time provided, automatically find free slot (default: false)

        Returns:
            ToolResult containing created event details including:
            - Event ID and HTML link
            - Scheduled start/end times
            - Applied color scheme
            - Thanos metadata confirmation
        """
        try:
            # Extract and validate required parameters
            task_id = arguments.get("task_id")
            task_title = arguments.get("task_title")

            if not task_id:
                return ToolResult.fail("Missing required parameter: task_id")
            if not task_title:
                return ToolResult.fail("Missing required parameter: task_title")

            # Extract optional parameters with defaults
            start_time_str = arguments.get("start_time")
            end_time_str = arguments.get("end_time")
            estimated_duration_minutes = arguments.get("estimated_duration_minutes", 60)
            calendar_id = arguments.get("calendar_id", "primary")
            task_description = arguments.get("task_description", "")
            project = arguments.get("project", "")
            priority = arguments.get("priority", "medium")
            tags = arguments.get("tags", [])
            task_url = arguments.get("url", "")
            location = arguments.get("location", "")
            timezone_str = arguments.get("timezone")
            auto_schedule = arguments.get("auto_schedule", False)

            # Validate priority
            if priority not in ["high", "medium", "low"]:
                return ToolResult.fail(
                    "Invalid priority value. Must be 'high', 'medium', or 'low'."
                )

            # If no start_time provided and auto_schedule is enabled, find a free slot
            if not start_time_str and auto_schedule:
                # Use find_free_slots to find an available time
                free_slots_result = await self._tool_find_free_slots({
                    "duration_minutes": estimated_duration_minutes,
                    "calendar_id": calendar_id,
                    "max_results": 1,
                })

                if not free_slots_result.success:
                    return ToolResult.fail(
                        f"Could not auto-schedule: {free_slots_result.error}"
                    )

                free_slots = free_slots_result.data.get("free_slots", [])
                if not free_slots:
                    return ToolResult.fail(
                        "No free slots available for auto-scheduling. Please specify start_time manually."
                    )

                # Use the first available slot
                first_slot = free_slots[0]
                start_time_str = first_slot.get("start")
                end_time_str = first_slot.get("end")

            # If still no start_time, return error
            if not start_time_str:
                return ToolResult.fail(
                    "Missing required parameter: start_time. Either provide start_time or set auto_schedule=true."
                )

            # Calculate end_time if not provided
            if not end_time_str:
                try:
                    from datetime import timedelta
                    start_dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    end_dt = start_dt + timedelta(minutes=estimated_duration_minutes)
                    end_time_str = end_dt.isoformat()
                except ValueError as e:
                    return ToolResult.fail(
                        f"Invalid start_time format: {e}. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
                    )

            # Build event summary with task prefix
            event_summary = f"🎯 {task_title}"

            # Build rich event description with task details
            description_parts = []

            # Add task description
            if task_description:
                description_parts.append(task_description)
                description_parts.append("")  # Blank line

            # Add task metadata section
            description_parts.append("📋 Task Details")
            description_parts.append("─" * 40)

            if project:
                description_parts.append(f"Project: {project}")

            description_parts.append(f"Priority: {priority.upper()}")

            if tags:
                description_parts.append(f"Tags: {', '.join(tags)}")

            description_parts.append(f"Estimated Duration: {estimated_duration_minutes} minutes")

            if task_url:
                description_parts.append("")
                description_parts.append(f"🔗 Task Link: {task_url}")

            description_parts.append("")
            description_parts.append("─" * 40)
            description_parts.append("⚡ Created by Thanos - Task Time Blocking")

            event_description = "\n".join(description_parts)

            # Determine color based on priority
            # Google Calendar color IDs:
            # 1 = Lavender, 2 = Sage, 3 = Grape, 4 = Flamingo, 5 = Banana
            # 6 = Tangerine, 7 = Peacock, 8 = Graphite, 9 = Blueberry, 10 = Basil, 11 = Tomato
            color_map = {
                "high": "11",      # Tomato (red) for high priority
                "medium": "9",     # Blueberry (blue) for medium priority
                "low": "2",        # Sage (green) for low priority
            }
            color_id = color_map.get(priority, "9")

            # Build extended properties with Thanos metadata
            # Extended properties allow us to embed custom metadata in events
            # This enables future syncing, tracking, and identification of Thanos-created events
            extended_properties = {
                "private": {
                    "thanos_created": "true",
                    "thanos_version": "1.0",
                    "task_id": str(task_id),
                    "task_priority": priority,
                    "created_at": datetime.now().isoformat(),
                }
            }

            # Add optional metadata
            if project:
                extended_properties["private"]["task_project"] = project

            if tags:
                extended_properties["private"]["task_tags"] = ",".join(tags)

            # Get authenticated service
            service = self._get_service()

            # Determine timezone
            if timezone_str:
                try:
                    tz = ZoneInfo(timezone_str)
                except Exception:
                    return ToolResult.fail(
                        f"Invalid timezone: {timezone_str}. Use IANA timezone names like 'America/New_York' or 'UTC'."
                    )
            else:
                # Use system local timezone
                try:
                    tz = ZoneInfo("localtime")
                except Exception:
                    tz = ZoneInfo("UTC")

            # Build the event body
            event_body = {
                "summary": event_summary,
                "description": event_description,
                "start": {
                    "dateTime": start_time_str,
                    "timeZone": str(tz),
                },
                "end": {
                    "dateTime": end_time_str,
                    "timeZone": str(tz),
                },
                "colorId": color_id,
                "transparency": "opaque",  # Mark as busy
                "extendedProperties": extended_properties,
            }

            # Add location if provided
            if location:
                event_body["location"] = location

            # Create the event using Google Calendar API
            created_event = (
                service.events()
                .insert(calendarId=calendar_id, body=event_body, sendUpdates="none")
                .execute()
            )

            # Format the response with all relevant event details
            event_data = {
                "event_id": created_event.get("id"),
                "html_link": created_event.get("htmlLink"),
                "summary": created_event.get("summary"),
                "description": event_description,
                "start_time": created_event.get("start", {}).get("dateTime"),
                "end_time": created_event.get("end", {}).get("dateTime"),
                "timezone": created_event.get("start", {}).get("timeZone"),
                "color_id": color_id,
                "calendar_id": calendar_id,
                "task_metadata": {
                    "task_id": task_id,
                    "task_title": task_title,
                    "project": project,
                    "priority": priority,
                    "tags": tags,
                    "estimated_duration_minutes": estimated_duration_minutes,
                    "task_url": task_url,
                },
                "thanos_metadata": extended_properties["private"],
            }

            # Add location if provided
            if location:
                event_data["location"] = location

            message = f"Successfully created time block for task: {task_title}"
            if auto_schedule:
                message += f" (auto-scheduled at {start_time_str})"

            return ToolResult.ok(event_data, message=message)

        except HttpError as e:
            # Handle specific Google Calendar API errors
            if e.resp.status == 404:
                return ToolResult.fail(f"Calendar not found: {calendar_id}")
            elif e.resp.status == 403:
                return ToolResult.fail(
                    f"Permission denied. Check that you have write access to calendar: {calendar_id}"
                )
            else:
                return ToolResult.fail(f"Google Calendar API error: {e}")
        except ValueError as e:
            # Handle authentication errors from _get_service()
            return ToolResult.fail(str(e))
        except Exception as e:
            return ToolResult.fail(f"Error creating time block: {e}")

    def _calculate_day_quality(
        self, busy_percentage: float, fragmentation_score: float, longest_block_minutes: float
    ) -> str:
        """
        Calculate a qualitative rating for a day's schedule quality.

        Args:
            busy_percentage: Percentage of day that is busy
            fragmentation_score: Fragmentation score for the day
            longest_block_minutes: Duration of longest continuous free block in minutes

        Returns:
            Quality rating: "excellent", "good", "fair", "poor"
        """
        # Excellent: Low busy (<60%), low fragmentation (<50), good longest block (>2h)
        if busy_percentage < 60 and fragmentation_score < 50 and longest_block_minutes >= 120:
            return "excellent"

        # Good: Moderate busy (<75%), moderate fragmentation (<100), decent block (>1h)
        if busy_percentage < 75 and fragmentation_score < 100 and longest_block_minutes >= 60:
            return "good"

        # Fair: High busy (<90%) or high fragmentation but some free time
        if busy_percentage < 90 and longest_block_minutes >= 30:
            return "fair"

        # Poor: Very high busy (>90%) or very fragmented or no significant blocks
        return "poor"

    def _interpret_fragmentation(self, fragmentation_score: float) -> str:
        """
        Provide human-readable interpretation of fragmentation score.

        Args:
            fragmentation_score: Calculated fragmentation score

        Returns:
            Interpretation string
        """
        if fragmentation_score < 50:
            return "Low fragmentation - good for deep work with long, continuous blocks"
        elif fragmentation_score < 100:
            return "Moderate fragmentation - mixed schedule with some context switching"
        elif fragmentation_score < 200:
            return "High fragmentation - many small gaps, significant context switching overhead"
        else:
            return "Very high fragmentation - heavily fragmented schedule, difficult for focused work"

    def _calculate_schedule_health(
        self, busy_percentage: float, fragmentation_score: float, longest_block_hours: float
    ) -> dict[str, Any]:
        """
        Calculate overall schedule health assessment.

        Args:
            busy_percentage: Overall busy percentage
            fragmentation_score: Overall fragmentation score
            longest_block_hours: Longest continuous block in hours

        Returns:
            Dictionary with health rating and recommendations
        """
        # Calculate health score (0-100, higher is better)
        # Factors: busy percentage (lower is better), fragmentation (lower is better), longest block (higher is better)
        busy_score = max(0, 100 - busy_percentage)  # 0-100
        fragmentation_score_normalized = max(0, 100 - (fragmentation_score / 2))  # 0-100
        block_score = min(100, (longest_block_hours / 4) * 100)  # 0-100 (4 hours = perfect)

        overall_score = (busy_score * 0.4 + fragmentation_score_normalized * 0.3 + block_score * 0.3)

        # Determine rating
        if overall_score >= 80:
            rating = "excellent"
            recommendation = "Your schedule is well-balanced with good availability for deep work."
        elif overall_score >= 60:
            rating = "good"
            recommendation = "Your schedule is manageable but could benefit from consolidating meetings."
        elif overall_score >= 40:
            rating = "fair"
            recommendation = "Your schedule is quite busy or fragmented. Consider blocking time for focused work."
        else:
            rating = "needs_attention"
            recommendation = "Your schedule is heavily booked or fragmented. Prioritize protecting time for important work."

        return {
            "rating": rating,
            "score": round(overall_score, 1),
            "recommendation": recommendation,
        }

    def _determine_conflict_type(
        self,
        proposed_start: datetime,
        proposed_end: datetime,
        event_start: datetime,
        event_end: datetime,
    ) -> str:
        """
        Determine the type of conflict between proposed slot and existing event.

        Args:
            proposed_start: Proposed slot start time
            proposed_end: Proposed slot end time
            event_start: Event start time (with buffer applied)
            event_end: Event end time (with buffer applied)

        Returns:
            String describing conflict type: COMPLETE_OVERLAP, PARTIAL_START, PARTIAL_END, ENCLOSED, or ENCLOSES
        """
        # Complete overlap - proposed slot completely overlaps with event
        if proposed_start <= event_start and proposed_end >= event_end:
            return "ENCLOSES"  # Proposed slot completely encloses the event

        # Proposed slot is completely enclosed by event
        if proposed_start >= event_start and proposed_end <= event_end:
            return "ENCLOSED"  # Event completely encloses proposed slot

        # Partial overlap at start
        if proposed_start < event_start and proposed_end > event_start and proposed_end <= event_end:
            return "PARTIAL_START"  # Proposed slot overlaps with event start

        # Partial overlap at end
        if proposed_start >= event_start and proposed_start < event_end and proposed_end > event_end:
            return "PARTIAL_END"  # Proposed slot overlaps with event end

        # Default case (shouldn't happen if conflict detection is correct)
        return "OVERLAP"

    async def close(self):
        """
        Close any open connections.

        Google Calendar API client doesn't maintain persistent connections,
        so this is a no-op for compatibility with BaseAdapter interface.
        """
        self._service = None

    async def health_check(self) -> ToolResult:
        """
        Check Google Calendar API connectivity.

        Returns:
            ToolResult indicating connection status
        """
        if not self.is_authenticated():
            return ToolResult.fail(
                "Not authenticated. Use the 'authorize' tool to connect Google Calendar."
            )

        try:
            service = self._get_service()

            # Simple API call to verify connectivity
            # Get the user's calendar list (lightweight operation)
            service.calendarList().list(maxResults=1).execute()

            return ToolResult.ok(
                {
                    "status": "ok",
                    "adapter": self.name,
                    "api": "connected",
                    "authenticated": True,
                }
            )

        except HttpError as e:
            return ToolResult.fail(f"API error: {e}")
        except Exception as e:
            return ToolResult.fail(f"Health check failed: {e}")
