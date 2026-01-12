"""Unit tests for insight generation and scoring.

Tests the insight generator with mock patterns and verifies:
- Scoring algorithm correctness (significance, actionability, impact, recency)
- Top 3 selection diversity (category distribution)
- Insight formatting output (summary, action, evidence)
- Confidence level calculations
- Insights are actionable and well-formatted

Test coverage:
- generate_insight_from_task_pattern
- generate_insight_from_health_correlation
- generate_insight_from_habit_streak
- generate_insight_from_trend
- calculate_recency_score
- calculate_significance_score
- rank_insights
- filter_insights_by_confidence
- filter_insights_by_category
- select_top_insights (diversity, novelty, goal alignment)
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from Tools.pattern_recognition.insight_generator import (
    generate_insight_from_task_pattern,
    generate_insight_from_health_correlation,
    generate_insight_from_habit_streak,
    generate_insight_from_trend,
    calculate_recency_score,
    calculate_significance_score,
    generate_insights_from_all_patterns,
    rank_insights,
    filter_insights_by_confidence,
    filter_insights_by_category,
    select_top_insights,
    _calculate_goal_alignment_scores,
    _calculate_novelty_adjustments,
)
from Tools.pattern_recognition.models import (
    Insight,
    InsightCategory,
    TaskCompletionPattern,
    HealthCorrelation,
    HabitStreak,
    Trend,
    PatternType,
    TrendDirection,
)


# ============================================================================
# Mock Data Generators
# ============================================================================

def create_mock_task_pattern(
    completion_rate: float = 8.0,
    confidence: float = 0.85,
    days_ago: int = 5
) -> TaskCompletionPattern:
    """Create mock task completion pattern."""
    end_date = datetime.now() - timedelta(days=days_ago)
    start_date = end_date - timedelta(days=30)

    return TaskCompletionPattern(
        pattern_type=PatternType.HOURLY,
        description="Most productive between 9-11am",
        time_period="9-11am",
        completion_rate=completion_rate,
        sample_size=30,
        confidence_score=confidence,
        date_range_start=start_date,
        date_range_end=end_date,
        evidence=[
            "Average 8.2 tasks completed during 9-11am",
            "40% above daily average",
            "Consistent across all 30 days",
        ],
        metadata={"peak_hours": [9, 10, 11]}
    )


def create_mock_health_correlation(
    correlation_strength: float = 0.72,
    effect_size: float = 40.0,
    confidence: float = 0.80,
    days_ago: int = 3
) -> HealthCorrelation:
    """Create mock health correlation."""
    end_date = datetime.now() - timedelta(days=days_ago)
    start_date = end_date - timedelta(days=30)

    return HealthCorrelation(
        health_metric="sleep_duration",
        productivity_metric="tasks_completed",
        correlation_strength=correlation_strength,
        correlation_description="7+ hours sleep correlates with 40% more tasks completed",
        threshold_value=7.0,
        effect_size=effect_size,
        confidence_score=confidence,
        sample_size=25,
        date_range_start=start_date,
        date_range_end=end_date,
        evidence=[
            "Strong positive correlation (r=0.72)",
            "Days with 7+ hours: avg 9.2 tasks",
            "Days with <7 hours: avg 6.6 tasks",
        ],
        metadata={"threshold_percentile": 0.6}
    )


def create_mock_habit_streak(
    streak_length: int = 45,
    is_active: bool = True,
    consistency: float = 0.92,
    confidence: float = 0.88,
    days_since_completion: int = 1
) -> HabitStreak:
    """Create mock habit streak."""
    last_completion = datetime.now() - timedelta(days=days_since_completion)
    break_date = None if is_active else last_completion - timedelta(days=streak_length)

    return HabitStreak(
        habit_name="Daily Review",
        streak_length=streak_length,
        is_active=is_active,
        last_completion_date=last_completion,
        break_date=break_date,
        break_reasons=[] if is_active else ["Friday evening scheduling conflicts", "Weekend travel"],
        consistency_score=consistency,
        longest_streak=50 if is_active else streak_length + 10,
        total_completions=90,
        confidence_score=confidence,
        date_range_start=last_completion - timedelta(days=90),
        date_range_end=last_completion,
        evidence=[
            "45-day current streak",
            "92% consistency over 90 days",
            "Approaching personal record of 50 days",
        ] if is_active else [
            "Streak broken on Fridays (60% of breaks)",
            "Travel disrupts consistency",
        ],
        metadata={"frequency_expected": 1}
    )


def create_mock_trend(
    direction: TrendDirection = TrendDirection.DECLINING,
    change_percentage: float = -15.0,
    trend_strength: float = 0.75,
    confidence: float = 0.78,
    days_ago: int = 2
) -> Trend:
    """Create mock trend."""
    end_date = datetime.now() - timedelta(days=days_ago)
    start_date = end_date - timedelta(days=30)

    start_value = 9.4
    end_value = start_value * (1 + change_percentage / 100)

    return Trend(
        metric_name="tasks_per_day",
        trend_direction=direction,
        trend_description=f"Tasks per day {direction.value} ({start_value:.1f} → {end_value:.1f} over 30 days)",
        start_value=start_value,
        end_value=end_value,
        change_percentage=change_percentage,
        trend_strength=trend_strength,
        momentum_indicator="30-day",
        confidence_score=confidence,
        sample_size=30,
        date_range_start=start_date,
        date_range_end=end_date,
        evidence=[
            f"Consistent {direction.value} pattern",
            "Linear regression shows clear trend",
            f"{abs(change_percentage):.0f}% change over period",
        ],
        metadata={"slope": change_percentage / 30}
    )


# ============================================================================
# Test Scoring Algorithm Correctness
# ============================================================================

class TestScoringAlgorithm:
    """Test scoring algorithm correctness for all score types."""

    def test_recency_score_calculation(self):
        """Test recency score exponential decay."""
        # Recent data should score high
        recent_date = datetime.now() - timedelta(days=1)
        score = calculate_recency_score(recent_date, recency_days=30)
        assert score > 0.95, "Recent data should have high recency score"

        # Data from 30 days ago should score ~0.37 (exp(-1))
        old_date = datetime.now() - timedelta(days=30)
        score = calculate_recency_score(old_date, recency_days=30)
        assert 0.35 <= score <= 0.40, f"Expected ~0.37, got {score}"

        # Very old data should score low
        very_old_date = datetime.now() - timedelta(days=90)
        score = calculate_recency_score(very_old_date, recency_days=30)
        assert score < 0.10, "Old data should have low recency score"

        # Today's data should score 1.0
        today = datetime.now()
        score = calculate_recency_score(today, recency_days=30)
        assert score >= 0.99, "Today's data should score near 1.0"

    def test_significance_score_components(self):
        """Test significance score combines confidence, sample size, and effect size."""
        # High confidence, large sample, large effect
        score = calculate_significance_score(
            confidence_score=0.9,
            sample_size=50,
            effect_size=0.8,
            min_sample_size=10
        )
        assert score > 0.85, f"High values should yield high significance: {score}"

        # Low confidence, small sample, small effect
        score = calculate_significance_score(
            confidence_score=0.5,
            sample_size=5,
            effect_size=0.2,
            min_sample_size=10
        )
        assert score < 0.40, f"Low values should yield low significance: {score}"

        # Verify component weights (50% confidence, 30% sample, 20% effect)
        # Perfect confidence only
        score_confidence_only = calculate_significance_score(
            confidence_score=1.0,
            sample_size=5,  # Will score 0.25 (5/20)
            effect_size=0.0,  # Will use default 0.5
            min_sample_size=10
        )
        # Expected: 1.0*0.5 + 0.25*0.3 + 0.5*0.2 = 0.5 + 0.075 + 0.1 = 0.675
        assert 0.65 <= score_confidence_only <= 0.70, f"Expected ~0.675, got {score_confidence_only}"

    def test_task_pattern_insight_scoring(self):
        """Test insight generation from task pattern has correct scores."""
        pattern = create_mock_task_pattern(
            completion_rate=8.0,
            confidence=0.85,
            days_ago=5
        )

        insight = generate_insight_from_task_pattern(pattern, recency_days=30)

        # Verify all scores are in valid range
        assert 0.0 <= insight.confidence_score <= 1.0
        assert 0.0 <= insight.actionability_score <= 1.0
        assert 0.0 <= insight.impact_score <= 1.0
        assert 0.0 <= insight.significance_score <= 1.0
        assert 0.0 <= insight.recency_score <= 1.0

        # Task patterns should have high actionability (0.85)
        assert insight.actionability_score == 0.85, "Task patterns are highly actionable"

        # Confidence should match pattern
        assert insight.confidence_score == pattern.confidence_score

        # Impact based on completion rate (8.0 / 10.0 = 0.8)
        expected_impact = min(1.0, pattern.completion_rate / 10.0)
        assert insight.impact_score == expected_impact

        # Overall score should be weighted combination
        overall = insight.get_overall_score()
        assert 0.0 <= overall <= 1.0, "Overall score must be in range"
        assert overall > 0.5, "High-quality pattern should score well"

    def test_health_correlation_insight_scoring(self):
        """Test insight generation from health correlation has correct scores."""
        correlation = create_mock_health_correlation(
            correlation_strength=0.72,
            effect_size=40.0,
            confidence=0.80,
            days_ago=3
        )

        insight = generate_insight_from_health_correlation(correlation, recency_days=30)

        # Sleep-related should have actionability 0.70
        assert insight.actionability_score == 0.70, "Sleep is moderately actionable"

        # Impact based on effect size (40% -> 0.40)
        assert insight.impact_score == 0.40, "Effect size should determine impact"

        # Confidence should match correlation
        assert insight.confidence_score == correlation.confidence_score

        # Category should be health correlation
        assert insight.category == InsightCategory.HEALTH_CORRELATION

    def test_habit_streak_insight_scoring(self):
        """Test insight generation from habit streak has correct scores."""
        # Active streak
        active_streak = create_mock_habit_streak(
            streak_length=45,
            is_active=True,
            consistency=0.92,
            confidence=0.88,
            days_since_completion=1
        )

        insight = generate_insight_from_habit_streak(active_streak, recency_days=30)

        # Habits should have high actionability (0.90)
        assert insight.actionability_score == 0.90, "Habits are highly actionable"

        # Active streak impact: min(1.0, 45/30) * 0.7 = 1.0 * 0.7 = 0.7
        expected_impact = min(1.0, active_streak.streak_length / 30.0) * 0.7
        assert insight.impact_score == expected_impact

        # Broken streak
        broken_streak = create_mock_habit_streak(
            streak_length=20,
            is_active=False,
            consistency=0.65,
            confidence=0.75,
            days_since_completion=5
        )

        insight_broken = generate_insight_from_habit_streak(broken_streak, recency_days=30)

        # Broken streak impact: (1.0 - 0.65) * 0.8 = 0.35 * 0.8 = 0.28
        expected_impact_broken = (1.0 - broken_streak.consistency_score) * 0.8
        assert insight_broken.impact_score == expected_impact_broken

    def test_trend_insight_scoring(self):
        """Test insight generation from trend has correct scores."""
        # Declining trend
        declining_trend = create_mock_trend(
            direction=TrendDirection.DECLINING,
            change_percentage=-15.0,
            trend_strength=0.75,
            confidence=0.78,
            days_ago=2
        )

        insight = generate_insight_from_trend(declining_trend, recency_days=30)

        # Declining trends should have actionability 0.80
        assert insight.actionability_score == 0.80, "Declining trends are actionable"

        # Impact: min(1.0, (15/50) * 0.75) = min(1.0, 0.225) = 0.225
        expected_impact = min(1.0, (abs(declining_trend.change_percentage) / 50.0) * declining_trend.trend_strength)
        assert abs(insight.impact_score - expected_impact) < 0.01

        # Improving trend
        improving_trend = create_mock_trend(
            direction=TrendDirection.IMPROVING,
            change_percentage=20.0,
            trend_strength=0.80,
            confidence=0.82,
            days_ago=1
        )

        insight_improving = generate_insight_from_trend(improving_trend, recency_days=30)

        # Improving trends should have actionability 0.70
        assert insight_improving.actionability_score == 0.70, "Improving trends moderately actionable"

        # Plateau/volatile should have lower actionability
        plateau_trend = create_mock_trend(
            direction=TrendDirection.PLATEAU,
            change_percentage=2.0,
            trend_strength=0.60,
            confidence=0.70,
            days_ago=4
        )

        insight_plateau = generate_insight_from_trend(plateau_trend, recency_days=30)
        assert insight_plateau.actionability_score == 0.50, "Plateau/volatile less actionable"


# ============================================================================
# Test Top 3 Selection Diversity
# ============================================================================

class TestTopInsightsSelection:
    """Test selection of top insights with diversity constraints."""

    def test_diversity_constraint_max_per_category(self):
        """Test that max_per_category constraint is enforced."""
        # Create 6 insights: 4 task, 2 health
        insights = [
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=10.0, confidence=0.90, days_ago=1)
            ),
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=9.0, confidence=0.88, days_ago=2)
            ),
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=8.5, confidence=0.85, days_ago=3)
            ),
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=8.0, confidence=0.82, days_ago=4)
            ),
            generate_insight_from_health_correlation(
                create_mock_health_correlation(correlation_strength=0.75, confidence=0.80, days_ago=1)
            ),
            generate_insight_from_health_correlation(
                create_mock_health_correlation(correlation_strength=0.70, confidence=0.75, days_ago=2)
            ),
        ]

        # Select top 3 with max 2 per category
        selected = select_top_insights(
            insights,
            num_insights=3,
            min_confidence=0.6,
            max_per_category=2
        )

        assert len(selected) == 3, "Should select exactly 3 insights"

        # Count categories
        category_counts = {}
        for insight in selected:
            cat = insight.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # No category should have more than 2
        for cat, count in category_counts.items():
            assert count <= 2, f"Category {cat} has {count} insights, max should be 2"

    def test_diversity_with_multiple_categories(self):
        """Test diversity across multiple categories."""
        insights = [
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=9.0, confidence=0.88, days_ago=1)
            ),
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=8.5, confidence=0.85, days_ago=2)
            ),
            generate_insight_from_health_correlation(
                create_mock_health_correlation(correlation_strength=0.72, confidence=0.80, days_ago=1)
            ),
            generate_insight_from_habit_streak(
                create_mock_habit_streak(streak_length=45, is_active=True, confidence=0.88, days_since_completion=1)
            ),
            generate_insight_from_trend(
                create_mock_trend(direction=TrendDirection.DECLINING, confidence=0.78, days_ago=2)
            ),
        ]

        # Select top 3 with max 1 per category (forces diversity)
        selected = select_top_insights(
            insights,
            num_insights=3,
            min_confidence=0.6,
            max_per_category=1
        )

        assert len(selected) == 3, "Should select exactly 3 insights"

        # All should be from different categories
        categories = [insight.category for insight in selected]
        assert len(set(categories)) == 3, "All 3 insights should be from different categories"

    def test_confidence_threshold_filtering(self):
        """Test that insights below confidence threshold are filtered out."""
        insights = [
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=9.0, confidence=0.90, days_ago=1)
            ),
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=8.0, confidence=0.50, days_ago=2)  # Below threshold
            ),
            generate_insight_from_health_correlation(
                create_mock_health_correlation(correlation_strength=0.72, confidence=0.75, days_ago=1)
            ),
        ]

        # Select with confidence threshold 0.6
        selected = select_top_insights(
            insights,
            num_insights=3,
            min_confidence=0.6,
            max_per_category=2
        )

        # Should only get 2 (the one with 0.50 confidence is filtered out)
        assert len(selected) == 2, "Low confidence insight should be filtered"

        # All selected should meet threshold
        for insight in selected:
            assert insight.confidence_score >= 0.6, f"Insight has confidence {insight.confidence_score} < 0.6"

    def test_novelty_penalty_for_repeated_insights(self):
        """Test that repeated insights receive novelty penalties."""
        base_pattern = create_mock_task_pattern(completion_rate=9.0, confidence=0.88, days_ago=1)
        insight = generate_insight_from_task_pattern(base_pattern)

        # Historical insight with exact same summary
        historical = [insight.summary]

        # Calculate novelty adjustments
        adjustments = _calculate_novelty_adjustments(
            [insight],
            historical,
            penalty=0.5
        )

        # Should have negative adjustment for exact match
        # Exact match penalty: -0.40 * (1 - 0.5) = -0.20
        assert id(insight) in adjustments, "Should have novelty adjustment"
        assert adjustments[id(insight)] < 0, "Repeated insight should have negative adjustment"
        assert adjustments[id(insight)] == -0.20, f"Expected -0.20 for exact match, got {adjustments[id(insight)]}"

    def test_novelty_similarity_detection(self):
        """Test novelty detection with similar (not exact) insights."""
        insight1 = generate_insight_from_task_pattern(
            create_mock_task_pattern(completion_rate=9.0, confidence=0.88, days_ago=1)
        )

        # Create similar summary (>70% word overlap)
        historical_similar = ["Most productive between 9-11am windows"]

        adjustments = _calculate_novelty_adjustments(
            [insight1],
            historical_similar,
            penalty=0.5
        )

        # Should have penalty for high similarity (>70%)
        # Penalty: -0.30 * (1 - 0.5) = -0.15
        assert id(insight1) in adjustments
        assert adjustments[id(insight1)] < 0
        # Allow some tolerance for similarity calculation
        assert -0.20 <= adjustments[id(insight1)] <= -0.10

    def test_goal_alignment_scoring(self):
        """Test goal alignment increases scores for relevant insights."""
        insights = [
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=9.0, confidence=0.85, days_ago=1)
            ),
            generate_insight_from_health_correlation(
                create_mock_health_correlation(correlation_strength=0.72, confidence=0.80, days_ago=1)
            ),
        ]

        # User goals mention sleep
        user_goals = ["improve sleep quality", "increase productivity"]

        goal_scores = _calculate_goal_alignment_scores(insights, user_goals)

        # Health correlation (about sleep) should get higher alignment
        health_insight = insights[1]
        task_insight = insights[0]

        assert id(health_insight) in goal_scores
        assert id(task_insight) in goal_scores

        # Sleep-related insight should align better with "improve sleep quality"
        assert goal_scores[id(health_insight)] > goal_scores[id(task_insight)], \
            "Sleep insight should align better with sleep goal"

    def test_goal_alignment_keyword_matching(self):
        """Test goal alignment uses keyword matching."""
        pattern = create_mock_task_pattern(completion_rate=9.0, confidence=0.85, days_ago=1)
        pattern.description = "Most productive in morning hours"
        insight = generate_insight_from_task_pattern(pattern)

        # Goal mentions "morning productivity"
        user_goals = ["improve morning productivity"]

        goal_scores = _calculate_goal_alignment_scores([insight], user_goals)

        # Should have positive alignment (keyword match)
        assert id(insight) in goal_scores
        assert goal_scores[id(insight)] > 0, "Should have positive alignment for keyword match"

    def test_select_top_insights_with_personalization(self):
        """Test full selection with goal alignment and novelty."""
        insights = [
            generate_insight_from_task_pattern(
                create_mock_task_pattern(completion_rate=9.0, confidence=0.88, days_ago=1)
            ),
            generate_insight_from_health_correlation(
                create_mock_health_correlation(correlation_strength=0.72, confidence=0.80, days_ago=1)
            ),
            generate_insight_from_habit_streak(
                create_mock_habit_streak(streak_length=45, is_active=True, confidence=0.88, days_since_completion=1)
            ),
            generate_insight_from_trend(
                create_mock_trend(direction=TrendDirection.DECLINING, confidence=0.78, days_ago=2)
            ),
        ]

        # User goals favor sleep and habits
        user_goals = ["improve sleep", "build daily habits"]

        # Historical insights include the task pattern
        historical = [insights[0].summary]

        selected = select_top_insights(
            insights,
            num_insights=3,
            min_confidence=0.6,
            user_goals=user_goals,
            historical_insights=historical,
            novelty_penalty=0.5,
            max_per_category=2
        )

        assert len(selected) <= 3, "Should select at most 3 insights"

        # Task pattern (first insight) should likely NOT be in top 3 due to novelty penalty
        # Health and habit insights should be boosted by goal alignment


# ============================================================================
# Test Insight Formatting
# ============================================================================

class TestInsightFormatting:
    """Test insight formatting and output quality."""

    def test_insight_has_required_fields(self):
        """Test that generated insights have all required fields."""
        pattern = create_mock_task_pattern()
        insight = generate_insight_from_task_pattern(pattern)

        # Required fields
        assert insight.summary, "Should have summary"
        assert insight.detailed_description, "Should have detailed description"
        assert insight.suggested_action, "Should have suggested action"
        assert insight.supporting_evidence, "Should have supporting evidence"
        assert insight.category, "Should have category"

        # Summary should be concise (roughly 1-2 sentences)
        assert len(insight.summary) > 10, "Summary should be substantial"
        assert len(insight.summary) < 200, "Summary should be concise"

    def test_suggested_action_is_actionable(self):
        """Test that suggested actions are specific and actionable."""
        patterns_and_insights = [
            (create_mock_task_pattern(), generate_insight_from_task_pattern),
            (create_mock_health_correlation(), generate_insight_from_health_correlation),
            (create_mock_habit_streak(), generate_insight_from_habit_streak),
            (create_mock_trend(), generate_insight_from_trend),
        ]

        for pattern, generator in patterns_and_insights:
            insight = generator(pattern)

            # Action should be non-empty
            assert insight.suggested_action, f"Insight from {type(pattern).__name__} missing action"

            # Action should contain action verbs or imperatives
            action_lower = insight.suggested_action.lower()
            has_action_verb = any(
                verb in action_lower
                for verb in ["schedule", "aim", "prioritize", "maintain", "restart",
                            "investigate", "identify", "monitor", "optimize", "work", "consider"]
            )
            assert has_action_verb, f"Action should contain action verb: {insight.suggested_action}"

    def test_evidence_is_included(self):
        """Test that insights include supporting evidence from patterns."""
        pattern = create_mock_task_pattern()
        pattern.evidence = [
            "Evidence item 1",
            "Evidence item 2",
            "Evidence item 3",
        ]

        insight = generate_insight_from_task_pattern(pattern)

        # Evidence should be carried over
        assert len(insight.supporting_evidence) > 0, "Should include evidence"
        assert insight.supporting_evidence == pattern.evidence, "Should preserve pattern evidence"

    def test_insight_format_for_display(self):
        """Test the format_for_display method produces well-formatted output."""
        insight = generate_insight_from_task_pattern(
            create_mock_task_pattern()
        )

        # Test compact format
        compact = insight.format_for_display(include_details=False)
        assert "💡" in compact, "Should include emoji"
        assert insight.summary in compact, "Should include summary"
        assert insight.suggested_action in compact, "Should include action"
        assert "Confidence:" in compact, "Should include confidence"
        assert "Impact:" in compact, "Should include impact"

        # Should not include detailed description
        assert insight.detailed_description not in compact

        # Test detailed format
        detailed = insight.format_for_display(include_details=True)
        assert insight.detailed_description in detailed, "Should include detailed description"
        assert "Evidence:" in detailed, "Should include evidence section"

    def test_confidence_indicators_in_range(self):
        """Test that all confidence-related scores are in valid range."""
        patterns = [
            create_mock_task_pattern(confidence=0.95),
            create_mock_health_correlation(confidence=0.80),
            create_mock_habit_streak(confidence=0.88),
            create_mock_trend(confidence=0.75),
        ]

        generators = [
            generate_insight_from_task_pattern,
            generate_insight_from_health_correlation,
            generate_insight_from_habit_streak,
            generate_insight_from_trend,
        ]

        for pattern, generator in zip(patterns, generators):
            insight = generator(pattern)

            # All scores should be 0-1
            assert 0.0 <= insight.confidence_score <= 1.0, "Confidence out of range"
            assert 0.0 <= insight.significance_score <= 1.0, "Significance out of range"
            assert 0.0 <= insight.actionability_score <= 1.0, "Actionability out of range"
            assert 0.0 <= insight.impact_score <= 1.0, "Impact out of range"
            assert 0.0 <= insight.recency_score <= 1.0, "Recency out of range"
            assert 0.0 <= insight.novelty_score <= 1.0, "Novelty out of range"

            # Overall score should also be in range
            overall = insight.get_overall_score()
            assert 0.0 <= overall <= 1.0, f"Overall score out of range: {overall}"


# ============================================================================
# Test Batch Processing and Utilities
# ============================================================================

class TestBatchProcessing:
    """Test batch insight generation and filtering utilities."""

    def test_generate_insights_from_all_patterns(self):
        """Test batch generation from multiple pattern types."""
        task_patterns = [create_mock_task_pattern(days_ago=i) for i in range(2)]
        health_correlations = [create_mock_health_correlation(days_ago=i) for i in range(2)]
        habit_streaks = [create_mock_habit_streak(days_since_completion=i+1) for i in range(2)]
        trends = [create_mock_trend(days_ago=i) for i in range(2)]

        insights = generate_insights_from_all_patterns(
            task_patterns=task_patterns,
            health_correlations=health_correlations,
            habit_streaks=habit_streaks,
            trends=trends,
            recency_days=30
        )

        # Should generate 8 insights total (2 of each type)
        assert len(insights) == 8, f"Expected 8 insights, got {len(insights)}"

        # Check category distribution
        categories = [i.category for i in insights]
        assert categories.count(InsightCategory.TASK_COMPLETION) == 2
        assert categories.count(InsightCategory.HEALTH_CORRELATION) == 2
        assert categories.count(InsightCategory.HABIT) == 2
        assert categories.count(InsightCategory.TREND) == 2

    def test_generate_insights_with_empty_lists(self):
        """Test batch generation handles empty pattern lists gracefully."""
        insights = generate_insights_from_all_patterns(
            task_patterns=None,
            health_correlations=[],
            habit_streaks=None,
            trends=[],
            recency_days=30
        )

        assert insights == [], "Should return empty list for empty inputs"

    def test_rank_insights(self):
        """Test ranking insights by overall score."""
        # Create insights with different scores
        high_score_insight = generate_insight_from_task_pattern(
            create_mock_task_pattern(completion_rate=10.0, confidence=0.95, days_ago=1)
        )

        mid_score_insight = generate_insight_from_health_correlation(
            create_mock_health_correlation(correlation_strength=0.70, confidence=0.75, days_ago=10)
        )

        low_score_insight = generate_insight_from_trend(
            create_mock_trend(
                direction=TrendDirection.PLATEAU,
                change_percentage=2.0,
                trend_strength=0.50,
                confidence=0.65,
                days_ago=20
            )
        )

        insights = [low_score_insight, high_score_insight, mid_score_insight]

        ranked = rank_insights(insights)

        assert len(ranked) == 3

        # Should be sorted by score (highest first)
        scores = [i.get_overall_score() for i in ranked]
        assert scores[0] >= scores[1] >= scores[2], "Should be sorted by descending score"

        # High score should be first
        assert ranked[0] == high_score_insight

    def test_filter_insights_by_confidence(self):
        """Test filtering insights by confidence threshold."""
        insights = [
            generate_insight_from_task_pattern(
                create_mock_task_pattern(confidence=0.90, days_ago=1)
            ),
            generate_insight_from_task_pattern(
                create_mock_task_pattern(confidence=0.50, days_ago=2)
            ),
            generate_insight_from_task_pattern(
                create_mock_task_pattern(confidence=0.75, days_ago=3)
            ),
        ]

        filtered = filter_insights_by_confidence(insights, min_confidence=0.6)

        # Should only get 2 (0.90 and 0.75)
        assert len(filtered) == 2, f"Expected 2 insights with confidence >= 0.6, got {len(filtered)}"

        for insight in filtered:
            assert insight.confidence_score >= 0.6

    def test_filter_insights_by_category(self):
        """Test filtering insights by category."""
        insights = [
            generate_insight_from_task_pattern(create_mock_task_pattern()),
            generate_insight_from_health_correlation(create_mock_health_correlation()),
            generate_insight_from_task_pattern(create_mock_task_pattern()),
            generate_insight_from_habit_streak(create_mock_habit_streak()),
        ]

        task_insights = filter_insights_by_category(insights, InsightCategory.TASK_COMPLETION)
        assert len(task_insights) == 2, "Should get 2 task completion insights"

        health_insights = filter_insights_by_category(insights, InsightCategory.HEALTH_CORRELATION)
        assert len(health_insights) == 1, "Should get 1 health correlation insight"

        habit_insights = filter_insights_by_category(insights, InsightCategory.HABIT)
        assert len(habit_insights) == 1, "Should get 1 habit insight"


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_insights_list(self):
        """Test handling of empty insights list."""
        selected = select_top_insights([], num_insights=3)
        assert selected == [], "Should return empty list for empty input"

        ranked = rank_insights([])
        assert ranked == [], "Should return empty list for empty input"

    def test_fewer_insights_than_requested(self):
        """Test when fewer insights available than requested."""
        insights = [
            generate_insight_from_task_pattern(create_mock_task_pattern(confidence=0.90)),
            generate_insight_from_health_correlation(create_mock_health_correlation(confidence=0.85)),
        ]

        selected = select_top_insights(insights, num_insights=5)

        # Should return all available (2) even though 5 requested
        assert len(selected) == 2, "Should return all available insights"

    def test_all_insights_below_confidence_threshold(self):
        """Test when all insights are below confidence threshold."""
        insights = [
            generate_insight_from_task_pattern(
                create_mock_task_pattern(confidence=0.50, days_ago=1)
            ),
            generate_insight_from_task_pattern(
                create_mock_task_pattern(confidence=0.45, days_ago=2)
            ),
        ]

        selected = select_top_insights(insights, num_insights=3, min_confidence=0.6)

        # Should return empty list
        assert selected == [], "Should return empty when all below threshold"

    def test_very_old_data_recency_score(self):
        """Test recency score for very old data."""
        very_old = datetime.now() - timedelta(days=365)
        score = calculate_recency_score(very_old, recency_days=30)

        # Should be very low but still >= 0
        assert score >= 0.0, "Score should never be negative"
        assert score < 0.01, "Very old data should score near 0"

    def test_pattern_with_minimal_evidence(self):
        """Test insight generation when pattern has minimal evidence."""
        pattern = create_mock_task_pattern()
        pattern.evidence = []  # Empty evidence

        insight = generate_insight_from_task_pattern(pattern)

        # Should still generate insight
        assert insight is not None
        assert insight.supporting_evidence == []

    def test_zero_completion_rate_pattern(self):
        """Test task pattern with zero completion rate."""
        pattern = create_mock_task_pattern(completion_rate=0.0, confidence=0.70)
        insight = generate_insight_from_task_pattern(pattern)

        # Should generate insight with low impact
        assert insight.impact_score == 0.0, "Zero completion should have zero impact"

        # Should suggest avoiding that time
        assert "Avoid" in insight.suggested_action or "low" in insight.suggested_action.lower()

    def test_negative_correlation(self):
        """Test health correlation with negative correlation."""
        correlation = create_mock_health_correlation(
            correlation_strength=-0.65,
            effect_size=-30.0,
            confidence=0.75
        )

        insight = generate_insight_from_health_correlation(correlation)

        # Should handle negative correlation gracefully
        assert insight is not None
        # Impact should be based on absolute value
        assert insight.impact_score > 0, "Negative correlation should still have positive impact score"
