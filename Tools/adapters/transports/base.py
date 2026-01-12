"""
Base transport interface for MCP communications.

Defines the abstract Transport class that all transport implementations must follow.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession


class TransportError(Exception):
    """Base exception for transport-related errors."""

    pass


class Transport(ABC):
    """
    Abstract base class for MCP transports.

    A transport handles the low-level communication with an MCP server,
    providing read and write streams that the MCP ClientSession can use.

    Implementations must provide:
    - Connection establishment and teardown
    - Read/write stream creation
    - Error handling specific to the transport type
    """

    def __init__(self, config: Any):
        """
        Initialize the transport with configuration.

        Args:
            config: Transport-specific configuration object
        """
        self.config = config

    @property
    @abstractmethod
    def transport_type(self) -> str:
        """
        Return the transport type identifier.

        Returns:
            Transport type (e.g., "stdio", "sse", "http")
        """
        pass

    @abstractmethod
    @asynccontextmanager
    async def connect(self) -> AsyncIterator[tuple[Any, Any]]:
        """
        Establish connection and yield read/write streams.

        This is an async context manager that:
        1. Establishes the connection to the MCP server
        2. Yields (read_stream, write_stream) tuple
        3. Cleans up the connection on exit

        The streams must be compatible with mcp.ClientSession:
        - read_stream: Used by ClientSession to receive messages
        - write_stream: Used by ClientSession to send messages

        Yields:
            Tuple of (read_stream, write_stream)

        Raises:
            TransportError: If connection fails or is interrupted

        Example:
            >>> async with transport.connect() as (read, write):
            ...     async with ClientSession(read, write) as session:
            ...         # Use the session
            ...         pass
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Close the transport and clean up resources.

        This method should:
        - Terminate any active connections
        - Clean up subprocesses or network resources
        - Release any held resources

        Should be idempotent (safe to call multiple times).
        """
        pass

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the transport.

        Returns:
            Dictionary with health status information

        Default implementation returns basic info.
        Subclasses can override for transport-specific checks.
        """
        return {
            "status": "unknown",
            "transport_type": self.transport_type,
            "message": "Health check not implemented for this transport",
        }
