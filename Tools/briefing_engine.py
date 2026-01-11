"""
BriefingEngine - Core class for generating intelligent daily briefings.

This module provides the main engine for gathering context from State files,
processing commitments and tasks, and preparing structured data for briefing
generation.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import json
import re


class BriefingEngine:
    """
    Core engine for generating personalized daily briefings.

    Gathers data from State files (Commitments.md, ThisWeek.md, CurrentFocus.md),
    processes and structures the information, and prepares it for rendering.
    """

    def __init__(self, state_dir: Optional[str] = None):
        """
        Initialize the BriefingEngine.

        Args:
            state_dir: Path to the State directory. Defaults to ./State relative to cwd.
        """
        if state_dir is None:
            state_dir = os.path.join(os.getcwd(), "State")

        self.state_dir = Path(state_dir)
        self.today = date.today()

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
