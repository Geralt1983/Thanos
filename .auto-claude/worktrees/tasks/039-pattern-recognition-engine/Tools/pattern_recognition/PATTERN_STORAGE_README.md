# Pattern Storage - Neo4j Knowledge Graph Integration

This module provides integration between the Pattern Recognition Engine and the Neo4j knowledge graph, allowing detected patterns to be stored, linked, and tracked over time.

## Overview

The pattern storage module uses the existing `neo4j_adapter._record_pattern()` method to store:
- **Detected patterns** with confidence scores
- **Pattern categories** (task_completion, health_correlation, habit, trend)
- **Relationships between patterns** (e.g., Pattern A supports Pattern B)
- **Historical pattern evolution** (track how patterns change over time)

## Pattern Types Supported

### 1. Task Completion Patterns
Patterns identified from task completion analysis (hourly, daily, weekly, task-type).

```python
from Tools.pattern_recognition import store_task_pattern, TaskCompletionPattern

# After detecting a pattern
pattern = TaskCompletionPattern(
    pattern_type=PatternType.HOURLY,
    description="Most productive during morning hours",
    time_period="9-11am",
    completion_rate=0.82,
    sample_size=45,
    confidence_score=0.87,
    date_range_start=start_date,
    date_range_end=end_date,
    evidence=["Completed 37/45 tasks during 9-11am window", ...]
)

# Store in Neo4j
result = await store_task_pattern(pattern, neo4j_adapter)
pattern_id = result["pattern_id"]
```

### 2. Health Correlations
Correlations between health metrics (sleep, readiness) and productivity.

```python
from Tools.pattern_recognition import store_health_correlation, HealthCorrelation

correlation = HealthCorrelation(
    health_metric="sleep_duration",
    productivity_metric="tasks_completed",
    correlation_strength=0.68,
    correlation_description="7+ hours sleep correlates with 40% more tasks",
    threshold_value=7.0,
    effect_size=0.40,
    confidence_score=0.75,
    sample_size=60,
    date_range_start=start_date,
    date_range_end=end_date,
    evidence=[...]
)

result = await store_health_correlation(correlation, neo4j_adapter)
```

### 3. Habit Streaks
Habit tracking with streak information and break pattern analysis.

```python
from Tools.pattern_recognition import store_habit_streak, HabitStreak

streak = HabitStreak(
    habit_name="daily_review",
    streak_length=45,
    is_active=True,
    last_completion_date=datetime.now(),
    consistency_score=0.93,
    longest_streak=52,
    total_completions=180,
    confidence_score=0.89,
    break_reasons=["Fridays", "high task load"],
    date_range_start=start_date,
    date_range_end=end_date,
    evidence=[...]
)

result = await store_habit_streak(streak, neo4j_adapter)
```

### 4. Trends
Detected trends in metrics over time (improving, declining, plateau, volatile).

```python
from Tools.pattern_recognition import store_trend, Trend

trend = Trend(
    metric_name="tasks_per_day",
    trend_direction=TrendDirection.IMPROVING,
    trend_description="Tasks per day increasing consistently",
    start_value=7.2,
    end_value=9.4,
    change_percentage=30.6,
    trend_strength=0.84,
    momentum_indicator="30-day",
    confidence_score=0.81,
    sample_size=30,
    date_range_start=start_date,
    date_range_end=end_date,
    evidence=[...]
)

result = await store_trend(trend, neo4j_adapter)
```

### 5. Insights
Actionable insights derived from patterns with multi-factor scoring.

```python
from Tools.pattern_recognition import store_insight, Insight

insight = Insight(
    summary="Schedule deep work in mornings for 40% higher productivity",
    category=InsightCategory.TASK_COMPLETION,
    detailed_description="Analysis shows 9-11am has highest completion rates",
    suggested_action="Block 9-11am daily for important deep work tasks",
    actionability_score=0.85,
    impact_score=0.75,
    confidence_score=0.87,
    significance_score=0.82,
    recency_score=0.90,
    novelty_score=0.70,
    supporting_evidence=[...],
    source_patterns=["pattern_task_completion_abc123"],
    date_range_start=start_date,
    date_range_end=end_date
)

result = await store_insight(insight, neo4j_adapter)
```

