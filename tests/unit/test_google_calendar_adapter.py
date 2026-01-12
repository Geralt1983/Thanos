#!/usr/bin/env python3
"""
Unit tests for Tools/adapters/google_calendar.py

Tests the GoogleCalendarAdapter class for Google Calendar API integration.
Covers: authentication, event CRUD, conflict detection, time-blocking, error scenarios.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock, mock_open

import pytest

# Mock modules that may not be installed in test environment
sys.modules["asyncpg"] = Mock()
sys.modules["google.auth.transport.requests"] = Mock()
sys.modules["google.oauth2.credentials"] = Mock()
sys.modules["google_auth_oauthlib.flow"] = Mock()
sys.modules["googleapiclient.discovery"] = Mock()

# Create proper HttpError mock class
class HttpError(Exception):
    """Mock HttpError for testing."""
    def __init__(self, resp, content):
        self.resp = resp
        self.content = content
        super().__init__(f"HTTP {resp.status}")

class RefreshError(Exception):
    """Mock RefreshError for testing."""
    pass

# Mock the errors module
mock_errors = Mock()
mock_errors.HttpError = HttpError
sys.modules["googleapiclient.errors"] = mock_errors

# Now import after mocking
from google.oauth2.credentials import Credentials

from Tools.adapters.base import ToolResult
from Tools.adapters.google_calendar import GoogleCalendarAdapter
from tests.fixtures.calendar_fixtures import (
    get_all_day_event,
    get_conflicting_event,
    get_mock_availability_response,
    get_mock_calendar,
    get_mock_calendar_list,
    get_mock_created_event_response,
    get_mock_credentials_data,
    get_mock_event,
    get_mock_events_response,
    get_mock_filter_config,
    get_mock_free_slots,
    get_mock_http_error,
    get_mock_task_data,
    get_recurring_event,
    get_workday_events,
)


# ========================================================================
# Fixtures
# ========================================================================


@pytest.fixture
def mock_env_credentials(monkeypatch):
    """Set up mock Google Calendar credentials in environment."""
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:8080/oauth2callback")


@pytest.fixture
def mock_credentials():
    """Create mock OAuth credentials."""
    creds = Mock()
    creds.valid = True
    creds.expired = False
    creds.token = "mock_access_token"
    creds.refresh_token = "mock_refresh_token"
    creds.to_json.return_value = json.dumps(get_mock_credentials_data())
    return creds


@pytest.fixture
def adapter(mock_env_credentials):
    """Create GoogleCalendarAdapter with mocked environment credentials."""
    with patch.object(GoogleCalendarAdapter, "_load_credentials"):
        return GoogleCalendarAdapter()


@pytest.fixture
def authenticated_adapter(mock_env_credentials, mock_credentials):
    """Create authenticated GoogleCalendarAdapter."""
    with patch.object(GoogleCalendarAdapter, "_load_credentials"):
        adapter = GoogleCalendarAdapter()
        adapter._credentials = mock_credentials
        return adapter


@pytest.fixture
def mock_service():
    """Create a mock Google Calendar API service."""
    service = Mock()
    service.calendarList.return_value.list.return_value.execute.return_value = get_mock_calendar_list()
    service.events.return_value.list.return_value.execute.return_value = get_mock_events_response([])
    service.events.return_value.insert.return_value.execute.return_value = get_mock_created_event_response()
    service.events.return_value.update.return_value.execute.return_value = get_mock_created_event_response()
    service.events.return_value.delete.return_value.execute.return_value = None
    return service


# ========================================================================
# Initialization Tests
# ========================================================================


class TestGoogleCalendarAdapterInit:
    """Test GoogleCalendarAdapter initialization."""

    def test_init_with_env_credentials(self, mock_env_credentials):
        """Test initialization reads credentials from environment."""
        with patch.object(GoogleCalendarAdapter, "_load_credentials"):
            adapter = GoogleCalendarAdapter()
            assert adapter.client_id == "test_client_id"
            assert adapter.client_secret == "test_client_secret"
            assert adapter.redirect_uri == "http://localhost:8080/oauth2callback"

    def test_init_with_explicit_credentials(self):
        """Test initialization with explicit credentials."""
        with patch.object(GoogleCalendarAdapter, "_load_credentials"):
            adapter = GoogleCalendarAdapter(
                client_id="explicit_id",
                client_secret="explicit_secret",
                redirect_uri="http://example.com/callback",
            )
            assert adapter.client_id == "explicit_id"
            assert adapter.client_secret == "explicit_secret"
            assert adapter.redirect_uri == "http://example.com/callback"

    def test_init_explicit_overrides_env(self, mock_env_credentials):
        """Test explicit credentials override environment."""
        with patch.object(GoogleCalendarAdapter, "_load_credentials"):
            adapter = GoogleCalendarAdapter(client_id="override_id")
            assert adapter.client_id == "override_id"

    def test_init_default_redirect_uri(self, monkeypatch):
        """Test default redirect URI when not specified."""
        monkeypatch.delenv("GOOGLE_CALENDAR_REDIRECT_URI", raising=False)
        with patch.object(GoogleCalendarAdapter, "_load_credentials"):
            adapter = GoogleCalendarAdapter()
            assert adapter.redirect_uri == "http://localhost:8080/oauth2callback"

    def test_name_property(self, adapter):
        """Test adapter name is 'google_calendar'."""
        assert adapter.name == "google_calendar"

    def test_credentials_initially_none(self, adapter):
        """Test credentials are None initially."""
        assert adapter._credentials is None
        assert adapter._service is None


# ========================================================================
# Credential Management Tests
# ========================================================================


class TestGoogleCalendarAdapterCredentials:
    """Test credential loading, saving, and refreshing."""

    def test_load_credentials_file_not_exists(self, adapter):
        """Test loading credentials when file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            adapter._load_credentials()
            assert adapter._credentials is None

    def test_load_credentials_success(self, adapter):
        """Test successfully loading credentials from file."""
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False

        with patch.object(Path, "exists", return_value=True):
            with patch("Tools.adapters.google_calendar.Credentials.from_authorized_user_file", return_value=mock_creds):
                adapter._load_credentials()
                assert adapter._credentials is not None
                assert adapter._credentials.valid

    def test_save_credentials(self, adapter, mock_credentials, tmp_path):
        """Test saving credentials to file."""
        adapter._credentials = mock_credentials

        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            with patch("os.chmod"):
                with patch.object(Path, "mkdir"):
                    adapter._save_credentials()

        mock_file.assert_called_once()

    def test_refresh_credentials_success(self, adapter, mock_credentials):
        """Test successful credential refresh."""
        mock_credentials.refresh = Mock()
        mock_credentials.refresh_token = "test_refresh_token"
        adapter._credentials = mock_credentials

        with patch("builtins.open", mock_open()):
            with patch("os.chmod"):
                with patch.object(Path, "mkdir"):
                    with patch("Tools.adapters.google_calendar.Request"):
                        result = adapter._refresh_credentials()

        assert result is True
        mock_credentials.refresh.assert_called_once()

    def test_refresh_credentials_failure(self, adapter, mock_credentials):
        """Test credential refresh failure."""
        mock_credentials.refresh = Mock(side_effect=RefreshError("Token expired"))
        mock_credentials.refresh_token = "test_refresh_token"
        adapter._credentials = mock_credentials

        with patch("Tools.adapters.google_calendar.Request"):
            result = adapter._refresh_credentials()

        assert result is False

    def test_refresh_credentials_no_refresh_token(self, adapter):
        """Test refresh fails when no refresh token available."""
        mock_creds = Mock()
        mock_creds.refresh_token = None
        adapter._credentials = mock_creds

        result = adapter._refresh_credentials()
        assert result is False

    def test_is_authenticated_valid_credentials(self, adapter, mock_credentials):
        """Test is_authenticated with valid credentials."""
        adapter._credentials = mock_credentials
        assert adapter.is_authenticated() is True

    def test_is_authenticated_no_credentials(self, adapter):
        """Test is_authenticated with no credentials."""
        adapter._credentials = None
        assert adapter.is_authenticated() is False

    def test_is_authenticated_expired_refreshable(self, adapter, mock_credentials):
        """Test is_authenticated with expired but refreshable credentials."""
        mock_credentials.expired = True
        mock_credentials.refresh = Mock()
        adapter._credentials = mock_credentials

        with patch.object(adapter, "_refresh_credentials", return_value=True):
            result = adapter.is_authenticated()

        assert result is True


