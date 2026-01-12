"""
MCP Migration Utilities.

Provides tools and utilities to help migrate from direct adapters to MCP bridges,
including tool comparison, configuration generation, validation, and migration checklists.

This module assists in:
- Comparing tools between direct adapters and MCP servers
- Generating MCP server configurations
- Validating that both approaches return equivalent results
- Providing migration checklists and guidance

Usage:
    from Tools.adapters.mcp_migration import (
        MigrationAnalyzer,
        compare_tools,
        generate_mcp_config,
        validate_migration,
    )

    # Compare tools between direct adapter and MCP server
    comparison = await compare_tools(
        direct_adapter=workos_adapter,
        mcp_bridge=workos_mcp_bridge
    )

    # Generate MCP configuration from direct adapter
    config = generate_mcp_config(
        adapter_name="workos",
        command="node",
        args=["dist/index.js"],
        env={"WORKOS_API_KEY": "${WORKOS_API_KEY}"}
    )

    # Validate migration produces equivalent results
    validation = await validate_migration(
        direct_adapter=workos_adapter,
        mcp_bridge=workos_mcp_bridge,
        test_cases=[{"tool": "get_tasks", "args": {"status": "active"}}]
    )
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import BaseAdapter, ToolResult

logger = logging.getLogger(__name__)


class MigrationStatus(str, Enum):
    """
    Migration readiness status.

    - READY: Safe to migrate, tools match and validation passed
    - PARTIAL: Some tools match, migration possible with caveats
    - NOT_READY: Significant differences, migration not recommended
    - UNKNOWN: Insufficient data to determine status
    """

    READY = "ready"
    PARTIAL = "partial"
    NOT_READY = "not_ready"
    UNKNOWN = "unknown"


class ComparisonType(str, Enum):
    """
    Types of tool comparison results.

    - IDENTICAL: Tools have same name and schema
    - SIMILAR: Tools have same name but different schemas
    - DIRECT_ONLY: Tool exists only in direct adapter
    - MCP_ONLY: Tool exists only in MCP bridge
    """

    IDENTICAL = "identical"
    SIMILAR = "similar"
    DIRECT_ONLY = "direct_only"
    MCP_ONLY = "mcp_only"


@dataclass
class ToolComparison:
    """
    Comparison result for a single tool.

    Tracks whether a tool exists in both adapter and bridge,
    and whether schemas match.
    """

    tool_name: str
    """Name of the tool being compared"""

    comparison_type: ComparisonType
    """Type of comparison result"""

    direct_schema: Optional[Dict[str, Any]] = None
    """Tool schema from direct adapter (if available)"""

    mcp_schema: Optional[Dict[str, Any]] = None
    """Tool schema from MCP bridge (if available)"""

    schema_differences: List[str] = field(default_factory=list)
    """List of schema differences found"""

    notes: str = ""
    """Additional notes about this comparison"""

    @property
    def is_compatible(self) -> bool:
        """Whether this tool can be migrated."""
        return self.comparison_type in [ComparisonType.IDENTICAL, ComparisonType.SIMILAR]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "comparison_type": self.comparison_type.value,
            "is_compatible": self.is_compatible,
            "direct_schema": self.direct_schema,
            "mcp_schema": self.mcp_schema,
            "schema_differences": self.schema_differences,
            "notes": self.notes,
        }


@dataclass
class ValidationResult:
    """
    Result of validating a tool call produces equivalent results.

    Compares direct adapter and MCP bridge outputs for the same input.
    """

    tool_name: str
    """Name of tool tested"""

    arguments: Dict[str, Any]
    """Arguments used for testing"""

    direct_result: Optional[ToolResult] = None
    """Result from direct adapter"""

    mcp_result: Optional[ToolResult] = None
    """Result from MCP bridge"""

    results_match: bool = False
    """Whether results are equivalent"""

    differences: List[str] = field(default_factory=list)
    """List of differences found"""

    direct_duration_ms: Optional[float] = None
    """Direct adapter execution time"""

    mcp_duration_ms: Optional[float] = None
    """MCP bridge execution time"""

    error: Optional[str] = None
    """Error message if validation failed"""

    @property
    def performance_overhead(self) -> Optional[float]:
        """Calculate performance overhead percentage of MCP vs direct."""
        if self.direct_duration_ms and self.mcp_duration_ms:
            overhead = (
                (self.mcp_duration_ms - self.direct_duration_ms)
                / self.direct_duration_ms
            ) * 100
            return overhead
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "results_match": self.results_match,
            "differences": self.differences,
            "direct_duration_ms": self.direct_duration_ms,
            "mcp_duration_ms": self.mcp_duration_ms,
            "performance_overhead": self.performance_overhead,
            "error": self.error,
            "direct_success": (
                self.direct_result.success if self.direct_result else None
            ),
            "mcp_success": self.mcp_result.success if self.mcp_result else None,
        }


@dataclass
class MigrationReport:
    """
    Comprehensive migration analysis report.

    Contains tool comparisons, validation results, and migration recommendations.
    """

    adapter_name: str
    """Name of adapter being migrated"""

    mcp_server_name: str
    """Name of MCP server being migrated to"""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    """When this report was generated"""

    tool_comparisons: List[ToolComparison] = field(default_factory=list)
    """Comparison results for all tools"""

    validation_results: List[ValidationResult] = field(default_factory=list)
    """Validation results for test cases"""

    migration_status: MigrationStatus = MigrationStatus.UNKNOWN
    """Overall migration readiness status"""

    recommendations: List[str] = field(default_factory=list)
    """Migration recommendations"""

    warnings: List[str] = field(default_factory=list)
    """Warnings to consider before migrating"""

    @property
    def compatible_tools(self) -> List[ToolComparison]:
        """Tools that can be migrated."""
        return [tc for tc in self.tool_comparisons if tc.is_compatible]

    @property
    def incompatible_tools(self) -> List[ToolComparison]:
        """Tools that cannot be migrated."""
        return [tc for tc in self.tool_comparisons if not tc.is_compatible]

    @property
    def passed_validations(self) -> List[ValidationResult]:
        """Validations that passed."""
        return [vr for vr in self.validation_results if vr.results_match]

    @property
    def failed_validations(self) -> List[ValidationResult]:
        """Validations that failed."""
        return [vr for vr in self.validation_results if not vr.results_match]

    @property
    def compatibility_percentage(self) -> float:
        """Percentage of tools that are compatible."""
        if not self.tool_comparisons:
            return 0.0
        return (len(self.compatible_tools) / len(self.tool_comparisons)) * 100

    @property
    def validation_pass_rate(self) -> float:
        """Percentage of validations that passed."""
        if not self.validation_results:
            return 0.0
        return (len(self.passed_validations) / len(self.validation_results)) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "adapter_name": self.adapter_name,
            "mcp_server_name": self.mcp_server_name,
            "timestamp": self.timestamp.isoformat(),
            "migration_status": self.migration_status.value,
            "summary": {
                "total_tools": len(self.tool_comparisons),
                "compatible_tools": len(self.compatible_tools),
                "incompatible_tools": len(self.incompatible_tools),
                "compatibility_percentage": self.compatibility_percentage,
                "total_validations": len(self.validation_results),
                "passed_validations": len(self.passed_validations),
                "failed_validations": len(self.failed_validations),
                "validation_pass_rate": self.validation_pass_rate,
            },
            "tool_comparisons": [tc.to_dict() for tc in self.tool_comparisons],
            "validation_results": [vr.to_dict() for vr in self.validation_results],
            "recommendations": self.recommendations,
            "warnings": self.warnings,
        }

    def save_to_file(self, filepath: Path) -> None:
        """
        Save report to JSON file.

        Args:
            filepath: Path to save report
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Migration report saved to {filepath}")


