#!/usr/bin/env python3
"""
Unit tests for Tools/adapters/oura.py

Tests the OuraAdapter class for Oura Ring API integration.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timedelta
import os
import sys

# Mock asyncpg before importing adapters (it may not be installed in test env)
sys.modules['asyncpg'] = Mock()

import httpx

from Tools.adapters.oura import OuraAdapter
from Tools.adapters.base import ToolResult


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def mock_env_token(monkeypatch):
    """Set up mock Oura access token in environment"""
    monkeypatch.setenv("OURA_PERSONAL_ACCESS_TOKEN", "test_token_12345")


@pytest.fixture
def adapter(mock_env_token):
    """Create OuraAdapter with mocked environment token"""
    return OuraAdapter()


@pytest.fixture
def adapter_with_explicit_token():
    """Create OuraAdapter with explicit token"""
    return OuraAdapter(access_token="explicit_token_67890")


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient"""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


# ========================================================================
# Initialization Tests
# ========================================================================

class TestOuraAdapterInit:
    """Test OuraAdapter initialization"""

    def test_init_with_env_token(self, mock_env_token):
        """Test initialization reads token from environment"""
        adapter = OuraAdapter()
        assert adapter.access_token == "test_token_12345"

    def test_init_with_explicit_token(self):
        """Test initialization with explicit token"""
        adapter = OuraAdapter(access_token="my_token")
        assert adapter.access_token == "my_token"

    def test_init_explicit_overrides_env(self, mock_env_token):
        """Test explicit token overrides environment"""
        adapter = OuraAdapter(access_token="override_token")
        assert adapter.access_token == "override_token"

    def test_init_no_token(self, monkeypatch):
        """Test initialization without token available"""
        monkeypatch.delenv("OURA_PERSONAL_ACCESS_TOKEN", raising=False)
        adapter = OuraAdapter()
        assert adapter.access_token is None

    def test_name_property(self, adapter):
        """Test adapter name is 'oura'"""
        assert adapter.name == "oura"

    def test_base_url(self, adapter):
        """Test BASE_URL is correct"""
        assert adapter.BASE_URL == "https://api.ouraring.com/v2"

    def test_client_initially_none(self, adapter):
        """Test HTTP client is None initially"""
        assert adapter._client is None


# ========================================================================
# Tool Listing Tests
# ========================================================================

class TestOuraAdapterListTools:
    """Test list_tools method"""

    def test_list_tools_returns_list(self, adapter):
        """Test list_tools returns a list"""
        tools = adapter.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_list_tools_contains_expected_tools(self, adapter):
        """Test list_tools contains all expected Oura tools"""
        tools = adapter.list_tools()
        tool_names = [t["name"] for t in tools]

        expected_tools = [
            "get_daily_readiness",
            "get_daily_sleep",
            "get_sleep",
            "get_daily_activity",
            "get_daily_stress",
            "get_workout",
            "get_heart_rate",
            "get_personal_info",
            "get_daily_summary",
            "get_today_health"
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"

    def test_tool_schema_structure(self, adapter):
        """Test tool schemas have required fields"""
        tools = adapter.list_tools()
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)
            assert isinstance(tool["parameters"], dict)

    def test_date_parameters(self, adapter):
        """Test date-based tools have start_date and end_date parameters"""
        tools = adapter.list_tools()
        date_tools = ["get_daily_readiness", "get_daily_sleep", "get_sleep"]

        for tool in tools:
            if tool["name"] in date_tools:
                params = tool["parameters"]
                assert "start_date" in params or len(params) == 0


# ========================================================================
# Client Management Tests
# ========================================================================

