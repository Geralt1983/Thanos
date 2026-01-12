# Pattern Recognition Engine - User Guide

**Last Updated:** 2026-01-11
**Version:** 1.0

## Overview

The Pattern Recognition Engine is an intelligent analysis system that identifies patterns in your productivity, habits, health metrics, and behavior. It automatically surfaces actionable insights to help you optimize your daily routine and achieve your goals.

**Key Features:**
- 📊 **Task completion analysis** by time of day and day of week
- 🏥 **Health-productivity correlations** (sleep, readiness, energy)
- 🔄 **Habit streak tracking** with break identification
- 📈 **Trend detection** (improving/declining/plateau patterns)
- 💡 **Automated insight generation** with confidence scoring
- 🧠 **Knowledge graph integration** for persona access

---

## Table of Contents

1. [How Pattern Recognition Works](#how-pattern-recognition-works)
2. [Understanding Insights](#understanding-insights)
3. [Configuration Options](#configuration-options)
4. [CLI Usage](#cli-usage)
5. [Troubleshooting](#troubleshooting)
6. [Advanced Topics](#advanced-topics)

---

## How Pattern Recognition Works

### Architecture Overview

The pattern recognition system follows a data pipeline architecture:

```
Historical Data → Time Series → Pattern Analysis → Insights → Storage
    ↓                ↓                ↓               ↓          ↓
Aggregator     TaskRecords      Analyzers      Generator    Neo4j
              HealthRecords     (4 types)      (Scoring)   (Graph)
              ProductivityRec
```

### 1. Data Aggregation

**Module:** `Tools/pattern_recognition/data_aggregator.py`

The DataAggregator collects historical data from multiple sources:

- **Task Completions**: From `State/Commitments.md`, `State/Today.md`, and `History/Sessions/`
- **Health Metrics**: From Oura API via OuraAdapter (sleep, readiness, HRV, steps)
- **Commitments**: From Neo4j knowledge graph
- **Sessions**: From `History/Sessions/` (timestamped activity records)

**Time Series Construction:**
- Data is organized into daily time series records
- Three record types: TaskCompletionRecord, HealthMetricRecord, ProductivityRecord
- Supports daily, weekly, and monthly aggregations
- Default analysis window: 30 days (configurable)

### 2. Pattern Analysis Algorithms

The system employs four specialized analyzers:

#### A. Task Completion Patterns

**Module:** `Tools/pattern_recognition/analyzers/task_patterns.py`

**Algorithms:**

1. **Hourly Pattern Detection**
   - Aggregates task completions by hour of day (0-23)
   - Calculates mean completion rate per hour
   - Identifies peak hours: >20% above daily average
   - Groups consecutive peak hours into productivity windows
   - Example: "Peak productivity 9-11am (122% of average)"

2. **Daily Pattern Detection**
   - Analyzes completion rates by day of week (Mon-Sun)
   - Calculates mean completions per day
   - Detects significant variations: >15% deviation from weekly average
   - Example: "Mondays show 30% lower completion rate"

3. **Task Type Patterns**
   - Groups tasks by type (work, personal, deep work, etc.)
   - Identifies when specific task types are completed
   - Detects type-time correlations: >15% concentration in specific hours
   - Example: "Deep work tasks completed best in morning hours"

4. **Daily Completion Rate**
   - Calculates average tasks completed per day
   - Compares first half vs second half of analysis period
   - Detects acceleration or deceleration trends
   - Example: "Daily completion rate: 6.2 tasks/day (+15% vs last period)"

**Statistical Methods:**
- **Confidence Scoring**: Based on sample size (60%) + consistency (40%)
- **Minimum Samples**: 3-5 depending on pattern type
- **Threshold**: min_confidence = 0.7 (patterns below this are filtered)

#### B. Health-Productivity Correlations

**Module:** `Tools/pattern_recognition/analyzers/health_correlation.py`

**Algorithms:**

1. **Sleep Duration ↔ Task Completion**
   - Pairs sleep data (day N) with next-day task completion (day N+1)
   - Calculates Pearson correlation coefficient
   - Identifies optimal sleep threshold via percentile analysis (75th percentile)
   - Quantifies effect size: tasks completed at different sleep levels
   - Example: "7+ hours sleep → 40% more tasks completed next day"

2. **Readiness Score ↔ Productivity**
   - Same-day correlation between Oura readiness and productivity score
   - Productivity calculated from: tasks (40%) + focus (30%) + energy (30%)
   - Detects readiness thresholds that predict high productivity
   - Example: "Readiness >85 correlates with 35% higher productivity"

3. **Deep Sleep ↔ Focus**
   - Pairs deep sleep duration (night N) with next-day focus metrics
   - Focus inferred from task completion patterns and session quality
   - Identifies deep sleep targets for optimal focus
   - Example: "2+ hours deep sleep → improved focus scores"

4. **Sleep Timing ↔ Morning Energy**
   - Same-day correlation between bedtime/wake time and morning energy
   - Energy measured from early-morning task completion rates
   - Detects optimal sleep schedules
   - Example: "Bedtime before 11pm → 25% higher morning energy"

**Statistical Methods:**
- **Pearson Correlation**: |r| > 0.3 considered meaningful
- **Confidence Scoring**: Sample size (50%) + correlation strength (30%) + effect size (20%)
- **Minimum Samples**: 10 paired observations
- **Threshold**: min_confidence = 0.65

#### C. Habit Streak Analysis

**Module:** `Tools/pattern_recognition/analyzers/habit_streaks.py`

**Algorithms:**

1. **Recurring Habit Identification**
   - Scans task completion records for repeated patterns
   - Configurable frequency: daily (every day), weekly (every 7 days)
   - Minimum occurrences: 5 within analysis window
   - Minimum span: 14 days
   - Example: "Daily review appears 45 times over 60 days"

2. **Streak Calculation**
   - **Current Streak**: Consecutive days from today backward
   - **Longest Streak**: Historical maximum streak length
   - **Total Completions**: Count across analysis period
   - Break detection: First date after active streak ends

3. **Consistency Scoring**
   - Formula: `actual_completions / expected_completions`
   - Expected based on habit frequency (daily=1/day, weekly=1/7 days)
   - Perfect consistency = 1.0 (every expected occurrence completed)
   - Example: 28 completions in 30 days = 0.93 consistency

4. **Streak Break Analysis**
   - **Day-of-week patterns**: Which days are breaks most common?
   - **Health correlations**: Do breaks coincide with poor sleep?
   - **Task load correlations**: Do high workload days cause breaks?
   - Root cause identification for improvement

**Statistical Methods:**
- **Confidence Scoring**: Sample size (60%) + consistency (40%)
- **Minimum Occurrences**: 5 instances
- **Threshold**: min_confidence = 0.6 (habits have inherent variability)

#### D. Trend Detection

**Module:** `Tools/pattern_recognition/analyzers/trend_detector.py`

**Algorithms:**

1. **Linear Regression Analysis**
   - Applies least squares regression to time series data
   - Calculates slope (rate of change) and R² (fit quality)
   - Detects four trend types:
     - **IMPROVING**: Slope > +5% per period
     - **DECLINING**: Slope < -5% per period
     - **PLATEAU**: -5% ≤ slope ≤ +5%
     - **VOLATILE**: High variance, inconsistent direction

2. **Trend Strength Calculation**
   - Measures consistency of direction across periods
   - Formula: `consistent_movements / total_movements`
   - High strength (>0.8): Clear, stable trend
   - Low strength (<0.5): Noisy, unreliable trend

3. **Momentum Indicators**
   - **7-day momentum**: Recent short-term direction
   - **30-day momentum**: Medium-term trend
   - **90-day momentum**: Long-term trajectory
   - Compares different time windows to detect acceleration/deceleration

4. **Multi-Metric Trend Analysis**
   - **Task Completion Trends**: Tasks/day over time
   - **Health Metric Trends**: Sleep quality, readiness, HRV
   - **Productivity Trends**: Composite productivity score
   - Cross-metric correlation to identify drivers

**Statistical Methods:**
- **Confidence Scoring**: Sample size (40%) + strength (35%) + magnitude (25%)
- **Minimum Samples**: 7 data points for 7-day, 14+ for longer trends
- **Threshold**: min_confidence = 0.65

### 3. Insight Generation

**Module:** `Tools/pattern_recognition/insight_generator.py`

**Scoring Algorithm:**

Insights are scored using a weighted multi-factor model:

```python
insight_score = (
    significance * 0.25 +      # Statistical strength
    actionability * 0.20 +     # Can user act on it?
    impact * 0.20 +            # Potential improvement magnitude
    confidence * 0.15 +        # Statistical confidence
    recency * 0.10 +           # Recent vs old data
    novelty * 0.10             # Not repetitive
)
```

**Factor Calculations:**

1. **Significance (25%)**
   - Combines: confidence score + sample size + effect size
   - High significance: Strong statistical backing + large effect
   - Formula: `(confidence * 0.4 + sample_size_score * 0.3 + effect_size * 0.3)`

2. **Actionability (20%)**
   - Pattern-specific scoring:
     - Habit patterns: 0.90 (highly actionable - just maintain the habit)
     - Task patterns: 0.85 (actionable - schedule tasks at peak times)
     - Health correlations: 0.60-0.70 (moderately actionable - lifestyle changes)
     - Trends: 0.50-0.80 (varies by controllability)

3. **Impact (20%)**
   - Based on magnitude of potential improvement
   - Task patterns: Completion rate differential (e.g., 40% more productive)
   - Health correlations: Effect size (e.g., +2.5 tasks per day)
   - Habits: Streak length and consistency potential
   - Trends: Change percentage over time

4. **Confidence (15%)**
   - Direct use of pattern's statistical confidence score
   - Higher confidence = more reliable insight

5. **Recency (10%)**
   - Exponential decay: `exp(-days_old / 30)`
   - Half-life: 30 days (patterns from 30 days ago score 0.5)
   - Recent patterns weighted higher (more relevant)

6. **Novelty (10%)**
   - Compares to previously surfaced insights
   - Jaccard similarity calculation on text
   - Penalties:
     - Exact duplicate: -0.20
     - >70% similar: -0.15
     - >50% similar: -0.10
   - Prevents repetitive insights week-to-week

**Top Insights Selection:**

The `select_top_insights()` function implements diversity-aware ranking:

1. **Filter by confidence**: Remove insights below threshold (default 0.65)
2. **Goal alignment**: Boost scores for insights matching user goals (+0.15 max)
3. **Novelty adjustment**: Penalize insights similar to recent ones
4. **Diversity enforcement**: Maximum 2 insights per category
5. **Rank by adjusted score**: Sort by (base_score + goal_bonus + novelty_penalty)
6. **Select top N**: Default 3 for weekly review

### 4. Storage & Retrieval

**Module:** `Tools/pattern_recognition/pattern_storage.py`

**Neo4j Knowledge Graph Integration:**

All detected patterns are stored in Neo4j with:
- **Rich metadata**: Confidence scores, date ranges, sample sizes
- **Evidence lists**: Top 5 supporting data points
- **Category tags**: task_completion, health_correlation, habit, trend
- **Relationships**: Patterns can SUPPORT, CONTRADICT, or EVOLVE_INTO others

**Query Interface:**

**Module:** `Tools/pattern_recognition/pattern_queries.py`

Persona agents can query patterns via:
- `get_patterns_by_category(category)`: Filter by type
- `get_recent_insights(limit, days_back)`: Latest insights
- `get_patterns_related_to(topic)`: Keyword search with automatic expansion
- `get_pattern_context_for_persona()`: Comprehensive context package

---

## Understanding Insights

### Insight Anatomy

Each insight contains:

```
💡 [SUMMARY]
Peak productivity during 09:00-11:00 (122% of average)

📊 Evidence:
• 90 data points analyzed
• Average: 8.5 tasks during peak hours vs 4.2 overall
• Consistency: 87% of peak-hour days show above-average completion

✅ Recommended Action:
Schedule important tasks during 09:00-11:00 to capitalize on peak productivity

🎯 Confidence: ●●●●○ 82% - High
```

**Components:**

1. **Summary** (1-2 sentences)
   - Concise description of the pattern
   - Quantified when possible (percentages, averages)

2. **Evidence** (3-5 data points)
   - Statistical backing
   - Sample size, effect size, consistency metrics
   - Demonstrates why this pattern is reliable

3. **Recommended Action** (specific, actionable)
   - Begins with action verb (Schedule, Maintain, Prioritize, etc.)
   - Concrete behavior change
   - Expected outcome stated

4. **Confidence Indicator**
   - Visual bar: ●●●●● (filled circles) + ○ (empty circles)
   - Percentage: 0-100%
   - Label: Low (<60%), Moderate (60-80%), High (≥80%)

### Insight Categories

**💡 Task Completion Insights**
- When you're most productive (hourly/daily patterns)
- Which task types succeed at which times
- Completion rate trends

**Example:**
> "Wednesdays show 17% higher completion rate. Schedule important tasks on Wednesday to leverage this pattern."

**🏥 Health-Productivity Insights**
- Sleep duration effects on productivity
- Readiness score correlations
- Deep sleep and focus relationships
- Sleep timing impacts

**Example:**
> "7+ hours sleep correlates with 40% more tasks completed next day. Prioritize sleep to boost productivity."

**🔄 Habit Insights**
- Current streaks and milestones
- Consistency scores
- Streak break patterns and causes

**Example:**
> "Daily review: 45-day streak (approaching your record of 60 days). Maintain momentum to set a new personal record."

**📈 Trend Insights**
- Improving/declining patterns
- Momentum indicators
- Rate of change

**Example:**
> "Task completion improving: 5.2 → 7.4 tasks/day over 30 days (+42%). Momentum is building - keep it up!"

### Confidence Levels Explained

**High Confidence (≥80%)**
- Large sample size (50+ data points)
- Strong statistical significance
- Consistent pattern (low variance)
- **Action:** Trust this insight - act on it confidently

**Moderate Confidence (60-80%)**
- Adequate sample size (20-50 data points)
- Moderate statistical significance
- Some variance but clear trend
- **Action:** Consider this insight - worth experimenting with

**Low Confidence (<60%)**
- Small sample size (<20 data points) OR
- High variance/noise OR
- Weak statistical significance
- **Action:** Informational only - don't change behavior yet
- **Note:** These are filtered out by default (min_confidence = 0.65)

### Interpreting Action Recommendations

**Action Verbs & Their Meanings:**

- **Schedule**: Add to your calendar/task list at specific times
  - Example: "Schedule deep work during morning peak hours"

- **Prioritize**: Move higher in importance/urgency
  - Example: "Prioritize sleep to improve next-day productivity"

- **Maintain**: Keep doing what you're doing
  - Example: "Maintain your 45-day streak to reach your goal"

- **Avoid**: Reduce or eliminate a behavior
  - Example: "Avoid scheduling important tasks on Monday mornings"

- **Increase/Decrease**: Adjust quantity or frequency
  - Example: "Increase deep sleep target to 2+ hours per night"

- **Review**: Investigate further before acting
  - Example: "Review task load on streak break days to identify patterns"

**How to Act on Insights:**

1. **Read all top 3 insights** in your weekly review
2. **Choose 1-2 to act on** this week (don't overwhelm yourself)
3. **Create specific commitments** based on recommendations
   - Example: "Schedule email processing during 9-10am peak window"
4. **Track results** over the next week
5. **Review effectiveness** in next week's insights

---

## Configuration Options

### Pattern Analysis Thresholds

**Location:** Various analyzer modules

#### Task Pattern Configuration

**File:** `Tools/pattern_recognition/analyzers/task_patterns.py`

```python
# Hourly patterns
analyze_hourly_patterns(
    task_records,
    min_samples=5,           # Minimum data points per hour
    min_confidence=0.7       # Minimum confidence to include (70%)
)

# Thresholds within function
HOURLY_PEAK_THRESHOLD = 1.2    # 20% above average = peak

# Daily patterns
analyze_daily_patterns(
    task_records,
    min_samples=3,           # Minimum data points per day-of-week
    min_confidence=0.7       # Minimum confidence (70%)
)

# Thresholds within function
DAILY_VARIATION_THRESHOLD = 0.15  # 15% variation required
```

**Tuning Guidance:**
- **Increase min_samples**: More data required = higher reliability but fewer patterns
- **Increase min_confidence**: Stricter filtering = only strongest patterns surface
- **Adjust thresholds**: Lower threshold (e.g., 1.15 = 15%) = more patterns detected

#### Health Correlation Configuration

**File:** `Tools/pattern_recognition/analyzers/health_correlation.py`

```python
# All correlation functions
analyze_sleep_duration_with_tasks(
    task_records,
    health_records,
    min_samples=10,          # Minimum paired observations
    min_confidence=0.65      # Minimum confidence (65%)
)

# Thresholds within function
CORRELATION_THRESHOLD = 0.3     # Pearson |r| > 0.3 = meaningful
OPTIMAL_THRESHOLD_PERCENTILE = 0.75  # 75th percentile for "optimal" values
```

**Tuning Guidance:**
- **min_samples=10**: Need at least 10 days of paired health+task data
- **CORRELATION_THRESHOLD**: Lowering to 0.25 detects weaker correlations (more noise)
- **Raising to 0.4**: Only strong correlations (fewer, higher quality)

#### Habit Streak Configuration

**File:** `Tools/pattern_recognition/analyzers/habit_streaks.py`

```python
identify_recurring_habits(
    task_records,
    min_occurrences=5,       # Must appear 5+ times
    min_span_days=14,        # Across 14+ days
    frequency=1              # Daily habit (1=daily, 7=weekly)
)

analyze_habit_streak(
    task_records,
    habit_name,
    frequency=1,             # Expected frequency
    min_confidence=0.6       # Minimum confidence (60%)
)
```

**Tuning Guidance:**
- **min_occurrences**: Lower (e.g., 3) detects new habits faster
- **frequency**: Set to 7 for weekly habits, 30 for monthly
- **min_confidence**: Kept lower (0.6) because habits have natural variability

#### Trend Detection Configuration

**File:** `Tools/pattern_recognition/analyzers/trend_detector.py`

```python
detect_trend(
    time_series_data,
    min_samples=7,           # Minimum data points
    min_confidence=0.65      # Minimum confidence (65%)
)

# Thresholds within function
TREND_SLOPE_THRESHOLD = 0.05    # 5% change = significant
MOMENTUM_WINDOWS = [7, 30, 90]  # Days for momentum calculation
```

**Tuning Guidance:**
- **TREND_SLOPE_THRESHOLD**: Lower (e.g., 0.03 = 3%) detects subtler trends
- **min_samples**: Need at least 7 days for short-term trends, 30+ for reliable long-term
- **Momentum windows**: Customize to your review cycle (e.g., [14, 60] for biweekly/bimonthly)

### Insight Scoring Configuration

**Location:** `Tools/pattern_recognition/insight_generator.py`

```python
# Scoring weights
SCORING_WEIGHTS = {
    "significance": 0.25,    # Statistical strength
    "actionability": 0.20,   # Can user act on it?
    "impact": 0.20,          # Potential improvement
    "confidence": 0.15,      # Statistical confidence
    "recency": 0.10,         # Recent vs old data
    "novelty": 0.10,         # Not repetitive
}

# Recency decay
RECENCY_HALF_LIFE_DAYS = 30  # Patterns decay 50% in 30 days

# Novelty thresholds
NOVELTY_PENALTY_EXACT = -0.20        # Exact duplicate
NOVELTY_PENALTY_HIGH_SIMILARITY = -0.15   # >70% similar
NOVELTY_PENALTY_MODERATE_SIMILARITY = -0.10  # >50% similar

# Top insights selection
select_top_insights(
    insights,
    num_insights=3,          # Number to surface
    min_confidence=0.65,     # Filter threshold
    max_per_category=2,      # Diversity constraint
    user_goals=[...]         # For personalization
)
```

**Tuning Guidance:**

- **Adjust weights** to change what types of insights surface:
  - Increase `actionability` (0.20 → 0.30): Favor practical insights
  - Increase `impact` (0.20 → 0.30): Favor high-leverage insights
  - Increase `novelty` (0.10 → 0.15): More variety week-to-week

- **Recency half-life**:
  - Shorter (e.g., 14 days): Favor very recent patterns
  - Longer (e.g., 60 days): Value long-term stable patterns

- **Diversity**:
  - `max_per_category=1`: Maximum variety (one per category)
  - `max_per_category=3`: Allow multiple similar insights

### Weekly Review Integration

**Location:** `commands/pa/weekly.py`

```python
# Pattern recognition settings
PATTERN_ANALYSIS_DAYS = 30   # Days of history to analyze
TOP_INSIGHTS_COUNT = 3       # Insights in weekly review
```

**Customization:**
- Increase `PATTERN_ANALYSIS_DAYS` to 60 or 90 for longer-term patterns
- Increase `TOP_INSIGHTS_COUNT` to 5 for more comprehensive reviews

### Configuration Best Practices

1. **Start conservative** (current defaults are well-tuned)
2. **Change one parameter at a time** to measure impact
3. **Track metrics** before and after changes:
   - Number of patterns detected per week
   - Average confidence scores
   - Actionability rate
4. **Validate with real data** after tuning (see Testing section)
5. **Document changes** in `docs/PATTERN_RECOGNITION_TUNING.md`

---

## CLI Usage

### Pattern Recognition Command

**Location:** `commands/pa/patterns.py`

**Basic Syntax:**
```bash
python -m commands.pa.patterns [mode] [options]
```

### Modes

#### 1. Show Mode (Default)

Display current patterns from storage or run fresh analysis.

```bash
# Show all current patterns
python -m commands.pa.patterns show

# Show with filters
python -m commands.pa.patterns show --category=habit --confidence=0.8

# Compact display
python -m commands.pa.patterns show --compact
```

**What it does:**
1. Tries to retrieve patterns from Neo4j knowledge graph
2. Falls back to fresh analysis if storage unavailable
3. Displays insights with evidence and confidence indicators

**Output example:**
```
📊 Pattern Recognition - SHOW mode
================================================================================

💡 INSIGHTS
================================================================================

1. 🔥 Habit Streak
   general: 90-day streak (approaching your record of 90 days)

   📊 Evidence:
   • Current streak: 90 days
   • Longest streak: 90 days
   • Consistency: 100%

   ✅ Action:
   Maintain momentum on general to set a new personal record

   🎯 Confidence: ●●●●● 97% - High

2. 💡 Task Completion Pattern
   Peak productivity during 09:00 (122% of average)

   📊 Evidence:
   • Sample size: 90 data points
   • Peak hour completion rate: 122%

   ✅ Action:
   Schedule important tasks during 09:00 to capitalize on peak productivity

   🎯 Confidence: ●●●●● 97% - High
```

#### 2. Analyze Mode

Run on-demand pattern analysis without waiting for weekly review.

```bash
# Analyze last 30 days (default)
python -m commands.pa.patterns analyze

# Analyze last 60 days
python -m commands.pa.patterns analyze --days=60

# Filter by confidence threshold
python -m commands.pa.patterns analyze --confidence=0.8

# Analyze and show compact
python -m commands.pa.patterns analyze --days=90 --compact
```

**What it does:**
1. Runs DataAggregator to collect historical data
2. Executes all four pattern analyzers
3. Generates insights with confidence scoring
4. Filters and displays results

**Use cases:**
- Monthly deep dives (--days=90)
- Testing after configuration changes
- Ad-hoc pattern exploration

#### 3. Export Mode

Export patterns to markdown file for documentation or sharing.

```bash
# Export to default location (History/patterns_export.md)
python -m commands.pa.patterns export

# Custom output file
python -m commands.pa.patterns export --output=january_patterns.md

# Export with filters
python -m commands.pa.patterns export --days=60 --category=health
```

**What it does:**
1. Runs pattern analysis
2. Generates markdown document with:
   - Table of contents
   - Metadata (date, analysis period)
   - All insights with evidence
   - Category organization
3. Saves to `History/[filename].md`

**Output format:**
```markdown
# Pattern Recognition Export

*Generated: 2026-01-11 14:30*

## Table of Contents
1. [Habit Insights](#habit-insights)
2. [Task Completion Insights](#task-completion-insights)

## Habit Insights
### 1. general: 90-day streak
- **Confidence:** 97%
- **Evidence:**
  - Current streak: 90 days
  - Consistency: 100%
...
```

#### 4. Visualize Mode

Display text-based trend visualizations.

```bash
# Visualize all trends
python -m commands.pa.patterns visualize

# With custom analysis period
python -m commands.pa.patterns visualize --days=90
```

**What it does:**
1. Runs trend detection analyzer
2. Creates ASCII charts showing trend direction
3. Displays start value, end value, change percentage

**Output example:**
```
📈 TREND VISUALIZATIONS
================================================================================

1. Task Completion Rate
   Task completion improving: 5.2 → 7.4 tasks/day over 30 days

   Start: 5.2
   │●
   │ ╱────────────────────────●  (+42.3%)
   End:   7.4
   📈 IMPROVING

2. Sleep Duration
   Sleep duration declining: 7.5 → 6.8 hours over 30 days

   Start: 7.5
   │──────────────────●
   │            ●─────╲  (-9.3%)
   End:   6.8
   📉 DECLINING
```

#### 5. List Mode

List patterns organized by category.

```bash
# List all patterns by category
python -m commands.pa.patterns list

# Filter to specific category
python -m commands.pa.patterns list --category=task
python -m commands.pa.patterns list --category=health
python -m commands.pa.patterns list --category=habit
python -m commands.pa.patterns list --category=trend
```

**What it does:**
1. Runs pattern analysis
2. Groups patterns by category
3. Displays organized list with counts

**Output example:**
```
📋 PATTERNS BY CATEGORY
================================================================================

💡 Task Completion Patterns (7)
------------------------------------------------------------
1. Peak productivity during 09:00 (122% of average) (97% confidence)
2. Wednesdays show higher completion rate (+17%) (89% confidence)
3. Fridays show higher completion rate (+20%) (89% confidence)

🔄 Habit Streaks (1)
------------------------------------------------------------
1. general: 90-day streak (97% confidence)
```

#### 6. Search Mode

Search patterns by keyword or topic.

```bash
# Search for sleep-related patterns
python -m commands.pa.patterns search sleep

# Search for productivity patterns
python -m commands.pa.patterns search productivity

# Search with filters
python -m commands.pa.patterns search focus --confidence=0.7
```

**What it does:**
1. Runs pattern analysis
2. Searches all pattern descriptions, summaries, evidence
3. Topic expansion: "sleep" also matches "rest", "bedtime", "wake"
4. Displays matching patterns and insights

**Topic expansion examples:**
- `sleep` → sleep, rest, bedtime, wake, nap
- `productivity` → tasks, focus, completion, output
- `energy` → stamina, fatigue, vigor, vitality

### Command Options

**--days=N**
- Specifies analysis time window
- Default: 30 days
- Recommended: 30 (quick), 60 (medium), 90 (comprehensive)
- Example: `--days=60`

**--category=TYPE**
- Filters patterns by category
- Options: task, health, habit, trend, insight
- Example: `--category=habit`

**--confidence=N**
- Minimum confidence threshold (0.0-1.0)
- Default: 0.6
- Higher = fewer, stronger patterns
- Example: `--confidence=0.8` (only high-confidence)

**--compact**
- Uses compact single-line display format
- Good for quick scans or many patterns
- Example: `--compact`

**--output=FILE**
- Output filename for export mode
- Saved to History/ directory
- Example: `--output=my_patterns.md`

### Weekly Review Integration

Patterns are automatically included in weekly reviews:

```bash
# Run weekly review (includes patterns)
python -m commands.pa.weekly review

# Just the insights phase
python -m commands.pa.weekly insights
```

**What happens:**
1. Pattern recognition runs automatically before review generation
2. Top 3 insights included in review context
3. Formatted patterns section added to review output
4. Goals from `State/Goals.md` used for personalization

### Usage Examples

**Weekly routine:**
```bash
# Monday: Check what patterns emerged
python -m commands.pa.patterns show

# Friday: Export for documentation
python -m commands.pa.patterns export --output=week_$(date +%Y%m%d).md

# Sunday: Full weekly review (includes patterns)
python -m commands.pa.weekly review
```

**Monthly deep dive:**
```bash
# Analyze 90 days of patterns
python -m commands.pa.patterns analyze --days=90 --confidence=0.75

# Export comprehensive report
python -m commands.pa.patterns export --days=90 --output=monthly_review.md

# Visualize trends
python -m commands.pa.patterns visualize --days=90
```

**Troubleshooting workflow:**
```bash
# Check if habits are being tracked
python -m commands.pa.patterns list --category=habit

# Search for specific pattern
python -m commands.pa.patterns search "Monday"

# Lower threshold to see weaker patterns
python -m commands.pa.patterns analyze --confidence=0.5
```

---

## Troubleshooting

### Common Issues

#### Issue 1: No Patterns Detected

**Symptoms:**
```
📭 No patterns found. Try running analysis first with 'analyze' mode.
```

**Possible Causes:**

1. **Insufficient Historical Data**
   - Need minimum 14 days for habits, 7 days for task patterns
   - **Solution:** Wait for more data to accumulate
   - **Check:** `ls History/Sessions/` - should have multiple dated files

2. **Confidence Threshold Too High**
   - Default min_confidence = 0.65-0.7 may filter all patterns
   - **Solution:** Lower threshold temporarily
   ```bash
   python -m commands.pa.patterns analyze --confidence=0.5
   ```

3. **No Task Completions Recorded**
   - DataAggregator requires task completion data
   - **Check:** `cat State/Today.md` - should show completed tasks
   - **Solution:** Use the system daily to record completions

4. **Analysis Period Too Short**
   - Default 30 days may not capture weekly/monthly patterns
   - **Solution:** Increase analysis window
   ```bash
   python -m commands.pa.patterns analyze --days=60
   ```

**Debug Steps:**
```bash
# 1. Check raw data availability
ls -la History/Sessions/
cat State/Commitments.md

# 2. Try with minimal thresholds
python -m commands.pa.patterns analyze --confidence=0.3 --days=90

# 3. Check each category individually
python -m commands.pa.patterns list --category=task
python -m commands.pa.patterns list --category=habit
```

#### Issue 2: Only Habit Patterns, No Task Patterns

**Symptoms:**
- Habits detected successfully
- No hourly or daily task patterns

**Possible Causes:**

1. **Missing Hourly Distribution Data**
   - TaskCompletionRecord requires `hourly_distribution` field
   - **Check:** DataAggregator output logs
   - **Solution:** Ensure task completion times are recorded

2. **Uniform Task Distribution**
   - If you complete tasks evenly throughout the day, no "peak" hours
   - **Solution:** This is actually fine - means consistent productivity!
   - **Adjustment:** Lower HOURLY_PEAK_THRESHOLD from 1.2 to 1.1

3. **Small Variance**
   - Day-of-week variations <15% won't trigger patterns
   - **Solution:** Lower DAILY_VARIATION_THRESHOLD if desired

**Debug Steps:**
```python
# Check task records directly
from Tools.pattern_recognition.data_aggregator import DataAggregator
from datetime import datetime, timedelta

aggregator = DataAggregator()
data = await aggregator.aggregate_data(
    start_date=datetime.now().date() - timedelta(days=30),
    end_date=datetime.now().date()
)

print(f"Task completions: {len(data.task_completions)}")
for task in data.task_completions[:5]:
    print(f"  {task.completed_date}: {task.title}")
```

#### Issue 3: No Health Correlations

**Symptoms:**
```
🏥 Health Correlations (0)
```

**Possible Causes:**

1. **No Oura Data Available** (MOST COMMON)
   - Oura API integration not configured or no MCP access
   - **Check:** Try importing OuraAdapter
   ```python
   from Adapters.oura_adapter import OuraAdapter
   adapter = OuraAdapter()
   # Will fail if not configured
   ```
   - **Solution:** Configure Oura MCP or wait for real data

2. **Insufficient Paired Data**
   - Need minimum 10 days with BOTH task completions AND health metrics
   - **Check:** Validate data overlap
   - **Solution:** Continue using system daily

3. **No Statistical Correlation**
   - Your sleep/productivity may genuinely not correlate (uncommon)
   - **Solution:** Lower CORRELATION_THRESHOLD from 0.3 to 0.2

**Debug Steps:**
```python
# Check health data availability
from Tools.pattern_recognition.data_aggregator import DataAggregator
aggregator = DataAggregator()
data = await aggregator.aggregate_data(...)

print(f"Health metrics: {len(data.health_metrics)}")
for metric in data.health_metrics[:5]:
    print(f"  {metric.date}: Sleep {metric.total_sleep_duration}h, Readiness {metric.readiness_score}")
```

**Workaround:**
- Health correlations validated with synthetic data
- Will work automatically once Oura data flows in
- Use task patterns and habits in the meantime

#### Issue 4: Low Confidence Scores

**Symptoms:**
- Patterns detected but all have confidence <60%
- Insights filtered out by min_confidence threshold

**Possible Causes:**

1. **Small Sample Size**
   - Not enough data points for high confidence
   - **Solution:** Wait for more data or lower min_samples

2. **High Variance**
   - Inconsistent patterns (e.g., productive at different times each day)
   - **Solution:** This is informational - your schedule is variable
   - **Adjustment:** Lower min_confidence to see patterns anyway

3. **Noisy Data**
   - Data quality issues or outliers
   - **Solution:** Check for data anomalies

**Debug Steps:**
```bash
# See all patterns regardless of confidence
python -m commands.pa.patterns analyze --confidence=0.0

# Check sample sizes in pattern descriptions
python -m commands.pa.patterns list

# Look for patterns with confidence 0.4-0.6 (moderate)
python -m commands.pa.patterns analyze --confidence=0.4 --compact
```

**Remediation:**
- If consistent low confidence: Lower thresholds in analyzer code
- If specific pattern type: Adjust that analyzer's min_confidence
- If waiting for data: Be patient, confidence will improve over time

#### Issue 5: Repetitive Insights Week-to-Week

**Symptoms:**
- Same insights appear in consecutive weekly reviews
- Novelty scoring not working

**Possible Causes:**

1. **Dominant Patterns**
   - One pattern is so strong it always ranks #1
   - **Solution:** This may be legitimate - it's an important pattern!
   - **Adjustment:** Increase novelty weight from 0.10 to 0.15

2. **No Recent Patterns Stored**
   - Novelty comparison requires previous insights in Neo4j
   - **Check:** Query stored insights
   ```bash
   python -m commands.pa.patterns show --category=insight
   ```
   - **Solution:** Ensure pattern_storage is working

3. **Novelty Penalties Too Small**
   - Default penalties (-0.10 to -0.20) may not be enough
   - **Adjustment:** Increase NOVELTY_PENALTY values

**Remediation:**
```python
# In insight_generator.py, adjust novelty scoring:
NOVELTY_PENALTY_EXACT = -0.30  # Was -0.20
NOVELTY_PENALTY_HIGH_SIMILARITY = -0.25  # Was -0.15

# Or increase novelty weight in scoring
SCORING_WEIGHTS = {
    "novelty": 0.15,  # Was 0.10
    "significance": 0.23,  # Adjust down
    # ...
}
```

#### Issue 6: Neo4j Storage Failures

**Symptoms:**
```
⚠️ Failed to retrieve patterns: Connection refused
⚠️ Neo4j adapter not available
```

**Possible Causes:**

1. **Neo4j Not Running**
   - **Check:** `docker ps | grep neo4j` or Neo4j Desktop
   - **Solution:** Start Neo4j service

2. **Connection Configuration**
   - Wrong URI, username, or password
   - **Check:** `Adapters/neo4j_adapter.py` configuration
   - **Solution:** Update credentials

3. **Import Error**
   - Missing dependencies
   - **Solution:** `pip install neo4j`

**Workaround:**
- Pattern recognition works without storage
- Insights generated fresh each run
- Persona integration unavailable until Neo4j working

**Debug Steps:**
```python
# Test Neo4j connection directly
from Adapters.neo4j_adapter import get_adapter
adapter = get_adapter()
# Should connect without error
```

### Performance Issues

#### Slow Analysis (>30 seconds)

**Causes:**
- Large data sets (90+ days, 1000+ tasks)
- Multiple analyzer runs

**Solutions:**
1. **Reduce analysis window:** `--days=30` instead of `--days=90`
2. **Use compact display:** `--compact` skips detailed formatting
3. **Query storage instead:** `show` mode retrieves cached patterns
4. **Run weekly, not daily:** Pattern recognition is designed for weekly cadence

#### Memory Issues

**Symptoms:**
- Process killed during analysis
- Out of memory errors

**Solutions:**
1. **Reduce `days_back`:** Analyze shorter periods
2. **Batch processing:** Analyze categories separately
3. **Clear cache:** Restart Python session between runs

### Data Quality Issues

#### Inconsistent Pattern Detection

**Symptoms:**
- Pattern detected one week, gone the next
- Confidence scores fluctuate wildly

**Causes:**
- Irregular usage patterns
- Missing data on certain days
- Outlier days (vacations, sick days)

**Solutions:**
1. **Filter outliers:** Remove vacation days before analysis
2. **Increase min_samples:** Require more data for robustness
3. **Use longer windows:** 60-90 days smooths out noise
4. **Accept variability:** Life isn't perfectly consistent!

#### Wrong Patterns Detected

**Symptoms:**
- Insight suggests incorrect times or behaviors
- Correlation doesn't match experience

**Causes:**
- Spurious correlations (coincidence, not causation)
- Confounding variables
- Data entry errors

**Solutions:**
1. **Check data quality:** Validate task completion records
2. **Increase confidence threshold:** Filter weaker patterns
3. **Cross-reference evidence:** Review supporting data points
4. **Trust your judgment:** Insights are suggestions, not commands

### Getting Help

**Diagnostic Command:**
```bash
# Run comprehensive diagnostic
python -m commands.pa.patterns analyze --days=90 --confidence=0.3 > debug.txt
cat debug.txt
```

**Log Locations:**
- Pattern recognition output: Printed to stdout
- DataAggregator logs: Check for "Loading data from..." messages
- Errors: Captured in traceback

**Information to Include When Reporting Issues:**
1. Output of diagnostic command above
2. Data availability: `ls History/Sessions/ | wc -l`
3. Configuration changes made
4. Expected vs actual behavior

---

## Advanced Topics

### Custom Pattern Types

You can extend the system with custom analyzers:

**Template:**
```python
# Tools/pattern_recognition/analyzers/custom_analyzer.py

from ..models import CustomPattern
from ..time_series import TaskCompletionRecord

def analyze_custom_pattern(
    task_records: List[TaskCompletionRecord],
    min_samples: int = 5,
    min_confidence: float = 0.65
) -> List[CustomPattern]:
    """Analyze custom pattern type."""

    # 1. Aggregate data
    # 2. Calculate statistics
    # 3. Detect patterns
    # 4. Score confidence
    # 5. Return pattern objects

    return patterns
```

**Integration:**
```python
# Update __init__.py
from .analyzers.custom_analyzer import analyze_custom_pattern

# Use in weekly review
custom_patterns = analyze_custom_pattern(task_records)
```

### Persona Integration

Pattern insights are available to persona agents via query interface:

**Example Usage:**
```python
from Tools.pattern_recognition.pattern_queries import get_pattern_context_for_persona

# Get comprehensive context for decision-making
context = await get_pattern_context_for_persona(
    neo4j_adapter,
    focus_area="productivity",  # Or "sleep", "habits", etc.
    days_back=30
)

# Context includes:
# - Recent task patterns
# - Health correlations
# - Active habit streaks
# - Current trends

# Use in persona prompts
prompt = f"""
Based on the user's patterns:
{context}

Recommend optimal task scheduling for today.
"""
```

### A/B Testing Configurations

To scientifically test configuration changes:

1. **Baseline Measurement** (Week 1)
   ```bash
   python -m commands.pa.patterns analyze --days=30 > baseline.txt
   ```
   Record: Pattern count, avg confidence, category distribution

2. **Apply Configuration Change** (Week 2)
   - Modify threshold or weight
   - Document change in PATTERN_RECOGNITION_TUNING.md

3. **Measure Impact** (Week 2)
   ```bash
   python -m commands.pa.patterns analyze --days=30 > modified.txt
   ```

4. **Compare Metrics**
   ```bash
   diff baseline.txt modified.txt
   ```
   - Pattern count change?
   - Confidence distribution change?
   - More/fewer actionable insights?

5. **Iterate or Revert**
   - Keep if improvement
   - Revert if degradation
   - Try different value if inconclusive

### Exporting for External Analysis

**CSV Export (Manual):**
```python
from Tools.pattern_recognition.data_aggregator import DataAggregator
from datetime import datetime, timedelta
import csv

aggregator = DataAggregator()
data = await aggregator.aggregate_data(
    start_date=datetime.now().date() - timedelta(days=90),
    end_date=datetime.now().date()
)

# Export to CSV
with open('tasks.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['date', 'title', 'domain', 'completed'])
    for task in data.task_completions:
        writer.writerow([task.completed_date, task.title, task.domain, True])
```

**JSON Export:**
```python
import json

patterns = await get_all_task_patterns(task_records)

with open('patterns.json', 'w') as f:
    json.dump([
        {
            'type': str(p.pattern_type),
            'description': p.description,
            'confidence': p.confidence_score,
            'evidence': p.evidence
        }
        for p in patterns
    ], f, indent=2)
```

### Visualization Integration

For future graphical visualizations, data is ready for:

- **Time series plots:** Task completion over time
- **Heatmaps:** Hour-of-day × day-of-week productivity
- **Correlation matrices:** Health metrics × productivity
- **Trend charts:** 90-day smoothed averages

**Data Export for Plotting:**
```python
# Export time series data
from Tools.pattern_recognition.time_series import TimeSeriesAggregator

aggregator = TimeSeriesAggregator()
daily_data = aggregator.aggregate_by_period(task_records, 'daily')

# daily_data.data_points is ready for matplotlib, plotly, etc.
```

---

## Appendix

### Related Documentation

- **[PATTERN_RECOGNITION_TUNING.md](./PATTERN_RECOGNITION_TUNING.md)**: Detailed tuning guide with validation results
- **[VALIDATION_SUMMARY.md](./VALIDATION_SUMMARY.md)**: Real data validation report and test results
- **[PATTERN_STORAGE_README.md](../Tools/pattern_recognition/PATTERN_STORAGE_README.md)**: Neo4j storage integration
- **[PATTERN_QUERIES_README.md](../Tools/pattern_recognition/PATTERN_QUERIES_README.md)**: Query interface for persona agents

### Algorithm References

**Statistical Methods:**
- Pearson Correlation: Standard implementation for linear correlation
- Linear Regression: Least squares method for trend detection
- Confidence Scoring: Multi-factor weighted model

**Inspiration:**
- Time series analysis: Moving averages, seasonality detection
- Behavioral science: Habit formation research (streak psychology)
- Quantified self: Personal analytics best practices

### Glossary

**Confidence Score**: Statistical measure of pattern reliability (0.0-1.0)
**Effect Size**: Magnitude of impact (e.g., +40% productivity)
**Evidence**: Supporting data points that validate a pattern
**Insight**: Actionable recommendation derived from patterns
**Pattern**: Recurring statistical regularity in data
**Recency Scoring**: Exponential decay favoring recent patterns
**Threshold**: Minimum value required for pattern detection
**Time Series**: Sequential data points ordered by time

### Version History

- **v1.0** (2026-01-11): Initial documentation
  - Comprehensive algorithms overview
  - CLI usage guide
  - Troubleshooting section
  - Configuration reference
  - Integration with weekly review

---

**Questions or Issues?**
Consult the troubleshooting section or review validation documentation in `docs/VALIDATION_SUMMARY.md`.

**Contributing:**
Configuration improvements and tuning findings should be documented in `docs/PATTERN_RECOGNITION_TUNING.md`.