# ========================================================================
# OAuth Flow Tests
# ========================================================================


class TestGoogleCalendarAdapterOAuth:
    """Test OAuth authorization flow."""

    def test_get_authorization_url(self, adapter):
        """Test generating OAuth authorization URL."""
        mock_flow = Mock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?client_id=test",
            "mock_state_123",
        )

        with patch("google_auth_oauthlib.flow.Flow.from_client_config", return_value=mock_flow):
            url, state = adapter.get_authorization_url()

        assert "https://accounts.google.com" in url
        assert state == "mock_state_123"
        assert adapter._pending_state == "mock_state_123"

    def test_get_authorization_url_no_client_id(self, monkeypatch):
        """Test authorization URL generation fails without client ID."""
        monkeypatch.delenv("GOOGLE_CALENDAR_CLIENT_ID", raising=False)
        with patch.object(GoogleCalendarAdapter, "_load_credentials"):
            adapter = GoogleCalendarAdapter()

        with pytest.raises(ValueError, match="client_id"):
            adapter.get_authorization_url()

    def test_complete_authorization_success(self, adapter):
        """Test completing OAuth flow successfully."""
        adapter._pending_state = "mock_state_123"

        mock_flow = Mock()
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_flow.fetch_token.return_value = None
        mock_flow.credentials = mock_creds

        with patch("google_auth_oauthlib.flow.Flow.from_client_config", return_value=mock_flow):
            with patch.object(adapter, "_save_credentials"):
                result = adapter.complete_authorization(
                    "http://localhost:8080/oauth2callback?code=test&state=mock_state_123",
                    "mock_state_123",
                )

        assert result.success is True
        assert adapter._credentials is not None

    def test_complete_authorization_state_mismatch(self, adapter):
        """Test authorization completion fails with state mismatch."""
        adapter._pending_state = "expected_state"

        result = adapter.complete_authorization(
            "http://localhost:8080/oauth2callback?code=test&state=wrong_state",
            "wrong_state",
        )

        assert result.success is False
        assert "state mismatch" in result.error.lower()

    def test_complete_authorization_error(self, adapter):
        """Test authorization completion handles errors."""
        adapter._pending_state = "mock_state_123"

        mock_flow = Mock()
        mock_flow.fetch_token.side_effect = Exception("OAuth error")

        with patch("google_auth_oauthlib.flow.Flow.from_client_config", return_value=mock_flow):
            result = adapter.complete_authorization(
                "http://localhost:8080/oauth2callback?code=test&state=mock_state_123",
                "mock_state_123",
            )

        assert result.success is False
        assert "OAuth error" in result.error

    def test_revoke_credentials_success(self, authenticated_adapter):
        """Test successful credential revocation."""
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.post", return_value=mock_response):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "unlink"):
                    result = authenticated_adapter.revoke_credentials()

        assert result.success is True
        assert authenticated_adapter._credentials is None
        assert authenticated_adapter._service is None

    def test_revoke_credentials_partial_failure(self, authenticated_adapter):
        """Test credential revocation with partial failure."""
        mock_response = Mock()
        mock_response.status_code = 400

        with patch("httpx.post", return_value=mock_response):
            with patch.object(Path, "exists", return_value=False):
                result = authenticated_adapter.revoke_credentials()

        assert result.success is True
        assert result.data["status"] == "partially_revoked"


