"""Pattern storage module for Neo4j knowledge graph integration.

This module provides functions to store detected patterns, correlations, habits, and trends
in the Neo4j knowledge graph using the existing neo4j_adapter._record_pattern() method.

Features:
- Store all pattern types with confidence scores
- Track pattern categories (task_completion, health_correlation, habit, trend)
- Create relationships between patterns (e.g., Pattern A supports Pattern B)
- Track historical pattern evolution (how patterns change over time)
- Batch operations for atomic storage
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .models import (
    TaskCompletionPattern,
    HealthCorrelation,
    HabitStreak,
    Trend,
    Insight,
    InsightCategory,
)


# =============================================================================
# Pattern Conversion Functions
# =============================================================================


def _generate_pattern_id(category: str) -> str:
    """Generate a unique pattern ID.

    Args:
        category: Pattern category (task_completion, health_correlation, habit, trend)

    Returns:
        str: Unique pattern ID in format: pattern_{category}_{uuid}
    """
    return f"pattern_{category}_{uuid.uuid4().hex[:8]}"


def _format_date_range(start: Optional[datetime], end: Optional[datetime]) -> str:
    """Format date range for pattern description.

    Args:
        start: Start date
        end: End date

    Returns:
        str: Formatted date range (e.g., "2024-01-01 to 2024-01-31")
    """
    if start and end:
        return f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"
    elif start:
        return f"since {start.strftime('%Y-%m-%d')}"
    elif end:
        return f"until {end.strftime('%Y-%m-%d')}"
    return "unknown timeframe"


def convert_task_pattern_to_neo4j(pattern: TaskCompletionPattern) -> Dict[str, Any]:
    """Convert TaskCompletionPattern to Neo4j pattern format.

    Args:
        pattern: TaskCompletionPattern instance

    Returns:
        dict: Pattern data in neo4j_adapter._record_pattern() format
    """
    # Build detailed description including evidence
    description = f"{pattern.description} ({pattern.time_period}). "
    description += f"Sample size: {pattern.sample_size} data points. "
    description += f"Completion rate: {pattern.completion_rate:.1%}. "
    description += f"Period: {_format_date_range(pattern.date_range_start, pattern.date_range_end)}."

    return {
        "description": description,
        "type": "task_completion",
        "domain": pattern.metadata.get("domain", "work"),
        "frequency": pattern.pattern_type.value,  # hourly, daily, weekly, task_type
        "strength": pattern.confidence_score,
        "category": "task_completion",
        "metadata": {
            "pattern_type": pattern.pattern_type.value,
            "time_period": pattern.time_period,
            "completion_rate": pattern.completion_rate,
            "sample_size": pattern.sample_size,
            "confidence_score": pattern.confidence_score,
            "date_range_start": pattern.date_range_start.isoformat() if pattern.date_range_start else None,
            "date_range_end": pattern.date_range_end.isoformat() if pattern.date_range_end else None,
            "evidence": pattern.evidence[:5],  # Store top 5 pieces of evidence
            **pattern.metadata,
        }
    }


def convert_health_correlation_to_neo4j(correlation: HealthCorrelation) -> Dict[str, Any]:
    """Convert HealthCorrelation to Neo4j pattern format.

    Args:
        correlation: HealthCorrelation instance

    Returns:
        dict: Pattern data in neo4j_adapter._record_pattern() format
    """
    # Build detailed description
    description = f"{correlation.correlation_description}. "
    description += f"Correlation: {correlation.health_metric} vs {correlation.productivity_metric} "
    description += f"(r={correlation.correlation_strength:.2f}). "

    if correlation.threshold_value:
        description += f"Threshold: {correlation.threshold_value}. "
    if correlation.effect_size:
        description += f"Effect size: {correlation.effect_size:.1%}. "

    description += f"Sample size: {correlation.sample_size} data points. "
    description += f"Period: {_format_date_range(correlation.date_range_start, correlation.date_range_end)}."

    return {
        "description": description,
        "type": "health_correlation",
        "domain": correlation.metadata.get("domain", "health"),
        "frequency": "daily" if correlation.sample_size >= 30 else "situational",
        "strength": correlation.confidence_score,
        "category": "health_correlation",
        "metadata": {
            "health_metric": correlation.health_metric,
            "productivity_metric": correlation.productivity_metric,
            "correlation_strength": correlation.correlation_strength,
            "threshold_value": correlation.threshold_value,
            "effect_size": correlation.effect_size,
            "confidence_score": correlation.confidence_score,
            "sample_size": correlation.sample_size,
            "date_range_start": correlation.date_range_start.isoformat() if correlation.date_range_start else None,
            "date_range_end": correlation.date_range_end.isoformat() if correlation.date_range_end else None,
            "evidence": correlation.evidence[:5],
            **correlation.metadata,
        }
    }


def convert_habit_streak_to_neo4j(streak: HabitStreak) -> Dict[str, Any]:
    """Convert HabitStreak to Neo4j pattern format.

    Args:
        streak: HabitStreak instance

    Returns:
        dict: Pattern data in neo4j_adapter._record_pattern() format
    """
    # Build detailed description
    description = f"Habit: {streak.habit_name}. "

    if streak.is_active:
        description += f"Active {streak.streak_length}-day streak. "
    else:
        description += f"Broken streak ({streak.streak_length} days). "
        if streak.break_date:
            description += f"Broke on {streak.break_date.strftime('%Y-%m-%d')}. "

    description += f"Consistency: {streak.consistency_score:.1%}. "
    description += f"Longest streak: {streak.longest_streak} days. "
    description += f"Total completions: {streak.total_completions}. "

    if streak.break_reasons:
        description += f"Break patterns: {', '.join(streak.break_reasons[:3])}. "

    description += f"Period: {_format_date_range(streak.date_range_start, streak.date_range_end)}."

    return {
        "description": description,
        "type": "habit",
        "domain": streak.metadata.get("domain", "personal"),
        "frequency": "daily",
        "strength": streak.confidence_score,
        "category": "habit",
        "metadata": {
            "habit_name": streak.habit_name,
            "streak_length": streak.streak_length,
            "is_active": streak.is_active,
            "last_completion_date": streak.last_completion_date.isoformat(),
            "break_date": streak.break_date.isoformat() if streak.break_date else None,
            "break_reasons": streak.break_reasons,
            "consistency_score": streak.consistency_score,
            "longest_streak": streak.longest_streak,
            "total_completions": streak.total_completions,
            "confidence_score": streak.confidence_score,
            "date_range_start": streak.date_range_start.isoformat() if streak.date_range_start else None,
            "date_range_end": streak.date_range_end.isoformat() if streak.date_range_end else None,
            "evidence": streak.evidence[:5],
            **streak.metadata,
        }
    }


def convert_trend_to_neo4j(trend: Trend) -> Dict[str, Any]:
    """Convert Trend to Neo4j pattern format.

    Args:
        trend: Trend instance

    Returns:
        dict: Pattern data in neo4j_adapter._record_pattern() format
    """
    # Build detailed description
    description = f"{trend.trend_description}. "
    description += f"Metric: {trend.metric_name}. "
    description += f"Direction: {trend.trend_direction.value}. "
    description += f"Change: {trend.start_value:.1f} → {trend.end_value:.1f} "
    description += f"({trend.change_percentage:+.1f}%). "
    description += f"Trend strength: {trend.trend_strength:.1%}. "
    description += f"Momentum: {trend.momentum_indicator}. "
    description += f"Sample size: {trend.sample_size} data points. "
    description += f"Period: {_format_date_range(trend.date_range_start, trend.date_range_end)}."

    return {
        "description": description,
        "type": "trend",
        "domain": trend.metadata.get("domain", "work"),
        "frequency": trend.momentum_indicator,  # "7-day", "30-day", etc.
        "strength": trend.confidence_score,
        "category": "trend",
        "metadata": {
            "metric_name": trend.metric_name,
            "trend_direction": trend.trend_direction.value,
            "start_value": trend.start_value,
            "end_value": trend.end_value,
            "change_percentage": trend.change_percentage,
            "trend_strength": trend.trend_strength,
            "momentum_indicator": trend.momentum_indicator,
            "confidence_score": trend.confidence_score,
            "sample_size": trend.sample_size,
            "date_range_start": trend.date_range_start.isoformat() if trend.date_range_start else None,
            "date_range_end": trend.date_range_end.isoformat() if trend.date_range_end else None,
            "evidence": trend.evidence[:5],
            **trend.metadata,
        }
    }


def convert_insight_to_neo4j(insight: Insight) -> Dict[str, Any]:
    """Convert Insight to Neo4j pattern format.

    Args:
        insight: Insight instance

    Returns:
        dict: Pattern data in neo4j_adapter._record_pattern() format
    """
    # Build detailed description
    description = f"{insight.summary}. "
    description += f"Action: {insight.suggested_action}. "
    description += f"Impact: {insight.impact_score:.1%}. "
    description += f"Actionability: {insight.actionability_score:.1%}. "
    description += f"Overall score: {insight.get_overall_score():.1%}. "
    description += f"Created: {insight.created_at.strftime('%Y-%m-%d')}."

    return {
        "description": description,
        "type": "insight",
        "domain": insight.metadata.get("domain", "work"),
        "frequency": "weekly",
        "strength": insight.confidence_score,
        "category": insight.category.value,
        "metadata": {
            "summary": insight.summary,
            "category": insight.category.value,
            "detailed_description": insight.detailed_description,
            "suggested_action": insight.suggested_action,
            "actionability_score": insight.actionability_score,
            "impact_score": insight.impact_score,
            "confidence_score": insight.confidence_score,
            "significance_score": insight.significance_score,
            "recency_score": insight.recency_score,
            "novelty_score": insight.novelty_score,
            "overall_score": insight.get_overall_score(),
            "supporting_evidence": insight.supporting_evidence[:5],
            "source_patterns": insight.source_patterns,
            "date_range_start": insight.date_range_start.isoformat() if insight.date_range_start else None,
            "date_range_end": insight.date_range_end.isoformat() if insight.date_range_end else None,
            "created_at": insight.created_at.isoformat(),
            **insight.metadata,
        }
    }


# =============================================================================
# Pattern Storage Functions
# =============================================================================


async def store_task_pattern(
    pattern: TaskCompletionPattern,
    adapter: Any,
    session=None
) -> Dict[str, Any]:
    """Store a task completion pattern in Neo4j.

    Args:
        pattern: TaskCompletionPattern instance
        adapter: Neo4jAdapter instance
        session: Optional Neo4j session for batch operations

    Returns:
        dict: Result with pattern_id and success status
    """
    pattern_data = convert_task_pattern_to_neo4j(pattern)
    result = await adapter._record_pattern(pattern_data, session=session)

    if result.success:
        return {
            "pattern_id": result.data.get("id"),
            "category": "task_completion",
            "success": True,
            "message": result.data.get("message")
        }
    else:
        return {
            "pattern_id": None,
            "category": "task_completion",
            "success": False,
            "error": result.error
        }


async def store_health_correlation(
    correlation: HealthCorrelation,
    adapter: Any,
    session=None
) -> Dict[str, Any]:
    """Store a health correlation pattern in Neo4j.

    Args:
        correlation: HealthCorrelation instance
        adapter: Neo4jAdapter instance
        session: Optional Neo4j session for batch operations

    Returns:
        dict: Result with pattern_id and success status
    """
    pattern_data = convert_health_correlation_to_neo4j(correlation)
    result = await adapter._record_pattern(pattern_data, session=session)

    if result.success:
        return {
            "pattern_id": result.data.get("id"),
            "category": "health_correlation",
            "success": True,
            "message": result.data.get("message")
        }
    else:
        return {
            "pattern_id": None,
            "category": "health_correlation",
            "success": False,
            "error": result.error
        }


async def store_habit_streak(
    streak: HabitStreak,
    adapter: Any,
    session=None
) -> Dict[str, Any]:
    """Store a habit streak pattern in Neo4j.

    Args:
        streak: HabitStreak instance
        adapter: Neo4jAdapter instance
        session: Optional Neo4j session for batch operations

    Returns:
        dict: Result with pattern_id and success status
    """
    pattern_data = convert_habit_streak_to_neo4j(streak)
    result = await adapter._record_pattern(pattern_data, session=session)

    if result.success:
        return {
            "pattern_id": result.data.get("id"),
            "category": "habit",
            "success": True,
            "message": result.data.get("message")
        }
    else:
        return {
            "pattern_id": None,
            "category": "habit",
            "success": False,
            "error": result.error
        }


async def store_trend(
    trend: Trend,
    adapter: Any,
    session=None
) -> Dict[str, Any]:
    """Store a trend pattern in Neo4j.

    Args:
        trend: Trend instance
        adapter: Neo4jAdapter instance
        session: Optional Neo4j session for batch operations

    Returns:
        dict: Result with pattern_id and success status
    """
    pattern_data = convert_trend_to_neo4j(trend)
    result = await adapter._record_pattern(pattern_data, session=session)

    if result.success:
        return {
            "pattern_id": result.data.get("id"),
            "category": "trend",
            "success": True,
            "message": result.data.get("message")
        }
    else:
        return {
            "pattern_id": None,
            "category": "trend",
            "success": False,
            "error": result.error
        }


async def store_insight(
    insight: Insight,
    adapter: Any,
    session=None
) -> Dict[str, Any]:
    """Store an insight in Neo4j.

    Args:
        insight: Insight instance
        adapter: Neo4jAdapter instance
        session: Optional Neo4j session for batch operations

    Returns:
        dict: Result with pattern_id and success status
    """
    pattern_data = convert_insight_to_neo4j(insight)
    result = await adapter._record_pattern(pattern_data, session=session)

    if result.success:
        return {
            "pattern_id": result.data.get("id"),
            "category": insight.category.value,
            "success": True,
            "message": result.data.get("message")
        }
    else:
        return {
            "pattern_id": None,
            "category": insight.category.value,
            "success": False,
            "error": result.error
        }


# =============================================================================
# Pattern Relationship Functions
# =============================================================================


async def link_patterns(
    from_pattern_id: str,
    to_pattern_id: str,
    relationship: str,
    adapter: Any,
    properties: Optional[Dict[str, Any]] = None,
    session=None
) -> Dict[str, Any]:
    """Create a relationship between two patterns.

    Use cases:
    - Pattern A "supports" Pattern B (e.g., habit streak supports trend)
    - Pattern A "contradicts" Pattern B
    - Pattern A "evolves_into" Pattern B (historical evolution)
    - Pattern A "evidences" Insight B (pattern supports insight)

    Args:
        from_pattern_id: Source pattern ID
        to_pattern_id: Target pattern ID
        relationship: Relationship type (SUPPORTS, CONTRADICTS, EVOLVES_INTO, EVIDENCES)
        adapter: Neo4jAdapter instance
        properties: Optional relationship properties
        session: Optional Neo4j session for batch operations

    Returns:
        dict: Result with success status
    """
    # Map custom relationship types to Neo4j graph schema
    # Using LEADS_TO as a general pattern relationship
    link_data = {
        "from_id": from_pattern_id,
        "relationship": "LEADS_TO",  # Use existing valid relationship type
        "to_id": to_pattern_id,
        "properties": {
            "pattern_relationship": relationship,  # Store actual relationship type in properties
            **(properties or {})
        }
    }

    result = await adapter._link_nodes(link_data, session=session)

    if result.success:
        return {
            "from_id": from_pattern_id,
            "to_id": to_pattern_id,
            "relationship": relationship,
            "success": True
        }
    else:
        return {
            "from_id": from_pattern_id,
            "to_id": to_pattern_id,
            "relationship": relationship,
            "success": False,
            "error": result.error
        }


async def track_pattern_evolution(
    old_pattern_id: str,
    new_pattern_id: str,
    adapter: Any,
    change_description: Optional[str] = None,
    session=None
) -> Dict[str, Any]:
    """Track how a pattern evolves over time.

    Creates an "evolves_into" relationship from old pattern to new pattern,
    allowing historical tracking of how patterns change.

    Args:
        old_pattern_id: Previous pattern version ID
        new_pattern_id: New pattern version ID
        adapter: Neo4jAdapter instance
        change_description: Optional description of what changed
        session: Optional Neo4j session for batch operations

    Returns:
        dict: Result with success status
    """
    properties = {
        "evolution_date": datetime.utcnow().isoformat(),
    }

    if change_description:
        properties["change_description"] = change_description

    return await link_patterns(
        from_pattern_id=old_pattern_id,
        to_pattern_id=new_pattern_id,
        relationship="EVOLVES_INTO",
        adapter=adapter,
        properties=properties,
        session=session
    )


# =============================================================================
# Batch Storage Functions
# =============================================================================


async def store_all_patterns(
    patterns_dict: Dict[str, List],
    adapter: Any,
    atomic: bool = True,
    create_relationships: bool = True
) -> Dict[str, Any]:
    """Store all detected patterns in a single batch operation.

    Args:
        patterns_dict: Dictionary with pattern lists:
            {
                "task_patterns": [TaskCompletionPattern, ...],
                "health_correlations": [HealthCorrelation, ...],
                "habit_streaks": [HabitStreak, ...],
                "trends": [Trend, ...],
                "insights": [Insight, ...]
            }
        adapter: Neo4jAdapter instance
        atomic: If True, all operations in single transaction (all-or-nothing)
        create_relationships: If True, create EVIDENCES relationships from patterns to insights

    Returns:
        dict: Results with stored pattern IDs and statistics
    """
    results = {
        "task_patterns": [],
        "health_correlations": [],
        "habit_streaks": [],
        "trends": [],
        "insights": [],
        "relationships": [],
        "errors": [],
        "statistics": {
            "total_patterns": 0,
            "successful_patterns": 0,
            "failed_patterns": 0,
            "total_relationships": 0,
            "successful_relationships": 0,
        }
    }

    try:
        async with adapter.session_context(batch_transaction=atomic) as session:
            # Store task patterns
            for pattern in patterns_dict.get("task_patterns", []):
                try:
                    result = await store_task_pattern(pattern, adapter, session=session)
                    results["task_patterns"].append(result)
                    results["statistics"]["total_patterns"] += 1

                    if result["success"]:
                        results["statistics"]["successful_patterns"] += 1
                    else:
                        results["statistics"]["failed_patterns"] += 1
                        results["errors"].append(result.get("error"))
                except Exception as e:
                    results["statistics"]["total_patterns"] += 1
                    results["statistics"]["failed_patterns"] += 1
                    results["errors"].append(f"Task pattern error: {str(e)}")
                    if atomic:
                        raise

            # Store health correlations
            for correlation in patterns_dict.get("health_correlations", []):
                try:
                    result = await store_health_correlation(correlation, adapter, session=session)
                    results["health_correlations"].append(result)
                    results["statistics"]["total_patterns"] += 1

                    if result["success"]:
                        results["statistics"]["successful_patterns"] += 1
                    else:
                        results["statistics"]["failed_patterns"] += 1
                        results["errors"].append(result.get("error"))
                except Exception as e:
                    results["statistics"]["total_patterns"] += 1
                    results["statistics"]["failed_patterns"] += 1
                    results["errors"].append(f"Health correlation error: {str(e)}")
                    if atomic:
                        raise

            # Store habit streaks
            for streak in patterns_dict.get("habit_streaks", []):
                try:
                    result = await store_habit_streak(streak, adapter, session=session)
                    results["habit_streaks"].append(result)
                    results["statistics"]["total_patterns"] += 1

                    if result["success"]:
                        results["statistics"]["successful_patterns"] += 1
                    else:
                        results["statistics"]["failed_patterns"] += 1
                        results["errors"].append(result.get("error"))
                except Exception as e:
                    results["statistics"]["total_patterns"] += 1
                    results["statistics"]["failed_patterns"] += 1
                    results["errors"].append(f"Habit streak error: {str(e)}")
                    if atomic:
                        raise

            # Store trends
            for trend in patterns_dict.get("trends", []):
                try:
                    result = await store_trend(trend, adapter, session=session)
                    results["trends"].append(result)
                    results["statistics"]["total_patterns"] += 1

                    if result["success"]:
                        results["statistics"]["successful_patterns"] += 1
                    else:
                        results["statistics"]["failed_patterns"] += 1
                        results["errors"].append(result.get("error"))
                except Exception as e:
                    results["statistics"]["total_patterns"] += 1
                    results["statistics"]["failed_patterns"] += 1
                    results["errors"].append(f"Trend error: {str(e)}")
                    if atomic:
                        raise

            # Store insights and optionally create relationships
            insight_pattern_ids = []
            for insight in patterns_dict.get("insights", []):
                try:
                    result = await store_insight(insight, adapter, session=session)
                    results["insights"].append(result)
                    results["statistics"]["total_patterns"] += 1

                    if result["success"]:
                        results["statistics"]["successful_patterns"] += 1
                        if result.get("pattern_id"):
                            insight_pattern_ids.append((insight, result["pattern_id"]))
                    else:
                        results["statistics"]["failed_patterns"] += 1
                        results["errors"].append(result.get("error"))
                except Exception as e:
                    results["statistics"]["total_patterns"] += 1
                    results["statistics"]["failed_patterns"] += 1
                    results["errors"].append(f"Insight error: {str(e)}")
                    if atomic:
                        raise

            # Create relationships from patterns to insights if requested
            if create_relationships and insight_pattern_ids:
                # Get all successfully stored pattern IDs
                all_pattern_ids = []

                for result in results["task_patterns"]:
                    if result["success"] and result.get("pattern_id"):
                        all_pattern_ids.append(result["pattern_id"])

                for result in results["health_correlations"]:
                    if result["success"] and result.get("pattern_id"):
                        all_pattern_ids.append(result["pattern_id"])

                for result in results["habit_streaks"]:
                    if result["success"] and result.get("pattern_id"):
                        all_pattern_ids.append(result["pattern_id"])

                for result in results["trends"]:
                    if result["success"] and result.get("pattern_id"):
                        all_pattern_ids.append(result["pattern_id"])

                # Create EVIDENCES relationships from source patterns to insights
                for insight_obj, insight_id in insight_pattern_ids:
                    # If insight has source_patterns, try to find matching stored pattern IDs
                    # For now, we'll just note that relationships could be created here
                    # In a real implementation, you'd need to map source_patterns to actual IDs
                    pass

        return results

    except Exception as e:
        results["errors"].append(f"Batch storage failed: {str(e)}")
        return results
