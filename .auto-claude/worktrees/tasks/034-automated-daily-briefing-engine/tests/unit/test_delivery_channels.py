"""
Unit tests for DeliveryChannels functionality.

Tests delivery channel abstraction, CLI, File, and Notification implementations.
"""

import unittest
import tempfile
import shutil
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from io import StringIO
from unittest.mock import patch, MagicMock

# Add Tools to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Tools.delivery_channels import (
    DeliveryChannel,
    CLIChannel,
    FileChannel,
    NotificationChannel,
    create_delivery_channel,
    deliver_to_channels
)


class TestCLIChannel(unittest.TestCase):
    """Test suite for CLIChannel class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        self.channel = CLIChannel(config={'color': True})
        self.test_content = "# Morning Briefing\n\nTop Priorities:\n1. Task 1\n2. Task 2"
        self.test_type = "morning"

    def test_initialization(self):
        """Test CLIChannel initialization."""
        self.assertIsInstance(self.channel, CLIChannel)
        self.assertTrue(self.channel.use_color)

    def test_initialization_no_color(self):
        """Test CLIChannel initialization with color disabled."""
        channel = CLIChannel(config={'color': False})
        self.assertFalse(channel.use_color)

    def test_initialization_default_config(self):
        """Test CLIChannel initialization with default config."""
        channel = CLIChannel()
        self.assertTrue(channel.use_color)

    @patch('sys.stdout', new_callable=StringIO)
    def test_deliver_with_color(self, mock_stdout):
        """Test delivery with color formatting."""
        # Temporarily enable TTY for color test
        with patch('sys.stdout.isatty', return_value=True):
            channel = CLIChannel(config={'color': True})
            result = channel.deliver(self.test_content, self.test_type)

        self.assertTrue(result)
        output = mock_stdout.getvalue()
        self.assertIn("MORNING BRIEFING", output)
        self.assertIn("Task 1", output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_deliver_without_color(self, mock_stdout):
        """Test delivery without color formatting."""
        channel = CLIChannel(config={'color': False})
        result = channel.deliver(self.test_content, self.test_type)

        self.assertTrue(result)
        output = mock_stdout.getvalue()
        self.assertIn("MORNING BRIEFING", output)
        self.assertIn("Task 1", output)
        # Check that no ANSI codes are present
        self.assertNotIn('\033[', output)

    @patch('sys.stdout', new_callable=StringIO)
    def test_deliver_with_metadata(self, mock_stdout):
        """Test delivery with metadata (metadata not used in CLI)."""
        metadata = {'date': '2026-01-11', 'priorities': []}
        result = self.channel.deliver(self.test_content, self.test_type, metadata)

        self.assertTrue(result)
        output = mock_stdout.getvalue()
        self.assertIn("MORNING BRIEFING", output)

    def test_format_markdown(self):
        """Test markdown formatting with colors."""
        with patch('sys.stdout.isatty', return_value=True):
            channel = CLIChannel(config={'color': True})

            content = "# Header 1\n## Header 2\n### Header 3\nNormal text"
            formatted = channel._format_markdown(content)

            # Should contain ANSI codes for headers
            self.assertIn('\033[', formatted)

    def test_format_markdown_no_color(self):
        """Test markdown formatting without colors."""
        channel = CLIChannel(config={'color': False})

        content = "# Header 1\n## Header 2\nNormal text"
        formatted = channel._format_markdown(content)

        # Should return content unchanged
        self.assertEqual(formatted, content)


class TestFileChannel(unittest.TestCase):
    """Test suite for FileChannel class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, "History", "DailyBriefings")

        self.channel = FileChannel(config={
            'output_dir': self.output_dir,
            'filename_pattern': '{date}_{type}_briefing.md'
        })

        self.test_content = "# Morning Briefing\n\nTop Priorities:\n1. Task 1\n2. Task 2"
        self.test_type = "morning"

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test FileChannel initialization."""
        self.assertIsInstance(self.channel, FileChannel)
        self.assertEqual(self.channel.output_dir, self.output_dir)
        self.assertEqual(self.channel.filename_pattern, '{date}_{type}_briefing.md')

    def test_initialization_default_config(self):
        """Test FileChannel initialization with default config."""
        channel = FileChannel()
        self.assertEqual(channel.output_dir, 'History/DailyBriefings')
        self.assertEqual(channel.filename_pattern, '{date}_{type}_briefing.md')

    def test_deliver_creates_file(self):
        """Test that delivery creates a file."""
        metadata = {'date': '2026-01-11'}
        result = self.channel.deliver(self.test_content, self.test_type, metadata)

        self.assertTrue(result)

        # Check file was created
        expected_filename = '2026-01-11_morning_briefing.md'
        expected_path = Path(self.output_dir) / expected_filename
        self.assertTrue(expected_path.exists())

    def test_deliver_file_content(self):
        """Test that file contains correct content."""
        metadata = {'date': '2026-01-11'}
        result = self.channel.deliver(self.test_content, self.test_type, metadata)

        self.assertTrue(result)

        # Read and verify file content
        expected_filename = '2026-01-11_morning_briefing.md'
        expected_path = Path(self.output_dir) / expected_filename

        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for metadata header
        self.assertIn('type: morning', content)
        self.assertIn('date: 2026-01-11', content)
        self.assertIn('generated_at:', content)

        # Check for actual content
        self.assertIn('# Morning Briefing', content)
        self.assertIn('Task 1', content)

    def test_deliver_creates_directory(self):
        """Test that delivery creates output directory if it doesn't exist."""
        # Create channel with non-existent directory
        new_output_dir = os.path.join(self.temp_dir, "NewDir", "Briefings")
        channel = FileChannel(config={
            'output_dir': new_output_dir,
            'filename_pattern': '{date}_{type}_briefing.md'
        })

        metadata = {'date': '2026-01-11'}
        result = channel.deliver(self.test_content, self.test_type, metadata)

        self.assertTrue(result)
        self.assertTrue(Path(new_output_dir).exists())

    def test_deliver_without_metadata(self):
        """Test delivery without metadata (uses current date)."""
        result = self.channel.deliver(self.test_content, self.test_type)

        self.assertTrue(result)

        # Check that a file was created (with today's date)
        files = list(Path(self.output_dir).glob('*_morning_briefing.md'))
        self.assertEqual(len(files), 1)

    def test_deliver_overwrites_existing_file(self):
        """Test that delivery overwrites existing file."""
        metadata = {'date': '2026-01-11'}

        # First delivery
        self.channel.deliver("First content", self.test_type, metadata)

        # Second delivery (should overwrite)
        result = self.channel.deliver("Second content", self.test_type, metadata)

        self.assertTrue(result)

        # Verify content was overwritten
        expected_filename = '2026-01-11_morning_briefing.md'
        expected_path = Path(self.output_dir) / expected_filename

        with open(expected_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('Second content', content)
        self.assertNotIn('First content', content)


class TestNotificationChannel(unittest.TestCase):
    """Test suite for NotificationChannel class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        self.channel = NotificationChannel(config={'summary_only': True})
        self.test_content = "# Morning Briefing\n\nTop Priorities:\n1. Task 1\n2. Task 2\n3. Task 3"
        self.test_type = "morning"

    def test_initialization(self):
        """Test NotificationChannel initialization."""
        self.assertIsInstance(self.channel, NotificationChannel)
        self.assertTrue(self.channel.summary_only)
        self.assertIsInstance(self.channel.notification_available, bool)

    def test_initialization_default_config(self):
        """Test NotificationChannel initialization with default config."""
        channel = NotificationChannel()
        self.assertTrue(channel.summary_only)

    def test_check_notification_availability(self):
        """Test notification availability check."""
        # Result depends on platform, just verify it returns a boolean
        available = self.channel._check_notification_availability()
        self.assertIsInstance(available, bool)

    def test_extract_summary_with_priorities(self):
        """Test summary extraction with priorities in metadata."""
        metadata = {
            'priorities': [
                {'title': 'First priority task'},
                {'title': 'Second priority task'},
                {'title': 'Third priority task'},
                {'title': 'Fourth priority task (should not appear)'}
            ]
        }

        summary = self.channel._extract_summary(self.test_content, metadata)

        self.assertIn('Top Priorities:', summary)
        self.assertIn('1. First priority task', summary)
        self.assertIn('2. Second priority task', summary)
        self.assertIn('3. Third priority task', summary)
        self.assertNotIn('Fourth priority task', summary)

    def test_extract_summary_without_metadata(self):
        """Test summary extraction without metadata (uses first lines)."""
        summary = self.channel._extract_summary(self.test_content, None)

        # Should include first few non-header lines
        self.assertIn('Task 1', summary)

    def test_extract_summary_truncates_long_titles(self):
        """Test that long priority titles are truncated."""
        long_title = "A" * 100  # 100 character title
        metadata = {
            'priorities': [
                {'title': long_title}
            ]
        }

        summary = self.channel._extract_summary(self.test_content, metadata)

        # Should be truncated to 60 chars
        self.assertLessEqual(len(summary.split('\n')[1]), 65)  # "1. " + 60 chars

    @patch('Tools.delivery_channels.NotificationChannel._send_notification')
    def test_deliver_when_available(self, mock_send):
        """Test delivery when notification system is available."""
        mock_send.return_value = True
        self.channel.notification_available = True

        result = self.channel.deliver(self.test_content, self.test_type)

        self.assertTrue(result)
        mock_send.assert_called_once()

    def test_deliver_when_unavailable(self):
        """Test delivery when notification system is unavailable."""
        self.channel.notification_available = False

        result = self.channel.deliver(self.test_content, self.test_type)

        self.assertFalse(result)

    def test_has_command(self):
        """Test command availability check."""
        # Test with a command that should exist
        has_ls = self.channel._has_command('ls')
        self.assertTrue(has_ls)

        # Test with a command that should not exist
        has_fake = self.channel._has_command('this_command_does_not_exist_12345')
        self.assertFalse(has_fake)


class TestFactoryFunction(unittest.TestCase):
    """Test suite for create_delivery_channel factory function."""

    def test_create_cli_channel(self):
        """Test creating CLI channel."""
        channel = create_delivery_channel('cli', {'color': True})
        self.assertIsInstance(channel, CLIChannel)
        self.assertTrue(channel.use_color)

    def test_create_file_channel(self):
        """Test creating File channel."""
        config = {
            'output_dir': 'test_output',
            'filename_pattern': '{date}_{type}.md'
        }
        channel = create_delivery_channel('file', config)
        self.assertIsInstance(channel, FileChannel)
        self.assertEqual(channel.output_dir, 'test_output')

    def test_create_notification_channel(self):
        """Test creating Notification channel."""
        channel = create_delivery_channel('notification', {'summary_only': False})
        self.assertIsInstance(channel, NotificationChannel)
        self.assertFalse(channel.summary_only)

    def test_create_with_case_insensitive_type(self):
        """Test that channel type is case-insensitive."""
        channel_lower = create_delivery_channel('cli')
        channel_upper = create_delivery_channel('CLI')
        channel_mixed = create_delivery_channel('Cli')

        self.assertIsInstance(channel_lower, CLIChannel)
        self.assertIsInstance(channel_upper, CLIChannel)
        self.assertIsInstance(channel_mixed, CLIChannel)

    def test_create_invalid_channel(self):
        """Test creating channel with invalid type."""
        channel = create_delivery_channel('invalid_type')
        self.assertIsNone(channel)

    def test_create_without_config(self):
        """Test creating channel without config."""
        channel = create_delivery_channel('cli')
        self.assertIsInstance(channel, CLIChannel)


class TestMultiChannelDelivery(unittest.TestCase):
    """Test suite for deliver_to_channels function."""

    def setUp(self):
        """Set up test fixtures before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_content = "# Morning Briefing\n\nTest content"
        self.test_type = "morning"

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    @patch('sys.stdout', new_callable=StringIO)
    def test_deliver_to_multiple_channels(self, mock_stdout):
        """Test delivering to multiple channels simultaneously."""
        channels_config = {
            'cli': {
                'enabled': True,
                'color': False
            },
            'file': {
                'enabled': True,
                'output_dir': self.temp_dir,
                'filename_pattern': '{date}_{type}_test.md'
            }
        }

        results = deliver_to_channels(
            self.test_content,
            self.test_type,
            channels_config,
            metadata={'date': '2026-01-11'}
        )

        # Both channels should succeed
        self.assertTrue(results['cli'])
        self.assertTrue(results['file'])

        # Verify CLI output
        output = mock_stdout.getvalue()
        self.assertIn("MORNING BRIEFING", output)

        # Verify file was created
        files = list(Path(self.temp_dir).glob('*_morning_test.md'))
        self.assertEqual(len(files), 1)

    def test_deliver_skips_disabled_channels(self):
        """Test that disabled channels are skipped."""
        channels_config = {
            'cli': {
                'enabled': False,
                'color': True
            },
            'file': {
                'enabled': True,
                'output_dir': self.temp_dir
            }
        }

        results = deliver_to_channels(
            self.test_content,
            self.test_type,
            channels_config,
            metadata={'date': '2026-01-11'}
        )

        # CLI should be skipped, file should succeed
        self.assertNotIn('cli', results)
        self.assertTrue(results['file'])

    def test_deliver_handles_invalid_channel(self):
        """Test handling of invalid channel types."""
        channels_config = {
            'invalid_type': {
                'enabled': True
            }
        }

        results = deliver_to_channels(
            self.test_content,
            self.test_type,
            channels_config
        )

        # Invalid channel should fail
        self.assertFalse(results['invalid_type'])

    def test_deliver_with_empty_config(self):
        """Test delivery with empty channels config."""
        results = deliver_to_channels(
            self.test_content,
            self.test_type,
            {}
        )

        # Should return empty results
        self.assertEqual(results, {})


if __name__ == '__main__':
    unittest.main()