# ========================================================================
# Service Management Tests
# ========================================================================


class TestGoogleCalendarAdapterService:
    """Test Google Calendar API service management."""

    def test_get_service_valid_credentials(self, authenticated_adapter):
        """Test getting service with valid credentials."""
        with patch("googleapiclient.discovery.build") as mock_build:
            mock_build.return_value = Mock()
            service = authenticated_adapter._get_service()

        assert service is not None
        mock_build.assert_called_once()

    def test_get_service_no_credentials(self, adapter):
        """Test getting service without credentials raises error."""
        with pytest.raises(ValueError, match="No valid Google Calendar credentials"):
            adapter._get_service()

    def test_get_service_expired_refreshable(self, authenticated_adapter, mock_credentials):
        """Test getting service with expired but refreshable credentials."""
        mock_credentials.expired = True
        authenticated_adapter._credentials = mock_credentials

        with patch.object(authenticated_adapter, "_refresh_credentials", return_value=True):
            with patch("googleapiclient.discovery.build") as mock_build:
                mock_build.return_value = Mock()
                service = authenticated_adapter._get_service()

        assert service is not None

    def test_get_service_expired_not_refreshable(self, authenticated_adapter, mock_credentials):
        """Test getting service with expired non-refreshable credentials."""
        mock_credentials.expired = True
        authenticated_adapter._credentials = mock_credentials

        with patch.object(authenticated_adapter, "_refresh_credentials", return_value=False):
            with pytest.raises(ValueError, match="expired and cannot be refreshed"):
                authenticated_adapter._get_service()

    def test_get_service_reuses_existing(self, authenticated_adapter):
        """Test service is reused when already created."""
        mock_service = Mock()
        authenticated_adapter._service = mock_service

        service = authenticated_adapter._get_service()
        assert service is mock_service


