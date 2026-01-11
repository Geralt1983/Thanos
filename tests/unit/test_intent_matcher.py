#!/usr/bin/env python3
"""
Unit tests for Tools/intent_matcher.py

Tests the KeywordMatcher class for efficient intent detection with pre-compiled regex patterns.
"""

import pytest
import re
from Tools.intent_matcher import KeywordMatcher, MatchResult


# ========================================================================
# Module-level Fixtures
# ========================================================================

@pytest.fixture
def sample_keywords():
    """Sample keyword structure for testing"""
    return {
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


@pytest.fixture
def sample_triggers():
    """Sample trigger keywords for testing"""
    return {
        'ops': ['urgent', 'asap', 'emergency'],
        'health': ['medication', 'vyvanse']
    }


@pytest.fixture
def matcher(sample_keywords, sample_triggers):
    """Create KeywordMatcher with sample data"""
    return KeywordMatcher(sample_keywords, sample_triggers)


@pytest.fixture
def simple_matcher():
    """Create simple KeywordMatcher for basic tests"""
    keywords = {
        'agent1': {
            'high': ['important'],
            'medium': ['moderate'],
            'low': ['minor']
        }
    }
    triggers = {'agent1': ['critical']}
    return KeywordMatcher(keywords, triggers)


# ========================================================================
# Initialization Tests
# ========================================================================

class TestKeywordMatcherInitialization:
    """Test KeywordMatcher initialization"""

    def test_initialization_with_keywords_and_triggers(self, sample_keywords, sample_triggers):
        """Test initialization with keywords and triggers"""
        matcher = KeywordMatcher(sample_keywords, sample_triggers)
        assert matcher.keywords == sample_keywords
        assert matcher.triggers == sample_triggers
        assert matcher._pattern is not None
        assert len(matcher._keyword_map) > 0

    def test_initialization_without_triggers(self, sample_keywords):
        """Test initialization without triggers"""
        matcher = KeywordMatcher(sample_keywords)
        assert matcher.keywords == sample_keywords
        assert matcher.triggers == {}
        assert matcher._pattern is not None

    def test_initialization_with_empty_keywords(self):
        """Test initialization with empty keywords"""
        matcher = KeywordMatcher({})
        assert matcher.keywords == {}
        assert matcher._pattern is not None
        # Should create empty pattern that matches nothing
        assert matcher.match("test message") == {}

    def test_pattern_compiled_at_init(self, matcher):
        """Test pattern is compiled during initialization"""
        assert matcher._pattern is not None
        assert isinstance(matcher._pattern, re.Pattern)
        assert len(matcher._keyword_map) > 0


# ========================================================================
# Pattern Compilation Tests
# ========================================================================

class TestPatternCompilation:
    """Test _compile_patterns method"""

    def test_pattern_has_word_boundaries(self, matcher):
        """Test pattern uses word boundaries"""
        pattern_str = matcher._pattern.pattern
        assert r'\b' in pattern_str
        # Should have word boundary at start and end
        assert pattern_str.startswith(r'\b(')
        assert pattern_str.endswith(r')\b')

    def test_pattern_is_case_insensitive(self, matcher):
        """Test pattern has case insensitive flag"""
        assert matcher._pattern.flags & re.IGNORECASE

    def test_special_characters_escaped(self):
        """Test special regex characters are escaped"""
        keywords = {
            'test': {
                'high': ['$100', 'x.y', 'a+b', 'c*d', '[test]']
            }
        }
        matcher = KeywordMatcher(keywords)
        # Should not raise regex compilation error
        assert matcher._pattern is not None
        # Should match literal characters
        assert matcher.match("I need $100") == {'test': 5}
        assert matcher.match("file x.y") == {'test': 5}

    def test_multi_word_phrases_compiled(self, sample_keywords):
        """Test multi-word phrases are compiled correctly"""
        matcher = KeywordMatcher(sample_keywords)
        # Multi-word phrases should be in keyword map
        assert 'what should i do' in matcher._keyword_map
        assert 'i keep doing this' in matcher._keyword_map
        assert 'im tired' in matcher._keyword_map

    def test_patterns_sorted_by_length(self):
        """Test patterns are sorted by length (descending)"""
        keywords = {
            'test': {
                'high': ['a', 'abc', 'ab', 'abcd']
            }
        }
        matcher = KeywordMatcher(keywords)
        pattern_str = matcher._pattern.pattern
        # Longer patterns should appear first in alternation
        # This prevents "ab" from matching before "abcd"
        # Extract the alternation group
        alternation = pattern_str[3:-3]  # Remove \b( and )\b
        parts = alternation.split('|')
        # Check that parts are sorted by length descending
        for i in range(len(parts) - 1):
            assert len(parts[i]) >= len(parts[i + 1])

    def test_keyword_map_contains_all_keywords(self, matcher):
        """Test keyword_map contains all keywords from all agents"""
        # Count expected keywords
        expected_count = 0
        for agent, priority_dict in matcher.keywords.items():
            for priority, keyword_list in priority_dict.items():
                expected_count += len(keyword_list)

        # Add triggers
        for agent, trigger_list in matcher.triggers.items():
            expected_count += len(trigger_list)

        assert len(matcher._keyword_map) == expected_count

    def test_weights_assigned_correctly(self, simple_matcher):
        """Test weights are assigned based on priority"""
        # Check high priority keyword
        assert simple_matcher._keyword_map['important'] == ('agent1', KeywordMatcher.WEIGHT_HIGH)
        # Check medium priority keyword
        assert simple_matcher._keyword_map['moderate'] == ('agent1', KeywordMatcher.WEIGHT_MEDIUM)
        # Check low priority keyword
        assert simple_matcher._keyword_map['minor'] == ('agent1', KeywordMatcher.WEIGHT_LOW)
        # Check trigger keyword
        assert simple_matcher._keyword_map['critical'] == ('agent1', KeywordMatcher.WEIGHT_TRIGGER)


# ========================================================================
# Basic Matching Tests
# ========================================================================

class TestBasicMatching:
    """Test basic match() functionality"""

    def test_match_single_keyword(self, simple_matcher):
        """Test matching a single keyword"""
        scores = simple_matcher.match("This is important")
        assert scores == {'agent1': KeywordMatcher.WEIGHT_HIGH}

    def test_match_multiple_keywords_same_agent(self, simple_matcher):
        """Test matching multiple keywords for same agent"""
        scores = simple_matcher.match("This is important and moderate")
        expected = KeywordMatcher.WEIGHT_HIGH + KeywordMatcher.WEIGHT_MEDIUM
        assert scores == {'agent1': expected}

    def test_match_multiple_agents(self, matcher):
        """Test matching keywords from multiple agents"""
        scores = matcher.match("I have tasks and need strategy advice")
        assert 'ops' in scores
        assert 'strategy' in scores
        assert scores['ops'] > 0
        assert scores['strategy'] > 0

    def test_match_no_keywords(self, matcher):
        """Test message with no matching keywords"""
        scores = matcher.match("The quick brown fox jumps over the lazy dog")
        assert scores == {}

    def test_match_empty_message(self, matcher):
        """Test empty message"""
        scores = matcher.match("")
        assert scores == {}

    def test_match_none_message(self, matcher):
        """Test None message"""
        scores = matcher.match(None)
        assert scores == {}

    def test_match_case_insensitive(self, simple_matcher):
        """Test matching is case insensitive"""
        assert simple_matcher.match("IMPORTANT") == {'agent1': KeywordMatcher.WEIGHT_HIGH}
        assert simple_matcher.match("Important") == {'agent1': KeywordMatcher.WEIGHT_HIGH}
        assert simple_matcher.match("important") == {'agent1': KeywordMatcher.WEIGHT_HIGH}

    def test_match_trigger_highest_weight(self, simple_matcher):
        """Test triggers have highest weight"""
        scores = simple_matcher.match("This is critical")
        assert scores == {'agent1': KeywordMatcher.WEIGHT_TRIGGER}
        assert KeywordMatcher.WEIGHT_TRIGGER > KeywordMatcher.WEIGHT_HIGH


# ========================================================================
# Word Boundary Tests
# ========================================================================

class TestWordBoundaries:
    """Test word boundary enforcement"""

    def test_no_match_within_word(self):
        """Test keyword not matched when inside another word"""
        keywords = {
            'test': {
                'high': ['task', 'focus']
            }
        }
        matcher = KeywordMatcher(keywords)

        # Should not match 'task' in 'multitask'
        scores = matcher.match("I need to multitask today")
        assert scores == {}

        # Should not match 'focus' in 'refocus'
        scores = matcher.match("Let me refocus on this")
        assert scores == {}

    def test_match_at_word_boundary(self):
        """Test keyword matched at word boundaries"""
        keywords = {
            'test': {
                'high': ['task']
            }
        }
        matcher = KeywordMatcher(keywords)

        # Should match standalone 'task'
        assert matcher.match("I have a task") == {'test': 5}
        assert matcher.match("task is important") == {'test': 5}
        assert matcher.match("my task") == {'test': 5}

    def test_match_with_punctuation(self):
        """Test keyword matched with punctuation boundaries"""
        keywords = {
            'test': {
                'high': ['task']
            }
        }
        matcher = KeywordMatcher(keywords)

        assert matcher.match("task.") == {'test': 5}
        assert matcher.match("task,") == {'test': 5}
        assert matcher.match("task!") == {'test': 5}
        assert matcher.match("task?") == {'test': 5}
        assert matcher.match("(task)") == {'test': 5}
        assert matcher.match("[task]") == {'test': 5}

    def test_multi_word_phrase_boundaries(self):
        """Test multi-word phrases respect word boundaries"""
        keywords = {
            'test': {
                'high': ['what should i do']
            }
        }
        matcher = KeywordMatcher(keywords)

        # Should match exact phrase
        assert matcher.match("what should i do about this") == {'test': 5}
        assert matcher.match("I wonder what should i do") == {'test': 5}


# ========================================================================
# Multi-word Phrase Tests
# ========================================================================

class TestMultiWordPhrases:
    """Test matching of multi-word phrases"""

    def test_match_multi_word_phrase(self, matcher):
        """Test matching multi-word phrases"""
        scores = matcher.match("I don't know what should i do")
        assert 'ops' in scores

    def test_multi_word_phrase_not_split(self):
        """Test multi-word phrase must match completely"""
        keywords = {
            'test': {
                'high': ['what should i do']
            }
        }
        matcher = KeywordMatcher(keywords)

        # Should match complete phrase
        assert matcher.match("what should i do") == {'test': 5}

        # Should not match partial phrase with extra words in between
        # The phrase needs to be exact (though case insensitive)
        assert matcher.match("what should really i do") == {}

    def test_longer_phrase_matched_first(self):
        """Test longer phrases matched before shorter ones"""
        keywords = {
            'test': {
                'high': ['what should i do', 'what should'],
                'medium': ['what']
            }
        }
        matcher = KeywordMatcher(keywords)

        # Should match longest phrase first
        scores = matcher.match("what should i do")
        # Should get high weight for longest match
        assert scores == {'test': 5}


# ========================================================================
# Score Accumulation Tests
# ========================================================================

class TestScoreAccumulation:
    """Test score accumulation logic"""

    def test_same_keyword_multiple_times(self):
        """Test same keyword appearing multiple times accumulates score"""
        keywords = {
            'test': {
                'high': ['task']
            }
        }
        matcher = KeywordMatcher(keywords)

        scores = matcher.match("task one task two task three")
        # Should accumulate: 5 + 5 + 5 = 15
        assert scores == {'test': 15}

    def test_different_priorities_accumulate(self, simple_matcher):
        """Test different priority keywords accumulate"""
        scores = simple_matcher.match("important moderate minor")
        expected = (KeywordMatcher.WEIGHT_HIGH +
                   KeywordMatcher.WEIGHT_MEDIUM +
                   KeywordMatcher.WEIGHT_LOW)
        assert scores == {'agent1': expected}

    def test_triggers_and_keywords_accumulate(self, simple_matcher):
        """Test triggers and regular keywords accumulate"""
        scores = simple_matcher.match("critical and important")
        expected = KeywordMatcher.WEIGHT_TRIGGER + KeywordMatcher.WEIGHT_HIGH
        assert scores == {'agent1': expected}

    def test_multiple_agents_independent_scores(self, matcher):
        """Test multiple agents have independent scores"""
        scores = matcher.match("urgent tasks and exhausted energy")
        # 'urgent' -> ops trigger (10), 'tasks' -> ops medium (2)
        # 'exhausted' -> health medium (2), 'energy' -> health high (5)
        assert scores['ops'] == 12  # 10 + 2
        assert scores['health'] == 7  # 2 + 5


# ========================================================================
# match_with_details Tests
# ========================================================================

class TestMatchWithDetails:
    """Test match_with_details() functionality"""

    def test_returns_scores_and_matches(self, simple_matcher):
        """Test match_with_details returns both scores and matches"""
        scores, matches = simple_matcher.match_with_details("important task")

        assert isinstance(scores, dict)
        assert isinstance(matches, list)
        assert scores == {'agent1': KeywordMatcher.WEIGHT_HIGH}
        assert len(matches) == 1

    def test_match_result_structure(self, simple_matcher):
        """Test MatchResult has correct structure"""
        scores, matches = simple_matcher.match_with_details("critical")

        assert len(matches) == 1
        match = matches[0]
        assert isinstance(match, MatchResult)
        assert match.agent == 'agent1'
        assert match.keyword == 'critical'
        assert match.weight == KeywordMatcher.WEIGHT_TRIGGER
        assert isinstance(match.start, int)
        assert isinstance(match.end, int)

    def test_match_positions_correct(self):
        """Test match positions are correct"""
        keywords = {
            'test': {
                'high': ['task']
            }
        }
        matcher = KeywordMatcher(keywords)

        message = "my task today"
        scores, matches = matcher.match_with_details(message)

        assert len(matches) == 1
        match = matches[0]
        assert message.lower()[match.start:match.end] == 'task'

    def test_multiple_matches_all_captured(self, simple_matcher):
        """Test all matches are captured in details"""
        scores, matches = simple_matcher.match_with_details("critical important moderate")

        assert len(matches) == 3
        keywords_found = [m.keyword for m in matches]
        assert 'critical' in keywords_found
        assert 'important' in keywords_found
        assert 'moderate' in keywords_found

    def test_empty_message_returns_empty(self, matcher):
        """Test empty message returns empty results"""
        scores, matches = matcher.match_with_details("")
        assert scores == {}
        assert matches == []


# ========================================================================
# get_pattern_info Tests
# ========================================================================

class TestGetPatternInfo:
    """Test get_pattern_info() functionality"""

    def test_pattern_info_structure(self, matcher):
        """Test pattern info has correct structure"""
        info = matcher.get_pattern_info()

        assert 'total_keywords' in info
        assert 'pattern_length' in info
        assert 'agents' in info
        assert isinstance(info['total_keywords'], int)
        assert isinstance(info['pattern_length'], int)
        assert isinstance(info['agents'], dict)

    def test_total_keywords_count(self, simple_matcher):
        """Test total keywords count is correct"""
        info = simple_matcher.get_pattern_info()
        # 3 keywords + 1 trigger = 4 total
        assert info['total_keywords'] == 4

    def test_agent_counts(self, simple_matcher):
        """Test agent keyword counts are correct"""
        info = simple_matcher.get_pattern_info()
        assert info['agents'] == {'agent1': 4}

    def test_pattern_length(self, matcher):
        """Test pattern length is reasonable"""
        info = matcher.get_pattern_info()
        # Pattern should be longer than 0
        assert info['pattern_length'] > 0

    def test_multiple_agents_counted(self, matcher):
        """Test multiple agents are counted separately"""
        info = matcher.get_pattern_info()
        assert 'ops' in info['agents']
        assert 'coach' in info['agents']
        assert 'strategy' in info['agents']
        assert 'health' in info['agents']


# ========================================================================
# Edge Cases
# ========================================================================

class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_unicode_characters(self):
        """Test keywords and messages with unicode"""
        keywords = {
            'test': {
                'high': ['emoji', 'unicode']
            }
        }
        matcher = KeywordMatcher(keywords)

        # Should handle unicode in message
        scores = matcher.match("This has emoji 🔥 content")
        assert scores == {'test': 5}

        scores = matcher.match("This has unicode 日本語 text")
        assert scores == {'test': 5}

    def test_very_long_message(self, matcher):
        """Test matching in very long message"""
        # Create a long message with keywords scattered throughout
        long_message = ("random words " * 100) + "urgent task" + (" more words" * 100)
        scores = matcher.match(long_message)

        assert 'ops' in scores
        assert scores['ops'] > 0

    def test_whitespace_handling(self):
        """Test various whitespace scenarios"""
        keywords = {
            'test': {
                'high': ['task']
            }
        }
        matcher = KeywordMatcher(keywords)

        assert matcher.match("  task  ") == {'test': 5}
        assert matcher.match("\ttask\t") == {'test': 5}
        assert matcher.match("\ntask\n") == {'test': 5}
        assert matcher.match("  multiple   spaces   task  ") == {'test': 5}

    def test_repeated_keywords(self):
        """Test same keyword repeated multiple times"""
        keywords = {
            'test': {
                'high': ['task']
            }
        }
        matcher = KeywordMatcher(keywords)

        scores = matcher.match("task task task")
        # Should accumulate: 5 + 5 + 5 = 15
        assert scores == {'test': 15}

    def test_overlapping_keyword_variations(self):
        """Test keywords that are variations of each other"""
        keywords = {
            'test': {
                'high': ['task', 'tasks']
            }
        }
        matcher = KeywordMatcher(keywords)

        # Both should be matched independently
        scores = matcher.match("task and tasks")
        assert scores == {'test': 10}  # 5 + 5

    def test_numbers_in_keywords(self):
        """Test keywords with numbers"""
        keywords = {
            'test': {
                'high': ['task1', '2day', 'version3']
            }
        }
        matcher = KeywordMatcher(keywords)

        assert matcher.match("working on task1") == {'test': 5}
        assert matcher.match("need this 2day") == {'test': 5}
        assert matcher.match("using version3") == {'test': 5}

    def test_hyphenated_words(self):
        """Test hyphenated keywords"""
        keywords = {
            'test': {
                'high': ['long-term', 'high-priority']
            }
        }
        matcher = KeywordMatcher(keywords)

        assert matcher.match("long-term planning") == {'test': 5}
        assert matcher.match("this is high-priority") == {'test': 5}

    def test_apostrophes_in_keywords(self):
        """Test keywords with apostrophes"""
        keywords = {
            'test': {
                'high': ["i'm tired", "can't focus"]
            }
        }
        matcher = KeywordMatcher(keywords)

        assert matcher.match("I'm tired today") == {'test': 5}
        assert matcher.match("I can't focus") == {'test': 5}


# ========================================================================
# Integration Tests
# ========================================================================

class TestIntegration:
    """Integration tests with realistic scenarios"""

    def test_realistic_ops_message(self, matcher):
        """Test realistic ops agent message"""
        message = "I'm overwhelmed with urgent tasks today. What should I do?"
        scores = matcher.match(message)

        assert 'ops' in scores
        # Should have high score: overwhelmed (high=5) + urgent (trigger=10) +
        # tasks (medium=2) + today (medium=2) + what should i do (high=5) = 24
        # Note: "what should i do" is a multi-word phrase that should match
        assert scores['ops'] >= 15  # At least the core keywords

    def test_realistic_health_message(self, matcher):
        """Test realistic health agent message"""
        message = "I'm tired and can't focus. Need to rest."
        scores = matcher.match(message)

        assert 'health' in scores
        # Should match: im tired (high=5) + i cant focus (high=5) + focus (medium=2) + rest (low=1)
        # Note: both "im tired" and "i cant focus" are multi-word phrases
        assert scores['health'] >= 10

    def test_realistic_coach_message(self, matcher):
        """Test realistic coach agent message"""
        message = "I keep doing this same pattern. Need accountability."
        scores = matcher.match(message)

        assert 'coach' in scores
        # Should match: i keep doing this (high=5) + pattern (high=5) + accountability (high=5)
        assert scores['coach'] >= 10

    def test_realistic_strategy_message(self, matcher):
        """Test realistic strategy agent message"""
        message = "Need to make a decision about long-term revenue goals"
        scores = matcher.match(message)

        assert 'strategy' in scores
        # Should match: decision (medium=2) + long-term (high=5) + revenue (medium=2) + goals (high=5)
        assert scores['strategy'] >= 10

    def test_multi_agent_message(self, matcher):
        """Test message that could match multiple agents"""
        message = "Urgent: Need strategy for managing overwhelming workload"
        scores = matcher.match(message)

        # Should match both ops and strategy
        assert len(scores) >= 2
        assert 'ops' in scores
        assert 'strategy' in scores


# ========================================================================
# Weight Constants Tests
# ========================================================================

class TestWeightConstants:
    """Test weight constant values"""

    def test_weight_values(self):
        """Test weight constants have expected values"""
        assert KeywordMatcher.WEIGHT_TRIGGER == 10
        assert KeywordMatcher.WEIGHT_HIGH == 5
        assert KeywordMatcher.WEIGHT_MEDIUM == 2
        assert KeywordMatcher.WEIGHT_LOW == 1

    def test_weight_hierarchy(self):
        """Test weights are properly ordered"""
        assert KeywordMatcher.WEIGHT_TRIGGER > KeywordMatcher.WEIGHT_HIGH
        assert KeywordMatcher.WEIGHT_HIGH > KeywordMatcher.WEIGHT_MEDIUM
        assert KeywordMatcher.WEIGHT_MEDIUM > KeywordMatcher.WEIGHT_LOW
        assert KeywordMatcher.WEIGHT_LOW > 0
