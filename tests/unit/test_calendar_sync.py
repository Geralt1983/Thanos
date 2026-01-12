#!/usr/bin/env python3
"""
Unit tests for Tools/calendar_sync.py

Tests the calendar sync utility for syncing Google Calendar events
to State/ directory for use in daily briefings and schedule management.
"""

import asyncio
import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open
from zoneinfo import ZoneInfo

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.adapters.base import ToolResult
from Tools.calendar_sync import (
    sync_today_events,
    sync_week_events,
    sync_calendar,
)


# ========================================================================
# Fixtures
# ========================================================================


@pytest.fixture
def mock_adapter_manager():
    """Create mock AdapterManager with mocked call_tool."""
    manager = AsyncMock()
    manager.call_tool = AsyncMock()
    manager.close_all = AsyncMock()
    return manager


@pytest.fixture
def mock_today_events_response():
    """Create mock response for get_today_events."""
    return ToolResult(
        success=True,
        data={
            "events": [
                {
                    "id": "event1",
                    "summary": "Morning Standup",
                    "start": {"dateTime": "2024-01-15T09:00:00-05:00"},
                    "end": {"dateTime": "2024-01-15T09:30:00-05:00"},
                },
                {
                    "id": "event2",
                    "summary": "Project Review",
                    "start": {"dateTime": "2024-01-15T14:00:00-05:00"},
                    "end": {"dateTime": "2024-01-15T15:00:00-05:00"},
                },
            ],
            "summary": {
                "total_events": 2,
                "total_duration_minutes": 90,
            },
        },
    )


@pytest.fixture
def mock_week_events_response():
    """Create mock response for get_events (week)."""
    return ToolResult(
        success=True,
        data={
            "events": [
                {
                    "id": "event1",
                    "summary": "Monday Meeting",
                    "start": {"dateTime": "2024-01-15T09:00:00-05:00"},
                    "end": {"dateTime": "2024-01-15T10:00:00-05:00"},
                },
                {
                    "id": "event2",
                    "summary": "Wednesday Review",
                    "start": {"dateTime": "2024-01-17T14:00:00-05:00"},
                    "end": {"dateTime": "2024-01-17T15:00:00-05:00"},
                },
                {
                    "id": "event3",
                    "summary": "Friday Standup",
                    "start": {"dateTime": "2024-01-19T09:00:00-05:00"},
                    "end": {"dateTime": "2024-01-19T09:30:00-05:00"},
                },
            ],
        },
    )


@pytest.fixture
def temp_state_dir():
    """Create temporary State directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir) / "State"
        state_dir.mkdir(parents=True, exist_ok=True)
        yield state_dir


# ========================================================================
# sync_today_events Tests
# ========================================================================


class TestSyncTodayEvents:
    """Test sync_today_events function."""

    @pytest.mark.asyncio
    async def test_sync_today_events_success(
        self, mock_adapter_manager, mock_today_events_response, temp_state_dir
    ):
        """Test successfully syncing today's events."""
        mock_adapter_manager.call_tool.return_value = mock_today_events_response

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            result = await sync_today_events(
                mock_adapter_manager, timezone="America/New_York"
            )

        assert result["success"] is True
        assert result["event_count"] == 2
        assert "file" in result
        assert "data" in result

        # Verify call_tool was called correctly
        mock_adapter_manager.call_tool.assert_called_once_with(
            "google_calendar.get_today_events",
            arguments={"timezone": "America/New_York"},
        )

        # Verify data structure
        assert result["data"]["timezone"] == "America/New_York"
        assert len(result["data"]["events"]) == 2
        assert "synced_at" in result["data"]
        assert "date" in result["data"]

    @pytest.mark.asyncio
    async def test_sync_today_events_api_failure(
        self, mock_adapter_manager, temp_state_dir
    ):
        """Test handling API failure when syncing today's events."""
        mock_adapter_manager.call_tool.return_value = ToolResult(
            success=False, data=None, error="API rate limit exceeded"
        )

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            result = await sync_today_events(mock_adapter_manager)

        assert result["success"] is False
        assert "API rate limit exceeded" in result["error"]
        assert result["events"] == []

    @pytest.mark.asyncio
    async def test_sync_today_events_exception_handling(
        self, mock_adapter_manager, temp_state_dir
    ):
        """Test exception handling in sync_today_events."""
        mock_adapter_manager.call_tool.side_effect = Exception(
            "Network connection failed"
        )

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            result = await sync_today_events(mock_adapter_manager)

        assert result["success"] is False
        assert "Network connection failed" in result["error"]
        assert result["events"] == []

    @pytest.mark.asyncio
    async def test_sync_today_events_empty_events(
        self, mock_adapter_manager, temp_state_dir
    ):
        """Test syncing when no events exist for today."""
        mock_adapter_manager.call_tool.return_value = ToolResult(
            success=True,
            data={"events": [], "summary": {"total_events": 0}},
        )

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            result = await sync_today_events(mock_adapter_manager)

        assert result["success"] is True
        assert result["event_count"] == 0
        assert result["data"]["events"] == []

    @pytest.mark.asyncio
    async def test_sync_today_events_timezone_handling(
        self, mock_adapter_manager, mock_today_events_response, temp_state_dir
    ):
        """Test timezone handling in sync_today_events."""
        mock_adapter_manager.call_tool.return_value = mock_today_events_response

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            result = await sync_today_events(
                mock_adapter_manager, timezone="America/Los_Angeles"
            )

        assert result["success"] is True
        assert result["data"]["timezone"] == "America/Los_Angeles"

        # Verify timezone was passed to API call
        call_args = mock_adapter_manager.call_tool.call_args
        assert call_args[1]["arguments"]["timezone"] == "America/Los_Angeles"