class MigrationAnalyzer:
    """
    Analyzes migration from direct adapter to MCP bridge.

    Provides comprehensive comparison, validation, and reporting to ensure
    safe migration with equivalent functionality.
    """

    def __init__(
        self,
        direct_adapter: BaseAdapter,
        mcp_bridge: BaseAdapter,
    ):
        """
        Initialize migration analyzer.

        Args:
            direct_adapter: Existing direct adapter
            mcp_bridge: MCP bridge to migrate to
        """
        self.direct_adapter = direct_adapter
        self.mcp_bridge = mcp_bridge
        self.report = MigrationReport(
            adapter_name=direct_adapter.name,
            mcp_server_name=mcp_bridge.name,
        )

    async def analyze(
        self,
        validate_tools: bool = True,
        test_cases: Optional[List[Dict[str, Any]]] = None,
    ) -> MigrationReport:
        """
        Perform comprehensive migration analysis.

        Args:
            validate_tools: Whether to validate tool functionality
            test_cases: List of test cases for validation (format: {"tool": "name", "args": {}})

        Returns:
            MigrationReport with complete analysis
        """
        logger.info(
            f"Starting migration analysis: {self.direct_adapter.name} -> {self.mcp_bridge.name}"
        )

        # Step 1: Compare tools
        await self._compare_tools()

        # Step 2: Validate with test cases if provided
        if validate_tools and test_cases:
            await self._validate_tools(test_cases)

        # Step 3: Determine migration status
        self._determine_migration_status()

        # Step 4: Generate recommendations
        self._generate_recommendations()

        logger.info(
            f"Migration analysis complete. Status: {self.report.migration_status.value}"
        )
        return self.report

    async def _compare_tools(self) -> None:
        """Compare tools between direct adapter and MCP bridge."""
        logger.debug("Comparing tools between adapter and bridge")

        # Get tools from both sources
        direct_tools = {tool["name"]: tool for tool in self.direct_adapter.list_tools()}
        mcp_tools = {tool["name"]: tool for tool in self.mcp_bridge.list_tools()}

        all_tool_names = set(direct_tools.keys()) | set(mcp_tools.keys())

        for tool_name in sorted(all_tool_names):
            direct_tool = direct_tools.get(tool_name)
            mcp_tool = mcp_tools.get(tool_name)

            if direct_tool and mcp_tool:
                # Both exist - compare schemas
                comparison = self._compare_tool_schemas(
                    tool_name, direct_tool, mcp_tool
                )
            elif direct_tool:
                # Only in direct adapter
                comparison = ToolComparison(
                    tool_name=tool_name,
                    comparison_type=ComparisonType.DIRECT_ONLY,
                    direct_schema=direct_tool,
                    notes="Tool only available in direct adapter",
                )
            else:
                # Only in MCP bridge
                comparison = ToolComparison(
                    tool_name=tool_name,
                    comparison_type=ComparisonType.MCP_ONLY,
                    mcp_schema=mcp_tool,
                    notes="Tool only available in MCP bridge",
                )

            self.report.tool_comparisons.append(comparison)

        logger.info(
            f"Tool comparison complete: {len(self.report.compatible_tools)}/{len(self.report.tool_comparisons)} compatible"
        )

    def _compare_tool_schemas(
        self,
        tool_name: str,
        direct_tool: Dict[str, Any],
        mcp_tool: Dict[str, Any],
    ) -> ToolComparison:
        """
        Compare schemas of tools from direct adapter and MCP bridge.

        Args:
            tool_name: Name of tool
            direct_tool: Tool definition from direct adapter
            mcp_tool: Tool definition from MCP bridge

        Returns:
            ToolComparison with detailed comparison
        """
        differences = []

        # Compare descriptions
        direct_desc = direct_tool.get("description", "")
        mcp_desc = mcp_tool.get("description", "")
        if direct_desc != mcp_desc:
            differences.append(f"Description differs")

        # Compare input schemas
        direct_schema = direct_tool.get("inputSchema", {})
        mcp_schema = mcp_tool.get("inputSchema", {})

        # Compare required fields
        direct_required = set(direct_schema.get("required", []))
        mcp_required = set(mcp_schema.get("required", []))

        if direct_required != mcp_required:
            missing_in_mcp = direct_required - mcp_required
            extra_in_mcp = mcp_required - direct_required
            if missing_in_mcp:
                differences.append(f"Required in direct but not MCP: {missing_in_mcp}")
            if extra_in_mcp:
                differences.append(f"Required in MCP but not direct: {extra_in_mcp}")

        # Compare properties
        direct_props = set(direct_schema.get("properties", {}).keys())
        mcp_props = set(mcp_schema.get("properties", {}).keys())

        if direct_props != mcp_props:
            missing_in_mcp = direct_props - mcp_props
            extra_in_mcp = mcp_props - direct_props
            if missing_in_mcp:
                differences.append(
                    f"Properties in direct but not MCP: {missing_in_mcp}"
                )
            if extra_in_mcp:
                differences.append(f"Properties in MCP but not direct: {extra_in_mcp}")

        # Determine comparison type
        if not differences:
            comparison_type = ComparisonType.IDENTICAL
            notes = "Schemas are identical"
        else:
            comparison_type = ComparisonType.SIMILAR
            notes = f"Found {len(differences)} schema differences"

        return ToolComparison(
            tool_name=tool_name,
            comparison_type=comparison_type,
            direct_schema=direct_tool,
            mcp_schema=mcp_tool,
            schema_differences=differences,
            notes=notes,
        )

    async def _validate_tools(self, test_cases: List[Dict[str, Any]]) -> None:
        """
        Validate that tools produce equivalent results.

        Args:
            test_cases: List of test cases with format {"tool": "name", "args": {}}
        """
        logger.info(f"Validating {len(test_cases)} test cases")

        for test_case in test_cases:
            tool_name = test_case["tool"]
            arguments = test_case.get("args", {})

            validation = await self._validate_single_tool(tool_name, arguments)
            self.report.validation_results.append(validation)

        logger.info(
            f"Validation complete: {len(self.report.passed_validations)}/{len(self.report.validation_results)} passed"
        )

    async def _validate_single_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a single tool call produces equivalent results.

        Args:
            tool_name: Name of tool to validate
            arguments: Arguments for tool call

        Returns:
            ValidationResult with comparison details
        """
        validation = ValidationResult(tool_name=tool_name, arguments=arguments)

        try:
            # Call direct adapter
            start_time = datetime.utcnow()
            direct_result = await self.direct_adapter.call_tool(tool_name, arguments)
            direct_duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            validation.direct_result = direct_result
            validation.direct_duration_ms = direct_duration

            # Call MCP bridge
            start_time = datetime.utcnow()
            mcp_result = await self.mcp_bridge.call_tool(tool_name, arguments)
            mcp_duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            validation.mcp_result = mcp_result
            validation.mcp_duration_ms = mcp_duration

            # Compare results
            validation.results_match, validation.differences = self._compare_results(
                direct_result, mcp_result
            )

        except Exception as e:
            validation.error = str(e)
            validation.results_match = False
            validation.differences.append(f"Validation error: {e}")
            logger.warning(f"Validation failed for {tool_name}: {e}")

        return validation

    def _compare_results(
        self, direct_result: ToolResult, mcp_result: ToolResult
    ) -> Tuple[bool, List[str]]:
        """
        Compare results from direct adapter and MCP bridge.

        Args:
            direct_result: Result from direct adapter
            mcp_result: Result from MCP bridge

        Returns:
            Tuple of (results_match, differences)
        """
        differences = []

        # Compare success status
        if direct_result.success != mcp_result.success:
            differences.append(
                f"Success status differs: direct={direct_result.success}, mcp={mcp_result.success}"
            )

        # Compare error messages
        if direct_result.error != mcp_result.error:
            differences.append(
                f"Error messages differ: direct={direct_result.error}, mcp={mcp_result.error}"
            )

        # Compare data (for successful calls)
        if direct_result.success and mcp_result.success:
            # For complex objects, we do a structural comparison
            # Note: This is a simplified comparison - you may need more sophisticated logic
            direct_data = direct_result.data
            mcp_data = mcp_result.data

            if direct_data != mcp_data:
                # Try JSON serialization for comparison
                try:
                    direct_json = json.dumps(direct_data, sort_keys=True, default=str)
                    mcp_json = json.dumps(mcp_data, sort_keys=True, default=str)
                    if direct_json != mcp_json:
                        differences.append("Data content differs")
                except (TypeError, ValueError):
                    differences.append("Data content differs (unable to serialize)")

        results_match = len(differences) == 0
        return results_match, differences

    def _determine_migration_status(self) -> None:
        """Determine overall migration readiness status."""
        # Calculate compatibility
        compatibility = self.report.compatibility_percentage
        validation_rate = self.report.validation_pass_rate

        if compatibility == 100 and (
            not self.report.validation_results or validation_rate >= 90
        ):
            self.report.migration_status = MigrationStatus.READY
        elif compatibility >= 80 and validation_rate >= 80:
            self.report.migration_status = MigrationStatus.PARTIAL
        elif compatibility < 50 or validation_rate < 50:
            self.report.migration_status = MigrationStatus.NOT_READY
        else:
            self.report.migration_status = MigrationStatus.PARTIAL

    def _generate_recommendations(self) -> None:
        """Generate migration recommendations based on analysis."""
        recommendations = []
        warnings = []

        # Recommendations based on tool compatibility
        if self.report.compatibility_percentage == 100:
            recommendations.append(
                "✓ All tools are compatible - migration should be straightforward"
            )
        elif self.report.compatibility_percentage >= 80:
            recommendations.append(
                "⚠ Most tools are compatible, but review incompatible tools carefully"
            )
            warnings.append(
                f"{len(self.report.incompatible_tools)} tools are incompatible"
            )
        else:
            recommendations.append(
                "✗ Low tool compatibility - consider keeping direct adapter"
            )
            warnings.append(
                "Migration may result in loss of functionality for some tools"
            )

        # Recommendations based on validation
        if self.report.validation_results:
            if self.report.validation_pass_rate == 100:
                recommendations.append(
                    "✓ All validations passed - results are equivalent"
                )
            elif self.report.validation_pass_rate >= 80:
                recommendations.append(
                    "⚠ Most validations passed, but review failures"
                )
                warnings.append(
                    f"{len(self.report.failed_validations)} validations failed"
                )
            else:
                recommendations.append(
                    "✗ Validation failures detected - investigate before migrating"
                )
                warnings.append(
                    "Results may differ significantly between direct and MCP approaches"
                )

        # Performance recommendations
        if self.report.validation_results:
            avg_overhead = sum(
                vr.performance_overhead or 0
                for vr in self.report.validation_results
                if vr.performance_overhead is not None
            ) / len(self.report.validation_results)

            if avg_overhead < 20:
                recommendations.append(
                    f"✓ Performance overhead is acceptable (~{avg_overhead:.1f}%)"
                )
            elif avg_overhead < 50:
                recommendations.append(
                    f"⚠ Moderate performance overhead (~{avg_overhead:.1f}%)"
                )
            else:
                recommendations.append(
                    f"✗ Significant performance overhead (~{avg_overhead:.1f}%)"
                )
                warnings.append(
                    "MCP bridge may be noticeably slower than direct adapter"
                )

        # Tools only in one adapter
        direct_only_tools = [
            tc for tc in self.report.tool_comparisons
            if tc.comparison_type == ComparisonType.DIRECT_ONLY
        ]
        mcp_only_tools = [
            tc for tc in self.report.tool_comparisons
            if tc.comparison_type == ComparisonType.MCP_ONLY
        ]

        if direct_only_tools:
            warnings.append(
                f"{len(direct_only_tools)} tools only available in direct adapter: "
                f"{', '.join(tc.tool_name for tc in direct_only_tools[:3])}"
                + ("..." if len(direct_only_tools) > 3 else "")
            )

        if mcp_only_tools:
            recommendations.append(
                f"ℹ {len(mcp_only_tools)} additional tools available in MCP bridge: "
                f"{', '.join(tc.tool_name for tc in mcp_only_tools[:3])}"
                + ("..." if len(mcp_only_tools) > 3 else "")
            )

        self.report.recommendations = recommendations
        self.report.warnings = warnings


# Convenience functions


async def compare_tools(
    direct_adapter: BaseAdapter,
    mcp_bridge: BaseAdapter,
) -> List[ToolComparison]:
    """
    Compare tools between direct adapter and MCP bridge.

    Args:
        direct_adapter: Direct adapter instance
        mcp_bridge: MCP bridge instance

    Returns:
        List of ToolComparison objects
    """
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    await analyzer._compare_tools()
    return analyzer.report.tool_comparisons


async def validate_migration(
    direct_adapter: BaseAdapter,
    mcp_bridge: BaseAdapter,
    test_cases: List[Dict[str, Any]],
) -> List[ValidationResult]:
    """
    Validate that migration produces equivalent results.

    Args:
        direct_adapter: Direct adapter instance
        mcp_bridge: MCP bridge instance
        test_cases: List of test cases (format: {"tool": "name", "args": {}})

    Returns:
        List of ValidationResult objects
    """
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
    await analyzer._validate_tools(test_cases)
    return analyzer.report.validation_results


def generate_mcp_config(
    adapter_name: str,
    command: str,
    args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
    enabled: bool = True,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate MCP server configuration for .mcp.json file.

    Args:
        adapter_name: Name of adapter/server
        command: Command to run MCP server
        args: Command arguments
        env: Environment variables
        enabled: Whether server is enabled
        tags: Tags for server categorization

    Returns:
        Configuration dictionary ready for .mcp.json

    Example:
        config = generate_mcp_config(
            adapter_name="workos-mcp",
            command="node",
            args=["dist/index.js"],
            env={"WORKOS_API_KEY": "${WORKOS_API_KEY}"}
        )
    """
    config = {
        adapter_name: {
            "transport": "stdio",
            "command": command,
            "enabled": enabled,
        }
    }

    if args:
        config[adapter_name]["args"] = args

    if env:
        config[adapter_name]["env"] = env

    if tags:
        config[adapter_name]["tags"] = tags

    return config


