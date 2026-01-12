"""
Unit tests for BriefingScheduler daemon.

Tests scheduler logic, duplicate prevention, time checking, and execution flow.
"""

import unittest
import tempfile
import shutil
import json
import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Tools.briefing_scheduler import BriefingScheduler


class TestBriefingScheduler(unittest.TestCase):
    """Test suite for BriefingScheduler class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create temporary directory structure
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.state_dir = Path(self.temp_dir) / "State"
        self.templates_dir = Path(self.temp_dir) / "Templates"
        self.logs_dir = Path(self.temp_dir) / "logs"

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Create History/DailyBriefings directory for file delivery tests
        self.history_dir = Path(self.temp_dir) / "History" / "DailyBriefings"
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal valid config
        self.config_path = self.config_dir / "briefing_schedule.json"
        self.default_config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "timezone": "local",
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        "wednesday": True,
                        "thursday": True,
                        "friday": True,
                        "saturday": True,
                        "sunday": True
                    },
                    "template": "briefing_morning.md",
                    "delivery_channels": ["cli", "file"]
                },
                "evening": {
                    "enabled": False,
                    "time": "19:00",
                    "timezone": "local",
                    "days": {
                        "monday": True,
                        "tuesday": True,
                        "wednesday": True,
                        "thursday": True,
                        "friday": True,
                        "saturday": False,
                        "sunday": False
                    },
                    "template": "briefing_evening.md",
                    "delivery_channels": ["cli"]
                }
            },
            "delivery": {
                "cli": {"enabled": True, "color": True},
                "file": {
                    "enabled": True,
                    "output_dir": str(Path(self.temp_dir) / "History" / "DailyBriefings"),
                    "filename_pattern": "{date}_{type}_briefing.md"
                }
            },
            "scheduler": {
                "check_interval_minutes": 1,
                "prevent_duplicate_runs": True,
                "log_file": str(self.logs_dir / "briefing_scheduler.log")
            },
            "content": {
                "max_priorities": 3,
                "include_quick_wins": True
            },
            "advanced": {
                "state_dir": str(self.state_dir),
                "templates_dir": str(self.templates_dir)
            }
        }

        # Create schema file (minimal for validation to pass)
        schema_path = self.config_dir / "briefing_schedule.schema.json"
        with open(schema_path, 'w') as f:
            json.dump({"type": "object"}, f)

        self._write_config(self.default_config)

        # Create minimal template files
        (self.templates_dir / "briefing_morning.md").write_text("# Morning Briefing\n{{ today_date }}")
        (self.templates_dir / "briefing_evening.md").write_text("# Evening Briefing\n{{ today_date }}")

        # Create minimal State files
        (self.state_dir / "Commitments.md").write_text("# Commitments\n")
        (self.state_dir / "ThisWeek.md").write_text("# This Week\n")
        (self.state_dir / "CurrentFocus.md").write_text("# Current Focus\n")

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def _write_config(self, config):
        """Helper to write config to file."""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        self.assertEqual(scheduler.config_path, self.config_path)
        self.assertEqual(scheduler.state_dir, self.state_dir)
        self.assertEqual(scheduler.templates_dir, self.templates_dir)
        self.assertIsNotNone(scheduler.logger)
        self.assertIsNotNone(scheduler.engine)
        self.assertFalse(scheduler.should_stop)

    def test_config_validation_on_init(self):
        """Test that completely invalid JSON raises error on initialization."""
        # Write invalid JSON (not just missing fields, but malformed JSON)
        with open(self.config_path, 'w') as f:
            f.write("{invalid json without quotes")

        # Should raise ValueError due to JSON parsing error
        with self.assertRaises(ValueError):
            BriefingScheduler(
                config_path=str(self.config_path),
                state_dir=str(self.state_dir),
                templates_dir=str(self.templates_dir)
            )

    def test_get_current_day_name(self):
        """Test getting current day name."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        day_name = scheduler._get_current_day_name()
        self.assertIn(day_name, [
            "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"
        ])

    def test_duplicate_prevention_has_not_run(self):
        """Test duplicate prevention when briefing has not run today."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        self.assertFalse(scheduler._has_run_today("morning"))
        self.assertFalse(scheduler._has_run_today("evening"))

    def test_duplicate_prevention_mark_as_run(self):
        """Test marking a briefing as run."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        scheduler._mark_as_run("morning")

        self.assertTrue(scheduler._has_run_today("morning"))
        self.assertFalse(scheduler._has_run_today("evening"))

    def test_duplicate_prevention_disabled(self):
        """Test that duplicate prevention can be disabled."""
        config = self.default_config.copy()
        config["scheduler"]["prevent_duplicate_runs"] = False
        self._write_config(config)

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Mark as run
        scheduler._mark_as_run("morning")

        # Should still return False when prevention is disabled
        self.assertFalse(scheduler._has_run_today("morning"))

    def test_should_run_briefing_disabled(self):
        """Test that disabled briefings don't run."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        config = {"enabled": False, "time": "07:00", "days": {"monday": True}}
        result = scheduler._should_run_briefing("test", config, datetime.now())

        self.assertFalse(result)

    def test_should_run_briefing_wrong_day(self):
        """Test that briefings don't run on disabled days."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        current_day = scheduler._get_current_day_name()
        config = {
            "enabled": True,
            "time": "07:00",
            "days": {current_day: False}  # Disable current day
        }

        result = scheduler._should_run_briefing("test", config, datetime.now())
        self.assertFalse(result)

    def test_should_run_briefing_already_run(self):
        """Test that briefings don't run twice on same day."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        current_day = scheduler._get_current_day_name()
        now = datetime.now()

        config = {
            "enabled": True,
            "time": now.strftime("%H:%M"),
            "days": {current_day: True}
        }

        # Mark as already run
        scheduler._mark_as_run("test")

        result = scheduler._should_run_briefing("test", config, now)
        self.assertFalse(result)

    def test_should_run_briefing_correct_time(self):
        """Test that briefing runs at correct time."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        current_day = scheduler._get_current_day_name()
        now = datetime.now()

        config = {
            "enabled": True,
            "time": now.strftime("%H:%M"),  # Current time
            "days": {current_day: True}
        }

        result = scheduler._should_run_briefing("test", config, now)
        self.assertTrue(result)

    def test_should_run_briefing_wrong_time(self):
        """Test that briefing doesn't run at wrong time."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        current_day = scheduler._get_current_day_name()
        now = datetime.now()
        different_time = (now + timedelta(hours=1)).strftime("%H:%M")

        config = {
            "enabled": True,
            "time": different_time,  # Different time
            "days": {current_day: True}
        }

        result = scheduler._should_run_briefing("test", config, now)
        self.assertFalse(result)

    def test_run_state_persistence(self):
        """Test that run state is persisted across scheduler instances."""
        # Create first scheduler and mark run
        scheduler1 = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )
        scheduler1._mark_as_run("morning")

        # Create second scheduler and check if state is loaded
        scheduler2 = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        self.assertTrue(scheduler2._has_run_today("morning"))

    def test_run_state_cleanup(self):
        """Test that old run state entries are cleaned up."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Add old entry (8 days ago)
        old_date = (date.today() - timedelta(days=8)).isoformat()
        scheduler.run_state[f"{old_date}_morning"] = {
            "timestamp": datetime.now().isoformat(),
            "type": "morning"
        }

        # Mark new run (this triggers cleanup)
        scheduler._mark_as_run("morning")

        # Old entry should be removed
        self.assertNotIn(f"{old_date}_morning", scheduler.run_state)

    @patch('Tools.briefing_scheduler.BriefingEngine')
    def test_run_briefing_success(self, mock_engine_class):
        """Test successful briefing execution."""
        # Mock the engine
        mock_engine = MagicMock()
        mock_engine.gather_context.return_value = {
            "today_date": date.today().isoformat(),
            "commitments": []
        }
        mock_engine.render_briefing.return_value = "# Morning Briefing\nTest content"
        mock_engine_class.return_value = mock_engine

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        config = {
            "template": "briefing_morning.md",
            "delivery_channels": ["cli"]
        }

        # Run briefing
        scheduler._run_briefing("morning", config)

        # Verify it was marked as run
        self.assertTrue(scheduler._has_run_today("morning"))

    def test_deliver_file_creates_output(self):
        """Test that file delivery creates output file using FileChannel."""
        # Import FileChannel
        from Tools.delivery_channels import FileChannel

        output_dir = Path(self.temp_dir) / "output"
        config = {
            "output_dir": str(output_dir),
            "filename_pattern": "{date}_{type}_briefing.md"
        }

        content = "# Test Briefing\nContent here"

        # Create FileChannel and deliver
        file_channel = FileChannel(config)
        metadata = {"date": date.today().isoformat()}
        result = file_channel.deliver(content, "morning", metadata)

        # Verify delivery succeeded
        self.assertTrue(result)

        # Check file was created
        expected_file = output_dir / f"{date.today().isoformat()}_morning_briefing.md"
        self.assertTrue(expected_file.exists())

        # Check content (FileChannel adds YAML frontmatter, so check content is included)
        with open(expected_file, 'r') as f:
            file_content = f.read()
            self.assertIn(content, file_content)
            # Verify frontmatter is present
            self.assertIn("---", file_content)
            self.assertIn("type: morning", file_content)

    def test_check_and_run_no_briefings_due(self):
        """Test check_and_run when no briefings are due."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Set times that don't match current time
        config = self.default_config.copy()
        config["briefings"]["morning"]["time"] = "00:00"
        config["briefings"]["evening"]["enabled"] = False
        self._write_config(config)

        # Reload config
        scheduler.config = scheduler._load_config()

        # This should not raise any errors
        scheduler.check_and_run()

        # No briefings should have run
        self.assertFalse(scheduler._has_run_today("morning"))

    def test_graceful_shutdown_signal(self):
        """Test that scheduler sets should_stop on signal."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        self.assertFalse(scheduler.should_stop)

        # Simulate SIGTERM
        scheduler._handle_shutdown(15, None)

        self.assertTrue(scheduler.should_stop)


class TestSchedulerEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_missing_config_file(self):
        """Test initialization with missing config file."""
        with self.assertRaises(FileNotFoundError):
            BriefingScheduler(
                config_path=os.path.join(self.temp_dir, "nonexistent.json")
            )

    def test_invalid_json_config(self):
        """Test initialization with invalid JSON."""
        config_path = Path(self.temp_dir) / "invalid.json"
        config_path.write_text("{ invalid json }")

        with self.assertRaises(Exception):
            BriefingScheduler(config_path=str(config_path))


if __name__ == '__main__':
    unittest.main()
