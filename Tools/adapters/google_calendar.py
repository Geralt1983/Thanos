"""
Google Calendar API adapter for Thanos.

Provides OAuth 2.0 authentication and access to Google Calendar API
for calendar integration, event management, and scheduling intelligence.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base import BaseAdapter, ToolResult


class GoogleCalendarAdapter(BaseAdapter):
    """Direct adapter for Google Calendar API with OAuth 2.0 authentication."""

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
        except Exception as e:
            # Credentials file is corrupted or invalid
            # We'll need to re-authenticate
            pass

    def _save_credentials(self) -> None:
        """Save OAuth credentials to storage."""
        if not self._credentials:
            return

        creds_path = self._get_credentials_path()

        # Ensure the State directory exists
        creds_path.parent.mkdir(parents=True, exist_ok=True)

        # Save credentials to file
        with open(creds_path, "w") as f:
            f.write(self._credentials.to_json())

        # Set restrictive permissions (0600 - owner read/write only)
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
            return True
        except Exception:
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

            return ToolResult.ok(
                {
                    "status": "authenticated",
                    "scopes": self.SCOPES,
                    "expires_at": (
                        self._credentials.expiry.isoformat()
                        if self._credentials.expiry
                        else None
                    ),
                }
            )

        except Exception as e:
            return ToolResult.fail(f"Authorization failed: {e}")

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
