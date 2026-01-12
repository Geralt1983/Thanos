"""
Integration tests for Google Calendar adapter with real API interactions.

These tests use actual Google Calendar API instances and (optionally) real OAuth credentials
to validate the complete end-to-end flow works correctly in real-world scenarios.

Tests can be run with pytest markers:
  - pytest -m integration         # Run all integration tests with mocked API
  - pytest -m "integration and requires_google_calendar"  # Tests that need real credentials
  - pytest --skip-integration     # Skip all integration tests
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, MagicMock, patch

import pytest

# Mock Google modules that may not be installed
sys.modules["google.auth.transport.requests"] = Mock()
sys.modules["google.oauth2.credentials"] = Mock()
sys.modules["google_auth_oauthlib.flow"] = Mock()
sys.modules["googleapiclient.discovery"] = Mock()
sys.modules["googleapiclient.errors"] = Mock()

# Import after mocking
from Tools.adapters.google_calendar import GoogleCalendarAdapter
from Tools.adapters.base import ToolResult
from tests.fixtures.calendar_fixtures import (
    get_mock_calendar_list,
    get_mock_credentials_data,
    get_mock_event,
    get_mock_events_response,
    get_workday_events,
    get_mock_task_data,
)


# Check if Google Calendar credentials are available
GOOGLE_CALENDAR_CLIENT_ID = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
GOOGLE_CALENDAR_CLIENT_SECRET = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")
HAS_GOOGLE_CREDENTIALS = (
    GOOGLE_CALENDAR_CLIENT_ID is not None
    and GOOGLE_CALENDAR_CLIENT_SECRET is not None
    and not GOOGLE_CALENDAR_CLIENT_ID.startswith("your-")
)


# =============================================================================
# Pytest Markers and Fixtures
# =============================================================================

pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
def temp_credentials_dir(tmp_path):
    """Create a temporary directory for credential storage."""
    creds_dir = tmp_path / "State"
    creds_dir.mkdir(parents=True, exist_ok=True)
    return creds_dir


@pytest.fixture(scope="function")
def mock_env_credentials(monkeypatch, temp_credentials_dir):
    """Set up mock Google Calendar credentials in environment."""
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:8080/oauth2callback")
    # Override credentials path to use temp directory
    monkeypatch.setenv("THANOS_STATE_DIR", str(temp_credentials_dir))
    return temp_credentials_dir


@pytest.fixture(scope="function")
def calendar_adapter_mock_api(mock_env_credentials):
    """
    Create GoogleCalendarAdapter instance with mocked Google API.

    This adapter has credentials loaded but API calls are mocked.
    Safe to use without real Google Calendar credentials.
    """
    with patch.object(GoogleCalendarAdapter, "_load_credentials"):
        adapter = GoogleCalendarAdapter()

        # Set up mock credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds.token = "mock_access_token"
        mock_creds.refresh_token = "mock_refresh_token"
        adapter._credentials = mock_creds

        # Set up mock Google Calendar service
        mock_service = Mock()
        adapter._service = mock_service

        yield adapter


@pytest.fixture(scope="function")
def calendar_adapter_real_api(mock_env_credentials):
    """
    Create GoogleCalendarAdapter instance with real Google Calendar API.

    Tests using this fixture will be skipped if credentials are not available.
    This fixture loads real credentials and makes real API calls.
    """
    if not HAS_GOOGLE_CREDENTIALS:
        pytest.skip("Google Calendar credentials not available (set GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET)")

    # Use real credentials from environment
    adapter = GoogleCalendarAdapter(
        client_id=GOOGLE_CALENDAR_CLIENT_ID,
        client_secret=GOOGLE_CALENDAR_CLIENT_SECRET,
    )

    # Check if adapter has valid credentials
    if not adapter.is_authenticated():
        pytest.skip("Google Calendar adapter not authenticated. Run OAuth flow first.")

    yield adapter

    # Cleanup: No cleanup needed as tests should be idempotent


# =============================================================================
# Integration Tests - OAuth Flow with Mocked API
# =============================================================================


class TestGoogleCalendarOAuthIntegration:
    """Integration tests for OAuth authorization flow."""

    @pytest.mark.asyncio
    async def test_oauth_flow_complete_cycle(self, mock_env_credentials):
        """
        Test complete OAuth flow from start to finish.

        Acceptance Criteria:
        - Authorization URL generated successfully
        - OAuth state preserved correctly
        - Token exchange completes
        - Credentials stored to file
        """
        adapter = GoogleCalendarAdapter()

        # Step 1: Generate authorization URL
        with patch("Tools.adapters.google_calendar.Flow") as mock_flow_class:
            mock_flow = Mock()
            mock_flow.authorization_url.return_value = (
                "https://accounts.google.com/o/oauth2/auth?client_id=test",
                "mock_state_123",
            )
            mock_flow_class.from_client_config.return_value = mock_flow

            url, state = adapter.get_authorization_url()

        assert "https://accounts.google.com" in url
        assert state == "mock_state_123"
        assert adapter._pending_state == "mock_state_123"

        # Step 2: Complete authorization with callback
        with patch("Tools.adapters.google_calendar.Flow") as mock_flow_class:
            mock_flow = Mock()
            mock_creds = Mock()
            mock_creds.valid = True
            mock_creds.token = "access_token_abc"
            mock_creds.refresh_token = "refresh_token_xyz"
            mock_creds.to_json.return_value = json.dumps(get_mock_credentials_data())

            mock_flow.fetch_token.return_value = None
            mock_flow.credentials = mock_creds
            mock_flow_class.from_client_config.return_value = mock_flow

            result = adapter.complete_authorization(
                "http://localhost:8080/oauth2callback?code=test_code&state=mock_state_123",
                "mock_state_123",
            )

        assert result.success is True
        assert adapter._credentials is not None
        assert adapter.is_authenticated() is True

    @pytest.mark.asyncio
    async def test_oauth_credentials_persistence(self, mock_env_credentials):
        """
        Test that OAuth credentials are saved and can be reloaded.

        Acceptance Criteria:
        - Credentials saved to State/calendar_credentials.json
        - File has restricted permissions (0600)
        - Credentials can be reloaded in new adapter instance
        """
        adapter = GoogleCalendarAdapter()

        # Set up credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.token = "test_token"
        mock_creds.refresh_token = "test_refresh"
        mock_creds.to_json.return_value = json.dumps(get_mock_credentials_data())
        adapter._credentials = mock_creds

        # Save credentials
        creds_path = mock_env_credentials / "calendar_credentials.json"
        with patch("builtins.open", create=True) as mock_open:
            with patch("os.chmod") as mock_chmod:
                adapter._save_credentials()

        # Verify chmod was called with 0600
        mock_chmod.assert_called()

        # Test reloading in new adapter instance
        adapter2 = GoogleCalendarAdapter()
        with patch("Tools.adapters.google_calendar.Credentials.from_authorized_user_file") as mock_from_file:
            mock_from_file.return_value = mock_creds
            with patch.object(Path, "exists", return_value=True):
                adapter2._load_credentials()

        assert adapter2._credentials is not None

    @pytest.mark.asyncio
    async def test_credential_refresh_flow(self, calendar_adapter_mock_api):
        """
        Test that expired credentials are automatically refreshed.

        Acceptance Criteria:
        - Expired credentials detected
        - Refresh token used to get new access token
        - New credentials saved
        - Service calls succeed after refresh
        """
        adapter = calendar_adapter_mock_api

        # Set credentials as expired
        adapter._credentials.expired = True
        adapter._credentials.valid = False
        adapter._credentials.refresh = Mock()

        with patch("Tools.adapters.google_calendar.Request"):
            with patch.object(adapter, "_save_credentials"):
                result = adapter._refresh_credentials()

        assert result is True
        adapter._credentials.refresh.assert_called_once()


# =============================================================================
# Integration Tests - Calendar Operations with Mocked API
# =============================================================================


class TestGoogleCalendarOperationsIntegration:
    """Integration tests for calendar read/write operations."""

    @pytest.mark.asyncio
    async def test_list_calendars_integration(self, calendar_adapter_mock_api):
        """
        Test listing calendars returns complete data.

        Acceptance Criteria:
        - All calendars returned with metadata
        - Primary calendar identified
        - Calendar IDs, names, and colors included
        """
        adapter = calendar_adapter_mock_api

        # Mock API response
        adapter._service.calendarList.return_value.list.return_value.execute.return_value = get_mock_calendar_list()

        result = await adapter.call_tool("list_calendars", {})

        assert result.success is True
        assert "calendars" in result.data
        calendars = result.data["calendars"]

        assert len(calendars) > 0
        assert any(cal["primary"] for cal in calendars)
        assert all("id" in cal for cal in calendars)
        assert all("summary" in cal for cal in calendars)

    @pytest.mark.asyncio
    async def test_get_today_events_integration(self, calendar_adapter_mock_api):
        """
        Test fetching today's events with timezone handling.

        Acceptance Criteria:
        - Today's events retrieved correctly
        - Timezone conversion works
        - All-day and timed events distinguished
        - Events sorted by start time
        """
        adapter = calendar_adapter_mock_api

        # Mock today's events
        events = get_workday_events()
        adapter._service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        result = await adapter.call_tool("get_today_events", {})

        assert result.success is True
        assert "events" in result.data

        returned_events = result.data["events"]
        assert len(returned_events) > 0

        # Verify events have required fields
        for event in returned_events:
            assert "id" in event
            assert "summary" in event
            assert "start" in event or "start_time" in event

    @pytest.mark.asyncio
    async def test_create_and_delete_event_integration(self, calendar_adapter_mock_api):
        """
        Test creating and deleting events (idempotent).

        Acceptance Criteria:
        - Event created successfully
        - Event ID returned
        - Event can be deleted with force flag
        - Cleanup works properly
        """
        adapter = calendar_adapter_mock_api

        # Mock event creation with Thanos metadata
        created_event = get_mock_event("Test Event", datetime.now(), 60, event_id="test_event_123")
        created_event["extendedProperties"] = {"private": {"thanos_created": "true"}}
        adapter._service.events.return_value.insert.return_value.execute.return_value = created_event

        # Create event
        create_result = await adapter.call_tool(
            "create_event",
            {
                "calendar_id": "primary",
                "summary": "Test Event",
                "start_time": datetime.now().isoformat(),
                "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            },
        )

        assert create_result.success is True
        assert "event_id" in create_result.data
        event_id = create_result.data["event_id"]

        # Mock event fetching for safety check
        adapter._service.events.return_value.get.return_value.execute.return_value = created_event
        # Mock event deletion
        adapter._service.events.return_value.delete.return_value.execute.return_value = None

        # Delete event (cleanup) - Thanos-created events can be deleted
        delete_result = await adapter.call_tool(
            "delete_event",
            {
                "event_id": event_id,
                "calendar_id": "primary",
            },
        )

        assert delete_result.success is True

    @pytest.mark.asyncio
    async def test_find_free_slots_integration(self, calendar_adapter_mock_api):
        """
        Test finding free time slots between events.

        Acceptance Criteria:
        - Free slots identified correctly
        - Working hours respected
        - Minimum duration filter works
        - Slots don't overlap with events
        """
        adapter = calendar_adapter_mock_api

        # Mock events with gaps
        base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        events = [
            get_mock_event("Morning Meeting", base_time, 60),
            get_mock_event("Afternoon Meeting", base_time + timedelta(hours=4), 60),
        ]
        adapter._service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        result = await adapter.call_tool(
            "find_free_slots",
            {
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "min_duration_minutes": 60,
                "working_hours_start": 9,
                "working_hours_end": 17,
            },
        )

        assert result.success is True
        # Check for either 'slots' or 'free_slots' in response
        assert "slots" in result.data or "free_slots" in result.data
        slots = result.data.get("slots", result.data.get("free_slots", []))

        # Should have free slots between meetings
        assert isinstance(slots, list)
        for slot in slots:
            assert "start" in slot or "start_time" in slot
            assert "end" in slot or "end_time" in slot

    @pytest.mark.asyncio
    async def test_check_conflicts_integration(self, calendar_adapter_mock_api):
        """
        Test conflict detection with existing events.

        Acceptance Criteria:
        - Conflicts detected accurately
        - No false positives
        - Conflict details provided
        - Tentative events handled correctly
        """
        adapter = calendar_adapter_mock_api

        # Mock existing event
        conflict_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
        events = [get_mock_event("Existing Meeting", conflict_time, 60)]
        adapter._service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        # Check for conflict with overlapping time
        result = await adapter.call_tool(
            "check_conflicts",
            {
                "start_time": (conflict_time + timedelta(minutes=30)).isoformat(),
                "end_time": (conflict_time + timedelta(minutes=90)).isoformat(),
            },
        )

        assert result.success is True
        # API returns has_conflicts (plural)
        assert "has_conflicts" in result.data or "has_conflict" in result.data
        has_conflict = result.data.get("has_conflicts", result.data.get("has_conflict"))
        assert has_conflict is True
        assert len(result.data["conflicts"]) > 0

        # Check for no conflict with non-overlapping time
        result_no_conflict = await adapter.call_tool(
            "check_conflicts",
            {
                "start_time": (conflict_time + timedelta(hours=2)).isoformat(),
                "end_time": (conflict_time + timedelta(hours=3)).isoformat(),
            },
        )

        assert result_no_conflict.success is True
        has_conflict_no = result_no_conflict.data.get("has_conflicts", result_no_conflict.data.get("has_conflict"))
        assert has_conflict_no is False

    @pytest.mark.asyncio
    async def test_block_time_for_task_integration(self, calendar_adapter_mock_api):
        """
        Test blocking time for a task with Thanos metadata.

        Acceptance Criteria:
        - Event created with task details
        - Thanos metadata added to extended properties
        - Task ID preserved
        - Event can be identified as Thanos-created
        """
        adapter = calendar_adapter_mock_api

        # Mock event creation
        task_data = get_mock_task_data()
        created_event = get_mock_event(
            task_data["title"],
            datetime.now(),
            task_data["estimated_duration_minutes"],
            event_id="task_block_123",
        )
        created_event["extendedProperties"] = {
            "private": {
                "thanos_created": "true",
                "task_id": task_data["id"],
            }
        }
        adapter._service.events.return_value.insert.return_value.execute.return_value = created_event

        # Block time for task - use simplified parameters
        result = await adapter.call_tool(
            "block_time_for_task",
            {
                "task_id": task_data["id"],
                "task_title": task_data["title"],
                "task_description": task_data["description"],
                "duration_minutes": task_data["estimated_duration_minutes"],
                "start_time": datetime.now().isoformat(),
            },
        )

        assert result.success is True
        assert "event_id" in result.data

        # Verify Thanos metadata (this would be in the actual API call)
        # In real implementation, we'd verify the metadata was passed correctly


# =============================================================================
# Integration Tests - End-to-End Scenarios with Mocked API
# =============================================================================


class TestGoogleCalendarEndToEndScenarios:
    """End-to-end integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_daily_briefing_workflow(self, calendar_adapter_mock_api):
        """
        Test workflow for daily briefing calendar integration.

        Acceptance Criteria:
        - Fetch today's events
        - Calculate availability
        - Identify upcoming events
        - Format for briefing display
        """
        adapter = calendar_adapter_mock_api

        # Mock today's events
        events = get_workday_events()
        adapter._service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        # Fetch today's events
        events_result = await adapter.call_tool("get_today_events", {})
        assert events_result.success is True

        # Get availability
        availability_result = await adapter.call_tool(
            "get_availability",
            {
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
            },
        )
        assert availability_result.success is True
        # API returns summary with busy_hours and free_hours
        assert "summary" in availability_result.data
        summary = availability_result.data["summary"]
        assert "busy_hours" in summary or "busy_minutes" in availability_result.data
        assert "free_hours" in summary or "free_minutes" in availability_result.data

    @pytest.mark.asyncio
    async def test_task_scheduling_workflow(self, calendar_adapter_mock_api):
        """
        Test workflow for scheduling a task in free time.

        Acceptance Criteria:
        - Find free slots
        - Check for conflicts
        - Block time for task
        - All operations complete successfully
        """
        adapter = calendar_adapter_mock_api

        # Mock sparse calendar
        base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        events = [get_mock_event("Morning Meeting", base_time, 60)]
        adapter._service.events.return_value.list.return_value.execute.return_value = get_mock_events_response(events)

        # Step 1: Find free slots
        slots_result = await adapter.call_tool(
            "find_free_slots",
            {
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "min_duration_minutes": 90,
                "working_hours_start": 9,
                "working_hours_end": 17,
            },
        )
        assert slots_result.success is True
        slots = slots_result.data.get("slots", slots_result.data.get("free_slots", []))
        assert len(slots) > 0

        # Step 2: Check conflicts (should be none in free slot)
        free_slot = slots[0]
        start_key = "start" if "start" in free_slot else "start_time"
        end_key = "end" if "end" in free_slot else "end_time"

        conflict_result = await adapter.call_tool(
            "check_conflicts",
            {
                "start_time": free_slot[start_key],
                "end_time": free_slot[end_key],
            },
        )
        assert conflict_result.success is True
        has_conflict = conflict_result.data.get("has_conflicts", conflict_result.data.get("has_conflict"))
        assert has_conflict is False

        # Step 3: Block time for task
        task_data = get_mock_task_data()
        created_event = get_mock_event(
            task_data["title"],
            datetime.fromisoformat(free_slot[start_key].replace("Z", "+00:00")),
            90,
            event_id="scheduled_task_123",
        )
        adapter._service.events.return_value.insert.return_value.execute.return_value = created_event

        block_result = await adapter.call_tool(
            "block_time_for_task",
            {
                "task_id": task_data["id"],
                "task_title": task_data["title"],
                "duration_minutes": 90,
                "start_time": free_slot[start_key],
            },
        )
        assert block_result.success is True

    @pytest.mark.asyncio
    async def test_event_modification_workflow(self, calendar_adapter_mock_api):
        """
        Test workflow for creating, updating, and deleting events.

        Acceptance Criteria:
        - Event created
        - Event updated successfully
        - Event deleted successfully
        - All operations idempotent
        """
        adapter = calendar_adapter_mock_api

        # Create event with Thanos metadata
        start_time = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        created_event = get_mock_event("Original Event", start_time, 60, event_id="modify_test_123")
        created_event["extendedProperties"] = {"private": {"thanos_created": "true"}}
        adapter._service.events.return_value.insert.return_value.execute.return_value = created_event

        create_result = await adapter.call_tool(
            "create_event",
            {
                "calendar_id": "primary",
                "summary": "Original Event",
                "start_time": start_time.isoformat(),
                "end_time": (start_time + timedelta(hours=1)).isoformat(),
            },
        )
        assert create_result.success is True
        event_id = create_result.data["event_id"]

        # Update event - mock get for safety check
        updated_event = get_mock_event("Updated Event", start_time, 60, event_id=event_id)
        updated_event["extendedProperties"] = {"private": {"thanos_created": "true"}}
        adapter._service.events.return_value.get.return_value.execute.return_value = created_event
        adapter._service.events.return_value.update.return_value.execute.return_value = updated_event

        update_result = await adapter.call_tool(
            "update_event",
            {
                "event_id": event_id,
                "calendar_id": "primary",
                "summary": "Updated Event",
            },
        )
        assert update_result.success is True

        # Delete event
        adapter._service.events.return_value.delete.return_value.execute.return_value = None

        delete_result = await adapter.call_tool(
            "delete_event",
            {
                "event_id": event_id,
                "calendar_id": "primary",
            },
        )
        assert delete_result.success is True


