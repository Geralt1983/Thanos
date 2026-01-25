"""
Channel Abstraction Layer - Multi-platform messaging interface.

Provides a unified interface for sending/receiving messages across platforms:
- Telegram (implemented)
- iMessage (planned)
- Slack (planned)
- Discord (planned)

Usage:
    from Tools.channels import get_channel, ChannelManager

    # Get specific channel
    telegram = get_channel("telegram")
    await telegram.send("Hello from Thanos!")

    # Or use the manager for multi-channel
    manager = ChannelManager()
    await manager.broadcast("System update complete")
"""

from .base import Channel, Message, ChannelConfig, ChannelType
from .manager import ChannelManager, get_channel, get_default_channel

__all__ = [
    "Channel",
    "Message",
    "ChannelConfig",
    "ChannelType",
    "ChannelManager",
    "get_channel",
    "get_default_channel",
]
