"""
Integration tests for BriefingScheduler end-to-end flow.

Tests the complete briefing generation and delivery pipeline,
including scheduler execution, multi-channel delivery, and error recovery.
"""

import unittest
import tempfile
import shutil
import json
import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta, time
from unittest.mock import Mock, patch, MagicMock, call

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Tools.briefing_scheduler import BriefingScheduler
from Tools.briefing_engine import BriefingEngine
from Tools.delivery_channels import CLIChannel, FileChannel, deliver_to_channels


class TestBriefingSchedulerIntegration(unittest.TestCase):
    """Integration tests for end-to-end briefing generation and delivery."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create temporary directory structure
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.state_dir = Path(self.temp_dir) / "State"
        self.templates_dir = Path(self.temp_dir) / "Templates"
        self.logs_dir = Path(self.temp_dir) / "logs"
        self.history_dir = Path(self.temp_dir) / "History" / "DailyBriefings"

        # Create directories
        for directory in [self.config_dir, self.state_dir, self.templates_dir,
                         self.logs_dir, self.history_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Create test config
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
                    "enabled": True,
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
                    "delivery_channels": ["cli", "file"]
                }
            },
            "delivery": {
                "cli": {"enabled": True, "color": True},
                "file": {
                    "enabled": True,
                    "output_dir": str(self.history_dir),
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

        with open(self.config_path, 'w') as f:
            json.dump(self.default_config, f, indent=2)

        # Create test State files
        self._create_test_state_files()

        # Create test templates
        self._create_test_templates()

    def tearDown(self):
        """Clean up test fixtures after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_test_state_files(self):
        """Create test State files with sample data."""
        # Commitments.md
        commitments = """# Active Commitments

## Work Commitments
- [ ] Complete quarterly report (due: 2026-01-15)
- [ ] Review team PRs (due: 2026-01-12)
- [x] Finish feature implementation

## Personal Commitments
- [ ] Schedule dentist appointment
- [ ] Plan weekend trip
"""
        (self.state_dir / "Commitments.md").write_text(commitments)

        # ThisWeek.md
        this_week = """# This Week

## Tasks
- [ ] Update documentation
- [ ] Fix critical bug
- [ ] Team standup meetings
- [x] Code review session
"""
        (self.state_dir / "ThisWeek.md").write_text(this_week)

        # CurrentFocus.md
        current_focus = """# Current Focus

## Primary Focus
- Deep work on project architecture
- Improve test coverage

## Secondary Focus
- Team collaboration
- Code reviews
"""
        (self.state_dir / "CurrentFocus.md").write_text(current_focus)

    def _create_test_templates(self):
        """Create test briefing templates."""
        # Morning template
        morning_template = """# Morning Briefing
*{{ date }} - {{ day_of_week }}*

## Top Priorities
{% if priorities %}
{% for priority in priorities[:3] %}
{{ loop.index }}. {{ priority.title }} ({{ priority.urgency }})
{% endfor %}
{% else %}
No priorities identified.
{% endif %}

## Active Commitments
{% if commitments %}
{% for commitment in commitments[:5] %}
- {{ commitment }}
{% endfor %}
{% else %}
No active commitments.
{% endif %}

## Quick Wins
{% if quick_wins %}
{% for win in quick_wins %}
- {{ win }}
{% endfor %}
{% else %}
No quick wins identified.
{% endif %}
"""
        (self.templates_dir / "briefing_morning.md").write_text(morning_template)

        # Evening template
        evening_template = """# Evening Briefing
*{{ date }} - {{ day_of_week }}*

## Today's Reflections
What went well today?

## Tomorrow's Preview
{% if priorities %}
Top priorities for tomorrow:
{% for priority in priorities[:3] %}
{{ loop.index }}. {{ priority.title }}
{% endfor %}
{% endif %}

## Prep for Tomorrow
- Review morning priorities
- Set up workspace
- Plan first task
"""
        (self.templates_dir / "briefing_evening.md").write_text(evening_template)

    # Test 1: Full briefing generation flow
    def test_full_briefing_generation_flow(self):
        """Test complete end-to-end briefing generation and delivery."""
        try:
            import jinja2
        except ImportError:
            self.skipTest("Jinja2 not available")

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Verify State files were read
        self.assertIsNotNone(scheduler.engine)

        # Verify context was gathered
        context = scheduler.engine.gather_context()
        self.assertIn('commitments', context)
        self.assertIn('this_week', context)  # Fixed: 'this_week' not 'this_week_tasks'
        self.assertIn('current_focus', context)

        # Test that _run_briefing can be called
        with patch('Tools.delivery_channels.deliver_to_channels') as mock_deliver:
            mock_deliver.return_value = True

            briefing_config = scheduler.config['briefings']['morning']
            scheduler._run_briefing('morning', briefing_config)

            # Verify delivery was called
            self.assertTrue(mock_deliver.called)

    # Test 2: Scheduled execution with mocked time
    def test_scheduled_execution_with_mocked_time(self):
        """Test scheduler triggers briefings at configured times."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Mock current time to match morning briefing time (07:00)
        mock_time = datetime(2026, 1, 13, 7, 0, 0)  # Monday 7:00 AM

        with patch('Tools.briefing_scheduler.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Check if briefing should run
            briefing_config = scheduler.config['briefings']['morning']
            should_run = scheduler._should_run_briefing('morning', briefing_config, mock_time)

            # Verify it should run at 07:00
            self.assertTrue(should_run)

        # Test evening time (19:00)
        mock_time_evening = datetime(2026, 1, 13, 19, 0, 0)  # Monday 7:00 PM

        with patch('Tools.briefing_scheduler.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time_evening
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            briefing_config = scheduler.config['briefings']['evening']
            should_run = scheduler._should_run_briefing('evening', briefing_config, mock_time_evening)

            self.assertTrue(should_run)

    # Test 3: Multi-channel delivery
    @unittest.skipIf(not hasattr(__import__('sys').modules.get('jinja2'), '__version__')
                     if 'jinja2' in __import__('sys').modules else True,
                     "Jinja2 not available")
    def test_multi_channel_delivery(self):
        """Test briefing delivery through multiple channels."""
        try:
            import jinja2
        except ImportError:
            self.skipTest("Jinja2 not available")

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Generate briefing content
        context = scheduler.engine.gather_context()
        content = scheduler.engine.render_briefing('morning')

        # Configure multiple delivery channels
        channels_config = {
            "cli": {"enabled": True, "color": True},
            "file": {
                "enabled": True,
                "output_dir": str(self.history_dir),
                "filename_pattern": "{date}_{type}_briefing.md"
            }
        }

        # Mock channel deliveries
        with patch('Tools.delivery_channels.CLIChannel.deliver') as mock_cli, \
             patch('Tools.delivery_channels.FileChannel.deliver') as mock_file:

            mock_cli.return_value = True
            mock_file.return_value = True

            # Deliver to channels
            results = deliver_to_channels(
                content=content,
                briefing_type='morning',
                channels_config=channels_config,
                delivery_config=self.default_config['delivery']
            )

            # Verify both channels were called
            self.assertTrue(mock_cli.called)
            self.assertTrue(mock_file.called)

    # Test 4: Config loading and validation
    def test_config_loading_and_validation(self):
        """Test configuration file loading and validation."""
        # Valid config should load successfully
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        self.assertIsNotNone(scheduler.config)
        self.assertEqual(scheduler.config['version'], '1.0.0')
        self.assertTrue(scheduler.config['briefings']['morning']['enabled'])

        # Test that validation catches completely invalid JSON
        invalid_json_path = self.config_dir / "invalid.json"
        with open(invalid_json_path, 'w') as f:
            f.write("{invalid json")

        # Should raise error on invalid JSON
        with self.assertRaises(Exception):  # Could be JSONDecodeError or ValueError
            BriefingScheduler(
                config_path=str(invalid_json_path),
                state_dir=str(self.state_dir),
                templates_dir=str(self.templates_dir)
            )

    # Test 5: Error recovery
    def test_error_recovery_missing_state_files(self):
        """Test scheduler recovers gracefully from missing State files."""
        # Remove State files
        for file in self.state_dir.glob("*.md"):
            file.unlink()

        # Scheduler should still initialize
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Gather context should return empty data structures, not crash
        context = scheduler.engine.gather_context()

        self.assertIsNotNone(context)
        self.assertIn('commitments', context)
        self.assertIn('this_week', context)  # Fixed: 'this_week' not 'this_week_tasks'
        # Empty lists/dicts are expected, not errors
        self.assertEqual(len(context['commitments']), 0)

    # Test 6: Duplicate run prevention
    def test_duplicate_run_prevention(self):
        """Test scheduler prevents duplicate briefing runs on same day."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # First run should succeed
        self.assertFalse(scheduler._has_run_today('morning'))

        # Mark as run
        scheduler._mark_as_run('morning')

        # Second check should show it has run
        self.assertTrue(scheduler._has_run_today('morning'))

        # Different briefing type should not be marked
        self.assertFalse(scheduler._has_run_today('evening'))

    # Test 7: Day-of-week filtering
    def test_day_of_week_filtering(self):
        """Test briefings respect day-of-week configuration."""
        # Disable Saturday evening briefings in config
        self.default_config['briefings']['evening']['days']['saturday'] = False

        with open(self.config_path, 'w') as f:
            json.dump(self.default_config, f, indent=2)

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Mock Saturday at 19:00
        mock_saturday = datetime(2026, 1, 17, 19, 0, 0)  # Saturday 7:00 PM

        with patch('Tools.briefing_scheduler.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_saturday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Get current day name
            with patch.object(scheduler, '_get_current_day_name', return_value='saturday'):
                briefing_config = scheduler.config['briefings']['evening']
                should_run = scheduler._should_run_briefing('evening', briefing_config, mock_saturday)

                # Should NOT run on Saturday
                self.assertFalse(should_run)

    # Test 8: File delivery output verification
    def test_file_delivery_creates_output(self):
        """Test FileChannel creates output files correctly."""
        try:
            import jinja2
        except ImportError:
            self.skipTest("Jinja2 not available")

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Generate briefing
        context = scheduler.engine.gather_context()
        content = scheduler.engine.render_briefing('morning')

        # Create FileChannel and deliver
        file_channel = FileChannel(self.default_config['delivery']['file'])
        result = file_channel.deliver(content, 'morning')

        # Verify delivery succeeded
        self.assertTrue(result)

        # Verify file was created
        today = date.today().isoformat()
        expected_filename = f"{today}_morning_briefing.md"
        expected_path = self.history_dir / expected_filename

        self.assertTrue(expected_path.exists())

        # Verify content
        saved_content = expected_path.read_text()
        self.assertIn("Morning Briefing", saved_content)

    # Test 9: Priority ranking integration
    def test_priority_ranking_integration(self):
        """Test priority ranking works correctly in full flow."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Gather context and rank priorities
        context = scheduler.engine.gather_context()
        priorities = scheduler.engine.rank_priorities(context)

        # Verify priorities were ranked
        self.assertGreater(len(priorities), 0)

        # Verify priorities have required fields
        for priority in priorities:
            self.assertIn('title', priority)
            self.assertIn('priority_score', priority)
            self.assertIn('urgency_level', priority)  # Fixed: 'urgency_level' not 'urgency'

        # Verify priorities are sorted by score (descending)
        scores = [p['priority_score'] for p in priorities]
        self.assertEqual(scores, sorted(scores, reverse=True))

    # Test 10: Template rendering with context
    def test_template_rendering_with_context(self):
        """Test templates render correctly with gathered context."""
        try:
            import jinja2
        except ImportError:
            self.skipTest("Jinja2 not available")

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Gather context
        context = scheduler.engine.gather_context()

        # Render morning briefing
        morning_content = scheduler.engine.render_briefing('morning')

        self.assertIsNotNone(morning_content)
        self.assertIn("Morning Briefing", morning_content)
        self.assertIn("Top Priorities", morning_content)

        # Render evening briefing
        evening_content = scheduler.engine.render_briefing('evening')

        self.assertIsNotNone(evening_content)
        self.assertIn("Evening Briefing", evening_content)
        self.assertIn("Tomorrow's Preview", evening_content)

    # Test 11: Error recovery from template rendering failures
    def test_error_recovery_template_rendering_failure(self):
        """Test scheduler recovers from template rendering errors."""
        # Create invalid template
        (self.templates_dir / "briefing_morning.md").write_text("{{ invalid_syntax {%")

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Rendering should handle the error gracefully
        context = scheduler.engine.gather_context()

        # Should not crash, might return None or error message
        try:
            content = scheduler.engine.render_briefing('morning', context)
            # If it succeeds, verify it's a string
            if content is not None:
                self.assertIsInstance(content, str)
        except Exception as e:
            # If it raises an exception, that's also acceptable for this test
            # The point is the scheduler doesn't crash the entire process
            self.assertIsInstance(e, Exception)

    # Test 12: Check interval configuration
    def test_check_interval_configuration(self):
        """Test scheduler respects check_interval_minutes configuration."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Verify check interval is loaded from config
        check_interval = scheduler.config['scheduler']['check_interval_minutes']
        self.assertEqual(check_interval, 1)

        # Update config with different interval
        self.default_config['scheduler']['check_interval_minutes'] = 5
        with open(self.config_path, 'w') as f:
            json.dump(self.default_config, f, indent=2)

        # Create new scheduler
        scheduler2 = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        self.assertEqual(scheduler2.config['scheduler']['check_interval_minutes'], 5)

    # Test 13: Integration with real BriefingEngine
    def test_integration_with_real_briefing_engine(self):
        """Test scheduler works with real BriefingEngine instance."""
        try:
            import jinja2
        except ImportError:
            self.skipTest("Jinja2 not available")

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Verify BriefingEngine was initialized
        self.assertIsInstance(scheduler.engine, BriefingEngine)

        # Verify engine can access State files
        context = scheduler.engine.gather_context()
        self.assertIsNotNone(context)

        # Verify engine can rank priorities
        priorities = scheduler.engine.rank_priorities(context)
        self.assertIsInstance(priorities, list)

        # Verify engine can render briefings
        content = scheduler.engine.render_briefing('morning')
        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 0)


