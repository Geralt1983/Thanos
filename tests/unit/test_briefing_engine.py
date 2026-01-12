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

from Tools.briefing_engine import BriefingEngine, JINJA2_AVAILABLE


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
        self.assertIn("calendar", context)
        self.assertIn("today_date", context)
        self.assertIn("day_of_week", context)
        self.assertIn("is_weekend", context)
        self.assertIn("metadata", context)

        # Lists should be empty when files missing
        self.assertEqual(context["commitments"], [])
        self.assertIsInstance(context["this_week"], dict)
        self.assertIsInstance(context["current_focus"], dict)
        self.assertIsInstance(context["calendar"], dict)
        self.assertEqual(context["calendar"]["events"], [])

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
        self.assertIsInstance(context["calendar"], dict)
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

    def test_read_calendar_with_events(self):
        """Test reading calendar_today.json with events."""
        import json

        calendar_data = {
            "synced_at": "2026-01-11T22:52:53.560647-05:00",
            "date": "2026-01-11",
            "timezone": "America/New_York",
            "events": [
                {
                    "id": "event1",
                    "summary": "Morning Standup",
                    "start": {"dateTime": "2024-01-15T09:00:00-05:00"},
                    "end": {"dateTime": "2024-01-15T09:30:00-05:00"}
                },
                {
                    "id": "event2",
                    "summary": "Project Review",
                    "start": {"dateTime": "2024-01-15T14:00:00-05:00"},
                    "end": {"dateTime": "2024-01-15T15:00:00-05:00"}
                }
            ],
            "summary": {
                "total_events": 2,
                "total_duration_minutes": 90
            }
        }

        calendar_file = self.state_dir / "calendar_today.json"
        with open(calendar_file, 'w') as f:
            json.dump(calendar_data, f)

        context = self.engine.gather_context()
        calendar = context["calendar"]

        # Verify structure
        self.assertIn("events", calendar)
        self.assertIn("synced_at", calendar)
        self.assertIn("date", calendar)
        self.assertIn("timezone", calendar)
        self.assertIn("summary", calendar)

        # Verify data
        self.assertEqual(len(calendar["events"]), 2)
        self.assertEqual(calendar["events"][0]["summary"], "Morning Standup")
        self.assertEqual(calendar["timezone"], "America/New_York")
        self.assertEqual(calendar["summary"]["total_events"], 2)

    def test_read_calendar_missing_file(self):
        """Test reading calendar when file doesn't exist."""
        context = self.engine.gather_context()
        calendar = context["calendar"]

        # Should return default structure
        self.assertEqual(calendar["events"], [])
        self.assertIsNone(calendar["synced_at"])
        self.assertEqual(calendar["date"], self.engine.today.isoformat())
        self.assertIsNone(calendar["timezone"])
        self.assertEqual(calendar["summary"]["total_events"], 0)

    def test_read_calendar_invalid_json(self):
        """Test reading calendar with invalid JSON."""
        calendar_file = self.state_dir / "calendar_today.json"
        calendar_file.write_text("{ invalid json }")

        context = self.engine.gather_context()
        calendar = context["calendar"]

        # Should return default structure on error
        self.assertEqual(calendar["events"], [])
        self.assertEqual(calendar["summary"]["total_events"], 0)

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


class TestPriorityRanking(unittest.TestCase):
    """Test suite for priority ranking functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "State"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.engine = BriefingEngine(state_dir=str(self.state_dir))

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def test_rank_priorities_by_deadline_urgency(self):
        """Test that items are ranked by deadline urgency."""
        from datetime import timedelta

        today = self.engine.today
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        overdue = today - timedelta(days=1)

        commitments_content = f"""# Commitments

