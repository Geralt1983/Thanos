"""
BriefingEngine - Core class for generating intelligent daily briefings.

This module provides the main engine for gathering context from State files,
processing commitments and tasks, and preparing structured data for briefing
generation.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta
import json
import re

try:
    from jinja2 import Environment, FileSystemLoader, Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    from Tools.health_state_tracker import HealthStateTracker
    HEALTH_TRACKER_AVAILABLE = True
except ImportError:
    HEALTH_TRACKER_AVAILABLE = False

try:
    from Tools.pattern_analyzer import PatternAnalyzer
    PATTERN_ANALYZER_AVAILABLE = True
except ImportError:
    PATTERN_ANALYZER_AVAILABLE = False


class BriefingEngine:
    """
    Core engine for generating personalized daily briefings.

    Gathers data from State files (Commitments.md, ThisWeek.md, CurrentFocus.md),
    processes and structures the information, and prepares it for rendering.
    """

    def __init__(self, state_dir: Optional[str] = None, templates_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the BriefingEngine.

        Args:
            state_dir: Path to the State directory. Defaults to ./State relative to cwd.
            templates_dir: Path to the Templates directory. Defaults to ./Templates relative to cwd.
            config: Optional configuration dict for sections and other options.
        """
        if state_dir is None:
            state_dir = os.path.join(os.getcwd(), "State")
        if templates_dir is None:
            templates_dir = os.path.join(os.getcwd(), "Templates")

        self.state_dir = Path(state_dir)
        self.templates_dir = Path(templates_dir)
        self.today = date.today()
        self.config = config or {}

        # Initialize Jinja2 environment if available
        if JINJA2_AVAILABLE and self.templates_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self.jinja_env = None

        # Initialize HealthStateTracker if available
        if HEALTH_TRACKER_AVAILABLE:
            self.health_tracker = HealthStateTracker(state_dir=str(self.state_dir))
        else:
            self.health_tracker = None

        # Initialize PatternAnalyzer if available and enabled in config
        patterns_config = self.config.get("patterns", {})
        patterns_enabled = patterns_config.get("enabled", False)
        if PATTERN_ANALYZER_AVAILABLE and patterns_enabled:
            self.pattern_analyzer = PatternAnalyzer(state_dir=str(self.state_dir))
        else:
            self.pattern_analyzer = None

        # Register built-in section providers
        self._section_providers = self._register_builtin_sections()

    def gather_context(self) -> Dict[str, Any]:
        """
        Gather all context needed for briefing generation.

        Reads from State files and structures the data into a comprehensive
        briefing context dictionary.

        Returns:
            Dict containing structured briefing data with keys:
            - commitments: List of active commitments
            - this_week: This week's tasks and goals
            - current_focus: Current focus areas
            - today_date: Today's date
            - day_of_week: Day name (Monday, Tuesday, etc.)
            - is_weekend: Boolean indicating if today is weekend
            - metadata: Additional context about data sources
        """
        context = {
            "today_date": self.today.isoformat(),
            "day_of_week": self.today.strftime("%A"),
            "is_weekend": self.today.weekday() >= 5,  # Saturday=5, Sunday=6
            "commitments": self._read_commitments(),
            "this_week": self._read_this_week(),
            "current_focus": self._read_current_focus(),
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "state_dir": str(self.state_dir),
                "files_read": [],
                "files_missing": []
            }
        }

        return context

    def _read_commitments(self) -> List[Dict[str, Any]]:
        """
        Read and parse Commitments.md file.

        Returns:
            List of commitment dictionaries with parsed metadata.
        """
        file_path = self.state_dir / "Commitments.md"

        if not file_path.exists():
            self._mark_file_missing("Commitments.md")
            return []

        self._mark_file_read("Commitments.md")

        try:
            content = file_path.read_text(encoding='utf-8')
            return self._parse_commitments(content)
        except Exception as e:
            print(f"Warning: Error reading Commitments.md: {e}")
            return []

    def _parse_commitments(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse commitments from markdown content.

        Extracts commitments with their metadata (deadlines, priority, status).

        Args:
            content: Raw markdown content

        Returns:
            List of parsed commitment dictionaries
        """
        commitments = []

        # Split by headers (## or ###)
        sections = re.split(r'\n##+ ', content)

        for section in sections:
            if not section.strip():
                continue

            lines = section.split('\n')
            title = lines[0].strip()

            # Skip metadata sections
            if title.lower() in ['metadata', 'archive', 'completed']:
                continue

            # Look for task items (- [ ] or - [x])
            for line in lines[1:]:
                # Match checkbox items
                checkbox_match = re.match(r'^\s*-\s*\[([ xX])\]\s*(.+)$', line)
                if checkbox_match:
                    is_complete = checkbox_match.group(1).lower() == 'x'
                    task_text = checkbox_match.group(2).strip()

                    # Extract deadline if present (e.g., "Task name (due: 2024-01-15)")
                    deadline = None
                    deadline_match = re.search(r'\(due:\s*(\d{4}-\d{2}-\d{2})\)', task_text)
                    if deadline_match:
                        deadline = deadline_match.group(1)
                        task_text = re.sub(r'\s*\(due:\s*\d{4}-\d{2}-\d{2}\)', '', task_text)

                    commitments.append({
                        "title": task_text,
                        "category": title,
                        "is_complete": is_complete,
                        "deadline": deadline,
                        "raw_line": line.strip()
                    })

        return commitments

    def _read_this_week(self) -> Dict[str, Any]:
        """
        Read and parse ThisWeek.md file.

        Returns:
            Dictionary with this week's goals and tasks.
        """
        file_path = self.state_dir / "ThisWeek.md"

        if not file_path.exists():
            self._mark_file_missing("ThisWeek.md")
            return {
                "goals": [],
                "tasks": [],
                "notes": ""
            }

        self._mark_file_read("ThisWeek.md")

        try:
            content = file_path.read_text(encoding='utf-8')
            return self._parse_this_week(content)
        except Exception as e:
            print(f"Warning: Error reading ThisWeek.md: {e}")
            return {
                "goals": [],
                "tasks": [],
                "notes": ""
            }

    def _parse_this_week(self, content: str) -> Dict[str, Any]:
        """
        Parse this week's content from markdown.

        Args:
            content: Raw markdown content

        Returns:
            Dictionary with goals, tasks, and notes
        """
        result = {
            "goals": [],
            "tasks": [],
            "notes": ""
        }

        lines = content.split('\n')
        current_section = None

        for line in lines:
            # Detect section headers
            if line.startswith('##'):
                section_title = line.strip('#').strip().lower()
                if 'goal' in section_title:
                    current_section = 'goals'
                elif 'task' in section_title:
                    current_section = 'tasks'
                elif 'note' in section_title:
                    current_section = 'notes'
                else:
                    current_section = None
                continue

            # Parse items based on current section
            if current_section in ['goals', 'tasks']:
                # Match list items
                item_match = re.match(r'^\s*[-*]\s*\[([ xX])\]\s*(.+)$', line)
                if item_match:
                    is_complete = item_match.group(1).lower() == 'x'
                    text = item_match.group(2).strip()
                    result[current_section].append({
                        "text": text,
                        "is_complete": is_complete
                    })
                elif re.match(r'^\s*[-*]\s+(.+)$', line):
                    # Plain list item without checkbox
                    text = re.match(r'^\s*[-*]\s+(.+)$', line).group(1).strip()
                    result[current_section].append({
                        "text": text,
                        "is_complete": False
                    })
            elif current_section == 'notes' and line.strip():
                result['notes'] += line + '\n'

        result['notes'] = result['notes'].strip()
        return result

    def _read_current_focus(self) -> Dict[str, Any]:
        """
        Read and parse CurrentFocus.md file.

        Returns:
            Dictionary with current focus information.
        """
        file_path = self.state_dir / "CurrentFocus.md"

        if not file_path.exists():
            self._mark_file_missing("CurrentFocus.md")
            return {
                "focus_areas": [],
                "priorities": [],
                "content": ""
            }

        self._mark_file_read("CurrentFocus.md")

        try:
            content = file_path.read_text(encoding='utf-8')
            return self._parse_current_focus(content)
        except Exception as e:
            print(f"Warning: Error reading CurrentFocus.md: {e}")
            return {
                "focus_areas": [],
                "priorities": [],
                "content": ""
            }

    def _parse_current_focus(self, content: str) -> Dict[str, Any]:
        """
        Parse current focus from markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Dictionary with focus areas and priorities
        """
        result = {
            "focus_areas": [],
            "priorities": [],
            "content": content
        }

        lines = content.split('\n')
        current_section = None

        for line in lines:
            # Detect section headers
            if line.startswith('##'):
                section_title = line.strip('#').strip().lower()
                if 'focus' in section_title or 'area' in section_title:
                    current_section = 'focus_areas'
                elif 'priorit' in section_title:
                    current_section = 'priorities'
                else:
                    current_section = None
                continue

            # Parse list items
            if current_section:
                item_match = re.match(r'^\s*[-*]\s+(.+)$', line)
                if item_match:
                    text = item_match.group(1).strip()
                    result[current_section].append(text)

        return result

    def _mark_file_read(self, filename: str) -> None:
        """Track which files were successfully read."""
        # This will be used by gather_context to populate metadata
        pass

    def _mark_file_missing(self, filename: str) -> None:
        """Track which files were missing."""
        # This will be used by gather_context to populate metadata
        pass

    def get_active_commitments(self, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get only active (incomplete) commitments from the context.

        Args:
            context: Briefing context dict. If None, will gather fresh context.

        Returns:
            List of active commitments
        """
        if context is None:
            context = self.gather_context()

        return [c for c in context.get("commitments", []) if not c.get("is_complete", False)]

    def get_pending_tasks(self, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get pending tasks from this week's goals.

        Args:
            context: Briefing context dict. If None, will gather fresh context.

        Returns:
            List of pending tasks
        """
        if context is None:
            context = self.gather_context()

        this_week = context.get("this_week", {})
        tasks = this_week.get("tasks", [])

        return [t for t in tasks if not t.get("is_complete", False)]

    def rank_priorities(
        self,
        context: Optional[Dict[str, Any]] = None,
        energy_level: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank all tasks and commitments by priority.

        Considers multiple factors:
        - Deadline urgency (due today > due this week > backlog)
        - Day of week (weekday vs weekend)
        - Task category (work vs personal)
        - Energy level (optional, affects recommendations)

        Args:
            context: Briefing context dict. If None, will gather fresh context.
            energy_level: Optional energy level (1-10). Used for task recommendations.

        Returns:
            List of prioritized items, sorted by priority score (highest first).
            Each item includes 'priority_score', 'priority_reason', and 'urgency_level'.
        """
        if context is None:
            context = self.gather_context()

        # Gather all actionable items
        items = []

        # Add active commitments
        for commitment in self.get_active_commitments(context):
            items.append({
                "type": "commitment",
                "source": commitment,
                "title": commitment["title"],
                "category": commitment.get("category", "Uncategorized"),
                "deadline": commitment.get("deadline"),
                "is_weekend": context["is_weekend"]
            })

        # Add pending tasks from this week
        for task in self.get_pending_tasks(context):
            items.append({
                "type": "task",
                "source": task,
                "title": task["text"],
                "category": "This Week",
                "deadline": None,  # ThisWeek tasks don't have explicit deadlines
                "is_weekend": context["is_weekend"]
            })

        # Add priorities from CurrentFocus
        current_focus = context.get("current_focus", {})
        for priority in current_focus.get("priorities", []):
            items.append({
                "type": "priority",
                "source": {"text": priority},
                "title": priority,
                "category": "Current Focus",
                "deadline": None,
                "is_weekend": context["is_weekend"]
            })

        # Calculate priority scores for each item
        for item in items:
            score, reason, urgency = self._calculate_priority_score(
                item,
                context["day_of_week"],
                context["is_weekend"],
                energy_level
            )
            item["priority_score"] = score
            item["priority_reason"] = reason
            item["urgency_level"] = urgency

        # Sort by priority score (descending)
        items.sort(key=lambda x: x["priority_score"], reverse=True)

        return items

    def _calculate_priority_score(
        self,
        item: Dict[str, Any],
        day_of_week: str,
        is_weekend: bool,
        energy_level: Optional[int] = None
    ) -> Tuple[float, str, str]:
        """
        Calculate priority score for an item.

        Args:
            item: Item dictionary with title, category, deadline, etc.
            day_of_week: Current day name
            is_weekend: Whether today is a weekend
            energy_level: Optional energy level (1-10)

        Returns:
            Tuple of (score, reason, urgency_level)
            - score: Float priority score (higher = more urgent)
            - reason: Human-readable explanation of priority
            - urgency_level: "critical", "high", "medium", or "low"
        """
        score = 0.0
        reasons = []
        urgency_level = "medium"

        # 1. Deadline-based urgency (most important factor)
        deadline = item.get("deadline")
        if deadline:
            try:
                deadline_date = date.fromisoformat(deadline)
                days_until = (deadline_date - self.today).days

                if days_until < 0:
                    score += 100
                    reasons.append(f"OVERDUE by {abs(days_until)} days")
                    urgency_level = "critical"
                elif days_until == 0:
                    score += 90
                    reasons.append("due TODAY")
                    urgency_level = "critical"
                elif days_until == 1:
                    score += 75
                    reasons.append("due tomorrow")
                    urgency_level = "high"
                elif days_until <= 3:
                    score += 60
                    reasons.append(f"due in {days_until} days")
                    urgency_level = "high"
                elif days_until <= 7:
                    score += 40
                    reasons.append("due this week")
                    urgency_level = "medium"
                else:
                    score += 20
                    reasons.append(f"due in {days_until} days")
            except (ValueError, TypeError):
                pass

        # 2. Item type priority
        item_type = item.get("type", "task")
        if item_type == "priority":
            score += 35
            reasons.append("current focus")
        elif item_type == "commitment":
            score += 25
            reasons.append("active commitment")
        else:  # task
            score += 15
            reasons.append("this week task")

        # 3. Weekend vs weekday context
        category_lower = item.get("category", "").lower()
        is_work_related = any(keyword in category_lower for keyword in
                              ["work", "project", "team", "meeting", "client"])

        if is_weekend:
            if is_work_related:
                # Deprioritize work items on weekends unless urgent
                if urgency_level in ["critical", "high"]:
                    reasons.append("urgent work (weekend)")
                else:
                    score -= 30
                    reasons.append("work item (weekend - lower priority)")
            else:
                score += 10
                reasons.append("personal time")
        else:  # weekday
            if is_work_related:
                score += 20
                reasons.append("work priority (weekday)")
            else:
                score += 5

        # 4. Energy level considerations (if provided)
        if energy_level is not None:
            # Analyze task title for complexity hints
            title_lower = item.get("title", "").lower()
            is_complex = any(word in title_lower for word in
                           ["design", "architect", "plan", "research", "analyze", "write"])
            is_simple = any(word in title_lower for word in
                          ["send", "email", "call", "schedule", "update", "review"])

            if energy_level >= 7:  # High energy
                if is_complex:
                    score += 15
                    reasons.append("good energy for complex work")
            elif energy_level <= 4:  # Low energy
                if is_simple:
                    score += 10
                    reasons.append("manageable with current energy")
                elif is_complex:
                    score -= 20
                    reasons.append("may need higher energy")

        # 5. Day-of-week patterns
        if day_of_week == "Monday":
            if "meeting" in category_lower or "standup" in item.get("title", "").lower():
                score += 10
                reasons.append("Monday meeting")
        elif day_of_week == "Friday":
            if any(word in item.get("title", "").lower() for word in
                  ["admin", "expense", "timesheet", "report", "update"]):
                score += 10
                reasons.append("Friday admin task")

        # 6. Pattern-based adjustments (subtle influence from learned patterns)
        pattern_boost, pattern_reasons = self._get_pattern_boost(item, day_of_week)
        if pattern_boost > 0:
            score += pattern_boost
            reasons.extend(pattern_reasons)

        # Determine final urgency level based on score
        if score >= 90:
            urgency_level = "critical"
        elif score >= 60:
            urgency_level = "high"
        elif score >= 30:
            urgency_level = "medium"
        else:
            urgency_level = "low"

        # Format reason string
        reason = "; ".join(reasons) if reasons else "standard priority"

        return score, reason, urgency_level

    def get_top_priorities(
        self,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 3,
        energy_level: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the top N priority items for today.

        Args:
            context: Briefing context dict. If None, will gather fresh context.
            limit: Maximum number of priorities to return (default: 3)
            energy_level: Optional energy level (1-10) for task recommendations

        Returns:
            List of top priority items, ranked by urgency and relevance
        """
        ranked_items = self.rank_priorities(context, energy_level)
        return ranked_items[:limit]

    def _get_pattern_boost(
        self,
        item: Dict[str, Any],
        day_of_week: str,
        current_time_of_day: Optional[str] = None
    ) -> Tuple[float, List[str]]:
        """
        Calculate pattern-based priority boost for an item.

        Uses historical completion patterns to provide a subtle boost to tasks
        that are typically completed on this day/time. Pattern influence is
        subtle and does not override deadline urgency.

        Args:
            item: Task/commitment/priority item
            day_of_week: Current day name (e.g., 'Monday')
            current_time_of_day: Current time period (morning/afternoon/evening/night)

        Returns:
            Tuple of (boost_score, reasons)
            - boost_score: Float boost to add to priority score (typically 0-15)
            - reasons: List of human-readable explanations for the boost
        """
        # Return no boost if pattern analyzer not available or not initialized
        if not self.pattern_analyzer:
            return 0.0, []

        boost = 0.0
        reasons = []

        # Get pattern influence level from config
        patterns_config = self.config.get("patterns", {})
        influence_level = patterns_config.get("influence_level", "medium")

        # Map influence level to max boost
        max_boost_map = {
            "low": 5.0,
            "medium": 10.0,
            "high": 15.0
        }
        max_boost = max_boost_map.get(influence_level, 10.0)

        # Get task category from item (needed for special cases even without patterns)
        task_category = self._infer_task_category_from_item(item)

        try:
            # Get pattern recommendations for current context
            if current_time_of_day is None:
                current_hour = datetime.now().hour
                current_time_of_day = self._classify_time_of_day_for_patterns(current_hour)

            recommendations = self.pattern_analyzer.get_recommendations_for_context(
                current_day=day_of_week,
                current_time_of_day=current_time_of_day
            )

            # Check if we have sufficient pattern data
            if recommendations.get("has_recommendations", False):
                # Check day-based patterns
                for rec in recommendations.get("recommendations", []):
                    if rec["type"] == "day_pattern" and rec["category"] == task_category:
                        # Scale boost by confidence (40-100% → 0.4-1.0 of max_boost)
                        confidence_ratio = rec["confidence"] / 100.0
                        day_boost = max_boost * confidence_ratio * 0.5  # 50% weight for day pattern
                        boost += day_boost
                        reasons.append(f"typically done on {day_of_week}s ({rec['confidence']:.0f}% pattern)")

                    elif rec["type"] == "time_pattern" and rec["category"] == task_category:
                        # Scale boost by confidence
                        confidence_ratio = rec["confidence"] / 100.0
                        time_boost = max_boost * confidence_ratio * 0.5  # 50% weight for time pattern
                        boost += time_boost
                        reasons.append(f"typically done in {current_time_of_day} ({rec['confidence']:.0f}% pattern)")

                # Special case: Monday energy awareness (requires pattern data)
                if day_of_week == "Monday":
                    patterns = self.pattern_analyzer.identify_patterns()
                    if patterns.get("has_sufficient_data", False):
                        day_patterns = patterns.get("day_of_week_patterns", {})
                        monday_data = day_patterns.get("Monday", {})

                        # If admin tasks dominate Mondays, boost admin tasks slightly
                        if monday_data.get("dominant_category") == "admin":
                            if task_category == "admin":
                                boost += max_boost * 0.2  # 20% of max boost
                                reasons.append("Monday lighter tasks pattern")

        except Exception as e:
            # Gracefully handle any pattern analysis errors
            print(f"Warning: Error calculating pattern boost: {e}")

        # Special case: Friday admin tasks (always apply, even without pattern data)
        # This is a well-known pattern that most people follow
        if day_of_week == "Friday" and task_category == "admin":
            if not any("Friday" in r for r in reasons):  # Don't double-boost
                boost += max_boost * 0.3  # 30% of max boost
                reasons.append("Friday admin pattern")

        # Cap the boost to max_boost
        boost = min(boost, max_boost)

        return boost, reasons

    def _classify_time_of_day_for_patterns(self, hour: int) -> str:
        """
        Classify hour into time period for pattern matching.

        Args:
            hour: Hour of day (0-23)

        Returns:
            Time period string: 'morning', 'afternoon', 'evening', or 'night'
        """
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"

    def _infer_task_category_from_item(self, item: Dict[str, Any]) -> str:
        """
        Infer pattern category from a task/commitment item.

        Uses title and category to determine what type of task this is
        for pattern matching purposes.

        Args:
            item: Task/commitment/priority item

        Returns:
            Category string (work, personal, admin, learning, health, household)
        """
        title = item.get("title", "").lower()
        category = item.get("category", "").lower()

        # Check for admin keywords first (most specific)
        admin_keywords = ["admin", "email", "expense", "timesheet", "report", "paperwork",
                         "invoice", "schedule", "calendar", "organize", "file"]
        if any(keyword in title or keyword in category for keyword in admin_keywords):
            return "admin"

        # Check for health keywords before work (to avoid "workout" matching "work")
        health_keywords = ["health", "exercise", "workout", "gym", "run", "walk", "doctor",
                          "medical", "therapy", "meditation"]
        if any(keyword in title or keyword in category for keyword in health_keywords):
            return "health"

        # Check for work keywords
        work_keywords = ["work", "project", "meeting", "client", "team", "code", "design",
                        "develop", "fix", "bug", "feature", "review"]
        if any(keyword in title or keyword in category for keyword in work_keywords):
            return "work"

        # Check for learning keywords
        learning_keywords = ["learn", "study", "read", "course", "tutorial", "research",
                           "practice", "training"]
        if any(keyword in title or keyword in category for keyword in learning_keywords):
            return "learning"

        # Check for household keywords
        household_keywords = ["clean", "laundry", "groceries", "shopping", "cooking", "repair",
                            "maintenance", "errand"]
        if any(keyword in title or keyword in category for keyword in household_keywords):
            return "household"

        # Default to personal
        return "personal"

    def _classify_task_type(self, item: Dict[str, Any]) -> str:
        """
        Classify a task as 'deep_work', 'admin', or 'general'.

        Analyzes task title and category to determine cognitive load.

        Args:
            item: Task/commitment/priority item

        Returns:
            One of: 'deep_work', 'admin', 'general'
        """
        title_lower = item.get("title", "").lower()
        category_lower = item.get("category", "").lower()

        # Deep work keywords (require high cognitive load)
        deep_work_keywords = [
            "design", "architect", "plan", "research", "analyze", "write",
            "develop", "implement", "refactor", "debug", "solve", "create",
            "strategy", "prototype", "algorithm", "optimize", "complex"
        ]

        # Admin/light work keywords (lower cognitive load)
        admin_keywords = [
            "send", "email", "call", "schedule", "update", "review", "respond",
            "organize", "file", "expense", "timesheet", "report", "status",
            "meeting", "standup", "sync", "check-in", "admin", "coordinate"
        ]

        # Check for deep work
        if any(keyword in title_lower for keyword in deep_work_keywords):
            return "deep_work"

        # Check for admin
        if any(keyword in title_lower for keyword in admin_keywords):
            return "admin"

        # Check category for hints
        if any(keyword in category_lower for keyword in ["admin", "meeting", "email"]):
            return "admin"

        return "general"

    def _calculate_peak_focus_time(self, vyvanse_time: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Calculate peak focus window based on Vyvanse timing.

        Vyvanse typically peaks 2-4 hours after dose.

        Args:
            vyvanse_time: Time medication was taken (HH:MM format)

        Returns:
            Dictionary with peak_start, peak_end (datetime), or None if no vyvanse_time
        """
        if not vyvanse_time:
            return None

        try:
            from datetime import time as dt_time
            vyvanse_dt = datetime.combine(self.today, dt_time.fromisoformat(vyvanse_time))
            peak_start = vyvanse_dt + timedelta(hours=2)
            peak_end = vyvanse_dt + timedelta(hours=4)

            return {
                "peak_start": peak_start,
                "peak_end": peak_end,
                "peak_start_str": peak_start.strftime("%I:%M %p"),
                "peak_end_str": peak_end.strftime("%I:%M %p"),
                "is_peak_now": peak_start <= datetime.now() <= peak_end
            }
        except (ValueError, TypeError):
            return None

    def get_health_aware_recommendations(
        self,
        context: Optional[Dict[str, Any]] = None,
        health_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get task recommendations based on current health state.

        Integrates energy level, sleep quality, and medication timing to provide
        intelligent task recommendations and scheduling advice.

        Args:
            context: Briefing context dict. If None, will gather fresh context.
            health_state: Health state assessment from HealthStateTracker.
                         If None and health_tracker available, will get current state.

        Returns:
            Dictionary with:
            - recommended_tasks: Tasks suited to current energy
            - deep_work_tasks: High-value complex tasks (if energy permits)
            - admin_tasks: Light tasks suitable for low energy
            - reschedule_recommendations: Tasks to reschedule if energy too low
            - peak_focus_window: Optimal focus time based on medication
            - reasoning: Explanation of recommendations
        """
        if context is None:
            context = self.gather_context()

        # Get health state
        if health_state is None and self.health_tracker:
            health_state = self.health_tracker.get_current_state_assessment()

        # Extract key health metrics
        energy_level = None
        vyvanse_time = None
        if health_state and health_state.get("has_todays_data"):
            energy_level = health_state.get("current_energy")
            vyvanse_time = health_state.get("vyvanse_time")

        # Get all ranked priorities
        all_priorities = self.rank_priorities(context, energy_level)

        # Classify tasks
        deep_work_tasks = []
        admin_tasks = []
        general_tasks = []

        for item in all_priorities:
            task_type = self._classify_task_type(item)
            item["task_type"] = task_type

            if task_type == "deep_work":
                deep_work_tasks.append(item)
            elif task_type == "admin":
                admin_tasks.append(item)
            else:
                general_tasks.append(item)

        # Calculate peak focus window
        peak_focus = self._calculate_peak_focus_time(vyvanse_time)

        # Generate recommendations based on energy level
        recommended_tasks = []
        reschedule_recommendations = []
        reasoning = []

        if energy_level is not None:
            if energy_level >= 8:
                # High energy - recommend deep work
                reasoning.append("🚀 High energy detected - ideal for deep work and complex tasks")
                recommended_tasks = deep_work_tasks[:3] + general_tasks[:2]

                if peak_focus and peak_focus["is_peak_now"]:
                    reasoning.append(f"⚡ Currently in peak focus window ({peak_focus['peak_start_str']} - {peak_focus['peak_end_str']})")
                elif peak_focus:
                    reasoning.append(f"⏰ Peak focus time coming: {peak_focus['peak_start_str']} - {peak_focus['peak_end_str']}")

            elif energy_level >= 6:
                # Good energy - mix of deep work and general tasks
                reasoning.append("✅ Good energy - suitable for most tasks, prioritize important work")
                recommended_tasks = (deep_work_tasks[:2] + general_tasks[:2] + admin_tasks[:1])[:5]

            elif energy_level >= 4:
                # Moderate energy - focus on lighter tasks
                reasoning.append("⚠️ Moderate energy - focus on lighter tasks and admin work")
                recommended_tasks = admin_tasks[:3] + general_tasks[:2]

                # Identify deep work tasks that should be rescheduled
                for task in deep_work_tasks:
                    if task.get("urgency_level") in ["critical", "high"]:
                        reschedule_recommendations.append({
                            "task": task,
                            "reason": "Important complex task requires higher energy - consider rescheduling to peak focus time"
                        })

            else:
                # Low energy - only admin/light tasks
                reasoning.append("🔋 Low energy - prioritize rest and simple administrative tasks only")
                recommended_tasks = admin_tasks[:3]

                # All deep work should be rescheduled
                for task in deep_work_tasks[:5]:
                    reschedule_recommendations.append({
                        "task": task,
                        "reason": "Complex task - reschedule to when energy is higher"
                    })

                # High-urgency general tasks might also need rescheduling
                for task in general_tasks:
                    if task.get("urgency_level") in ["critical", "high"]:
                        reschedule_recommendations.append({
                            "task": task,
                            "reason": "Important task but low energy - consider rescheduling or getting support"
                        })
                        break  # Only suggest rescheduling most urgent

        else:
            # No energy data - use standard priority ranking
            reasoning.append("ℹ️ No energy data available - using standard priority ranking")
            recommended_tasks = all_priorities[:5]

        # Add pattern-based insights
        if health_state and health_state.get("patterns"):
            patterns = health_state["patterns"]
            day_of_week = self.today.strftime("%A")

            if patterns.get("worst_energy_day") == day_of_week:
                reasoning.append(f"📊 Historically low energy on {day_of_week} - adjust expectations accordingly")
            elif patterns.get("best_energy_day") == day_of_week:
                reasoning.append(f"📊 Typically high energy on {day_of_week} - great day for challenges!")

        return {
            "recommended_tasks": recommended_tasks[:5],
            "deep_work_tasks": deep_work_tasks[:5],
            "admin_tasks": admin_tasks[:5],
            "general_tasks": general_tasks[:5],
            "reschedule_recommendations": reschedule_recommendations,
            "peak_focus_window": peak_focus,
            "energy_level": energy_level,
            "reasoning": reasoning,
            "health_state": health_state
        }

    def render_briefing(
        self,
        briefing_type: str = "morning",
        context: Optional[Dict[str, Any]] = None,
        energy_level: Optional[int] = None,
        custom_sections: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Render a briefing using the appropriate template.

        Args:
            briefing_type: Type of briefing ("morning" or "evening")
            context: Briefing context dict. If None, will gather fresh context.
            energy_level: Optional energy level (1-10) for task recommendations
            custom_sections: Optional list of custom sections to inject
                Each section is a dict with 'title' and 'content' keys
            **kwargs: Additional template variables to pass to the template

        Returns:
            Rendered briefing as markdown string

        Raises:
            ValueError: If Jinja2 is not available or template not found
        """
        if not JINJA2_AVAILABLE:
            raise ValueError(
                "Jinja2 is required for template rendering. "
                "Install it with: pip install jinja2"
            )

        if self.jinja_env is None:
            raise ValueError(
                f"Templates directory not found: {self.templates_dir}. "
                "Create the Templates directory with briefing templates."
            )

        # Gather context if not provided
        if context is None:
            context = self.gather_context()

        # Prepare template data
        template_data = self._prepare_template_data(
            context,
            briefing_type,
            energy_level,
            custom_sections,
            **kwargs
        )

        # Load and render template
        template_name = f"briefing_{briefing_type}.md"
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**template_data)
        except Exception as e:
            raise ValueError(f"Error rendering template {template_name}: {e}")

    def _prepare_template_data(
        self,
        context: Dict[str, Any],
        briefing_type: str,
        energy_level: Optional[int] = None,
        custom_sections: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Prepare data dictionary for template rendering.

        Args:
            context: Briefing context from gather_context()
            briefing_type: Type of briefing ("morning" or "evening")
            energy_level: Optional energy level (1-10)
            custom_sections: Optional custom sections to inject (legacy support)
            **kwargs: Additional template variables

        Returns:
            Dictionary of template variables
        """
        # Base data available to all templates
        template_data = {
            "today_date": context["today_date"],
            "day_of_week": context["day_of_week"],
            "is_weekend": context["is_weekend"],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "custom_sections": custom_sections or [],
        }

        # Get adaptive briefing mode (if not explicitly disabled)
        adaptive_mode = kwargs.get("adaptive_mode")
        if adaptive_mode is None:
            # Calculate adaptive mode by default
            adaptive_mode = self.get_adaptive_briefing_mode(context)
        template_data["adaptive_mode"] = adaptive_mode

        # Prepare section data using the new section system
        sections_data = self.prepare_sections_data(
            context,
            briefing_type,
            energy_level=energy_level,
            **kwargs
        )

        # Extract section data into template variables for backward compatibility
        for section in sections_data:
            section_id = section.get("id")
            section_data = section.get("data", {})
            template_data.update(section_data)

        # Add sections_data for advanced templates that want structured section info
        template_data["sections_data"] = sections_data

        # Morning-specific data (backward compatibility)
        if briefing_type == "morning":
            if "focus_areas" not in template_data:
                template_data["focus_areas"] = context.get("current_focus", {}).get("focus_areas", [])
            if "quick_wins" not in template_data:
                template_data["quick_wins"] = self._identify_quick_wins(context)

        # Evening-specific data (backward compatibility)
        elif briefing_type == "evening":
            # Tomorrow's priorities (shift perspective by 1 day)
            top_priorities = template_data.get("top_priorities", [])
            template_data.update({
                "accomplishments": kwargs.get("accomplishments", []),
                "energy_data": kwargs.get("energy_data", {}),
                "reflection_data": kwargs.get("reflection_data", {}),
                "reflection_notes": kwargs.get("reflection_notes", {}),
                "tomorrow_priorities": top_priorities[:3],  # Preview tomorrow's top items
                "prep_checklist": kwargs.get("prep_checklist", []),
                "commitment_progress": kwargs.get("commitment_progress", []),
            })

        # Add any additional kwargs
        template_data.update(kwargs)

        return template_data

    def _identify_quick_wins(self, context: Dict[str, Any]) -> List[str]:
        """
        Identify quick win tasks (simple, low-effort items).

        Args:
            context: Briefing context

        Returns:
            List of quick win task descriptions
        """
        quick_wins = []

        # Keywords that suggest simple/quick tasks
        quick_keywords = [
            "send", "email", "call", "schedule", "book", "order",
            "reply", "respond", "check", "review", "update", "post"
        ]

        # Check commitments
        for commitment in self.get_active_commitments(context):
            title_lower = commitment["title"].lower()
            if any(keyword in title_lower for keyword in quick_keywords):
                quick_wins.append(commitment["title"])

        # Check this week's tasks
        for task in self.get_pending_tasks(context):
            title_lower = task["text"].lower()
            if any(keyword in title_lower for keyword in quick_keywords):
                quick_wins.append(task["text"])

        # Limit to top 5 quick wins
        return quick_wins[:5]

    def _register_builtin_sections(self) -> Dict[str, callable]:
        """
        Register built-in section data providers.

        Returns:
            Dictionary mapping section IDs to provider functions
        """
        return {
            "priorities": self._provide_priorities_section,
            "commitments": self._provide_commitments_section,
            "tasks": self._provide_tasks_section,
            "focus": self._provide_focus_section,
            "quick_wins": self._provide_quick_wins_section,
            "calendar": self._provide_calendar_section,
            "health": self._provide_health_section,
        }

    def register_section_provider(self, section_id: str, provider_func: callable):
        """
        Register a custom section provider.

        Args:
            section_id: Unique identifier for the section
            provider_func: Callable that takes (context, briefing_type, **kwargs) and returns section data dict
        """
        self._section_providers[section_id] = provider_func

    def _provide_priorities_section(self, context: Dict[str, Any], briefing_type: str, **kwargs) -> Dict[str, Any]:
        """Provide data for priorities section."""
        energy_level = kwargs.get("energy_level")
        top_priorities = self.get_top_priorities(context, limit=3, energy_level=energy_level)
        return {
            "title": "🎯 Top 3 Priorities",
            "data": {
                "top_priorities": top_priorities
            }
        }

    def _provide_commitments_section(self, context: Dict[str, Any], briefing_type: str, **kwargs) -> Dict[str, Any]:
        """Provide data for commitments section."""
        active_commitments = self.get_active_commitments(context)
        return {
            "title": "📋 Active Commitments",
            "data": {
                "active_commitments": active_commitments
            }
        }

    def _provide_tasks_section(self, context: Dict[str, Any], briefing_type: str, **kwargs) -> Dict[str, Any]:
        """Provide data for tasks section."""
        pending_tasks = self.get_pending_tasks(context)
        return {
            "title": "📅 This Week's Tasks",
            "data": {
                "pending_tasks": pending_tasks
            }
        }

    def _provide_focus_section(self, context: Dict[str, Any], briefing_type: str, **kwargs) -> Dict[str, Any]:
        """Provide data for focus areas section."""
        focus_areas = context.get("current_focus", {}).get("focus_areas", [])
        return {
            "title": "🎓 Current Focus Areas",
            "data": {
                "focus_areas": focus_areas
            }
        }

    def _provide_quick_wins_section(self, context: Dict[str, Any], briefing_type: str, **kwargs) -> Dict[str, Any]:
        """Provide data for quick wins section."""
        quick_wins = self._identify_quick_wins(context)
        return {
            "title": "💡 Quick Wins",
            "data": {
                "quick_wins": quick_wins
            }
        }

    def _provide_calendar_section(self, context: Dict[str, Any], briefing_type: str, **kwargs) -> Dict[str, Any]:
        """Provide data for calendar section (placeholder)."""
        # Future: integrate with calendar API or ical files
        return {
            "title": "📆 Calendar",
            "data": {
                "events": kwargs.get("calendar_events", [])
            }
        }

    def _provide_health_section(self, context: Dict[str, Any], briefing_type: str, **kwargs) -> Dict[str, Any]:
        """Provide data for health state section."""
        health_state = kwargs.get("health_state")
        if health_state:
            return {
                "title": "🏥 Health State",
                "data": {
                    "health_state": health_state
                }
            }
        return None

    def get_enabled_sections(self, briefing_type: str = "morning") -> List[str]:
        """
        Get list of enabled sections based on configuration.

        Args:
            briefing_type: Type of briefing ("morning" or "evening")

        Returns:
            List of enabled section IDs in display order
        """
        # Get sections config
        sections_config = self.config.get("content", {}).get("sections", {})

        # Get enabled sections list
        enabled = sections_config.get("enabled", [
            "priorities", "commitments", "tasks", "focus", "quick_wins", "calendar", "health"
        ])

        # Get display order
        order = sections_config.get("order", [
            "health", "priorities", "calendar", "commitments", "tasks", "focus", "quick_wins"
        ])

        # Return sections in specified order, filtering to only enabled ones
        ordered_enabled = []
        for section_id in order:
            if section_id in enabled:
                ordered_enabled.append(section_id)

        # Add any enabled sections not in order list (append at end)
        for section_id in enabled:
            if section_id not in ordered_enabled:
                ordered_enabled.append(section_id)

        return ordered_enabled

    def get_section_data(self, section_id: str, context: Dict[str, Any], briefing_type: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific section.

        Args:
            section_id: Section identifier
            context: Briefing context
            briefing_type: Type of briefing
            **kwargs: Additional arguments for provider

        Returns:
            Section data dict or None if section not available
        """
        provider = self._section_providers.get(section_id)
        if provider:
            return provider(context, briefing_type, **kwargs)

        # Check for custom sections
        sections_config = self.config.get("content", {}).get("sections", {})
        custom_sections = sections_config.get("custom", [])

        for custom_section in custom_sections:
            if custom_section.get("id") == section_id:
                return self._get_custom_section_data(custom_section, context, briefing_type, **kwargs)

        return None

    def _get_custom_section_data(self, custom_section: Dict[str, Any], context: Dict[str, Any], briefing_type: str, **kwargs) -> Dict[str, Any]:
        """
        Get data for a custom section.

        Args:
            custom_section: Custom section configuration
            context: Briefing context
            briefing_type: Type of briefing
            **kwargs: Additional arguments

        Returns:
            Section data dict
        """
        # Check conditions
        conditions = custom_section.get("conditions", {})

        # Check day condition
        if "days" in conditions:
            current_day = context["day_of_week"].lower()
            if current_day not in conditions["days"]:
                return None

        # Check briefing type condition
        if "briefing_types" in conditions:
            if briefing_type not in conditions["briefing_types"]:
                return None

        # Get data from provider if specified
        data = {}
        data_provider = custom_section.get("data_provider")
        if data_provider:
            try:
                # Import and call the data provider function
                module_path, func_name = data_provider.rsplit(".", 1)
                import importlib
                module = importlib.import_module(module_path)
                provider_func = getattr(module, func_name)
                data = provider_func(context, briefing_type, **kwargs)
            except Exception as e:
                # Log error but continue
                data = {"error": f"Failed to load data provider: {str(e)}"}

        # Prepare section data
        section_data = {
            "title": custom_section.get("title", "Custom Section"),
            "data": data,
            "template": custom_section.get("template"),
        }

        return section_data

    def prepare_sections_data(self, context: Dict[str, Any], briefing_type: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Prepare data for all enabled sections in display order.

        Args:
            context: Briefing context
            briefing_type: Type of briefing
            **kwargs: Additional arguments for section providers

        Returns:
            List of section data dicts
        """
        sections_data = []
        enabled_sections = self.get_enabled_sections(briefing_type)

        for section_id in enabled_sections:
            section_data = self.get_section_data(section_id, context, briefing_type, **kwargs)
            if section_data:  # Only include sections that return data
                section_data["id"] = section_id
                sections_data.append(section_data)

        return sections_data

    def prompt_for_health_state(
        self,
        skip_prompts: bool = False,
        default_energy: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Prompt user for their current health state (energy, sleep, medication).

        Args:
            skip_prompts: If True, skip interactive prompts and return None
            default_energy: If provided and skip_prompts is True, use this energy level

        Returns:
            Dictionary with health state data if prompts completed, None if skipped
            Dictionary includes: energy_level, sleep_hours, vyvanse_time, trend
        """
        if skip_prompts:
            if default_energy is not None:
                # Use provided energy level but don't log
                return {"energy_level": default_energy, "from_prompts": False}
            return None

        if not HEALTH_TRACKER_AVAILABLE or self.health_tracker is None:
            print("⚠️  Health tracking not available (HealthStateTracker not found)")
            return None

        print("\n" + "="*60)
        print("🏥 Morning Health Check")
        print("="*60)
        print("Quick health check to optimize your day:")
        print()

        # Show 7-day trend if available
        trend = self._get_health_trend()
        if trend:
            print(f"📊 7-Day Trend:")
            print(f"   Average Energy: {trend['avg_energy']:.1f}/10")
            print(f"   Average Sleep: {trend['avg_sleep']:.1f} hours")
            if trend.get('best_day'):
                print(f"   Best Day: {trend['best_day']} (energy: {trend['best_energy']:.1f})")
            print()

        # Prompt for energy level (1-10)
        while True:
            try:
                energy_input = input("⚡ Energy level (1-10, where 1=exhausted, 10=energized): ").strip()
                if not energy_input:
                    print("   ⏭️  Skipping health check...")
                    return None
                energy_level = int(energy_input)
                if 1 <= energy_level <= 10:
                    break
                print("   ⚠️  Please enter a number between 1 and 10")
            except ValueError:
                print("   ⚠️  Please enter a valid number")
            except (KeyboardInterrupt, EOFError):
                print("\n   ⏭️  Skipping health check...")
                return None

        # Prompt for sleep hours
        while True:
            try:
                sleep_input = input("😴 Hours of sleep last night (e.g., 7.5): ").strip()
                if not sleep_input:
                    print("   ⏭️  Skipping sleep tracking...")
                    sleep_hours = None
                    break
                sleep_hours = float(sleep_input)
                if 0 <= sleep_hours <= 24:
                    break
                print("   ⚠️  Please enter hours between 0 and 24")
            except ValueError:
                print("   ⚠️  Please enter a valid number")
            except (KeyboardInterrupt, EOFError):
                print("\n   ⏭️  Skipping sleep tracking...")
                sleep_hours = None
                break

        # Prompt for Vyvanse time (optional)
        vyvanse_time = None
        try:
            vyvanse_input = input("💊 Vyvanse time (HH:MM, e.g., 08:30, or press Enter to skip): ").strip()
            if vyvanse_input:
                # Validate time format
                if re.match(r'^\d{1,2}:\d{2}$', vyvanse_input):
                    # Normalize to HH:MM format
                    hour, minute = vyvanse_input.split(':')
                    hour = int(hour)
                    minute = int(minute)
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        vyvanse_time = f"{hour:02d}:{minute:02d}"
                    else:
                        print("   ⚠️  Invalid time, skipping medication tracking")
                else:
                    print("   ⚠️  Invalid format, skipping medication tracking")
        except (KeyboardInterrupt, EOFError):
            print("\n   ⏭️  Skipping medication tracking...")

        # Log the entry to HealthLog.json
        if sleep_hours is not None:
            success = self.health_tracker.log_entry(
                energy_level=energy_level,
                sleep_hours=sleep_hours,
                vyvanse_time=vyvanse_time,
                notes="Morning briefing health check"
            )
            if success:
                print(f"\n✅ Health state logged successfully!")
            else:
                print(f"\n⚠️  Warning: Failed to save health state")
        else:
            print(f"\n⚠️  Skipping health log (missing sleep hours)")

        print("="*60 + "\n")

        # Return health data for use in briefing
        return {
            "energy_level": energy_level,
            "sleep_hours": sleep_hours,
            "vyvanse_time": vyvanse_time,
            "trend": trend,
            "from_prompts": True
        }

    def _get_health_trend(self) -> Optional[Dict[str, Any]]:
        """
        Get 7-day health trend from HealthStateTracker.

        Returns:
            Dictionary with trend data or None if not available
        """
        if not HEALTH_TRACKER_AVAILABLE or self.health_tracker is None:
            return None

        try:
            # Get 7-day averages
            averages = self.health_tracker.calculate_averages(days=7)
            if not averages:
                return None

            # Get recent entries for best day calculation
            recent_entries = self.health_tracker.get_recent_entries(days=7)
            if not recent_entries:
                return None

            # Find best energy day
            best_entry = max(recent_entries, key=lambda e: e.get('energy_level', 0))
            best_date = date.fromisoformat(best_entry['date'])
            best_day = best_date.strftime('%A')

            return {
                'avg_energy': averages['avg_energy_level'],
                'avg_sleep': averages['avg_sleep_hours'],
                'sample_size': averages['sample_size'],
                'best_day': best_day,
                'best_energy': best_entry['energy_level']
            }
        except Exception as e:
            print(f"Warning: Error getting health trend: {e}")
            return None

    def prompt_for_evening_reflection(
        self,
        skip_prompts: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Prompt user for evening reflection (energy check, accomplishments, learnings).

        Args:
            skip_prompts: If True, skip interactive prompts and return None

        Returns:
            Dictionary with evening reflection data if prompts completed, None if skipped
            Dictionary includes: morning_energy, evening_energy, energy_change, trend,
                               accomplishments, energy_draining_activities, wins,
                               improvements_for_tomorrow
        """
        if skip_prompts:
            return None

        if not HEALTH_TRACKER_AVAILABLE or self.health_tracker is None:
            print("⚠️  Health tracking not available (HealthStateTracker not found)")
            return None

        print("\n" + "="*60)
        print("🌙 Evening Reflection")
        print("="*60)
        print("Let's reflect on your day and prepare for tomorrow:")
        print()

        # Get morning energy from today's health log
        morning_energy = None
        today_entry = self.health_tracker.get_entry(self.today)
        if today_entry and 'energy_level' in today_entry:
            morning_energy = today_entry['energy_level']
            print(f"📊 Morning Energy: {morning_energy}/10")
            print()

        # Prompt for current (evening) energy level
        while True:
            try:
                energy_input = input("⚡ Current energy level (1-10, where 1=exhausted, 10=energized): ").strip()
                if not energy_input:
                    print("   ⏭️  Skipping evening reflection...")
                    return None
                evening_energy = int(energy_input)
                if 1 <= evening_energy <= 10:
                    break
                print("   ⚠️  Please enter a number between 1 and 10")
            except ValueError:
                print("   ⚠️  Please enter a valid number")
            except (KeyboardInterrupt, EOFError):
                print("\n   ⏭️  Skipping evening reflection...")
                return None

        # Calculate energy change
        energy_change = None
        energy_trend = None
        if morning_energy is not None:
            energy_change = evening_energy - morning_energy
            if energy_change > 0:
                energy_trend = f"↗️ Energy increased by {energy_change} points"
            elif energy_change < 0:
                energy_trend = f"↘️ Energy decreased by {abs(energy_change)} points"
            else:
                energy_trend = "→ Energy remained stable"
            print(f"\n{energy_trend}")
            print()

        # Prompt for accomplishments
        print("✅ What did you accomplish today?")
        print("   (Enter each accomplishment, press Enter twice when done)")
        accomplishments = []
        while True:
            try:
                accomplishment = input("   - ").strip()
                if not accomplishment:
                    if len(accomplishments) == 0:
                        # At least one accomplishment recommended
                        print("     💡 Even small wins count! Try to note at least one thing.")
                        continue
                    break
                accomplishments.append(accomplishment)
            except (KeyboardInterrupt, EOFError):
                print("\n   ⏭️  Skipping accomplishments...")
                break

        # Celebrate wins
        wins = []
        if accomplishments:
            print(f"\n🌟 Great! You accomplished {len(accomplishments)} thing(s) today!")
            wins.append(f"Completed {len(accomplishments)} task(s)")

        # Identify energy-draining activities (if energy decreased significantly)
        energy_draining = []
        if energy_change is not None and energy_change <= -3:
            print(f"\n🤔 Your energy dropped significantly today (from {morning_energy} to {evening_energy}).")
            try:
                draining = input("   What activities or tasks felt most draining? ").strip()
                if draining:
                    energy_draining.append(draining)
            except (KeyboardInterrupt, EOFError):
                print("\n   ⏭️  Skipping...")

        # Prompt for learnings/improvements
        print("\n💡 What could make tomorrow better?")
        improvements = []
        try:
            improvement = input("   - ").strip()
            if improvement:
                improvements.append(improvement)
        except (KeyboardInterrupt, EOFError):
            print("\n   ⏭️  Skipping...")

        # Add automatic recommendations based on energy patterns
        if energy_change is not None:
            if energy_change <= -4:
                improvements.append("Consider shorter work blocks with more breaks")
                improvements.append("Review your task list to identify energy-draining activities")
            elif evening_energy <= 3:
                improvements.append("Prioritize rest and recovery tonight")
                improvements.append("Start tomorrow with easier tasks to build momentum")

        # Get 7-day trend for context
        trend_data = self._get_health_trend()

        print(f"\n✅ Evening reflection completed!")
        print("="*60 + "\n")

        # Return reflection data for use in briefing
        return {
            "morning_energy": morning_energy,
            "evening_energy": evening_energy,
            "energy_change": energy_change,
            "trend": energy_trend,
            "accomplishments": accomplishments,
            "energy_draining_activities": energy_draining,
            "wins": wins,
            "improvements_for_tomorrow": improvements,
            "health_trend": trend_data,
            "from_prompts": True
        }

    def _track_briefing_activity(self, briefing_type: str = "morning") -> bool:
        """
        Track when a briefing is generated for activity monitoring.

        Args:
            briefing_type: Type of briefing generated (morning/evening)

        Returns:
            True if successfully tracked, False otherwise.
        """
        activity_file = self.state_dir / ".briefing_activity.json"

        # Load existing activity data
        if activity_file.exists():
            try:
                with open(activity_file, 'r', encoding='utf-8') as f:
                    activity_data = json.load(f)
            except Exception:
                activity_data = {"briefings": [], "metadata": {}}
        else:
            activity_data = {"briefings": [], "metadata": {}}

        # Add new briefing activity
        activity_data["briefings"].append({
            "date": self.today.isoformat(),
            "type": briefing_type,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last 90 days of data
        cutoff_date = (self.today - timedelta(days=90)).isoformat()
        activity_data["briefings"] = [
            b for b in activity_data["briefings"]
            if b["date"] >= cutoff_date
        ]

        # Sort by date (most recent first)
        activity_data["briefings"].sort(
            key=lambda x: x["date"],
            reverse=True
        )

        activity_data["metadata"]["last_updated"] = datetime.now().isoformat()

        # Save updated data
        try:
            with open(activity_file, 'w', encoding='utf-8') as f:
                json.dump(activity_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def _get_last_activity_date(self) -> Optional[date]:
        """
        Get the date of the last briefing or task activity.

        Returns:
            Date of last activity, or None if no activity found.
        """
        last_dates = []

        # Check briefing activity
        activity_file = self.state_dir / ".briefing_activity.json"
        if activity_file.exists():
            try:
                with open(activity_file, 'r', encoding='utf-8') as f:
                    activity_data = json.load(f)
                    if activity_data.get("briefings"):
                        last_briefing_date = activity_data["briefings"][0]["date"]
                        last_dates.append(date.fromisoformat(last_briefing_date))
            except Exception:
                pass

        # Check task completions from PatternAnalyzer
        if self.pattern_analyzer is not None:
            completions = self.pattern_analyzer.patterns_data.get("task_completions", [])
            if completions:
                # Completions are sorted by date (most recent first)
                last_completion_date = completions[0]["completion_date"]
                last_dates.append(date.fromisoformat(last_completion_date))

        # Return the most recent activity date
        if last_dates:
            return max(last_dates)
        return None

    def _count_recent_activities(self, days: int = 7) -> int:
        """
        Count the number of activities (briefings + task completions) in recent days.

        Args:
            days: Number of days to look back

        Returns:
            Total count of activities.
        """
        count = 0
        cutoff_date = (self.today - timedelta(days=days)).isoformat()

        # Count briefings
        activity_file = self.state_dir / ".briefing_activity.json"
        if activity_file.exists():
            try:
                with open(activity_file, 'r', encoding='utf-8') as f:
                    activity_data = json.load(f)
                    count += len([
                        b for b in activity_data.get("briefings", [])
                        if b["date"] >= cutoff_date
                    ])
            except Exception:
                pass

        # Count task completions
        if self.pattern_analyzer is not None:
            completions = self.pattern_analyzer.patterns_data.get("task_completions", [])
            count += len([
                c for c in completions
                if c["completion_date"] >= cutoff_date
            ])

        return count

    def _count_overdue_tasks(self, context: Optional[Dict[str, Any]] = None) -> int:
        """
        Count the number of overdue tasks in the context.

        Args:
            context: Briefing context. If None, will gather fresh context.

        Returns:
            Number of overdue tasks.
        """
        if context is None:
            context = self.gather_context()

        overdue_count = 0
        today_str = self.today.isoformat()

        # Check commitments for overdue items
        for commitment in context.get("commitments", []):
            # Use is_complete field (not completed)
            if commitment.get("is_complete"):
                continue
            # Use deadline field (not due_date)
            deadline = commitment.get("deadline")
            if deadline and deadline < today_str:
                overdue_count += 1

        # Check this week tasks for overdue items
        tasks = context.get("this_week", {}).get("tasks", [])
        for task in tasks:
            if task.get("completed"):
                continue
            due_date = task.get("due_date")
            if due_date and due_date < today_str:
                overdue_count += 1

        return overdue_count

    def get_adaptive_briefing_mode(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Determine the adaptive briefing mode based on recent activity.

        Analyzes:
        - Days since last activity (inactivity detection)
        - Recent activity volume (high activity detection)
        - Overdue tasks count (catch-up mode detection)

        Args:
            context: Briefing context. If None, will gather fresh context.

        Returns:
            Dictionary with adaptation information:
            - mode: 'reentry' | 'concise' | 'catchup' | 'normal'
            - days_inactive: Number of days since last activity (None if active)
            - recent_activities: Count of activities in last 7 days
            - overdue_tasks: Number of overdue tasks
            - reasoning: Human-readable explanation
            - recommendations: List of adaptive recommendations
        """
        if context is None:
            context = self.gather_context()

        last_activity = self._get_last_activity_date()
        days_inactive = None
        if last_activity:
            days_inactive = (self.today - last_activity).days

        recent_activities = self._count_recent_activities(days=7)
        overdue_tasks = self._count_overdue_tasks(context)

        # Determine mode based on conditions
        mode = "normal"
        reasoning = "Regular briefing with standard content."
        recommendations = []

        # Priority 1: Inactivity (3+ days without activity)
        if days_inactive is not None and days_inactive >= 3:
            mode = "reentry"
            reasoning = f"You haven't checked in for {days_inactive} days. Let's ease back in gently."
            recommendations.extend([
                "Welcome back! Take a moment to review what's changed.",
                "Focus on understanding your current commitments before diving into tasks.",
                "Consider starting with quick wins to build momentum.",
                "Don't feel pressured to tackle everything at once."
            ])

        # Priority 2: Many overdue tasks (5+ tasks)
        elif overdue_tasks >= 5:
            mode = "catchup"
            reasoning = f"You have {overdue_tasks} overdue tasks. Let's focus on catching up."
            recommendations.extend([
                f"You have {overdue_tasks} overdue items that need attention.",
                "Prioritize the most urgent overdue tasks first.",
                "Consider rescheduling less urgent items to reduce overwhelm.",
                "Break large overdue tasks into smaller, manageable steps.",
                "Set realistic goals for today - progress is better than perfection."
            ])

        # Priority 3: High activity (15+ activities in last 7 days)
        elif recent_activities >= 15:
            mode = "concise"
            reasoning = f"You've been very active ({recent_activities} activities in 7 days). Here's a concise briefing."
            recommendations.extend([
                "You're on a productive streak! Keep it up.",
                "Quick priorities to maintain momentum.",
                "Remember to balance productivity with rest.",
                "Watch for signs of burnout - it's okay to take breaks."
            ])

        # Track this briefing activity
        self._track_briefing_activity()

        return {
            "mode": mode,
            "days_inactive": days_inactive,
            "recent_activities": recent_activities,
            "overdue_tasks": overdue_tasks,
            "reasoning": reasoning,
            "recommendations": recommendations,
            "detected_at": datetime.now().isoformat()
        }