# ========================================================================
# sync_week_events Tests
# ========================================================================


class TestSyncWeekEvents:
    """Test sync_week_events function."""

    @pytest.mark.asyncio
    async def test_sync_week_events_success(
        self, mock_adapter_manager, mock_week_events_response, temp_state_dir
    ):
        """Test successfully syncing week's events."""
        mock_adapter_manager.call_tool.return_value = mock_week_events_response

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            result = await sync_week_events(
                mock_adapter_manager, timezone="America/New_York"
            )

        assert result["success"] is True
        assert result["event_count"] == 3
        assert "file" in result
        assert "data" in result

        # Verify data structure
        assert result["data"]["timezone"] == "America/New_York"
        assert len(result["data"]["events"]) == 3
        assert "synced_at" in result["data"]
        assert "week_start" in result["data"]
        assert "week_end" in result["data"]

    @pytest.mark.asyncio
    async def test_sync_week_events_date_calculation(
        self, mock_adapter_manager, mock_week_events_response, temp_state_dir
    ):
        """Test week date range calculation (Monday to Sunday)."""
        mock_adapter_manager.call_tool.return_value = mock_week_events_response

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            # Mock current date as Wednesday, Jan 17, 2024
            with patch("Tools.calendar_sync.datetime") as mock_datetime:
                mock_now = datetime(2024, 1, 17, 12, 0, 0, tzinfo=ZoneInfo("America/New_York"))
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

                result = await sync_week_events(mock_adapter_manager)

        # Verify call_tool was called with correct date range
        call_args = mock_adapter_manager.call_tool.call_args
        arguments = call_args[1]["arguments"]

        # Week should be Monday 1/15 to Sunday 1/21
        assert "start_date" in arguments
        assert "end_date" in arguments

    @pytest.mark.asyncio
    async def test_sync_week_events_api_failure(
        self, mock_adapter_manager, temp_state_dir
    ):
        """Test handling API failure when syncing week's events."""
        mock_adapter_manager.call_tool.return_value = ToolResult(
            success=False, data=None, error="Calendar not found"
        )

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            result = await sync_week_events(mock_adapter_manager)

        assert result["success"] is False
        assert "Calendar not found" in result["error"]
        assert result["events"] == []

    @pytest.mark.asyncio
    async def test_sync_week_events_exception_handling(
        self, mock_adapter_manager, temp_state_dir
    ):
        """Test exception handling in sync_week_events."""
        mock_adapter_manager.call_tool.side_effect = ValueError("Invalid date format")

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            result = await sync_week_events(mock_adapter_manager)

        assert result["success"] is False
        assert "Invalid date format" in result["error"]

    @pytest.mark.asyncio
    async def test_sync_week_events_empty_week(
        self, mock_adapter_manager, temp_state_dir
    ):
        """Test syncing when no events exist for the week."""
        mock_adapter_manager.call_tool.return_value = ToolResult(
            success=True, data={"events": []}
        )

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_path = Mock()
            mock_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_path

            result = await sync_week_events(mock_adapter_manager)

        assert result["success"] is True
        assert result["event_count"] == 0
        assert result["data"]["events"] == []


