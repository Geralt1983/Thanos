# HealthStateTracker Documentation

## Overview

The `HealthStateTracker` module provides comprehensive tracking and analysis of daily health metrics including energy levels, sleep hours, and medication timing (specifically Vyvanse for ADHD management). It helps users optimize their task scheduling by identifying patterns and providing intelligent recommendations based on historical data.

## Features

- **Daily Health Logging**: Track energy (1-10), sleep hours, and medication timing
- **Historical Analysis**: Calculate 7-day averages and trends
- **Pattern Detection**: Identify day-of-week patterns and correlations
- **Intelligent Recommendations**: Get task recommendations based on current energy state
- **Medication Timing**: Track and optimize Vyvanse timing for peak performance
- **Persistent Storage**: All data stored in `State/HealthLog.json`

## Quick Start

```python
from Tools.health_state_tracker import HealthStateTracker

# Initialize tracker
tracker = HealthStateTracker()

# Log today's health state
tracker.log_entry(
    energy_level=7,
    sleep_hours=8.0,
    vyvanse_time="08:30",
    notes="Feeling productive"
)

# Get current assessment with recommendations
assessment = tracker.get_current_state_assessment()
print(assessment['recommendations'])
```

## API Reference

### HealthStateTracker Class

#### `__init__(state_dir: Optional[str] = None)`

Initialize the tracker.

**Args:**
- `state_dir`: Path to State directory (defaults to `./State`)

#### `log_entry(energy_level, sleep_hours, vyvanse_time=None, entry_date=None, notes=None) -> bool`

Log a health state entry.

**Args:**
- `energy_level` (int): Energy level from 1 (exhausted) to 10 (peak energy)
- `sleep_hours` (float): Hours of sleep (e.g., 7.5)
- `vyvanse_time` (str, optional): Time medication taken in HH:MM format (e.g., "08:30")
- `entry_date` (date, optional): Date for this entry (defaults to today)
- `notes` (str, optional): Optional notes about the day

**Returns:**
- `bool`: True if successful, False otherwise

**Example:**
```python
tracker.log_entry(
    energy_level=8,
    sleep_hours=8.5,
    vyvanse_time="08:00",
    notes="Great sleep, ready for deep work"
)
```

#### `get_entry(entry_date: Optional[date] = None) -> Optional[Dict]`

Get health entry for a specific date.

**Args:**
- `entry_date`: Date to retrieve (defaults to today)

**Returns:**
- Entry dictionary if found, None otherwise

**Example:**
```python
today = tracker.get_entry()
if today:
    print(f"Energy: {today['energy_level']}/10")
```

#### `get_recent_entries(days: int = 7) -> List[Dict]`

Get entries from the last N days.

**Args:**
- `days`: Number of days to look back (default: 7)

**Returns:**
- List of entries sorted by date (most recent first)

#### `calculate_averages(days: int = 7) -> Dict`

Calculate averages for health metrics.

**Args:**
- `days`: Number of days to calculate over (default: 7)

**Returns:**
- Dictionary with `avg_energy_level`, `avg_sleep_hours`, and `sample_size`

**Example:**
```python
averages = tracker.calculate_averages(days=7)
print(f"7-day avg energy: {averages['avg_energy_level']}/10")
```

#### `identify_patterns(min_days: int = 14) -> Dict`

Identify patterns in health data.

**Args:**
- `min_days`: Minimum days of data required (default: 14)

**Returns:**
- Dictionary with pattern analysis including:
  - `has_sufficient_data`: Whether enough data exists
  - `day_of_week_patterns`: Average metrics by day
  - `best_energy_day`: Day with highest average energy
  - `worst_energy_day`: Day with lowest average energy
  - `sleep_energy_correlation`: Correlation analysis
  - `vyvanse_timing`: Medication timing analysis
  - `insights`: List of human-readable insights

**Example:**
```python
patterns = tracker.identify_patterns()
if patterns['has_sufficient_data']:
    print(f"Your worst energy day is typically {patterns['worst_energy_day']}")
    for insight in patterns['insights']:
        print(f"• {insight}")
```

#### `get_current_state_assessment() -> Dict`

Get current health state assessment with recommendations.

**Returns:**
- Dictionary with current state and task recommendations

**Example:**
```python
assessment = tracker.get_current_state_assessment()
print(f"Current energy: {assessment['current_energy']}/10")
for rec in assessment['recommendations']:
    print(f"• {rec}")
```

## Data Structure

### HealthLog.json Format

```json
{
  "entries": [
    {
      "date": "2026-01-11",
      "day_of_week": "Saturday",
      "energy_level": 7,
      "sleep_hours": 8.0,
      "vyvanse_time": "08:30",
      "notes": "Feeling productive",
      "logged_at": "2026-01-11T09:15:00"
    }
  ],
  "metadata": {
    "created_at": "2026-01-11T00:00:00",
    "last_updated": "2026-01-11T09:15:00",
    "version": "1.0"
  }
}
```

