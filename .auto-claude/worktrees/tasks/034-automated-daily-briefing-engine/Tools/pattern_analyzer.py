"""
PatternAnalyzer - Module for tracking and analyzing task completion patterns.

This module tracks what tasks users complete on different days and times,
identifies recurring patterns, and provides insights to improve briefing relevance.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, time, timedelta
from collections import defaultdict
import re


class PatternAnalyzer:
    """
    Tracks and analyzes task completion patterns over time.

    Stores task completion history in State/BriefingPatterns.json and provides
    pattern analysis to identify when users typically complete certain types of tasks.
    """

    def __init__(self, state_dir: Optional[str] = None):
        """
        Initialize the PatternAnalyzer.

        Args:
            state_dir: Path to the State directory. Defaults to ./State relative to cwd.
        """
        if state_dir is None:
            state_dir = os.path.join(os.getcwd(), "State")

        self.state_dir = Path(state_dir)
        self.patterns_path = self.state_dir / "BriefingPatterns.json"
        self.today = date.today()

        # Ensure State directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Load existing patterns
        self.patterns_data = self._load_patterns()

    def _load_patterns(self) -> Dict[str, Any]:
        """
        Load patterns data from JSON file.

        Returns:
            Dictionary with patterns data structure.
        """
        if not self.patterns_path.exists():
            return {
                "task_completions": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }

        try:
            with open(self.patterns_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading BriefingPatterns.json: {e}")
            return {
                "task_completions": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                    "load_error": str(e)
                }
            }

    def _save_patterns(self) -> bool:
        """
        Save patterns data to JSON file.

        Returns:
            True if save successful, False otherwise.
        """
        try:
            self.patterns_data["metadata"]["last_updated"] = datetime.now().isoformat()
            with open(self.patterns_path, 'w', encoding='utf-8') as f:
                json.dump(self.patterns_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error: Failed to save BriefingPatterns.json: {e}")
            return False

    def record_task_completion(
        self,
        task_title: str,
        task_category: Optional[str] = None,
        completion_time: Optional[datetime] = None,
        completion_date: Optional[date] = None
    ) -> bool:
        """
        Record a task completion event.

        Args:
            task_title: Title/description of the completed task
            task_category: Category (e.g., 'work', 'personal', 'admin', 'deep_work')
            completion_time: Time when task was completed. Defaults to now.
            completion_date: Date when task was completed. Defaults to today.

        Returns:
            True if recorded successfully, False otherwise.
        """
        if not task_title or not task_title.strip():
            print("Error: task_title cannot be empty")
            return False

        if completion_time is None:
            completion_time = datetime.now()

        if completion_date is None:
            completion_date = self.today

        # Infer category if not provided
        if task_category is None:
            task_category = self._infer_task_category(task_title)

        # Create completion record
        completion = {
            "task_title": task_title.strip(),
            "task_category": task_category,
            "completion_date": completion_date.isoformat(),
            "completion_time": completion_time.strftime("%H:%M"),
            "day_of_week": completion_date.strftime("%A"),
            "hour": completion_time.hour,
            "time_of_day": self._classify_time_of_day(completion_time.hour),
            "recorded_at": datetime.now().isoformat()
        }

        # Add to completions
        self.patterns_data["task_completions"].append(completion)

        # Keep only last 180 days of data (6 months)
        cutoff_date = (self.today - timedelta(days=180)).isoformat()
        self.patterns_data["task_completions"] = [
            c for c in self.patterns_data["task_completions"]
            if c["completion_date"] >= cutoff_date
        ]

        # Sort by date (most recent first)
        self.patterns_data["task_completions"].sort(
            key=lambda x: (x["completion_date"], x["completion_time"]),
            reverse=True
        )

        return self._save_patterns()

    def _infer_task_category(self, task_title: str) -> str:
        """
        Infer task category from task title using keyword matching.

        Args:
            task_title: Task title to analyze

        Returns:
            Inferred category string.
        """
        title_lower = task_title.lower()

        # Deep work indicators
        deep_work_keywords = [
            'design', 'architect', 'research', 'implement', 'build', 'develop',
            'code', 'write', 'create', 'analyze', 'plan', 'refactor', 'optimize'
        ]

        # Admin work indicators
        admin_keywords = [
            'email', 'meeting', 'standup', 'status', 'report', 'timesheet',
            'expense', 'submit', 'review', 'respond', 'schedule', 'calendar',
            'update', 'fill', 'send'
        ]

        # Personal indicators
        personal_keywords = [
            'call', 'personal', 'home', 'family', 'health', 'appointment',
            'grocery', 'shopping', 'errands', 'pay', 'bills'
        ]

        # Check for keyword matches
        if any(keyword in title_lower for keyword in deep_work_keywords):
            return 'deep_work'
        elif any(keyword in title_lower for keyword in admin_keywords):
            return 'admin'
        elif any(keyword in title_lower for keyword in personal_keywords):
            return 'personal'

        # Default to general
        return 'general'

    def _classify_time_of_day(self, hour: int) -> str:
        """
        Classify hour into time of day category.

        Args:
            hour: Hour of day (0-23)

        Returns:
            Time of day classification.
        """
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 21:
            return 'evening'
        else:
            return 'night'

    def get_completions(
        self,
        days: int = 30,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get task completions from the last N days.

        Args:
            days: Number of days to look back
            category: Filter by category (optional)

        Returns:
            List of completion records.
        """
        cutoff_date = (self.today - timedelta(days=days)).isoformat()
        completions = [
            c for c in self.patterns_data["task_completions"]
            if c["completion_date"] >= cutoff_date
        ]

        if category:
            completions = [c for c in completions if c["task_category"] == category]

        return completions

    def identify_patterns(self, min_days: int = 14) -> Dict[str, Any]:
        """
        Identify recurring patterns in task completions.

        Analyzes day-of-week patterns, time-of-day patterns, and category patterns.
        Requires minimum data to ensure meaningful patterns.

        Args:
            min_days: Minimum days of data required for pattern detection

        Returns:
            Dictionary with identified patterns and insights.
        """
        # Get completions from last 90 days
        completions = self.get_completions(days=90)

        # Check if we have enough unique days
        unique_dates = set(c["completion_date"] for c in completions)
        if len(unique_dates) < min_days:
            return {
                "has_sufficient_data": False,
                "sample_size": len(unique_dates),
                "required_size": min_days,
                "message": f"Need at least {min_days} days of task completion data. Currently have {len(unique_dates)} days."
            }

        # Analyze patterns
        day_patterns = self._analyze_day_of_week_patterns(completions)
        time_patterns = self._analyze_time_of_day_patterns(completions)
        category_patterns = self._analyze_category_patterns(completions)
        insights = self._generate_insights(day_patterns, time_patterns, category_patterns)

        return {
            "has_sufficient_data": True,
            "sample_size": len(unique_dates),
            "total_completions": len(completions),
            "day_of_week_patterns": day_patterns,
            "time_of_day_patterns": time_patterns,
            "category_patterns": category_patterns,
            "insights": insights
        }

    def _analyze_day_of_week_patterns(
        self,
        completions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns by day of week.

        Args:
            completions: List of completion records

        Returns:
            Dictionary with day-of-week pattern analysis.
        """
        # Group by day of week and category
        day_category_stats = defaultdict(lambda: defaultdict(int))
        day_totals = defaultdict(int)

        for completion in completions:
            day = completion["day_of_week"]
            category = completion["task_category"]
            day_category_stats[day][category] += 1
            day_totals[day] += 1

        # Calculate percentages and identify dominant categories
        patterns = {}
        for day, total in day_totals.items():
            categories = day_category_stats[day]
            category_percentages = {
                cat: round((count / total) * 100, 1)
                for cat, count in categories.items()
            }

            # Find dominant category (if > 40% of completions)
            dominant_category = None
            max_percentage = 0
            for cat, pct in category_percentages.items():
                if pct > max_percentage:
                    max_percentage = pct
                    dominant_category = cat

            patterns[day] = {
                "total_completions": total,
                "category_distribution": category_percentages,
                "dominant_category": dominant_category if max_percentage > 40 else None,
                "dominant_percentage": max_percentage
            }

        return patterns

    def _analyze_time_of_day_patterns(
        self,
        completions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns by time of day.

        Args:
            completions: List of completion records

        Returns:
            Dictionary with time-of-day pattern analysis.
        """
        # Group by time of day and category
        time_category_stats = defaultdict(lambda: defaultdict(int))
        time_totals = defaultdict(int)

        for completion in completions:
            time_period = completion["time_of_day"]
            category = completion["task_category"]
            time_category_stats[time_period][category] += 1
            time_totals[time_period] += 1

        # Calculate percentages
        patterns = {}
        for time_period, total in time_totals.items():
            categories = time_category_stats[time_period]
            category_percentages = {
                cat: round((count / total) * 100, 1)
                for cat, count in categories.items()
            }

            # Find dominant category
            dominant_category = None
            max_percentage = 0
            for cat, pct in category_percentages.items():
                if pct > max_percentage:
                    max_percentage = pct
                    dominant_category = cat

            patterns[time_period] = {
                "total_completions": total,
                "category_distribution": category_percentages,
                "dominant_category": dominant_category if max_percentage > 40 else None,
                "dominant_percentage": max_percentage
            }

        return patterns

    def _analyze_category_patterns(
        self,
        completions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze overall category distribution patterns.

        Args:
            completions: List of completion records

        Returns:
            Dictionary with category pattern analysis.
        """
        category_stats = defaultdict(lambda: {
            "count": 0,
            "days": set(),
            "times": defaultdict(int)
        })

        for completion in completions:
            category = completion["task_category"]
            day = completion["day_of_week"]
            time_period = completion["time_of_day"]

            category_stats[category]["count"] += 1
            category_stats[category]["days"].add(day)
            category_stats[category]["times"][time_period] += 1

        # Calculate patterns
        total_completions = len(completions)
        patterns = {}

        for category, stats in category_stats.items():
            count = stats["count"]
            percentage = round((count / total_completions) * 100, 1)

            # Find preferred time of day for this category
            preferred_time = max(stats["times"].items(), key=lambda x: x[1])[0] if stats["times"] else None
            preferred_time_count = stats["times"][preferred_time] if preferred_time else 0
            preferred_time_percentage = round((preferred_time_count / count) * 100, 1) if count > 0 else 0

            # Find common days
            common_days = list(stats["days"])

            patterns[category] = {
                "total_completions": count,
                "percentage_of_total": percentage,
                "common_days": sorted(common_days),
                "preferred_time_of_day": preferred_time,
                "preferred_time_percentage": preferred_time_percentage
            }

        return patterns

    def _generate_insights(
        self,
        day_patterns: Dict[str, Any],
        time_patterns: Dict[str, Any],
        category_patterns: Dict[str, Any]
    ) -> List[str]:
        """
        Generate human-readable insights from patterns.

        Args:
            day_patterns: Day of week patterns
            time_patterns: Time of day patterns
            category_patterns: Category patterns

        Returns:
            List of insight strings.
        """
        insights = []

        # Day of week insights
        for day, data in day_patterns.items():
            if data["dominant_category"] and data["dominant_percentage"] > 50:
                insights.append(
                    f"{data['dominant_percentage']:.0f}% of tasks on {day} are {data['dominant_category']} "
                    f"({data['total_completions']} completions)"
                )

        # Time of day insights
        for time_period, data in time_patterns.items():
            if data["dominant_category"] and data["dominant_percentage"] > 50:
                insights.append(
                    f"You typically do {data['dominant_category']} tasks in the {time_period} "
                    f"({data['dominant_percentage']:.0f}%)"
                )

        # Category insights
        for category, data in category_patterns.items():
            if data["percentage_of_total"] > 30:
                insights.append(
                    f"{category.replace('_', ' ').title()} tasks make up {data['percentage_of_total']:.0f}% "
                    f"of your completions"
                )

            if data["preferred_time_of_day"] and data["preferred_time_percentage"] > 50:
                insights.append(
                    f"You prefer completing {category} tasks in the {data['preferred_time_of_day']} "
                    f"({data['preferred_time_percentage']:.0f}%)"
                )

        return insights

    def get_recommendations_for_context(
        self,
        current_day: Optional[str] = None,
        current_time_of_day: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get task recommendations based on historical patterns for current context.

        Args:
            current_day: Day of week (e.g., 'Monday'). Defaults to today.
            current_time_of_day: Time period (morning/afternoon/evening/night). Defaults to current time.

        Returns:
            Dictionary with recommendations based on patterns.
        """
        if current_day is None:
            current_day = self.today.strftime("%A")

        if current_time_of_day is None:
            current_hour = datetime.now().hour
            current_time_of_day = self._classify_time_of_day(current_hour)

        # Get patterns
        patterns = self.identify_patterns()

        if not patterns["has_sufficient_data"]:
            return {
                "has_recommendations": False,
                "reason": patterns["message"]
            }

        recommendations = []

        # Day-based recommendations
        day_patterns = patterns["day_of_week_patterns"]
        if current_day in day_patterns:
            day_data = day_patterns[current_day]
            if day_data["dominant_category"] and day_data["dominant_percentage"] > 40:
                recommendations.append({
                    "type": "day_pattern",
                    "category": day_data["dominant_category"],
                    "reason": f"You typically complete {day_data['dominant_category']} tasks on {current_day}",
                    "confidence": day_data["dominant_percentage"]
                })

        # Time-based recommendations
        time_patterns = patterns["time_of_day_patterns"]
        if current_time_of_day in time_patterns:
            time_data = time_patterns[current_time_of_day]
            if time_data["dominant_category"] and time_data["dominant_percentage"] > 40:
                recommendations.append({
                    "type": "time_pattern",
                    "category": time_data["dominant_category"],
                    "reason": f"You typically complete {time_data['dominant_category']} tasks in the {current_time_of_day}",
                    "confidence": time_data["dominant_percentage"]
                })

        return {
            "has_recommendations": len(recommendations) > 0,
            "current_context": {
                "day": current_day,
                "time_of_day": current_time_of_day
            },
            "recommendations": recommendations
        }


if __name__ == "__main__":
    # Example usage
    analyzer = PatternAnalyzer()

    print("PatternAnalyzer Example Usage")
    print("=" * 50)

    # Record some sample completions
    print("\n1. Recording task completions...")
    analyzer.record_task_completion(
        "Review PR for authentication",
        task_category="admin"
    )
    print("✓ Recorded task completion")

    # Get recent completions
    print("\n2. Recent completions (last 30 days):")
    completions = analyzer.get_completions(days=30)
    print(f"Total completions: {len(completions)}")

    # Try to identify patterns (will need more data)
    print("\n3. Identifying patterns...")
    patterns = analyzer.identify_patterns()
    if patterns["has_sufficient_data"]:
        print(f"Sample size: {patterns['sample_size']} days")
        print(f"Total completions: {patterns['total_completions']}")
        print("\nInsights:")
        for insight in patterns["insights"]:
            print(f"  • {insight}")
    else:
        print(f"⚠ {patterns['message']}")

    print("\n" + "=" * 50)
    print("PatternAnalyzer module ready!")
