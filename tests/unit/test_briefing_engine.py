"""
Unit tests for BriefingEngine core functionality.

Tests data gathering, parsing, and context generation.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import date
import sys
import os

# Add Tools to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Tools.briefing_engine import BriefingEngine


class TestBriefingEngine(unittest.TestCase):
    """Test suite for BriefingEngine class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create temporary directory for State files
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "State"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Initialize engine with test state directory
        self.engine = BriefingEngine(state_dir=str(self.state_dir))

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test BriefingEngine initialization."""
        self.assertEqual(str(self.engine.state_dir), str(self.state_dir))
        self.assertIsInstance(self.engine.today, date)

    def test_gather_context_with_missing_files(self):
        """Test context gathering when State files are missing."""
        context = self.engine.gather_context()

        # Should return valid structure even with missing files
        self.assertIn("commitments", context)
        self.assertIn("this_week", context)
        self.assertIn("current_focus", context)
        self.assertIn("today_date", context)
        self.assertIn("day_of_week", context)
        self.assertIn("is_weekend", context)
        self.assertIn("metadata", context)

        # Lists should be empty when files missing
        self.assertEqual(context["commitments"], [])
        self.assertIsInstance(context["this_week"], dict)
        self.assertIsInstance(context["current_focus"], dict)

    def test_gather_context_basic_structure(self):
        """Test that gather_context returns properly structured data."""
        # Create minimal State files
        (self.state_dir / "Commitments.md").write_text("# Commitments\n")
        (self.state_dir / "ThisWeek.md").write_text("# This Week\n")
        (self.state_dir / "CurrentFocus.md").write_text("# Current Focus\n")

        context = self.engine.gather_context()

        # Verify structure
        self.assertIsInstance(context, dict)
        self.assertIsInstance(context["commitments"], list)
        self.assertIsInstance(context["this_week"], dict)
        self.assertIsInstance(context["current_focus"], dict)
        self.assertIsInstance(context["metadata"], dict)

        # Verify date fields
        self.assertEqual(context["today_date"], self.engine.today.isoformat())
        self.assertIn(context["day_of_week"],
                      ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        self.assertIsInstance(context["is_weekend"], bool)

    def test_parse_commitments_basic(self):
        """Test parsing basic commitments."""
        content = """# Commitments

## Work
- [ ] Complete project proposal
- [x] Send weekly update
- [ ] Review PR #123

## Personal
- [ ] Schedule dentist appointment
- [x] Pay rent
"""
        (self.state_dir / "Commitments.md").write_text(content)

        context = self.engine.gather_context()
        commitments = context["commitments"]

        # Should have 5 commitments
        self.assertEqual(len(commitments), 5)

        # Check first commitment
        self.assertEqual(commitments[0]["title"], "Complete project proposal")
        self.assertEqual(commitments[0]["category"], "Work")
        self.assertFalse(commitments[0]["is_complete"])

        # Check completed commitment
        completed = [c for c in commitments if c["title"] == "Send weekly update"]
        self.assertEqual(len(completed), 1)
        self.assertTrue(completed[0]["is_complete"])

    def test_parse_commitments_with_deadlines(self):
        """Test parsing commitments with deadline metadata."""
        content = """# Commitments

## Work
- [ ] Submit report (due: 2024-01-15)
- [ ] Team meeting (due: 2024-01-12)
- [ ] Normal task without deadline
"""
        (self.state_dir / "Commitments.md").write_text(content)

        context = self.engine.gather_context()
        commitments = context["commitments"]

        # Find commitment with deadline
        report = [c for c in commitments if "Submit report" in c["title"]]
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]["deadline"], "2024-01-15")
        self.assertEqual(report[0]["title"], "Submit report")

        # Task without deadline
        normal = [c for c in commitments if "Normal task" in c["title"]]
        self.assertEqual(len(normal), 1)
        self.assertIsNone(normal[0]["deadline"])

    def test_parse_this_week_goals_and_tasks(self):
        """Test parsing ThisWeek.md with goals and tasks."""
        content = """# This Week