## Work
- [ ] Overdue task (due: {overdue.isoformat()})
- [ ] Due today task (due: {today.isoformat()})
- [ ] Due tomorrow task (due: {tomorrow.isoformat()})
- [ ] Due next week task (due: {next_week.isoformat()})
- [ ] No deadline task
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        ranked = self.engine.rank_priorities()

        # Verify ordering: overdue > today > tomorrow > next week > no deadline
        self.assertGreater(len(ranked), 0)

        # Find each task
        overdue_item = next(i for i in ranked if "Overdue" in i["title"])
        today_item = next(i for i in ranked if "Due today" in i["title"])
        tomorrow_item = next(i for i in ranked if "Due tomorrow" in i["title"])
        next_week_item = next(i for i in ranked if "Due next week" in i["title"])
        no_deadline_item = next(i for i in ranked if "No deadline" in i["title"])

        # Check urgency levels
        self.assertEqual(overdue_item["urgency_level"], "critical")
        self.assertEqual(today_item["urgency_level"], "critical")
        self.assertEqual(tomorrow_item["urgency_level"], "high")

        # Check priority scores are in correct order
        self.assertGreater(overdue_item["priority_score"], today_item["priority_score"])
        self.assertGreater(today_item["priority_score"], tomorrow_item["priority_score"])
        self.assertGreater(tomorrow_item["priority_score"], next_week_item["priority_score"])
        self.assertGreater(next_week_item["priority_score"], no_deadline_item["priority_score"])

    def test_weekend_deprioritizes_work_tasks(self):
        """Test that work tasks are deprioritized on weekends unless urgent."""
        from datetime import timedelta

        # Mock weekend day
        original_today = self.engine.today
        # Find next Saturday (weekday 5)
        days_until_saturday = (5 - original_today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        saturday = original_today + timedelta(days=days_until_saturday)
        self.engine.today = saturday

        commitments_content = """# Commitments

## Work
- [ ] Regular work task

## Personal
- [ ] Personal task
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        context = self.engine.gather_context()
        self.assertTrue(context["is_weekend"])

        ranked = self.engine.rank_priorities(context)

        # Find tasks
        work_item = next(i for i in ranked if "work task" in i["title"])
        personal_item = next(i for i in ranked if "Personal task" in i["title"])

        # Personal task should be higher priority on weekend
        self.assertGreater(personal_item["priority_score"], work_item["priority_score"])
        self.assertIn("weekend", work_item["priority_reason"].lower())

        # Restore original date
        self.engine.today = original_today

    def test_weekend_prioritizes_urgent_work_tasks(self):
        """Test that urgent work tasks stay high priority even on weekends."""
        from datetime import timedelta

        # Mock weekend day
        original_today = self.engine.today
        days_until_saturday = (5 - original_today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        saturday = original_today + timedelta(days=days_until_saturday)
        self.engine.today = saturday

        commitments_content = f"""# Commitments

## Work
- [ ] Urgent work task (due: {saturday.isoformat()})

## Personal
- [ ] Regular personal task
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        context = self.engine.gather_context()
        ranked = self.engine.rank_priorities(context)

        # Find tasks
        urgent_work = next(i for i in ranked if "Urgent work" in i["title"])
        personal = next(i for i in ranked if "Regular personal" in i["title"])

        # Urgent work should still be higher priority
        self.assertGreater(urgent_work["priority_score"], personal["priority_score"])
        self.assertEqual(urgent_work["urgency_level"], "critical")

        # Restore
        self.engine.today = original_today

    def test_weekday_prioritizes_work_tasks(self):
        """Test that work tasks get higher priority on weekdays."""
        from datetime import timedelta

        # Ensure we're on a weekday
        original_today = self.engine.today
        if original_today.weekday() >= 5:  # Weekend
            # Move to next Monday
            days_until_monday = (7 - original_today.weekday()) % 7
            monday = original_today + timedelta(days=days_until_monday)
            self.engine.today = monday

        commitments_content = """# Commitments

## Work
- [ ] Work task

## Personal
- [ ] Personal task
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        context = self.engine.gather_context()
        self.assertFalse(context["is_weekend"])

        ranked = self.engine.rank_priorities(context)

        # Find tasks
        work_item = next(i for i in ranked if "Work task" in i["title"])
        personal_item = next(i for i in ranked if "Personal task" in i["title"])

        # Work task should be higher priority on weekday
        self.assertGreater(work_item["priority_score"], personal_item["priority_score"])
        self.assertIn("weekday", work_item["priority_reason"].lower())

        # Restore
        self.engine.today = original_today

    def test_energy_level_affects_complex_tasks(self):
        """Test that energy level affects task recommendations."""
        commitments_content = """# Commitments

## Work
- [ ] Design new architecture for API
- [ ] Send status update email
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        # High energy - complex task should get boost
        ranked_high_energy = self.engine.rank_priorities(energy_level=8)
        design_task_high = next(i for i in ranked_high_energy if "Design" in i["title"])
        self.assertIn("good energy", design_task_high["priority_reason"].lower())

        # Low energy - simple task should get boost
        ranked_low_energy = self.engine.rank_priorities(energy_level=3)
        email_task_low = next(i for i in ranked_low_energy if "email" in i["title"])
        design_task_low = next(i for i in ranked_low_energy if "Design" in i["title"])

        self.assertIn("manageable", email_task_low["priority_reason"].lower())
        self.assertIn("higher energy", design_task_low["priority_reason"].lower())

        # Complex task should be deprioritized with low energy
        self.assertLess(design_task_low["priority_score"], design_task_high["priority_score"])

    def test_get_top_priorities(self):
        """Test getting top N priorities."""
        commitments_content = """# Commitments

## Work
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
- [ ] Task 4
- [ ] Task 5
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        top_3 = self.engine.get_top_priorities(limit=3)

        self.assertEqual(len(top_3), 3)
        # Verify they're sorted by priority
        self.assertGreaterEqual(top_3[0]["priority_score"], top_3[1]["priority_score"])
        self.assertGreaterEqual(top_3[1]["priority_score"], top_3[2]["priority_score"])

    def test_rank_priorities_includes_all_sources(self):
        """Test that ranking includes commitments, tasks, and current focus."""
        commitments_content = """# Commitments

## Work
- [ ] Work commitment
"""
        this_week_content = """# This Week

## Tasks
- [ ] This week task
"""
        current_focus_content = """# Current Focus

## Priorities
- Critical priority item
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)
        (self.state_dir / "ThisWeek.md").write_text(this_week_content)
        (self.state_dir / "CurrentFocus.md").write_text(current_focus_content)

        ranked = self.engine.rank_priorities()

        # Should have all three types
        types = set(item["type"] for item in ranked)
        self.assertIn("commitment", types)
        self.assertIn("task", types)
        self.assertIn("priority", types)

        # Verify each source is present
        titles = [item["title"] for item in ranked]
        self.assertIn("Work commitment", titles)
        self.assertIn("This week task", titles)
        self.assertIn("Critical priority item", titles)

    def test_priority_reason_is_descriptive(self):
        """Test that priority reasons are human-readable."""
        from datetime import timedelta

        today = self.engine.today
        commitments_content = f"""# Commitments

## Work
- [ ] Urgent task (due: {today.isoformat()})
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        ranked = self.engine.rank_priorities()
        urgent_item = ranked[0]

        # Should have descriptive reason
        self.assertIsInstance(urgent_item["priority_reason"], str)
        self.assertGreater(len(urgent_item["priority_reason"]), 0)
        self.assertIn("due TODAY", urgent_item["priority_reason"])

    def test_monday_meeting_boost(self):
        """Test that Monday meetings get priority boost."""
        from datetime import timedelta

        # Mock Monday
        original_today = self.engine.today
        days_until_monday = (7 - original_today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        monday = original_today + timedelta(days=days_until_monday)
        self.engine.today = monday

        commitments_content = """# Commitments