## Energy Level Guide

| Level | Description | Recommended Tasks |
|-------|-------------|-------------------|
| 9-10 | Peak energy | Deep work, complex problem solving, creative work |
| 7-8 | High energy | Most tasks, important meetings, challenging work |
| 5-6 | Moderate energy | Routine tasks, collaboration, lighter work |
| 3-4 | Low energy | Admin work, simple tasks, emails |
| 1-2 | Exhausted | Rest, postpone complex tasks |

## Pattern Detection

The tracker identifies several types of patterns:

### Day-of-Week Patterns

Analyzes which days typically have higher or lower energy levels.

**Example insights:**
- "Energy typically low on Mondays (avg: 4.5/10)"
- "Energy typically high on Wednesday (avg: 8.2/10)"

### Sleep-Energy Correlation

Determines if there's a correlation between sleep hours and energy levels.

**Correlation levels:**
- **Strong**: 2+ point difference in energy between good sleep (7.5+ hrs) and poor sleep (<6 hrs)
- **Moderate**: 1-2 point difference
- **Weak**: Less than 1 point difference

### Vyvanse Timing Optimization

Analyzes which medication timing results in best energy levels.

**Example:**
- "Best results with 08:00 timing (avg energy: 8.5/10)"
- "Peak focus time: 10:00 AM - 12:00 PM" (2-4 hours after dose)

## Recommendations

The system provides intelligent recommendations based on:

1. **Current Energy Level**: Task complexity matched to current state
2. **Vyvanse Timing**: Identifies peak focus windows (2-3 hours post-dose)
3. **Historical Patterns**: Warns about typically low-energy days
4. **Sleep Quality**: Factors in last night's sleep

**Example recommendations:**

High Energy (8+):
- "High energy - ideal for deep work and complex tasks"
- "Peak focus time: 10:00 AM - 12:00 PM"

Moderate Energy (5-7):
- "Good energy - suitable for most tasks"

Low Energy (3-4):
- "Moderate energy - focus on lighter tasks and admin work"
- "Consider rescheduling complex tasks"

Very Low Energy (1-2):
- "Low energy - prioritize rest and simple tasks"
- "Historically low energy on Mondays - adjust expectations"

## Integration with Briefing Engine

The HealthStateTracker integrates with the BriefingEngine to provide personalized task recommendations:

```python
from Tools.health_state_tracker import HealthStateTracker
from Tools.briefing_engine import BriefingEngine

tracker = HealthStateTracker()
engine = BriefingEngine()

# Get current health assessment
assessment = tracker.get_current_state_assessment()
current_energy = assessment.get('current_energy')

# Use energy level for priority ranking
priorities = engine.get_top_priorities(energy_level=current_energy)
```

## Example Usage

See `example_health_state_tracker.py` for comprehensive examples including:

1. Logging basic health entries
2. Creating historical data for analysis
3. Calculating 7-day averages
4. Identifying patterns (requires 14+ days)
5. Getting current state assessment
6. Low energy day recommendations
7. Reviewing recent history

Run the examples:
```bash
python example_health_state_tracker.py
```

## Best Practices

1. **Log Daily**: Log your health state every morning for best pattern detection
2. **Be Consistent**: Use the same time each day for more accurate patterns
3. **Minimum 2 Weeks**: Pattern detection requires at least 14 days of data
4. **Be Honest**: Accurate logging leads to better recommendations
5. **Review Patterns**: Check patterns monthly to understand your rhythms

## ADHD-Specific Features

The HealthStateTracker is designed with ADHD needs in mind:

1. **Medication Tracking**: Specifically tracks Vyvanse timing for optimal focus windows
2. **Energy-Based Planning**: Matches task complexity to current energy state
3. **Pattern Recognition**: Identifies personal rhythms for better self-awareness
4. **Simple Logging**: Quick 1-10 scale reduces decision fatigue
5. **Actionable Insights**: Provides concrete, actionable recommendations

## Troubleshooting

### "Insufficient data for pattern detection"

- **Cause**: Less than minimum required days of data
- **Solution**: Log daily for at least 14 days before expecting patterns

### Data not persisting

- **Cause**: State directory missing or permissions issue
- **Solution**: Check that `State/` directory exists and is writable

### Inaccurate patterns

- **Cause**: Inconsistent logging or insufficient data
- **Solution**: Log daily at consistent times for at least 3-4 weeks

## Future Enhancements

Planned features for future versions:

- Sleep quality tracking (not just duration)
- Exercise and activity correlation
- Mood tracking integration
- Weather/seasonal pattern detection
- Custom medication types beyond Vyvanse
- Automatic suggestions for optimal medication timing
- Integration with wearables (Fitbit, Apple Watch)

## Related Documentation

- [BriefingEngine Guide](./BRIEFING_COMMAND.md)
- [Template Customization](../Templates/README.md)
- [Configuration Guide](../config/README.md)
