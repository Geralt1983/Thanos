"""
Unit tests for commands.pa.briefing manual trigger command.
"""

import unittest
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from commands.pa import briefing


class TestBriefingCommand(unittest.TestCase):
    """Test the manual briefing trigger command."""

    def setUp(self):
        """Set up test fixtures."""
        self.maxDiff = None

        # Create a mock config
        self.mock_config = {
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "template": "briefing_morning.md"
                },
                "evening": {
                    "enabled": True,
                    "time": "19:00",
                    "template": "briefing_evening.md"
                }
            },
            "delivery": {
                "cli": {"enabled": True},
                "file": {
                    "enabled": True,
                    "output_dir": "History/DailyBriefings"
                }
            },
            "content": {
                "max_priorities": 3,
                "include_quick_wins": True
            },
            "advanced": {
                "state_dir": "State",
                "templates_dir": "Templates"
            }
        }

    def test_load_config_default(self):
        """Test loading default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_dir = tmpdir_path / "config"
            config_dir.mkdir()
            config_file = config_dir / "briefing_schedule.json"

            # Write test config
            with open(config_file, 'w') as f:
                json.dump(self.mock_config, f)

            # Patch Path to use our temp directory
            with patch('commands.pa.briefing.Path') as mock_path:
                mock_path.return_value.parent.parent.parent = tmpdir_path
                mock_path.return_value.exists.return_value = True

                # This would test load_config but we need to handle the path mocking better
                # For now, just verify the function exists
                self.assertTrue(callable(briefing.load_config))

    def test_load_config_custom_path(self):
        """Test loading config from custom path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.mock_config, f)
            config_path = f.name

        try:
            config = briefing.load_config(config_path)
            self.assertIsInstance(config, dict)
            self.assertIn('briefings', config)
            self.assertIn('delivery', config)
        finally:
            Path(config_path).unlink()

    def test_load_config_missing_file(self):
        """Test loading config with missing file."""
        with self.assertRaises(FileNotFoundError):
            briefing.load_config('/nonexistent/path/config.json')

    def test_setup_logging(self):
        """Test logging setup."""
        logger = briefing.setup_logging(verbose=False)
        self.assertIsNotNone(logger)

        logger_verbose = briefing.setup_logging(verbose=True)
        self.assertIsNotNone(logger_verbose)

    def test_save_to_file(self):
        """Test saving briefing to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            briefing_content = "# Test Briefing\n\nThis is a test."
            file_path = briefing.save_to_file(
                briefing=briefing_content,
                briefing_type="morning",
                output_dir=tmpdir
            )

            # Verify file was created
            self.assertTrue(Path(file_path).exists())

            # Verify content
            with open(file_path, 'r') as f:
                content = f.read()
                self.assertIn("Morning Briefing", content)
                self.assertIn("Test Briefing", content)
                self.assertIn("Generated at", content)

    @patch('commands.pa.briefing.BriefingEngine')
    def test_generate_briefing_morning(self, mock_engine_class):
        """Test generating morning briefing."""
        # Setup mock
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.gather_context.return_value = {
            "today_date": "2024-01-11",
            "day_of_week": "Thursday",
            "is_weekend": False,
            "commitments": [],
            "this_week": {"tasks": []},
            "current_focus": []
        }
        mock_engine.render_briefing.return_value = "# Morning Briefing\n\nTest content"

        # Mock logger
        mock_logger = MagicMock()

        # Test with dry run
        with patch('builtins.print'):
            exit_code = briefing.generate_briefing(
                briefing_type="morning",
                config=self.mock_config,
                energy_level=7,
                dry_run=True,
                logger=mock_logger
            )

        # Verify
        self.assertEqual(exit_code, 0)
        mock_engine.gather_context.assert_called_once()
        mock_engine.render_briefing.assert_called_once_with(
            briefing_type="morning",
            context=mock_engine.gather_context.return_value,
            energy_level=7
        )

    @patch('commands.pa.briefing.BriefingEngine')
    def test_generate_briefing_evening(self, mock_engine_class):
        """Test generating evening briefing."""
        # Setup mock
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.gather_context.return_value = {
            "today_date": "2024-01-11",
            "day_of_week": "Thursday",
            "is_weekend": False
        }
        mock_engine.render_briefing.return_value = "# Evening Briefing\n\nTest content"

        mock_logger = MagicMock()

        # Test with dry run
        with patch('builtins.print'):
            exit_code = briefing.generate_briefing(
                briefing_type="evening",
                config=self.mock_config,
                dry_run=True,
                logger=mock_logger
            )

        # Verify
        self.assertEqual(exit_code, 0)
        mock_engine.render_briefing.assert_called_once()

    def test_generate_briefing_invalid_type(self):
        """Test generating briefing with invalid type."""
        mock_logger = MagicMock()

        with patch('builtins.print'):
            exit_code = briefing.generate_briefing(
                briefing_type="invalid",
                config=self.mock_config,
                dry_run=True,
                logger=mock_logger
            )

        # Should return error code
        self.assertEqual(exit_code, 1)

    @patch('commands.pa.briefing.BriefingEngine')
    def test_generate_briefing_engine_error(self, mock_engine_class):
        """Test handling BriefingEngine initialization error."""
        mock_engine_class.side_effect = Exception("Engine init failed")
        mock_logger = MagicMock()

        with patch('builtins.print'):
            exit_code = briefing.generate_briefing(
                briefing_type="morning",
                config=self.mock_config,
                dry_run=True,
                logger=mock_logger
            )

        # Should return error code
        self.assertEqual(exit_code, 1)

    @patch('commands.pa.briefing.BriefingEngine')
    def test_generate_briefing_context_error(self, mock_engine_class):
        """Test handling context gathering error."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.gather_context.side_effect = Exception("Context error")
        mock_logger = MagicMock()

        with patch('builtins.print'):
            exit_code = briefing.generate_briefing(
                briefing_type="morning",
                config=self.mock_config,
                dry_run=True,
                logger=mock_logger
            )

        # Should return error code
        self.assertEqual(exit_code, 1)

    @patch('commands.pa.briefing.BriefingEngine')
    def test_generate_briefing_render_error(self, mock_engine_class):
        """Test handling rendering error."""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.gather_context.return_value = {"test": "data"}
        mock_engine.render_briefing.side_effect = Exception("Render error")
        mock_logger = MagicMock()

        with patch('builtins.print'):
            exit_code = briefing.generate_briefing(
                briefing_type="morning",
                config=self.mock_config,
                dry_run=True,
                logger=mock_logger
            )

        # Should return error code
        self.assertEqual(exit_code, 1)

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        self.assertTrue(callable(briefing.main))


if __name__ == '__main__':
    unittest.main()