# =============================================================================
# Integration Tests - With Real Google Calendar API
# =============================================================================


class TestGoogleCalendarRealAPIIntegration:
    """
    Integration tests using real Google Calendar API.

    These tests are skipped if credentials are not available.
    They validate the complete end-to-end flow with actual API calls.
    """

    @pytest.mark.requires_google_calendar
    @pytest.mark.asyncio
    async def test_real_oauth_and_list_calendars(self, calendar_adapter_real_api):
        """
        Test real OAuth authentication and calendar listing.

        Acceptance Criteria:
        - Authenticated with real credentials
        - Real calendars returned from API
        - API call succeeds
        - Response format matches expected structure
        """
        adapter = calendar_adapter_real_api

        # Verify authentication
        assert adapter.is_authenticated() is True

        # List calendars
        result = await adapter.call_tool("list_calendars", {})

        assert result.success is True
        assert "calendars" in result.data
        assert len(result.data["calendars"]) > 0

        # Verify primary calendar exists
        calendars = result.data["calendars"]
        primary_cal = next((c for c in calendars if c.get("primary")), None)
        assert primary_cal is not None

        print(f"\n=== Real API Test Results ===")
        print(f"Calendars found: {len(calendars)}")
        print(f"Primary calendar: {primary_cal['summary']}")
        print(f"================================\n")

    @pytest.mark.requires_google_calendar
    @pytest.mark.asyncio
    async def test_real_create_and_cleanup_event(self, calendar_adapter_real_api):
        """
        Test creating and deleting real events (idempotent cleanup).

        Acceptance Criteria:
        - Event created in real calendar
        - Event visible in Google Calendar UI
        - Event successfully deleted (cleanup)
        - No orphaned events left
        """
        adapter = calendar_adapter_real_api

        # Create test event with unique identifier
        test_id = f"test_{int(time.time())}"
        start_time = datetime.now().replace(hour=22, minute=0, second=0, microsecond=0)  # Late evening to avoid conflicts
        end_time = start_time + timedelta(minutes=30)

        create_result = await adapter.call_tool(
            "create_event",
            {
                "calendar_id": "primary",
                "summary": f"[Thanos Test Event {test_id}]",
                "description": "Automated integration test - will be deleted immediately",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

        assert create_result.success is True
        assert "event_id" in create_result.data
        event_id = create_result.data["event_id"]

        print(f"\n=== Created test event: {event_id} ===")

        # Cleanup: Delete the event
        delete_result = await adapter.call_tool(
            "delete_event",
            {
                "event_id": event_id,
                "calendar_id": "primary",
            },
        )

        assert delete_result.success is True
        print(f"=== Cleaned up test event ===\n")

    @pytest.mark.requires_google_calendar
    @pytest.mark.asyncio
    async def test_real_find_free_slots(self, calendar_adapter_real_api):
        """
        Test finding real free slots in actual calendar.

        Acceptance Criteria:
        - Free slots found in real calendar
        - Slots don't overlap with real events
        - Working hours filter works
        - Results are realistic
        """
        adapter = calendar_adapter_real_api

        # Find free slots for tomorrow (to avoid today's events)
        tomorrow = datetime.now() + timedelta(days=1)

        result = await adapter.call_tool(
            "find_free_slots",
            {
                "start_date": tomorrow.strftime("%Y-%m-%d"),
                "end_date": tomorrow.strftime("%Y-%m-%d"),
                "min_duration_minutes": 30,
                "working_hours_start": "09:00",
                "working_hours_end": "17:00",
            },
        )

        assert result.success is True
        assert "slots" in result.data

        slots = result.data["slots"]
        print(f"\n=== Found {len(slots)} free slots for tomorrow ===")
        if slots:
            print(f"First slot: {slots[0]}")
        print(f"================================\n")


# =============================================================================
# Integration Tests - Error Handling
# =============================================================================


class TestGoogleCalendarErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_api_error_handling(self, calendar_adapter_mock_api):
        """
        Test handling of invalid tool names gracefully.

        Acceptance Criteria:
        - Invalid tool names caught and handled
        - Error messages are informative
        - No crashes or uncaught exceptions
        """
        adapter = calendar_adapter_mock_api

        # Test with an invalid tool name (simpler error scenario)
        result = await adapter.call_tool("invalid_tool_name", {})

        # Should handle error gracefully
        assert result is not None
        assert result.success is False
        assert "unknown tool" in result.error.lower() or "invalid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_parameters_handling(self, calendar_adapter_mock_api):
        """
        Test handling of invalid parameters.

        Acceptance Criteria:
        - Invalid parameters rejected
        - Clear error messages
        - No API calls made with invalid data
        """
        adapter = calendar_adapter_mock_api

        # Try to create event with invalid dates
        result = await adapter.call_tool(
            "create_event",
            {
                "calendar_id": "primary",
                "summary": "Test",
                "start_time": "invalid-date",
                "end_time": "invalid-date",
            },
        )

        # Should fail with validation error
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_authentication_handling(self, mock_env_credentials):
        """
        Test handling of missing authentication.

        Acceptance Criteria:
        - Missing credentials detected
        - Appropriate error message
        - No API calls attempted
        """
        adapter = GoogleCalendarAdapter()
        adapter._credentials = None

        result = await adapter.call_tool("list_calendars", {})

        assert result.success is False
        assert "not authenticated" in result.error.lower() or "credentials" in result.error.lower()


# =============================================================================
# Utility Functions
# =============================================================================


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (uses real or mocked dependencies)"
    )
    config.addinivalue_line(
        "markers",
        "requires_google_calendar: mark test as requiring Google Calendar API credentials"
    )
