#!/usr/bin/env python3
"""
Channel Manager - Unified interface for multi-channel messaging.

Manages multiple channels and provides routing, broadcasting, and fallback logic.
"""

import os
import asyncio
from typing import Dict, Optional, List, Type
from pathlib import Path

from .base import Channel, ChannelConfig, ChannelType, Message, CLIChannel


# Registry of channel implementations
_CHANNEL_REGISTRY: Dict[ChannelType, Type[Channel]] = {
    ChannelType.CLI: CLIChannel,
}

# Singleton instances
_channel_instances: Dict[ChannelType, Channel] = {}
_default_channel: Optional[ChannelType] = None


def register_channel(channel_type: ChannelType, channel_class: Type[Channel]):
    """
    Register a channel implementation.

    Args:
        channel_type: Type of channel
        channel_class: Channel implementation class
    """
    _CHANNEL_REGISTRY[channel_type] = channel_class


def get_channel(channel_type: str | ChannelType) -> Optional[Channel]:
    """
    Get a channel instance by type.

    Creates instance if not exists, using environment config.

    Args:
        channel_type: Channel type (string or enum)

    Returns:
        Channel instance or None if not available
    """
    if isinstance(channel_type, str):
        try:
            channel_type = ChannelType(channel_type.lower())
        except ValueError:
            return None

    # Return cached instance if exists
    if channel_type in _channel_instances:
        return _channel_instances[channel_type]

    # Check if implementation exists
    if channel_type not in _CHANNEL_REGISTRY:
        return None

    # Build config from environment
    config = _build_config_from_env(channel_type)
    if not config.enabled:
        return None

    # Create instance
    channel_class = _CHANNEL_REGISTRY[channel_type]
    instance = channel_class(config)
    _channel_instances[channel_type] = instance

    return instance


def get_default_channel() -> Optional[Channel]:
    """
    Get the default channel for sending messages.

    Priority: Telegram > Slack > Discord > CLI

    Returns:
        Default channel instance
    """
    global _default_channel

    if _default_channel and _default_channel in _channel_instances:
        return _channel_instances[_default_channel]

    # Try channels in priority order
    priority = [
        ChannelType.TELEGRAM,
        ChannelType.SLACK,
        ChannelType.DISCORD,
        ChannelType.CLI,
    ]

    for channel_type in priority:
        channel = get_channel(channel_type)
        if channel and channel.config.enabled:
            _default_channel = channel_type
            return channel

    return None


def _build_config_from_env(channel_type: ChannelType) -> ChannelConfig:
    """
    Build channel config from environment variables.

    Environment variable naming: THANOS_{CHANNEL}_{SETTING}
    e.g., THANOS_TELEGRAM_TOKEN, THANOS_SLACK_API_KEY

    Args:
        channel_type: Channel type to build config for

    Returns:
        ChannelConfig populated from environment
    """
    prefix = f"THANOS_{channel_type.value.upper()}_"

    # Also check without prefix for common vars
    token = (
        os.getenv(f"{prefix}TOKEN") or
        os.getenv(f"{prefix}BOT_TOKEN") or
        os.getenv(f"{channel_type.value.upper()}_BOT_TOKEN")
    )

    return ChannelConfig(
        channel_type=channel_type,
        enabled=os.getenv(f"{prefix}ENABLED", "true").lower() == "true",
        token=token,
        api_key=os.getenv(f"{prefix}API_KEY"),
        default_recipient=os.getenv(f"{prefix}DEFAULT_CHAT_ID") or os.getenv(f"{prefix}DEFAULT_RECIPIENT"),
        mention_only=os.getenv(f"{prefix}MENTION_ONLY", "false").lower() == "true",
        typing_indicator=os.getenv(f"{prefix}TYPING", "true").lower() == "true",
    )


