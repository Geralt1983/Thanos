"""
MCP Capability Management.

Provides utilities for working with MCP client and server capabilities,
including capability detection, matching, and graceful degradation strategies.
"""

import logging
from typing import Any, Optional

from mcp.types import (
    ClientCapabilities,
    ServerCapabilities,
    ToolsCapability,
    PromptsCapability,
    ResourcesCapability,
    LoggingCapability,
)

logger = logging.getLogger(__name__)


class CapabilityManager:
    """
    Manages MCP capabilities for client-server negotiation.

    Tracks both client capabilities (what we support) and server capabilities
    (what the MCP server supports), enabling feature detection and graceful
    degradation when capabilities don't match.

    Example:
        >>> manager = CapabilityManager()
        >>> manager.set_server_capabilities(server_caps)
        >>> if manager.supports_tool_list_changed():
        ...     # Subscribe to tool list changes
        ...     pass
    """

    def __init__(self):
        """Initialize capability manager with default client capabilities."""
        self._client_capabilities: ClientCapabilities = self._build_default_client_capabilities()
        self._server_capabilities: Optional[ServerCapabilities] = None

    def _build_default_client_capabilities(self) -> ClientCapabilities:
        """
        Build default client capabilities for Thanos.

        We support:
        - roots: Can list roots (for file system access)
        - experimental: Open to experimental features

        We don't support (at this time):
        - sampling: We're not providing LLM sampling to servers
        - elicitation: We're not prompting users on behalf of servers
        - tasks: Not yet implementing task-augmented requests
        """
        return ClientCapabilities(
            experimental={
                "thanos": {
                    "version": "1.0",
                    "features": ["multi-server", "connection-pooling"],
                }
            },
            sampling=None,  # We don't provide sampling
            elicitation=None,  # We don't provide elicitation
            roots=None,  # Can be enabled if needed
            tasks=None,  # Not yet supporting task-augmented requests
        )

    def get_client_capabilities(self) -> ClientCapabilities:
        """
        Get the client capabilities to send during initialization.

        Returns:
            ClientCapabilities object for the initialize request
        """
        return self._client_capabilities

    def set_server_capabilities(self, capabilities: ServerCapabilities) -> None:
        """
        Store server capabilities received during initialization.

        Args:
            capabilities: ServerCapabilities from InitializeResult
        """
        self._server_capabilities = capabilities
        logger.debug(f"Server capabilities set: {self._format_capabilities(capabilities)}")

    def get_server_capabilities(self) -> Optional[ServerCapabilities]:
        """
        Get the stored server capabilities.

        Returns:
            ServerCapabilities if set, None otherwise
        """
        return self._server_capabilities

    def _format_capabilities(self, capabilities: ServerCapabilities) -> dict[str, Any]:
        """Format capabilities for logging."""
        return {
            "tools": capabilities.tools is not None,
            "prompts": capabilities.prompts is not None,
            "resources": capabilities.resources is not None,
            "logging": capabilities.logging is not None,
            "completions": capabilities.completions is not None,
            "tasks": capabilities.tasks is not None,
            "experimental": list(capabilities.experimental.keys()) if capabilities.experimental else [],
        }

    # Tool capabilities

    def supports_tools(self) -> bool:
        """
        Check if server supports tools.

        Returns:
            True if server has tools capability
        """
        if self._server_capabilities is None:
            logger.warning("Server capabilities not set, assuming no tools support")
            return False
        return self._server_capabilities.tools is not None

    def supports_tool_list_changed(self) -> bool:
        """
        Check if server supports tool list change notifications.

        Returns:
            True if server will notify when tool list changes
        """
        if not self.supports_tools():
            return False

        tools_cap = self._server_capabilities.tools
        return tools_cap.listChanged is True if tools_cap else False

    # Prompt capabilities

    def supports_prompts(self) -> bool:
        """
        Check if server supports prompts.

        Returns:
            True if server has prompts capability
        """
        if self._server_capabilities is None:
            return False
        return self._server_capabilities.prompts is not None

    def supports_prompt_list_changed(self) -> bool:
        """
        Check if server supports prompt list change notifications.

        Returns:
            True if server will notify when prompt list changes
        """
        if not self.supports_prompts():
            return False

        prompts_cap = self._server_capabilities.prompts
        return prompts_cap.listChanged is True if prompts_cap else False

    # Resource capabilities

    def supports_resources(self) -> bool:
        """
        Check if server supports resources.

        Returns:
            True if server has resources capability
        """
        if self._server_capabilities is None:
            return False
        return self._server_capabilities.resources is not None

    def supports_resource_subscriptions(self) -> bool:
        """
        Check if server supports resource subscriptions.

        Returns:
            True if server allows subscribing to resource updates
        """
        if not self.supports_resources():
            return False

        resources_cap = self._server_capabilities.resources
        return resources_cap.subscribe is True if resources_cap else False

    def supports_resource_list_changed(self) -> bool:
        """
        Check if server supports resource list change notifications.

        Returns:
            True if server will notify when resource list changes
        """
        if not self.supports_resources():
            return False

        resources_cap = self._server_capabilities.resources
        return resources_cap.listChanged is True if resources_cap else False

    # Logging capability

    def supports_logging(self) -> bool:
        """
        Check if server supports sending log messages to client.

        Returns:
            True if server has logging capability
        """
        if self._server_capabilities is None:
            return False
        return self._server_capabilities.logging is not None

    # Task capabilities

    def supports_tasks(self) -> bool:
        """
        Check if server supports task-augmented requests.

        Returns:
            True if server has tasks capability
        """
        if self._server_capabilities is None:
            return False
        return self._server_capabilities.tasks is not None

    # Experimental capabilities

    def get_experimental_capabilities(self) -> dict[str, dict[str, Any]]:
        """
        Get experimental capabilities from server.

        Returns:
            Dictionary of experimental capabilities, empty dict if none
        """
        if self._server_capabilities is None:
            return {}
        return self._server_capabilities.experimental or {}

    def supports_experimental_feature(self, namespace: str, feature: str) -> bool:
        """
        Check if server supports a specific experimental feature.

        Args:
            namespace: Feature namespace (e.g., "thanos", "anthropic")
            feature: Feature name within namespace

        Returns:
            True if feature is supported
        """
        experimental = self.get_experimental_capabilities()
        if namespace not in experimental:
            return False

        namespace_features = experimental[namespace]
        if not isinstance(namespace_features, dict):
            return False

        # Check if feature exists in namespace
        return feature in namespace_features

    # Graceful degradation helpers

    def require_tools_support(self) -> None:
        """
        Raise an exception if server doesn't support tools.

        Raises:
            RuntimeError: If tools are not supported
        """
        if not self.supports_tools():
            raise RuntimeError(
                "Server does not support tools capability. "
                "This server cannot be used for tool execution."
            )

    def warn_if_no_tool_list_changed(self) -> None:
        """Log debug message if server doesn't support tool list change notifications."""
        if self.supports_tools() and not self.supports_tool_list_changed():
            logger.debug(
                "Server does not support tool list change notifications. "
                "Tool list updates will require manual refresh."
            )

    def get_capability_summary(self) -> dict[str, Any]:
        """
        Get a human-readable summary of capabilities.

        Returns:
            Dictionary with capability status
        """
        if self._server_capabilities is None:
            return {"status": "not_initialized", "capabilities": {}}

        return {
            "status": "initialized",
            "capabilities": {
                "tools": {
                    "supported": self.supports_tools(),
                    "list_changed": self.supports_tool_list_changed(),
                },
                "prompts": {
                    "supported": self.supports_prompts(),
                    "list_changed": self.supports_prompt_list_changed(),
                },
                "resources": {
                    "supported": self.supports_resources(),
                    "subscribe": self.supports_resource_subscriptions(),
                    "list_changed": self.supports_resource_list_changed(),
                },
                "logging": {"supported": self.supports_logging()},
                "tasks": {"supported": self.supports_tasks()},
                "experimental": self.get_experimental_capabilities(),
            },
        }


def create_capability_manager() -> CapabilityManager:
    """
    Factory function to create a CapabilityManager with defaults.

    Returns:
        CapabilityManager instance
    """
    return CapabilityManager()
