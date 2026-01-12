# Pattern Recognition CLI Command

**File:** `commands/pa/patterns.py`

Comprehensive CLI command for viewing, analyzing, exporting, and visualizing behavioral patterns and insights.

## Overview

The patterns command provides on-demand access to the pattern recognition engine, allowing you to:
- View all detected patterns without waiting for weekly review
- Run fresh pattern analysis on historical data
- Export patterns to markdown for documentation
- Visualize trends with text-based charts
- Search patterns by keyword or category
- List patterns organized by type

## Usage

```bash
python -m commands.pa.patterns [mode] [options]
```

## Modes

### 1. Show (Default)
Display all current patterns from Neo4j knowledge graph or run fresh analysis if none found.

```bash
python -m commands.pa.patterns show
python -m commands.pa.patterns show --compact
python -m commands.pa.patterns show --category=habit
python -m commands.pa.patterns show --days=60
```

**Features:**
- Tries Neo4j first for stored patterns
- Falls back to fresh analysis if no stored patterns
- Supports compact or full display format
- Category filtering (task/health/habit/trend/insight)

### 2. Analyze
Run on-demand pattern analysis without waiting for weekly review.

```bash
python -m commands.pa.patterns analyze
python -m commands.pa.patterns analyze --days=60
python -m commands.pa.patterns analyze --confidence=0.7
```

**Features:**
- Analyzes N days of historical data (default: 30)
- Runs all pattern analyzers:
  - Task completion patterns (hourly, daily, weekly)
  - Health correlations (sleep/productivity)
  - Habit streaks and breaks
  - Trend detection (improving/declining)
- Generates actionable insights
- Filters by confidence threshold

### 3. Export
Export patterns to markdown file with table of contents and metadata.

```bash
python -m commands.pa.patterns export
python -m commands.pa.patterns export --output=my_patterns.md
python -m commands.pa.patterns export --days=90
```

**Features:**
- Exports to `History/patterns_export.md` by default
- Includes table of contents
- Rich metadata (confidence, evidence, date ranges)
- Markdown formatting for documentation

**Output Location:** `History/[output_filename]`

### 4. Visualize
Show trend visualizations with text-based ASCII charts.

```bash
python -m commands.pa.patterns visualize
python -m commands.pa.patterns visualize --days=60
```

**Features:**
- Text-based trend charts with ASCII art
- Direction indicators:
  - `╱` for improving trends
  - `╲` for declining trends
  - `─` for plateau
- Change percentage display
- Visual trend strength indicators

**Example Output:**
```
📈 TREND VISUALIZATIONS

1. Tasks per day
   Improving trend: 7.2 → 9.4 tasks/day

   Start: 7.2
   │●
   │ ╱─────────●  (+30.6%)
   End:   9.4
   📈 IMPROVING
```

### 5. List
List patterns organized by category.

```bash
python -m commands.pa.patterns list
python -m commands.pa.patterns list --category=habit
python -m commands.pa.patterns list --category=health
```

**Features:**
- Organized by category sections
- Category emojis for visual clarity:
  - 💡 Task Completion Patterns
  - 🏥 Health Correlations
  - 🔄 Habit Streaks
  - 📈 Trends
- Shows pattern count per category
- Confidence scores for each pattern

### 6. Search
Search patterns by keyword or topic.

```bash
python -m commands.pa.patterns search sleep
python -m commands.pa.patterns search productivity
python -m commands.pa.patterns search "deep work"
```

**Features:**
- Case-insensitive keyword matching
- Searches across:
  - Pattern descriptions
  - Insight summaries
  - Supporting evidence
- Returns matching patterns and insights
- Displays match count

## Options

### --days=N
Number of days to analyze (default: 30)

```bash
python -m commands.pa.patterns analyze --days=60
```

Valid range: 1-365 days

### --category=TYPE
Filter by category type

```bash
python -m commands.pa.patterns show --category=habit
python -m commands.pa.patterns list --category=health
```

Valid categories:
- `task` - Task completion patterns
- `health` - Health/sleep correlations
- `habit` - Habit streaks and breaks
- `trend` - Improving/declining trends
- `insight` - Generated insights (all types)

### --confidence=N
Minimum confidence threshold (0.0-1.0, default: 0.6)

```bash
python -m commands.pa.patterns analyze --confidence=0.7
python -m commands.pa.patterns show --confidence=0.8
```

Only shows patterns with confidence >= threshold.

### --compact
Use compact single-line display format

```bash
python -m commands.pa.patterns show --compact
```

Compact format shows:
- One line per insight
- Category emoji + summary + confidence indicator
- No evidence or detailed descriptions

### --output=FILE
Output filename for export mode (default: patterns_export.md)

```bash
python -m commands.pa.patterns export --output=weekly_patterns.md
```

File saved to `History/[filename]`

## Implementation Details

### Architecture

**File:** `commands/pa/patterns.py` (704 lines)

**Key Components:**
1. **Argument Parser** - Parses command-line arguments and options
2. **Pattern Analysis Engine** - Runs comprehensive pattern analysis
3. **Neo4j Integration** - Retrieves stored patterns from knowledge graph
4. **Display Formatters** - Multiple display formats (compact/full/charts)
5. **Export Engine** - Markdown export with TOC and metadata
6. **Search Engine** - Keyword-based pattern search