class TestOuraAdapterClient:
    """Test HTTP client management"""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self, adapter):
        """Test _get_client creates client on first call"""
        client = await adapter._get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        await adapter.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self, adapter):
        """Test _get_client reuses existing client"""
        client1 = await adapter._get_client()
        client2 = await adapter._get_client()
        assert client1 is client2
        await adapter.close()

    @pytest.mark.asyncio
    async def test_get_client_no_token_raises(self, monkeypatch):
        """Test _get_client raises when no token configured"""
        monkeypatch.delenv("OURA_PERSONAL_ACCESS_TOKEN", raising=False)
        adapter = OuraAdapter()

        with pytest.raises(ValueError, match="No Oura access token configured"):
            await adapter._get_client()

    @pytest.mark.asyncio
    async def test_close_clears_client(self, adapter):
        """Test close method clears the client"""
        await adapter._get_client()
        assert adapter._client is not None

        await adapter.close()
        assert adapter._client is None


# ========================================================================
# Tool Execution Tests
# ========================================================================

class TestOuraAdapterCallTool:
    """Test call_tool method"""

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, adapter):
        """Test calling unknown tool returns failure"""
        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_client:
            mock_client.return_value = AsyncMock()
            result = await adapter.call_tool("unknown_tool", {})
            assert result.success is False
            assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_http_error(self, adapter):
        """Test HTTP error handling"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        error = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=mock_response
        )

        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=error)
            mock_get.return_value = mock_client

            result = await adapter.call_tool("get_daily_readiness", {})
            assert result.success is False
            assert "HTTP 401" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_request_error(self, adapter):
        """Test request error handling"""
        error = httpx.RequestError("Connection failed")

        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=error)
            mock_get.return_value = mock_client

            result = await adapter.call_tool("get_daily_readiness", {})
            assert result.success is False
            assert "Request error" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_generic_exception(self, adapter):
        """Test generic exception handling"""
        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Unexpected error")

            result = await adapter.call_tool("get_daily_readiness", {})
            assert result.success is False
            assert "Error" in result.error


# ========================================================================
# Endpoint Fetching Tests
# ========================================================================

class TestOuraAdapterFetchEndpoint:
    """Test _fetch_endpoint method"""

    @pytest.mark.asyncio
    async def test_fetch_endpoint_success(self, adapter):
        """Test successful endpoint fetch"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": [{"score": 85}]}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        result = await adapter._fetch_endpoint(
            mock_client,
            "/usercollection/daily_readiness",
            "2024-01-01",
            "2024-01-01"
        )

        assert result.success is True
        assert result.data == [{"score": 85}]

    @pytest.mark.asyncio
    async def test_fetch_endpoint_with_date_params(self, adapter):
        """Test endpoint fetch passes date parameters"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        await adapter._fetch_endpoint(
            mock_client,
            "/test/endpoint",
            "2024-01-01",
            "2024-01-15"
        )

        mock_client.get.assert_called_once_with(
            "/test/endpoint",
            params={"start_date": "2024-01-01", "end_date": "2024-01-15"}
        )


# ========================================================================
# Special Tool Tests
# ========================================================================

class TestOuraAdapterPersonalInfo:
    """Test get_personal_info tool"""

    @pytest.mark.asyncio
    async def test_get_personal_info_success(self, adapter):
        """Test successful personal info fetch"""
        mock_response = Mock()
        mock_response.json.return_value = {"email": "test@example.com", "age": 30}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        result = await adapter._get_personal_info(mock_client)

        assert result.success is True
        assert result.data["email"] == "test@example.com"


class TestOuraAdapterDailySummary:
    """Test get_daily_summary tool"""

    @pytest.mark.asyncio
    async def test_get_daily_summary_success(self, adapter):
        """Test daily summary combines multiple endpoints"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"score": 80}]}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await adapter._get_daily_summary(mock_client, "2024-01-01", "2024-01-01")

        assert result.success is True
        assert "readiness" in result.data
        assert "sleep" in result.data
        assert "activity" in result.data
        assert "stress" in result.data

    @pytest.mark.asyncio
    async def test_get_daily_summary_partial_failure(self, adapter):
        """Test daily summary handles partial endpoint failures"""
        def mock_get(endpoint, **kwargs):
            response = AsyncMock()
            if "readiness" in endpoint:
                response.status_code = 200
                response.json.return_value = {"data": [{"score": 85}]}
            else:
                response.status_code = 500
            return response

        mock_client = AsyncMock()
        mock_client.get = mock_get

        result = await adapter._get_daily_summary(mock_client, "2024-01-01", "2024-01-01")

        assert result.success is True
        # Should have partial data


