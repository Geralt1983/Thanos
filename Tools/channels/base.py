#!/usr/bin/env python3
"""
Channel Base Classes - Abstract interface for multi-platform messaging.

Defines the contract that all channel implementations must follow.
Inspired by clawdbot's multi-channel architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, AsyncIterator, Callable, Awaitable
import asyncio


class ChannelType(Enum):
    """Supported channel types."""
    TELEGRAM = "telegram"
    IMESSAGE = "imessage"
    SLACK = "slack"
    DISCORD = "discord"
    SIGNAL = "signal"
    WHATSAPP = "whatsapp"
    CLI = "cli"  # Local terminal/interactive mode


class MessageType(Enum):
    """Types of messages."""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    DOCUMENT = "document"
    COMMAND = "command"
    REACTION = "reaction"


@dataclass
class Message:
    """
    Universal message format across all channels.

    Normalizes messages from different platforms into a common structure.
    """
    id: str
    channel_type: ChannelType
    channel_id: str  # Platform-specific identifier (chat_id, user_id, etc.)
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = field(default_factory=datetime.now)

    # Sender info
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    is_from_bot: bool = False

    # Reply context
    reply_to_id: Optional[str] = None
    thread_id: Optional[str] = None

    # Media attachments
    media_url: Optional[str] = None
    media_type: Optional[str] = None  # mime type
    media_data: Optional[bytes] = None

    # Platform-specific extras
    raw_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_command(self) -> bool:
        """Check if this is a command message."""
        return self.content.startswith("/") or self.message_type == MessageType.COMMAND


@dataclass
class ChannelConfig:
    """Configuration for a channel."""
    channel_type: ChannelType
    enabled: bool = True

    # Auth
    token: Optional[str] = None
    api_key: Optional[str] = None

    # Routing
    default_recipient: Optional[str] = None  # Default chat_id/user to send to
    allowed_senders: Optional[List[str]] = None  # Whitelist (None = allow all)
    blocked_senders: Optional[List[str]] = None  # Blacklist

    # Behavior
    auto_reply: bool = False  # Auto-acknowledge messages
    mention_only: bool = False  # Only respond when mentioned (for groups)
    typing_indicator: bool = True  # Show typing while processing

    # Rate limiting
    rate_limit_messages: int = 30  # Max messages per minute
    rate_limit_window: int = 60  # Window in seconds

    # Platform-specific
    extras: Dict[str, Any] = field(default_factory=dict)


class Channel(ABC):
    """
    Abstract base class for messaging channels.

    All channel implementations must implement these methods.
    """

    def __init__(self, config: ChannelConfig):
        """
        Initialize channel with configuration.

        Args:
            config: Channel configuration
        """
        self.config = config
        self.channel_type = config.channel_type
        self._connected = False
        self._message_handlers: List[Callable[[Message], Awaitable[None]]] = []

    @property
    def is_connected(self) -> bool:
        """Check if channel is connected."""
        return self._connected

    # =========================================================================
    # Connection Lifecycle
    # =========================================================================

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the messaging platform.

        Returns:
            True if connected successfully
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the platform."""
        pass

    async def reconnect(self) -> bool:
        """Reconnect to the platform."""
        await self.disconnect()
        return await self.connect()

    # =========================================================================
    # Sending Messages
    # =========================================================================

    @abstractmethod
    async def send(
        self,
        content: str,
        recipient: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs
    ) -> Optional[Message]:
        """
        Send a text message.

        Args:
            content: Message text
            recipient: Target chat/user ID (uses default if None)
            reply_to: Message ID to reply to
            **kwargs: Platform-specific options

        Returns:
            Sent message object, or None on failure
        """
        pass

    async def send_media(
        self,
        media_path: str,
        caption: Optional[str] = None,
        recipient: Optional[str] = None,
        media_type: str = "auto",
        **kwargs
    ) -> Optional[Message]:
        """
        Send media (image, document, etc.).

        Default implementation raises NotImplementedError.
        Channels should override if they support media.

        Args:
            media_path: Path to media file
            caption: Optional caption
            recipient: Target chat/user ID
            media_type: "auto", "photo", "document", "audio", "video"
            **kwargs: Platform-specific options

        Returns:
            Sent message object, or None on failure
        """
        raise NotImplementedError(f"{self.channel_type} does not support media")

    async def send_typing(self, recipient: Optional[str] = None) -> None:
        """
        Send typing indicator.

        Default implementation does nothing.
        Channels should override if they support typing indicators.
        """
        pass

    # =========================================================================
    # Receiving Messages
    # =========================================================================

    @abstractmethod
    async def receive(self) -> AsyncIterator[Message]:
        """
        Receive incoming messages as an async iterator.

        Yields:
            Incoming Message objects
        """
        # Must be implemented as: async for message in ...: yield message
        pass

    def on_message(self, handler: Callable[[Message], Awaitable[None]]) -> None:
        """
        Register a message handler callback.

        Args:
            handler: Async function to call on each message
        """
        self._message_handlers.append(handler)

    async def _dispatch_message(self, message: Message) -> None:
        """
        Dispatch message to all registered handlers.

        Args:
            message: Received message
        """
        for handler in self._message_handlers:
            try:
                await handler(message)
            except Exception as e:
                # Log but don't crash on handler errors
                print(f"Error in message handler: {e}")

    # =========================================================================
    # Security
    # =========================================================================

    def is_sender_allowed(self, sender_id: str) -> bool:
        """
        Check if sender is allowed to send messages.

        Implements allowlist/blocklist checking.

        Args:
            sender_id: Sender's platform-specific ID

        Returns:
            True if sender is allowed
        """
        # Check blocklist first
        if self.config.blocked_senders and sender_id in self.config.blocked_senders:
            return False

        # If allowlist exists, sender must be on it
        if self.config.allowed_senders:
            return sender_id in self.config.allowed_senders

        # No allowlist = allow all (except blocked)
        return True

    # =========================================================================
    # Utility
    # =========================================================================

    def get_default_recipient(self) -> Optional[str]:
        """Get the default recipient for this channel."""
        return self.config.default_recipient

    async def health_check(self) -> Dict[str, Any]:
        """
        Check channel health.

        Returns:
            Dict with status, latency, and any issues
        """
        return {
            "channel": self.channel_type.value,
            "connected": self._connected,
            "enabled": self.config.enabled,
        }


class CLIChannel(Channel):
    """
    CLI/Terminal channel - for local interactive mode.

    This is a simple implementation that reads from stdin and writes to stdout.
    Useful as a fallback when no other channels are available.
    """

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def send(
        self,
        content: str,
        recipient: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs
    ) -> Optional[Message]:
        print(f"\n{content}")
        return Message(
            id="cli_" + str(datetime.now().timestamp()),
            channel_type=ChannelType.CLI,
            channel_id="local",
            content=content,
            is_from_bot=True
        )

    async def receive(self) -> AsyncIterator[Message]:
        """Read from stdin."""
        while self._connected:
            try:
                # Non-blocking input with asyncio
                loop = asyncio.get_event_loop()
                user_input = await loop.run_in_executor(None, input, "You: ")

                if user_input.lower() in ("quit", "exit", "/quit", "/exit"):
                    break

                yield Message(
                    id="cli_" + str(datetime.now().timestamp()),
                    channel_type=ChannelType.CLI,
                    channel_id="local",
                    content=user_input,
                    sender_id="user",
                    sender_name="User"
                )
            except EOFError:
                break