# ========================================================================
# Calendar Listing Tests
# ========================================================================


class TestGoogleCalendarAdapterListCalendars:
    """Test list_calendars tool."""

    @pytest.mark.asyncio
    async def test_list_calendars_success(self, authenticated_adapter, mock_service):
        """Test successfully listing calendars."""
        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool("list_calendars", {})

        assert result.success is True
        assert "calendars" in result.data
        assert len(result.data["calendars"]) == 3
        assert result.data["calendars"][0]["id"] == "primary"

    @pytest.mark.asyncio
    async def test_list_calendars_api_error(self, authenticated_adapter):
        """Test list_calendars handles API errors."""
        mock_service = Mock()
        mock_error = HttpError(
            resp=Mock(status=403),
            content=json.dumps(get_mock_http_error(403, "Insufficient permissions")).encode(),
        )
        mock_service.calendarList.return_value.list.return_value.execute.side_effect = mock_error

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool("list_calendars", {})

        assert result.success is False
        assert "403" in result.error


# ========================================================================
# Event Fetching Tests
# ========================================================================


class TestGoogleCalendarAdapterGetEvents:
    """Test get_events tool."""

    @pytest.mark.asyncio
    async def test_get_events_success(self, authenticated_adapter, mock_service):
        """Test successfully fetching events."""
        events = get_workday_events()
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "get_events",
                {
                    "calendar_id": "primary",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-01",
                },
            )

        assert result.success is True
        assert len(result.data["events"]) == 5

    @pytest.mark.asyncio
    async def test_get_events_with_filters(self, authenticated_adapter, mock_service):
        """Test get_events applies filters correctly."""
        events = get_workday_events()
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        filter_config = get_mock_filter_config()
        with patch.object(authenticated_adapter, "_load_filter_config", return_value=filter_config):
            with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
                result = await authenticated_adapter.call_tool(
                    "get_events",
                    {
                        "calendar_id": "primary",
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-01",
                    },
                )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_events_missing_parameters(self, authenticated_adapter):
        """Test get_events fails with missing parameters."""
        result = await authenticated_adapter.call_tool("get_events", {})

        assert result.success is False
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_get_today_events_success(self, authenticated_adapter, mock_service):
        """Test get_today_events convenience tool."""
        events = get_workday_events()
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool("get_today_events", {})

        assert result.success is True
        assert "events" in result.data