## Pattern Relationships

### Linking Patterns

Create relationships between patterns to show how they support or relate to each other:

```python
from Tools.pattern_recognition import link_patterns

# Pattern A supports Pattern B
result = await link_patterns(
    from_pattern_id="pattern_task_completion_abc123",
    to_pattern_id="pattern_trend_xyz789",
    relationship="SUPPORTS",
    adapter=neo4j_adapter,
    properties={"relationship_strength": 0.85}
)

# Pattern evidences Insight
result = await link_patterns(
    from_pattern_id="pattern_health_correlation_def456",
    to_pattern_id="pattern_insight_ghi789",
    relationship="EVIDENCES",
    adapter=neo4j_adapter
)
```

**Supported Relationship Types:**
- `SUPPORTS` - Pattern A supports/reinforces Pattern B
- `CONTRADICTS` - Pattern A contradicts Pattern B
- `EVOLVES_INTO` - Pattern A evolved into Pattern B (historical tracking)
- `EVIDENCES` - Pattern provides evidence for an Insight

### Tracking Pattern Evolution

Track how patterns change over time:

```python
from Tools.pattern_recognition import track_pattern_evolution

# Pattern changed - create new version and link to old
old_pattern_id = "pattern_task_completion_old123"
new_pattern_id = "pattern_task_completion_new456"

result = await track_pattern_evolution(
    old_pattern_id=old_pattern_id,
    new_pattern_id=new_pattern_id,
    adapter=neo4j_adapter,
    change_description="Productivity window shifted from 9-11am to 10am-12pm"
)
```

This creates an `EVOLVES_INTO` relationship with metadata:
- `evolution_date`: When the pattern evolved
- `change_description`: What changed

## Batch Operations

Store all detected patterns atomically in a single transaction:

```python
from Tools.pattern_recognition import store_all_patterns

patterns_dict = {
    "task_patterns": [pattern1, pattern2, ...],
    "health_correlations": [correlation1, correlation2, ...],
    "habit_streaks": [streak1, streak2, ...],
    "trends": [trend1, trend2, ...],
    "insights": [insight1, insight2, ...]
}

# Store all patterns atomically
results = await store_all_patterns(
    patterns_dict=patterns_dict,
    adapter=neo4j_adapter,
    atomic=True,  # All-or-nothing transaction
    create_relationships=True  # Auto-create pattern->insight relationships
)

# Check results
print(f"Stored {results['statistics']['successful_patterns']} patterns")
print(f"Failed {results['statistics']['failed_patterns']} patterns")
print(f"Errors: {results['errors']}")
```

**Results Structure:**
```python
{
    "task_patterns": [{"pattern_id": "...", "success": True}, ...],
    "health_correlations": [...],
    "habit_streaks": [...],
    "trends": [...],
    "insights": [...],
    "relationships": [...],
    "errors": [...],
    "statistics": {
        "total_patterns": 15,
        "successful_patterns": 14,
        "failed_patterns": 1,
        "total_relationships": 8,
        "successful_relationships": 8
    }
}
```

## Session Reuse for Performance

Use session reuse for better performance when storing multiple patterns:

```python
# Without session reuse (each operation creates new session)
for pattern in patterns:
    await store_task_pattern(pattern, adapter)

# With session reuse (75-95% fewer sessions)
async with adapter.session_context() as session:
    for pattern in patterns:
        await store_task_pattern(pattern, adapter, session=session)

# With atomic transaction (all-or-nothing)
async with adapter.session_context(batch_transaction=True) as session:
    for pattern in patterns:
        await store_task_pattern(pattern, adapter, session=session)
    # All patterns committed together or rolled back on error
```

## Pattern Metadata

All stored patterns include rich metadata in Neo4j:

