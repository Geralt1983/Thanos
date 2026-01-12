"""
Tests for MCP migration utilities.

Tests cover:
- Tool comparison between direct adapters and MCP bridges
- Migration validation and result comparison
- Configuration generation
- Migration report generation
- Helper functions
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from Tools.adapters.base import BaseAdapter, ToolResult
from Tools.adapters.mcp_migration import (
    ComparisonType,
    MigrationAnalyzer,
    MigrationStatus,
    ToolComparison,
    ValidationResult,
    compare_tools,
    generate_mcp_config,
    get_migration_checklist,
    save_mcp_config,
    validate_migration,
    generate_migration_script,
)


# Mock adapter for testing
class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""

    def __init__(self, name: str, tools: List[Dict[str, Any]]):
        self._name = name
        self._tools = tools
        self._call_results = {}

    @property
    def name(self) -> str:
        return self._name

    def list_tools(self) -> List[Dict[str, Any]]:
        return self._tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        # Return predefined result or success by default
        if tool_name in self._call_results:
            return self._call_results[tool_name]

        return ToolResult(
            success=True,
            data={"result": f"Called {tool_name} with {arguments}"},
        )

    async def health_check(self) -> bool:
        return True

    async def close(self) -> None:
        pass

    def set_call_result(self, tool_name: str, result: ToolResult) -> None:
        """Set a predefined result for a tool call."""
        self._call_results[tool_name] = result


# Test fixtures
@pytest.fixture
def direct_adapter():
    """Create a mock direct adapter."""
    tools = [
        {
            "name": "get_tasks",
            "description": "Get all tasks",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["status"],
            },
        },
        {
            "name": "create_task",
            "description": "Create a new task",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["title"],
            },
        },
        {
            "name": "direct_only_tool",
            "description": "Only in direct adapter",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]
    return MockAdapter("direct", tools)


@pytest.fixture
def mcp_bridge():
    """Create a mock MCP bridge."""
    tools = [
        {
            "name": "get_tasks",
            "description": "Get all tasks",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["status"],
            },
        },
        {
            "name": "create_task",
            "description": "Create a task",  # Slightly different description
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string"},  # Extra property
                },
                "required": ["title"],
            },
        },
        {
            "name": "mcp_only_tool",
            "description": "Only in MCP bridge",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]
    return MockAdapter("mcp", tools)


# Tests for enums and dataclasses
def test_migration_status_enum():
    """Test MigrationStatus enum values."""
    assert MigrationStatus.READY.value == "ready"
    assert MigrationStatus.PARTIAL.value == "partial"
    assert MigrationStatus.NOT_READY.value == "not_ready"
    assert MigrationStatus.UNKNOWN.value == "unknown"


def test_comparison_type_enum():
    """Test ComparisonType enum values."""
    assert ComparisonType.IDENTICAL.value == "identical"
    assert ComparisonType.SIMILAR.value == "similar"
    assert ComparisonType.DIRECT_ONLY.value == "direct_only"
    assert ComparisonType.MCP_ONLY.value == "mcp_only"


def test_tool_comparison():
    """Test ToolComparison dataclass."""
    comparison = ToolComparison(
        tool_name="test_tool",
        comparison_type=ComparisonType.IDENTICAL,
        direct_schema={"name": "test_tool"},
        mcp_schema={"name": "test_tool"},
    )

    assert comparison.tool_name == "test_tool"
    assert comparison.is_compatible
    assert comparison.comparison_type == ComparisonType.IDENTICAL

    # Test to_dict
    data = comparison.to_dict()
    assert data["tool_name"] == "test_tool"
    assert data["is_compatible"] is True


def test_tool_comparison_incompatible():
    """Test incompatible tool comparison."""
    comparison = ToolComparison(
        tool_name="test_tool",
        comparison_type=ComparisonType.DIRECT_ONLY,
        direct_schema={"name": "test_tool"},
    )

    assert not comparison.is_compatible


def test_validation_result():
    """Test ValidationResult dataclass."""
    result = ValidationResult(
        tool_name="test_tool",
        arguments={"arg": "value"},
        direct_duration_ms=100.0,
        mcp_duration_ms=150.0,
        results_match=True,
    )

    assert result.tool_name == "test_tool"
    assert result.results_match
    assert result.performance_overhead == 50.0  # 50% overhead

    # Test to_dict
    data = result.to_dict()
    assert data["tool_name"] == "test_tool"
    assert data["performance_overhead"] == 50.0


def test_validation_result_no_timing():
    """Test ValidationResult without timing data."""
    result = ValidationResult(
        tool_name="test_tool",
        arguments={},
    )

    assert result.performance_overhead is None


# Tests for MigrationAnalyzer
@pytest.mark.asyncio
async def test_migration_analyzer_init(direct_adapter, mcp_bridge):
    """Test MigrationAnalyzer initialization."""
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)

    assert analyzer.direct_adapter == direct_adapter
    assert analyzer.mcp_bridge == mcp_bridge
    assert analyzer.report.adapter_name == "direct"
    assert analyzer.report.mcp_server_name == "mcp"


@pytest.mark.asyncio
async def test_compare_tools_identical(direct_adapter, mcp_bridge):
    """Test comparing tools finds identical tools."""
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    await analyzer._compare_tools()

    # Should find get_tasks as identical (same schema)
    get_tasks_comparison = next(
        tc for tc in analyzer.report.tool_comparisons if tc.tool_name == "get_tasks"
    )
    assert get_tasks_comparison.comparison_type == ComparisonType.IDENTICAL
    assert get_tasks_comparison.is_compatible


@pytest.mark.asyncio
async def test_compare_tools_similar(direct_adapter, mcp_bridge):
    """Test comparing tools finds similar tools with differences."""
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    await analyzer._compare_tools()

    # Should find create_task as similar (different description and properties)
    create_task_comparison = next(
        tc for tc in analyzer.report.tool_comparisons if tc.tool_name == "create_task"
    )
    assert create_task_comparison.comparison_type == ComparisonType.SIMILAR
    assert create_task_comparison.is_compatible
    assert len(create_task_comparison.schema_differences) > 0


@pytest.mark.asyncio
async def test_compare_tools_direct_only(direct_adapter, mcp_bridge):
    """Test comparing tools finds direct-only tools."""
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    await analyzer._compare_tools()

    # Should find direct_only_tool
    direct_only = next(
        tc
        for tc in analyzer.report.tool_comparisons
        if tc.tool_name == "direct_only_tool"
    )
    assert direct_only.comparison_type == ComparisonType.DIRECT_ONLY
    assert not direct_only.is_compatible


@pytest.mark.asyncio
async def test_compare_tools_mcp_only(direct_adapter, mcp_bridge):
    """Test comparing tools finds MCP-only tools."""
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    await analyzer._compare_tools()

    # Should find mcp_only_tool
    mcp_only = next(
        tc
        for tc in analyzer.report.tool_comparisons
        if tc.tool_name == "mcp_only_tool"
    )
    assert mcp_only.comparison_type == ComparisonType.MCP_ONLY
    assert not mcp_only.is_compatible


@pytest.mark.asyncio
async def test_validate_tools_matching_results(direct_adapter, mcp_bridge):
    """Test validation with matching results."""
    # Set same results for both adapters
    result = ToolResult(success=True, data={"tasks": []})
    direct_adapter.set_call_result("get_tasks", result)
    mcp_bridge.set_call_result("get_tasks", result)

    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    test_cases = [{"tool": "get_tasks", "args": {"status": "active"}}]

    await analyzer._validate_tools(test_cases)

    assert len(analyzer.report.validation_results) == 1
    validation = analyzer.report.validation_results[0]
    assert validation.results_match
    assert validation.tool_name == "get_tasks"
    assert validation.direct_duration_ms is not None
    assert validation.mcp_duration_ms is not None


@pytest.mark.asyncio
async def test_validate_tools_different_results(direct_adapter, mcp_bridge):
    """Test validation with different results."""
    # Set different results
    direct_adapter.set_call_result(
        "get_tasks", ToolResult(success=True, data={"tasks": ["task1"]})
    )
    mcp_bridge.set_call_result(
        "get_tasks", ToolResult(success=True, data={"tasks": ["task2"]})
    )

    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    test_cases = [{"tool": "get_tasks", "args": {"status": "active"}}]

    await analyzer._validate_tools(test_cases)

    assert len(analyzer.report.validation_results) == 1
    validation = analyzer.report.validation_results[0]
    assert not validation.results_match
    assert len(validation.differences) > 0


@pytest.mark.asyncio
async def test_validate_tools_error_handling(direct_adapter, mcp_bridge):
    """Test validation handles errors gracefully."""
    # Make direct adapter fail
    direct_adapter.set_call_result(
        "get_tasks",
        ToolResult.fail("Connection failed"),
    )
    mcp_bridge.set_call_result(
        "get_tasks",
        ToolResult(success=True, data={"tasks": []}),
    )

    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    test_cases = [{"tool": "get_tasks", "args": {"status": "active"}}]

    await analyzer._validate_tools(test_cases)

    assert len(analyzer.report.validation_results) == 1
    validation = analyzer.report.validation_results[0]
    assert not validation.results_match
    assert len(validation.differences) > 0


@pytest.mark.asyncio
async def test_full_analysis(direct_adapter, mcp_bridge):
    """Test full migration analysis."""
    # Set matching results for validation
    result = ToolResult(success=True, data={"tasks": []})
    direct_adapter.set_call_result("get_tasks", result)
    mcp_bridge.set_call_result("get_tasks", result)

    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    test_cases = [{"tool": "get_tasks", "args": {"status": "active"}}]

    report = await analyzer.analyze(validate_tools=True, test_cases=test_cases)

    # Check report contents
    assert report.adapter_name == "direct"
    assert report.mcp_server_name == "mcp"
    assert len(report.tool_comparisons) > 0
    assert len(report.validation_results) > 0
    assert report.migration_status != MigrationStatus.UNKNOWN
    assert len(report.recommendations) > 0


@pytest.mark.asyncio
async def test_migration_status_determination(direct_adapter, mcp_bridge):
    """Test migration status is determined correctly."""
    result = ToolResult(success=True, data={"tasks": []})
    direct_adapter.set_call_result("get_tasks", result)
    mcp_bridge.set_call_result("get_tasks", result)

    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    test_cases = [{"tool": "get_tasks", "args": {"status": "active"}}]

    await analyzer.analyze(validate_tools=True, test_cases=test_cases)

    # With 1 identical, 1 similar, 1 direct-only, 1 mcp-only:
    # Compatibility = 2/4 = 50% -> should be PARTIAL or NOT_READY
    assert analyzer.report.migration_status in [
        MigrationStatus.PARTIAL,
        MigrationStatus.NOT_READY,
    ]


def test_migration_report_properties(direct_adapter, mcp_bridge):
    """Test MigrationReport computed properties."""
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)

    # Add some tool comparisons
    analyzer.report.tool_comparisons = [
        ToolComparison("tool1", ComparisonType.IDENTICAL),
        ToolComparison("tool2", ComparisonType.SIMILAR),
        ToolComparison("tool3", ComparisonType.DIRECT_ONLY),
    ]

    # Add validation results
    analyzer.report.validation_results = [
        ValidationResult("tool1", {}, results_match=True),
        ValidationResult("tool2", {}, results_match=False),
    ]

    # Test properties
    assert len(analyzer.report.compatible_tools) == 2
    assert len(analyzer.report.incompatible_tools) == 1
    assert analyzer.report.compatibility_percentage == pytest.approx(66.67, rel=0.1)
    assert len(analyzer.report.passed_validations) == 1
    assert len(analyzer.report.failed_validations) == 1
    assert analyzer.report.validation_pass_rate == 50.0


def test_migration_report_to_dict(direct_adapter, mcp_bridge):
    """Test MigrationReport serialization."""
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    analyzer.report.tool_comparisons = [
        ToolComparison("tool1", ComparisonType.IDENTICAL),
    ]
    analyzer.report.migration_status = MigrationStatus.READY

    data = analyzer.report.to_dict()

    assert data["adapter_name"] == "direct"
    assert data["mcp_server_name"] == "mcp"
    assert data["migration_status"] == "ready"
    assert "summary" in data
    assert "tool_comparisons" in data


def test_migration_report_save_to_file(direct_adapter, mcp_bridge):
    """Test saving migration report to file."""
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "report.json"
        analyzer.report.save_to_file(filepath)

        assert filepath.exists()

        # Verify contents
        with open(filepath) as f:
            data = json.load(f)
            assert data["adapter_name"] == "direct"
            assert data["mcp_server_name"] == "mcp"


# Tests for convenience functions
@pytest.mark.asyncio
async def test_compare_tools_function(direct_adapter, mcp_bridge):
    """Test compare_tools convenience function."""
    comparisons = await compare_tools(direct_adapter, mcp_bridge)

    assert len(comparisons) > 0
    assert all(isinstance(c, ToolComparison) for c in comparisons)


@pytest.mark.asyncio
async def test_validate_migration_function(direct_adapter, mcp_bridge):
    """Test validate_migration convenience function."""
    result = ToolResult(success=True, data={})
    direct_adapter.set_call_result("get_tasks", result)
    mcp_bridge.set_call_result("get_tasks", result)

    test_cases = [{"tool": "get_tasks", "args": {"status": "active"}}]
    validations = await validate_migration(direct_adapter, mcp_bridge, test_cases)

    assert len(validations) == 1
    assert isinstance(validations[0], ValidationResult)


def test_generate_mcp_config():
    """Test MCP configuration generation."""
    config = generate_mcp_config(
        adapter_name="test-server",
        command="node",
        args=["dist/index.js"],
        env={"API_KEY": "${API_KEY}"},
        enabled=True,
        tags=["test", "demo"],
    )

    assert "test-server" in config
    server_config = config["test-server"]
    assert server_config["transport"] == "stdio"
    assert server_config["command"] == "node"
    assert server_config["args"] == ["dist/index.js"]
    assert server_config["env"] == {"API_KEY": "${API_KEY}"}
    assert server_config["enabled"] is True
    assert server_config["tags"] == ["test", "demo"]


def test_generate_mcp_config_minimal():
    """Test MCP configuration generation with minimal args."""
    config = generate_mcp_config(
        adapter_name="test-server",
        command="node",
    )

    assert "test-server" in config
    server_config = config["test-server"]
    assert server_config["command"] == "node"
    assert server_config["enabled"] is True
    assert "args" not in server_config
    assert "env" not in server_config


def test_save_mcp_config():
    """Test saving MCP configuration to file."""
    config = generate_mcp_config(
        adapter_name="test-server",
        command="node",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / ".mcp.json"
        save_mcp_config(config, filepath, merge=False)

        assert filepath.exists()

        # Verify contents
        with open(filepath) as f:
            saved_config = json.load(f)
            assert saved_config == config


def test_save_mcp_config_merge():
    """Test saving MCP configuration with merge."""
    config1 = generate_mcp_config(adapter_name="server1", command="node")
    config2 = generate_mcp_config(adapter_name="server2", command="python")

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / ".mcp.json"

        # Save first config
        save_mcp_config(config1, filepath, merge=False)

        # Save second config with merge
        save_mcp_config(config2, filepath, merge=True)

        # Verify both configs are present
        with open(filepath) as f:
            merged_config = json.load(f)
            assert "server1" in merged_config
            assert "server2" in merged_config


def test_get_migration_checklist():
    """Test migration checklist generation."""
    checklist = get_migration_checklist("workos")

    assert "Migration Checklist" in checklist
    assert "workos" in checklist
    assert "Pre-Migration Analysis" in checklist
    assert "Configuration Setup" in checklist
    assert "Testing" in checklist
    assert "Deployment" in checklist


def test_generate_migration_script():
    """Test migration script generation."""
    script = generate_migration_script(
        adapter_name="workos",
        mcp_server_name="workos-mcp",
        mcp_config_path=".mcp.json",
    )

    assert "workos" in script
    assert "workos-mcp" in script
    assert "MigrationAnalyzer" in script
    assert "async def main" in script
    assert ".mcp.json" in script


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