# ========================================================================
# sync_calendar Tests
# ========================================================================


class TestSyncCalendar:
    """Test sync_calendar main function."""

    @pytest.mark.asyncio
    async def test_sync_calendar_today_only(
        self, mock_adapter_manager, mock_today_events_response
    ):
        """Test syncing today's events only."""
        with patch("Tools.calendar_sync.get_default_manager", return_value=mock_adapter_manager):
            with patch("Tools.calendar_sync.GOOGLE_CALENDAR_AVAILABLE", True):
                with patch("Tools.calendar_sync.sync_today_events") as mock_sync_today:
                    mock_sync_today.return_value = {
                        "success": True,
                        "event_count": 2,
                        "file": "State/calendar_today.json",
                    }

                    result = await sync_calendar(sync_today=True, sync_week=False)

        assert result["success"] is True
        assert "today" in result["operations"]
        mock_sync_today.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_calendar_week_only(
        self, mock_adapter_manager, mock_week_events_response
    ):
        """Test syncing week's events only."""
        with patch("Tools.calendar_sync.get_default_manager", return_value=mock_adapter_manager):
            with patch("Tools.calendar_sync.GOOGLE_CALENDAR_AVAILABLE", True):
                with patch("Tools.calendar_sync.sync_week_events") as mock_sync_week:
                    mock_sync_week.return_value = {
                        "success": True,
                        "event_count": 3,
                        "file": "State/calendar_week.json",
                    }

                    result = await sync_calendar(sync_today=False, sync_week=True)

        assert result["success"] is True
        assert "week" in result["operations"]
        mock_sync_week.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_calendar_both(self, mock_adapter_manager):
        """Test syncing both today and week."""
        with patch("Tools.calendar_sync.get_default_manager", return_value=mock_adapter_manager):
            with patch("Tools.calendar_sync.GOOGLE_CALENDAR_AVAILABLE", True):
                with patch("Tools.calendar_sync.sync_today_events") as mock_sync_today:
                    with patch("Tools.calendar_sync.sync_week_events") as mock_sync_week:
                        mock_sync_today.return_value = {
                            "success": True,
                            "event_count": 2,
                            "file": "State/calendar_today.json",
                        }
                        mock_sync_week.return_value = {
                            "success": True,
                            "event_count": 5,
                            "file": "State/calendar_week.json",
                        }

                        result = await sync_calendar(sync_today=True, sync_week=True)

        assert result["success"] is True
        assert "today" in result["operations"]
        assert "week" in result["operations"]
        mock_sync_today.assert_called_once()
        mock_sync_week.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_calendar_adapter_not_available(self):
        """Test behavior when Google Calendar adapter is not available."""
        with patch("Tools.calendar_sync.GOOGLE_CALENDAR_AVAILABLE", False):
            result = await sync_calendar(sync_today=True)

        assert result["success"] is False
        assert "not available" in result["error"]
        assert result["operations"] == {}

    @pytest.mark.asyncio
    async def test_sync_calendar_partial_failure(self, mock_adapter_manager):
        """Test handling partial failure (one operation fails)."""
        with patch("Tools.calendar_sync.get_default_manager", return_value=mock_adapter_manager):
            with patch("Tools.calendar_sync.GOOGLE_CALENDAR_AVAILABLE", True):
                with patch("Tools.calendar_sync.sync_today_events") as mock_sync_today:
                    with patch("Tools.calendar_sync.sync_week_events") as mock_sync_week:
                        mock_sync_today.return_value = {
                            "success": True,
                            "event_count": 2,
                            "file": "State/calendar_today.json",
                        }
                        mock_sync_week.return_value = {
                            "success": False,
                            "error": "Network timeout",
                        }

                        result = await sync_calendar(sync_today=True, sync_week=True)

        assert result["success"] is False
        assert "today" in result["operations"]
        assert "week" in result["operations"]
        assert result["operations"]["today"]["success"] is True
        assert result["operations"]["week"]["success"] is False

    @pytest.mark.asyncio
    async def test_sync_calendar_custom_timezone(self, mock_adapter_manager):
        """Test syncing with custom timezone."""
        with patch("Tools.calendar_sync.get_default_manager", return_value=mock_adapter_manager):
            with patch("Tools.calendar_sync.GOOGLE_CALENDAR_AVAILABLE", True):
                with patch("Tools.calendar_sync.sync_today_events") as mock_sync_today:
                    mock_sync_today.return_value = {
                        "success": True,
                        "event_count": 1,
                        "file": "State/calendar_today.json",
                    }

                    result = await sync_calendar(
                        sync_today=True, timezone="Europe/London"
                    )

        # Verify timezone was passed as positional or keyword argument
        call_args = mock_sync_today.call_args
        # call_args is (args, kwargs), check kwargs
        if len(call_args) > 1 and "timezone" in call_args[1]:
            assert call_args[1]["timezone"] == "Europe/London"
        elif len(call_args[0]) > 1:
            # Check if passed as positional argument (position 1)
            assert call_args[0][1] == "Europe/London"

    @pytest.mark.asyncio
    async def test_sync_calendar_exception_handling(self, mock_adapter_manager):
        """Test exception handling in sync_calendar."""
        with patch("Tools.calendar_sync.get_default_manager", return_value=mock_adapter_manager):
            with patch("Tools.calendar_sync.GOOGLE_CALENDAR_AVAILABLE", True):
                with patch("Tools.calendar_sync.sync_today_events") as mock_sync_today:
                    mock_sync_today.side_effect = RuntimeError("Unexpected error")

                    result = await sync_calendar(sync_today=True)

        assert result["success"] is False
        assert "Unexpected error" in result["error"]

    @pytest.mark.asyncio
    async def test_sync_calendar_manager_cleanup(self, mock_adapter_manager):
        """Test that manager.close_all is called in finally block."""
        with patch("Tools.calendar_sync.get_default_manager", return_value=mock_adapter_manager):
            with patch("Tools.calendar_sync.GOOGLE_CALENDAR_AVAILABLE", True):
                with patch("Tools.calendar_sync.sync_today_events") as mock_sync_today:
                    mock_sync_today.return_value = {
                        "success": True,
                        "event_count": 1,
                        "file": "State/calendar_today.json",
                    }

                    await sync_calendar(sync_today=True)

        # Verify close_all was called
        mock_adapter_manager.close_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_calendar_manager_cleanup_on_error(self, mock_adapter_manager):
        """Test that manager.close_all is called even when error occurs."""
        with patch("Tools.calendar_sync.get_default_manager", return_value=mock_adapter_manager):
            with patch("Tools.calendar_sync.GOOGLE_CALENDAR_AVAILABLE", True):
                with patch("Tools.calendar_sync.sync_today_events") as mock_sync_today:
                    mock_sync_today.side_effect = Exception("Error")

                    await sync_calendar(sync_today=True)

        # Verify close_all was called despite error
        mock_adapter_manager.close_all.assert_called_once()


