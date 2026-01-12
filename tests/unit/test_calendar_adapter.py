#!/usr/bin/env python3
"""
Unit tests for Tools/adapters/calendar_adapter.py

Tests the unified CalendarAdapter wrapper that provides a consistent interface
across multiple calendar providers. Currently wraps GoogleCalendarAdapter with
future support planned for Apple Calendar.
"""

import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Mock modules that may not be installed in test environment
sys.modules["asyncpg"] = Mock()
sys.modules["google.auth.transport.requests"] = Mock()
sys.modules["google.oauth2.credentials"] = Mock()
sys.modules["google_auth_oauthlib.flow"] = Mock()
sys.modules["googleapiclient.discovery"] = Mock()
sys.modules["googleapiclient.errors"] = Mock()

from Tools.adapters.base import ToolResult
from Tools.adapters.calendar_adapter import CalendarAdapter
from Tools.adapters.google_calendar import GoogleCalendarAdapter


# ========================================================================
# Fixtures
# ========================================================================


@pytest.fixture
def mock_google_adapter():
    """Create a mock GoogleCalendarAdapter."""
    adapter = Mock(spec=GoogleCalendarAdapter)
    adapter.name = "google_calendar"
    adapter.list_tools.return_value = [
        {
            "name": "get_events",
            "description": "Get calendar events",
            "parameters": {
                "calendar_id": {"type": "string", "required": True},
                "start_date": {"type": "string", "required": True},
            },
        },
        {
            "name": "create_event",
            "description": "Create a calendar event",
            "parameters": {
                "summary": {"type": "string", "required": True},
            },
        },
    ]
    adapter.get_tool.return_value = {
        "name": "get_events",
        "description": "Get calendar events",
        "parameters": {},
    }
    adapter.validate_arguments.return_value = (True, None)
    adapter.call_tool = AsyncMock(
        return_value=ToolResult.ok({"events": []})
    )
    adapter.close = AsyncMock()
    adapter.health_check = AsyncMock(
        return_value=ToolResult.ok({"status": "healthy"})
    )
    return adapter


@pytest.fixture
def adapter(mock_google_adapter):
    """Create CalendarAdapter with mocked GoogleCalendarAdapter."""
    with patch(
        "Tools.adapters.calendar_adapter.GoogleCalendarAdapter",
        return_value=mock_google_adapter,
    ):
        return CalendarAdapter(provider="google")


# ========================================================================
# Initialization Tests
# ========================================================================


class TestCalendarAdapterInit:
    """Test CalendarAdapter initialization."""

    def test_init_default_provider(self, mock_google_adapter):
        """Test initialization with default provider (google)."""
        with patch(
            "Tools.adapters.calendar_adapter.GoogleCalendarAdapter",
            return_value=mock_google_adapter,
        ) as mock_class:
            adapter = CalendarAdapter()

            assert adapter.provider == "google"
            assert adapter.underlying_adapter == mock_google_adapter
            mock_class.assert_called_once_with(
                client_id=None,
                client_secret=None,
                redirect_uri=None,
            )

    def test_init_explicit_google_provider(self, mock_google_adapter):
        """Test initialization with explicit google provider."""
        with patch(
            "Tools.adapters.calendar_adapter.GoogleCalendarAdapter",
            return_value=mock_google_adapter,
        ) as mock_class:
            adapter = CalendarAdapter(provider="google")

            assert adapter.provider == "google"
            assert adapter.underlying_adapter == mock_google_adapter
            mock_class.assert_called_once()

    def test_init_with_google_credentials(self, mock_google_adapter):
        """Test initialization passes credentials to GoogleCalendarAdapter."""
        with patch(
            "Tools.adapters.calendar_adapter.GoogleCalendarAdapter",
            return_value=mock_google_adapter,
        ) as mock_class:
            adapter = CalendarAdapter(
                provider="google",
                client_id="test_id",
                client_secret="test_secret",
                redirect_uri="http://test.com/callback",
            )

            mock_class.assert_called_once_with(
                client_id="test_id",
                client_secret="test_secret",
                redirect_uri="http://test.com/callback",
            )

    def test_init_apple_provider_not_implemented(self):
        """Test initialization with apple provider raises error."""
        with pytest.raises(ValueError, match="Apple Calendar provider is not yet implemented"):
            CalendarAdapter(provider="apple")

    def test_init_unsupported_provider(self):
        """Test initialization with unsupported provider raises error."""
        with pytest.raises(ValueError, match="Unsupported calendar provider: outlook"):
            CalendarAdapter(provider="outlook")

    def test_name_property(self, adapter):
        """Test adapter name is 'calendar'."""
        assert adapter.name == "calendar"

    def test_provider_property(self, adapter):
        """Test provider property returns current provider."""
        assert adapter.provider == "google"

    def test_underlying_adapter_property(self, adapter, mock_google_adapter):
        """Test underlying_adapter property returns wrapped adapter."""
        assert adapter.underlying_adapter == mock_google_adapter


# ========================================================================
# Tool Listing Tests
# ========================================================================


