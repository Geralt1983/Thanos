#!/usr/bin/env python3
"""
Standalone runner for backward compatibility tests.
Runs the tests without requiring pytest to be installed.
"""

import sys
from pathlib import Path

# Ensure Thanos is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.intent_matcher import KeywordMatcher
from typing import Dict, List


# ========================================================================
# Legacy Implementation (for comparison)
# ========================================================================

class LegacyKeywordMatcher:
    """Legacy O(n*m) implementation using nested loops.

    This is the original implementation that was replaced by the optimized
    KeywordMatcher. We use it here to validate backward compatibility.
    """

    def __init__(self, agent_keywords: Dict[str, Dict[str, List[str]]],
                 agent_triggers: Dict[str, List[str]] = None):
        """Initialize with keyword dictionaries.

        Args:
            agent_keywords: Nested dict of {agent: {priority: [keywords]}}
            agent_triggers: Optional dict of {agent: [triggers]}
        """
        self.agent_keywords = agent_keywords
        self.agent_triggers = agent_triggers or {}

    def match(self, message: str) -> Dict[str, int]:
        """Match message using O(n*m) nested loops (legacy approach).

        Args:
            message: User message to match

        Returns:
            Dictionary of {agent_name: score}
        """
        message_lower = message.lower()
        agent_scores = {}

        # First pass: Check triggers (10 points each)
        for agent_name, triggers in self.agent_triggers.items():
            if agent_name not in agent_scores:
                agent_scores[agent_name] = 0
            for trigger in triggers:
                if trigger.lower() in message_lower:
                    agent_scores[agent_name] += 10

        # Second pass: Check keywords by priority
        for agent_name, priorities in self.agent_keywords.items():
            if agent_name not in agent_scores:
                agent_scores[agent_name] = 0

            # High priority: 5 points
            for keyword in priorities.get('high', []):
                if keyword in message_lower:
                    agent_scores[agent_name] += 5

            # Medium priority: 2 points
            for keyword in priorities.get('medium', []):
                if keyword in message_lower:
                    agent_scores[agent_name] += 2

            # Low priority: 1 point
            for keyword in priorities.get('low', []):
                if keyword in message_lower:
                    agent_scores[agent_name] += 1

        return agent_scores


# ========================================================================
# Test Data
# ========================================================================

AGENT_KEYWORDS = {
    'ops': {
        'high': ['what should i do', 'whats on my plate', 'help me plan', 'overwhelmed',
                 'what did i commit', 'process inbox', 'clear my inbox', 'prioritize'],
        'medium': ['task', 'tasks', 'todo', 'to-do', 'schedule', 'plan', 'organize',
                   'today', 'tomorrow', 'this week', 'deadline', 'due'],
        'low': ['busy', 'work', 'productive', 'efficiency']
    },
    'coach': {
        'high': ['i keep doing this', 'why cant i', 'im struggling', 'pattern',
                 'be honest', 'accountability', 'avoiding', 'procrastinating'],
        'medium': ['habit', 'stuck', 'motivation', 'discipline', 'consistent',
                   'excuse', 'failing', 'trying', 'again'],
        'low': ['feel', 'feeling', 'hard', 'difficult']
    },
    'strategy': {
        'high': ['quarterly', 'long-term', 'strategy', 'goals', 'where am i headed',
                 'big picture', 'priorities', 'direction'],
        'medium': ['should i take this client', 'revenue', 'growth', 'future',
                   'planning', 'decision', 'tradeoff', 'invest'],
        'low': ['career', 'business', 'opportunity', 'risk']
    },
    'health': {
        'high': ['im tired', 'should i take my vyvanse', 'i cant focus', 'supplements',
                 'i crashed', 'energy', 'sleep', 'medication'],
        'medium': ['exhausted', 'fatigue', 'focus', 'concentration', 'adhd',
                   'stimulant', 'caffeine', 'workout', 'exercise'],
        'low': ['rest', 'break', 'recovery', 'burnout']
    }
}

AGENT_TRIGGERS = {
    'ops': ['@ops', 'operational'],
    'coach': ['@coach', 'patterns'],
    'strategy': ['@strategy', 'strategic'],
    'health': ['@health', 'wellness']
}


# ========================================================================
# Test Helper Functions
# ========================================================================

def get_top_agent(scores: Dict[str, int]) -> str:
    """Get the agent with the highest score."""
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]


def assert_scores_match(legacy_scores: Dict[str, int],
                       optimized_scores: Dict[str, int],
                       message: str):
    """Assert that legacy and optimized scores match exactly."""
    all_agents = set(legacy_scores.keys()) | set(optimized_scores.keys())

    for agent in all_agents:
        legacy_score = legacy_scores.get(agent, 0)
        optimized_score = optimized_scores.get(agent, 0)

        if legacy_score != optimized_score:
            raise AssertionError(
                f"Score mismatch for agent '{agent}' on message: '{message}'\n"
                f"  Legacy:    {legacy_score}\n"
                f"  Optimized: {optimized_score}\n"
                f"  Legacy scores:    {legacy_scores}\n"
                f"  Optimized scores: {optimized_scores}"
            )


# ========================================================================
# Test Cases
# ========================================================================

