# Pattern Queries - Persona Agent Access to Patterns

This module provides query methods for persona agents to access stored patterns from the Neo4j knowledge graph. Patterns can be filtered by category, recency, topic, or confidence level.

## Overview

After patterns are analyzed and stored in Neo4j (via `pattern_storage.py`), persona agents need to query and access these patterns for context-aware decision-making. The `pattern_queries.py` module provides four main query functions:

1. **get_patterns_by_category()** - Query patterns by type
2. **get_recent_insights()** - Get latest insights
3. **get_patterns_related_to()** - Find patterns about specific topics
4. **get_pattern_context_for_persona()** - Comprehensive context package

## Installation

```python
from Tools.pattern_recognition.pattern_queries import (
    get_patterns_by_category,
    get_recent_insights,
    get_patterns_related_to,
    get_pattern_context_for_persona,
)
```

## Query Functions

### 1. get_patterns_by_category()

Query patterns filtered by category (task_completion, health_correlation, habit, trend, insight).

**Signature:**
```python
async def get_patterns_by_category(
    category: str,
    adapter: Any,
    limit: Optional[int] = None,
    min_confidence: float = 0.0,
    include_metadata: bool = True
) -> List[Union[TaskCompletionPattern, HealthCorrelation, HabitStreak, Trend, Insight]]
```

**Parameters:**
- `category`: Pattern category - accepts "task", "health", "habit", "trend", "insight"
- `adapter`: Neo4jAdapter instance for database access
- `limit`: Maximum patterns to return (None = all)
- `min_confidence`: Minimum confidence score filter (0.0 to 1.0)
- `include_metadata`: Include full metadata in results

**Examples:**

```python
# Get all habit patterns
habits = await get_patterns_by_category("habit", adapter)
for habit in habits:
    if habit.is_active:
        print(f"Active: {habit.habit_name} - {habit.streak_length} days")

# Get high-confidence task patterns
task_patterns = await get_patterns_by_category(
    "task_completion",
    adapter,
    min_confidence=0.7,
    limit=10
)

# Get health correlations
health = await get_patterns_by_category("health", adapter, min_confidence=0.6)
```

**Returns:** List of pattern model objects (TaskCompletionPattern, HealthCorrelation, HabitStreak, Trend, or Insight)

---

### 2. get_recent_insights()

Get recent insights, optionally filtered by category and date range.

**Signature:**
```python
async def get_recent_insights(
    adapter: Any,
    limit: int = 5,
    days_back: int = 7,
    min_confidence: float = 0.6,
    categories: Optional[List[str]] = None
) -> List[Insight]
```

**Parameters:**
- `adapter`: Neo4jAdapter instance
- `limit`: Maximum insights to return (default: 5)
- `days_back`: How many days back to search (default: 7)
- `min_confidence`: Minimum confidence filter (default: 0.6)
- `categories`: Optional category filter list

**Examples:**

```python
# Get last 5 insights
recent = await get_recent_insights(adapter)
for insight in recent:
    print(f"💡 {insight.summary}")
    print(f"   Action: {insight.suggested_action}")
    print(f"   Confidence: {insight.confidence_score:.0%}")

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
```

**Returns:** List of Insight objects sorted by recency

---

### 3. get_patterns_related_to()

Find patterns related to specific topics using keyword search.

**Signature:**
```python
async def get_patterns_related_to(
    topic: str,
    adapter: Any,
    limit: int = 10,
    min_confidence: float = 0.5,
    pattern_types: Optional[List[str]] = None
) -> List[Union[TaskCompletionPattern, HealthCorrelation, HabitStreak, Trend, Insight]]
```

**Parameters:**
- `topic`: Topic or keywords to search (e.g., "sleep", "morning", "productivity")
- `adapter`: Neo4jAdapter instance
- `limit`: Maximum patterns to return (default: 10)
- `min_confidence`: Minimum confidence filter (default: 0.5)
- `pattern_types`: Optional type filter list

