#!/usr/bin/env python3
"""
Classification Hook - The Gate

Prevents casual thoughts from becoming tasks.
Classifies user input into: thinking|venting|observation|question|task

Usage:
    python3 classify_input.py "user message here"

Returns: One of: thinking, venting, observation, question, task
"""

import sys
import re
from typing import Literal

ClassificationType = Literal["thinking", "venting", "observation", "question", "task"]


def classify_input(user_message: str) -> ClassificationType:
    """
    Classify user input to prevent casual thoughts becoming tasks.

    Args:
        user_message: The raw user input

    Returns:
        Classification type: thinking|venting|observation|question|task

    Examples:
        >>> classify_input("I'm wondering if I should switch frameworks")
        'thinking'

        >>> classify_input("I'm so frustrated with this bug")
        'venting'

        >>> classify_input("I noticed the API is slow")
        'observation'

        >>> classify_input("What's on my calendar?")
        'question'

        >>> classify_input("Add a task to review Q4 planning")
        'task'

        >>> classify_input("Can you help me plan my morning")
        'task'
    """
    # Normalize input
    lower_msg = user_message.lower().strip()

    if not lower_msg:
        return "observation"

    # Priority 1: Questions (highest priority)
    if "?" in user_message:
        return "question"

    # Priority 2: Explicit task patterns (must be very specific)
    task_patterns = [
        # Direct task commands
        r'\b(add|create|make|build)\s+(?:a\s+)?task\b',
        r'\btask\s+(?:to|for)\s+\w+',

        # Tool requests with action verbs
        r'\b(can\s+you|could\s+you|please)\s+(?:add|create|make|build|do|complete|finish)',
        r'\bhelp\s+me\s+(?:plan|organize|do|create|add|make)',

        # Completion requests
        r'\b(complete|finish|mark\s+(?:as\s+)?(?:done|complete))\s+',

        # Direct commands
        r'^(do|complete|finish|add|create|make)\s+\w+',
    ]

    for pattern in task_patterns:
        if re.search(pattern, lower_msg):
            return "task"

    # Priority 3: Venting (emotional processing)
    venting_patterns = [
        r'\b(frustrated?|frustrating)\b',
        r'\b(overwhelmed?|overwhelming)\b',
        r'\b(stressed?|stressing|stressful)\b',
        r'\bi\s+hate\b',
        r'\b(annoying|annoyed)\b',
        r'\b(exhausted?|exhausting)\b',
        r'\b(tired\s+of|sick\s+of)\b',
        r'\b(can\'t\s+stand|cannot\s+stand)\b',
        r'\b(driving\s+me\s+(?:crazy|nuts|insane))\b',
        r'\bugh\b',
        r'\b(this\s+sucks|that\s+sucks)\b',
    ]

    for pattern in venting_patterns:
        if re.search(pattern, lower_msg):
            return "venting"

    # Priority 4: Thinking (reflective, contemplative)
    thinking_patterns = [
        r'\bi\'?m\s+wondering\b',
        r'\bwhat\s+if\b',
        r'\b(?:thinking|thought)\s+about\b',
        r'\b(?:considering|contemplating)\b',
        r'\bshould\s+i\b',
        r'\bcould\s+we\b',
        r'\bmaybe\s+(?:i|we)\b',
        r'\bi\s+was\s+thinking\b',
        r'\bhow\s+about\b',
        r'\bwhat\s+about\b',
    ]

    for pattern in thinking_patterns:
        if re.search(pattern, lower_msg):
            return "thinking"

    # Priority 5: Observation (noticing, sharing info)
    observation_patterns = [
        r'\bi\s+noticed\b',
        r'\b(?:just\s+)?saw\b',
        r'\binteresting\s+that\b',
        r'\blooks?\s+like\b',
        r'\bseems?\s+like\b',
        r'\brealized?\b',
        r'\bobserved?\b',
        r'\bnote\s+that\b',
        r'\bfyi\b',
        r'\bheads\s+up\b',
    ]

    for pattern in observation_patterns:
        if re.search(pattern, lower_msg):
            return "observation"

    # Default: observation (safest - doesn't create tasks)
    # If we can't confidently classify it, treat it as passive observation
    return "observation"


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 classify_input.py \"user message\"", file=sys.stderr)
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    classification = classify_input(message)
    print(classification)


if __name__ == "__main__":
    main()