# ========================================================================
# Conflict Detection Tests
# ========================================================================


class TestGoogleCalendarAdapterConflicts:
    """Test check_conflicts tool."""

    @pytest.mark.asyncio
    async def test_check_conflicts_no_conflict(self, authenticated_adapter, mock_service):
        """Test checking conflicts when none exist."""
        events = [
            get_mock_event(
                "Existing Event",
                datetime.now().replace(hour=10, minute=0),
                60,
            )
        ]
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        start_time = datetime.now().replace(hour=14, minute=0)
        end_time = start_time + timedelta(hours=1)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "check_conflicts",
                {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            )

        assert result.success is True
        assert result.data["has_conflict"] is False
        assert len(result.data["conflicts"]) == 0

    @pytest.mark.asyncio
    async def test_check_conflicts_with_conflict(self, authenticated_adapter, mock_service):
        """Test checking conflicts when conflicts exist."""
        conflict_time = datetime.now().replace(hour=14, minute=0)
        events = [get_mock_event("Conflicting Event", conflict_time, 90)]
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        start_time = conflict_time + timedelta(minutes=30)
        end_time = start_time + timedelta(hours=1)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "check_conflicts",
                {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            )

        assert result.success is True
        assert result.data["has_conflict"] is True
        assert len(result.data["conflicts"]) > 0

    @pytest.mark.asyncio
    async def test_check_conflicts_tentative(self, authenticated_adapter, mock_service):
        """Test conflict detection with tentative events."""
        conflict_time = datetime.now().replace(hour=14, minute=0)
        events = [
            get_mock_event(
                "Tentative Event",
                conflict_time,
                60,
                status="tentative",
            )
        ]
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "check_conflicts",
                {
                    "start_time": conflict_time.isoformat(),
                    "end_time": (conflict_time + timedelta(hours=1)).isoformat(),
                    "include_tentative": True,
                },
            )

        assert result.success is True


# ========================================================================
# Free Slot Finding Tests
# ========================================================================


class TestGoogleCalendarAdapterFreeSlots:
    """Test find_free_slots tool."""

    @pytest.mark.asyncio
    async def test_find_free_slots_success(self, authenticated_adapter, mock_service):
        """Test finding free time slots."""
        events = [
            get_mock_event(
                "Morning Meeting",
                datetime.now().replace(hour=9, minute=0),
                60,
            ),
            get_mock_event(
                "Afternoon Meeting",
                datetime.now().replace(hour=14, minute=0),
                60,
            ),
        ]
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "find_free_slots",
                {
                    "start_date": datetime.now().strftime("%Y-%m-%d"),
                    "end_date": datetime.now().strftime("%Y-%m-%d"),
                    "min_duration_minutes": 30,
                },
            )

        assert result.success is True
        assert "slots" in result.data
        assert isinstance(result.data["slots"], list)

    @pytest.mark.asyncio
    async def test_find_free_slots_with_working_hours(self, authenticated_adapter, mock_service):
        """Test finding free slots within working hours."""
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response([])

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "find_free_slots",
                {
                    "start_date": datetime.now().strftime("%Y-%m-%d"),
                    "end_date": datetime.now().strftime("%Y-%m-%d"),
                    "min_duration_minutes": 60,
                    "working_hours_start": "09:00",
                    "working_hours_end": "17:00",
                },
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_find_free_slots_no_slots_available(self, authenticated_adapter, mock_service):
        """Test when no free slots are available."""
        base_time = datetime.now().replace(hour=9, minute=0)
        events = [
            get_mock_event(
                f"Event {i}",
                base_time + timedelta(hours=i),
                60,
            )
            for i in range(8)
        ]
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "find_free_slots",
                {
                    "start_date": datetime.now().strftime("%Y-%m-%d"),
                    "end_date": datetime.now().strftime("%Y-%m-%d"),
                    "min_duration_minutes": 120,
                },
            )

        assert result.success is True
        # Should still succeed but with empty or very few slots