**Topic Expansion:**
The function automatically expands common topics:
- "sleep" → ["sleep", "rest", "bedtime", "wake", "readiness", "tired"]
- "productivity" → ["productivity", "tasks", "completion", "work", "focus"]
- "morning" → ["morning", "am", "wake", "start", "early"]
- "energy" → ["energy", "readiness", "vitality", "fatigue"]
- "habit" → ["habit", "streak", "consistency", "routine", "daily"]

**Examples:**

```python
# Find all patterns about sleep
sleep_patterns = await get_patterns_related_to("sleep", adapter)
for pattern in sleep_patterns:
    print(pattern.description if hasattr(pattern, 'description') else pattern.summary)

# Find task completion patterns about morning productivity
morning_patterns = await get_patterns_related_to(
    "morning",
    adapter,
    pattern_types=["task_completion"],
    limit=5
)

# Find high-confidence patterns about exercise
exercise = await get_patterns_related_to(
    "exercise",
    adapter,
    min_confidence=0.7,
    pattern_types=["habit", "health_correlation"]
)
```

**Returns:** List of pattern model objects sorted by relevance and confidence

---

### 4. get_pattern_context_for_persona()

Get a comprehensive pattern context package for persona agents. This convenience function gathers multiple pattern types to provide rich context for decision-making.

**Signature:**
```python
async def get_pattern_context_for_persona(
    adapter: Any,
    focus_areas: Optional[List[str]] = None,
    max_patterns: int = 15
) -> Dict[str, Any]
```

**Parameters:**
- `adapter`: Neo4jAdapter instance
- `focus_areas`: Optional topics to focus on (e.g., ["sleep", "productivity"])
- `max_patterns`: Maximum total patterns to include (default: 15)

**Returns:** Dictionary with categorized patterns:
```python
{
    "recent_insights": [Insight, ...],           # Top 3-5 recent insights
    "active_habits": [HabitStreak, ...],         # Currently active habits
    "current_trends": [Trend, ...],              # Improving/declining trends
    "key_correlations": [HealthCorrelation, ...],# Health-productivity links
    "task_patterns": [TaskCompletionPattern, ...],# Task completion patterns
    "focus_area_patterns": [Pattern, ...]        # Topic-specific patterns (if focus_areas set)
}
```

**Examples:**

```python
# Get general pattern context
context = await get_pattern_context_for_persona(adapter)

# Display insights
for insight in context["recent_insights"]:
    print(f"💡 {insight.summary}")

# Display active habits
for habit in context["active_habits"]:
    print(f"🔄 {habit.habit_name}: {habit.streak_length} day streak")

# Display trends
for trend in context["current_trends"]:
    direction = "📈" if trend.trend_direction == "improving" else "📉"
    print(f"{direction} {trend.trend_description}")

# Get context focused on specific areas
context = await get_pattern_context_for_persona(
    adapter,
    focus_areas=["sleep", "productivity"]
)

# Access focus area patterns
for pattern in context["focus_area_patterns"]:
    # Handle different pattern types
    if isinstance(pattern, Insight):
        print(f"💡 {pattern.summary}")
    elif isinstance(pattern, HabitStreak):
        print(f"🔄 {pattern.habit_name}")
    # ... etc
```

## Integration with Persona Agents

Persona agents can use these query methods to access patterns for context-aware decision-making:

### Example: Daily Briefing Persona

```python
async def generate_daily_briefing(adapter, neo4j_adapter):
    """Generate personalized daily briefing using pattern context."""

    # Get comprehensive pattern context
    context = await get_pattern_context_for_persona(
        neo4j_adapter,
        focus_areas=["sleep", "morning", "productivity"]
    )

    # Use insights for recommendations
    if context["recent_insights"]:
        print("\n📊 Pattern Insights:")
        for insight in context["recent_insights"][:3]:
            print(f"  • {insight.summary}")
            print(f"    → {insight.suggested_action}")

    # Use habit context
    if context["active_habits"]:
        print("\n✅ Active Habits:")
        for habit in context["active_habits"]:
            print(f"  • {habit.habit_name}: {habit.streak_length} days")

    # Use trends for forward-looking advice
    declining_trends = [
        t for t in context["current_trends"]
        if t.trend_direction == "declining"
    ]
    if declining_trends:
        print("\n⚠️  Areas Needing Attention:")
        for trend in declining_trends:
            print(f"  • {trend.trend_description}")
```