class TestCalendarAdapterListTools:
    """Test list_tools proxying."""

    def test_list_tools_proxies_to_underlying(self, adapter, mock_google_adapter):
        """Test list_tools proxies to underlying adapter."""
        tools = adapter.list_tools()

        assert tools == mock_google_adapter.list_tools.return_value
        mock_google_adapter.list_tools.assert_called_once()

    def test_list_tools_returns_list(self, adapter):
        """Test list_tools returns a list."""
        tools = adapter.list_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_get_tool_proxies_to_underlying(self, adapter, mock_google_adapter):
        """Test get_tool proxies to underlying adapter."""
        tool = adapter.get_tool("get_events")

        assert tool == mock_google_adapter.get_tool.return_value
        mock_google_adapter.get_tool.assert_called_once_with("get_events")

    def test_validate_arguments_proxies_to_underlying(self, adapter, mock_google_adapter):
        """Test validate_arguments proxies to underlying adapter."""
        is_valid, error = adapter.validate_arguments(
            "get_events",
            {"calendar_id": "primary", "start_date": "2024-01-01"},
        )

        assert is_valid is True
        assert error is None
        mock_google_adapter.validate_arguments.assert_called_once_with(
            "get_events",
            {"calendar_id": "primary", "start_date": "2024-01-01"},
        )


# ========================================================================
# Tool Execution Tests
# ========================================================================


class TestCalendarAdapterCallTool:
    """Test call_tool proxying and error handling."""

    @pytest.mark.asyncio
    async def test_call_tool_proxies_to_underlying(self, adapter, mock_google_adapter):
        """Test call_tool proxies to underlying adapter."""
        result = await adapter.call_tool(
            "get_events",
            {"calendar_id": "primary", "start_date": "2024-01-01"},
        )

        assert result.success is True
        assert "events" in result.data
        mock_google_adapter.call_tool.assert_called_once_with(
            "get_events",
            {"calendar_id": "primary", "start_date": "2024-01-01"},
        )

    @pytest.mark.asyncio
    async def test_call_tool_success_result(self, adapter, mock_google_adapter):
        """Test call_tool returns successful ToolResult."""
        mock_google_adapter.call_tool.return_value = ToolResult.ok(
            {"events": [{"id": "event_1", "summary": "Test Event"}]}
        )

        result = await adapter.call_tool("get_events", {})

        assert result.success is True
        assert len(result.data["events"]) == 1

    @pytest.mark.asyncio
    async def test_call_tool_failure_result(self, adapter, mock_google_adapter):
        """Test call_tool propagates failure from underlying adapter."""
        mock_google_adapter.call_tool.return_value = ToolResult.fail(
            "API error: Invalid request"
        )

        result = await adapter.call_tool("get_events", {})

        assert result.success is False
        assert "API error" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_exception_handling(self, adapter, mock_google_adapter):
        """Test call_tool wraps exceptions in ToolResult.fail."""
        mock_google_adapter.call_tool.side_effect = Exception("Network error")

        result = await adapter.call_tool("get_events", {})

        assert result.success is False
        assert "Calendar adapter error" in result.error
        assert "Network error" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_exception_includes_metadata(self, adapter, mock_google_adapter):
        """Test exception result includes provider and tool_name metadata."""
        mock_google_adapter.call_tool.side_effect = ValueError("Invalid parameter")

        result = await adapter.call_tool("create_event", {"summary": "Test"})

        assert result.success is False
        assert result.metadata.get("provider") == "google"
        assert result.metadata.get("tool_name") == "create_event"

    @pytest.mark.asyncio
    async def test_call_tool_multiple_tools(self, adapter, mock_google_adapter):
        """Test calling different tools proxies correctly."""
        mock_google_adapter.call_tool.return_value = ToolResult.ok(
            {"event_id": "new_event_123"}
        )

        result1 = await adapter.call_tool("create_event", {"summary": "Meeting"})
        result2 = await adapter.call_tool("delete_event", {"event_id": "123"})

        assert result1.success is True
        assert result2.success is True
        assert mock_google_adapter.call_tool.call_count == 2


# ========================================================================
# Lifecycle Management Tests
# ========================================================================


class TestCalendarAdapterLifecycle:
    """Test close and health_check methods."""

    @pytest.mark.asyncio
    async def test_close_proxies_to_underlying(self, adapter, mock_google_adapter):
        """Test close proxies to underlying adapter."""
        await adapter.close()

        mock_google_adapter.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_proxies_to_underlying(self, adapter, mock_google_adapter):
        """Test health_check proxies to underlying adapter."""
        result = await adapter.health_check()

        assert result.success is True
        mock_google_adapter.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_enhances_with_provider_info(self, adapter, mock_google_adapter):
        """Test health_check adds provider and adapter info to result."""
        mock_google_adapter.health_check.return_value = ToolResult.ok(
            {"status": "healthy", "connection": "active"}
        )

        result = await adapter.health_check()

        assert result.success is True
        assert result.data["status"] == "healthy"
        assert result.data["provider"] == "google"
        assert result.data["adapter"] == "calendar"
        assert result.data["connection"] == "active"

    @pytest.mark.asyncio
    async def test_health_check_handles_non_dict_data(self, adapter, mock_google_adapter):
        """Test health_check handles non-dict data gracefully."""
        mock_google_adapter.health_check.return_value = ToolResult.ok("healthy")

        result = await adapter.health_check()

        assert result.success is True
        assert result.data == "healthy"
        # Should not crash when data is not a dict

    @pytest.mark.asyncio
    async def test_health_check_propagates_failure(self, adapter, mock_google_adapter):
        """Test health_check propagates failures from underlying adapter."""
        mock_google_adapter.health_check.return_value = ToolResult.fail(
            "Connection failed"
        )

        result = await adapter.health_check()

        assert result.success is False
        assert "Connection failed" in result.error


