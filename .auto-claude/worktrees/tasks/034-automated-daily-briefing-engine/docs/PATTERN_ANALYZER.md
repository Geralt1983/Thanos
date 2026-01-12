# PatternAnalyzer - Task Completion Pattern Tracking

The PatternAnalyzer module tracks what tasks users complete on different days and times, identifies recurring patterns, and provides intelligent recommendations to improve briefing relevance.

## Overview

**Purpose:** Learn from user behavior to surface the right tasks at the right times

**Key Features:**
- Track task completions by day of week and time of day
- Automatically infer task categories from titles
- Identify recurring patterns (requires 14+ days of data)
- Provide context-based task recommendations
- Store persistent history in State/BriefingPatterns.json
- Automatic data retention (180 days)

**ADHD-Friendly:** Learns your natural rhythms without requiring manual configuration

## Quick Start

```python
from Tools.pattern_analyzer import PatternAnalyzer

# Initialize analyzer
analyzer = PatternAnalyzer()

# Record a task completion
analyzer.record_task_completion(
    task_title="Review PR for authentication",
    task_category="admin"  # optional, will auto-infer if not provided
)

# Get recommendations for current context
recommendations = analyzer.get_recommendations_for_context()
if recommendations["has_recommendations"]:
    for rec in recommendations["recommendations"]:
        print(f"• {rec['reason']} (confidence: {rec['confidence']:.0f}%)")
```

## Core Concepts

### Task Categories

The analyzer recognizes these task categories:

- **deep_work**: Cognitively demanding tasks (design, code, research, architecture)
- **admin**: Administrative tasks (meetings, email, reports, scheduling)
- **personal**: Personal tasks (errands, family, health, home)
- **general**: Everything else

Categories are automatically inferred from task titles using keyword matching.

### Time of Day Periods

- **morning**: 5:00 AM - 11:59 AM
- **afternoon**: 12:00 PM - 4:59 PM
- **evening**: 5:00 PM - 8:59 PM
- **night**: 9:00 PM - 4:59 AM

### Pattern Detection

Requires **minimum 14 days** of task completion data (configurable).

Analyzes:
1. **Day of week patterns**: Which task types you do on which days
2. **Time of day patterns**: When you prefer to do certain tasks
3. **Category distribution**: Overall task type preferences

## API Reference

### Initialization

```python
PatternAnalyzer(state_dir: Optional[str] = None)
```

**Args:**
- `state_dir`: Path to State directory. Defaults to `./State`

**Example:**
```python
# Default location (./State)
analyzer = PatternAnalyzer()

# Custom location
analyzer = PatternAnalyzer(state_dir="/path/to/State")
```

### Recording Task Completions

```python
record_task_completion(
    task_title: str,
    task_category: Optional[str] = None,
    completion_time: Optional[datetime] = None,
    completion_date: Optional[date] = None
) -> bool
```

**Args:**
- `task_title`: Title/description of completed task (required)
- `task_category`: Category (admin/deep_work/personal/general). Auto-inferred if not provided
- `completion_time`: When task was completed. Defaults to now
- `completion_date`: Date of completion. Defaults to today

**Returns:** `True` if recorded successfully, `False` otherwise

**Examples:**
```python
# Basic recording (now, auto-inferred category)
analyzer.record_task_completion("Design API architecture")

# With explicit category
analyzer.record_task_completion(
    "Weekly status meeting",
    task_category="admin"
)

# Historical data (specific date/time)
from datetime import datetime
analyzer.record_task_completion(
    "Implement caching layer",
    task_category="deep_work",
    completion_time=datetime(2026, 1, 10, 9, 30),
    completion_date=date(2026, 1, 10)
)
```

### Retrieving Completions

```python
get_completions(
    days: int = 30,
    category: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Args:**
- `days`: Number of days to look back (default: 30)
- `category`: Filter by category (optional)

**Returns:** List of completion dictionaries

**Example:**
```python
# All recent completions
completions = analyzer.get_completions(days=30)

# Only admin tasks from last 7 days
admin_tasks = analyzer.get_completions(days=7, category="admin")

for completion in completions:
    print(f"{completion['task_title']} - {completion['day_of_week']}")
```

### Identifying Patterns

```python
identify_patterns(min_days: int = 14) -> Dict[str, Any]
```

**Args:**
- `min_days`: Minimum days of data required (default: 14)

**Returns:** Dictionary with pattern analysis

**Response Structure:**
```python
{
    "has_sufficient_data": bool,
    "sample_size": int,  # number of unique days with data
    "total_completions": int,
    "day_of_week_patterns": {
        "Monday": {
            "total_completions": int,
            "category_distribution": {"admin": 60.0, "deep_work": 40.0},
            "dominant_category": "admin",
            "dominant_percentage": 60.0
        },
        # ... other days
    },
    "time_of_day_patterns": {
        "morning": {
            "total_completions": int,
            "category_distribution": {"deep_work": 80.0, "admin": 20.0},
            "dominant_category": "deep_work",
            "dominant_percentage": 80.0
        },
        # ... other time periods
    },
    "category_patterns": {
        "admin": {
            "total_completions": int,
            "percentage_of_total": float,
            "common_days": ["Monday", "Friday"],
            "preferred_time_of_day": "afternoon",
            "preferred_time_percentage": 65.0
        },
        # ... other categories
    },
    "insights": [
        "80% of tasks on Friday are admin (12 completions)",
        "You typically do deep_work tasks in the morning (75%)",
        # ... more insights
    ]
}
```

**Example:**
```python
patterns = analyzer.identify_patterns(min_days=14)

