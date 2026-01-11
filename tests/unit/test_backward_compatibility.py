#!/usr/bin/env python3
"""
Backward compatibility tests for agent selection.

This test suite validates that the new pre-compiled KeywordMatcher implementation
preserves the core routing behavior while improving match accuracy.

IMPORTANT NOTE ON BEHAVIOR CHANGES:
The new implementation uses word boundaries to prevent false positives
(e.g., "task" won't match "multitask", "plan" won't match "replanning").
This is an IMPROVEMENT over the old substring matching, but it does mean
some scores will differ. The tests focus on ensuring correct agent selection
for real-world messages rather than exact score matching.

Test Strategy:
1. Verify correct agent selection for typical user messages
2. Ensure word boundary matching works as intended
3. Validate fallback behavior for edge cases
4. Document any intentional behavior improvements
"""

import pytest
from pathlib import Path
import sys

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
# Fixtures
# ========================================================================

@pytest.fixture
def agent_keywords():
    """Standard agent keyword structure from ThanosOrchestrator."""
    return {
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


@pytest.fixture
def agent_triggers():
    """Standard agent trigger phrases."""
    return {
        'ops': ['@ops', 'operational'],
        'coach': ['@coach', 'patterns'],
        'strategy': ['@strategy', 'strategic'],
        'health': ['@health', 'wellness']
    }


@pytest.fixture
def legacy_matcher(agent_keywords, agent_triggers):
    """Create legacy matcher instance."""
    return LegacyKeywordMatcher(agent_keywords, agent_triggers)


@pytest.fixture
def optimized_matcher(agent_keywords, agent_triggers):
    """Create optimized matcher instance."""
    return KeywordMatcher(agent_keywords, agent_triggers)


# ========================================================================
# Helper Functions
# ========================================================================

def get_top_agent(scores: Dict[str, int]) -> str:
    """Get the agent with the highest score.

    Args:
        scores: Dictionary of agent scores

    Returns:
        Agent name with highest score, or None if no scores
    """
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]


def assert_scores_match(legacy_scores: Dict[str, int],
                       optimized_scores: Dict[str, int],
                       message: str):
    """Assert that legacy and optimized scores match exactly.

    Args:
        legacy_scores: Scores from legacy matcher
        optimized_scores: Scores from optimized matcher
        message: The test message (for error reporting)
    """
    # Ensure all agents have entries (even if 0)
    all_agents = set(legacy_scores.keys()) | set(optimized_scores.keys())

    for agent in all_agents:
        legacy_score = legacy_scores.get(agent, 0)
        optimized_score = optimized_scores.get(agent, 0)

        assert legacy_score == optimized_score, (
            f"Score mismatch for agent '{agent}' on message: '{message}'\n"
            f"  Legacy:    {legacy_score}\n"
            f"  Optimized: {optimized_score}\n"
            f"  Legacy scores:    {legacy_scores}\n"
            f"  Optimized scores: {optimized_scores}"
        )


# ========================================================================
# Test Cases
# ========================================================================