## Work
- [ ] Team standup meeting
- [ ] Regular work task
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        context = self.engine.gather_context()
        self.assertEqual(context["day_of_week"], "Monday")

        ranked = self.engine.rank_priorities(context)

        meeting = next(i for i in ranked if "standup" in i["title"].lower())
        self.assertIn("Monday meeting", meeting["priority_reason"])

        # Restore
        self.engine.today = original_today

    def test_friday_admin_task_boost(self):
        """Test that Friday admin tasks get priority boost."""
        from datetime import timedelta

        # Mock Friday
        original_today = self.engine.today
        days_until_friday = (4 - original_today.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        friday = original_today + timedelta(days=days_until_friday)
        self.engine.today = friday

        commitments_content = """# Commitments

## Work
- [ ] Submit timesheet
- [ ] Regular work task
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        context = self.engine.gather_context()
        self.assertEqual(context["day_of_week"], "Friday")

        ranked = self.engine.rank_priorities(context)

        timesheet = next(i for i in ranked if "timesheet" in i["title"].lower())
        self.assertIn("Friday admin", timesheet["priority_reason"])

        # Restore
        self.engine.today = original_today

    def test_empty_context_returns_empty_list(self):
        """Test that ranking with no tasks returns empty list."""
        # Don't create any State files
        ranked = self.engine.rank_priorities()

        self.assertEqual(ranked, [])

    def test_completed_tasks_excluded_from_ranking(self):
        """Test that completed tasks are not included in ranking."""
        commitments_content = """# Commitments

## Work
- [ ] Pending task
- [x] Completed task
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        ranked = self.engine.rank_priorities()

        titles = [item["title"] for item in ranked]
        self.assertIn("Pending task", titles)
        self.assertNotIn("Completed task", titles)


class TestTemplateRendering(unittest.TestCase):
    """Test suite for template rendering functionality."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create temporary directory for State and Templates
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "State"
        self.templates_dir = Path(self.temp_dir) / "Templates"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal State files
        self._create_test_state_files()

        # Create minimal templates
        self._create_test_templates()

        # Initialize engine with test directories
        self.engine = BriefingEngine(
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def _create_test_state_files(self):
        """Create test State files."""
        commitments = """# Commitments

## Work
- [ ] Complete project proposal (due: 2024-12-31)
- [ ] Send weekly update

## Personal
- [ ] Schedule dentist appointment
"""
        (self.state_dir / "Commitments.md").write_text(commitments)

        this_week = """# This Week

## Goals
- [ ] Finish template system
- [x] Complete priority ranking

## Tasks
- [ ] Review code
- [ ] Update documentation
"""
        (self.state_dir / "ThisWeek.md").write_text(this_week)

        current_focus = """# Current Focus

## Focus Areas
- Template rendering system
- Testing infrastructure

## Priorities
- Complete briefing engine
"""
        (self.state_dir / "CurrentFocus.md").write_text(current_focus)

    def _create_test_templates(self):
        """Create minimal test templates."""
        morning_template = """# Morning Briefing - {{ day_of_week }}

## Top Priorities
{% for item in top_priorities %}
- {{ item.title }} ({{ item.urgency_level }})
{% endfor %}

## Quick Wins
{% for win in quick_wins %}
- {{ win }}
{% endfor %}
"""
        (self.templates_dir / "briefing_morning.md").write_text(morning_template)

        evening_template = """# Evening Briefing - {{ day_of_week }}

## Accomplishments
{% for item in accomplishments %}
- {{ item }}
{% endfor %}

## Tomorrow Preview
{% for item in tomorrow_priorities %}
- {{ item.title }}
{% endfor %}
"""
        (self.templates_dir / "briefing_evening.md").write_text(evening_template)

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_render_morning_briefing(self):
        """Test rendering a morning briefing."""
        briefing = self.engine.render_briefing(briefing_type="morning")

        self.assertIsInstance(briefing, str)
        self.assertIn("Morning Briefing", briefing)
        self.assertIn("Top Priorities", briefing)

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_render_evening_briefing(self):
        """Test rendering an evening briefing."""
        briefing = self.engine.render_briefing(
            briefing_type="evening",
            accomplishments=["Task 1", "Task 2"]
        )

        self.assertIsInstance(briefing, str)
        self.assertIn("Evening Briefing", briefing)
        self.assertIn("Accomplishments", briefing)
        self.assertIn("Task 1", briefing)

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_custom_sections_injection(self):
        """Test injecting custom sections into briefing."""
        custom_sections = [
            {"title": "Health Goals", "content": "Exercise 30 min"},
            {"title": "Learning", "content": "Read chapter 5"}
        ]

        # Update template to include custom sections
        template_with_custom = """# Morning Briefing

{% for section in custom_sections %}
## {{ section.title }}
{{ section.content }}
{% endfor %}
"""
        (self.templates_dir / "briefing_morning.md").write_text(template_with_custom)

        briefing = self.engine.render_briefing(
            briefing_type="morning",
            custom_sections=custom_sections
        )

        self.assertIn("Health Goals", briefing)
        self.assertIn("Exercise 30 min", briefing)
        self.assertIn("Learning", briefing)

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_prepare_template_data_morning(self):
        """Test preparing template data for morning briefing."""
        context = self.engine.gather_context()
        template_data = self.engine._prepare_template_data(
            context,
            briefing_type="morning",
            energy_level=7
        )

        # Check required fields
        self.assertIn("today_date", template_data)
        self.assertIn("day_of_week", template_data)
        self.assertIn("top_priorities", template_data)
        self.assertIn("active_commitments", template_data)
        self.assertIn("pending_tasks", template_data)
        self.assertIn("focus_areas", template_data)
        self.assertIn("quick_wins", template_data)

        # Verify data types
        self.assertIsInstance(template_data["top_priorities"], list)
        self.assertIsInstance(template_data["quick_wins"], list)

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_prepare_template_data_evening(self):
        """Test preparing template data for evening briefing."""
        context = self.engine.gather_context()
        template_data = self.engine._prepare_template_data(
            context,
            briefing_type="evening",
            accomplishments=["Task 1", "Task 2"]
        )

        # Check evening-specific fields
        self.assertIn("accomplishments", template_data)
        self.assertIn("tomorrow_priorities", template_data)
        self.assertIn("energy_data", template_data)
        self.assertIn("reflection_notes", template_data)

        # Verify passed data
        self.assertEqual(template_data["accomplishments"], ["Task 1", "Task 2"])

    def test_identify_quick_wins(self):
        """Test identifying quick win tasks."""
        context = self.engine.gather_context()
        quick_wins = self.engine._identify_quick_wins(context)

        self.assertIsInstance(quick_wins, list)
        # Should find "Send weekly update" as a quick win
        self.assertTrue(any("Send weekly update" in win for win in quick_wins))

    def test_render_without_jinja2(self):
        """Test that rendering fails gracefully without Jinja2."""
        if JINJA2_AVAILABLE:
            self.skipTest("Jinja2 is available, cannot test failure case")

        with self.assertRaises(ValueError) as context:
            self.engine.render_briefing()

        self.assertIn("Jinja2 is required", str(context.exception))

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_render_with_missing_template(self):
        """Test that rendering fails with helpful error for missing template."""
        with self.assertRaises(ValueError) as context:
            self.engine.render_briefing(briefing_type="nonexistent")

        self.assertIn("Error rendering template", str(context.exception))

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_energy_level_affects_template_data(self):
        """Test that energy level is passed through to priority ranking."""
        context = self.engine.gather_context()

        # Low energy
        low_energy_data = self.engine._prepare_template_data(
            context,
            briefing_type="morning",
            energy_level=3
        )

        # High energy
        high_energy_data = self.engine._prepare_template_data(
            context,
            briefing_type="morning",
            energy_level=9
        )

        # Both should have priorities, but scores may differ
        self.assertIsInstance(low_energy_data["top_priorities"], list)
        self.assertIsInstance(high_energy_data["top_priorities"], list)

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_kwargs_passed_to_template(self):
        """Test that additional kwargs are passed to template."""
        template = """Custom: {{ custom_field }}"""
        (self.templates_dir / "briefing_morning.md").write_text(template)

        briefing = self.engine.render_briefing(
            briefing_type="morning",
            custom_field="test_value"
        )

        self.assertIn("test_value", briefing)


class TestHealthStatePrompting(unittest.TestCase):
    """Test suite for health state prompting functionality."""

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

    def test_prompt_for_health_state_skip_prompts(self):
        """Test that health prompts are skipped when skip_prompts=True."""
        result = self.engine.prompt_for_health_state(skip_prompts=True)
        self.assertIsNone(result)

    def test_prompt_for_health_state_skip_with_default_energy(self):
        """Test that default energy is returned when skip_prompts=True with default_energy."""
        result = self.engine.prompt_for_health_state(skip_prompts=True, default_energy=7)
        self.assertIsNotNone(result)
        self.assertEqual(result['energy_level'], 7)
        self.assertFalse(result['from_prompts'])

    def test_get_health_trend_no_data(self):
        """Test that health trend returns None when no data available."""
        trend = self.engine._get_health_trend()
        self.assertIsNone(trend)

    def test_get_health_trend_with_data(self):
        """Test health trend calculation with existing data."""
        if self.engine.health_tracker is None:
            self.skipTest("HealthStateTracker not available")

        # Create some test health data
        from datetime import timedelta
        for i in range(7):
            entry_date = self.engine.today - timedelta(days=i)
            self.engine.health_tracker.log_entry(
                energy_level=7 - (i % 3),
                sleep_hours=7.5 + (i % 2),
                entry_date=entry_date
            )

        # Get trend
        trend = self.engine._get_health_trend()
        self.assertIsNotNone(trend)
        self.assertIn('avg_energy', trend)
        self.assertIn('avg_sleep', trend)
        self.assertIn('sample_size', trend)
        self.assertIn('best_day', trend)
        self.assertIn('best_energy', trend)

        # Verify values are reasonable
        self.assertGreater(trend['avg_energy'], 0)
        self.assertLess(trend['avg_energy'], 11)
        self.assertGreater(trend['avg_sleep'], 0)
        self.assertEqual(trend['sample_size'], 7)

    def test_health_tracker_initialization(self):
        """Test that health tracker is initialized if available."""
        if self.engine.health_tracker is None:
            self.skipTest("HealthStateTracker not available")

        from Tools.health_state_tracker import HealthStateTracker
        self.assertIsInstance(self.engine.health_tracker, HealthStateTracker)
        self.assertEqual(str(self.engine.health_tracker.state_dir), str(self.state_dir))

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_morning_briefing_with_health_state(self):
        """Test that morning briefing includes health state when provided."""
        # Create minimal templates
        templates_dir = Path(self.temp_dir) / "Templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        template_content = """# Morning Briefing
{% if health_state %}
Energy: {{ health_state.energy_level }}/10
{% endif %}
Priorities: {{ top_priorities|length }}"""

        (templates_dir / "briefing_morning.md").write_text(template_content)

        # Create engine with templates
        engine = BriefingEngine(
            state_dir=str(self.state_dir),
            templates_dir=str(templates_dir)
        )

        # Create minimal state files
        (self.state_dir / "Commitments.md").write_text("# Commitments\n")
        (self.state_dir / "ThisWeek.md").write_text("# This Week\n")
        (self.state_dir / "CurrentFocus.md").write_text("# Current Focus\n")

        # Render with health state
        health_state = {
            'energy_level': 8,
            'sleep_hours': 7.5,
            'from_prompts': True
        }
        briefing = engine.render_briefing(
            briefing_type="morning",
            health_state=health_state
        )

        self.assertIn("Energy: 8/10", briefing)

    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2 not available")
    def test_morning_briefing_without_health_state(self):
        """Test that morning briefing works without health state."""
        # Create minimal templates
        templates_dir = Path(self.temp_dir) / "Templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        template_content = """# Morning Briefing
{% if health_state %}
Energy: {{ health_state.energy_level }}/10
{% endif %}
Priorities: {{ top_priorities|length }}"""

        (templates_dir / "briefing_morning.md").write_text(template_content)

        # Create engine with templates
        engine = BriefingEngine(
            state_dir=str(self.state_dir),
            templates_dir=str(templates_dir)
        )

        # Create minimal state files
        (self.state_dir / "Commitments.md").write_text("# Commitments\n")
        (self.state_dir / "ThisWeek.md").write_text("# This Week\n")
        (self.state_dir / "CurrentFocus.md").write_text("# Current Focus\n")

        # Render without health state
        briefing = engine.render_briefing(
            briefing_type="morning",
            health_state=None
        )

        # Should not include energy line
        self.assertNotIn("Energy:", briefing)
        self.assertIn("Priorities:", briefing)


class TestHealthAwareRecommendations(unittest.TestCase):
    """Test suite for health-aware task recommendation functionality."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create temporary directory for State files
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "State"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Initialize engine with test state directory
        self.engine = BriefingEngine(state_dir=str(self.state_dir))

        # Create test State files with diverse tasks
        self._create_test_state_files()

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def _create_test_state_files(self):
        """Create test State files with various task types."""
        # Commitments with mix of deep work and admin tasks
        commitments_content = """# Commitments

## Work
- [ ] Design new authentication system (Work) @due:2026-01-15
- [ ] Send project status email to client (Work) @due:2026-01-12
- [ ] Research API architecture patterns (Work) @due:2026-01-20

## Personal
- [ ] Schedule dentist appointment (Personal)
- [ ] Review and organize files (Personal)
"""
        (self.state_dir / "Commitments.md").write_text(commitments_content)

        # This Week tasks
        thisweek_content = """# This Week

## Goals
- [ ] Implement complex algorithm optimization
- [ ] Call insurance company
- [ ] Write technical documentation
- [ ] Update timesheet
"""
        (self.state_dir / "ThisWeek.md").write_text(thisweek_content)

        # Current Focus
        focus_content = """# Current Focus

## Priorities
- Refactor core database layer
- Send team meeting notes
"""
        (self.state_dir / "CurrentFocus.md").write_text(focus_content)

    def test_classify_task_type_deep_work(self):
        """Test classification of deep work tasks."""
        deep_work_tasks = [
            {"title": "Design new authentication system", "category": "Work"},
            {"title": "Research API architecture patterns", "category": "Work"},
            {"title": "Implement complex algorithm", "category": "Work"},
            {"title": "Refactor core database layer", "category": "Work"},
            {"title": "Analyze performance bottlenecks", "category": "Work"}
        ]

        for task in deep_work_tasks:
            result = self.engine._classify_task_type(task)
            self.assertEqual(result, "deep_work", f"Failed for task: {task['title']}")

    def test_classify_task_type_admin(self):
        """Test classification of admin/light tasks."""
        admin_tasks = [
            {"title": "Send project status email", "category": "Work"},
            {"title": "Schedule dentist appointment", "category": "Personal"},
            {"title": "Call insurance company", "category": "Personal"},
            {"title": "Update timesheet", "category": "Work"},
            {"title": "Review meeting notes", "category": "Work"}
        ]

        for task in admin_tasks:
            result = self.engine._classify_task_type(task)
            self.assertEqual(result, "admin", f"Failed for task: {task['title']}")

    def test_classify_task_type_general(self):
        """Test classification of general tasks."""
        general_task = {"title": "Complete project milestone", "category": "Work"}
        result = self.engine._classify_task_type(general_task)
        self.assertEqual(result, "general")

    def test_calculate_peak_focus_time_with_vyvanse(self):
        """Test peak focus time calculation with Vyvanse timing."""
        result = self.engine._calculate_peak_focus_time("08:00")

        self.assertIsNotNone(result)
        self.assertIn("peak_start", result)
        self.assertIn("peak_end", result)
        self.assertIn("peak_start_str", result)
        self.assertIn("peak_end_str", result)
        self.assertIn("is_peak_now", result)

        # Peak should be 2-4 hours after dose
        from datetime import time as dt_time
        vyvanse_dt = datetime.combine(self.engine.today, dt_time(8, 0))
        expected_start = vyvanse_dt + timedelta(hours=2)
        self.assertEqual(result["peak_start"], expected_start)

    def test_calculate_peak_focus_time_without_vyvanse(self):
        """Test peak focus time calculation without Vyvanse timing."""
        result = self.engine._calculate_peak_focus_time(None)
        self.assertIsNone(result)

    def test_health_aware_recommendations_high_energy(self):
        """Test recommendations with high energy level (8+)."""
        # Create mock health state
        health_state = {
            "has_todays_data": True,
            "current_energy": 9,
            "current_sleep": 8.0,
            "vyvanse_time": "08:00",
            "patterns": None
        }

        recommendations = self.engine.get_health_aware_recommendations(
            health_state=health_state
        )

        # Should prioritize deep work
        self.assertIsNotNone(recommendations)
        self.assertIn("recommended_tasks", recommendations)
        self.assertIn("deep_work_tasks", recommendations)
        self.assertIn("reasoning", recommendations)

        # Check reasoning includes high energy message
        reasoning_text = " ".join(recommendations["reasoning"])
        self.assertIn("High energy", reasoning_text)

        # Should have deep work tasks in recommendations
        self.assertTrue(len(recommendations["deep_work_tasks"]) > 0)

    def test_health_aware_recommendations_low_energy(self):
        """Test recommendations with low energy level (< 4)."""
        # Create mock health state
        health_state = {
            "has_todays_data": True,
            "current_energy": 3,
            "current_sleep": 5.0,
            "vyvanse_time": None,
            "patterns": None
        }

        recommendations = self.engine.get_health_aware_recommendations(
            health_state=health_state
        )

        # Should prioritize admin tasks
        self.assertIsNotNone(recommendations)
        reasoning_text = " ".join(recommendations["reasoning"])
        self.assertIn("Low energy", reasoning_text)

        # Should have reschedule recommendations for deep work
        self.assertTrue(len(recommendations["reschedule_recommendations"]) > 0)

        # Rescheduled tasks should be deep work
        for item in recommendations["reschedule_recommendations"]:
            self.assertIn("task", item)
            self.assertIn("reason", item)

    def test_health_aware_recommendations_moderate_energy(self):
        """Test recommendations with moderate energy level (4-6)."""
        # Create mock health state
        health_state = {
            "has_todays_data": True,
            "current_energy": 5,
            "current_sleep": 7.0,
            "vyvanse_time": None,
            "patterns": None
        }

        recommendations = self.engine.get_health_aware_recommendations(
            health_state=health_state
        )

        # Should focus on lighter tasks
        reasoning_text = " ".join(recommendations["reasoning"])
        self.assertIn("Moderate energy", reasoning_text)

        # Should have admin tasks prioritized
        self.assertTrue(len(recommendations["admin_tasks"]) > 0)

    def test_health_aware_recommendations_with_peak_focus(self):
        """Test that peak focus window is identified."""
        # Create mock health state with Vyvanse timing
        health_state = {
            "has_todays_data": True,
            "current_energy": 8,
            "current_sleep": 7.5,
            "vyvanse_time": "08:00",
            "patterns": None
        }

        recommendations = self.engine.get_health_aware_recommendations(
            health_state=health_state
        )

        # Should have peak focus window
        self.assertIn("peak_focus_window", recommendations)
        self.assertIsNotNone(recommendations["peak_focus_window"])

        peak_focus = recommendations["peak_focus_window"]
        self.assertIn("peak_start_str", peak_focus)
        self.assertIn("peak_end_str", peak_focus)

    def test_health_aware_recommendations_reschedule_logic(self):
        """Test that important tasks are recommended for rescheduling when energy is low."""
        # Create mock health state with low energy
        health_state = {
            "has_todays_data": True,
            "current_energy": 2,
            "current_sleep": 4.0,
            "vyvanse_time": None,
            "patterns": None
        }

        recommendations = self.engine.get_health_aware_recommendations(
            health_state=health_state
        )

        # Should have reschedule recommendations
        reschedule = recommendations["reschedule_recommendations"]
        self.assertTrue(len(reschedule) > 0)

        # Each recommendation should have task and reason
        for item in reschedule:
            self.assertIn("task", item)
            self.assertIn("reason", item)
            self.assertIsInstance(item["reason"], str)
            self.assertTrue(len(item["reason"]) > 0)

    def test_health_aware_recommendations_no_health_data(self):
        """Test recommendations when no health data is available."""
        recommendations = self.engine.get_health_aware_recommendations(
            health_state=None
        )

        # Should still return recommendations with fallback
        self.assertIsNotNone(recommendations)
        reasoning_text = " ".join(recommendations["reasoning"])
        self.assertIn("No energy data", reasoning_text)

        # Should have recommended tasks (using standard priority ranking)
        self.assertTrue(len(recommendations["recommended_tasks"]) > 0)

    def test_health_aware_recommendations_with_patterns(self):
        """Test recommendations include pattern-based insights."""
        # Create mock health state with patterns
        health_state = {
            "has_todays_data": True,
            "current_energy": 6,
            "current_sleep": 7.0,
            "vyvanse_time": None,
            "patterns": {
                "has_sufficient_data": True,
                "worst_energy_day": self.engine.today.strftime("%A"),
                "best_energy_day": "Friday"
            }
        }

        recommendations = self.engine.get_health_aware_recommendations(
            health_state=health_state
        )

        # Should include pattern-based reasoning
        reasoning_text = " ".join(recommendations["reasoning"])
        self.assertIn("Historically low energy", reasoning_text)

    def test_health_aware_recommendations_structure(self):
        """Test that recommendations return expected data structure."""
        health_state = {
            "has_todays_data": True,
            "current_energy": 7,
            "current_sleep": 7.5,
            "vyvanse_time": "08:00",
            "patterns": None
        }

        recommendations = self.engine.get_health_aware_recommendations(
            health_state=health_state
        )

        # Verify all expected keys are present
        expected_keys = [
            "recommended_tasks",
            "deep_work_tasks",
            "admin_tasks",
            "general_tasks",
            "reschedule_recommendations",
            "peak_focus_window",
            "energy_level",
            "reasoning",
            "health_state"
        ]

        for key in expected_keys:
            self.assertIn(key, recommendations, f"Missing key: {key}")

        # Verify types
        self.assertIsInstance(recommendations["recommended_tasks"], list)
        self.assertIsInstance(recommendations["deep_work_tasks"], list)
        self.assertIsInstance(recommendations["admin_tasks"], list)
        self.assertIsInstance(recommendations["general_tasks"], list)
        self.assertIsInstance(recommendations["reschedule_recommendations"], list)
        self.assertIsInstance(recommendations["reasoning"], list)
        self.assertEqual(recommendations["energy_level"], 7)


if __name__ == '__main__':
    unittest.main()