class TestOuraAdapterTodayHealth:
    """Test get_today_health tool"""

    @pytest.mark.asyncio
    async def test_get_today_health_success(self, adapter):
        """Test today's health snapshot"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"score": 85, "day": "2024-01-01"}]}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(adapter, '_get_daily_summary', new_callable=AsyncMock) as mock_summary:
            mock_summary.return_value = ToolResult.ok({
                "readiness": [{"score": 85, "day": "2024-01-01"}],
                "sleep": [{"score": 80, "day": "2024-01-01"}],
                "activity": [{"score": 75, "day": "2024-01-01"}],
                "stress": []
            })

            result = await adapter._get_today_health(mock_client)

            assert result.success is True
            assert "date" in result.data
            assert "summary" in result.data


# ========================================================================
# Helper Method Tests
# ========================================================================

class TestOuraAdapterGetLatest:
    """Test _get_latest helper method"""

    def test_get_latest_exact_match(self, adapter):
        """Test _get_latest finds exact date match"""
        items = [
            {"day": "2024-01-01", "score": 80},
            {"day": "2024-01-02", "score": 85},
            {"day": "2024-01-03", "score": 90}
        ]
        result = adapter._get_latest(items, "2024-01-02")
        assert result["score"] == 85

    def test_get_latest_fallback(self, adapter):
        """Test _get_latest falls back to most recent"""
        items = [
            {"day": "2024-01-01", "score": 80},
            {"day": "2024-01-02", "score": 85}
        ]
        result = adapter._get_latest(items, "2024-01-05")
        assert result["score"] == 85  # Last item

    def test_get_latest_empty(self, adapter):
        """Test _get_latest handles empty list"""
        result = adapter._get_latest([], "2024-01-01")
        assert result is None

    def test_get_latest_none_items(self, adapter):
        """Test _get_latest handles None"""
        result = adapter._get_latest(None, "2024-01-01")
        assert result is None


class TestOuraAdapterCalculateSummary:
    """Test _calculate_summary helper method"""

    def test_calculate_summary_excellent(self, adapter):
        """Test summary calculation for excellent scores"""
        snapshot = {
            "readiness": {"score": 90},
            "sleep": {"score": 88},
            "activity": {"score": 85}
        }
        summary = adapter._calculate_summary(snapshot)
        assert summary["overall_status"] == "excellent"
        assert summary["readiness_score"] == 90
        assert summary["sleep_score"] == 88

    def test_calculate_summary_good(self, adapter):
        """Test summary calculation for good scores"""
        snapshot = {
            "readiness": {"score": 75},
            "sleep": {"score": 72},
            "activity": {"score": 70}
        }
        summary = adapter._calculate_summary(snapshot)
        assert summary["overall_status"] == "good"

    def test_calculate_summary_fair(self, adapter):
        """Test summary calculation for fair scores"""
        snapshot = {
            "readiness": {"score": 60},
            "sleep": {"score": 58},
            "activity": {"score": 55}
        }
        summary = adapter._calculate_summary(snapshot)
        assert summary["overall_status"] == "fair"

    def test_calculate_summary_poor(self, adapter):
        """Test summary calculation for poor scores"""
        snapshot = {
            "readiness": {"score": 40},
            "sleep": {"score": 45},
            "activity": {"score": 50}
        }
        summary = adapter._calculate_summary(snapshot)
        assert summary["overall_status"] == "poor"

    def test_calculate_summary_recommendations(self, adapter):
        """Test summary adds recommendations for low scores"""
        snapshot = {
            "readiness": {"score": 60},
            "sleep": {"score": 55},
            "activity": {"score": 70}
        }
        summary = adapter._calculate_summary(snapshot)
        assert len(summary["recommendations"]) > 0
        assert any("recovery" in r.lower() for r in summary["recommendations"])
        assert any("sleep" in r.lower() for r in summary["recommendations"])

    def test_calculate_summary_no_data(self, adapter):
        """Test summary handles missing data"""
        snapshot = {
            "readiness": None,
            "sleep": None,
            "activity": None
        }
        summary = adapter._calculate_summary(snapshot)
        assert summary["overall_status"] == "unknown"
        assert summary["recommendations"] == []


# ========================================================================
# Health Check Tests
# ========================================================================

class TestOuraAdapterHealthCheck:
    """Test health_check method"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, adapter):
        """Test successful health check"""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            result = await adapter.health_check()

            assert result.success is True
            assert result.data["status"] == "ok"
            assert result.data["adapter"] == "oura"
            assert result.data["api"] == "connected"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, adapter):
        """Test health check on API failure"""
        mock_response = AsyncMock()
        mock_response.status_code = 503

        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            result = await adapter.health_check()

            assert result.success is False
            assert "status 503" in result.error

    @pytest.mark.asyncio
    async def test_health_check_exception(self, adapter):
        """Test health check handles exceptions"""
        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await adapter.health_check()

            assert result.success is False
            assert "Health check failed" in result.error


