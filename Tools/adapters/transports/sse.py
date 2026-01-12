"""
SSE (Server-Sent Events) transport for MCP servers.

Implements HTTP-based communication with MCP servers using Server-Sent Events.
This transport is used for remote MCP servers that expose SSE endpoints.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.client.sse import sse_client

from ..mcp_config import SSEConfig
from .base import Transport, TransportError

logger = logging.getLogger(__name__)


class SSETransport(Transport):
    """
    SSE (Server-Sent Events) transport for remote MCP servers.

    This transport connects to MCP servers that expose HTTP endpoints using
    the Server-Sent Events protocol. It's used for remote servers that cannot
    be spawned as subprocesses.

    The transport:
    - Connects to SSE endpoint via HTTP/HTTPS
    - Sends custom headers for authentication/authorization
    - Handles reconnection with configurable intervals
    - Supports connection timeouts

    Example:
        >>> from mcp_config import SSEConfig
        >>> config = SSEConfig(
        ...     url="https://api.example.com/mcp",
        ...     headers={"Authorization": "Bearer token"},
        ...     timeout=30,
        ...     reconnect_interval=5
        ... )
        >>> transport = SSETransport(config)
        >>> async with transport.connect() as (read, write):
        ...     # Use read/write streams with ClientSession
        ...     pass

    Note:
        This transport is scaffolded for future use. Full implementation
        and testing will be completed in a later phase when remote MCP
        servers become available for testing.
    """

    def __init__(self, config: SSEConfig):
        """
        Initialize SSE transport.

        Args:
            config: SSE configuration with URL, headers, and timeouts
        """
        super().__init__(config)
        self.config: SSEConfig = config
        self._session = None

    @property
    def transport_type(self) -> str:
        """Return transport type identifier."""
        return "sse"

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[tuple[Any, Any]]:
        """
        Establish SSE connection to remote MCP server.

        Connects to the configured SSE endpoint and yields read/write streams
        compatible with mcp.ClientSession.

        Yields:
            Tuple of (read_stream, write_stream) for MCP communication

        Raises:
            TransportError: If connection fails or server is unreachable

        Note:
            This implementation uses the MCP SDK's sse_client, which handles
            the SSE protocol details and reconnection logic.
        """
        logger.debug(f"Connecting to SSE endpoint: {self.config.url}")

        try:
            # Establish SSE connection using MCP SDK's sse_client
            # The sse_client handles the SSE protocol and provides read/write streams
            async with sse_client(
                url=self.config.url,
                headers=self.config.headers,
                timeout=self.config.timeout,
            ) as (read, write):
                logger.info(f"SSE connection established to: {self.config.url}")
                yield read, write

        except Exception as e:
            logger.error(
                f"SSE transport error for '{self.config.url}': {e}",
                exc_info=True,
            )
            raise TransportError(f"SSE connection failed: {e}") from e

    async def close(self):
        """
        Close the SSE connection.

        Note:
            The sse_client context manager handles connection cleanup,
            so this method primarily serves as a clean shutdown hook.
        """
        logger.debug(f"Closing SSE transport for: {self.config.url}")
        self._session = None

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on SSE transport.

        Returns:
            Dictionary with health status and configuration info

        Note:
            This is a basic health check. A full implementation could
            attempt a connection to verify server availability.
        """
        return {
            "status": "configured",
            "transport_type": self.transport_type,
            "url": self.config.url,
            "timeout": self.config.timeout,
            "reconnect_interval": self.config.reconnect_interval,
            "has_headers": len(self.config.headers) > 0,
        }