if patterns["has_sufficient_data"]:
    print(f"Analyzed {patterns['sample_size']} days")
    print(f"Total completions: {patterns['total_completions']}")

    print("\nInsights:")
    for insight in patterns["insights"]:
        print(f"  • {insight}")
else:
    print(patterns["message"])  # e.g., "Need at least 14 days of data"
```

### Getting Recommendations

```python
get_recommendations_for_context(
    current_day: Optional[str] = None,
    current_time_of_day: Optional[str] = None
) -> Dict[str, Any]
```

**Args:**
- `current_day`: Day of week (e.g., "Monday"). Defaults to today
- `current_time_of_day`: Time period (morning/afternoon/evening/night). Defaults to current time

**Returns:** Dictionary with recommendations

**Response Structure:**
```python
{
    "has_recommendations": bool,
    "current_context": {
        "day": "Friday",
        "time_of_day": "afternoon"
    },
    "recommendations": [
        {
            "type": "day_pattern",  # or "time_pattern"
            "category": "admin",
            "reason": "You typically complete admin tasks on Friday",
            "confidence": 75.0  # percentage
        }
    ]
}
```

**Example:**
```python
# Get recommendations for current context
recommendations = analyzer.get_recommendations_for_context()

if recommendations["has_recommendations"]:
    print(f"Context: {recommendations['current_context']['day']}, "
          f"{recommendations['current_context']['time_of_day']}")

    for rec in recommendations["recommendations"]:
        print(f"\n• Suggestion: Focus on {rec['category']} tasks")
        print(f"  Reason: {rec['reason']}")
        print(f"  Confidence: {rec['confidence']:.0f}%")

# Get recommendations for specific context
recommendations = analyzer.get_recommendations_for_context(
    current_day="Friday",
    current_time_of_day="afternoon"
)
```

## Data Storage

### Location

Data stored in: `State/BriefingPatterns.json`

### Structure

```json
{
  "task_completions": [
    {
      "task_title": "Review PR for authentication",
      "task_category": "admin",
      "completion_date": "2026-01-11",
      "completion_time": "14:30",
      "day_of_week": "Saturday",
      "hour": 14,
      "time_of_day": "afternoon",
      "recorded_at": "2026-01-11T14:30:00.000000"
    }
  ],
  "metadata": {
    "created_at": "2026-01-11T00:00:00.000000",
    "last_updated": "2026-01-11T14:30:00.000000",
    "version": "1.0"
  }
}
```

### Data Retention

- Automatically keeps last **180 days** of data (6 months)
- Older data is automatically removed when new data is added
- Sorted by date (most recent first)

## Category Inference

The analyzer automatically infers task categories from titles using keyword matching:

### Deep Work Keywords
```
design, architect, research, implement, build, develop,
code, write, create, analyze, plan, refactor, optimize
```

### Admin Keywords
```
email, meeting, standup, status, report, timesheet,
expense, submit, review, respond, schedule, calendar,
update, fill, send
```

### Personal Keywords
```
call, personal, home, family, health, appointment,
grocery, shopping, errands, pay, bills
```

**Examples:**
- "Design new API architecture" → `deep_work`
- "Send weekly status report" → `admin`
- "Pay utility bills" → `personal`
- "Something random" → `general`

## Pattern Detection Algorithm

### Requirements

- **Minimum 14 days** of unique task completion data (configurable via `min_days` parameter)
- Data from last 90 days is analyzed

### Day of Week Analysis

1. Groups completions by day of week and category
2. Calculates percentage distribution for each day
3. Identifies dominant category if >40% of completions
4. Reports total completions per day

**Example Output:**
```
Friday: 15 completions
  → Dominant: admin (73%)
```

### Time of Day Analysis

1. Groups completions by time period and category
2. Calculates percentage distribution for each period
3. Identifies dominant category if >40% of completions
4. Reports total completions per period

**Example Output:**
```
morning: 20 completions
  → Dominant: deep_work (80%)
```

### Category Analysis

1. Analyzes overall category distribution
2. Identifies preferred time of day for each category
3. Lists common days for each category
4. Calculates percentage of total completions

**Example Output:**
```
admin: 30 completions (35% of total)
  → Preferred time: afternoon (65%)
  → Common days: Monday, Friday
```

### Insight Generation

Automatically generates human-readable insights when:

- **Day pattern:** >50% of tasks on a specific day are one category
- **Time pattern:** >50% of tasks in a time period are one category
- **Category dominance:** Category represents >30% of all completions
- **Time preference:** >50% of category completions happen at one time

## Integration with BriefingEngine

The PatternAnalyzer is designed to integrate with the BriefingEngine for intelligent task recommendations:

```python
from Tools.pattern_analyzer import PatternAnalyzer
from Tools.briefing_engine import BriefingEngine