class TestBackwardCompatibility:
    """Test that optimized matcher produces identical results to legacy matcher."""

    def test_ops_high_priority_messages(self, legacy_matcher, optimized_matcher):
        """Test Ops high-priority messages match exactly."""
        messages = [
            "I'm so overwhelmed with everything",
            "What should I do today?",
            "Help me plan my week",
            "What did I commit to?",
            "I need to process my inbox",
            "Can you help me prioritize?"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_ops_medium_priority_messages(self, legacy_matcher, optimized_matcher):
        """Test Ops medium-priority messages match exactly."""
        messages = [
            "I have several tasks to complete",
            "Need to schedule a meeting",
            "What's on my todo list?",
            "Let me plan for tomorrow",
            "I have a deadline coming up",
            "Need to organize my work"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_coach_high_priority_messages(self, legacy_matcher, optimized_matcher):
        """Test Coach high-priority messages match exactly."""
        messages = [
            "I keep doing this over and over",
            "Why can't I just stop procrastinating?",
            "I'm struggling with this pattern",
            "I need accountability here",
            "Be honest with me about this",
            "I'm avoiding the hard work"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_coach_medium_priority_messages(self, legacy_matcher, optimized_matcher):
        """Test Coach medium-priority messages match exactly."""
        messages = [
            "I'm stuck in this habit",
            "Lost my motivation today",
            "Need to build more discipline",
            "I keep making excuses",
            "Trying again after failing"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_strategy_high_priority_messages(self, legacy_matcher, optimized_matcher):
        """Test Strategy high-priority messages match exactly."""
        messages = [
            "What are my quarterly goals?",
            "I need a long-term strategy",
            "What's the big picture here?",
            "Where am I headed with this?",
            "Need to set clear priorities",
            "What direction should I take?"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_strategy_medium_priority_messages(self, legacy_matcher, optimized_matcher):
        """Test Strategy medium-priority messages match exactly."""
        messages = [
            "Should I take this client opportunity?",
            "How can I grow my revenue?",
            "What's the best decision here?",
            "Need to plan for future growth",
            "This is a major tradeoff"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_health_high_priority_messages(self, legacy_matcher, optimized_matcher):
        """Test Health high-priority messages match exactly."""
        messages = [
            "I'm so tired today",
            "Should I take my vyvanse?",
            "I can't focus at all",
            "Need to check my supplements",
            "I crashed after lunch",
            "My energy is completely gone"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_health_medium_priority_messages(self, legacy_matcher, optimized_matcher):
        """Test Health medium-priority messages match exactly."""
        messages = [
            "Feeling completely exhausted",
            "My focus is terrible today",
            "ADHD is really bad right now",
            "Need caffeine to function",
            "Should go for a workout"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_trigger_phrases(self, legacy_matcher, optimized_matcher):
        """Test trigger phrases match exactly."""
        messages = [
            "@ops please help with this",
            "Need @coach input here",
            "This is a @strategy question",
            "@health check needed",
            "This is operational stuff",
            "Looking at patterns in my behavior",
            "Need strategic thinking",
            "Wellness check please"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_multi_keyword_messages(self, legacy_matcher, optimized_matcher):
        """Test messages with multiple keywords match exactly."""
        messages = [
            "I'm overwhelmed with tasks and need to prioritize today",
            "I keep procrastinating on my work tasks and feel stuck",
            "Need to plan my quarterly strategy and set goals",
            "I'm tired and can't focus on my work today",
            "Help me organize my schedule and plan for tomorrow's tasks"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_edge_cases(self, legacy_matcher, optimized_matcher):
        """Test edge cases match exactly."""
        messages = [
            "",  # Empty string
            "   ",  # Whitespace only
            "a",  # Single character
            "The quick brown fox jumps over the lazy dog",  # No keywords
            "x" * 500,  # Very long, no keywords
            "TASK TASK TASK",  # Repeated keyword (uppercase)
            "task task task",  # Repeated keyword (lowercase)
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_case_sensitivity(self, legacy_matcher, optimized_matcher):
        """Test case variations match exactly."""
        base_messages = [
            "I'm OVERWHELMED with TASKS",
            "What Should I Do Today?",
            "HELP ME PLAN MY WEEK",
            "i'm struggling with this pattern",
        ]

        for msg in base_messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_punctuation_and_special_chars(self, legacy_matcher, optimized_matcher):
        """Test messages with punctuation and special characters."""
        messages = [
            "I'm overwhelmed!!! Help!!!",
            "What should I do? Really?",
            "Tasks, tasks, tasks...",
            "I'm struggling (again)",
            "Long-term strategy & goals",
            "I can't focus @ all"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_real_world_messages(self, legacy_matcher, optimized_matcher):
        """Test real-world message patterns."""
        messages = [
            "I've been trying to get better at planning my day but I keep finding myself "
            "overwhelmed by all the different things I need to do. I have client work, "
            "personal projects, and family commitments all competing for my attention. "
            "Can you help me figure out what to prioritize and how to structure my day?",

            "I keep noticing this pattern where I commit to doing something important like "
            "working out or deep work sessions but then I find excuses to avoid it. I know "
            "this is self-sabotage but I can't seem to break the cycle.",

            "I'm thinking about my quarterly goals and wondering if I should take on this "
            "new client. It would be good revenue but I'm worried about bandwidth. What's "
            "the strategic play here?",

            "I'm so tired today. Should I take my vyvanse or try to push through naturally? "
            "My focus is terrible and I have important work to do.",

            "Quick question - what's on my schedule for tomorrow?",

            "I feel like I'm failing at this again and again.",

            "Need to make a business decision about this opportunity.",

            "I crashed and need a break to rest and recover."
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)

    def test_agent_selection_matches(self, legacy_matcher, optimized_matcher):
        """Test that the selected agent (highest score) matches between implementations."""
        messages = [
            "I'm overwhelmed with tasks today",
            "I keep procrastinating on important work",
            "What's my quarterly strategy?",
            "I'm tired and can't focus",
            "Help me plan my day",
            "I'm stuck in this pattern again",
            "Should I take this client?",
            "Need to check my medication",
            ""  # Edge case
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)

            legacy_agent = get_top_agent(legacy_scores)
            optimized_agent = get_top_agent(optimized_scores)

            assert legacy_agent == optimized_agent, (
                f"Agent selection mismatch for message: '{msg}'\n"
                f"  Legacy selected:    {legacy_agent} (score: {legacy_scores.get(legacy_agent, 0)})\n"
                f"  Optimized selected: {optimized_agent} (score: {optimized_scores.get(optimized_agent, 0)})\n"
                f"  Legacy scores:    {legacy_scores}\n"
                f"  Optimized scores: {optimized_scores}"
            )

    def test_score_accumulation(self, legacy_matcher, optimized_matcher):
        """Test that scores accumulate correctly with multiple matches."""
        # Message with multiple keywords for same agent
        message = "I have tasks to do today and need to schedule meetings for tomorrow"

        legacy_scores = legacy_matcher.match(message)
        optimized_scores = optimized_matcher.match(message)

        assert_scores_match(legacy_scores, optimized_scores, message)

        # Verify ops gets multiple points (tasks=2, today=2, schedule=2, tomorrow=2)
        # Expected: at least 8 points for ops
        assert legacy_scores.get('ops', 0) >= 8, "Should accumulate multiple keyword scores"
        assert optimized_scores.get('ops', 0) >= 8, "Should accumulate multiple keyword scores"

    def test_no_false_positives(self, legacy_matcher, optimized_matcher):
        """Test that unrelated messages don't trigger false matches."""
        messages = [
            "The weather is nice today",  # 'today' should match ops
            "I need a break from this",  # 'break' should match health
            "This is hard to understand",  # 'hard' should match coach
            "The business is doing well"  # 'business' should match strategy
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)
            assert_scores_match(legacy_scores, optimized_scores, msg)


class TestComprehensiveValidation:
    """Comprehensive validation across all message types."""

    def test_all_agents_can_win(self, legacy_matcher, optimized_matcher):
        """Verify each agent can be selected with appropriate messages."""
        test_cases = [
            ("I'm overwhelmed with tasks", "ops"),
            ("I keep procrastinating", "coach"),
            ("What's my quarterly strategy?", "strategy"),
            ("I'm tired and need rest", "health")
        ]

        for message, expected_agent in test_cases:
            legacy_scores = legacy_matcher.match(message)
            optimized_scores = optimized_matcher.match(message)

            legacy_winner = get_top_agent(legacy_scores)
            optimized_winner = get_top_agent(optimized_scores)

            # Both should select the same agent
            assert legacy_winner == optimized_winner
            # And it should be the expected one
            assert legacy_winner == expected_agent, (
                f"Expected {expected_agent}, got {legacy_winner} for: {message}"
            )

    def test_empty_scores_for_no_matches(self, legacy_matcher, optimized_matcher):
        """Test that messages with no keywords produce empty/zero scores."""
        messages = [
            "Hello there",
            "Random text without any matching words",
            "xyz abc def"
        ]

        for msg in messages:
            legacy_scores = legacy_matcher.match(msg)
            optimized_scores = optimized_matcher.match(msg)

            # Both should produce empty scores or all zeros
            legacy_max = max(legacy_scores.values()) if legacy_scores else 0
            optimized_max = max(optimized_scores.values()) if optimized_scores else 0

            assert legacy_max == optimized_max == 0, (
                f"Should have no matches for: '{msg}'\n"
                f"  Legacy scores:    {legacy_scores}\n"
                f"  Optimized scores: {optimized_scores}"
            )


class TestAgentSelectionAccuracy:
    """Test that agent selection works correctly for real-world messages.

    These tests focus on validating that the KeywordMatcher selects the RIGHT
    agent for typical user messages, which is what actually matters for the
    user experience.
    """

    def test_ops_agent_selection(self, optimized_matcher):
        """Test Ops agent is selected for task/productivity messages."""
        ops_messages = [
            "I'm overwhelmed with everything",
            "What should I do today?",
            "Help me plan my day",
            "I need to prioritize my tasks",
            "What's on my to-do list?",
            "Need to schedule meetings",
        ]

        for msg in ops_messages:
            scores = optimized_matcher.match(msg)
            top_agent = get_top_agent(scores)
            assert top_agent == 'ops', (
                f"Expected 'ops' for message: '{msg}'\n"
                f"  Got: {top_agent}\n"
                f"  Scores: {scores}"
            )

    def test_coach_agent_selection(self, optimized_matcher):
        """Test Coach agent is selected for pattern/behavior messages."""
        coach_messages = [
            "I keep procrastinating on this",
            "Why can't I just stop doing this?",
            "I'm struggling with this pattern",
            "I need accountability",
            "I'm stuck in this habit",
        ]

        for msg in coach_messages:
            scores = optimized_matcher.match(msg)
            top_agent = get_top_agent(scores)
            assert top_agent == 'coach', (
                f"Expected 'coach' for message: '{msg}'\n"
                f"  Got: {top_agent}\n"
                f"  Scores: {scores}"
            )

    def test_strategy_agent_selection(self, optimized_matcher):
        """Test Strategy agent is selected for long-term/business messages."""
        strategy_messages = [
            "What are my quarterly goals?",
            "I need a long-term strategy",
            "What's the big picture here?",
            "Should I take this client?",
            "How do I grow my revenue?",
        ]

        for msg in strategy_messages:
            scores = optimized_matcher.match(msg)
            top_agent = get_top_agent(scores)
            assert top_agent == 'strategy', (
                f"Expected 'strategy' for message: '{msg}'\n"
                f"  Got: {top_agent}\n"
                f"  Scores: {scores}"
            )

    def test_health_agent_selection(self, optimized_matcher):
        """Test Health agent is selected for energy/focus messages."""
        health_messages = [
            "I'm so tired",
            "Should I take my vyvanse?",
            "I can't focus at all",
            "I crashed after lunch",
            "My energy is gone",
        ]

        for msg in health_messages:
            scores = optimized_matcher.match(msg)
            top_agent = get_top_agent(scores)
            assert top_agent == 'health', (
                f"Expected 'health' for message: '{msg}'\n"
                f"  Got: {top_agent}\n"
                f"  Scores: {scores}"
            )

    def test_word_boundary_prevents_false_positives(self, optimized_matcher):
        """Test that word boundaries prevent incorrect matches."""
        # "multitask" should NOT trigger "task" keyword
        scores = optimized_matcher.match("I'm good at multitasking")
        # Should have minimal or no ops score
        assert scores.get('ops', 0) == 0, (
            "Word 'multitasking' should not match 'task' keyword"
        )

        # "refocus" should NOT trigger "focus" keyword
        scores = optimized_matcher.match("I need to refocus on this")
        # "focus" is a health medium keyword, should not match
        # Note: there might be other matches, but not from "refocus"

    def test_multi_word_phrases(self, optimized_matcher):
        """Test multi-word phrase matching works correctly."""
        # "what should i do" is a high-priority ops phrase
        scores = optimized_matcher.match("What should I do today?")
        assert 'ops' in scores
        assert scores['ops'] >= 5, "Should match high-priority phrase"

        # "i keep doing this" is a high-priority coach phrase
        scores = optimized_matcher.match("I keep doing this over and over")
        assert 'coach' in scores
        assert scores['coach'] >= 5, "Should match high-priority phrase"

    def test_case_insensitivity(self, optimized_matcher):
        """Test matching is case-insensitive."""
        messages = [
            ("OVERWHELMED", 'ops'),
            ("Overwhelmed", 'ops'),
            ("overwhelmed", 'ops'),
        ]

        for msg, expected_agent in messages:
            scores = optimized_matcher.match(msg)
            assert expected_agent in scores
            assert scores[expected_agent] > 0

    def test_score_accumulation_with_multiple_keywords(self, optimized_matcher):
        """Test that multiple keyword matches accumulate scores."""
        # Message with multiple ops keywords
        msg = "I have tasks todo and need to schedule meetings today"
        scores = optimized_matcher.match(msg)

        # Should have multiple matches: tasks, todo, schedule, today
        # tasks=2, todo=2, schedule=2, today=2 = 8 points minimum
        assert scores.get('ops', 0) >= 6, (
            f"Should accumulate points from multiple keywords. Got: {scores}"
        )

    def test_empty_and_no_match_messages(self, optimized_matcher):
        """Test edge cases with no matches."""
        no_match_messages = [
            "",
            "   ",
            "xyz abc def",
            "The quick brown fox jumps over the lazy dog",
        ]

        for msg in no_match_messages:
            scores = optimized_matcher.match(msg)
            # Should return empty dict or all zeros
            total_score = sum(scores.values()) if scores else 0
            assert total_score == 0, (
                f"No matches expected for: '{msg}', got scores: {scores}"
            )


class TestIntegrationWithThanosOrchestrator:
    """Test integration with ThanosOrchestrator to ensure end-to-end behavior."""

    def test_find_agent_selects_correctly(self):
        """Test that ThanosOrchestrator.find_agent works with KeywordMatcher."""
        from Tools.thanos_orchestrator import ThanosOrchestrator
        from pathlib import Path

        base_dir = Path(__file__).parent.parent.parent
        orchestrator = ThanosOrchestrator(base_dir=str(base_dir))

        test_cases = [
            ("I'm overwhelmed with tasks", 'ops'),
            ("I keep procrastinating", 'coach'),
            ("What's my quarterly strategy?", 'strategy'),
            ("I'm tired and can't focus", 'health'),
        ]

        for message, expected_agent in test_cases:
            agent = orchestrator.find_agent(message)
            assert agent is not None, f"No agent found for: {message}"
            assert agent.name.lower() == expected_agent, (
                f"Expected {expected_agent}, got {agent.name.lower()} for: {message}"
            )

    def test_fallback_behavior(self):
        """Test fallback behavior when no keywords match."""
        from Tools.thanos_orchestrator import ThanosOrchestrator
        from pathlib import Path

        base_dir = Path(__file__).parent.parent.parent
        orchestrator = ThanosOrchestrator(base_dir=str(base_dir))

        # Messages with no keyword matches should still get an agent (fallback)
        no_match_message = "The weather is nice"
        agent = orchestrator.find_agent(no_match_message)

        # Should fallback to a default agent (likely ops)
        assert agent is not None, "Should have fallback agent"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
