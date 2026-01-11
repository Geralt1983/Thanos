#!/usr/bin/env python3
"""
Intent matcher with pre-compiled regex patterns for O(m) keyword matching.

This module provides efficient keyword matching for intent detection in the
ThanosOrchestrator. Instead of O(n*m) substring searches, it uses pre-compiled
regex patterns with alternation groups for O(m) complexity.

Performance characteristics:
- Compilation: O(n) at initialization (one-time cost)
- Matching: O(m) where m = message length
- Expected speedup: 10-50x over nested loop approach

Usage:
    from Tools.intent_matcher import KeywordMatcher

    keywords = {
        'ops': {
            'high': ['overwhelmed', 'what should i do'],
            'medium': ['task', 'schedule'],
            'low': ['busy', 'work']
        }
    }

    triggers = {
        'ops': ['urgent', 'now']
    }

    matcher = KeywordMatcher(keywords, triggers)
    scores = matcher.match("I'm overwhelmed with tasks today")
    # Returns: {'ops': 7}  (high: 5 + medium: 2)
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MatchResult:
    """Result of a keyword match with metadata."""
    agent: str
    keyword: str
    weight: int
    start: int
    end: int


class KeywordMatcher:
    """Pre-compiled regex matcher for efficient intent detection.

    Compiles all keywords into optimized regex patterns at initialization,
    then provides fast O(m) matching via a single regex scan.
    """

    # Scoring weights for different match types
    WEIGHT_TRIGGER = 10
    WEIGHT_HIGH = 5
    WEIGHT_MEDIUM = 2
    WEIGHT_LOW = 1

    def __init__(self, keywords: Dict[str, Dict[str, List[str]]],
                 triggers: Optional[Dict[str, List[str]]] = None):
        """Initialize matcher with keyword dictionaries.

        Args:
            keywords: Nested dict of {agent: {priority: [keywords]}}
                     where priority is 'high', 'medium', or 'low'
            triggers: Optional dict of {agent: [trigger_phrases]}
                     Triggers have highest weight (10 points)
        """
        self.keywords = keywords
        self.triggers = triggers or {}

        # Compiled patterns and their metadata
        self._pattern = None
        self._keyword_map: Dict[str, Tuple[str, int]] = {}

        # Compile patterns at initialization
        self._compile_patterns()

    def _escape_regex(self, text: str) -> str:
        """Escape special regex characters in keyword text.

        Args:
            text: The keyword text to escape

        Returns:
            Escaped text safe for regex
        """
        return re.escape(text)

    def _compile_patterns(self):
        """Compile all keywords into a single optimized regex pattern.

        Creates a pattern like:
        \\b(overwhelmed|task|schedule|...)\\b

        Uses word boundaries (\\b) for proper matching that prevents false positives
        like matching 'task' in 'multitask' or 'focus' in 'refocus'.

        For multi-word phrases like 'what should i do', the word boundaries apply
        to the first and last words, while internal spaces are literal matches.

        With a mapping from each keyword back to (agent, weight) for scoring.
        """
        pattern_parts = []

        # Add triggers first (highest priority in matching)
        for agent, trigger_list in self.triggers.items():
            for trigger in trigger_list:
                escaped = self._escape_regex(trigger.lower())
                pattern_parts.append(escaped)
                self._keyword_map[trigger.lower()] = (agent, self.WEIGHT_TRIGGER)

        # Add keywords by priority
        weight_map = {
            'high': self.WEIGHT_HIGH,
            'medium': self.WEIGHT_MEDIUM,
            'low': self.WEIGHT_LOW
        }

        for agent, priority_dict in self.keywords.items():
            for priority, keyword_list in priority_dict.items():
                weight = weight_map.get(priority, 1)
                for keyword in keyword_list:
                    keyword_lower = keyword.lower()
                    escaped = self._escape_regex(keyword_lower)
                    pattern_parts.append(escaped)
                    # Note: If a keyword appears in multiple agents/priorities,
                    # the last one wins. In practice, keywords should be unique per agent.
                    self._keyword_map[keyword_lower] = (agent, weight)

        if not pattern_parts:
            # Empty pattern - match nothing
            self._pattern = re.compile(r'(?!.*)', re.IGNORECASE)
            return

        # Sort by length (descending) to match longer phrases first
        # This prevents "what should" from matching before "what should i do"
        pattern_parts.sort(key=len, reverse=True)

        # Build alternation pattern with word boundaries
        # The \b ensures we don't match keywords in the middle of other words
        # For example: \b(task)\b won't match 'multitask', only standalone 'task'
        # For multi-word phrases: \b(what\ should\ i\ do)\b ensures both
        # 'what' and 'do' are at word boundaries (spaces are literal in the middle)
        alternation = '|'.join(pattern_parts)

        # Build the final pattern with word boundaries
        # \b is a zero-width assertion that matches:
        # - Between a \w (word char: alphanumeric or _) and \W (non-word char)
        # - At the start/end of string if it borders a word character
        pattern_str = fr'\b({alternation})\b'

        self._pattern = re.compile(pattern_str, re.IGNORECASE)

    def match(self, message: str) -> Dict[str, int]:
        """Match keywords in message and return agent scores.

        Performs a single regex scan over the message and accumulates scores
        for each agent based on matched keywords.

        Args:
            message: The message text to analyze

        Returns:
            Dictionary mapping agent names to total scores
            Example: {'ops': 7, 'health': 2}
        """
        if not message or not self._pattern:
            return {}

        message_lower = message.lower()
        agent_scores: Dict[str, int] = {}

        # Single pass through message
        for match in self._pattern.finditer(message_lower):
            matched_text = match.group(1)

            # Look up the agent and weight for this keyword
            if matched_text in self._keyword_map:
                agent, weight = self._keyword_map[matched_text]

                # Initialize agent score if needed
                if agent not in agent_scores:
                    agent_scores[agent] = 0

                # Accumulate score
                agent_scores[agent] += weight

        return agent_scores

    def match_with_details(self, message: str) -> Tuple[Dict[str, int], List[MatchResult]]:
        """Match keywords and return both scores and match details.

        Useful for debugging and understanding why a particular agent was selected.

        Args:
            message: The message text to analyze

        Returns:
            Tuple of (scores_dict, match_details_list)
            - scores_dict: Same as match() return value
            - match_details_list: List of MatchResult objects with full metadata
        """
        if not message or not self._pattern:
            return {}, []

        message_lower = message.lower()
        agent_scores: Dict[str, int] = {}
        matches: List[MatchResult] = []

        for match in self._pattern.finditer(message_lower):
            matched_text = match.group(1)

            if matched_text in self._keyword_map:
                agent, weight = self._keyword_map[matched_text]

                if agent not in agent_scores:
                    agent_scores[agent] = 0

                agent_scores[agent] += weight

                matches.append(MatchResult(
                    agent=agent,
                    keyword=matched_text,
                    weight=weight,
                    start=match.start(1),
                    end=match.end(1)
                ))

        return agent_scores, matches

    def get_pattern_info(self) -> Dict:
        """Get information about the compiled patterns.

        Useful for debugging and performance analysis.

        Returns:
            Dictionary with pattern statistics:
            - total_keywords: Number of keywords compiled
            - pattern_length: Length of regex pattern string
            - agents: List of agent names with keyword counts
        """
        agent_counts = {}
        for keyword, (agent, weight) in self._keyword_map.items():
            if agent not in agent_counts:
                agent_counts[agent] = 0
            agent_counts[agent] += 1

        return {
            'total_keywords': len(self._keyword_map),
            'pattern_length': len(self._pattern.pattern) if self._pattern else 0,
            'agents': agent_counts
        }


def main():
    """Test the keyword matcher."""
    # Sample keyword structure from ThanosOrchestrator
    keywords = {
        'ops': {
            'high': ['what should i do', 'overwhelmed', 'prioritize'],
            'medium': ['task', 'tasks', 'schedule', 'today'],
            'low': ['busy', 'work']
        },
        'coach': {
            'high': ['i keep doing this', 'pattern', 'accountability'],
            'medium': ['habit', 'stuck', 'motivation'],
            'low': ['feel', 'feeling']
        },
        'strategy': {
            'high': ['long-term', 'strategy', 'goals'],
            'medium': ['revenue', 'growth', 'decision'],
            'low': ['career', 'business']
        },
        'health': {
            'high': ['im tired', 'i cant focus', 'energy'],
            'medium': ['exhausted', 'fatigue', 'focus'],
            'low': ['rest', 'break']
        }
    }

    triggers = {
        'ops': ['urgent', 'asap'],
        'health': ['medication', 'vyvanse']
    }

    matcher = KeywordMatcher(keywords, triggers)

    # Test cases
    test_messages = [
        "I'm overwhelmed with tasks today",
        "What should i do about this long-term strategy?",
        "I keep doing this and feel stuck in a pattern",
        "Im tired and cant focus on work",
        "Need to schedule a meeting asap"
    ]

    print("KeywordMatcher Test")
    print("=" * 60)
    print(f"Pattern info: {matcher.get_pattern_info()}")
    print()

    for msg in test_messages:
        scores, details = matcher.match_with_details(msg)
        print(f"Message: {msg}")
        print(f"Scores: {scores}")
        if details:
            print("Matches:")
            for m in details:
                print(f"  - {m.keyword} ({m.agent}, +{m.weight})")
        print()


if __name__ == "__main__":
    main()