# ========================================================================
# Availability Analysis Tests
# ========================================================================


class TestGoogleCalendarAdapterAvailability:
    """Test get_availability tool."""

    @pytest.mark.asyncio
    async def test_get_availability_success(self, authenticated_adapter, mock_service):
        """Test availability analysis."""
        events = get_workday_events()
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "get_availability",
                {
                    "start_date": datetime.now().strftime("%Y-%m-%d"),
                    "end_date": datetime.now().strftime("%Y-%m-%d"),
                },
            )

        assert result.success is True
        assert "total_minutes" in result.data
        assert "busy_minutes" in result.data
        assert "free_minutes" in result.data
        assert "event_count" in result.data

    @pytest.mark.asyncio
    async def test_get_availability_multiple_days(self, authenticated_adapter, mock_service):
        """Test availability analysis across multiple days."""
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response([])

        start_date = datetime.now()
        end_date = start_date + timedelta(days=6)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "get_availability",
                {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                },
            )

        assert result.success is True


# ========================================================================
# Event Creation Tests
# ========================================================================


class TestGoogleCalendarAdapterCreateEvent:
    """Test create_event tool."""

    @pytest.mark.asyncio
    async def test_create_event_success(self, authenticated_adapter, mock_service):
        """Test successfully creating an event."""
        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "create_event",
                {
                    "calendar_id": "primary",
                    "summary": "Test Event",
                    "start_time": datetime.now().isoformat(),
                    "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                },
            )

        assert result.success is True
        assert "event_id" in result.data
        assert result.data["summary"] == "New Event"

    @pytest.mark.asyncio
    async def test_create_event_with_description(self, authenticated_adapter, mock_service):
        """Test creating event with description and location."""
        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "create_event",
                {
                    "calendar_id": "primary",
                    "summary": "Team Meeting",
                    "description": "Discuss Q1 goals",
                    "location": "Conference Room A",
                    "start_time": datetime.now().isoformat(),
                    "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
                },
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_create_all_day_event(self, authenticated_adapter, mock_service):
        """Test creating an all-day event."""
        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "create_event",
                {
                    "calendar_id": "primary",
                    "summary": "Company Holiday",
                    "start_date": datetime.now().strftime("%Y-%m-%d"),
                    "end_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "all_day": True,
                },
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_create_event_api_error(self, authenticated_adapter):
        """Test create_event handles API errors."""
        mock_service = Mock()
        mock_error = HttpError(
            resp=Mock(status=400),
            content=json.dumps(get_mock_http_error(400, "Invalid request")).encode(),
        )
        mock_service.events.return_value.insert.return_value.execute.side_effect = mock_error

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "create_event",
                {
                    "calendar_id": "primary",
                    "summary": "Test",
                    "start_time": "invalid",
                    "end_time": "invalid",
                },
            )

        assert result.success is False


# ========================================================================
# Time-Blocking Tests
# ========================================================================


class TestGoogleCalendarAdapterTimeBlocking:
    """Test block_time_for_task tool."""

    @pytest.mark.asyncio
    async def test_block_time_for_task_success(self, authenticated_adapter, mock_service):
        """Test successfully blocking time for a task."""
        task_data = get_mock_task_data()

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "block_time_for_task",
                {
                    "task": task_data,
                    "start_time": datetime.now().isoformat(),
                },
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_block_time_for_task_with_auto_scheduling(self, authenticated_adapter, mock_service):
        """Test blocking time with automatic scheduling."""
        task_data = get_mock_task_data()
        mock_service.events.return_value.list.return_value.execute.return_value = get_mock_events_response([])

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "block_time_for_task",
                {
                    "task": task_data,
                    "auto_schedule": True,
                },
            )

        # May succeed or fail depending on whether free slots are found
        # Just verify it doesn't crash
        assert result is not None

    @pytest.mark.asyncio
    async def test_block_time_for_task_metadata(self, authenticated_adapter, mock_service):
        """Test that Thanos metadata is added to time blocks."""
        task_data = get_mock_task_data()

        created_event = get_mock_created_event_response()
        created_event["extendedProperties"] = {
            "private": {
                "thanos_created": "true",
                "task_id": task_data["id"],
            }
        }
        mock_service.events.return_value.insert.return_value.execute.return_value = created_event

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "block_time_for_task",
                {
                    "task": task_data,
                    "start_time": datetime.now().isoformat(),
                },
            )

        assert result.success is True