## Goals
- [ ] Launch new feature
- [x] Complete code review
- [ ] Write documentation

## Tasks
- [ ] Fix bug #456
- [ ] Update dependencies
- [x] Deploy to staging

## Notes
This is an important week for the product launch.
Need to coordinate with the design team.
"""
        (self.state_dir / "ThisWeek.md").write_text(content)

        context = self.engine.gather_context()
        this_week = context["this_week"]

        # Check goals
        self.assertEqual(len(this_week["goals"]), 3)
        self.assertEqual(this_week["goals"][0]["text"], "Launch new feature")
        self.assertFalse(this_week["goals"][0]["is_complete"])
        self.assertTrue(this_week["goals"][1]["is_complete"])

        # Check tasks
        self.assertEqual(len(this_week["tasks"]), 3)
        self.assertEqual(this_week["tasks"][0]["text"], "Fix bug #456")

        # Check notes
        self.assertIn("important week", this_week["notes"])
        self.assertIn("design team", this_week["notes"])

    def test_parse_this_week_plain_lists(self):
        """Test parsing ThisWeek.md with plain list items (no checkboxes)."""
        content = """# This Week

## Goals
- Launch new feature
- Complete code review

## Tasks
* Fix bug #456
* Update dependencies
"""
        (self.state_dir / "ThisWeek.md").write_text(content)

        context = self.engine.gather_context()
        this_week = context["this_week"]

        # Plain list items should be parsed as incomplete
        self.assertEqual(len(this_week["goals"]), 2)
        self.assertFalse(this_week["goals"][0]["is_complete"])

        self.assertEqual(len(this_week["tasks"]), 2)
        self.assertFalse(this_week["tasks"][0]["is_complete"])

    def test_parse_current_focus(self):
        """Test parsing CurrentFocus.md."""
        content = """# Current Focus

## Focus Areas
- Product launch preparation
- Bug fixes for Q1 release
- Team onboarding

## Priorities
- Fix critical security bug
- Complete customer demo
- Review architecture proposal
"""
        (self.state_dir / "CurrentFocus.md").write_text(content)

        context = self.engine.gather_context()
        current_focus = context["current_focus"]

        # Check focus areas
        self.assertEqual(len(current_focus["focus_areas"]), 3)
        self.assertIn("Product launch preparation", current_focus["focus_areas"])

        # Check priorities
        self.assertEqual(len(current_focus["priorities"]), 3)
        self.assertIn("Fix critical security bug", current_focus["priorities"])

        # Content should be preserved
        self.assertIn("Current Focus", current_focus["content"])

    def test_get_active_commitments(self):
        """Test filtering for active (incomplete) commitments."""
        content = """# Commitments

## Work
- [ ] Active task 1
- [x] Completed task
- [ ] Active task 2
"""
        (self.state_dir / "Commitments.md").write_text(content)

        context = self.engine.gather_context()
        active = self.engine.get_active_commitments(context)

        # Should only return incomplete commitments
        self.assertEqual(len(active), 2)
        for commitment in active:
            self.assertFalse(commitment["is_complete"])

    def test_get_active_commitments_without_context(self):
        """Test get_active_commitments gathers context if not provided."""
        content = """# Commitments

## Work
- [ ] Active task
- [x] Completed task
"""
        (self.state_dir / "Commitments.md").write_text(content)

        active = self.engine.get_active_commitments()

        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["title"], "Active task")

    def test_get_pending_tasks(self):
        """Test filtering for pending tasks from this week."""
        content = """# This Week

