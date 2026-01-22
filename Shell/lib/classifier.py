"""
Input Classification Module

Classifies user input to prevent casual thoughts becoming tasks.
Supports: thinking, venting, observation, question, task
"""

import re
from typing import Optional


def classify_input(user_message: str) -> str:
    """
    Classify user input based on linguistic patterns.

    Args:
        user_message: Raw user input string

    Returns:
        Classification: thinking|venting|observation|question|task

    Classification Logic:
        - thinking: Reflective, exploratory, no action implied
        - venting: Emotional processing, frustration
        - observation: Sharing information, no implicit ask
        - question: Direct inquiry, seeking information
        - task: Action-oriented, execution required
    """
    if not user_message or not user_message.strip():
        return "question"  # Empty input treated as prompt

    msg_lower = user_message.lower()

    # Thinking indicators - exploratory, no action
    thinking_patterns = [
        r"\bi'?m wondering\b",
        r"\bwhat if\b",
        r"\bthinking about\b",
        r"\bconsidering\b",
        r"\bi wonder\b",
        r"\bmaybe\b.*\bshould\b",
        r"\bpossibly\b",
        r"\bcould be\b"
    ]

    # Venting indicators - emotional processing
    venting_patterns = [
        r"\bi'?m (so |really )?(tired|exhausted|frustrated|overwhelmed)",
        r"\bthis is (so )?(stupid|annoying|difficult|hard|impossible|frustrating)",
        r"\bi (hate|can'?t stand|don'?t like)",
        r"\b(ugh|argh|damn|shit)\b",
        r"\bso (tired|done|over|frustrating|frustrat)",
        r"\bi feel (terrible|awful|burned out)",
        r"\bfrustrat(ed|ing)\b"
    ]

    # Observation indicators - informational
    observation_patterns = [
        r"\bi noticed\b",
        r"\bjust saw\b",
        r"\b(fyi|heads up|note)\b",
        r"\bi see that\b",
        r"\blooks like\b",
        r"\bapparently\b"
    ]

    # Task indicators - action-oriented
    task_patterns = [
        r"\b(create|add|make|build|implement|write|code)\b",
        r"\b(complete|finish|done with|mark as done)\b",
        r"\b(review|check|look at|analyze)\b",
        r"\bcan you (help|assist|show|teach|guide)\b.*\b(debug|fix|solve|build|create)\b",
        r"\b(need to|have to|must|should) (do|complete|finish|build|create)\b",
        r"\b(help me|assist with|work on)\b.*\b(debug|fix|solve|build|create)\b",
        r"\b(fix|solve|resolve|address)\b",
        r"\b(update|modify|change|edit)\b",
        r"\b(delete|remove|clean up)\b",
        r"\b(schedule|plan|organize)\b",
        r"\b(start|begin|initiate)\b",
        r"\bdebug\b"
    ]

    # Check each category in priority order (before question check)
    # Venting takes highest priority
    for pattern in venting_patterns:
        if re.search(pattern, msg_lower):
            return "venting"

    # Task patterns (check before question)
    for pattern in task_patterns:
        if re.search(pattern, msg_lower):
            return "task"

    # Question indicators - explicit questions
    if "?" in user_message:
        return "question"

    # Question words at start
    question_words = [
        r"^(what|when|where|who|why|how|which|is|are|do|does|did)\b"
    ]
    for pattern in question_words:
        if re.search(pattern, msg_lower):
            return "question"

    # Thinking patterns
    for pattern in thinking_patterns:
        if re.search(pattern, msg_lower):
            return "thinking"

    # Observation patterns
    for pattern in observation_patterns:
        if re.search(pattern, msg_lower):
            return "observation"

    # Default: question (safer than assuming task)
    return "question"


def get_classification_confidence(user_message: str) -> tuple[str, float]:
    """
    Classify input and return confidence score.

    Args:
        user_message: Raw user input

    Returns:
        Tuple of (classification, confidence_score)
    """
    classification = classify_input(user_message)

    # Simple confidence heuristic
    # More specific patterns = higher confidence
    msg_lower = user_message.lower()

    confidence_indicators = {
        "task": [r"\bplease\b", r"\bcan you\b", r"\bcreate\b", r"\badd\b"],
        "question": [r"\?", r"^what\b", r"^how\b"],
        "venting": [r"\bugh\b", r"\btired\b", r"\bfrustrated\b"],
        "thinking": [r"\bwondering\b", r"\bwhat if\b"],
        "observation": [r"\bfyi\b", r"\bnoticed\b"]
    }

    matches = 0
    if classification in confidence_indicators:
        for pattern in confidence_indicators[classification]:
            if re.search(pattern, msg_lower):
                matches += 1

    # Base confidence + bonus per match
    confidence = 0.6 + (matches * 0.15)
    confidence = min(confidence, 1.0)  # Cap at 1.0

    return classification, confidence


if __name__ == "__main__":
    # Test cases
    test_inputs = [
        ("I'm wondering if we should refactor this", "thinking"),
        ("I'm so tired of this bug", "venting"),
        ("I noticed the API is slow", "observation"),
        ("What's on my calendar?", "question"),
        ("Add a task to review Q4 planning", "task"),
        ("Can you help me debug this?", "task"),
        ("This is so frustrating", "venting"),
        ("I'm thinking about changing careers", "thinking")
    ]

    print("Classification Test Results:")
    print("-" * 60)
    for input_text, expected in test_inputs:
        result = classify_input(input_text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{input_text}' → {result} (expected: {expected})")
