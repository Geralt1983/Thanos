#!/usr/bin/env python3
"""
Dynamic Priority Hook

Automatically updates State/CurrentFocus.md when priorities shift in conversation.

This addresses the user's requirement:
"I need you to update your logic to dynamically update priorities as the day goes
on through our discussions."

Triggered post-tool-use to detect priority shifts and update CurrentFocus.md.
"""

import os
import sys
import re
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("thanos.priority-hook")


class PriorityShiftDetector:
    """Detects and handles priority shifts in conversations."""

    # Priority shift indicators
    SHIFT_PATTERNS = [
        r"top priority",
        r"highest priority",
        r"most important",
        r"more important than",
        r"more urgent than",
        r"focus on.*instead",
        r"switch to",
        r"must do.*(?:first|before)",
        r"critical.*(?:this week|today)",
        r"urgent.*need",
        r"priority\s+\d+[:\s]",  # "priority 1:"
        r"first priority",
        r"main focus",
    ]

    # Deprioritization indicators
    DEPRIORITIZE_PATTERNS = [
        r"(?:can|will)\s+wait",
        r"lower priority",
        r"not\s+(?:as\s+)?urgent",
        r"put\s+(?:it|that)\s+on\s+hold",
        r"back\s+burner",
        r"postpone",
    ]

    def __init__(self, focus_file_path: Path):
        self.focus_file = focus_file_path

    def detect_shift(self, user_message: str, assistant_response: str = "") -> bool:
        """
        Detect if conversation indicates a priority shift.

        Args:
            user_message: User's message
            assistant_response: Assistant's response

        Returns:
            bool: True if shift detected
        """
        combined = f"{user_message} {assistant_response}".lower()

        for pattern in self.SHIFT_PATTERNS:
            if re.search(pattern, combined):
                logger.info(f"Priority shift detected: pattern='{pattern}'")
                return True

        return False

    def extract_priorities(self, user_message: str) -> List[str]:
        """
        Extract new priorities from user message.

        Args:
            user_message: User's message

        Returns:
            List of priority items
        """
        priorities = []

        # Pattern 1: Explicit priority list
        # "Top priorities: X, Y, Z"
        list_match = re.search(
            r"(?:top |main |key )?priorit(?:y|ies)[:\s]+(.+?)(?:\.|$)",
            user_message,
            re.IGNORECASE,
        )

        if list_match:
            items = list_match.group(1).split(",")
            priorities.extend([item.strip() for item in items if item.strip()])

        # Pattern 2: Individual priority statements
        # "Top priority this week: X"
        individual_patterns = [
            r"(?:top|first|main|highest)\s+priority[:\s]+(.+?)(?:\.|$)",
            r"focus\s+on\s+(.+?)(?:\s+(?:first|instead|today))",
            r"must\s+(?:do|complete|finish)\s+(.+?)(?:\s+(?:first|before|today))",
            r"priority\s+\d+[:\s]+(.+?)(?:\.|$)",
        ]

        for pattern in individual_patterns:
            matches = re.findall(pattern, user_message, re.IGNORECASE)
            for match in matches:
                cleaned = match.strip()
                if cleaned and cleaned not in priorities:
                    priorities.append(cleaned)

        # Pattern 3: Infer from high-value task creation
        # "Add milestone task: Complete passport application"
        task_pattern = r"(?:add|create).*(?:milestone|critical|urgent).*[:\s]+(.+?)(?:\.|$)"
        task_match = re.search(task_pattern, user_message, re.IGNORECASE)

        if task_match:
            task_title = task_match.group(1).strip()
            if task_title and task_title not in priorities:
                priorities.append(task_title)

        return priorities[:3]  # Top 3 max

    def update_current_focus(self, new_priorities: List[str]) -> bool:
        """
        Update State/CurrentFocus.md with new priorities.

        Args:
            new_priorities: List of priority items (max 3)

        Returns:
            bool: True if update successful
        """
        if not self.focus_file.exists():
            logger.warning(f"Focus file not found: {self.focus_file}")
            return False

        if not new_priorities:
            logger.info("No new priorities to update")
            return False

        try:
            # Read current content
            content = self.focus_file.read_text()

            # Find and replace priorities section
            priorities_match = re.search(
                r"(## Priorities\n)(.*?)(?=\n##|\Z)", content, re.DOTALL
            )

            if not priorities_match:
                logger.warning("Priorities section not found in CurrentFocus.md")
                return False

            # Build new priorities section
            new_section = "## Priorities\n"
            for priority in new_priorities:
                # Clean up priority text
                priority = priority.strip()
                # Remove trailing punctuation
                priority = priority.rstrip(".,;:")
                # Ensure it starts with dash if not already
                if not priority.startswith("-"):
                    new_section += f"- {priority}\n"
                else:
                    new_section += f"{priority}\n"

            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_section += f"\n*Updated: {timestamp}*\n"

            # Replace section in content
            updated_content = (
                content[: priorities_match.start()]
                + new_section
                + content[priorities_match.end() :]
            )

            # Write back
            self.focus_file.write_text(updated_content)

            logger.info(f"Updated priorities: {new_priorities}")
            return True

        except Exception as e:
            logger.error(f"Failed to update priorities: {e}")
            return False


def process_tool_use_context(context_json: str) -> None:
    """
    Process tool use context and update priorities if shift detected.

    Args:
        context_json: JSON string with tool use context
    """
    try:
        context = json.loads(context_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse context JSON: {e}")
        return

    user_message = context.get("user_message", "")
    assistant_response = context.get("assistant_response", "")

    if not user_message:
        return

    # Initialize detector
    focus_file = PROJECT_ROOT / "State" / "CurrentFocus.md"
    detector = PriorityShiftDetector(focus_file)

    # Detect shift
    if detector.detect_shift(user_message, assistant_response):
        # Extract new priorities
        new_priorities = detector.extract_priorities(user_message)

        if new_priorities:
            # Update CurrentFocus.md
            success = detector.update_current_focus(new_priorities)

            if success:
                print(f"✓ Priorities updated: {', '.join(new_priorities)}")
            else:
                print("✗ Failed to update priorities")
        else:
            logger.info("Priority shift detected but no new priorities extracted")


def main():
    """
    CLI entry point.

    Expects context JSON as stdin or first argument.
    """
    if len(sys.argv) > 1:
        context_json = sys.argv[1]
    else:
        context_json = sys.stdin.read()

    if not context_json.strip():
        logger.warning("No context provided")
        return

    process_tool_use_context(context_json)


if __name__ == "__main__":
    main()
