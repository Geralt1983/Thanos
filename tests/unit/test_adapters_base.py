#!/usr/bin/env python3
"""
Unit tests for Tools/adapters/base.py

Tests the ToolResult dataclass and BaseAdapter abstract base class.
"""

from datetime import datetime
import sys
from unittest.mock import Mock

import pytest


# Mock asyncpg before importing adapters (it may not be installed in test env)
sys.modules["asyncpg"] = Mock()

from Tools.adapters.base import BaseAdapter, ToolResult


# ========================================================================
# ToolResult Tests
# ========================================================================


class TestToolResult:
    """Test ToolResult dataclass"""

    def test_success_result_creation(self):
        """Test creating a successful result"""
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert "timestamp" in result.metadata

    def test_failure_result_creation(self):
        """Test creating a failed result"""
        result = ToolResult(success=False, data=None, error="Something went wrong")
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"

    def test_ok_factory_method(self):
        """Test ToolResult.ok factory method"""
        result = ToolResult.ok({"users": [1, 2, 3]})
        assert result.success is True
        assert result.data == {"users": [1, 2, 3]}
        assert result.error is None

    def test_ok_with_metadata(self):
        """Test ToolResult.ok with additional metadata"""
        result = ToolResult.ok({"data": "test"}, source="api", version="v1")
        assert result.success is True
        assert result.metadata.get("source") == "api"
        assert result.metadata.get("version") == "v1"

    def test_fail_factory_method(self):
        """Test ToolResult.fail factory method"""
        result = ToolResult.fail("Connection timeout")
        assert result.success is False
        assert result.data is None
        assert result.error == "Connection timeout"

    def test_fail_with_metadata(self):
        """Test ToolResult.fail with additional metadata"""
        result = ToolResult.fail("Rate limited", retry_after=60)
        assert result.success is False
        assert result.error == "Rate limited"
        assert result.metadata.get("retry_after") == 60

    def test_timestamp_auto_added(self):
        """Test that timestamp is automatically added to metadata"""
        result = ToolResult(success=True, data=None)
        assert "timestamp" in result.metadata
        # Validate timestamp format
        try:
            datetime.fromisoformat(result.metadata["timestamp"])
        except ValueError:
            pytest.fail("Timestamp is not a valid ISO format")

    def test_timestamp_preserved_if_provided(self):
        """Test that provided timestamp is preserved"""
        custom_timestamp = "2024-01-01T12:00:00"
        result = ToolResult(success=True, data=None, metadata={"timestamp": custom_timestamp})
        assert result.metadata["timestamp"] == custom_timestamp

    def test_to_dict_method(self):
        """Test converting ToolResult to dictionary"""
        result = ToolResult(success=True, data={"key": "value"}, error=None)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["data"] == {"key": "value"}
        assert result_dict["error"] is None
        assert "metadata" in result_dict
        assert "timestamp" in result_dict["metadata"]

    def test_to_dict_with_error(self):
        """Test to_dict includes error when present"""
        result = ToolResult.fail("Test error")
        result_dict = result.to_dict()

        assert result_dict["success"] is False
        assert result_dict["error"] == "Test error"
        assert result_dict["data"] is None

    def test_complex_data_types(self):
        """Test ToolResult handles complex data types"""
        complex_data = {
            "list": [1, 2, 3],
            "nested": {"a": {"b": "c"}},
            "none_value": None,
            "boolean": True,
        }
        result = ToolResult.ok(complex_data)
        assert result.data == complex_data

    def test_metadata_is_mutable(self):
        """Test metadata can be modified after creation"""
        result = ToolResult.ok({"data": "test"})
        result.metadata["custom_key"] = "custom_value"
        assert result.metadata["custom_key"] == "custom_value"


# ========================================================================
# BaseAdapter Tests
# ========================================================================


class ConcreteAdapter(BaseAdapter):
    """Concrete implementation for testing BaseAdapter"""

    def __init__(self, adapter_name: str = "test_adapter"):
        self._name = adapter_name
        self._tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {
                    "param1": {"type": "string", "required": True},
                    "param2": {"type": "integer", "required": False},
                },
            },
            {
                "name": "simple_tool",
                "description": "A simple tool with no required params",
                "parameters": {},
            },
        ]

    @property
    def name(self) -> str:
        return self._name

    def list_tools(self):
        return self._tools

    async def call_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        if tool_name == "test_tool":
            return ToolResult.ok({"result": f"Called with {arguments}"})
        elif tool_name == "simple_tool":
            return ToolResult.ok({"result": "simple"})
        return ToolResult.fail(f"Unknown tool: {tool_name}")