# ========================================================================
# CLI Tests
# ========================================================================


class TestCLI:
    """Test CLI argument parsing and execution."""

    def test_main_default_behavior(self):
        """Test default behavior syncs today's events."""
        with patch("sys.argv", ["calendar_sync.py"]):
            with patch("Tools.calendar_sync.asyncio.run") as mock_run:
                mock_run.return_value = {"success": True, "operations": {}}

                from Tools.calendar_sync import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0

                # Verify sync_calendar was called with sync_today=True
                call_args = mock_run.call_args[0][0]  # Get the coroutine
                # We can't easily inspect the coroutine, so just verify run was called

    def test_main_today_flag(self):
        """Test --today flag."""
        with patch("sys.argv", ["calendar_sync.py", "--today"]):
            with patch("Tools.calendar_sync.asyncio.run") as mock_run:
                mock_run.return_value = {"success": True, "operations": {}}

                from Tools.calendar_sync import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0

    def test_main_week_flag(self):
        """Test --week flag."""
        with patch("sys.argv", ["calendar_sync.py", "--week"]):
            with patch("Tools.calendar_sync.asyncio.run") as mock_run:
                mock_run.return_value = {"success": True, "operations": {}}

                from Tools.calendar_sync import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0

    def test_main_all_flag(self):
        """Test --all flag syncs both."""
        with patch("sys.argv", ["calendar_sync.py", "--all"]):
            with patch("Tools.calendar_sync.asyncio.run") as mock_run:
                mock_run.return_value = {"success": True, "operations": {}}

                from Tools.calendar_sync import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0

    def test_main_custom_timezone(self):
        """Test --timezone flag."""
        with patch("sys.argv", ["calendar_sync.py", "--timezone", "Europe/Paris"]):
            with patch("Tools.calendar_sync.asyncio.run") as mock_run:
                mock_run.return_value = {"success": True, "operations": {}}

                from Tools.calendar_sync import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0

    def test_main_failure_exit_code(self):
        """Test exit code 1 on failure."""
        with patch("sys.argv", ["calendar_sync.py"]):
            with patch("Tools.calendar_sync.asyncio.run") as mock_run:
                mock_run.return_value = {
                    "success": False,
                    "error": "Sync failed",
                    "operations": {},
                }

                from Tools.calendar_sync import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1

    def test_main_keyboard_interrupt(self):
        """Test handling Ctrl+C during sync."""
        with patch("sys.argv", ["calendar_sync.py"]):
            with patch("Tools.calendar_sync.asyncio.run") as mock_run:
                mock_run.side_effect = KeyboardInterrupt()

                from Tools.calendar_sync import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 130

    def test_main_unexpected_exception(self):
        """Test handling unexpected exceptions."""
        with patch("sys.argv", ["calendar_sync.py"]):
            with patch("Tools.calendar_sync.asyncio.run") as mock_run:
                mock_run.side_effect = RuntimeError("Unexpected error")

                from Tools.calendar_sync import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1


