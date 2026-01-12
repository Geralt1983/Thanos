"""
Unit tests for HealthStateTracker functionality.

Tests health data logging, pattern detection, and recommendation logic.
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import date, timedelta
import sys
import os

# Add Tools to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Tools.health_state_tracker import HealthStateTracker


class TestHealthStateTracker(unittest.TestCase):
    """Test suite for HealthStateTracker class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        # Create temporary directory for State files
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "State"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Initialize tracker with test state directory
        self.tracker = HealthStateTracker(state_dir=str(self.state_dir))

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test HealthStateTracker initialization."""
        self.assertEqual(str(self.tracker.state_dir), str(self.state_dir))
        self.assertIsInstance(self.tracker.today, date)
        self.assertTrue(self.tracker.state_dir.exists())
        self.assertIsInstance(self.tracker.health_log, dict)

    def test_log_entry_basic(self):
        """Test logging a basic health entry."""
        result = self.tracker.log_entry(
            energy_level=7,
            sleep_hours=8.0,
            vyvanse_time="08:30"
        )

        self.assertTrue(result)
        self.assertEqual(len(self.tracker.health_log["entries"]), 1)

        entry = self.tracker.health_log["entries"][0]
        self.assertEqual(entry["energy_level"], 7)
        self.assertEqual(entry["sleep_hours"], 8.0)
        self.assertEqual(entry["vyvanse_time"], "08:30")
        self.assertEqual(entry["date"], self.tracker.today.isoformat())

    def test_log_entry_validation(self):
        """Test input validation for log_entry."""
        # Invalid energy level
        result = self.tracker.log_entry(energy_level=11, sleep_hours=8.0)
        self.assertFalse(result)

        result = self.tracker.log_entry(energy_level=0, sleep_hours=8.0)
        self.assertFalse(result)

        # Invalid sleep hours
        result = self.tracker.log_entry(energy_level=7, sleep_hours=-1)
        self.assertFalse(result)

        result = self.tracker.log_entry(energy_level=7, sleep_hours=25)
        self.assertFalse(result)

        # Invalid time format
        result = self.tracker.log_entry(energy_level=7, sleep_hours=8.0, vyvanse_time="8:30am")
        self.assertFalse(result)

    def test_log_entry_update_existing(self):
        """Test updating an existing entry for the same date."""
        # Log initial entry
        self.tracker.log_entry(energy_level=5, sleep_hours=6.0)
        self.assertEqual(len(self.tracker.health_log["entries"]), 1)

        # Update entry for same date
        self.tracker.log_entry(energy_level=7, sleep_hours=8.0)
        self.assertEqual(len(self.tracker.health_log["entries"]), 1)

        # Verify updated values
        entry = self.tracker.health_log["entries"][0]
        self.assertEqual(entry["energy_level"], 7)
        self.assertEqual(entry["sleep_hours"], 8.0)

    def test_log_entry_with_notes(self):
        """Test logging entry with notes."""
        result = self.tracker.log_entry(
            energy_level=6,
            sleep_hours=7.5,
            notes="Felt productive today"
        )

        self.assertTrue(result)
        entry = self.tracker.health_log["entries"][0]
        self.assertEqual(entry["notes"], "Felt productive today")

    def test_get_entry_today(self):
        """Test retrieving today's entry."""
        self.tracker.log_entry(energy_level=8, sleep_hours=8.5)

        entry = self.tracker.get_entry()
        self.assertIsNotNone(entry)
        self.assertEqual(entry["energy_level"], 8)
        self.assertEqual(entry["sleep_hours"], 8.5)

    def test_get_entry_missing(self):
        """Test retrieving entry when none exists."""
        entry = self.tracker.get_entry()
        self.assertIsNone(entry)

    def test_get_entry_specific_date(self):
        """Test retrieving entry for specific date."""
        past_date = self.tracker.today - timedelta(days=5)
        self.tracker.log_entry(
            energy_level=6,
            sleep_hours=7.0,
            entry_date=past_date
        )

        entry = self.tracker.get_entry(entry_date=past_date)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["energy_level"], 6)
        self.assertEqual(entry["date"], past_date.isoformat())

    def test_get_recent_entries(self):
        """Test getting recent entries."""
        # Log entries for past 10 days
        for i in range(10):
            entry_date = self.tracker.today - timedelta(days=i)
            self.tracker.log_entry(
                energy_level=7 - (i % 3),
                sleep_hours=7.5,
                entry_date=entry_date
            )

        # Get last 7 days
        recent = self.tracker.get_recent_entries(days=7)
        self.assertEqual(len(recent), 7)

        # Verify sorted by date (most recent first)
        dates = [e["date"] for e in recent]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_calculate_averages_basic(self):
        """Test calculating 7-day averages."""
        # Log entries with known values
        for i in range(7):
            entry_date = self.tracker.today - timedelta(days=i)
            self.tracker.log_entry(
                energy_level=6,
                sleep_hours=8.0,
                entry_date=entry_date
            )

        averages = self.tracker.calculate_averages(days=7)
        self.assertEqual(averages["avg_energy_level"], 6.0)
        self.assertEqual(averages["avg_sleep_hours"], 8.0)
        self.assertEqual(averages["sample_size"], 7)

    def test_calculate_averages_no_data(self):
        """Test calculating averages with no data."""
        averages = self.tracker.calculate_averages(days=7)
        self.assertEqual(averages["avg_energy_level"], 0.0)
        self.assertEqual(averages["avg_sleep_hours"], 0.0)
        self.assertEqual(averages["sample_size"], 0)

    def test_calculate_averages_varying_values(self):
        """Test calculating averages with varying values."""
        energy_values = [5, 6, 7, 8, 7, 6, 5]
        sleep_values = [6.5, 7.0, 7.5, 8.0, 7.5, 7.0, 6.5]

        for i, (energy, sleep) in enumerate(zip(energy_values, sleep_values)):
            entry_date = self.tracker.today - timedelta(days=i)
            self.tracker.log_entry(
                energy_level=energy,
                sleep_hours=sleep,
                entry_date=entry_date
            )

        averages = self.tracker.calculate_averages(days=7)
        expected_avg_energy = sum(energy_values) / len(energy_values)
        expected_avg_sleep = sum(sleep_values) / len(sleep_values)

        self.assertAlmostEqual(averages["avg_energy_level"], expected_avg_energy, places=1)
        self.assertAlmostEqual(averages["avg_sleep_hours"], expected_avg_sleep, places=1)

    def test_identify_patterns_insufficient_data(self):
        """Test pattern identification with insufficient data."""
        # Log only 5 days of data
        for i in range(5):
            entry_date = self.tracker.today - timedelta(days=i)
            self.tracker.log_entry(
                energy_level=7,
                sleep_hours=8.0,
                entry_date=entry_date
            )

        patterns = self.tracker.identify_patterns(min_days=14)
        self.assertFalse(patterns["has_sufficient_data"])
        self.assertEqual(patterns["sample_size"], 5)
        self.assertEqual(patterns["required_size"], 14)

    def test_identify_patterns_day_of_week(self):
        """Test pattern identification for day of week."""
        # Create 4 weeks of data with Monday being low energy
        for week in range(4):
            for day in range(7):
                entry_date = self.tracker.today - timedelta(days=week * 7 + day)
                day_name = entry_date.strftime("%A")

                # Mondays have lower energy
                if day_name == "Monday":
                    energy = 4
                else:
                    energy = 7

                self.tracker.log_entry(
                    energy_level=energy,
                    sleep_hours=7.5,
                    entry_date=entry_date
                )

        patterns = self.tracker.identify_patterns(min_days=14)
        self.assertTrue(patterns["has_sufficient_data"])
        self.assertIn("day_of_week_patterns", patterns)

        # Check that Monday has lower average
        monday_avg = patterns["day_of_week_patterns"]["Monday"]["avg_energy"]
        tuesday_avg = patterns["day_of_week_patterns"]["Tuesday"]["avg_energy"]
        self.assertLess(monday_avg, tuesday_avg)

        # Check worst day identification
        self.assertEqual(patterns["worst_energy_day"], "Monday")

    def test_identify_patterns_best_worst_days(self):
        """Test identification of best and worst energy days."""
        # Create data with Friday being best, Monday being worst
        for week in range(4):
            for day in range(7):
                entry_date = self.tracker.today - timedelta(days=week * 7 + day)
                day_name = entry_date.strftime("%A")

                if day_name == "Monday":
                    energy = 4
                elif day_name == "Friday":
                    energy = 9
                else:
                    energy = 6

                self.tracker.log_entry(
                    energy_level=energy,
                    sleep_hours=7.5,
                    entry_date=entry_date
                )

        patterns = self.tracker.identify_patterns(min_days=14)
        self.assertEqual(patterns["worst_energy_day"], "Monday")
        self.assertEqual(patterns["best_energy_day"], "Friday")

    def test_sleep_energy_correlation_strong(self):
        """Test sleep-energy correlation detection (strong)."""
        # Create data with clear sleep-energy correlation
        for i in range(20):
            entry_date = self.tracker.today - timedelta(days=i)
            # Alternate between good sleep (high energy) and poor sleep (low energy)
            if i % 2 == 0:
                energy = 8
                sleep = 8.5
            else:
                energy = 4
                sleep = 5.5

            self.tracker.log_entry(
                energy_level=energy,
                sleep_hours=sleep,
                entry_date=entry_date
            )

        patterns = self.tracker.identify_patterns(min_days=14)
        correlation = patterns["sleep_energy_correlation"]

        self.assertIn(correlation["correlation"], ["strong", "moderate"])
        self.assertIn("relationship", correlation)

    def test_vyvanse_timing_analysis(self):
        """Test Vyvanse timing analysis."""
        # Create data with 08:00 timing being better than 10:00
        for i in range(20):
            entry_date = self.tracker.today - timedelta(days=i)
            if i % 2 == 0:
                energy = 8
                vyvanse_time = "08:00"
            else:
                energy = 5
                vyvanse_time = "10:00"

            self.tracker.log_entry(
                energy_level=energy,
                sleep_hours=7.5,
                vyvanse_time=vyvanse_time,
                entry_date=entry_date
            )

        patterns = self.tracker.identify_patterns(min_days=14)
        vyvanse = patterns["vyvanse_timing"]

        self.assertTrue(vyvanse["has_data"])
        self.assertIn("optimal_time", vyvanse)
        self.assertIn("time_averages", vyvanse)

    def test_vyvanse_timing_no_data(self):
        """Test Vyvanse timing analysis with no medication data."""
        for i in range(20):
            entry_date = self.tracker.today - timedelta(days=i)
            self.tracker.log_entry(
                energy_level=7,
                sleep_hours=7.5,
                entry_date=entry_date
            )

        patterns = self.tracker.identify_patterns(min_days=14)
        vyvanse = patterns["vyvanse_timing"]

        self.assertFalse(vyvanse["has_data"])

    def test_get_current_state_assessment_with_data(self):
        """Test current state assessment with today's data."""
        # Log today's entry
        self.tracker.log_entry(
            energy_level=8,
            sleep_hours=8.0,
            vyvanse_time="08:30"
        )

        # Add some historical data
        for i in range(1, 8):
            entry_date = self.tracker.today - timedelta(days=i)
            self.tracker.log_entry(
                energy_level=6,
                sleep_hours=7.5,
                entry_date=entry_date
            )

        assessment = self.tracker.get_current_state_assessment()

        self.assertTrue(assessment["has_todays_data"])
        self.assertEqual(assessment["current_energy"], 8)
        self.assertEqual(assessment["current_sleep"], 8.0)
        self.assertEqual(assessment["vyvanse_time"], "08:30")
        self.assertIn("recommendations", assessment)
        self.assertGreater(len(assessment["recommendations"]), 0)

    def test_get_current_state_assessment_no_data(self):
        """Test current state assessment without today's data."""
        assessment = self.tracker.get_current_state_assessment()

        self.assertFalse(assessment["has_todays_data"])
        self.assertIsNone(assessment["current_energy"])
        self.assertIsNone(assessment["current_sleep"])

    def test_recommendations_high_energy(self):
        """Test recommendations for high energy level."""
        self.tracker.log_entry(energy_level=9, sleep_hours=8.5)
        assessment = self.tracker.get_current_state_assessment()

        recommendations = assessment["recommendations"]
        self.assertTrue(any("deep work" in r.lower() for r in recommendations))

    def test_recommendations_low_energy(self):
        """Test recommendations for low energy level."""
        self.tracker.log_entry(energy_level=3, sleep_hours=5.0)
        assessment = self.tracker.get_current_state_assessment()

        recommendations = assessment["recommendations"]
        self.assertTrue(any("simple" in r.lower() or "rest" in r.lower() for r in recommendations))

    def test_recommendations_vyvanse_peak_timing(self):
        """Test recommendations include Vyvanse peak timing."""
        self.tracker.log_entry(
            energy_level=7,
            sleep_hours=7.5,
            vyvanse_time="08:00"
        )
        assessment = self.tracker.get_current_state_assessment()

        recommendations = assessment["recommendations"]
        self.assertTrue(any("peak focus time" in r.lower() for r in recommendations))

    def test_persistence_across_instances(self):
        """Test that data persists across tracker instances."""
        # Log entry in first instance
        self.tracker.log_entry(energy_level=7, sleep_hours=8.0)

        # Create new tracker instance
        new_tracker = HealthStateTracker(state_dir=str(self.state_dir))

        # Verify data persisted
        entry = new_tracker.get_entry()
        self.assertIsNotNone(entry)
        self.assertEqual(entry["energy_level"], 7)
        self.assertEqual(entry["sleep_hours"], 8.0)

    def test_health_log_file_structure(self):
        """Test that health log file has proper structure."""
        self.tracker.log_entry(energy_level=7, sleep_hours=8.0)

        # Read file directly
        with open(self.tracker.health_log_path, 'r') as f:
            data = json.load(f)

        self.assertIn("entries", data)
        self.assertIn("metadata", data)
        self.assertIsInstance(data["entries"], list)
        self.assertIsInstance(data["metadata"], dict)
        self.assertIn("last_updated", data["metadata"])

    def test_entries_sorted_by_date(self):
        """Test that entries are sorted by date (most recent first)."""
        # Log entries out of order
        dates = [
            self.tracker.today - timedelta(days=5),
            self.tracker.today - timedelta(days=2),
            self.tracker.today,
            self.tracker.today - timedelta(days=8)
        ]

        for entry_date in dates:
            self.tracker.log_entry(
                energy_level=7,
                sleep_hours=7.5,
                entry_date=entry_date
            )

        entries = self.tracker.health_log["entries"]
        dates_in_log = [e["date"] for e in entries]

        # Verify sorted in descending order (most recent first)
        self.assertEqual(dates_in_log, sorted(dates_in_log, reverse=True))


if __name__ == "__main__":
    unittest.main()
