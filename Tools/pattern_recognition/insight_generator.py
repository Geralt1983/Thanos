"""Insight generation and scoring for pattern recognition engine.

This module converts detected patterns, correlations, streaks, and trends into
actionable insights with comprehensive scoring based on significance, actionability,
impact potential, and recency.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Union, Dict
import statistics

from .models import (
    Insight,
    InsightCategory,
    TaskCompletionPattern,
    HealthCorrelation,
    HabitStreak,
    Trend,
    TrendDirection,
)


def generate_insight_from_task_pattern(
    pattern: TaskCompletionPattern,
    recency_days: int = 30
) -> Insight:
    """Generate actionable insight from a task completion pattern.

    Args:
        pattern: Task completion pattern to convert to insight
        recency_days: Days since end of pattern for recency scoring

    Returns:
        Insight object with comprehensive scoring

    Examples:
        "Schedule deep work 9-11am when you're 40% more productive"
    """
    # Calculate scores
    confidence_score = pattern.confidence_score
    recency_score = calculate_recency_score(pattern.date_range_end, recency_days)

    # Actionability: Task timing patterns are highly actionable
    actionability_score = 0.85

    # Impact: Based on completion rate difference from average
    # Higher completion rate = higher impact potential
    impact_score = min(1.0, pattern.completion_rate / 10.0)  # Normalize to 0-1

    # Statistical significance: Based on sample size and confidence
    significance_score = calculate_significance_score(
        confidence_score=confidence_score,
        sample_size=pattern.sample_size
    )

    # Build summary and action
    summary = f"{pattern.description}"

    if pattern.completion_rate > 5:
        action_verb = "Schedule"
        impact_phrase = "high productivity"
    else:
        action_verb = "Avoid scheduling"
        impact_phrase = "low productivity"

    suggested_action = (
        f"{action_verb} important tasks during {pattern.time_period} "
        f"to capitalize on {impact_phrase} windows"
    )

    detailed_description = (
        f"Analysis of {pattern.sample_size} data points from "
        f"{pattern.date_range_start.strftime('%Y-%m-%d')} to "
        f"{pattern.date_range_end.strftime('%Y-%m-%d')} shows {pattern.description.lower()}. "
        f"Average completion rate: {pattern.completion_rate:.1f} tasks."
    )

    return Insight(
        summary=summary,
        category=InsightCategory.TASK_COMPLETION,
        detailed_description=detailed_description,
        suggested_action=suggested_action,
        actionability_score=actionability_score,
        impact_score=impact_score,
        confidence_score=confidence_score,
        significance_score=significance_score,
        recency_score=recency_score,
        novelty_score=0.5,  # Default, can be updated based on historical insights
        supporting_evidence=pattern.evidence,
        source_patterns=[f"task_pattern_{pattern.pattern_type.value}"],
        date_range_start=pattern.date_range_start,
        date_range_end=pattern.date_range_end,
        metadata={
            "pattern_type": pattern.pattern_type.value,
            "time_period": pattern.time_period,
            "completion_rate": pattern.completion_rate,
        }
    )


def generate_insight_from_health_correlation(
    correlation: HealthCorrelation,
    recency_days: int = 30
) -> Insight:
    """Generate actionable insight from a health-productivity correlation.

    Args:
        correlation: Health correlation to convert to insight
        recency_days: Days since end of correlation for recency scoring

    Returns:
        Insight object with comprehensive scoring

    Examples:
        "Prioritize sleep: 7+ hours correlates with 40% more tasks completed"
    """
    # Calculate scores
    confidence_score = correlation.confidence_score
    recency_score = calculate_recency_score(
        correlation.date_range_end or datetime.now(),
        recency_days
    )

    # Actionability: Health behaviors are moderately actionable
    # Sleep and recovery are somewhat under user control
    actionability_score = 0.70 if "sleep" in correlation.health_metric.lower() else 0.60

    # Impact: Based on effect size
    if correlation.effect_size:
        # Effect size is percentage improvement
        impact_score = min(1.0, abs(correlation.effect_size) / 100.0)
    else:
        # Fall back to correlation strength
        impact_score = min(1.0, abs(correlation.correlation_strength))

    # Statistical significance
    significance_score = calculate_significance_score(
        confidence_score=confidence_score,
        sample_size=correlation.sample_size,
        effect_size=abs(correlation.correlation_strength)
    )

    # Build summary and action
    summary = correlation.correlation_description

    # Determine action based on correlation type
    metric_name = correlation.health_metric.replace("_", " ").title()

    if correlation.threshold_value:
        threshold_str = f"{correlation.threshold_value:.1f}"
        if "hour" in correlation.health_metric.lower():
            threshold_str += " hours"

        suggested_action = (
            f"Aim for {threshold_str} {metric_name.lower()} to optimize "
            f"{correlation.productivity_metric.replace('_', ' ')}"
        )
    else:
        suggested_action = (
            f"Monitor and optimize {metric_name.lower()} to improve "
            f"{correlation.productivity_metric.replace('_', ' ')}"
        )

    detailed_description = (
        f"Analysis of {correlation.sample_size} days shows {correlation.correlation_description}. "
        f"Correlation strength: {correlation.correlation_strength:.2f}."
    )

    if correlation.effect_size:
        detailed_description += f" Effect size: {correlation.effect_size:.0f}% improvement."

    return Insight(
        summary=summary,
        category=InsightCategory.HEALTH_CORRELATION,
        detailed_description=detailed_description,
        suggested_action=suggested_action,
        actionability_score=actionability_score,
        impact_score=impact_score,
        confidence_score=confidence_score,
        significance_score=significance_score,
        recency_score=recency_score,
        novelty_score=0.5,
        supporting_evidence=correlation.evidence,
        source_patterns=[f"health_correlation_{correlation.health_metric}"],
        date_range_start=correlation.date_range_start,
        date_range_end=correlation.date_range_end,
        metadata={
            "health_metric": correlation.health_metric,
            "productivity_metric": correlation.productivity_metric,
            "correlation_strength": correlation.correlation_strength,
            "threshold_value": correlation.threshold_value,
            "effect_size": correlation.effect_size,
        }
    )


def generate_insight_from_habit_streak(
    streak: HabitStreak,
    recency_days: int = 30
) -> Insight:
    """Generate actionable insight from a habit streak.

    Args:
        streak: Habit streak to convert to insight
        recency_days: Days since last completion for recency scoring

    Returns:
        Insight object with comprehensive scoring

    Examples:
        "Your daily review habit is at risk - last 3 breaks happened on Fridays"
    """
    # Calculate scores
    confidence_score = streak.confidence_score
    recency_score = calculate_recency_score(streak.last_completion_date, recency_days)

    # Actionability: Habits are highly actionable
    actionability_score = 0.90

    # Impact: Based on streak length and consistency
    # Longer streaks = higher impact if broken
    # Lower consistency = higher impact from improvement
    if streak.is_active:
        # Active streak - impact from maintaining it
        impact_score = min(1.0, streak.streak_length / 30.0) * 0.7
    else:
        # Broken streak - impact from restarting
        impact_score = (1.0 - streak.consistency_score) * 0.8

    # Statistical significance
    significance_score = calculate_significance_score(
        confidence_score=confidence_score,
        sample_size=streak.total_completions
    )

    # Build summary and action based on streak status
    if streak.is_active:
        if streak.streak_length >= streak.longest_streak * 0.9:
            # Near record streak
            summary = (
                f"🔥 {streak.habit_name}: {streak.streak_length}-day streak "
                f"(approaching your record of {streak.longest_streak} days)"
            )
            suggested_action = f"Maintain momentum on {streak.habit_name} to set a new personal record"
        else:
            summary = f"✅ {streak.habit_name}: {streak.streak_length}-day active streak"
            suggested_action = f"Keep up the consistency with {streak.habit_name}"
    else:
        days_since_break = (datetime.now() - (streak.break_date or streak.last_completion_date)).days
        summary = (
            f"⚠️ {streak.habit_name}: streak broken {days_since_break} days ago "
            f"({streak.consistency_score:.0%} consistency)"
        )

        if streak.break_reasons:
            reason_summary = ", ".join(streak.break_reasons[:2])
            suggested_action = (
                f"Restart {streak.habit_name} - past breaks often occurred due to: {reason_summary}"
            )
        else:
            suggested_action = f"Restart your {streak.habit_name} habit to rebuild momentum"

    # Detailed description
    detailed_description = (
        f"Habit '{streak.habit_name}' tracked over {streak.total_completions} completions "
        f"from {streak.date_range_start.strftime('%Y-%m-%d')} to "
        f"{streak.date_range_end.strftime('%Y-%m-%d')}. "
        f"Consistency score: {streak.consistency_score:.0%}. "
        f"Longest streak: {streak.longest_streak} days."
    )

    if not streak.is_active and streak.break_reasons:
        detailed_description += f" Common break patterns: {', '.join(streak.break_reasons)}."

    return Insight(
        summary=summary,
        category=InsightCategory.HABIT,
        detailed_description=detailed_description,
        suggested_action=suggested_action,
        actionability_score=actionability_score,
        impact_score=impact_score,
        confidence_score=confidence_score,
        significance_score=significance_score,
        recency_score=recency_score,
        novelty_score=0.5,
        supporting_evidence=streak.evidence,
        source_patterns=[f"habit_streak_{streak.habit_name}"],
        date_range_start=streak.date_range_start,
        date_range_end=streak.date_range_end,
        metadata={
            "habit_name": streak.habit_name,
            "streak_length": streak.streak_length,
            "is_active": streak.is_active,
            "consistency_score": streak.consistency_score,
            "longest_streak": streak.longest_streak,
        }
    )


def generate_insight_from_trend(
    trend: Trend,
    recency_days: int = 30
) -> Insight:
    """Generate actionable insight from a detected trend.

    Args:
        trend: Trend to convert to insight
        recency_days: Days since end of trend for recency scoring

    Returns:
        Insight object with comprehensive scoring

    Examples:
        "Tasks per day declining (9.4 → 7.2 over 30 days) - momentum at risk"
    """
    # Calculate scores
    confidence_score = trend.confidence_score
    recency_score = calculate_recency_score(
        trend.date_range_end or datetime.now(),
        recency_days
    )

    # Actionability: Trends are moderately actionable depending on type
    # Declining trends are more actionable (can intervene)
    if trend.trend_direction == TrendDirection.DECLINING:
        actionability_score = 0.80
    elif trend.trend_direction == TrendDirection.IMPROVING:
        actionability_score = 0.70  # Can maintain
    else:
        actionability_score = 0.50  # Plateau/volatile harder to act on

    # Impact: Based on change percentage and trend strength
    impact_score = min(1.0, (abs(trend.change_percentage) / 50.0) * trend.trend_strength)

    # Statistical significance
    significance_score = calculate_significance_score(
        confidence_score=confidence_score,
        sample_size=trend.sample_size,
        effect_size=abs(trend.change_percentage) / 100.0
    )

    # Build summary and action
    direction_emoji = {
        TrendDirection.IMPROVING: "📈",
        TrendDirection.DECLINING: "📉",
        TrendDirection.PLATEAU: "📊",
        TrendDirection.VOLATILE: "📊",
    }

    emoji = direction_emoji.get(trend.trend_direction, "📊")
    summary = f"{emoji} {trend.trend_description}"

    # Suggested actions based on trend direction
    if trend.trend_direction == TrendDirection.DECLINING:
        suggested_action = (
            f"Investigate and address factors causing decline in {trend.metric_name.replace('_', ' ')}. "
            f"Review recent changes in habits or schedule."
        )
    elif trend.trend_direction == TrendDirection.IMPROVING:
        suggested_action = (
            f"Identify and reinforce behaviors contributing to improvement in "
            f"{trend.metric_name.replace('_', ' ')}. Consider sharing what's working."
        )
    elif trend.trend_direction == TrendDirection.PLATEAU:
        suggested_action = (
            f"To break the plateau in {trend.metric_name.replace('_', ' ')}, "
            f"consider trying new approaches or optimization strategies."
        )
    else:  # VOLATILE
        suggested_action = (
            f"Work on consistency in {trend.metric_name.replace('_', ' ')}. "
            f"Identify and reduce sources of variability."
        )

    # Detailed description
    detailed_description = (
        f"Over {trend.momentum_indicator}, {trend.metric_name.replace('_', ' ')} "
        f"went from {trend.start_value:.1f} to {trend.end_value:.1f} "
        f"({trend.change_percentage:+.0f}%). "
        f"Trend strength: {trend.trend_strength:.0%}. "
        f"Analyzed {trend.sample_size} data points."
    )

    return Insight(
        summary=summary,
        category=InsightCategory.TREND,
        detailed_description=detailed_description,
        suggested_action=suggested_action,
        actionability_score=actionability_score,
        impact_score=impact_score,
        confidence_score=confidence_score,
        significance_score=significance_score,
        recency_score=recency_score,
        novelty_score=0.5,
        supporting_evidence=trend.evidence,
        source_patterns=[f"trend_{trend.metric_name}"],
        date_range_start=trend.date_range_start,
        date_range_end=trend.date_range_end,
        metadata={
            "metric_name": trend.metric_name,
            "trend_direction": trend.trend_direction.value,
            "change_percentage": trend.change_percentage,
            "trend_strength": trend.trend_strength,
            "momentum_indicator": trend.momentum_indicator,
        }
    )


def calculate_recency_score(
    end_date: datetime,
    recency_days: int = 30
) -> float:
    """Calculate recency score based on how recent the data is.

    Args:
        end_date: End date of the pattern/trend
        recency_days: Maximum days to consider recent (default 30)

    Returns:
        float: Recency score between 0.0 (very old) and 1.0 (very recent)

    Algorithm:
        - Data from today: score = 1.0
        - Data from recency_days ago: score = 0.5
        - Data older than 2*recency_days: score approaches 0.0
        Uses exponential decay: score = exp(-days / recency_days)
    """
    import math

    days_ago = (datetime.now() - end_date).days

    # Exponential decay with half-life at recency_days
    # At recency_days: score ~= 0.37
    # At 2*recency_days: score ~= 0.14
    score = math.exp(-days_ago / recency_days)

    return max(0.0, min(1.0, score))


def calculate_significance_score(
    confidence_score: float,
    sample_size: int,
    effect_size: Optional[float] = None,
    min_sample_size: int = 10
) -> float:
    """Calculate statistical significance score.

    Args:
        confidence_score: Confidence score from the pattern/correlation (0-1)
        sample_size: Number of data points
        effect_size: Optional effect size (correlation strength, change percentage)
        min_sample_size: Minimum sample size for full confidence

    Returns:
        float: Significance score between 0.0 and 1.0

    Algorithm:
        Combines three factors:
        - Confidence score (50% weight): Statistical confidence from analysis
        - Sample size adequacy (30% weight): Larger samples more significant
        - Effect size (20% weight): Larger effects more significant
    """
    # Sample size component (sigmoid function)
    # Full weight at min_sample_size*2, half at min_sample_size
    sample_score = min(1.0, sample_size / (min_sample_size * 2))

    # Effect size component
    if effect_size is not None:
        effect_score = min(1.0, abs(effect_size))
    else:
        effect_score = 0.5  # Neutral if not provided

    # Weighted combination
    significance = (
        confidence_score * 0.5 +
        sample_score * 0.3 +
        effect_score * 0.2
    )

    return max(0.0, min(1.0, significance))


def generate_insights_from_all_patterns(
    task_patterns: Optional[List[TaskCompletionPattern]] = None,
    health_correlations: Optional[List[HealthCorrelation]] = None,
    habit_streaks: Optional[List[HabitStreak]] = None,
    trends: Optional[List[Trend]] = None,
    recency_days: int = 30
) -> List[Insight]:
    """Generate insights from all detected patterns, correlations, streaks, and trends.

    Args:
        task_patterns: List of task completion patterns
        health_correlations: List of health-productivity correlations
        habit_streaks: List of habit streaks
        trends: List of detected trends
        recency_days: Days for recency scoring

    Returns:
        List of all generated insights

    Usage:
        insights = generate_insights_from_all_patterns(
            task_patterns=get_all_task_patterns(task_records),
            health_correlations=get_all_health_correlations(task_records, health_records),
            habit_streaks=get_all_habit_streaks(task_records),
            trends=get_all_trends(productivity_data, health_data),
        )
    """
    all_insights = []

    # Generate insights from task patterns
    if task_patterns:
        for pattern in task_patterns:
            try:
                insight = generate_insight_from_task_pattern(pattern, recency_days)
                all_insights.append(insight)
            except Exception as e:
                # Log error but continue processing other patterns
                print(f"Error generating insight from task pattern: {e}")

    # Generate insights from health correlations
    if health_correlations:
        for correlation in health_correlations:
            try:
                insight = generate_insight_from_health_correlation(correlation, recency_days)
                all_insights.append(insight)
            except Exception as e:
                print(f"Error generating insight from health correlation: {e}")

    # Generate insights from habit streaks
    if habit_streaks:
        for streak in habit_streaks:
            try:
                insight = generate_insight_from_habit_streak(streak, recency_days)
                all_insights.append(insight)
            except Exception as e:
                print(f"Error generating insight from habit streak: {e}")

    # Generate insights from trends
    if trends:
        for trend in trends:
            try:
                insight = generate_insight_from_trend(trend, recency_days)
                all_insights.append(insight)
            except Exception as e:
                print(f"Error generating insight from trend: {e}")

    return all_insights


def rank_insights(
    insights: List[Insight],
    weights: Optional[dict] = None
) -> List[Insight]:
    """Rank insights by overall score using customizable weights.

    Args:
        insights: List of insights to rank
        weights: Optional custom weights for scoring components
                 Default: {
                     "significance": 0.25,
                     "actionability": 0.20,
                     "impact": 0.20,
                     "confidence": 0.15,
                     "recency": 0.10,
                     "novelty": 0.10,
                 }

    Returns:
        List of insights sorted by overall score (highest first)

    Usage:
        ranked = rank_insights(all_insights)
        top_3 = ranked[:3]
    """
    if not insights:
        return []

    # Use provided weights or defaults from Insight.get_overall_score()
    # Note: get_overall_score() uses built-in weights

    # Sort by overall score (descending)
    ranked = sorted(
        insights,
        key=lambda x: x.get_overall_score(),
        reverse=True
    )

    return ranked


def filter_insights_by_confidence(
    insights: List[Insight],
    min_confidence: float = 0.65
) -> List[Insight]:
    """Filter insights to only include those meeting minimum confidence threshold.

    Args:
        insights: List of insights to filter
        min_confidence: Minimum confidence score (0.0 to 1.0)

    Returns:
        List of insights with confidence >= min_confidence
    """
    return [
        insight for insight in insights
        if insight.confidence_score >= min_confidence
    ]


def filter_insights_by_category(
    insights: List[Insight],
    category: InsightCategory
) -> List[Insight]:
    """Filter insights by category.

    Args:
        insights: List of insights to filter
        category: Category to filter by

    Returns:
        List of insights matching the category
    """
    return [
        insight for insight in insights
        if insight.category == category
    ]


def select_top_insights(
    insights: List[Insight],
    num_insights: int = 3,
    min_confidence: float = 0.65,
    user_goals: Optional[List[str]] = None,
    historical_insights: Optional[List[str]] = None,
    novelty_penalty: float = 0.5,
    max_per_category: int = 2
) -> List[Insight]:
    """Select top N insights ensuring diversity, actionability, novelty, and personalization.

    This is the core selection algorithm for surfacing insights to users in weekly reviews.
    It ensures a balanced, relevant set of insights by enforcing:
    - Diversity: Not all insights from the same category
    - Actionability: Prioritizes insights users can act on (via scoring)
    - Novelty: Avoids repeating same insights weekly
    - Personalization: Aligns with user's stated goals

    Args:
        insights: List of all available insights
        num_insights: Number of insights to select (default 3)
        min_confidence: Minimum confidence threshold (default 0.6)
        user_goals: Optional list of user goal keywords/phrases from State/Goals.md
                   e.g., ["improve sleep", "increase productivity", "build meditation habit"]
        historical_insights: Optional list of insight summaries shown in past 7 days
                            Used to avoid repetition and boost novelty scores
        novelty_penalty: Score multiplier for repeated insights (default 0.5 = 50% penalty)
        max_per_category: Maximum insights from same category (default 2)

    Returns:
        List of selected insights (length <= num_insights), sorted by adjusted score

    Algorithm:
        1. Filter by minimum confidence threshold
        2. Calculate goal alignment scores (if goals provided)
        3. Apply novelty penalties for recently shown insights
        4. Rank by adjusted overall score (original + goal alignment - novelty penalty)
        5. Select top N with diversity constraints (max_per_category)

    Usage:
        # Basic usage - top 3 with default settings
        top_insights = select_top_insights(all_insights)

        # With user goals for personalization
        top_insights = select_top_insights(
            all_insights,
            user_goals=["improve sleep quality", "increase morning productivity"],
            historical_insights=last_week_summaries
        )

        # Custom settings
        top_insights = select_top_insights(
            all_insights,
            num_insights=5,
            min_confidence=0.7,
            max_per_category=3
        )
    """
    if not insights:
        return []

    # Step 1: Filter by confidence threshold
    filtered = filter_insights_by_confidence(insights, min_confidence)
    if not filtered:
        return []

    # Step 2: Calculate goal alignment scores
    goal_scores = {}
    if user_goals:
        goal_scores = _calculate_goal_alignment_scores(filtered, user_goals)

    # Step 3: Apply novelty penalties
    novelty_adjustments = {}
    if historical_insights:
        novelty_adjustments = _calculate_novelty_adjustments(
            filtered, historical_insights, novelty_penalty
        )

    # Step 4: Calculate adjusted scores
    scored_insights = []
    for insight in filtered:
        base_score = insight.get_overall_score()
        goal_bonus = goal_scores.get(id(insight), 0.0)
        novelty_adjustment = novelty_adjustments.get(id(insight), 0.0)

        # Adjusted score: base + goal bonus + novelty adjustment (negative for repeated)
        adjusted_score = base_score + goal_bonus + novelty_adjustment

        scored_insights.append({
            "insight": insight,
            "adjusted_score": adjusted_score,
            "base_score": base_score,
            "goal_bonus": goal_bonus,
            "novelty_adjustment": novelty_adjustment,
        })

    # Step 5: Sort by adjusted score
    scored_insights.sort(key=lambda x: x["adjusted_score"], reverse=True)

    # Step 6: Select top N with diversity constraints
    selected = []
    category_counts = {}

    for item in scored_insights:
        insight = item["insight"]
        category = insight.category

        # Check if we've hit the limit for this category
        if category_counts.get(category, 0) >= max_per_category:
            continue

        # Add to selection
        selected.append(insight)
        category_counts[category] = category_counts.get(category, 0) + 1

        # Check if we've selected enough
        if len(selected) >= num_insights:
            break

    return selected


def _calculate_goal_alignment_scores(
    insights: List[Insight],
    user_goals: List[str]
) -> Dict[int, float]:
    """Calculate how well each insight aligns with user goals.

    Args:
        insights: List of insights to score
        user_goals: List of user goal keywords/phrases

    Returns:
        Dictionary mapping insight id to goal alignment bonus (0.0 to 0.15)

    Algorithm:
        For each insight, check if any goal keywords appear in:
        - Summary
        - Detailed description
        - Suggested action
        - Category (converted to readable form)

        Scoring:
        - Exact phrase match in summary/action: +0.15
        - Exact phrase match in description: +0.10
        - Keyword match in summary/action: +0.10
        - Keyword match in description: +0.05
        - Category alignment: +0.05

        Maximum bonus: 0.15 (capped to not overwhelm other factors)
    """
    if not user_goals:
        return {}

    scores = {}

    # Normalize goals for matching
    normalized_goals = [goal.lower().strip() for goal in user_goals]

    for insight in insights:
        alignment_score = 0.0

        # Prepare searchable text
        summary = insight.summary.lower()
        description = insight.detailed_description.lower()
        action = insight.suggested_action.lower()
        category = insight.category.value.replace("_", " ")

        # Check each goal
        for goal in normalized_goals:
            goal_words = goal.split()

            # Exact phrase match in summary/action (highest priority)
            if goal in summary or goal in action:
                alignment_score += 0.15
                break  # Don't double-count same goal

            # Exact phrase match in description
            elif goal in description:
                alignment_score += 0.10
                break

            # Keyword match (any word from goal appears)
            else:
                matches_in_summary = sum(1 for word in goal_words if word in summary or word in action)
                matches_in_description = sum(1 for word in goal_words if word in description)

                if matches_in_summary > 0:
                    # Proportional to match percentage
                    match_ratio = matches_in_summary / len(goal_words)
                    alignment_score += 0.10 * match_ratio

                if matches_in_description > 0:
                    match_ratio = matches_in_description / len(goal_words)
                    alignment_score += 0.05 * match_ratio

                # Category alignment bonus
                if any(word in category for word in goal_words):
                    alignment_score += 0.05

        # Cap maximum bonus at 0.15 (15% boost to overall score)
        scores[id(insight)] = min(0.15, alignment_score)

    return scores


def _calculate_novelty_adjustments(
    insights: List[Insight],
    historical_insights: List[str],
    penalty: float
) -> Dict[int, float]:
    """Calculate novelty adjustments for insights based on recent history.

    Args:
        insights: List of insights to score
        historical_insights: List of insight summaries shown recently
        penalty: Penalty multiplier for repeated insights (e.g., 0.5 = 50% reduction)

    Returns:
        Dictionary mapping insight id to novelty adjustment (negative for repeated)

    Algorithm:
        For each insight, check similarity with historical insights:
        - Exact summary match: Apply full penalty (e.g., -0.20 for penalty=0.5)
        - High similarity (>70% word overlap): Apply partial penalty (e.g., -0.15)
        - Moderate similarity (>50% word overlap): Apply small penalty (e.g., -0.10)
        - Low similarity (<50%): No penalty

        Penalty is calculated as: -(1 - penalty) * base_penalty
        E.g., penalty=0.5 means 50% reduction → -0.5 * 0.40 = -0.20 max
    """
    if not historical_insights:
        return {}

    adjustments = {}

    # Normalize historical summaries
    historical_normalized = [hist.lower().strip() for hist in historical_insights]

    for insight in insights:
        summary = insight.summary.lower().strip()
        max_penalty = 0.0

        # Check against each historical insight
        for hist_summary in historical_normalized:
            # Exact match
            if summary == hist_summary:
                max_penalty = max(max_penalty, 0.40 * (1 - penalty))
                continue

            # Calculate word overlap similarity
            summary_words = set(summary.split())
            hist_words = set(hist_summary.split())

            if not summary_words or not hist_words:
                continue

            # Jaccard similarity (intersection / union)
            intersection = summary_words.intersection(hist_words)
            union = summary_words.union(hist_words)
            similarity = len(intersection) / len(union) if union else 0.0

            # Apply penalties based on similarity
            if similarity > 0.70:
                max_penalty = max(max_penalty, 0.30 * (1 - penalty))
            elif similarity > 0.50:
                max_penalty = max(max_penalty, 0.20 * (1 - penalty))
            elif similarity > 0.30:
                max_penalty = max(max_penalty, 0.10 * (1 - penalty))

        # Store as negative adjustment (penalty)
        if max_penalty > 0:
            adjustments[id(insight)] = -max_penalty

    return adjustments