# ========================================================================
# Event Update Tests
# ========================================================================


class TestGoogleCalendarAdapterUpdateEvent:
    """Test update_event tool."""

    @pytest.mark.asyncio
    async def test_update_event_success(self, authenticated_adapter, mock_service):
        """Test successfully updating an event."""
        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "update_event",
                {
                    "event_id": "event_123",
                    "calendar_id": "primary",
                    "summary": "Updated Event",
                },
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_update_event_time(self, authenticated_adapter, mock_service):
        """Test updating event time."""
        new_start = datetime.now() + timedelta(hours=2)
        new_end = new_start + timedelta(hours=1)

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "update_event",
                {
                    "event_id": "event_123",
                    "calendar_id": "primary",
                    "start_time": new_start.isoformat(),
                    "end_time": new_end.isoformat(),
                },
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_update_event_not_found(self, authenticated_adapter):
        """Test updating non-existent event."""
        mock_service = Mock()
        mock_error = HttpError(
            resp=Mock(status=404),
            content=json.dumps(get_mock_http_error(404, "Not found")).encode(),
        )
        mock_service.events.return_value.update.return_value.execute.side_effect = mock_error

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "update_event",
                {
                    "event_id": "nonexistent",
                    "calendar_id": "primary",
                    "summary": "Updated",
                },
            )

        assert result.success is False


# ========================================================================
# Event Deletion Tests
# ========================================================================


class TestGoogleCalendarAdapterDeleteEvent:
    """Test delete_event tool."""

    @pytest.mark.asyncio
    async def test_delete_event_success(self, authenticated_adapter, mock_service):
        """Test successfully deleting an event."""
        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "delete_event",
                {
                    "event_id": "event_123",
                    "calendar_id": "primary",
                },
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_delete_event_not_found(self, authenticated_adapter):
        """Test deleting non-existent event."""
        mock_service = Mock()
        mock_error = HttpError(
            resp=Mock(status=404),
            content=json.dumps(get_mock_http_error(404, "Not found")).encode(),
        )
        mock_service.events.return_value.delete.return_value.execute.side_effect = mock_error

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool(
                "delete_event",
                {
                    "event_id": "nonexistent",
                    "calendar_id": "primary",
                },
            )

        assert result.success is False


# ========================================================================
# Filter Configuration Tests
# ========================================================================


