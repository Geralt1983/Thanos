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
