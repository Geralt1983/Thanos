"""
DeliveryChannels - Abstraction for delivering briefings through multiple channels.

This module provides a base DeliveryChannel class and concrete implementations
for CLI, File, and Notification delivery methods.
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging


class DeliveryChannel(ABC):
    """
    Abstract base class for briefing delivery channels.

    Subclasses must implement the deliver() method to handle
    channel-specific delivery logic.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the delivery channel.

        Args:
            config: Channel-specific configuration dictionary.
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def deliver(self, content: str, briefing_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Deliver the briefing content through this channel.

        Args:
            content: The briefing content to deliver (typically markdown).
            briefing_type: Type of briefing ('morning', 'evening', etc.).
            metadata: Optional metadata about the briefing.

        Returns:
            True if delivery was successful, False otherwise.
        """
        pass

    def log_delivery(self, briefing_type: str, success: bool, details: str = ""):
        """
        Log the delivery attempt.

        Args:
            briefing_type: Type of briefing delivered.
            success: Whether delivery was successful.
            details: Additional details about the delivery.
        """
        timestamp = datetime.now().isoformat()
        status = "SUCCESS" if success else "FAILED"
        message = f"[{timestamp}] {self.__class__.__name__} - {briefing_type} - {status}"
        if details:
            message += f" - {details}"

        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)


class CLIChannel(DeliveryChannel):
    """
    Delivery channel that prints briefings to stdout with optional color formatting.

    Supports ANSI color codes for enhanced readability in terminal environments.
    """

    # ANSI color codes
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CLIChannel.

        Args:
            config: Configuration with optional 'color' boolean (default: True).
        """
        super().__init__(config)
        self.use_color = self.config.get('color', True)

        # Disable color on non-TTY outputs (e.g., when piped)
        if not sys.stdout.isatty():
            self.use_color = False

    def deliver(self, content: str, briefing_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Print the briefing to stdout with optional color formatting.

        Args:
            content: The briefing content to print.
            briefing_type: Type of briefing ('morning', 'evening', etc.).
            metadata: Optional metadata (not used in CLI output).

        Returns:
            True if printing was successful, False otherwise.
        """
        try:
            # Add header with color if enabled
            if self.use_color:
                header_color = self.COLORS['cyan'] + self.COLORS['bold']
                reset = self.COLORS['reset']
                separator = self.COLORS['blue'] + "=" * 80 + reset

                print(f"\n{separator}")
                print(f"{header_color}{briefing_type.upper()} BRIEFING{reset}")
                print(f"{separator}\n")

                # Apply subtle formatting to markdown headers
                formatted_content = self._format_markdown(content)
                print(formatted_content)

                print(f"\n{separator}\n")
            else:
                # Plain output without colors
                print(f"\n{'=' * 80}")
                print(f"{briefing_type.upper()} BRIEFING")
                print(f"{'=' * 80}\n")
                print(content)
                print(f"\n{'=' * 80}\n")

            self.log_delivery(briefing_type, True, "Printed to stdout")
            return True

        except Exception as e:
            self.log_delivery(briefing_type, False, f"Error: {e}")
            return False

    def _format_markdown(self, content: str) -> str:
        """
        Apply color formatting to markdown elements.

        Args:
            content: Raw markdown content.

        Returns:
            Content with ANSI color codes for headers and emphasis.
        """
        if not self.use_color:
            return content

        lines = content.split('\n')
        formatted_lines = []

        for line in lines:
            # Color headers
            if line.startswith('# '):
                line = self.COLORS['bold'] + self.COLORS['magenta'] + line + self.COLORS['reset']
            elif line.startswith('## '):
                line = self.COLORS['bold'] + self.COLORS['cyan'] + line + self.COLORS['reset']
            elif line.startswith('### '):
                line = self.COLORS['bold'] + self.COLORS['blue'] + line + self.COLORS['reset']

            formatted_lines.append(line)

        return '\n'.join(formatted_lines)


class FileChannel(DeliveryChannel):
    """
    Delivery channel that writes briefings to the filesystem.

    Saves briefings to configured directory with customizable filename patterns.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize FileChannel.

        Args:
            config: Configuration with 'output_dir' and 'filename_pattern'.
                   Example: {
                       'output_dir': 'History/DailyBriefings',
                       'filename_pattern': '{date}_{type}_briefing.md'
                   }
        """
        super().__init__(config)
        self.output_dir = self.config.get('output_dir', 'History/DailyBriefings')
        self.filename_pattern = self.config.get('filename_pattern', '{date}_{type}_briefing.md')

    def deliver(self, content: str, briefing_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Write the briefing to a file.

        Args:
            content: The briefing content to write.
            briefing_type: Type of briefing ('morning', 'evening', etc.).
            metadata: Optional metadata with 'date' field.

        Returns:
            True if file was written successfully, False otherwise.
        """
        try:
            # Prepare output directory
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Generate filename
            today = datetime.now().strftime("%Y-%m-%d")
            if metadata and 'date' in metadata:
                today = metadata['date']

            filename = self.filename_pattern.format(
                date=today,
                type=briefing_type
            )

            file_path = output_path / filename

            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                # Add metadata header
                f.write(f"---\n")
                f.write(f"type: {briefing_type}\n")
                f.write(f"date: {today}\n")
                f.write(f"generated_at: {datetime.now().isoformat()}\n")
                f.write(f"---\n\n")
                f.write(content)

            self.log_delivery(briefing_type, True, f"Saved to {file_path}")
            return True

        except Exception as e:
            self.log_delivery(briefing_type, False, f"Error: {e}")
            return False


class NotificationChannel(DeliveryChannel):
    """
    Delivery channel for OS-level desktop notifications.

    Uses platform-specific notification systems:
    - macOS: terminal-notifier or osascript
    - Linux: notify-send
    - Windows: Not yet supported
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize NotificationChannel.

        Args:
            config: Configuration with optional 'summary_only' boolean.
                   Example: {
                       'summary_only': True  # Only show top 3 priorities
                   }
        """
        super().__init__(config)
        self.summary_only = self.config.get('summary_only', True)
        self.notification_available = self._check_notification_availability()

    def _check_notification_availability(self) -> bool:
        """
        Check if notification system is available on this platform.

        Returns:
            True if notifications can be sent, False otherwise.
        """
        import platform
        import shutil

        system = platform.system()

        if system == 'Darwin':  # macOS
            # Check for terminal-notifier or osascript
            return shutil.which('terminal-notifier') is not None or shutil.which('osascript') is not None
        elif system == 'Linux':
            # Check for notify-send
            return shutil.which('notify-send') is not None
        else:
            return False

    def deliver(self, content: str, briefing_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send a desktop notification with briefing summary.

        Args:
            content: The full briefing content.
            briefing_type: Type of briefing ('morning', 'evening', etc.).
            metadata: Optional metadata with 'priorities' field.

        Returns:
            True if notification was sent successfully, False otherwise.
        """
        # Gracefully degrade if notifications not available
        if not self.notification_available:
            self.log_delivery(briefing_type, False, "Notification system not available")
            return False

        try:
            # Extract summary (top 3 priorities or first few lines)
            summary = self._extract_summary(content, metadata)

            # Send notification based on platform
            success = self._send_notification(
                title=f"{briefing_type.capitalize()} Briefing",
                message=summary
            )

            if success:
                self.log_delivery(briefing_type, True, "Notification sent")
            else:
                self.log_delivery(briefing_type, False, "Failed to send notification")

            return success

        except Exception as e:
            self.log_delivery(briefing_type, False, f"Error: {e}")
            return False

    def _extract_summary(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Extract a brief summary from the briefing content.

        Args:
            content: Full briefing content.
            metadata: Optional metadata with 'priorities' field.

        Returns:
            Brief summary suitable for notification.
        """
        if metadata and 'priorities' in metadata and self.summary_only:
            # Use top 3 priorities if available
            priorities = metadata['priorities'][:3]
            if priorities:
                summary_lines = ["Top Priorities:"]
                for i, priority in enumerate(priorities, 1):
                    # Extract title from priority dict or string
                    if isinstance(priority, dict):
                        title = priority.get('title', priority.get('text', str(priority)))
                    else:
                        title = str(priority)
                    summary_lines.append(f"{i}. {title[:60]}")
                return '\n'.join(summary_lines)

        # Fallback: use first few lines of content
        lines = [line for line in content.split('\n') if line.strip() and not line.startswith('#')]
        return '\n'.join(lines[:3])

    def _send_notification(self, title: str, message: str) -> bool:
        """
        Send notification using platform-specific command.

        Args:
            title: Notification title.
            message: Notification message body.

        Returns:
            True if notification sent successfully, False otherwise.
        """
        import platform
        import subprocess

        system = platform.system()

        try:
            if system == 'Darwin':  # macOS
                # Try terminal-notifier first
                if self._has_command('terminal-notifier'):
                    subprocess.run([
                        'terminal-notifier',
                        '-title', title,
                        '-message', message,
                        '-sound', 'default'
                    ], check=True, capture_output=True)
                    return True

                # Fallback to osascript
                elif self._has_command('osascript'):
                    script = f'display notification "{message}" with title "{title}"'
                    subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                    return True

            elif system == 'Linux':
                # Use notify-send
                if self._has_command('notify-send'):
                    subprocess.run([
                        'notify-send',
                        title,
                        message,
                        '-u', 'normal'
                    ], check=True, capture_output=True)
                    return True

            return False

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Notification command failed: {e}")
            return False

    def _has_command(self, command: str) -> bool:
        """
        Check if a command is available in PATH.

        Args:
            command: Command name to check.

        Returns:
            True if command is available, False otherwise.
        """
        import shutil
        return shutil.which(command) is not None


def create_delivery_channel(channel_type: str, config: Optional[Dict[str, Any]] = None) -> Optional[DeliveryChannel]:
    """
    Factory function to create delivery channel instances.

    Args:
        channel_type: Type of channel ('cli', 'file', 'notification').
        config: Channel-specific configuration.

    Returns:
        DeliveryChannel instance or None if type is invalid.

    Examples:
        >>> cli_channel = create_delivery_channel('cli', {'color': True})
        >>> file_channel = create_delivery_channel('file', {
        ...     'output_dir': 'History/DailyBriefings',
        ...     'filename_pattern': '{date}_{type}_briefing.md'
        ... })
    """
    channels = {
        'cli': CLIChannel,
        'file': FileChannel,
        'notification': NotificationChannel,
    }

    channel_class = channels.get(channel_type.lower())
    if channel_class:
        return channel_class(config)

    return None


def deliver_to_channels(
    content: str,
    briefing_type: str,
    channels_config: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, bool]:
    """
    Deliver briefing content to multiple channels simultaneously.

    Args:
        content: The briefing content to deliver.
        briefing_type: Type of briefing ('morning', 'evening', etc.).
        channels_config: Dictionary mapping channel types to their configs.
                        Example: {
                            'cli': {'enabled': True, 'color': True},
                            'file': {'enabled': True, 'output_dir': 'History/DailyBriefings'}
                        }
        metadata: Optional metadata to pass to channels.

    Returns:
        Dictionary mapping channel types to delivery success status.

    Examples:
        >>> results = deliver_to_channels(
        ...     content="# Morning Briefing\\n...",
        ...     briefing_type="morning",
        ...     channels_config={
        ...         'cli': {'enabled': True, 'color': True},
        ...         'file': {'enabled': True, 'output_dir': 'History/DailyBriefings'}
        ...     }
        ... )
        >>> print(results)
        {'cli': True, 'file': True}
    """
    results = {}

    for channel_type, channel_config in channels_config.items():
        # Skip disabled channels
        if not channel_config.get('enabled', True):
            continue

        # Create and use channel
        channel = create_delivery_channel(channel_type, channel_config)
        if channel:
            success = channel.deliver(content, briefing_type, metadata)
            results[channel_type] = success
        else:
            results[channel_type] = False

    return results