# ========================================================================
# Provider-Specific Tests
# ========================================================================


class TestCalendarAdapterProviders:
    """Test provider-specific behavior."""

    def test_google_provider_creates_google_adapter(self, mock_google_adapter):
        """Test google provider creates GoogleCalendarAdapter."""
        with patch(
            "Tools.adapters.calendar_adapter.GoogleCalendarAdapter",
            return_value=mock_google_adapter,
        ) as mock_class:
            adapter = CalendarAdapter(provider="google")

            assert isinstance(adapter.underlying_adapter, Mock)
            mock_class.assert_called_once()

    def test_multiple_instances_use_separate_adapters(self, mock_google_adapter):
        """Test multiple CalendarAdapter instances have separate underlying adapters."""
        mock1 = Mock(spec=GoogleCalendarAdapter)
        mock2 = Mock(spec=GoogleCalendarAdapter)

        with patch(
            "Tools.adapters.calendar_adapter.GoogleCalendarAdapter",
            side_effect=[mock1, mock2],
        ):
            adapter1 = CalendarAdapter(provider="google")
            adapter2 = CalendarAdapter(provider="google")

            assert adapter1.underlying_adapter != adapter2.underlying_adapter
            assert adapter1.underlying_adapter == mock1
            assert adapter2.underlying_adapter == mock2


# ========================================================================
# Integration-Like Tests
# ========================================================================


class TestCalendarAdapterIntegration:
    """Test end-to-end flows through CalendarAdapter."""

    @pytest.mark.asyncio
    async def test_full_tool_workflow(self, adapter, mock_google_adapter):
        """Test complete workflow: list tools, validate, call tool."""
        # List available tools
        tools = adapter.list_tools()
        assert len(tools) > 0

        # Validate arguments
        is_valid, error = adapter.validate_arguments(
            "get_events",
            {"calendar_id": "primary", "start_date": "2024-01-01"},
        )
        assert is_valid is True

        # Call tool
        result = await adapter.call_tool(
            "get_events",
            {"calendar_id": "primary", "start_date": "2024-01-01"},
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, adapter, mock_google_adapter):
        """Test error handling and recovery."""
        # First call fails
        mock_google_adapter.call_tool.return_value = ToolResult.fail("API error")
        result1 = await adapter.call_tool("get_events", {})
        assert result1.success is False

        # Second call succeeds
        mock_google_adapter.call_tool.return_value = ToolResult.ok({"events": []})
        result2 = await adapter.call_tool("get_events", {})
        assert result2.success is True

    @pytest.mark.asyncio
    async def test_health_check_before_operations(self, adapter, mock_google_adapter):
        """Test health check before performing operations."""
        # Check health
        health = await adapter.health_check()
        assert health.success is True
        assert health.data["provider"] == "google"

        # Perform operation
        result = await adapter.call_tool("get_events", {})
        assert result.success is True


# ========================================================================
# Logging Tests
# ========================================================================


class TestCalendarAdapterLogging:
    """Test logging behavior."""

    def test_init_logs_provider(self, mock_google_adapter, caplog):
        """Test initialization logs the provider being used."""
        import logging

        with caplog.at_level(logging.INFO):
            with patch(
                "Tools.adapters.calendar_adapter.GoogleCalendarAdapter",
                return_value=mock_google_adapter,
            ):
                adapter = CalendarAdapter(provider="google")

        assert any(
            "Initialized CalendarAdapter with provider: google" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_call_tool_logs_proxy_operation(self, adapter, mock_google_adapter, caplog):
        """Test call_tool logs the proxy operation."""
        import logging

        with caplog.at_level(logging.DEBUG):
            await adapter.call_tool("get_events", {})

        assert any(
            "CalendarAdapter proxying get_events to google provider" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_error_logging(self, adapter, mock_google_adapter, caplog):
        """Test errors are logged with details."""
        import logging

        mock_google_adapter.call_tool.side_effect = Exception("Test error")

        with caplog.at_level(logging.ERROR):
            await adapter.call_tool("create_event", {})

        assert any(
            "Error in CalendarAdapter.call_tool(create_event)" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_close_logs_operation(self, adapter, mock_google_adapter, caplog):
        """Test close operation is logged."""
        import logging

        with caplog.at_level(logging.DEBUG):
            await adapter.close()

        assert any(
            "Closing CalendarAdapter (google provider)" in record.message
            for record in caplog.records
        )
