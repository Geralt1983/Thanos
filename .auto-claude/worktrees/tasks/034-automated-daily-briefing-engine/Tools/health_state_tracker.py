"""
HealthStateTracker - Module for tracking and assessing energy, sleep, and medication timing.

This module provides functionality for logging daily health metrics (energy levels,
sleep hours, medication timing) and analyzing patterns over time to provide intelligent
recommendations for task scheduling.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, time, timedelta
from collections import defaultdict


class HealthStateTracker:
    """
    Tracks and analyzes health state metrics including energy, sleep, and medication.

    Stores daily entries in State/HealthLog.json and provides pattern analysis
    for optimizing task scheduling based on historical data.
    """

    def __init__(self, state_dir: Optional[str] = None):
        """
        Initialize the HealthStateTracker.

        Args:
            state_dir: Path to the State directory. Defaults to ./State relative to cwd.
        """
        if state_dir is None:
            state_dir = os.path.join(os.getcwd(), "State")

        self.state_dir = Path(state_dir)
        self.health_log_path = self.state_dir / "HealthLog.json"
        self.today = date.today()

        # Ensure State directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Load existing health log
        self.health_log = self._load_health_log()

    def _load_health_log(self) -> Dict[str, Any]:
        """
        Load health log from JSON file.

        Returns:
            Dictionary with health log data structure.
        """
        if not self.health_log_path.exists():
            return {
                "entries": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }

        try:
            with open(self.health_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading HealthLog.json: {e}")
            return {
                "entries": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                    "load_error": str(e)
                }
            }

    def _save_health_log(self) -> bool:
        """
        Save health log to JSON file.

        Returns:
            True if save successful, False otherwise.
        """
        try:
            self.health_log["metadata"]["last_updated"] = datetime.now().isoformat()
            with open(self.health_log_path, 'w', encoding='utf-8') as f:
                json.dump(self.health_log, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error: Failed to save HealthLog.json: {e}")
            return False

    def log_entry(
        self,
        energy_level: int,
        sleep_hours: float,
        vyvanse_time: Optional[str] = None,
        entry_date: Optional[date] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Log a health state entry for a given date.

        Args:
            energy_level: Energy level from 1 (exhausted) to 10 (peak energy)
            sleep_hours: Hours of sleep (e.g., 7.5)
            vyvanse_time: Time medication taken in HH:MM format (e.g., "08:30")
            entry_date: Date for this entry. Defaults to today.
            notes: Optional notes about the day

        Returns:
            True if entry logged successfully, False otherwise.
        """
        # Validate inputs
        if not (1 <= energy_level <= 10):
            print("Error: energy_level must be between 1 and 10")
            return False

        if sleep_hours < 0 or sleep_hours > 24:
            print("Error: sleep_hours must be between 0 and 24")
            return False

        if vyvanse_time is not None:
            if not self._validate_time_format(vyvanse_time):
                print("Error: vyvanse_time must be in HH:MM format (e.g., '08:30')")
                return False

        if entry_date is None:
            entry_date = self.today

        # Check if entry already exists for this date
        date_str = entry_date.isoformat()
        existing_index = None
        for i, entry in enumerate(self.health_log["entries"]):
            if entry["date"] == date_str:
                existing_index = i
                break

        # Create entry
        entry = {
            "date": date_str,
            "day_of_week": entry_date.strftime("%A"),
            "energy_level": energy_level,
            "sleep_hours": sleep_hours,
            "vyvanse_time": vyvanse_time,
            "notes": notes,
            "logged_at": datetime.now().isoformat()
        }

        # Update or append entry
        if existing_index is not None:
            self.health_log["entries"][existing_index] = entry
        else:
            self.health_log["entries"].append(entry)

        # Sort entries by date (most recent first)
        self.health_log["entries"].sort(key=lambda x: x["date"], reverse=True)

        return self._save_health_log()

    def _validate_time_format(self, time_str: str) -> bool:
        """
        Validate time string is in HH:MM format.

        Args:
            time_str: Time string to validate

        Returns:
            True if valid, False otherwise.
        """
        try:
            time.fromisoformat(time_str)
            return True
        except (ValueError, TypeError):
            return False

    def get_entry(self, entry_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        Get health entry for a specific date.

        Args:
            entry_date: Date to retrieve. Defaults to today.

        Returns:
            Entry dictionary if found, None otherwise.
        """
        if entry_date is None:
            entry_date = self.today

        date_str = entry_date.isoformat()
        for entry in self.health_log["entries"]:
            if entry["date"] == date_str:
                return entry

        return None

    def get_recent_entries(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get entries from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of entries sorted by date (most recent first).
        """
        cutoff_date = self.today - timedelta(days=days - 1)
        cutoff_str = cutoff_date.isoformat()

        recent = [
            entry for entry in self.health_log["entries"]
            if entry["date"] >= cutoff_str
        ]

        return recent

    def calculate_averages(self, days: int = 7) -> Dict[str, float]:
        """
        Calculate 7-day averages for health metrics.

        Args:
            days: Number of days to calculate averages over

        Returns:
            Dictionary with average values for energy_level and sleep_hours.
        """
        entries = self.get_recent_entries(days)

        if not entries:
            return {
                "avg_energy_level": 0.0,
                "avg_sleep_hours": 0.0,
                "sample_size": 0
            }

        total_energy = sum(e["energy_level"] for e in entries)
        total_sleep = sum(e["sleep_hours"] for e in entries)
        count = len(entries)

        return {
            "avg_energy_level": round(total_energy / count, 1),
            "avg_sleep_hours": round(total_sleep / count, 1),
            "sample_size": count
        }

    def identify_patterns(self, min_days: int = 14) -> Dict[str, Any]:
        """
        Identify patterns in health data.

        Analyzes day-of-week patterns, correlations between sleep and energy,
        and optimal medication timing.

        Args:
            min_days: Minimum days of data required for pattern detection

        Returns:
            Dictionary with identified patterns and insights.
        """
        entries = self.get_recent_entries(days=90)  # Look back up to 90 days

        if len(entries) < min_days:
            return {
                "has_sufficient_data": False,
                "sample_size": len(entries),
                "required_size": min_days,
                "message": f"Need at least {min_days} days of data for pattern detection. Currently have {len(entries)} days."
            }

        # Group by day of week
        day_stats = defaultdict(lambda: {"energy": [], "sleep": []})
        for entry in entries:
            day = entry["day_of_week"]
            day_stats[day]["energy"].append(entry["energy_level"])
            day_stats[day]["sleep"].append(entry["sleep_hours"])

        # Calculate averages by day
        day_averages = {}
        for day, stats in day_stats.items():
            if stats["energy"]:
                day_averages[day] = {
                    "avg_energy": round(sum(stats["energy"]) / len(stats["energy"]), 1),
                    "avg_sleep": round(sum(stats["sleep"]) / len(stats["sleep"]), 1),
                    "sample_size": len(stats["energy"])
                }

        # Find best and worst days
        if day_averages:
            sorted_days = sorted(day_averages.items(), key=lambda x: x[1]["avg_energy"])
            worst_day = sorted_days[0]
            best_day = sorted_days[-1]
        else:
            worst_day = None
            best_day = None

        # Sleep-energy correlation
        sleep_energy_correlation = self._calculate_sleep_energy_correlation(entries)

        # Vyvanse timing analysis
        vyvanse_analysis = self._analyze_vyvanse_timing(entries)

        # Generate insights
        insights = []
        if worst_day and best_day:
            if worst_day[1]["avg_energy"] < 5:
                insights.append(f"Energy typically low on {worst_day[0]} (avg: {worst_day[1]['avg_energy']}/10)")
            if best_day[1]["avg_energy"] >= 7:
                insights.append(f"Energy typically high on {best_day[0]} (avg: {best_day[1]['avg_energy']}/10)")

        if sleep_energy_correlation["correlation"] == "strong":
            insights.append(f"Strong correlation: {sleep_energy_correlation['relationship']}")

        if vyvanse_analysis["has_data"] and vyvanse_analysis["optimal_time"]:
            insights.append(f"Optimal medication timing appears to be {vyvanse_analysis['optimal_time']}")

        return {
            "has_sufficient_data": True,
            "sample_size": len(entries),
            "day_of_week_patterns": day_averages,
            "best_energy_day": best_day[0] if best_day else None,
            "worst_energy_day": worst_day[0] if worst_day else None,
            "sleep_energy_correlation": sleep_energy_correlation,
            "vyvanse_timing": vyvanse_analysis,
            "insights": insights
        }

    def _calculate_sleep_energy_correlation(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate correlation between sleep hours and energy levels.

        Args:
            entries: List of health log entries

        Returns:
            Dictionary with correlation analysis.
        """
        if len(entries) < 5:
            return {"correlation": "insufficient_data", "relationship": "Need more data"}

        # Simple correlation: compare high sleep vs low sleep days
        high_sleep_days = [e for e in entries if e["sleep_hours"] >= 7.5]
        low_sleep_days = [e for e in entries if e["sleep_hours"] < 6]

        if high_sleep_days and low_sleep_days:
            avg_energy_high_sleep = sum(e["energy_level"] for e in high_sleep_days) / len(high_sleep_days)
            avg_energy_low_sleep = sum(e["energy_level"] for e in low_sleep_days) / len(low_sleep_days)

            difference = avg_energy_high_sleep - avg_energy_low_sleep

            if difference >= 2.0:
                return {
                    "correlation": "strong",
                    "relationship": f"Good sleep (7.5+ hrs) → {difference:.1f} points higher energy",
                    "avg_energy_high_sleep": round(avg_energy_high_sleep, 1),
                    "avg_energy_low_sleep": round(avg_energy_low_sleep, 1)
                }
            elif difference >= 1.0:
                return {
                    "correlation": "moderate",
                    "relationship": f"Sleep affects energy (+{difference:.1f} points with good sleep)",
                    "avg_energy_high_sleep": round(avg_energy_high_sleep, 1),
                    "avg_energy_low_sleep": round(avg_energy_low_sleep, 1)
                }

        return {
            "correlation": "weak",
            "relationship": "No clear sleep-energy correlation detected"
        }

    def _analyze_vyvanse_timing(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze Vyvanse timing patterns and effectiveness.

        Args:
            entries: List of health log entries

        Returns:
            Dictionary with Vyvanse timing analysis.
        """
        entries_with_vyvanse = [e for e in entries if e.get("vyvanse_time")]

        if not entries_with_vyvanse:
            return {
                "has_data": False,
                "message": "No Vyvanse timing data available"
            }

        # Group by time and calculate average energy
        time_energy = defaultdict(list)
        for entry in entries_with_vyvanse:
            time_energy[entry["vyvanse_time"]].append(entry["energy_level"])

        # Calculate averages
        time_averages = {
            time_str: round(sum(energies) / len(energies), 1)
            for time_str, energies in time_energy.items()
        }

        # Find optimal time
        if time_averages:
            optimal_time = max(time_averages.items(), key=lambda x: x[1])
            return {
                "has_data": True,
                "sample_size": len(entries_with_vyvanse),
                "time_averages": time_averages,
                "optimal_time": optimal_time[0],
                "optimal_avg_energy": optimal_time[1],
                "message": f"Best results with {optimal_time[0]} timing (avg energy: {optimal_time[1]}/10)"
            }

        return {
            "has_data": True,
            "sample_size": len(entries_with_vyvanse),
            "message": "Insufficient data for timing optimization"
        }

    def get_current_state_assessment(self) -> Dict[str, Any]:
        """
        Get current health state assessment with recommendations.

        Returns:
            Dictionary with current state and task recommendations.
        """
        today_entry = self.get_entry()
        recent_avg = self.calculate_averages(days=7)
        patterns = self.identify_patterns()

        assessment = {
            "date": self.today.isoformat(),
            "day_of_week": self.today.strftime("%A"),
            "has_todays_data": today_entry is not None,
            "current_energy": today_entry["energy_level"] if today_entry else None,
            "current_sleep": today_entry["sleep_hours"] if today_entry else None,
            "vyvanse_time": today_entry.get("vyvanse_time") if today_entry else None,
            "seven_day_avg": recent_avg,
            "patterns": patterns if patterns.get("has_sufficient_data") else None
        }

        # Generate recommendations
        recommendations = []
        if today_entry:
            energy = today_entry["energy_level"]
            if energy >= 8:
                recommendations.append("High energy - ideal for deep work and complex tasks")
            elif energy >= 6:
                recommendations.append("Good energy - suitable for most tasks")
            elif energy >= 4:
                recommendations.append("Moderate energy - focus on lighter tasks and admin work")
            else:
                recommendations.append("Low energy - prioritize rest and simple tasks")

            # Vyvanse peak timing (typically 2-3 hours after dose)
            if today_entry.get("vyvanse_time"):
                vyvanse_dt = datetime.combine(self.today, time.fromisoformat(today_entry["vyvanse_time"]))
                peak_start = vyvanse_dt + timedelta(hours=2)
                peak_end = vyvanse_dt + timedelta(hours=4)
                recommendations.append(
                    f"Peak focus time: {peak_start.strftime('%I:%M %p')} - {peak_end.strftime('%I:%M %p')}"
                )

        # Pattern-based recommendations
        if patterns and patterns.get("has_sufficient_data"):
            if patterns.get("worst_energy_day") == self.today.strftime("%A"):
                recommendations.append(f"Historically low energy on {self.today.strftime('%A')} - adjust expectations")
            if patterns.get("best_energy_day") == self.today.strftime("%A"):
                recommendations.append(f"Typically high energy on {self.today.strftime('%A')} - great day for challenges")

        assessment["recommendations"] = recommendations

        return assessment