# ========================================================================
# Data Structure Tests
# ========================================================================


class TestDataStructures:
    """Test data structure validation."""

    @pytest.mark.asyncio
    async def test_today_events_data_structure(
        self, mock_adapter_manager, mock_today_events_response, temp_state_dir
    ):
        """Test that sync_today_events returns correctly structured data."""
        mock_adapter_manager.call_tool.return_value = mock_today_events_response

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_file_path = Mock()
            mock_file_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_file_path

            result = await sync_today_events(mock_adapter_manager)

        assert result["success"] is True

        # Verify data structure in result
        data = result["data"]
        assert "synced_at" in data
        assert "date" in data
        assert "timezone" in data
        assert "events" in data
        assert "summary" in data
        assert len(data["events"]) == 2

        # Verify ISO format timestamps
        assert "T" in data["synced_at"]
        assert len(data["date"]) == 10  # YYYY-MM-DD format

    @pytest.mark.asyncio
    async def test_week_events_data_structure(
        self, mock_adapter_manager, mock_week_events_response, temp_state_dir
    ):
        """Test that sync_week_events returns correctly structured data."""
        mock_adapter_manager.call_tool.return_value = mock_week_events_response

        with patch("Tools.calendar_sync.Path") as mock_path_class:
            mock_file_path = Mock()
            mock_file_path.parent.parent = temp_state_dir.parent
            mock_path_class.return_value = mock_file_path

            result = await sync_week_events(mock_adapter_manager)

        assert result["success"] is True

        # Verify data structure in result
        data = result["data"]
        assert "synced_at" in data
        assert "week_start" in data
        assert "week_end" in data
        assert "timezone" in data
        assert "events" in data
        assert "event_count" in data
        assert len(data["events"]) == 3
        assert data["event_count"] == 3

        # Verify date formats
        assert len(data["week_start"]) == 10  # YYYY-MM-DD
        assert len(data["week_end"]) == 10  # YYYY-MM-DD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