# ========================================================================
# Integration-like Tests
# ========================================================================

class TestOuraAdapterToolRouting:
    """Test tool routing through call_tool"""

    @pytest.mark.asyncio
    async def test_routing_to_personal_info(self, adapter):
        """Test personal_info tool is routed correctly"""
        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            with patch.object(adapter, '_get_personal_info', new_callable=AsyncMock) as mock_personal:
                mock_personal.return_value = ToolResult.ok({"email": "test@test.com"})
                mock_client = AsyncMock()
                mock_get.return_value = mock_client

                result = await adapter.call_tool("get_personal_info", {})

                mock_personal.assert_called_once()
                assert result.success is True

    @pytest.mark.asyncio
    async def test_routing_to_today_health(self, adapter):
        """Test today_health tool is routed correctly"""
        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            with patch.object(adapter, '_get_today_health', new_callable=AsyncMock) as mock_today:
                mock_today.return_value = ToolResult.ok({"date": "2024-01-01"})
                mock_client = AsyncMock()
                mock_get.return_value = mock_client

                result = await adapter.call_tool("get_today_health", {})

                mock_today.assert_called_once()
                assert result.success is True

    @pytest.mark.asyncio
    async def test_routing_to_daily_summary(self, adapter):
        """Test daily_summary tool is routed correctly"""
        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            with patch.object(adapter, '_get_daily_summary', new_callable=AsyncMock) as mock_summary:
                mock_summary.return_value = ToolResult.ok({"readiness": []})
                mock_client = AsyncMock()
                mock_get.return_value = mock_client

                result = await adapter.call_tool("get_daily_summary", {
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-01"
                })

                mock_summary.assert_called_once()
                assert result.success is True

    @pytest.mark.asyncio
    async def test_routing_to_endpoint_tools(self, adapter):
        """Test endpoint-based tools are routed correctly"""
        with patch.object(adapter, '_get_client', new_callable=AsyncMock) as mock_get:
            with patch.object(adapter, '_fetch_endpoint', new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = ToolResult.ok([{"score": 85}])
                mock_client = AsyncMock()
                mock_get.return_value = mock_client

                endpoint_tools = [
                    "get_daily_readiness",
                    "get_daily_sleep",
                    "get_sleep",
                    "get_daily_activity",
                    "get_daily_stress",
                    "get_workout",
                    "get_heart_rate"
                ]

                for tool_name in endpoint_tools:
                    result = await adapter.call_tool(tool_name, {})
                    assert result.success is True, f"Failed for {tool_name}"