### Example: Weekly Review Persona

```python
async def enhance_weekly_review_with_patterns(adapter, neo4j_adapter):
    """Enhance weekly review with stored patterns."""

    # Get recent insights (last 7 days)
    insights = await get_recent_insights(neo4j_adapter, limit=10, days_back=7)

    # Get all trends
    trends = await get_patterns_by_category("trend", neo4j_adapter, limit=10)

    # Get sleep-related patterns
    sleep_patterns = await get_patterns_related_to(
        "sleep",
        neo4j_adapter,
        pattern_types=["health_correlation"]
    )

    # Build comprehensive review
    return {
        "insights": insights,
        "trends": trends,
        "sleep_analysis": sleep_patterns
    }
```

### Example: Task Prioritization Persona

```python
async def get_optimal_task_timing(adapter, neo4j_adapter):
    """Determine optimal times for different task types."""

    # Get task completion patterns
    task_patterns = await get_patterns_by_category(
        "task_completion",
        neo4j_adapter,
        min_confidence=0.7
    )

    # Filter for hourly patterns
    hourly_patterns = [
        p for p in task_patterns
        if p.pattern_type == PatternType.HOURLY
    ]

    # Find peak productivity windows
    peak_hours = []
    for pattern in hourly_patterns:
        if pattern.completion_rate > 0.8:  # 80%+ completion rate
            peak_hours.append({
                "time": pattern.time_period,
                "rate": pattern.completion_rate,
                "confidence": pattern.confidence_score
            })

    return sorted(peak_hours, key=lambda x: x["rate"], reverse=True)
```

## Error Handling

All query functions include graceful error handling:

```python
try:
    patterns = await get_patterns_by_category("habit", adapter)
except Exception as e:
    print(f"Error querying patterns: {e}")
    patterns = []  # Graceful degradation
```

If a query fails:
1. Error is logged to console
2. Empty list or dictionary is returned
3. Application continues normally (no crash)

## Performance Considerations

1. **Use Limits**: Always specify `limit` parameter for large result sets
2. **Filter by Confidence**: Use `min_confidence` to get only quality patterns
3. **Narrow Pattern Types**: Specify `pattern_types` or `categories` to reduce query scope
4. **Cache Results**: Consider caching pattern context for multiple operations

```python
# Good: Limited, filtered query
patterns = await get_patterns_by_category(
    "habit",
    adapter,
    limit=10,
    min_confidence=0.7
)

# Better: Use comprehensive context function (optimized)
context = await get_pattern_context_for_persona(
    adapter,
    max_patterns=15  # Automatically distributes across categories
)
```

## Neo4j Query Format

The query functions generate Cypher queries like:

```cypher
# Get patterns by category
MATCH (p:Pattern)
WHERE p.category = 'habit' OR p.type = 'habit'
AND p.strength >= 0.7
RETURN p
ORDER BY p.strength DESC, p.created_at DESC
LIMIT 10

# Get recent insights
MATCH (p:Pattern)
WHERE p.type = 'insight'
AND p.strength >= 0.6
AND p.metadata.created_at >= '2024-01-01T00:00:00'
RETURN p
ORDER BY p.metadata.created_at DESC
LIMIT 5

# Get patterns related to topic
MATCH (p:Pattern)
WHERE (p.description =~ '(?i).*sleep.*' OR p.description =~ '(?i).*rest.*')
AND p.strength >= 0.5
RETURN p
ORDER BY p.strength DESC
LIMIT 10
```

## See Also

- `pattern_storage.py` - Store patterns in Neo4j
- `insight_generator.py` - Generate insights from patterns
- `weekly_review_formatter.py` - Format patterns for display
- `PATTERN_STORAGE_README.md` - Pattern storage documentation
