#!/usr/bin/env python3
"""
Commitment Detector - Pattern-based NLP detection of commitment statements.

Detects commitment phrases in natural language conversation and extracts:
- Person (who the commitment is to)
- Action (what is being committed to)
- Deadline (when it should be done)

Designed to integrate with RelationshipTracker and CommitmentTracker to prevent
ADHD-related relationship decay through forgotten promises.

Key Classes:
    CommitmentDetector: Core pattern matching engine
    DetectedCommitment: Container for detected commitment data

Usage:
    from Tools.commitment_detector import CommitmentDetector

    detector = CommitmentDetector()

    # Detect commitment in text
    result = detector.detect("I promised to call Mom this weekend")
    if result:
        print(f"Person: {result.person}")
        print(f"Action: {result.action}")
        print(f"Deadline: {result.deadline_phrase}")

Commitment Patterns Detected:
    - "I promised [person] [action]"
    - "I'll [action] [person]"
    - "I will [action]"
    - "I'm going to [action]"
    - "I need to [action]"
    - "I should [action]"
    - "Remind me to [action]"
    - "I have to [action]"
    - "I've got to [action]"
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple


@dataclass
class DetectedCommitment:
    """Container for detected commitment data."""

    raw_text: str
    pattern_matched: str
    action: Optional[str] = None
    person: Optional[str] = None
    deadline_phrase: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "raw_text": self.raw_text,
            "pattern_matched": self.pattern_matched,
            "action": self.action,
            "person": self.person,
            "deadline_phrase": self.deadline_phrase,
            "confidence": self.confidence,
        }


class CommitmentDetector:
    """
    Pre-compiled regex matcher for commitment phrase detection.

    Uses optimized regex patterns to identify commitment statements
    in natural language conversation. Follows the pattern established
    by intent_matcher.py for efficient keyword matching.

    Attributes:
        patterns: List of compiled regex patterns for commitment detection
        person_patterns: List of compiled patterns for person extraction
    """

    # Commitment trigger phrases with confidence weights
    # High confidence (0.9): Strong explicit commitments
    HIGH_CONFIDENCE_PATTERNS = [
        r"\bI promised\b",
        r"\bI'll make sure\b",
        r"\bI commit to\b",
        r"\bI swear\b",
    ]

    # Medium confidence (0.7): Clear intent but less formal
    MEDIUM_CONFIDENCE_PATTERNS = [
        r"\bI'll\b",
        r"\bI will\b",
        r"\bI'm going to\b",
        r"\bI need to\b",
        r"\bI have to\b",
        r"\bI've got to\b",
        r"\bI gotta\b",
        r"\bRemind me to\b",
        r"\bI should\b",
    ]

    # Low confidence (0.5): Weak or conditional commitments
    LOW_CONFIDENCE_PATTERNS = [
        r"\bI might\b",
        r"\bI could\b",
        r"\bmaybe I'll\b",
        r"\bI ought to\b",
    ]

    def __init__(self):
        """Initialize detector with pre-compiled patterns."""
        # Compile all commitment patterns
        self.patterns: List[Tuple[re.Pattern, float, str]] = []

        # High confidence patterns
        for pattern_str in self.HIGH_CONFIDENCE_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            self.patterns.append((pattern, 0.9, pattern_str))

        # Medium confidence patterns
        for pattern_str in self.MEDIUM_CONFIDENCE_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            self.patterns.append((pattern, 0.7, pattern_str))

        # Low confidence patterns
        for pattern_str in self.LOW_CONFIDENCE_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            self.patterns.append((pattern, 0.5, pattern_str))

        # Compile person extraction patterns
        # Matches capitalized names in common commitment contexts
        self.person_patterns = [
            # "I promised [Person] that..."
            re.compile(r"\bI promised\s+([A-Z][a-z]+)\b", re.IGNORECASE),
            # "I'll tell [Person] about..."
            re.compile(r"\bI'll\s+(?:tell|call|text|email|message)\s+([A-Z][a-z]+)\b", re.IGNORECASE),
            # "I will call [Person]"
            re.compile(r"\bI will\s+(?:call|text|email|message|tell)\s+([A-Z][a-z]+)\b", re.IGNORECASE),
            # "I need to call [Person]"
            re.compile(r"\b(?:need|have|got)\s+to\s+(?:call|text|email|message|tell)\s+([A-Z][a-z]+)\b", re.IGNORECASE),
            # General pattern: any capitalized word (likely a name)
            re.compile(r"\b([A-Z][a-z]+)\b"),
        ]

        # Compile deadline extraction patterns
        self.deadline_patterns = [
            # Specific times
            re.compile(r"\b(today|tonight|tomorrow)\b", re.IGNORECASE),
            re.compile(r"\b(this\s+(?:morning|afternoon|evening|week|weekend|month))\b", re.IGNORECASE),
            re.compile(r"\b(next\s+(?:week|month|year|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))\b", re.IGNORECASE),
            re.compile(r"\b(by\s+(?:Friday|Monday|Tuesday|Wednesday|Thursday|Saturday|Sunday|tomorrow|tonight|the\s+end\s+of\s+the\s+week))\b", re.IGNORECASE),
            re.compile(r"\b(in\s+(?:a\s+(?:few|couple)\s+(?:hours|days|weeks)|an?\s+hour|a\s+day|a\s+week))\b", re.IGNORECASE),
            # Days of week
            re.compile(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", re.IGNORECASE),
        ]

    def detect(self, text: str) -> Optional[DetectedCommitment]:
        """
        Detect commitment patterns in text.

        Args:
            text: The input text to analyze

        Returns:
            DetectedCommitment if a commitment is found, None otherwise
        """
        if not text or not isinstance(text, str):
            return None

        # Check for commitment patterns
        best_match = None
        best_confidence = 0.0
        best_pattern = None

        for pattern, confidence, pattern_str in self.patterns:
            match = pattern.search(text)
            if match and confidence > best_confidence:
                best_match = match
                best_confidence = confidence
                best_pattern = pattern_str

        if not best_match:
            return None

        # Extract the action (text after the commitment phrase)
        action = self._extract_action(text, best_match)

        # Extract person if present
        person = self._extract_person(text)

        # Extract deadline if present
        deadline_phrase = self._extract_deadline(text)

        return DetectedCommitment(
            raw_text=text,
            pattern_matched=best_pattern,
            action=action,
            person=person,
            deadline_phrase=deadline_phrase,
            confidence=best_confidence,
        )

    def _extract_action(self, text: str, match: re.Match) -> Optional[str]:
        """
        Extract the action part of the commitment.

        Args:
            text: Full text
            match: Regex match object for the commitment pattern

        Returns:
            The action phrase, or None if not found
        """
        # Get text after the commitment phrase
        action_text = text[match.end():].strip()

        if not action_text:
            return None

        # Remove leading "that", "to", etc.
        action_text = re.sub(r"^(?:that|to)\s+", "", action_text, flags=re.IGNORECASE)

        # Truncate at sentence boundaries (., !, ?)
        sentence_end = re.search(r"[.!?]", action_text)
        if sentence_end:
            action_text = action_text[:sentence_end.start()]

        return action_text.strip() if action_text else None

    def _extract_person(self, text: str) -> Optional[str]:
        """
        Extract person name from commitment text.

        Tries multiple patterns in order of specificity:
        1. Context-specific patterns ("I promised Ashley...")
        2. General capitalized word patterns

        Args:
            text: The full text to analyze

        Returns:
            Person name if found, None otherwise
        """
        for pattern in self.person_patterns:
            match = pattern.search(text)
            if match:
                person = match.group(1)
                # Filter out common false positives
                if person.lower() not in ["i", "a", "the", "to", "this", "that"]:
                    return person

        return None

    def _extract_deadline(self, text: str) -> Optional[str]:
        """
        Extract deadline/time phrase from commitment text.

        Args:
            text: The full text to analyze

        Returns:
            Deadline phrase if found, None otherwise
        """
        for pattern in self.deadline_patterns:
            match = pattern.search(text)
            if match:
                return match.group(0)

        return None

    def detect_batch(self, texts: List[str]) -> List[Optional[DetectedCommitment]]:
        """
        Detect commitments in multiple texts.

        Args:
            texts: List of text strings to analyze

        Returns:
            List of DetectedCommitment objects (None for non-matches)
        """
        return [self.detect(text) for text in texts]


# Convenience function for quick detection
def detect_commitment(text: str) -> Optional[DetectedCommitment]:
    """
    Convenience function for one-off commitment detection.

    Args:
        text: The text to analyze

    Returns:
        DetectedCommitment if found, None otherwise

    Usage:
        from Tools.commitment_detector import detect_commitment

        result = detect_commitment("I promised to call Mom")
        if result:
            print(f"Found commitment: {result.action}")
    """
    detector = CommitmentDetector()
    return detector.detect(text)