## Tasks
- [ ] Pending task 1
- [x] Done task
- [ ] Pending task 2
"""
        (self.state_dir / "ThisWeek.md").write_text(content)

        context = self.engine.gather_context()
        pending = self.engine.get_pending_tasks(context)

        # Should only return incomplete tasks
        self.assertEqual(len(pending), 2)
        for task in pending:
            self.assertFalse(task["is_complete"])

    def test_get_pending_tasks_without_context(self):
        """Test get_pending_tasks gathers context if not provided."""
        content = """# This Week

## Tasks
- [ ] Pending task
- [x] Done task
"""
        (self.state_dir / "ThisWeek.md").write_text(content)

        pending = self.engine.get_pending_tasks()

        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["text"], "Pending task")

    def test_weekend_detection(self):
        """Test is_weekend flag is correctly set."""
        context = self.engine.gather_context()

        # is_weekend should be a boolean
        self.assertIsInstance(context["is_weekend"], bool)

        # Verify it matches actual day
        today_weekday = self.engine.today.weekday()
        expected_weekend = today_weekday >= 5
        self.assertEqual(context["is_weekend"], expected_weekend)

    def test_empty_files(self):
        """Test handling of empty State files."""
        # Create empty files
        (self.state_dir / "Commitments.md").write_text("")
        (self.state_dir / "ThisWeek.md").write_text("")
        (self.state_dir / "CurrentFocus.md").write_text("")

        context = self.engine.gather_context()

        # Should handle empty files gracefully
        self.assertEqual(context["commitments"], [])
        self.assertEqual(context["this_week"]["goals"], [])
        self.assertEqual(context["this_week"]["tasks"], [])
        self.assertEqual(context["current_focus"]["focus_areas"], [])

    def test_malformed_markdown(self):
        """Test handling of malformed markdown content."""
        content = """This is not valid markdown
No headers
- Random list item
[x] Invalid checkbox
"""
        (self.state_dir / "Commitments.md").write_text(content)

        # Should not crash
        context = self.engine.gather_context()

        # May have parsed some items, but shouldn't crash
        self.assertIsInstance(context["commitments"], list)

    def test_unicode_content(self):
        """Test handling of unicode characters in content."""
        content = """# Commitments

## Work
- [ ] Review résumé for José
- [ ] Prepare presentation with 日本語 slides
- [x] Send email to François
"""
        (self.state_dir / "Commitments.md").write_text(content, encoding='utf-8')

        context = self.engine.gather_context()
        commitments = context["commitments"]

        # Should handle unicode properly
        self.assertTrue(any("José" in c["title"] for c in commitments))
        self.assertTrue(any("日本語" in c["title"] for c in commitments))
        self.assertTrue(any("François" in c["title"] for c in commitments))


class TestBriefingEngineEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "State"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.engine = BriefingEngine(state_dir=str(self.state_dir))

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def test_nonexistent_state_directory(self):
        """Test behavior when State directory doesn't exist."""
        nonexistent = Path(self.temp_dir) / "NonexistentState"
        engine = BriefingEngine(state_dir=str(nonexistent))

        # Should not crash, should return empty data
        context = engine.gather_context()

        self.assertEqual(context["commitments"], [])
        self.assertIsInstance(context["this_week"], dict)
        self.assertIsInstance(context["current_focus"], dict)

    def test_default_state_directory(self):
        """Test using default State directory (./State)."""
        engine = BriefingEngine()

        # Should use ./State relative to cwd
        expected_path = Path(os.getcwd()) / "State"
        self.assertEqual(str(engine.state_dir), str(expected_path))

    def test_nested_sections_in_commitments(self):
        """Test handling of nested sections in Commitments.md."""
        content = """# Commitments

## Work

### Project A
- [ ] Task A1
- [ ] Task A2

### Project B
- [ ] Task B1

## Personal
- [ ] Personal task
"""
        (self.state_dir / "Commitments.md").write_text(content)

        context = self.engine.gather_context()
        commitments = context["commitments"]

        # Should parse all tasks regardless of nesting
        self.assertGreater(len(commitments), 0)


if __name__ == '__main__':
    unittest.main()
