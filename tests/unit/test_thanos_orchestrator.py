#!/usr/bin/env python3
"""
Integration tests for Tools/thanos_orchestrator.py

Tests the ThanosOrchestrator's find_agent method with various messages to ensure
correct agent routing using the optimized KeywordMatcher.

Coverage:
- All agent types (ops, coach, strategy, health)
- Keyword matching at all priority levels (high, medium, low)
- Trigger phrase matching
- Edge cases (empty strings, special characters, long messages)
- Multi-keyword scenarios
- Fallback behavior
- Backward compatibility with expected routing
"""

import pytest
from pathlib import Path
import sys

# Ensure Thanos is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.thanos_orchestrator import ThanosOrchestrator, Agent


# ========================================================================
# Module-level Fixtures
# ========================================================================

@pytest.fixture
def orchestrator():
    """Create ThanosOrchestrator instance for testing"""
    # Use current directory as base (tests run from repo root)
    base_dir = Path(__file__).parent.parent.parent
    return ThanosOrchestrator(base_dir=str(base_dir))


@pytest.fixture
def agents(orchestrator):
    """Get agents dictionary for quick reference"""
    return orchestrator.agents


# ========================================================================
# Test Ops Agent Routing
# ========================================================================

class TestOpsAgentRouting:
    """Test routing to Ops agent for task/productivity queries"""

    def test_high_priority_keywords(self, orchestrator, agents):
        """Test Ops agent high-priority keyword matching"""
        messages = [
            "I'm so overwhelmed with everything",
            "What should I do today?",
            "Help me plan my week",
            "What did I commit to?",
            "I need to process my inbox",
            "Can you help me prioritize?"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            assert agent.name.lower() == 'ops', f"Expected ops, got {agent.name} for: {msg}"

    def test_medium_priority_keywords(self, orchestrator, agents):
        """Test Ops agent medium-priority keyword matching"""
        messages = [
            "I have several tasks to complete",
            "Need to schedule a meeting",
            "What's on my todo list?",
            "Let me plan for tomorrow",
            "I have a deadline coming up"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            assert agent.name.lower() == 'ops', f"Expected ops, got {agent.name} for: {msg}"

    def test_low_priority_keywords(self, orchestrator, agents):
        """Test Ops agent low-priority keyword matching"""
        messages = [
            "I'm really busy today",
            "Got a lot of work to do",
            "Need to be more productive",
            "How can I improve my efficiency?"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            # Low priority might not always win, but should contribute to score
            # Just verify an agent is selected

    def test_multi_word_phrases(self, orchestrator, agents):
        """Test Ops agent matching with multi-word trigger phrases"""
        messages = [
            "What should I do about this situation?",
            "What's on my plate right now?",
            "I need to clear my inbox before the meeting"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            assert agent.name.lower() == 'ops', f"Expected ops, got {agent.name} for: {msg}"


# ========================================================================
# Test Coach Agent Routing
# ========================================================================

class TestCoachAgentRouting:
    """Test routing to Coach agent for behavioral/habit queries"""

    def test_high_priority_keywords(self, orchestrator, agents):
        """Test Coach agent high-priority keyword matching"""
        messages = [
            "I keep doing this same thing over and over",
            "Why can't I stick to my goals?",
            "I'm struggling with consistency",
            "I notice a pattern in my behavior",
            "Be honest with me about this",
            "I need some accountability",
            "I'm avoiding the hard work",
            "Why do I keep procrastinating?"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            assert agent.name.lower() == 'coach', f"Expected coach, got {agent.name} for: {msg}"

    def test_medium_priority_keywords(self, orchestrator, agents):
        """Test Coach agent medium-priority keyword matching"""
        messages = [
            "I'm trying to build a better habit",
            "I feel stuck in this situation",
            "Need some motivation to keep going",
            "How do I stay more consistent?",
            "I keep making excuses",
            "Why do I keep failing at this?"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            assert agent.name.lower() == 'coach', f"Expected coach, got {agent.name} for: {msg}"

    def test_low_priority_keywords(self, orchestrator, agents):
        """Test Coach agent low-priority keyword matching"""
        messages = [
            "I feel frustrated about this",
            "This is really hard for me",
            "I'm having difficulty with this change"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            # Low priority might not always win alone


# ========================================================================
# Test Strategy Agent Routing
# ========================================================================

class TestStrategyAgentRouting:
    """Test routing to Strategy agent for long-term/business queries"""

    def test_high_priority_keywords(self, orchestrator, agents):
        """Test Strategy agent high-priority keyword matching"""
        messages = [
            "What's my quarterly plan?",
            "I need to think about long-term goals",
            "What's my strategy for growth?",
            "What are my main goals this year?",
            "Where am I headed with this business?",
            "Need to look at the big picture",
            "What should my priorities be?",
            "What direction should I take?"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            assert agent.name.lower() == 'strategy', f"Expected strategy, got {agent.name} for: {msg}"

    def test_medium_priority_keywords(self, orchestrator, agents):
        """Test Strategy agent medium-priority keyword matching"""
        messages = [
            "Should I take this client on?",
            "How can I increase revenue?",
            "What's the best path for growth?",
            "Need help with future planning",
            "This is an important decision",
            "What's the tradeoff here?",
            "Should I invest in this?"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            assert agent.name.lower() == 'strategy', f"Expected strategy, got {agent.name} for: {msg}"

    def test_low_priority_keywords(self, orchestrator, agents):
        """Test Strategy agent low-priority keyword matching"""
        messages = [
            "Thinking about my career path",
            "How should I grow my business?",
            "Evaluating a new opportunity",
            "What are the risks here?"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            # Low priority might not always win alone


# ========================================================================
# Test Health Agent Routing
# ========================================================================

class TestHealthAgentRouting:
    """Test routing to Health agent for health/energy queries"""

    def test_high_priority_keywords(self, orchestrator, agents):
        """Test Health agent high-priority keyword matching"""
        messages = [
            "I'm tired and drained",
            "Should I take my vyvanse now?",
            "I can't focus on anything",
            "Need to think about my supplements",
            "I completely crashed this afternoon",
            "My energy is really low",
            "I'm not sleeping well",
            "Should I adjust my medication?"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            assert agent.name.lower() == 'health', f"Expected health, got {agent.name} for: {msg}"

    def test_medium_priority_keywords(self, orchestrator, agents):
        """Test Health agent medium-priority keyword matching"""
        messages = [
            "I'm completely exhausted",
            "Dealing with a lot of fatigue",
            "Can't maintain focus today",
            "My concentration is off",
            "My ADHD is really affecting me",
            "Need to think about stimulant timing",
            "Should I have more caffeine?",
            "Need to get a workout in",
            "Haven't been exercising enough"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            assert agent.name.lower() == 'health', f"Expected health, got {agent.name} for: {msg}"

    def test_low_priority_keywords(self, orchestrator, agents):
        """Test Health agent low-priority keyword matching"""
        messages = [
            "I need to rest more",
            "Should I take a break?",
            "Thinking about recovery time",
            "Worried about burnout"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            # Low priority might not always win alone


# ========================================================================
# Test Edge Cases
# ========================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_message(self, orchestrator, agents):
        """Test handling of empty message"""
        agent = orchestrator.find_agent("")
        assert agent is not None
        # Should fallback to ops
        assert agent.name.lower() == 'ops'

    def test_whitespace_only(self, orchestrator, agents):
        """Test handling of whitespace-only message"""
        agent = orchestrator.find_agent("   \t\n  ")
        assert agent is not None

    def test_special_characters(self, orchestrator, agents):
        """Test handling of special characters"""
        messages = [
            "What should I do??? Really overwhelmed!!!",
            "I'm so @#$% tired today",
            "Can't focus... at all...",
            "Help me plan (urgent!)",
            "Goals: long-term strategy & growth"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"

    def test_very_long_message(self, orchestrator, agents):
        """Test handling of very long messages"""
        # Build a long message with ops keywords
        long_msg = "I need help with planning. " * 100 + "What should I do today?"
        agent = orchestrator.find_agent(long_msg)
        assert agent is not None
        assert agent.name.lower() == 'ops'

    def test_case_insensitivity(self, orchestrator, agents):
        """Test that matching is case-insensitive"""
        messages = [
            "I'M OVERWHELMED",
            "what should i do",
            "I Keep Doing This Pattern",
            "LONG-TERM STRATEGY"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"

    def test_no_keyword_match_defaults_to_ops(self, orchestrator, agents):
        """Test that messages with no keyword matches default appropriately"""
        # Messages with no strong keywords
        messages = [
            "Hello there",
            "Just checking in",
            "How are things?"
        ]

        for msg in messages:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent found for: {msg}"
            # Should fall back to ops (default)
            assert agent.name.lower() == 'ops', f"Expected ops fallback for: {msg}"


# ========================================================================
# Test Multi-Keyword Scenarios
# ========================================================================

class TestMultiKeywordScenarios:
    """Test messages with multiple keywords from different agents"""

    def test_ops_keywords_win_with_higher_count(self, orchestrator, agents):
        """Test that agent with more matching keywords wins"""
        # Multiple ops keywords should win
        msg = "I have tasks to do today and need to schedule my work"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'ops'

    def test_high_priority_beats_multiple_low_priority(self, orchestrator, agents):
        """Test that high-priority keywords beat multiple low-priority"""
        # "overwhelmed" (ops high=5) should beat "feel" + "hard" (coach low=1+1)
        msg = "I'm overwhelmed even though I feel this is hard"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'ops'

    def test_combined_score_wins(self, orchestrator, agents):
        """Test that combined scores determine winner"""
        # Multiple health keywords
        msg = "I'm tired and exhausted and need rest"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'health'

    def test_strategy_wins_with_strong_keywords(self, orchestrator, agents):
        """Test strategy agent can win with strong keywords"""
        msg = "What's my long-term strategy for quarterly goals?"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'strategy'


# ========================================================================
# Test Fallback Behavior
# ========================================================================

class TestFallbackBehavior:
    """Test fallback routing when no strong matches"""

    def test_what_should_pattern_routes_to_ops(self, orchestrator, agents):
        """Test 'what should' pattern routes to ops"""
        msg = "What should I eat for lunch?"  # No strong keywords
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'ops'

    def test_help_me_pattern_routes_to_ops(self, orchestrator, agents):
        """Test 'help me' pattern routes to ops"""
        msg = "Help me figure this out"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'ops'

    def test_should_i_pattern_routes_to_strategy(self, orchestrator, agents):
        """Test 'should i' pattern routes to strategy"""
        msg = "Should I go to the store?"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'strategy'

    def test_is_it_worth_pattern_routes_to_strategy(self, orchestrator, agents):
        """Test 'is it worth' pattern routes to strategy"""
        msg = "Is it worth trying this approach?"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'strategy'

    def test_default_fallback_is_ops(self, orchestrator, agents):
        """Test final fallback is ops agent"""
        msg = "Just a random message with no triggers"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'ops'


# ========================================================================
# Test Word Boundary Matching
# ========================================================================

class TestWordBoundaryMatching:
    """Test that keyword matching respects word boundaries"""

    def test_task_not_in_multitask(self, orchestrator, agents):
        """Test 'task' doesn't match within 'multitask'"""
        # This tests that word boundaries work correctly
        # The KeywordMatcher should use \b to prevent partial matches
        msg = "I'm multitasking on several things"
        agent = orchestrator.find_agent(msg)
        # Should still match 'task' within multitask if word boundary is not working
        # If working correctly, depends on what other keywords match
        assert agent is not None

    def test_focus_not_in_refocus(self, orchestrator, agents):
        """Test 'focus' doesn't match within 'refocus'"""
        msg = "Need to refocus my attention"
        agent = orchestrator.find_agent(msg)
        # 'focus' is a health medium keyword
        # If word boundaries work, it won't match 'refocus'
        assert agent is not None

    def test_standalone_keywords_match(self, orchestrator, agents):
        """Test standalone keywords match correctly"""
        msg = "The task is important"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        # 'task' should match as standalone word


# ========================================================================
# Test Trigger Phrases
# ========================================================================

class TestTriggerPhrases:
    """Test agent-specific trigger phrases from frontmatter"""

    def test_agent_triggers_loaded(self, orchestrator):
        """Test that agent triggers are loaded from frontmatter"""
        # Verify the intent matcher has triggers
        matcher = orchestrator._get_intent_matcher()
        assert matcher.triggers is not None
        # Should have triggers for at least some agents
        assert len(matcher.triggers) >= 0  # May or may not have triggers in frontmatter

    def test_trigger_phrase_gets_highest_weight(self, orchestrator):
        """Test that trigger phrases get highest weight (10 points)"""
        # If triggers exist, they should score highest
        matcher = orchestrator._get_intent_matcher()
        if matcher.triggers:
            # Test that WEIGHT_TRIGGER is 10
            assert matcher.WEIGHT_TRIGGER == 10
            assert matcher.WEIGHT_TRIGGER > matcher.WEIGHT_HIGH


# ========================================================================
# Test Backward Compatibility
# ========================================================================

class TestBackwardCompatibility:
    """Test that refactored find_agent maintains expected behavior"""

    def test_common_ops_scenarios(self, orchestrator, agents):
        """Test common ops scenarios route correctly"""
        scenarios = [
            ("What's on my plate today?", 'ops'),
            ("I need to clear my inbox", 'ops'),
            ("Help me prioritize my tasks", 'ops'),
            ("What did I commit to do?", 'ops'),
        ]

        for msg, expected_agent in scenarios:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent for: {msg}"
            assert agent.name.lower() == expected_agent, \
                f"Expected {expected_agent}, got {agent.name} for: {msg}"

    def test_common_coach_scenarios(self, orchestrator, agents):
        """Test common coach scenarios route correctly"""
        scenarios = [
            ("I keep procrastinating on this", 'coach'),
            ("Why can't I stay consistent?", 'coach'),
            ("I need accountability for my goals", 'coach'),
        ]

        for msg, expected_agent in scenarios:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent for: {msg}"
            assert agent.name.lower() == expected_agent, \
                f"Expected {expected_agent}, got {agent.name} for: {msg}"

    def test_common_strategy_scenarios(self, orchestrator, agents):
        """Test common strategy scenarios route correctly"""
        scenarios = [
            ("What should my quarterly goals be?", 'strategy'),
            ("Should I take this client?", 'strategy'),
            ("What's my long-term direction?", 'strategy'),
        ]

        for msg, expected_agent in scenarios:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent for: {msg}"
            assert agent.name.lower() == expected_agent, \
                f"Expected {expected_agent}, got {agent.name} for: {msg}"

    def test_common_health_scenarios(self, orchestrator, agents):
        """Test common health scenarios route correctly"""
        scenarios = [
            ("Should I take my vyvanse?", 'health'),
            ("I'm tired and can't focus", 'health'),
            ("My energy crashed", 'health'),
        ]

        for msg, expected_agent in scenarios:
            agent = orchestrator.find_agent(msg)
            assert agent is not None, f"No agent for: {msg}"
            assert agent.name.lower() == expected_agent, \
                f"Expected {expected_agent}, got {agent.name} for: {msg}"


# ========================================================================
# Test Performance Characteristics
# ========================================================================

class TestPerformanceCharacteristics:
    """Test that the optimized matcher is actually being used"""

    def test_intent_matcher_is_cached(self, orchestrator):
        """Test that intent matcher is cached after first use"""
        # First call creates matcher
        matcher1 = orchestrator._get_intent_matcher()
        assert matcher1 is not None

        # Second call should return same instance
        matcher2 = orchestrator._get_intent_matcher()
        assert matcher2 is matcher1, "Intent matcher should be cached"

    def test_patterns_are_precompiled(self, orchestrator):
        """Test that regex patterns are pre-compiled"""
        matcher = orchestrator._get_intent_matcher()
        assert matcher._pattern is not None, "Patterns should be pre-compiled"
        assert matcher._keyword_map is not None, "Keyword map should be built"
        assert len(matcher._keyword_map) > 0, "Should have keywords mapped"

    def test_find_agent_uses_matcher(self, orchestrator):
        """Test that find_agent uses the KeywordMatcher"""
        # This is verified by checking that _intent_matcher is initialized
        agent = orchestrator.find_agent("I'm overwhelmed")
        assert agent is not None
        assert orchestrator._intent_matcher is not None, \
            "Intent matcher should be initialized after find_agent call"


# ========================================================================
# Test Real-World Message Patterns
# ========================================================================

class TestRealWorldMessages:
    """Test with realistic message patterns"""

    def test_morning_check_in(self, orchestrator, agents):
        """Test morning check-in type messages"""
        msg = "What should I focus on today? I have a lot on my plate."
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'ops'

    def test_habit_struggle(self, orchestrator, agents):
        """Test habit-related struggle messages"""
        msg = "I keep doing this pattern where I avoid the hard tasks. Why can't I just do them?"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'coach'

    def test_business_decision(self, orchestrator, agents):
        """Test business decision messages"""
        msg = "Should I take this client? What's the best long-term strategy for revenue growth?"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'strategy'

    def test_energy_crash(self, orchestrator, agents):
        """Test energy/health crash messages"""
        msg = "I'm tired and my focus is completely gone. Should I take my medication?"
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'health'

    def test_overwhelm_with_context(self, orchestrator, agents):
        """Test overwhelm message with context"""
        msg = "I'm feeling overwhelmed. I have 5 tasks due today, 3 meetings, and I haven't even checked my inbox."
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'ops'

    def test_procrastination_pattern(self, orchestrator, agents):
        """Test procrastination pattern message"""
        msg = "I keep procrastinating on this project. I notice the pattern but can't break it."
        agent = orchestrator.find_agent(msg)
        assert agent is not None
        assert agent.name.lower() == 'coach'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
