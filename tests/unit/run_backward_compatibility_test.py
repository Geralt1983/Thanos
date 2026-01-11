#!/usr/bin/env python3
"""
Simple test runner for backward compatibility tests.
Validates that agent selection works correctly with the new KeywordMatcher.
"""

from pathlib import Path
import sys

# Ensure Thanos is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.intent_matcher import KeywordMatcher
from Tools.thanos_orchestrator import ThanosOrchestrator


def get_top_agent(scores):
    """Get agent with highest score."""
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]


def test_agent_selection_accuracy():
    """Test that KeywordMatcher selects the right agent for real messages."""
    print("=" * 80)
    print("AGENT SELECTION ACCURACY TEST")
    print("=" * 80)
    print()

    # Set up keyword structure
    agent_keywords = {
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

    agent_triggers = {
        'ops': ['@ops', 'operational'],
        'coach': ['@coach', 'patterns'],
        'strategy': ['@strategy', 'strategic'],
        'health': ['@health', 'wellness']
    }

    # Create matcher
    matcher = KeywordMatcher(agent_keywords, agent_triggers)
    info = matcher.get_pattern_info()

    print(f"KeywordMatcher initialized:")
    print(f"  Total keywords: {info['total_keywords']}")
    print(f"  Pattern length: {info['pattern_length']} characters")
    print(f"  Agents: {list(info['agents'].keys())}")
    print()

    # Test cases: (message, expected_agent)
    test_cases = [
        # Ops agent tests
        ("I am overwhelmed with everything", 'ops'),
        ("What should I do today?", 'ops'),
        ("Help me plan my day", 'ops'),
        ("I need to prioritize my tasks", 'ops'),
        ("What is on my to-do list?", 'ops'),
        ("Need to schedule meetings", 'ops'),

        # Coach agent tests
        ("I keep procrastinating on this", 'coach'),
        ("I am struggling with this pattern", 'coach'),
        ("I need accountability", 'coach'),
        ("I am stuck in this habit", 'coach'),

        # Strategy agent tests
        ("What are my quarterly goals?", 'strategy'),
        ("I need a long-term strategy", 'strategy'),
        ("What is the big picture here?", 'strategy'),
        ("Should I take this client?", 'strategy'),
        ("How do I grow my revenue?", 'strategy'),

        # Health agent tests
        ("Should I take my vyvanse?", 'health'),
        ("I cant focus at all", 'health'),
        ("I crashed after lunch", 'health'),
        ("My energy is gone", 'health'),
        ("I am so exhausted", 'health'),
    ]

    passed = 0
    failed = 0

    print("Running agent selection tests...")
    print()

    for message, expected_agent in test_cases:
        scores = matcher.match(message)
        selected_agent = get_top_agent(scores)

        if selected_agent == expected_agent:
            print(f"✓ PASS: {expected_agent:8s} <- '{message[:50]}'")
            passed += 1
        else:
            print(f"✗ FAIL: Expected {expected_agent}, got {selected_agent}")
            print(f"        Message: '{message}'")
            print(f"        Scores: {scores}")
            failed += 1

    print()
    print("=" * 80)
    print(f"AGENT SELECTION: {passed} passed, {failed} failed")
    print("=" * 80)
    print()

    return failed == 0


def test_substring_matching():
    """Test that substring matching works like legacy 'in' operator."""
    print("=" * 80)
    print("SUBSTRING MATCHING TEST")
    print("=" * 80)
    print()

    agent_keywords = {
        'ops': {
            'medium': ['task', 'focus'],
            'low': []
        }
    }

    matcher = KeywordMatcher(agent_keywords, {})

    # These SHOULD match via substring (matching legacy behavior)
    match_cases = [
        ("I have a task", 2, "task should match exactly"),
        ("I have tasks to do", 2, "tasks keyword matches (longer pattern preferred)"),
        ("I am multitasking", 2, "task should match within multitasking"),
        ("I need to task and also focus", 4, "both task and focus match separately"),
    ]

    print("Testing substring matching (legacy behavior)...")
    print()

    passed = 0
    failed = 0

    for message, expected_score, explanation in match_cases:
        scores = matcher.match(message)
        ops_score = scores.get('ops', 0)

        if ops_score == expected_score:
            print(f"✓ PASS: {explanation}")
            print(f"        Message: '{message}' -> score: {ops_score}")
            passed += 1
        else:
            print(f"✗ FAIL: {explanation}")
            print(f"        Message: '{message}'")
            print(f"        Expected score: {expected_score}, got: {ops_score}")
            failed += 1

    print()
    print("=" * 80)
    print(f"SUBSTRING MATCHING: {passed} passed, {failed} failed")
    print("=" * 80)
    print()

    return failed == 0


def test_integration_with_orchestrator():
    """Test integration with ThanosOrchestrator."""
    print("=" * 80)
    print("INTEGRATION TEST")
    print("=" * 80)
    print()

    base_dir = Path(__file__).parent.parent.parent
    orchestrator = ThanosOrchestrator(base_dir=str(base_dir))

    test_cases = [
        ("I'm overwhelmed with tasks", 'ops'),
        ("I keep procrastinating", 'coach'),
        ("What's my quarterly strategy?", 'strategy'),
        ("I'm tired and can't focus", 'health'),
    ]

    print("Testing ThanosOrchestrator.find_agent()...")
    print()

    passed = 0
    failed = 0

    for message, expected_agent in test_cases:
        agent = orchestrator.find_agent(message)

        if agent and agent.name.lower() == expected_agent:
            print(f"✓ PASS: {expected_agent:8s} <- '{message}'")
            passed += 1
        else:
            print(f"✗ FAIL: Expected {expected_agent}, got {agent.name.lower() if agent else 'None'}")
            print(f"        Message: '{message}'")
            failed += 1

    # Test fallback behavior
    print()
    print("Testing fallback behavior...")
    fallback_msg = "The weather is nice"
    agent = orchestrator.find_agent(fallback_msg)

    if agent is not None:
        print(f"✓ PASS: Fallback agent selected: {agent.name.lower()}")
        passed += 1
    else:
        print(f"✗ FAIL: No fallback agent for message with no keywords")
        failed += 1

    print()
    print("=" * 80)
    print(f"INTEGRATION: {passed} passed, {failed} failed")
    print("=" * 80)
    print()

    return failed == 0


def main():
    """Run all backward compatibility tests."""
    print("\n")
    print("*" * 80)
    print("* BACKWARD COMPATIBILITY VALIDATION")
    print("* Testing KeywordMatcher agent selection accuracy")
    print("*" * 80)
    print()

    all_passed = True

    # Test 1: Agent selection accuracy
    if not test_agent_selection_accuracy():
        all_passed = False

    # Test 2: Substring matching (backward compatibility)
    if not test_substring_matching():
        all_passed = False

    # Test 3: Integration with ThanosOrchestrator
    if not test_integration_with_orchestrator():
        all_passed = False

    # Final summary
    print()
    print("*" * 80)
    if all_passed:
        print("* ✓ ALL TESTS PASSED")
        print("* Agent selection behavior validated successfully")
        print("*" * 80)
        return 0
    else:
        print("* ✗ SOME TESTS FAILED")
        print("* Review failures above")
        print("*" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