# Initialize both
analyzer = PatternAnalyzer()
engine = BriefingEngine()

# Get current patterns
patterns = analyzer.identify_patterns()

if patterns["has_sufficient_data"]:
    # Get context-based recommendations
    recommendations = analyzer.get_recommendations_for_context()

    if recommendations["has_recommendations"]:
        # Use recommendations to influence priority ranking
        for rec in recommendations["recommendations"]:
            print(f"Suggest {rec['category']} tasks ({rec['confidence']:.0f}% confidence)")
            print(f"Reason: {rec['reason']}")
```

See subtask 6.2 for full integration with priority ranking.

## Best Practices

### Recording Completions

1. **Record promptly:** Record tasks when you complete them for accurate time tracking
2. **Be consistent:** Try to record most task completions to build reliable patterns
3. **Use clear titles:** Descriptive titles help with automatic category inference
4. **Manual categories:** Override auto-inference when needed for accuracy

### Pattern Detection

1. **Wait for sufficient data:** Patterns require 14+ days of data
2. **Review insights:** Read generated insights to understand your patterns
3. **Consider confidence:** Higher confidence recommendations are more reliable
4. **Account for changes:** Life patterns change; recent data is weighted

### Recommendations

1. **Use as guidance:** Recommendations influence, not dictate
2. **Context matters:** Different contexts may have different patterns
3. **Override when needed:** You know your schedule best
4. **Track exceptions:** Some days may not follow patterns

## Troubleshooting

### "Need at least 14 days of data"

**Problem:** Not enough historical data for pattern detection

**Solutions:**
- Continue recording task completions daily
- Lower `min_days` parameter (not recommended below 7)
- Manually create historical data for testing

**Example:**
```python
# Lower threshold for testing (use with caution)
patterns = analyzer.identify_patterns(min_days=7)
```

### Inaccurate Category Inference

**Problem:** Tasks are being categorized incorrectly

**Solutions:**
- Provide explicit `task_category` parameter
- Use more descriptive task titles with relevant keywords
- Review keyword lists in source code

**Example:**
```python
# Override auto-inference
analyzer.record_task_completion(
    "Team sync",
    task_category="admin"  # explicitly set
)
```

### No Recommendations Available

**Problem:** `has_recommendations` is False despite sufficient data

**Reasons:**
- No dominant patterns found (no category >40% in any context)
- Data is evenly distributed across categories
- Not enough data in specific day/time context

**Solutions:**
- Continue recording data to strengthen patterns
- Check `insights` in `identify_patterns()` output
- Review raw pattern percentages

### Data File Issues

**Problem:** Error loading or saving BriefingPatterns.json

**Solutions:**
- Check file permissions on State/BriefingPatterns.json
- Verify JSON syntax if manually edited
- Delete file to reset (will lose historical data)

**Recovery:**
```python
# PatternAnalyzer will create new file automatically
analyzer = PatternAnalyzer()
# Start fresh
```

## Performance Considerations

### Data Volume

- **Storage:** ~1KB per task completion
- **180 days × 10 tasks/day:** ~1.8MB (typical use)
- **Memory:** Entire dataset loaded into memory
- **Lookup:** O(n) for filtering, O(n log n) for sorting

### Optimization Tips

1. **Data retention:** Automatic cleanup at 180 days
2. **Batch operations:** Record multiple tasks, then analyze patterns
3. **Cache patterns:** Pattern detection is expensive, cache results
4. **Filter early:** Use category filter in `get_completions()` when possible

## Examples

See `example_pattern_analyzer.py` for comprehensive examples:

1. **Basic Usage** - Recording task completions
2. **Category Inference** - Automatic categorization
3. **Historical Data** - Creating past data with patterns
4. **Retrieving Completions** - Querying history
5. **Pattern Identification** - Analyzing patterns
6. **Recommendations** - Context-based suggestions
7. **Data Persistence** - Cross-session data storage

Run examples:
```bash
python3 example_pattern_analyzer.py
```

## Testing

Run unit tests:
```bash
python3 -m pytest tests/unit/test_pattern_analyzer.py -v
```

**Test Coverage:**
- 20 comprehensive unit tests
- 100% code coverage of core functionality
- Edge cases and error handling
- Pattern detection algorithms
- Data persistence

## Future Enhancements (Subtask 6.2+)

- Integration with BriefingEngine for priority ranking
- Pattern influence on task recommendations
- Adaptive briefing based on activity levels
- Weekly pattern summaries
- Machine learning for better predictions

## Related Documentation

- [BriefingEngine](./BRIEFING_ENGINE.md) - Core briefing generation
- [HealthStateTracker](./HEALTH_STATE_TRACKER.md) - Energy and health tracking
- [Priority Ranking](./PRIORITY_RANKING.md) - Task priority algorithms

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review example scripts
3. Examine test cases for usage patterns
4. Verify State/BriefingPatterns.json structure