class TestBaseAdapter:
    """Test BaseAdapter abstract base class"""

    @pytest.fixture
    def adapter(self):
        """Create a concrete adapter for testing"""
        return ConcreteAdapter()

    def test_name_property(self, adapter):
        """Test adapter name property"""
        assert adapter.name == "test_adapter"

    def test_list_tools(self, adapter):
        """Test list_tools returns tool definitions"""
        tools = adapter.list_tools()
        assert len(tools) == 2
        assert tools[0]["name"] == "test_tool"
        assert tools[1]["name"] == "simple_tool"

    def test_get_tool_exists(self, adapter):
        """Test get_tool returns tool schema when it exists"""
        tool = adapter.get_tool("test_tool")
        assert tool is not None
        assert tool["name"] == "test_tool"
        assert tool["description"] == "A test tool"
        assert "parameters" in tool

    def test_get_tool_not_found(self, adapter):
        """Test get_tool returns None for unknown tool"""
        tool = adapter.get_tool("nonexistent_tool")
        assert tool is None

    def test_validate_arguments_valid(self, adapter):
        """Test validate_arguments with valid arguments"""
        is_valid, error = adapter.validate_arguments("test_tool", {"param1": "value"})
        assert is_valid is True
        assert error is None

    def test_validate_arguments_missing_required(self, adapter):
        """Test validate_arguments catches missing required parameters"""
        is_valid, error = adapter.validate_arguments("test_tool", {})
        assert is_valid is False
        assert "Missing required parameter" in error
        assert "param1" in error

    def test_validate_arguments_unknown_tool(self, adapter):
        """Test validate_arguments with unknown tool"""
        is_valid, error = adapter.validate_arguments("unknown_tool", {})
        assert is_valid is False
        assert "Unknown tool" in error

    def test_validate_arguments_optional_param(self, adapter):
        """Test validate_arguments allows optional parameters to be missing"""
        is_valid, error = adapter.validate_arguments("test_tool", {"param1": "value"})
        assert is_valid is True
        # param2 is optional, so should pass

    def test_validate_arguments_no_params_tool(self, adapter):
        """Test validate_arguments with tool that has no parameters"""
        is_valid, error = adapter.validate_arguments("simple_tool", {})
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_call_tool(self, adapter):
        """Test call_tool executes and returns result"""
        result = await adapter.call_tool("test_tool", {"param1": "test_value"})
        assert result.success is True
        assert "result" in result.data

    @pytest.mark.asyncio
    async def test_call_tool_unknown(self, adapter):
        """Test call_tool with unknown tool returns failure"""
        result = await adapter.call_tool("unknown", {})
        assert result.success is False
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_validated(self, adapter):
        """Test call_tool_validated validates then executes"""
        result = await adapter.call_tool_validated("test_tool", {"param1": "value"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_call_tool_validated_fails_validation(self, adapter):
        """Test call_tool_validated fails for invalid arguments"""
        result = await adapter.call_tool_validated("test_tool", {})
        assert result.success is False
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_close_default(self, adapter):
        """Test close method (default is no-op)"""
        # Should not raise
        await adapter.close()

    @pytest.mark.asyncio
    async def test_health_check_default(self, adapter):
        """Test health_check default implementation"""
        result = await adapter.health_check()
        assert result.success is True
        assert result.data["status"] == "ok"
        assert result.data["adapter"] == "test_adapter"


class TestBaseAdapterCustomName:
    """Test BaseAdapter with custom name"""

    def test_custom_adapter_name(self):
        """Test adapter with custom name"""
        adapter = ConcreteAdapter(adapter_name="custom_name")
        assert adapter.name == "custom_name"

    @pytest.mark.asyncio
    async def test_health_check_shows_custom_name(self):
        """Test health_check returns custom adapter name"""
        adapter = ConcreteAdapter(adapter_name="my_adapter")
        result = await adapter.health_check()
        assert result.data["adapter"] == "my_adapter"


class TestBaseAdapterEdgeCases:
    """Test edge cases for BaseAdapter"""

    def test_empty_tools_list(self):
        """Test adapter with no tools"""

        class EmptyAdapter(BaseAdapter):
            @property
            def name(self):
                return "empty"

            def list_tools(self):
                return []

            async def call_tool(self, tool_name, arguments):
                return ToolResult.fail("No tools available")

        adapter = EmptyAdapter()
        assert adapter.list_tools() == []
        assert adapter.get_tool("any") is None

    def test_tool_without_required_field(self):
        """Test validation when parameter spec lacks 'required' field"""

        class SimpleAdapter(BaseAdapter):
            @property
            def name(self):
                return "simple"

            def list_tools(self):
                return [
                    {
                        "name": "tool1",
                        "description": "test",
                        "parameters": {
                            "param": {"type": "string"}  # No 'required' field
                        },
                    }
                ]

            async def call_tool(self, tool_name, arguments):
                return ToolResult.ok({})

        adapter = SimpleAdapter()
        # Should pass since 'required' defaults to False when not specified
        is_valid, error = adapter.validate_arguments("tool1", {})
        assert is_valid is True
