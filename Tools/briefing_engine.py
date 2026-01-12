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


class BriefingEngine:
    """
    Core engine for generating personalized daily briefings.

    Gathers data from State files (Commitments.md, ThisWeek.md, CurrentFocus.md),
    processes and structures the information, and prepares it for rendering.
    """

    def __init__(self, state_dir: Optional[str] = None, templates_dir: Optional[str] = None):
        """
        Initialize the BriefingEngine.

        Args:
            state_dir: Path to the State directory. Defaults to ./State relative to cwd.
            templates_dir: Path to the Templates directory. Defaults to ./Templates relative to cwd.
        """
        if state_dir is None:
            state_dir = os.path.join(os.getcwd(), "State")
        if templates_dir is None:
            templates_dir = os.path.join(os.getcwd(), "Templates")

        self.state_dir = Path(state_dir)
        self.templates_dir = Path(templates_dir)
        self.today = date.today()

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
            custom_sections: Optional custom sections to inject
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

        # Common data for both morning and evening
        active_commitments = self.get_active_commitments(context)
        pending_tasks = self.get_pending_tasks(context)
        top_priorities = self.get_top_priorities(context, limit=3, energy_level=energy_level)

        template_data.update({
            "active_commitments": active_commitments,
            "pending_tasks": pending_tasks,
            "top_priorities": top_priorities,
        })

        # Morning-specific data
        if briefing_type == "morning":
            template_data.update({
                "focus_areas": context.get("current_focus", {}).get("focus_areas", []),
                "quick_wins": self._identify_quick_wins(context),
            })

        # Evening-specific data
        elif briefing_type == "evening":
            # Tomorrow's priorities (shift perspective by 1 day)
            # For now, use same priorities but mark as "tomorrow"
            template_data.update({
                "accomplishments": kwargs.get("accomplishments", []),
                "energy_data": kwargs.get("energy_data", {}),
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
                'avg_energy': averages['avg_energy'],
                'avg_sleep': averages['avg_sleep'],
                'sample_size': averages['sample_size'],
                'best_day': best_day,
                'best_energy': best_entry['energy_level']
            }
        except Exception as e:
            print(f"Warning: Error getting health trend: {e}")
            return None

    # =============================================================================
    # ENERGY-AWARE COACH EXPLANATION HELPERS
    # =============================================================================

    def format_energy_context_for_coach(
        self,
        energy_level: str,
        readiness_score: Optional[int] = None,
        sleep_score: Optional[int] = None,
        source: str = "default"
    ) -> Dict[str, Any]:
        """
        Format energy context data for Coach explanations.

        Args:
            energy_level: Current energy level (high, medium, low)
            readiness_score: Oura readiness score (0-100) if available
            sleep_score: Oura sleep score (0-100) if available
            source: Source of energy data (oura, manual, default)

        Returns:
            Dictionary with formatted energy context for Coach templates
        """
        return {
            "energy_level": energy_level,
            "readiness_score": readiness_score,
            "sleep_score": sleep_score,
            "source": source,
            "readiness_display": f"{readiness_score}" if readiness_score else "N/A",
            "sleep_display": f"{sleep_score}" if sleep_score else "N/A",
            "energy_emoji": {
                "high": "🚀",
                "medium": "✅",
                "low": "🔋"
            }.get(energy_level, "ℹ️"),
            "is_high_energy": energy_level == "high",
            "is_medium_energy": energy_level == "medium",
            "is_low_energy": energy_level == "low"
        }

    def explain_task_suggestion(
        self,
        task_title: str,
        cognitive_load: str,
        value_tier: Optional[str],
        energy_level: str,
        readiness_score: Optional[int],
        match_reason: str
    ) -> str:
        """
        Generate Coach-style explanation for why a task was suggested.

        Args:
            task_title: Name of the suggested task
            cognitive_load: Task's cognitive load (low, medium, high)
            value_tier: Task's value tier (checkbox, progress, milestone, deliverable)
            energy_level: Current energy level (high, medium, low)
            readiness_score: Oura readiness score if available
            match_reason: Technical match reason from energy-prioritization service

        Returns:
            Human-readable Coach explanation string
        """
        readiness_display = f"readiness: {readiness_score}" if readiness_score else "estimated energy"

        if energy_level == "high":
            if cognitive_load == "high":
                return f"I'm suggesting '{task_title}' because you're at peak energy today ({readiness_display}). This is perfect for complex work like this."
            elif value_tier in ["milestone", "deliverable"]:
                return f"Your readiness of {readiness_score} means you can tackle that {value_tier} task '{task_title}' you've been putting off."
            else:
                return f"High energy day - let's knock out '{task_title}'. These are the days to make real progress."

        elif energy_level == "medium":
            if cognitive_load == "medium":
                return f"At {readiness_score} readiness, you're in a good place for '{task_title}'. Not your peak, but definitely capable."
            elif value_tier == "progress":
                return f"Your energy is solid today ({readiness_display}). '{task_title}' is a progress task that moves things forward without overwhelming you."
            else:
                return f"Medium energy - perfect for steady progress. '{task_title}' builds momentum without burning you out."

        else:  # low energy
            if cognitive_load == "low":
                return f"Your readiness is {readiness_score} today. '{task_title}' is a low-cognitive task that keeps momentum without pushing too hard."
            elif value_tier == "checkbox":
                return f"At {readiness_score} readiness, be gentle with yourself. '{task_title}' is a quick win that builds momentum without draining you further."
            else:
                return f"Low energy doesn't mean no progress. '{task_title}' lets you stay productive while respecting your state."

    def explain_goal_adjustment(
        self,
        original_target: int,
        adjusted_target: int,
        adjustment_percentage: float,
        readiness_score: Optional[int],
        sleep_score: Optional[int],
        energy_level: str
    ) -> str:
        """
        Generate Coach-style explanation for daily goal adjustment.

        Args:
            original_target: Original target points
            adjusted_target: Adjusted target points
            adjustment_percentage: Percentage adjustment (e.g., 15, 0, -25)
            readiness_score: Oura readiness score if available
            sleep_score: Oura sleep score if available
            energy_level: Current energy level (high, medium, low)

        Returns:
            Human-readable Coach explanation string
        """
        readiness_display = f"{readiness_score}" if readiness_score else "N/A"
        sleep_display = f"{sleep_score}" if sleep_score else "N/A"

        if adjustment_percentage > 0:
            # Target increased (high energy)
            if sleep_score:
                return f"I increased your target from {original_target} to {adjusted_target} points (+{int(adjustment_percentage)}%) because your readiness is {readiness_display} and sleep is {sleep_display}. You've got the capacity for more today."
            else:
                return f"Your body says you're ready - readiness at {readiness_display}. I'm confident you can handle the higher target of {adjusted_target} points."

        elif adjustment_percentage == 0:
            # Target maintained (medium energy)
            return f"Your readiness is {readiness_display} - right in the normal range. Keeping your target at {original_target} points."

        else:
            # Target reduced (low energy)
            if sleep_score:
                return f"I dropped your target from {original_target} to {adjusted_target} points ({int(adjustment_percentage)}%) because your readiness is {readiness_display} and sleep is {sleep_display}. This protects your streak while respecting your state."
            else:
                return f"At {readiness_display} readiness, pushing for {original_target} points would hurt more than help. {adjusted_target} points lets you maintain progress and protect your streak."

    def detect_energy_task_mismatch(
        self,
        task_title: str,
        cognitive_load: str,
        energy_level: str,
        readiness_score: Optional[int]
    ) -> Optional[str]:
        """
        Detect potential energy-task mismatches and generate warnings.

        Args:
            task_title: Name of the task being attempted
            cognitive_load: Task's cognitive load (low, medium, high)
            energy_level: Current energy level (high, medium, low)
            readiness_score: Oura readiness score if available

        Returns:
            Warning message if mismatch detected, None otherwise
        """
        readiness_display = f"{readiness_score}" if readiness_score else "low"

        # High cognitive load on low energy
        if cognitive_load == "high" and energy_level == "low":
            return f"⚠️ I notice you're looking at '{task_title}' which requires deep focus, but your readiness is {readiness_display}. Consider tackling this when you're fresher, or break it into smaller chunks."

        # Low cognitive load on high energy (possible avoidance)
        if cognitive_load == "low" and energy_level == "high":
            return f"You're choosing '{task_title}' even with high readiness ({readiness_display}). Any reason you're not tackling bigger stuff? Avoidance or strategy?"

        # Medium/high cognitive on low energy
        if cognitive_load == "medium" and energy_level == "low" and readiness_score and readiness_score < 60:
            return f"'{task_title}' is medium complexity and you're at {readiness_display} readiness. Doable, but it'll cost more energy than it's worth. Want to see lighter options?"

        return None

    def generate_energy_pattern_insights(
        self,
        recent_readiness_scores: List[int],
        recent_energy_levels: List[str],
        days_count: int = 7
    ) -> List[str]:
        """
        Generate Coach-style insights about energy patterns.

        Args:
            recent_readiness_scores: List of readiness scores from recent days
            recent_energy_levels: List of energy levels from recent days
            days_count: Number of days to analyze (default: 7)

        Returns:
            List of insight strings
        """
        insights = []

        if not recent_readiness_scores:
            return insights

        # Calculate average
        avg_readiness = sum(recent_readiness_scores) / len(recent_readiness_scores)

        # Detect consistent low energy
        low_energy_days = sum(1 for r in recent_readiness_scores if r < 70)
        if low_energy_days >= 3:
            scores_str = ", ".join(str(r) for r in recent_readiness_scores[:low_energy_days])
            insights.append(
                f"I'm seeing a pattern: readiness below 70 for {low_energy_days} days (scores: {scores_str}). "
                "You're completing tasks but this isn't sustainable. What needs to change?"
            )

        # Detect declining trend
        if len(recent_readiness_scores) >= 3:
            first_half = recent_readiness_scores[:len(recent_readiness_scores)//2]
            second_half = recent_readiness_scores[len(recent_readiness_scores)//2:]
            if sum(second_half)/len(second_half) < sum(first_half)/len(first_half) - 10:
                insights.append(
                    f"Your readiness is declining: started at {first_half[0]}, now at {recent_readiness_scores[-1]}. "
                    "What's blocking recovery?"
                )

        # Detect high variability
        if len(recent_readiness_scores) >= 5:
            variance = max(recent_readiness_scores) - min(recent_readiness_scores)
            if variance > 30:
                insights.append(
                    f"Your energy is swinging wildly: {min(recent_readiness_scores)} to {max(recent_readiness_scores)} "
                    "this week. That's a {variance}-point swing. What's causing the instability?"
                )

        return insights
