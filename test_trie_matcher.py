#!/usr/bin/env python3
"""
Quick test to verify TrieKeywordMatcher implementation works correctly.
"""

from Tools.intent_matcher import KeywordMatcher, TrieKeywordMatcher, AHOCORASICK_AVAILABLE

# Sample keywords from ThanosOrchestrator
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

# Test messages
test_cases = [
    ("I'm overwhelmed with tasks today", {'ops': 11, 'coach': 0, 'strategy': 0, 'health': 0}),
    ("What should i do about this long-term strategy?", {'ops': 5, 'coach': 0, 'strategy': 10, 'health': 0}),
    ("I keep doing this and feel stuck in a pattern", {'ops': 0, 'coach': 13, 'strategy': 0, 'health': 0}),
    ("Im tired and cant focus on work", {'ops': 1, 'coach': 0, 'strategy': 0, 'health': 7}),
    ("Need to schedule a meeting asap", {'ops': 12, 'coach': 0, 'strategy': 0, 'health': 0}),
    ("", {'ops': 0, 'coach': 0, 'strategy': 0, 'health': 0}),  # Empty message
]

print("=" * 70)
print("TrieKeywordMatcher Verification Test")
print("=" * 70)
print(f"Aho-Corasick available: {AHOCORASICK_AVAILABLE}")
print()

# Create matchers
regex_matcher = KeywordMatcher(keywords, triggers)
trie_matcher = TrieKeywordMatcher(keywords, triggers)

# Verify trie matcher info
trie_info = trie_matcher.get_pattern_info()
print(f"Trie matcher info: {trie_info}")
print()

all_passed = True
for message, expected_scores in test_cases:
    # Test with both matchers
    regex_scores = regex_matcher.match(message)
    trie_scores = trie_matcher.match(message)

    # Check if they match
    if regex_scores != trie_scores:
        print(f"❌ MISMATCH for message: '{message}'")
        print(f"   Regex scores: {regex_scores}")
        print(f"   Trie scores:  {trie_scores}")
        all_passed = False
    elif regex_scores != expected_scores:
        print(f"❌ INCORRECT for message: '{message}'")
        print(f"   Expected: {expected_scores}")
        print(f"   Got:      {regex_scores}")
        all_passed = False
    else:
        print(f"✅ PASS: '{message[:50]}...' -> {trie_scores}")

print()
print("=" * 70)
if all_passed:
    print("✅ All tests PASSED! TrieKeywordMatcher is working correctly.")
else:
    print("❌ Some tests FAILED!")
print("=" * 70)

# Test match_with_details
print("\nTesting match_with_details():")
test_msg = "I'm overwhelmed with tasks today"
regex_scores, regex_details = regex_matcher.match_with_details(test_msg)
trie_scores, trie_details = trie_matcher.match_with_details(test_msg)

print(f"Regex matcher found {len(regex_details)} matches")
print(f"Trie matcher found {len(trie_details)} matches")

if regex_scores == trie_scores:
    print("✅ Scores match!")
else:
    print("❌ Scores don't match!")
    print(f"   Regex: {regex_scores}")
    print(f"   Trie:  {trie_scores}")

# Test get_pattern_info
print("\nTesting get_pattern_info():")
regex_info = regex_matcher.get_pattern_info()
trie_info = trie_matcher.get_pattern_info()
print(f"Regex total keywords: {regex_info['total_keywords']}")
print(f"Trie total keywords: {trie_info['total_keywords']}")
if regex_info['total_keywords'] == trie_info['total_keywords']:
    print("✅ Keyword counts match!")
else:
    print("❌ Keyword counts don't match!")