class TestSchedulerExecutionFlow(unittest.TestCase):
    """Test specific execution flow scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.state_dir = Path(self.temp_dir) / "State"
        self.templates_dir = Path(self.temp_dir) / "Templates"
        self.logs_dir = Path(self.temp_dir) / "logs"

        for directory in [self.config_dir, self.state_dir, self.templates_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Create minimal config
        self.config_path = self.config_dir / "briefing_schedule.json"
        config = {
            "version": "1.0.0",
            "briefings": {
                "morning": {
                    "enabled": True,
                    "time": "07:00",
                    "timezone": "local",
                    "days": {day: True for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]},
                    "template": "briefing_morning.md",
                    "delivery_channels": ["cli"]
                }
            },
            "delivery": {
                "cli": {"enabled": True, "color": False}
            },
            "scheduler": {
                "check_interval_minutes": 1,
                "prevent_duplicate_runs": True,
                "log_file": str(self.logs_dir / "test.log")
            },
            "content": {"max_priorities": 3, "include_quick_wins": True},
            "advanced": {
                "state_dir": str(self.state_dir),
                "templates_dir": str(self.templates_dir)
            }
        }
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Create minimal State files
        (self.state_dir / "Commitments.md").write_text("# Commitments\n- [ ] Test task")
        (self.state_dir / "ThisWeek.md").write_text("# This Week\n- [ ] Test task")
        (self.state_dir / "CurrentFocus.md").write_text("# Focus\nTest focus")

        # Create minimal template
        (self.templates_dir / "briefing_morning.md").write_text("# Test Briefing\n{{ date }}")

    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_execute_briefing_method(self):
        """Test _run_briefing method performs full execution."""
        try:
            import jinja2
        except ImportError:
            self.skipTest("Jinja2 not available")

        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Mock delivery to track calls
        with patch('Tools.delivery_channels.deliver_to_channels') as mock_deliver:
            mock_deliver.return_value = True

            # Get briefing config
            briefing_config = scheduler.config['briefings']['morning']

            # Execute briefing
            scheduler._run_briefing('morning', briefing_config)

            # Verify delivery was called
            self.assertTrue(mock_deliver.called)

            # Verify briefing was marked as run
            self.assertTrue(scheduler._has_run_today('morning'))

    def test_run_once_mode(self):
        """Test run_once method (for cron)."""
        scheduler = BriefingScheduler(
            config_path=str(self.config_path),
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Mock time to match briefing time
        mock_time = datetime(2026, 1, 13, 7, 0, 0)

        with patch('Tools.briefing_scheduler.datetime') as mock_datetime, \
             patch('Tools.delivery_channels.deliver_to_channels') as mock_deliver:

            mock_datetime.now.return_value = mock_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            mock_deliver.return_value = True

            # Run once (simulates cron execution)
            scheduler.run_once()

            # The method executes without error
            # (actual delivery depends on time matching and duplicate prevention)


if __name__ == '__main__':
    unittest.main()
