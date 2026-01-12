"""
MCP Transport Layer.

Provides transport abstractions for communicating with MCP servers via different
protocols: stdio (subprocess), SSE (Server-Sent Events), and HTTP/HTTPS.
"""

from .base import Transport, TransportError
from .stdio import StdioTransport
from .sse import SSETransport

__all__ = [
    "Transport",
    "TransportError",
    "StdioTransport",
    "SSETransport",
]