### Neo4j Node Properties
- `id`: Unique pattern ID (e.g., `pattern_task_completion_abc123`)
- `description`: Human-readable pattern description with evidence
- `type`: Pattern type (`task_completion`, `health_correlation`, `habit`, `trend`, `insight`)
- `domain`: Domain category (`work`, `personal`, `health`, `relationship`)
- `frequency`: Frequency indicator (`daily`, `weekly`, `hourly`, etc.)
- `strength`: Confidence score (0.0-1.0)
- `category`: Pattern category for filtering
- `first_observed`: When pattern was first detected
- `last_observed`: When pattern was last observed/updated
- `metadata`: JSON object with detailed metrics and evidence

### Category Values
- `task_completion` - Task completion patterns
- `health_correlation` - Health-productivity correlations
- `habit` - Habit streaks and consistency
- `trend` - Trends over time
- `behavioral` - General behavioral patterns

## Querying Stored Patterns

Patterns are stored as `Pattern` nodes in Neo4j and can be queried:

```cypher
-- Get all patterns by category
MATCH (p:Pattern {category: 'task_completion'})
RETURN p
ORDER BY p.strength DESC

-- Get patterns with high confidence
MATCH (p:Pattern)
WHERE p.strength >= 0.8
RETURN p
ORDER BY p.last_observed DESC

-- Find pattern evolution chains
MATCH path = (old:Pattern)-[:LEADS_TO*]->(new:Pattern)
WHERE ALL(rel IN relationships(path) WHERE rel.pattern_relationship = 'EVOLVES_INTO')
RETURN path

-- Find insights with supporting patterns
MATCH (pattern:Pattern)-[r:LEADS_TO]->(insight:Pattern {type: 'insight'})
WHERE r.pattern_relationship = 'EVIDENCES'
RETURN pattern, insight
```

## Integration with Weekly Review

Patterns are automatically stored during weekly review generation:

```python
# In commands/pa/weekly.py
from Tools.pattern_recognition import (
    run_pattern_recognition,
    store_all_patterns
)

# Analyze patterns
patterns = await run_pattern_recognition(days=30)

# Store in Neo4j
results = await store_all_patterns(
    patterns_dict={
        "task_patterns": patterns["task_patterns"],
        "health_correlations": patterns["health_correlations"],
        "habit_streaks": patterns["habit_streaks"],
        "trends": patterns["trends"],
        "insights": patterns["insights"]
    },
    adapter=neo4j_adapter,
    atomic=True
)
```

## Error Handling

All storage functions include graceful error handling:

```python
result = await store_task_pattern(pattern, adapter)

if result["success"]:
    print(f"Stored pattern: {result['pattern_id']}")
else:
    print(f"Failed to store pattern: {result['error']}")
```

Batch operations support partial success (non-atomic mode):

```python
# Non-atomic: Continue on individual failures
results = await store_all_patterns(
    patterns_dict=patterns,
    adapter=neo4j_adapter,
    atomic=False  # Don't rollback entire batch on single failure
)

# Check individual errors
for error in results["errors"]:
    print(f"Error: {error}")
```

## Architecture Notes

### Neo4j Schema Integration

The pattern storage module integrates with the existing Neo4j schema:

- **Node Type**: `Pattern` (existing node type in schema)
- **Properties**: Follows existing pattern node structure
- **Relationships**: Uses `LEADS_TO` relationship type with `pattern_relationship` property for semantic meaning

### Pattern ID Format

Pattern IDs follow the format: `pattern_{category}_{uuid8}`

Examples:
- `pattern_task_completion_a7b3c9f2`
- `pattern_health_correlation_d4e8f1a6`
- `pattern_habit_9c2b5e7a`
- `pattern_trend_f3a9c7d2`

### Backwards Compatibility

The module uses the existing `neo4j_adapter._record_pattern()` method, ensuring:
- No changes to Neo4j schema required
- Compatible with existing pattern queries
- Seamless integration with other adapters

## Future Enhancements

Potential future improvements:

1. **Pattern Deduplication**: Detect and merge similar patterns
2. **Pattern Decay**: Auto-decrease strength of old patterns
3. **Pattern Recommendations**: Suggest new patterns to track based on data
4. **Pattern Dashboards**: Visualize pattern networks
5. **Pattern Alerts**: Notify when patterns change significantly
