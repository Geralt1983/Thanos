"""
Stdio transport for MCP servers.

Implements subprocess-based communication with MCP servers using stdin/stdout.
This is the primary transport for locally-run MCP servers.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client

from ..mcp_config import StdioConfig
from .base import Transport, TransportError

logger = logging.getLogger(__name__)


class StdioTransport(Transport):
    """
    Stdio transport for subprocess-based MCP servers.

    This transport spawns an MCP server as a subprocess and communicates
    via JSON-RPC over stdin/stdout. It's the most common transport for
    locally-run MCP servers.

    The transport:
    - Spawns the server process with specified command and arguments
    - Merges environment variables with the parent process
    - Sets up stdin/stdout streams for JSON-RPC communication
    - Handles process lifecycle (spawn and termination)

    Example:
        >>> from mcp_config import StdioConfig
        >>> config = StdioConfig(
        ...     command="node",
        ...     args=["./dist/index.js"],
        ...     env={"API_KEY": "secret"}
        ... )
        >>> transport = StdioTransport(config)
        >>> async with transport.connect() as (read, write):
        ...     # Use read/write streams with ClientSession
        ...     pass
    """

    def __init__(self, config: StdioConfig):
        """
        Initialize stdio transport.

        Args:
            config: Stdio configuration with command, args, and environment
        """
        super().__init__(config)
        self.config: StdioConfig = config
        self._process = None

    @property
    def transport_type(self) -> str:
        """Return transport type identifier."""
        return "stdio"

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[tuple[Any, Any]]:
        """
        Spawn subprocess and establish stdio streams.

        Spawns the MCP server as a subprocess using the configured command,
        arguments, and environment variables. Yields read and write streams
        compatible with mcp.ClientSession.

        Yields:
            Tuple of (read_stream, write_stream) for JSON-RPC communication

        Raises:
            TransportError: If subprocess fails to spawn or terminates unexpectedly

        Note:
            The subprocess is automatically terminated when the context exits.
        """
        # Merge environment variables
        env = {**os.environ, **self.config.env}

        # Create server parameters
        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=env,
            cwd=self.config.cwd,
        )

        logger.debug(
            f"Spawning MCP server via stdio: {self.config.command} "
            f"{' '.join(self.config.args)}"
        )

        try:
            # Establish stdio connection using MCP SDK's stdio_client
            # This context manager handles subprocess lifecycle
            async with stdio_client(server_params) as (read, write):
                logger.debug(
                    f"Stdio connection established for: {self.config.command}"
                )
                yield read, write

        except Exception as e:
            logger.error(
                f"Stdio transport error for '{self.config.command}': {e}",
                exc_info=True,
            )
            raise TransportError(f"Stdio connection failed: {e}") from e

    async def close(self):
        """
        Close the transport and terminate subprocess.

        Note:
            The stdio_client context manager automatically handles process
            termination, so this method primarily serves as a clean shutdown hook.
        """
        logger.debug(f"Closing stdio transport for: {self.config.command}")
        # Process cleanup is handled by stdio_client context manager
        self._process = None

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on stdio transport.

        Returns:
            Dictionary with health status and configuration info
        """
        return {
            "status": "configured",
            "transport_type": self.transport_type,
            "command": self.config.command,
            "args": self.config.args,
            "env_vars": list(self.config.env.keys()),
            "cwd": self.config.cwd,
        }
