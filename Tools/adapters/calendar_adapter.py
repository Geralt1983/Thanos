"""
Unified Calendar adapter for Thanos.

Provides a consistent interface for calendar operations across multiple providers
(Google Calendar, Apple Calendar, etc.). Currently wraps GoogleCalendarAdapter,
with future support for additional providers planned.
"""

import logging
from typing import Any, Literal, Optional

from .base import BaseAdapter, ToolResult
from .google_calendar import GoogleCalendarAdapter

logger = logging.getLogger(__name__)


CalendarProvider = Literal["google", "apple"]


class CalendarAdapter(BaseAdapter):
    """
    Unified calendar adapter supporting multiple calendar providers.

    Currently supports:
    - Google Calendar (via GoogleCalendarAdapter)

    Future support planned:
    - Apple Calendar

    This adapter provides a consistent interface regardless of the underlying
    provider, making it easy to switch providers or support multiple calendars
    from a single interface.

    Example:
        # Use default provider (Google Calendar)
        adapter = CalendarAdapter()

        # List available tools
        tools = adapter.list_tools()

        # Get today's events
        result = await adapter.call_tool("get_today_events", {
            "calendar_id": "primary"
        })
    """

    def __init__(
        self,
        provider: CalendarProvider = "google",
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        """
        Initialize the unified calendar adapter.

        Args:
            provider: Calendar provider to use. Currently only "google" is supported.
            client_id: OAuth client ID (Google Calendar only). Falls back to env var.
            client_secret: OAuth client secret (Google Calendar only). Falls back to env var.
            redirect_uri: OAuth redirect URI (Google Calendar only). Falls back to env var.

        Raises:
            ValueError: If an unsupported provider is specified.
        """
        self._provider = provider
        self._underlying_adapter: BaseAdapter

        if provider == "google":
            self._underlying_adapter = GoogleCalendarAdapter(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
        elif provider == "apple":
            # Future: Implement AppleCalendarAdapter
            raise ValueError(
                "Apple Calendar provider is not yet implemented. "
                "Currently only 'google' is supported."
            )
        else:
            raise ValueError(
                f"Unsupported calendar provider: {provider}. "
                f"Supported providers: 'google'"
            )

        logger.info(f"Initialized CalendarAdapter with provider: {provider}")

    @property
    def name(self) -> str:
        """Adapter identifier used for routing."""
        return "calendar"

    @property
    def provider(self) -> CalendarProvider:
        """Get the current calendar provider."""
        return self._provider

    @property
    def underlying_adapter(self) -> BaseAdapter:
        """Get the underlying provider-specific adapter."""
        return self._underlying_adapter

    def list_tools(self) -> list[dict[str, Any]]:
        """
        Return list of available calendar tools.

        Proxies to the underlying provider adapter, ensuring consistent
        interface regardless of provider.

        Returns:
            List of tool schemas with names, descriptions, and parameters.
        """
        return self._underlying_adapter.list_tools()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """
        Execute a calendar tool.

        Proxies to the underlying provider adapter, providing unified error
        handling and logging.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool parameters

        Returns:
            ToolResult with success status and data/error
        """
        logger.debug(
            f"CalendarAdapter proxying {tool_name} to {self._provider} provider"
        )
        try:
            result = await self._underlying_adapter.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(
                f"Error in CalendarAdapter.call_tool({tool_name}): {e}", exc_info=True
            )
            return ToolResult.fail(
                f"Calendar adapter error: {e}",
                provider=self._provider,
                tool_name=tool_name,
            )

    async def close(self) -> None:
        """
        Close any open connections in the underlying adapter.

        Proxies to the underlying provider adapter's close method.
        """
        logger.debug(f"Closing CalendarAdapter ({self._provider} provider)")
        await self._underlying_adapter.close()

    async def health_check(self) -> ToolResult:
        """
        Check adapter health/connectivity.

        Proxies to the underlying provider adapter's health check,
        adding provider information to the result.

        Returns:
            ToolResult with health status and provider information
        """
        result = await self._underlying_adapter.health_check()

        # Enhance result with provider information
        if result.success and isinstance(result.data, dict):
            result.data["provider"] = self._provider
            result.data["adapter"] = self.name

        return result

    def get_tool(self, tool_name: str) -> Optional[dict[str, Any]]:
        """
        Get a specific tool's schema by name.

        Proxies to the underlying provider adapter.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool schema dict or None if not found
        """
        return self._underlying_adapter.get_tool(tool_name)

    def validate_arguments(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate arguments against tool schema.

        Proxies to the underlying provider adapter.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self._underlying_adapter.validate_arguments(tool_name, arguments)