### Pattern Analysis Workflow

1. **Data Aggregation**
   - Uses `DataAggregator` to pull historical data
   - Task completions from State files
   - Health metrics from Oura API
   - Commitments from Neo4j
   - Session records from History

2. **Time Series Conversion**
   - Converts raw data to time series format
   - Creates `TaskCompletionRecord` objects
   - Creates `HealthMetricRecord` objects
   - Creates `ProductivityRecord` objects

3. **Pattern Analysis**
   - **Task Patterns:** Hourly, daily, weekly completion patterns
   - **Health Correlations:** Sleep/readiness vs productivity
   - **Habit Streaks:** Recurring habits, streaks, breaks
   - **Trend Detection:** Improving/declining/plateau trends

4. **Insight Generation**
   - Generates insights from all detected patterns
   - Scores by significance, actionability, impact
   - Filters by confidence threshold
   - Returns actionable recommendations

### Dependencies

**Core Modules:**
- `Tools.pattern_recognition.data_aggregator` - Data collection
- `Tools.pattern_recognition.time_series` - Time series structures
- `Tools.pattern_recognition.analyzers.*` - Pattern analyzers
- `Tools.pattern_recognition.insight_generator` - Insight generation
- `Tools.pattern_recognition.weekly_review_formatter` - Display formatting
- `Tools.pattern_recognition.pattern_queries` - Neo4j queries
- `Tools.pattern_recognition.pattern_storage` - Neo4j storage

**External Dependencies:**
- `asyncio` - Async pattern analysis
- `datetime` - Date range handling
- `pathlib` - File path operations

### Error Handling

**Graceful Degradation:**
- Missing modules → Error message with instructions
- No Neo4j connection → Falls back to fresh analysis
- Insufficient data → Displays appropriate message
- Parse errors → Default values used

**Exception Handling:**
- `ImportError` → Module availability check
- `Exception` → Catch-all with traceback for debugging

## Examples

### View All Patterns
```bash
python -m commands.pa.patterns show
```

Output:
```
============================================================
📊 Pattern Recognition - SHOW mode
============================================================

Retrieved 15 recent patterns from knowledge graph

============================================================
💡 INSIGHTS
============================================================

1. Most productive 9-11am (avg 8.2 tasks)
   ●●●●○ 82% confidence - High

   📊 Evidence:
      • Analyzed 45 days from 2024-11-15 to 2024-12-30
      • Peak productivity window: 9-11am (40% above average)
      • Consistent pattern across 85% of workdays

   🎯 Action: Schedule important tasks during 9-11am...

[... more insights ...]
```

### Analyze Last 60 Days
```bash
python -m commands.pa.patterns analyze --days=60
```

### Export to Markdown
```bash
python -m commands.pa.patterns export --output=2024_patterns.md
```

Output: `History/2024_patterns.md` with:
- Table of contents
- Full insight details
- Evidence and confidence scores
- Metadata and date ranges

### Visualize Trends
```bash
python -m commands.pa.patterns visualize
```

### List Habit Patterns
```bash
python -m commands.pa.patterns list --category=habit
```

### Search for Sleep Patterns
```bash
python -m commands.pa.patterns search sleep
```

## Integration with Weekly Review

The patterns command complements the weekly review system:

**Weekly Review (`commands/pa/weekly.py`):**
- Automatically runs pattern recognition before review
- Includes top 3 insights in review context
- Strategic, high-level reflection

**Patterns Command (`commands/pa/patterns.py`):**
- On-demand pattern access anytime
- View all patterns, not just top 3
- Detailed analysis and export capabilities
- Search and filter functionality

**Use Cases:**
- **Weekly Review:** Get top insights for strategic reflection
- **Patterns Command:** Deep dive into specific patterns between reviews
- **Export:** Document patterns for sharing or archival
- **Visualize:** Understand trend trajectories over time

## Future Enhancements

Potential improvements:
- [ ] Interactive mode with prompts
- [ ] Pattern comparison across time periods
- [ ] Correlation heatmap visualization
- [ ] Pattern strength rankings
- [ ] Custom threshold configuration
- [ ] Pattern alerts/notifications
- [ ] Integration with daily briefing
- [ ] Pattern evolution tracking over weeks/months

## Troubleshooting

### "Required modules not available"
**Solution:** Ensure all pattern recognition modules are in `Tools/pattern_recognition/`

### "No patterns found"
**Causes:**
- No historical data available
- Date range too narrow
- Confidence threshold too high

**Solution:**
- Run `analyze` mode to generate fresh patterns
- Increase `--days` parameter
- Lower `--confidence` threshold

### "Neo4j adapter not available"
**Solution:** This is expected if Neo4j isn't configured. Command falls back to fresh analysis.

### "Insufficient data for pattern analysis"
**Solution:** Need at least 7-14 days of data for meaningful patterns. Keep logging data.

## Related Commands

- `commands/pa/weekly.py` - Weekly review with automatic pattern integration
- `commands/pa/daily.py` - Daily briefing (could integrate patterns in future)

## See Also

- **Pattern Storage:** `Tools/pattern_recognition/pattern_storage.py`
- **Pattern Queries:** `Tools/pattern_recognition/pattern_queries.py`
- **Formatters:** `Tools/pattern_recognition/weekly_review_formatter.py`
- **Models:** `Tools/pattern_recognition/models.py`