class ChannelManager:
    """
    Manages multiple messaging channels with unified interface.

    Features:
    - Multi-channel message routing
    - Broadcast to all channels
    - Fallback logic on send failure
    - Unified message receiving across channels
    """

    def __init__(self):
        """Initialize channel manager."""
        self.channels: Dict[ChannelType, Channel] = {}
        self._receive_task: Optional[asyncio.Task] = None

    async def add_channel(self, channel: Channel) -> bool:
        """
        Add and connect a channel.

        Args:
            channel: Channel instance to add

        Returns:
            True if connected successfully
        """
        if await channel.connect():
            self.channels[channel.channel_type] = channel
            return True
        return False

    async def remove_channel(self, channel_type: ChannelType) -> None:
        """
        Remove and disconnect a channel.

        Args:
            channel_type: Channel to remove
        """
        if channel_type in self.channels:
            await self.channels[channel_type].disconnect()
            del self.channels[channel_type]

    def get(self, channel_type: ChannelType) -> Optional[Channel]:
        """Get a channel by type."""
        return self.channels.get(channel_type)

    @property
    def default(self) -> Optional[Channel]:
        """Get the default channel."""
        # Priority order
        for ct in [ChannelType.TELEGRAM, ChannelType.SLACK, ChannelType.CLI]:
            if ct in self.channels:
                return self.channels[ct]
        return None

    # =========================================================================
    # Sending
    # =========================================================================

    async def send(
        self,
        content: str,
        channel_type: Optional[ChannelType] = None,
        recipient: Optional[str] = None,
        fallback: bool = True,
        **kwargs
    ) -> Optional[Message]:
        """
        Send a message to a channel.

        Args:
            content: Message text
            channel_type: Target channel (uses default if None)
            recipient: Target chat/user ID
            fallback: Try other channels on failure
            **kwargs: Channel-specific options

        Returns:
            Sent message or None on failure
        """
        channel = (
            self.channels.get(channel_type) if channel_type
            else self.default
        )

        if channel:
            try:
                return await channel.send(content, recipient, **kwargs)
            except Exception as e:
                if not fallback:
                    raise

        # Fallback to other channels
        if fallback:
            for ch in self.channels.values():
                if ch != channel:
                    try:
                        return await ch.send(content, recipient, **kwargs)
                    except Exception:
                        continue

        return None

    async def broadcast(
        self,
        content: str,
        exclude: Optional[List[ChannelType]] = None,
        **kwargs
    ) -> Dict[ChannelType, Optional[Message]]:
        """
        Broadcast message to all channels.

        Args:
            content: Message text
            exclude: Channels to skip
            **kwargs: Channel-specific options

        Returns:
            Dict mapping channel type to sent message (or None on failure)
        """
        exclude = exclude or []
        results = {}

        for channel_type, channel in self.channels.items():
            if channel_type not in exclude:
                try:
                    results[channel_type] = await channel.send(content, **kwargs)
                except Exception:
                    results[channel_type] = None

        return results

    # =========================================================================
    # Receiving
    # =========================================================================

    async def receive_all(self):
        """
        Receive messages from all channels.

        Yields:
            Messages from any connected channel
        """
        async def channel_receiver(channel: Channel):
            async for message in channel.receive():
                yield message

        # Create tasks for all channels
        tasks = [
            asyncio.create_task(self._drain_channel(ch))
            for ch in self.channels.values()
        ]

        # This is a simplified version - real implementation would merge streams
        if tasks:
            await asyncio.gather(*tasks)

    async def _drain_channel(self, channel: Channel):
        """Drain messages from a single channel."""
        try:
            async for message in channel.receive():
                await channel._dispatch_message(message)
        except Exception as e:
            print(f"Error receiving from {channel.channel_type}: {e}")

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def connect_all(self) -> Dict[ChannelType, bool]:
        """
        Connect all configured channels.

        Returns:
            Dict mapping channel type to connection success
        """
        results = {}
        for channel_type, channel in self.channels.items():
            try:
                results[channel_type] = await channel.connect()
            except Exception:
                results[channel_type] = False
        return results

    async def disconnect_all(self) -> None:
        """Disconnect all channels."""
        for channel in self.channels.values():
            try:
                await channel.disconnect()
            except Exception:
                pass

    async def health_check(self) -> Dict[ChannelType, Dict]:
        """
        Check health of all channels.

        Returns:
            Dict mapping channel type to health status
        """
        results = {}
        for channel_type, channel in self.channels.items():
            try:
                results[channel_type] = await channel.health_check()
            except Exception as e:
                results[channel_type] = {"error": str(e)}
        return results


# =========================================================================
# Auto-register available channels
# =========================================================================

def _register_available_channels():
    """Register channel implementations that are available."""
    # Telegram
    try:
        from .telegram import TelegramChannel
        register_channel(ChannelType.TELEGRAM, TelegramChannel)
    except ImportError:
        pass

    # Future channels would be registered here
    # from .slack import SlackChannel
    # from .discord import DiscordChannel


# Run on import
_register_available_channels()