def save_mcp_config(
    config: Dict[str, Any],
    filepath: Path,
    merge: bool = True,
) -> None:
    """
    Save MCP configuration to file.

    Args:
        config: Configuration dictionary
        filepath: Path to .mcp.json file
        merge: Whether to merge with existing config (default: True)
    """
    existing_config = {}

    if merge and filepath.exists():
        try:
            with open(filepath) as f:
                existing_config = json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning(f"Could not read existing config from {filepath}")

    # Merge configs
    merged_config = {**existing_config, **config}

    # Save to file
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(merged_config, f, indent=2)

    logger.info(f"MCP configuration saved to {filepath}")


def get_migration_checklist(adapter_name: str) -> str:
    """
    Get migration checklist for transitioning to MCP bridge.

    Args:
        adapter_name: Name of adapter being migrated

    Returns:
        Markdown-formatted checklist
    """
    checklist = f"""
# Migration Checklist: {adapter_name} Direct Adapter → MCP Bridge

## Pre-Migration Analysis
- [ ] Run MigrationAnalyzer to compare tools
- [ ] Review tool comparison results
- [ ] Identify tools that won't be available after migration
- [ ] Create test cases for critical functionality
- [ ] Run validation tests to ensure equivalent results
- [ ] Review performance overhead measurements
- [ ] Document any known differences or limitations

## Configuration Setup
- [ ] Install/verify MCP server is working
- [ ] Create .mcp.json configuration file
- [ ] Configure environment variables
- [ ] Test MCP server connection manually
- [ ] Verify all required tools are exposed by MCP server
- [ ] Configure any server-specific settings (timeouts, etc.)

## Code Migration
- [ ] Update AdapterManager initialization to enable MCP
- [ ] Replace direct adapter instantiation with MCP bridge discovery
- [ ] Update tool names if MCP server uses different naming
- [ ] Update any adapter-specific configuration
- [ ] Add error handling for MCP-specific errors
- [ ] Update logging to distinguish MCP bridge calls

## Testing
- [ ] Run unit tests for affected code paths
- [ ] Test all critical tool calls manually
- [ ] Verify error handling works as expected
- [ ] Test with invalid inputs to ensure proper validation
- [ ] Performance test critical operations
- [ ] Test reconnection and recovery scenarios

## Deployment
- [ ] Deploy MCP server to production environment
- [ ] Update production configuration files
- [ ] Configure production environment variables
- [ ] Set up monitoring for MCP server health
- [ ] Set up alerts for MCP connection failures
- [ ] Document rollback procedure

## Post-Migration
- [ ] Monitor error rates and performance
- [ ] Review logs for MCP-specific issues
- [ ] Gather user feedback on any behavioral changes
- [ ] Document any migration issues encountered
- [ ] Update team documentation with new architecture
- [ ] Consider removing direct adapter code (after validation period)

## Rollback Plan (if needed)
- [ ] Keep direct adapter code available
- [ ] Document configuration changes needed to revert
- [ ] Test rollback procedure in staging
- [ ] Communicate rollback plan to team
- [ ] Monitor for issues requiring rollback

## Notes
- Migration status: UNKNOWN (run MigrationAnalyzer first)
- Critical tools to validate: [List your critical tools]
- Expected performance impact: [Document based on validation]
- Timeline: [Your migration timeline]
- Point of contact: [Technical owner]
"""
    return checklist.strip()


