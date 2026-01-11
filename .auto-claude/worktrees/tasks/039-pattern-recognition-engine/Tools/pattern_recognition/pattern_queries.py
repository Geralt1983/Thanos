"""Pattern query methods for persona agents to access stored patterns.

This module provides methods for persona agents to query patterns from the Neo4j
knowledge graph. Patterns can be filtered by category, recency, topic, or confidence.

Usage:
    from Tools.pattern_recognition.pattern_queries import (
        get_patterns_by_category,
        get_recent_insights,
        get_patterns_related_to,
    )

    # Get all habit patterns
    habits = await get_patterns_by_category("habit", adapter)

    # Get last 5 insights
    insights = await get_recent_insights(adapter, limit=5)

    # Find patterns about sleep
    sleep_patterns = await get_patterns_related_to("sleep", adapter)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from .models import (
    TaskCompletionPattern,
    HealthCorrelation,
    HabitStreak,
    Trend,
    Insight,
    PatternType,
    TrendDirection,
    InsightCategory,
)


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_pattern_from_neo4j(pattern_data: Dict[str, Any]) -> Optional[Union[
    TaskCompletionPattern, HealthCorrelation, HabitStreak, Trend, Insight
]]:
    """Parse a pattern from Neo4j storage format back into model objects.

    Args:
        pattern_data: Raw pattern data from Neo4j with 'type' and 'metadata' fields

    Returns:
        Pattern model object or None if parsing fails
    """
    try:
        pattern_type = pattern_data.get("type")
        metadata = pattern_data.get("metadata", {})

        if pattern_type == "task_completion":
            return TaskCompletionPattern(
                pattern_type=PatternType(metadata.get("pattern_type", "hourly")),
                description=pattern_data.get("description", ""),
                time_period=metadata.get("time_period", ""),
                completion_rate=metadata.get("completion_rate", 0.0),
                sample_size=metadata.get("sample_size", 0),
                confidence_score=metadata.get("confidence_score", 0.0),
                date_range_start=datetime.fromisoformat(metadata["date_range_start"]) if metadata.get("date_range_start") else datetime.now(),
                date_range_end=datetime.fromisoformat(metadata["date_range_end"]) if metadata.get("date_range_end") else datetime.now(),
                evidence=metadata.get("evidence", []),
                metadata={k: v for k, v in metadata.items() if k not in ["pattern_type", "time_period", "completion_rate", "sample_size", "confidence_score", "date_range_start", "date_range_end", "evidence"]},
            )

        elif pattern_type == "health_correlation":
            return HealthCorrelation(
                health_metric=metadata.get("health_metric", ""),
                productivity_metric=metadata.get("productivity_metric", ""),
                correlation_strength=metadata.get("correlation_strength", 0.0),
                correlation_description=pattern_data.get("description", ""),
                threshold_value=metadata.get("threshold_value"),
                effect_size=metadata.get("effect_size"),
                confidence_score=metadata.get("confidence_score", 0.0),
                sample_size=metadata.get("sample_size", 0),
                date_range_start=datetime.fromisoformat(metadata["date_range_start"]) if metadata.get("date_range_start") else None,
                date_range_end=datetime.fromisoformat(metadata["date_range_end"]) if metadata.get("date_range_end") else None,
                evidence=metadata.get("evidence", []),
                metadata={k: v for k, v in metadata.items() if k not in ["health_metric", "productivity_metric", "correlation_strength", "threshold_value", "effect_size", "confidence_score", "sample_size", "date_range_start", "date_range_end", "evidence"]},
            )

        elif pattern_type == "habit":
            return HabitStreak(
                habit_name=metadata.get("habit_name", ""),
                streak_length=metadata.get("streak_length", 0),
                is_active=metadata.get("is_active", False),
                last_completion_date=datetime.fromisoformat(metadata["last_completion_date"]) if metadata.get("last_completion_date") else datetime.now(),
                break_date=datetime.fromisoformat(metadata["break_date"]) if metadata.get("break_date") else None,
                break_reasons=metadata.get("break_reasons", []),
                consistency_score=metadata.get("consistency_score", 0.0),
                longest_streak=metadata.get("longest_streak", 0),
                total_completions=metadata.get("total_completions", 0),
                confidence_score=metadata.get("confidence_score", 0.0),
                date_range_start=datetime.fromisoformat(metadata["date_range_start"]) if metadata.get("date_range_start") else None,
                date_range_end=datetime.fromisoformat(metadata["date_range_end"]) if metadata.get("date_range_end") else None,
                evidence=metadata.get("evidence", []),
                metadata={k: v for k, v in metadata.items() if k not in ["habit_name", "streak_length", "is_active", "last_completion_date", "break_date", "break_reasons", "consistency_score", "longest_streak", "total_completions", "confidence_score", "date_range_start", "date_range_end", "evidence"]},
            )

        elif pattern_type == "trend":
            return Trend(
                metric_name=metadata.get("metric_name", ""),
                trend_direction=TrendDirection(metadata.get("trend_direction", "plateau")),
                trend_description=pattern_data.get("description", ""),
                start_value=metadata.get("start_value", 0.0),
                end_value=metadata.get("end_value", 0.0),
                change_percentage=metadata.get("change_percentage", 0.0),
                trend_strength=metadata.get("trend_strength", 0.0),
                momentum_indicator=metadata.get("momentum_indicator", ""),
                confidence_score=metadata.get("confidence_score", 0.0),
                sample_size=metadata.get("sample_size", 0),
                date_range_start=datetime.fromisoformat(metadata["date_range_start"]) if metadata.get("date_range_start") else None,
                date_range_end=datetime.fromisoformat(metadata["date_range_end"]) if metadata.get("date_range_end") else None,
                evidence=metadata.get("evidence", []),
                metadata={k: v for k, v in metadata.items() if k not in ["metric_name", "trend_direction", "start_value", "end_value", "change_percentage", "trend_strength", "momentum_indicator", "confidence_score", "sample_size", "date_range_start", "date_range_end", "evidence"]},
            )

        elif pattern_type == "insight":
            return Insight(
                summary=metadata.get("summary", ""),
                category=InsightCategory(metadata.get("category", "behavioral")),
                detailed_description=metadata.get("detailed_description", ""),
                suggested_action=metadata.get("suggested_action", ""),
                actionability_score=metadata.get("actionability_score", 0.0),
                impact_score=metadata.get("impact_score", 0.0),
                confidence_score=metadata.get("confidence_score", 0.0),
                significance_score=metadata.get("significance_score", 0.0),
                recency_score=metadata.get("recency_score", 0.0),
                novelty_score=metadata.get("novelty_score", 0.5),
                supporting_evidence=metadata.get("supporting_evidence", []),
                source_patterns=metadata.get("source_patterns", []),
                date_range_start=datetime.fromisoformat(metadata["date_range_start"]) if metadata.get("date_range_start") else None,
                date_range_end=datetime.fromisoformat(metadata["date_range_end"]) if metadata.get("date_range_end") else None,
                created_at=datetime.fromisoformat(metadata["created_at"]) if metadata.get("created_at") else datetime.now(),
                metadata={k: v for k, v in metadata.items() if k not in ["summary", "category", "detailed_description", "suggested_action", "actionability_score", "impact_score", "confidence_score", "significance_score", "recency_score", "novelty_score", "supporting_evidence", "source_patterns", "date_range_start", "date_range_end", "created_at"]},
            )

        return None

    except Exception as e:
        # Graceful degradation - log error but don't crash
        print(f"Warning: Failed to parse pattern from Neo4j: {str(e)}")
        return None


def _build_category_filter(category: str) -> str:
    """Build Neo4j query filter for pattern category.

    Args:
        category: Pattern category (task_completion, health_correlation, habit, trend, insight)

    Returns:
        str: Cypher query filter clause
    """
    # Map user-friendly names to stored categories
    category_map = {
        "task": "task_completion",
        "task_completion": "task_completion",
        "health": "health_correlation",
        "health_correlation": "health_correlation",
        "habit": "habit",
        "habits": "habit",
        "trend": "trend",
        "trends": "trend",
        "insight": "insight",
        "insights": "insight",
        "behavioral": "behavioral",
    }

    normalized = category_map.get(category.lower(), category.lower())
    return f"p.category = '{normalized}' OR p.type = '{normalized}'"


def _build_topic_filter(topic: str) -> List[str]:
    """Build search keywords from topic query.

    Args:
        topic: Topic or keywords to search for (e.g., "sleep", "productivity", "morning")

    Returns:
        List[str]: List of search keywords
    """
    # Expand topic into related terms
    topic_expansions = {
        "sleep": ["sleep", "rest", "bedtime", "wake", "readiness", "tired"],
        "productivity": ["productivity", "tasks", "completion", "work", "focus", "output"],
        "morning": ["morning", "am", "wake", "start", "early"],
        "evening": ["evening", "pm", "night", "late"],
        "energy": ["energy", "readiness", "vitality", "fatigue", "tired"],
        "habit": ["habit", "streak", "consistency", "routine", "daily"],
        "exercise": ["exercise", "workout", "fitness", "activity", "steps", "movement"],
        "focus": ["focus", "concentration", "attention", "deep work", "flow"],
    }

    keywords = [topic.lower()]

    # Add expanded terms if available
    for key, terms in topic_expansions.items():
        if key in topic.lower():
            keywords.extend(terms)

    return list(set(keywords))  # Remove duplicates


# =============================================================================
# Query Functions
# =============================================================================


async def get_patterns_by_category(
    category: str,
    adapter: Any,
    limit: Optional[int] = None,
    min_confidence: float = 0.0,
    include_metadata: bool = True
) -> List[Union[TaskCompletionPattern, HealthCorrelation, HabitStreak, Trend, Insight]]:
    """Get patterns filtered by category.

    Persona agents can use this to retrieve specific types of patterns for context
    and decision-making.

    Args:
        category: Pattern category (task_completion, health_correlation, habit, trend, insight)
        adapter: Neo4jAdapter instance
        limit: Maximum number of patterns to return (None for all)
        min_confidence: Minimum confidence score filter (0.0 to 1.0)
        include_metadata: Whether to include full metadata in results

    Returns:
        List of pattern model objects

    Examples:
        # Get all habit patterns
        habits = await get_patterns_by_category("habit", adapter)

        # Get high-confidence task patterns
        task_patterns = await get_patterns_by_category(
            "task_completion",
            adapter,
            min_confidence=0.7,
            limit=10
        )
    """
    try:
        # Build Cypher query to fetch patterns by category
        category_filter = _build_category_filter(category)

        query = f"""
        MATCH (p:Pattern)
        WHERE ({category_filter})
        AND p.strength >= $min_confidence
        RETURN p
        ORDER BY p.strength DESC, p.created_at DESC
        {f'LIMIT {limit}' if limit else ''}
        """

        # Execute query via adapter
        result = await adapter.execute_query(
            query,
            parameters={"min_confidence": min_confidence}
        )

        if not result.success:
            print(f"Warning: Failed to query patterns by category: {result.error}")
            return []

        # Parse results into model objects
        patterns = []
        for record in result.data.get("records", []):
            pattern_node = record.get("p", {})
            pattern_obj = _parse_pattern_from_neo4j(pattern_node)
            if pattern_obj:
                patterns.append(pattern_obj)

        return patterns

    except Exception as e:
        print(f"Error querying patterns by category: {str(e)}")
        return []


async def get_recent_insights(
    adapter: Any,
    limit: int = 5,
    days_back: int = 7,
    min_confidence: float = 0.6,
    categories: Optional[List[str]] = None
) -> List[Insight]:
    """Get recent insights, optionally filtered by category.

    Persona agents can use this to access the latest pattern-based insights
    for informing recommendations and decision-making.

    Args:
        adapter: Neo4jAdapter instance
        limit: Maximum number of insights to return (default 5)
        days_back: How many days back to search (default 7)
        min_confidence: Minimum confidence score filter (default 0.6)
        categories: Optional list of insight categories to include

    Returns:
        List of Insight objects sorted by recency

    Examples:
        # Get last 5 insights
        recent = await get_recent_insights(adapter)

        # Get recent habit insights only
        habit_insights = await get_recent_insights(
            adapter,
            limit=3,
            categories=["habit"]
        )

        # Get high-confidence insights from last 14 days
        insights = await get_recent_insights(
            adapter,
            limit=10,
            days_back=14,
            min_confidence=0.8
        )
    """
    try:
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_back)
        cutoff_iso = cutoff_date.isoformat()

        # Build category filter if specified
        category_clause = ""
        if categories:
            normalized_categories = [
                cat if cat in ["task_completion", "health_correlation", "habit", "trend", "behavioral"]
                else cat.lower()
                for cat in categories
            ]
            category_list = ", ".join([f"'{cat}'" for cat in normalized_categories])
            category_clause = f"AND p.category IN [{category_list}]"

        query = f"""
        MATCH (p:Pattern)
        WHERE p.type = 'insight'
        AND p.strength >= $min_confidence
        AND p.metadata.created_at >= $cutoff_date
        {category_clause}
        RETURN p
        ORDER BY p.metadata.created_at DESC
        LIMIT $limit
        """

        # Execute query via adapter
        result = await adapter.execute_query(
            query,
            parameters={
                "min_confidence": min_confidence,
                "cutoff_date": cutoff_iso,
                "limit": limit
            }
        )

        if not result.success:
            print(f"Warning: Failed to query recent insights: {result.error}")
            return []

        # Parse results into Insight objects
        insights = []
        for record in result.data.get("records", []):
            pattern_node = record.get("p", {})
            insight_obj = _parse_pattern_from_neo4j(pattern_node)
            if isinstance(insight_obj, Insight):
                insights.append(insight_obj)

        return insights

    except Exception as e:
        print(f"Error querying recent insights: {str(e)}")
        return []


async def get_patterns_related_to(
    topic: str,
    adapter: Any,
    limit: int = 10,
    min_confidence: float = 0.5,
    pattern_types: Optional[List[str]] = None
) -> List[Union[TaskCompletionPattern, HealthCorrelation, HabitStreak, Trend, Insight]]:
    """Get patterns related to a specific topic or keywords.

    Searches pattern descriptions and metadata for relevant matches. Useful for
    persona agents to find context about specific areas (e.g., "sleep", "morning
    productivity", "habits").

    Args:
        topic: Topic or keywords to search for (e.g., "sleep", "productivity", "morning")
        adapter: Neo4jAdapter instance
        limit: Maximum number of patterns to return (default 10)
        min_confidence: Minimum confidence score filter (default 0.5)
        pattern_types: Optional list of pattern types to search (default: all types)

    Returns:
        List of pattern model objects sorted by relevance and confidence

    Examples:
        # Find all patterns about sleep
        sleep_patterns = await get_patterns_related_to("sleep", adapter)

        # Find task completion patterns about morning productivity
        morning_patterns = await get_patterns_related_to(
            "morning",
            adapter,
            pattern_types=["task_completion"],
            limit=5
        )

        # Find high-confidence patterns about exercise habits
        exercise = await get_patterns_related_to(
            "exercise",
            adapter,
            min_confidence=0.7,
            pattern_types=["habit", "health_correlation"]
        )
    """
    try:
        # Build search keywords
        keywords = _build_topic_filter(topic)

        # Build pattern type filter if specified
        type_clause = ""
        if pattern_types:
            # Normalize pattern types
            normalized_types = []
            type_map = {
                "task": "task_completion",
                "health": "health_correlation",
                "habit": "habit",
                "trend": "trend",
                "insight": "insight",
            }
            for pt in pattern_types:
                normalized_types.append(type_map.get(pt.lower(), pt.lower()))

            type_list = ", ".join([f"'{t}'" for t in normalized_types])
            type_clause = f"AND p.type IN [{type_list}]"

        # Build keyword search using case-insensitive regex
        keyword_conditions = " OR ".join([
            f"p.description =~ '(?i).*{keyword}.*'"
            for keyword in keywords[:5]  # Limit to top 5 keywords for query performance
        ])

        query = f"""
        MATCH (p:Pattern)
        WHERE ({keyword_conditions})
        AND p.strength >= $min_confidence
        {type_clause}
        RETURN p
        ORDER BY p.strength DESC, p.created_at DESC
        LIMIT $limit
        """

        # Execute query via adapter
        result = await adapter.execute_query(
            query,
            parameters={
                "min_confidence": min_confidence,
                "limit": limit
            }
        )

        if not result.success:
            print(f"Warning: Failed to query patterns by topic: {result.error}")
            return []

        # Parse results into model objects
        patterns = []
        for record in result.data.get("records", []):
            pattern_node = record.get("p", {})
            pattern_obj = _parse_pattern_from_neo4j(pattern_node)
            if pattern_obj:
                patterns.append(pattern_obj)

        return patterns

    except Exception as e:
        print(f"Error querying patterns by topic: {str(e)}")
        return []


async def get_pattern_context_for_persona(
    adapter: Any,
    focus_areas: Optional[List[str]] = None,
    max_patterns: int = 15
) -> Dict[str, Any]:
    """Get a comprehensive pattern context package for persona agents.

    This is a convenience function that gathers multiple types of patterns to
    provide rich context for persona decision-making. It includes recent insights,
    active habits, current trends, and relevant correlations.

    Args:
        adapter: Neo4jAdapter instance
        focus_areas: Optional list of topics to focus on (e.g., ["sleep", "productivity"])
        max_patterns: Maximum total patterns to include (default 15)

    Returns:
        Dictionary with categorized patterns:
        {
            "recent_insights": [Insight, ...],
            "active_habits": [HabitStreak, ...],
            "current_trends": [Trend, ...],
            "key_correlations": [HealthCorrelation, ...],
            "task_patterns": [TaskCompletionPattern, ...],
            "focus_area_patterns": [Pattern, ...] if focus_areas specified
        }

    Examples:
        # Get general pattern context
        context = await get_pattern_context_for_persona(adapter)

        # Get context focused on sleep and productivity
        context = await get_pattern_context_for_persona(
            adapter,
            focus_areas=["sleep", "productivity"]
        )
    """
    context = {
        "recent_insights": [],
        "active_habits": [],
        "current_trends": [],
        "key_correlations": [],
        "task_patterns": [],
        "focus_area_patterns": [],
    }

    try:
        # Get recent insights (top 3-5)
        context["recent_insights"] = await get_recent_insights(
            adapter,
            limit=min(5, max_patterns // 3),
            min_confidence=0.6
        )

        # Get active habit streaks
        habits = await get_patterns_by_category(
            "habit",
            adapter,
            limit=min(5, max_patterns // 5),
            min_confidence=0.5
        )
        context["active_habits"] = [h for h in habits if isinstance(h, HabitStreak) and h.is_active]

        # Get recent trends (improving or declining)
        trends = await get_patterns_by_category(
            "trend",
            adapter,
            limit=min(5, max_patterns // 5),
            min_confidence=0.6
        )
        context["current_trends"] = [
            t for t in trends
            if isinstance(t, Trend) and t.trend_direction in [TrendDirection.IMPROVING, TrendDirection.DECLINING]
        ]

        # Get key health correlations
        context["key_correlations"] = await get_patterns_by_category(
            "health_correlation",
            adapter,
            limit=min(3, max_patterns // 5),
            min_confidence=0.7
        )

        # Get task completion patterns
        context["task_patterns"] = await get_patterns_by_category(
            "task_completion",
            adapter,
            limit=min(3, max_patterns // 5),
            min_confidence=0.7
        )

        # Get focus area specific patterns if requested
        if focus_areas:
            for topic in focus_areas[:3]:  # Limit to 3 focus areas
                topic_patterns = await get_patterns_related_to(
                    topic,
                    adapter,
                    limit=3,
                    min_confidence=0.6
                )
                context["focus_area_patterns"].extend(topic_patterns)

        return context

    except Exception as e:
        print(f"Error building pattern context for persona: {str(e)}")
        return context
