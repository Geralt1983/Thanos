"""
Google Calendar API adapter for Thanos.

Provides OAuth 2.0 authentication and access to Google Calendar API
for calendar integration, event management, and scheduling intelligence.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

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
                    "reminders": event.get("reminders"),
                    "conference_data": event.get("conferenceData"),
                }

                formatted_events.append(formatted_event)

            # Sort events by start time (for non-single-event queries)
            if not single_events:
                formatted_events.sort(key=lambda e: e["start"] or "")

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
            calendar_list = service.calendarList().list(maxResults=1).execute()

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