def run_all_tests():
    """Run all backward compatibility tests."""
    legacy_matcher = LegacyKeywordMatcher(AGENT_KEYWORDS, AGENT_TRIGGERS)
    optimized_matcher = KeywordMatcher(AGENT_KEYWORDS, AGENT_TRIGGERS)

    tests_run = 0
    tests_passed = 0
    tests_failed = 0

    print("=" * 70)
    print("BACKWARD COMPATIBILITY VALIDATION")
    print("=" * 70)
    print(f"Testing: Legacy O(n*m) vs Optimized O(m) KeywordMatcher")
    print()

    # Test suite
    test_suites = {
        "Ops High Priority": [
            "I'm so overwhelmed with everything",
            "What should I do today?",
            "Help me plan my week",
            "What did I commit to?",
            "I need to process my inbox",
            "Can you help me prioritize?"
        ],
        "Ops Medium Priority": [
            "I have several tasks to complete",
            "Need to schedule a meeting",
            "What's on my todo list?",
            "Let me plan for tomorrow",
            "I have a deadline coming up",
            "Need to organize my work"
        ],
        "Coach High Priority": [
            "I keep doing this over and over",
            "Why can't I just stop procrastinating?",
            "I'm struggling with this pattern",
            "I need accountability here",
            "Be honest with me about this",
            "I'm avoiding the hard work"
        ],
        "Coach Medium Priority": [
            "I'm stuck in this habit",
            "Lost my motivation today",
            "Need to build more discipline",
            "I keep making excuses",
            "Trying again after failing"
        ],
        "Strategy High Priority": [
            "What are my quarterly goals?",
            "I need a long-term strategy",
            "What's the big picture here?",
            "Where am I headed with this?",
            "Need to set clear priorities",
            "What direction should I take?"
        ],
        "Strategy Medium Priority": [
            "Should I take this client opportunity?",
            "How can I grow my revenue?",
            "What's the best decision here?",
            "Need to plan for future growth",
            "This is a major tradeoff"
        ],
        "Health High Priority": [
            "I'm so tired today",
            "Should I take my vyvanse?",
            "I can't focus at all",
            "Need to check my supplements",
            "I crashed after lunch",
            "My energy is completely gone"
        ],
        "Health Medium Priority": [
            "Feeling completely exhausted",
            "My focus is terrible today",
            "ADHD is really bad right now",
            "Need caffeine to function",
            "Should go for a workout"
        ],
        "Trigger Phrases": [
            "@ops please help with this",
            "Need @coach input here",
            "This is a @strategy question",
            "@health check needed",
            "This is operational stuff",
            "Looking at patterns in my behavior",
            "Need strategic thinking",
            "Wellness check please"
        ],
        "Multi-Keyword Messages": [
            "I'm overwhelmed with tasks and need to prioritize today",
            "I keep procrastinating on my work tasks and feel stuck",
            "Need to plan my quarterly strategy and set goals",
            "I'm tired and can't focus on my work today",
            "Help me organize my schedule and plan for tomorrow's tasks"
        ],
        "Edge Cases": [
            "",  # Empty string
            "   ",  # Whitespace only
            "a",  # Single character
            "The quick brown fox jumps over the lazy dog",  # No keywords
            "TASK TASK TASK",  # Repeated keyword (uppercase)
            "task task task",  # Repeated keyword (lowercase)
        ],
        "Real World Messages": [
            "I've been trying to get better at planning my day but I keep finding myself "
            "overwhelmed by all the different things I need to do.",

            "I keep noticing this pattern where I commit to doing something important like "
            "working out but then I find excuses to avoid it.",

            "I'm thinking about my quarterly goals and wondering if I should take on this "
            "new client.",

            "I'm so tired today. Should I take my vyvanse or try to push through naturally?",

            "Quick question - what's on my schedule for tomorrow?",
        ]
    }

    for suite_name, messages in test_suites.items():
        print(f"\n{suite_name}:")
        print("-" * 70)

        for msg in messages:
            tests_run += 1
            try:
                legacy_scores = legacy_matcher.match(msg)
                optimized_scores = optimized_matcher.match(msg)
                assert_scores_match(legacy_scores, optimized_scores, msg)

                legacy_agent = get_top_agent(legacy_scores)
                optimized_agent = get_top_agent(optimized_scores)

                if legacy_agent != optimized_agent:
                    raise AssertionError(
                        f"Agent selection mismatch!\n"
                        f"  Message: '{msg}'\n"
                        f"  Legacy:    {legacy_agent}\n"
                        f"  Optimized: {optimized_agent}"
                    )

                tests_passed += 1
                msg_preview = msg[:50] + "..." if len(msg) > 50 else msg
                print(f"  ✓ {msg_preview}")

            except AssertionError as e:
                tests_failed += 1
                print(f"  ✗ FAILED: {msg[:50]}")
                print(f"    {str(e)}")

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests:  {tests_run}")
    print(f"Passed:       {tests_passed} ✓")
    print(f"Failed:       {tests_failed} ✗")
    print()

    if tests_failed == 0:
        print("SUCCESS: All tests passed! ✓")
        print("The optimized KeywordMatcher produces identical results to the legacy implementation.")
        return 0
    else:
        print("FAILURE: Some tests failed! ✗")
        print("The implementations do not match perfectly.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
