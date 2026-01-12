"""
Unit tests for PatternAnalyzer functionality.

Tests pattern tracking, analysis, and recommendation logic.
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import date, datetime, timedelta
import sys
import os

# Add Tools to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Tools.pattern_analyzer import PatternAnalyzer


class TestPatternAnalyzer(unittest.TestCase):
    """Test suite for PatternAnalyzer class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create temporary directory for State files
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "State"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Initialize analyzer with test state directory
        self.analyzer = PatternAnalyzer(state_dir=str(self.state_dir))

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test PatternAnalyzer initialization."""
        self.assertEqual(str(self.analyzer.state_dir), str(self.state_dir))
        self.assertIsInstance(self.analyzer.today, date)
        self.assertTrue(self.analyzer.state_dir.exists())
        self.assertIsInstance(self.analyzer.patterns_data, dict)
        self.assertIn("task_completions", self.analyzer.patterns_data)
        self.assertIn("metadata", self.analyzer.patterns_data)

    def test_record_task_completion_basic(self):
        """Test recording a basic task completion."""
        result = self.analyzer.record_task_completion(
            task_title="Review PR for authentication",
            task_category="admin"
        )

        self.assertTrue(result)
        self.assertEqual(len(self.analyzer.patterns_data["task_completions"]), 1)

        completion = self.analyzer.patterns_data["task_completions"][0]
        self.assertEqual(completion["task_title"], "Review PR for authentication")
        self.assertEqual(completion["task_category"], "admin")
        self.assertIn("day_of_week", completion)
        self.assertIn("time_of_day", completion)
        self.assertIn("hour", completion)

    def test_record_task_completion_with_time(self):
        """Test recording task completion with specific time."""
        specific_time = datetime(2026, 1, 9, 14, 30)  # Friday afternoon
        specific_date = specific_time.date()

        result = self.analyzer.record_task_completion(
            task_title="Design API architecture",
            task_category="deep_work",
            completion_time=specific_time,
            completion_date=specific_date
        )

        self.assertTrue(result)
        completion = self.analyzer.patterns_data["task_completions"][0]
        self.assertEqual(completion["completion_time"], "14:30")
        self.assertEqual(completion["hour"], 14)
        self.assertEqual(completion["time_of_day"], "afternoon")
        self.assertEqual(completion["day_of_week"], "Friday")

    def test_record_task_completion_validation(self):
        """Test validation for task completion recording."""
        # Empty task title
        result = self.analyzer.record_task_completion(task_title="")
        self.assertFalse(result)

        result = self.analyzer.record_task_completion(task_title="   ")
        self.assertFalse(result)

    def test_infer_task_category(self):
        """Test automatic task category inference."""
        # Test deep work
        self.assertEqual(
            self.analyzer._infer_task_category("Design new API architecture"),
            "deep_work"
        )
        self.assertEqual(
            self.analyzer._infer_task_category("Implement authentication system"),
            "deep_work"
        )

        # Test admin
        self.assertEqual(
            self.analyzer._infer_task_category("Send weekly status report"),
            "admin"
        )
        self.assertEqual(
            self.analyzer._infer_task_category("Schedule team meeting"),
            "admin"
        )

        # Test personal
        self.assertEqual(
            self.analyzer._infer_task_category("Call mom about weekend"),
            "personal"
        )
        self.assertEqual(
            self.analyzer._infer_task_category("Pay utility bills"),
            "personal"
        )

        # Test general (no clear match)
        self.assertEqual(
            self.analyzer._infer_task_category("Something random"),
            "general"
        )

    def test_classify_time_of_day(self):
        """Test time of day classification."""
        self.assertEqual(self.analyzer._classify_time_of_day(8), "morning")
        self.assertEqual(self.analyzer._classify_time_of_day(13), "afternoon")
        self.assertEqual(self.analyzer._classify_time_of_day(18), "evening")
        self.assertEqual(self.analyzer._classify_time_of_day(23), "night")
        self.assertEqual(self.analyzer._classify_time_of_day(3), "night")

    def test_get_completions_basic(self):
        """Test retrieving completions."""
        # Record some completions
        self.analyzer.record_task_completion("Task 1", "admin")
        self.analyzer.record_task_completion("Task 2", "deep_work")

        completions = self.analyzer.get_completions(days=30)
        self.assertEqual(len(completions), 2)

    def test_get_completions_with_category_filter(self):
        """Test retrieving completions filtered by category."""
        self.analyzer.record_task_completion("Admin task", "admin")
        self.analyzer.record_task_completion("Deep work task", "deep_work")
        self.analyzer.record_task_completion("Another admin task", "admin")

        admin_completions = self.analyzer.get_completions(days=30, category="admin")
        self.assertEqual(len(admin_completions), 2)

        deep_work_completions = self.analyzer.get_completions(days=30, category="deep_work")
        self.assertEqual(len(deep_work_completions), 1)

    def test_get_completions_date_filter(self):
        """Test that old completions are filtered by date."""
        # Record a recent completion
        self.analyzer.record_task_completion("Recent task", "admin")

        # Record an old completion (31 days ago)
        old_date = self.analyzer.today - timedelta(days=31)
        old_time = datetime.combine(old_date, datetime.now().time())
        self.analyzer.record_task_completion(
            "Old task",
            "admin",
            completion_time=old_time,
            completion_date=old_date
        )

        # Get last 30 days - should only include recent
        completions = self.analyzer.get_completions(days=30)
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0]["task_title"], "Recent task")

    def test_identify_patterns_insufficient_data(self):
        """Test pattern identification with insufficient data."""
        # Record only a few completions
        self.analyzer.record_task_completion("Task 1", "admin")
        self.analyzer.record_task_completion("Task 2", "deep_work")

        patterns = self.analyzer.identify_patterns(min_days=14)
        self.assertFalse(patterns["has_sufficient_data"])
        self.assertIn("message", patterns)

    def test_identify_patterns_with_sufficient_data(self):
        """Test pattern identification with sufficient data."""
        # Create 20 days of task completion data
        for day_offset in range(20):
            completion_date = self.analyzer.today - timedelta(days=day_offset)
            completion_time = datetime.combine(completion_date, datetime.now().time())

            # Pattern: Admin tasks on Fridays, deep work on other days
            if completion_date.strftime("%A") == "Friday":
                self.analyzer.record_task_completion(
                    f"Admin task {day_offset}",
                    "admin",
                    completion_time=completion_time,
                    completion_date=completion_date
                )
            else:
                self.analyzer.record_task_completion(
                    f"Deep work task {day_offset}",
                    "deep_work",
                    completion_time=completion_time,
                    completion_date=completion_date
                )

        patterns = self.analyzer.identify_patterns(min_days=14)
        self.assertTrue(patterns["has_sufficient_data"])
        self.assertIn("day_of_week_patterns", patterns)
        self.assertIn("time_of_day_patterns", patterns)
        self.assertIn("category_patterns", patterns)
        self.assertIn("insights", patterns)

    def test_day_of_week_patterns(self):
        """Test day of week pattern analysis."""
        # Create pattern: All admin tasks on Monday
        for i in range(4):  # 4 Mondays
            monday = self.analyzer.today - timedelta(days=self.analyzer.today.weekday() + 7 * i)
            monday_time = datetime.combine(monday, datetime.now().time())

            self.analyzer.record_task_completion(
                f"Admin task {i}",
                "admin",
                completion_time=monday_time,
                completion_date=monday
            )

        # Add some other tasks on other days
        for day_offset in range(1, 15):
            if (self.analyzer.today - timedelta(days=day_offset)).strftime("%A") != "Monday":
                completion_date = self.analyzer.today - timedelta(days=day_offset)
                completion_time = datetime.combine(completion_date, datetime.now().time())
                self.analyzer.record_task_completion(
                    f"Other task {day_offset}",
                    "deep_work",
                    completion_time=completion_time,
                    completion_date=completion_date
                )

        patterns = self.analyzer.identify_patterns(min_days=14)
        if patterns["has_sufficient_data"]:
            day_patterns = patterns["day_of_week_patterns"]
            if "Monday" in day_patterns:
                self.assertIn("category_distribution", day_patterns["Monday"])

    def test_time_of_day_patterns(self):
        """Test time of day pattern analysis."""
        # Create pattern: Morning deep work, afternoon admin
        for day_offset in range(15):
            completion_date = self.analyzer.today - timedelta(days=day_offset)

            # Morning deep work
            morning_time = datetime.combine(completion_date, datetime.min.time().replace(hour=9))
            self.analyzer.record_task_completion(
                f"Morning deep work {day_offset}",
                "deep_work",
                completion_time=morning_time,
                completion_date=completion_date
            )

            # Afternoon admin
            afternoon_time = datetime.combine(completion_date, datetime.min.time().replace(hour=14))
            self.analyzer.record_task_completion(
                f"Afternoon admin {day_offset}",
                "admin",
                completion_time=afternoon_time,
                completion_date=completion_date
            )

        patterns = self.analyzer.identify_patterns(min_days=14)
        self.assertTrue(patterns["has_sufficient_data"])

        time_patterns = patterns["time_of_day_patterns"]
        self.assertIn("morning", time_patterns)
        self.assertIn("afternoon", time_patterns)

    def test_category_patterns(self):
        """Test category pattern analysis."""
        # Create varied completions across categories
        categories = ["admin", "deep_work", "personal", "general"]
        for day_offset in range(20):
            completion_date = self.analyzer.today - timedelta(days=day_offset)
            completion_time = datetime.combine(completion_date, datetime.now().time())

            category = categories[day_offset % len(categories)]
            self.analyzer.record_task_completion(
                f"Task {day_offset}",
                category,
                completion_time=completion_time,
                completion_date=completion_date
            )

        patterns = self.analyzer.identify_patterns(min_days=14)
        self.assertTrue(patterns["has_sufficient_data"])

        category_patterns = patterns["category_patterns"]
        self.assertGreater(len(category_patterns), 0)

        for category, data in category_patterns.items():
            self.assertIn("total_completions", data)
            self.assertIn("percentage_of_total", data)
            self.assertIn("preferred_time_of_day", data)

    def test_insights_generation(self):
        """Test that insights are generated correctly."""
        # Create strong pattern: All Friday tasks are admin
        fridays_count = 0
        for day_offset in range(60):
            completion_date = self.analyzer.today - timedelta(days=day_offset)
            completion_time = datetime.combine(completion_date, datetime.now().time())

            if completion_date.strftime("%A") == "Friday":
                self.analyzer.record_task_completion(
                    f"Admin task {day_offset}",
                    "admin",
                    completion_time=completion_time,
                    completion_date=completion_date
                )
                fridays_count += 1
            else:
                self.analyzer.record_task_completion(
                    f"Other task {day_offset}",
                    "deep_work",
                    completion_time=completion_time,
                    completion_date=completion_date
                )

        if fridays_count >= 3:  # Ensure we have enough Friday data
            patterns = self.analyzer.identify_patterns(min_days=14)
            self.assertTrue(patterns["has_sufficient_data"])
            self.assertGreater(len(patterns["insights"]), 0)

    def test_get_recommendations_insufficient_data(self):
        """Test recommendations with insufficient data."""
        recommendations = self.analyzer.get_recommendations_for_context()
        self.assertFalse(recommendations["has_recommendations"])
        self.assertIn("reason", recommendations)

    def test_get_recommendations_with_patterns(self):
        """Test recommendations based on historical patterns."""
        # Create strong Friday admin pattern
        for week in range(3):
            friday = self.analyzer.today - timedelta(days=self.analyzer.today.weekday() - 4 + 7 * week)
            if friday <= self.analyzer.today:
                friday_time = datetime.combine(friday, datetime.min.time().replace(hour=14))
                self.analyzer.record_task_completion(
                    f"Admin task week {week}",
                    "admin",
                    completion_time=friday_time,
                    completion_date=friday
                )

        # Add other tasks throughout the weeks
        for day_offset in range(1, 21):
            completion_date = self.analyzer.today - timedelta(days=day_offset)
            if completion_date.strftime("%A") != "Friday":
                completion_time = datetime.combine(completion_date, datetime.now().time())
                self.analyzer.record_task_completion(
                    f"Other task {day_offset}",
                    "deep_work",
                    completion_time=completion_time,
                    completion_date=completion_date
                )

        recommendations = self.analyzer.get_recommendations_for_context(
            current_day="Friday",
            current_time_of_day="afternoon"
        )

        self.assertIn("has_recommendations", recommendations)
        self.assertIn("current_context", recommendations)
        self.assertEqual(recommendations["current_context"]["day"], "Friday")

    def test_recommendations_context_defaults(self):
        """Test that recommendations use current context by default."""
        # Create enough data
        for day_offset in range(20):
            completion_date = self.analyzer.today - timedelta(days=day_offset)
            completion_time = datetime.combine(completion_date, datetime.now().time())
            self.analyzer.record_task_completion(
                f"Task {day_offset}",
                "admin",
                completion_time=completion_time,
                completion_date=completion_date
            )

        recommendations = self.analyzer.get_recommendations_for_context()
        self.assertIn("current_context", recommendations)
        self.assertIsNotNone(recommendations["current_context"]["day"])
        self.assertIsNotNone(recommendations["current_context"]["time_of_day"])

    def test_data_retention_limit(self):
        """Test that data older than 180 days is automatically cleaned up."""
        # Record a task from 200 days ago
        old_date = self.analyzer.today - timedelta(days=200)
        old_time = datetime.combine(old_date, datetime.now().time())
        self.analyzer.record_task_completion(
            "Very old task",
            "admin",
            completion_time=old_time,
            completion_date=old_date
        )

        # Record a recent task
        self.analyzer.record_task_completion("Recent task", "admin")

        # Old task should be filtered out
        completions = self.analyzer.patterns_data["task_completions"]
        dates = [c["completion_date"] for c in completions]
        self.assertNotIn(old_date.isoformat(), dates)

    def test_persistence(self):
        """Test that patterns persist across analyzer instances."""
        # Record a completion
        self.analyzer.record_task_completion("Test task", "admin")

        # Create new analyzer instance with same state dir
        new_analyzer = PatternAnalyzer(state_dir=str(self.state_dir))

        # Data should be loaded
        self.assertEqual(
            len(new_analyzer.patterns_data["task_completions"]),
            1
        )
        self.assertEqual(
            new_analyzer.patterns_data["task_completions"][0]["task_title"],
            "Test task"
        )


if __name__ == '__main__':
    unittest.main()
