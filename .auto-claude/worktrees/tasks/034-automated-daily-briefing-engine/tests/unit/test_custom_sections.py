"""
Unit tests for BriefingEngine custom sections functionality.

Tests section configuration, enabling/disabling, reordering, and custom sections.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add Tools to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Tools.briefing_engine import BriefingEngine


class TestCustomSections(unittest.TestCase):
    """Test suite for custom sections functionality."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create temporary directory for State files
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "State"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Create sample State files
        self._create_sample_state_files()

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def _create_sample_state_files(self):
        """Create sample State files for testing."""
        # Create Commitments.md
        commitments_file = self.state_dir / "Commitments.md"
        commitments_file.write_text("""# Commitments

## Active Commitments
- [x] Complete project proposal (Work) - due: 2025-01-15
- [ ] Review team code (Work) - due: 2025-01-12
- [ ] Plan weekend trip (Personal) - due: 2025-01-20

## Completed
- [x] Send report
""")

        # Create ThisWeek.md
        this_week_file = self.state_dir / "ThisWeek.md"
        this_week_file.write_text("""# This Week

## Goals
- Finish documentation
- Review PRs

## Tasks
- [ ] Update tests
- [ ] Fix bug in API
- [x] Deploy to staging
""")

        # Create CurrentFocus.md
        current_focus_file = self.state_dir / "CurrentFocus.md"
        current_focus_file.write_text("""# Current Focus

## Focus Areas
- API refactoring
- Performance optimization

## Priorities
- High priority task
- Medium priority task
""")

    def test_default_sections_enabled(self):
        """Test that all default sections are enabled without config."""
        engine = BriefingEngine(state_dir=str(self.state_dir))
        enabled_sections = engine.get_enabled_sections("morning")

        # Should include all default sections
        self.assertIn("priorities", enabled_sections)
        self.assertIn("commitments", enabled_sections)
        self.assertIn("tasks", enabled_sections)
        self.assertIn("focus", enabled_sections)
        self.assertIn("quick_wins", enabled_sections)

    def test_enable_disable_sections(self):
        """Test enabling/disabling specific sections."""
        config = {
            "content": {
                "sections": {
                    "enabled": ["priorities", "commitments"],
                    "order": ["priorities", "commitments"]
                }
            }
        }
        engine = BriefingEngine(state_dir=str(self.state_dir), config=config)
        enabled_sections = engine.get_enabled_sections("morning")

        # Should only have enabled sections
        self.assertEqual(enabled_sections, ["priorities", "commitments"])
        self.assertNotIn("tasks", enabled_sections)
        self.assertNotIn("focus", enabled_sections)

    def test_section_ordering(self):
        """Test that sections are returned in specified order."""
        config = {
            "content": {
                "sections": {
                    "enabled": ["priorities", "commitments", "tasks", "focus"],
                    "order": ["focus", "tasks", "commitments", "priorities"]
                }
            }
        }
        engine = BriefingEngine(state_dir=str(self.state_dir), config=config)
        enabled_sections = engine.get_enabled_sections("morning")

        # Should be in specified order
        self.assertEqual(enabled_sections, ["focus", "tasks", "commitments", "priorities"])

    def test_section_ordering_with_partial_order(self):
        """Test section ordering when order list doesn't include all enabled sections."""
        config = {
            "content": {
                "sections": {
                    "enabled": ["priorities", "commitments", "tasks", "focus", "quick_wins"],
                    "order": ["priorities", "tasks"]
                }
            }
        }
        engine = BriefingEngine(state_dir=str(self.state_dir), config=config)
        enabled_sections = engine.get_enabled_sections("morning")

        # Should have ordered sections first, then remaining enabled sections
        self.assertEqual(enabled_sections[:2], ["priorities", "tasks"])
        self.assertIn("commitments", enabled_sections)
        self.assertIn("focus", enabled_sections)
        self.assertIn("quick_wins", enabled_sections)

    def test_prepare_sections_data(self):
        """Test preparing section data for all enabled sections."""
        config = {
            "content": {
                "sections": {
                    "enabled": ["priorities", "commitments"],
                    "order": ["priorities", "commitments"]
                }
            }
        }
        engine = BriefingEngine(state_dir=str(self.state_dir), config=config)
        context = engine.gather_context()
        sections_data = engine.prepare_sections_data(context, "morning")

        # Should have data for both sections
        self.assertEqual(len(sections_data), 2)

        # Check priorities section
        priorities_section = sections_data[0]
        self.assertEqual(priorities_section["id"], "priorities")
        self.assertIn("top_priorities", priorities_section["data"])

        # Check commitments section
        commitments_section = sections_data[1]
        self.assertEqual(commitments_section["id"], "commitments")
        self.assertIn("active_commitments", commitments_section["data"])

    def test_get_section_data(self):
        """Test getting data for a specific section."""
        engine = BriefingEngine(state_dir=str(self.state_dir))
        context = engine.gather_context()

        # Get priorities section
        priorities_data = engine.get_section_data("priorities", context, "morning")
        self.assertIsNotNone(priorities_data)
        self.assertEqual(priorities_data["title"], "🎯 Top 3 Priorities")
        self.assertIn("top_priorities", priorities_data["data"])

        # Get commitments section
        commitments_data = engine.get_section_data("commitments", context, "morning")
        self.assertIsNotNone(commitments_data)
        self.assertEqual(commitments_data["title"], "📋 Active Commitments")
        self.assertIn("active_commitments", commitments_data["data"])

    def test_custom_section_provider(self):
        """Test registering a custom section provider."""
        def custom_provider(context, briefing_type, **kwargs):
            return {
                "title": "🔥 Custom Section",
                "data": {
                    "custom_data": "This is custom data"
                }
            }

        engine = BriefingEngine(state_dir=str(self.state_dir))
        engine.register_section_provider("custom", custom_provider)

        context = engine.gather_context()
        section_data = engine.get_section_data("custom", context, "morning")

        self.assertIsNotNone(section_data)
        self.assertEqual(section_data["title"], "🔥 Custom Section")
        self.assertEqual(section_data["data"]["custom_data"], "This is custom data")

    def test_custom_section_with_config(self):
        """Test custom section defined in config."""
        config = {
            "content": {
                "sections": {
                    "enabled": ["priorities", "weather"],
                    "order": ["weather", "priorities"],
                    "custom": [
                        {
                            "id": "weather",
                            "title": "🌤️ Weather",
                            "enabled_by_default": True
                        }
                    ]
                }
            }
        }
        engine = BriefingEngine(state_dir=str(self.state_dir), config=config)
        context = engine.gather_context()

        # Get custom section
        weather_data = engine.get_section_data("weather", context, "morning")
        self.assertIsNotNone(weather_data)
        self.assertEqual(weather_data["title"], "🌤️ Weather")

    def test_custom_section_with_day_conditions(self):
        """Test custom section that only appears on specific days."""
        config = {
            "content": {
                "sections": {
                    "enabled": ["priorities", "weekly_review"],
                    "custom": [
                        {
                            "id": "weekly_review",
                            "title": "📊 Weekly Review",
                            "conditions": {
                                "days": ["sunday", "monday"]
                            }
                        }
                    ]
                }
            }
        }
        engine = BriefingEngine(state_dir=str(self.state_dir), config=config)
        context = engine.gather_context()

        # Get section data
        section_data = engine.get_section_data("weekly_review", context, "morning")

        # Section should only appear if today is Sunday or Monday
        current_day = context["day_of_week"].lower()
        if current_day in ["sunday", "monday"]:
            self.assertIsNotNone(section_data)
        else:
            self.assertIsNone(section_data)

    def test_custom_section_with_briefing_type_conditions(self):
        """Test custom section that only appears for specific briefing types."""
        config = {
            "content": {
                "sections": {
                    "enabled": ["priorities", "evening_recap"],
                    "custom": [
                        {
                            "id": "evening_recap",
                            "title": "🌙 Evening Recap",
                            "conditions": {
                                "briefing_types": ["evening"]
                            }
                        }
                    ]
                }
            }
        }
        engine = BriefingEngine(state_dir=str(self.state_dir), config=config)
        context = engine.gather_context()

        # Should not appear in morning briefing
        morning_data = engine.get_section_data("evening_recap", context, "morning")
        self.assertIsNone(morning_data)

        # Should appear in evening briefing
        evening_data = engine.get_section_data("evening_recap", context, "evening")
        self.assertIsNotNone(evening_data)

    def test_section_data_in_template_data(self):
        """Test that section data is properly included in template data."""
        config = {
            "content": {
                "sections": {
                    "enabled": ["priorities", "commitments"],
                    "order": ["priorities", "commitments"]
                }
            }
        }
        engine = BriefingEngine(state_dir=str(self.state_dir), config=config)
        context = engine.gather_context()
        template_data = engine._prepare_template_data(context, "morning")

        # Should have sections_data
        self.assertIn("sections_data", template_data)
        sections_data = template_data["sections_data"]
        self.assertEqual(len(sections_data), 2)

        # Should also have backward-compatible individual fields
        self.assertIn("top_priorities", template_data)
        self.assertIn("active_commitments", template_data)

    def test_health_section_only_with_health_state(self):
        """Test that health section only appears when health_state is provided."""
        config = {
            "content": {
                "sections": {
                    "enabled": ["priorities", "health"],
                    "order": ["health", "priorities"]
                }
            }
        }
        engine = BriefingEngine(state_dir=str(self.state_dir), config=config)
        context = engine.gather_context()

        # Without health_state, section should return None
        section_without_health = engine.get_section_data("health", context, "morning")
        self.assertIsNone(section_without_health)

        # With health_state, section should return data
        section_with_health = engine.get_section_data(
            "health",
            context,
            "morning",
            health_state={"energy_level": 7}
        )
        self.assertIsNotNone(section_with_health)
        self.assertIn("health_state", section_with_health["data"])

    def test_builtin_section_providers_registered(self):
        """Test that all built-in section providers are registered."""
        engine = BriefingEngine(state_dir=str(self.state_dir))

        expected_sections = [
            "priorities",
            "commitments",
            "tasks",
            "focus",
            "quick_wins",
            "calendar",
            "health"
        ]

        for section_id in expected_sections:
            self.assertIn(section_id, engine._section_providers)
            self.assertTrue(callable(engine._section_providers[section_id]))


if __name__ == '__main__':
    unittest.main()