def generate_migration_script(
    adapter_name: str,
    mcp_server_name: str,
    mcp_config_path: str = ".mcp.json",
) -> str:
    """
    Generate Python migration script template.

    Args:
        adapter_name: Name of direct adapter
        mcp_server_name: Name of MCP server
        mcp_config_path: Path to MCP configuration file

    Returns:
        Python script template as string
    """
    script = f'''"""
Migration script: {adapter_name} → {mcp_server_name} MCP Bridge

This script helps migrate from direct adapter to MCP bridge by:
1. Comparing tools and validating functionality
2. Generating migration report
3. Providing recommendations
"""

import asyncio
import json
from pathlib import Path
from Tools.adapters import get_default_manager
from Tools.adapters.mcp_migration import MigrationAnalyzer


async def main():
    """Run migration analysis."""
    print("=== Migration Analysis: {adapter_name} → {mcp_server_name} ===\\n")

    # Initialize adapters
    print("Initializing adapters...")
    manager = await get_default_manager(enable_mcp=True)

    # Get adapters
    direct_adapter = manager._adapters.get("{adapter_name}")
    mcp_bridge = manager._adapters.get("{mcp_server_name}")

    if not direct_adapter:
        print(f"ERROR: Direct adapter '{adapter_name}' not found")
        return

    if not mcp_bridge:
        print(f"ERROR: MCP bridge '{mcp_server_name}' not found")
        print(f"Make sure {mcp_config_path} is configured correctly")
        return

    # Create analyzer
    analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)

    # Define test cases for critical functionality
    test_cases = [
        # Add your test cases here
        # {{"tool": "tool_name", "args": {{"param": "value"}}}},
    ]

    # Run analysis
    print("\\nAnalyzing migration...")
    report = await analyzer.analyze(
        validate_tools=True,
        test_cases=test_cases
    )

    # Print summary
    print("\\n=== Migration Report ===")
    print(f"Status: {{report.migration_status.value.upper()}}")
    print(f"\\nTool Compatibility: {{report.compatibility_percentage:.1f}}%")
    print(f"  - Compatible: {{len(report.compatible_tools)}}")
    print(f"  - Incompatible: {{len(report.incompatible_tools)}}")

    if report.validation_results:
        print(f"\\nValidation Results: {{report.validation_pass_rate:.1f}}%")
        print(f"  - Passed: {{len(report.passed_validations)}}")
        print(f"  - Failed: {{len(report.failed_validations)}}")

    print("\\n=== Recommendations ===")
    for rec in report.recommendations:
        print(f"  {{rec}}")

    if report.warnings:
        print("\\n=== Warnings ===")
        for warning in report.warnings:
            print(f"  ⚠ {{warning}}")

    # Save detailed report
    report_path = Path("migration_report_{adapter_name}.json")
    report.save_to_file(report_path)
    print(f"\\n✓ Detailed report saved to {{report_path}}")

    # Cleanup
    await manager.close_all()


if __name__ == "__main__":
    asyncio.run(main())
'''
    return script