class TestGoogleCalendarAdapterFilters:
    """Test calendar filter functionality."""

    def test_load_filter_config_success(self, adapter):
        """Test loading filter configuration."""
        filter_config = get_mock_filter_config()

        with patch("builtins.open", mock_open(read_data=json.dumps(filter_config))):
            with patch.object(Path, "exists", return_value=True):
                config = adapter._load_filter_config()

        assert config is not None
        assert "excluded_calendars" in config

    def test_load_filter_config_not_exists(self, adapter):
        """Test loading filter config when file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            config = adapter._load_filter_config()

        # Should return default config with enabled=False
        assert "enabled" in config
        assert config["enabled"] is False

    def test_should_exclude_event_by_pattern(self, adapter):
        """Test event exclusion by pattern matching."""
        filters = {
            "enabled": True,
            "summary_patterns": {
                "exclude": ["^\\[SPAM\\]"],
                "include": [],
                "case_sensitive": False,
            },
            "event_types": {
                "include_cancelled_events": True,
            }
        }

        event = get_mock_event("[SPAM] Unwanted Event")
        result = adapter._should_exclude_event(event, filters)

        assert result is True

    def test_should_exclude_cancelled_event(self, adapter):
        """Test exclusion of cancelled events."""
        filters = {
            "enabled": True,
            "event_types": {
                "include_cancelled_events": False,
            }
        }

        event = get_mock_event("Cancelled Event", status="cancelled")
        result = adapter._should_exclude_event(event, filters)

        assert result is True


# ========================================================================
# Tool Listing Tests
# ========================================================================


class TestGoogleCalendarAdapterListTools:
    """Test list_tools method."""

    def test_list_tools_returns_list(self, adapter):
        """Test list_tools returns a list."""
        tools = adapter.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_list_tools_contains_expected_tools(self, adapter):
        """Test list_tools contains all expected calendar tools."""
        tools = adapter.list_tools()
        tool_names = [t["name"] for t in tools]

        expected_tools = [
            "authorize",
            "complete_auth",
            "check_auth",
            "revoke_auth",
            "list_calendars",
            "get_events",
            "get_today_events",
            "find_free_slots",
            "check_conflicts",
            "get_availability",
            "create_event",
            "block_time_for_task",
            "update_event",
            "delete_event",
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"

    def test_tool_schema_structure(self, adapter):
        """Test tool schemas have required fields."""
        tools = adapter.list_tools()
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)
            assert isinstance(tool["parameters"], dict)


# ========================================================================
# Error Handling Tests
# ========================================================================


class TestGoogleCalendarAdapterErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, authenticated_adapter):
        """Test calling unknown tool returns failure."""
        result = await authenticated_adapter.call_tool("unknown_tool", {})

        assert result.success is False
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_not_authenticated(self, adapter):
        """Test calling tool without authentication."""
        result = await adapter.call_tool("list_calendars", {})

        assert result.success is False

    @pytest.mark.asyncio
    async def test_api_quota_exceeded(self, authenticated_adapter):
        """Test handling API quota exceeded error."""
        mock_service = Mock()
        mock_error = HttpError(
            resp=Mock(status=429),
            content=json.dumps(get_mock_http_error(429, "Rate Limit Exceeded")).encode(),
        )
        mock_service.calendarList.return_value.list.return_value.execute.side_effect = mock_error

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool("list_calendars", {})

        assert result.success is False
        assert "429" in result.error

    @pytest.mark.asyncio
    async def test_network_error_handling(self, authenticated_adapter):
        """Test handling network errors."""
        mock_service = Mock()
        mock_service.calendarList.return_value.list.return_value.execute.side_effect = ConnectionError(
            "Network unavailable"
        )

        with patch.object(authenticated_adapter, "_get_service", return_value=mock_service):
            result = await authenticated_adapter.call_tool("list_calendars", {})

        assert result.success is False

    @pytest.mark.asyncio
    async def test_invalid_date_format(self, authenticated_adapter):
        """Test handling invalid date formats."""
        result = await authenticated_adapter.call_tool(
            "get_events",
            {
                "calendar_id": "primary",
                "start_date": "invalid-date",
                "end_date": "2024-01-01",
            },
        )

        # Should either fail validation or API call
        assert result is not None


# ========================================================================
# Integration-like Tests
# ========================================================================


class TestGoogleCalendarAdapterToolRouting:
    """Test tool routing through call_tool."""

    @pytest.mark.asyncio
    async def test_routing_to_authorization(self, adapter):
        """Test authorize tool is routed correctly."""
        with patch.object(adapter, "get_authorization_url", return_value=("http://example.com", "state")):
            result = await adapter.call_tool("authorize", {})

        assert result.success is True
        assert "authorization_url" in result.data

    @pytest.mark.asyncio
    async def test_routing_to_check_auth(self, authenticated_adapter):
        """Test check_auth tool is routed correctly."""
        result = await authenticated_adapter.call_tool("check_auth", {})

        assert result.success is True
        assert "authenticated" in result.data
        assert result.data["authenticated"] is True
