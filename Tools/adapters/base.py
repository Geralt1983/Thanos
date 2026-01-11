"""
Base adapter interface for Thanos MCP bridge.

Provides abstract base class and standard result type for all adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ToolResult:
    """Standard result from any adapter tool call."""

    success: bool
    data: Any
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Add timestamp to metadata if not present."""
        if "timestamp" not in self.metadata:
            self.metadata["timestamp"] = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def ok(cls, data: Any, **metadata) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata) -> "ToolResult":
        """Create a failed result."""
        return cls(success=False, data=None, error=error, metadata=metadata)


class BaseAdapter(ABC):
    """Abstract base class for all Thanos adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter identifier used for routing."""
        pass

    @abstractmethod
    def list_tools(self) -> list[dict[str, Any]]:
        """
        Return list of available tools with their schemas.

        Each tool should have:
        - name: str - Tool identifier
        - description: str - Human-readable description
        - parameters: Dict - JSON Schema for parameters
        """
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """
        Execute a tool and return the result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool parameters

        Returns:
            ToolResult with success status and data/error
        """
        pass

    def get_tool(self, tool_name: str) -> Optional[dict[str, Any]]:
        """Get a specific tool's schema by name."""
        tools = {t["name"]: t for t in self.list_tools()}
        return tools.get(tool_name)

    def validate_arguments(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate arguments against tool schema.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            return False, f"Unknown tool: {tool_name}"

        params = tool.get("parameters", {})

        # Check required parameters
        for param_name, param_spec in params.items():
            if param_spec.get("required", False) and param_name not in arguments:
                return False, f"Missing required parameter: {param_name}"

        # Basic type validation could be added here
        # For now, we trust the caller to provide valid types

        return True, None

    async def call_tool_validated(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """
        Validate arguments then execute tool.

        Convenience method that combines validation and execution.
        """
        is_valid, error = self.validate_arguments(tool_name, arguments)
        if not is_valid:
            return ToolResult.fail(error)
        return await self.call_tool(tool_name, arguments)

    async def close(self):
        """
        Close any open connections.

        Override in subclasses that maintain persistent connections.
        """
        # Default implementation does nothing - subclasses may override
        pass  # noqa: B027

    async def health_check(self) -> ToolResult:
        """
        Check adapter health/connectivity.

        Override in subclasses to provide meaningful health checks.
        """
        return ToolResult.ok({"status": "ok", "adapter": self.name})