# Migration documentation
MIGRATION_GUIDE = """
# MCP Migration Guide

## Overview
This guide helps you migrate from direct adapters to MCP bridges in Thanos.

## Why Migrate?
- **Ecosystem Integration**: Access to growing MCP ecosystem
- **Third-Party Tools**: Use tools from any MCP-compatible server
- **Standardization**: MCP is becoming the standard for tool integration
- **Future-Proof**: New features will be built on MCP foundation

## When to Migrate
✓ **Good candidates for migration:**
- Adapters with MCP server equivalents available
- Adapters where performance overhead is acceptable
- Adapters that would benefit from ecosystem tools

✗ **Keep as direct adapters:**
- Performance-critical integrations
- Adapters without MCP server equivalents
- Adapters with complex custom logic

## Migration Process

### 1. Analysis Phase
Use `MigrationAnalyzer` to understand compatibility:

```python
from Tools.adapters.mcp_migration import MigrationAnalyzer

analyzer = MigrationAnalyzer(direct_adapter, mcp_bridge)
report = await analyzer.analyze(
    validate_tools=True,
    test_cases=[...]
)
```

### 2. Configuration Phase
Generate and save MCP configuration:

```python
from Tools.adapters.mcp_migration import generate_mcp_config, save_mcp_config

config = generate_mcp_config(
    adapter_name="my-server",
    command="node",
    args=["dist/index.js"],
    env={"API_KEY": "${MY_API_KEY}"}
)

save_mcp_config(config, Path(".mcp.json"))
```

### 3. Testing Phase
Validate that both approaches work equivalently:

```python
from Tools.adapters.mcp_migration import validate_migration

test_cases = [
    {"tool": "critical_tool_1", "args": {"param": "value"}},
    {"tool": "critical_tool_2", "args": {}},
]

results = await validate_migration(direct_adapter, mcp_bridge, test_cases)
```

### 4. Migration Phase
Update your code to use MCP bridges:

```python
# Before: Direct adapter
manager = await get_default_manager()  # Only direct adapters

# After: MCP bridges enabled
manager = await get_default_manager(enable_mcp=True)  # Both direct and MCP
```

### 5. Monitoring Phase
- Monitor error rates and performance
- Watch for MCP-specific errors
- Validate results match expectations
- Be ready to rollback if needed

## Best Practices

1. **Start with analysis**: Always run MigrationAnalyzer before migrating
2. **Test thoroughly**: Create comprehensive test cases for critical tools
3. **Migrate incrementally**: Consider hybrid approach initially
4. **Monitor performance**: MCP adds overhead - measure impact
5. **Document changes**: Keep team informed of architectural changes
6. **Plan rollback**: Always have a way to revert if needed

## Troubleshooting

### Tools don't match
- Check MCP server version
- Verify server configuration
- Review server documentation

### Validation failures
- Compare tool schemas carefully
- Check for data format differences
- Verify environment variables

### Performance issues
- Enable connection pooling
- Use result caching
- Consider keeping direct adapter for critical paths

## Support
For issues or questions about migration, consult the MCP integration documentation
or reach out to the Thanos development team.
"""
