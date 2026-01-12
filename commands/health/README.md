# Health Commands

A suite of health monitoring commands for tracking wellness metrics using Oura Ring data integration.

## Quick Start

```bash
# Generate health summary
python -m commands.health.summary

# Generate enhanced summary with LLM insights
python -m commands.health.summary --llm-enhance

# Include 7-day trend analysis
python -m commands.health.summary --trends

# Combined: trends + LLM enhancement
python -m commands.health.summary --trends --llm-enhance
```

## Available Commands

| Command | Purpose | Quick Usage |
|---------|---------|-------------|
| `summary` | Health metrics dashboard | `python -m commands.health.summary --llm-enhance` |

### health:summary

Generates a comprehensive health metrics dashboard combining Oura Ring data (readiness, sleep, stress) into a unified health snapshot with insights and recommendations.

**Features:**
- 📊 Real-time Oura Ring data integration
- 💡 Evidence-based health insights
- 🎯 Actionable, prioritized recommendations
- 🧠 ADHD-friendly formatting with emojis and clear structure
- 💾 Auto-saves to History/HealthSummaries/
- ✨ Optional LLM enhancement for personalized insights

## Setup Requirements

### 1. Oura Ring Account

You must have an Oura Ring and active account with data.

### 2. Configure Oura Access Token

Set your Oura Personal Access Token:

```bash
# Add to your environment variables
export OURA_PERSONAL_ACCESS_TOKEN="your_token_here"

# Or add to your .env file
OURA_PERSONAL_ACCESS_TOKEN=your_token_here
```

**Get your token:**
1. Visit https://cloud.ouraring.com/personal-access-tokens
2. Create a new Personal Access Token
3. Copy and save it securely

### 3. Dependencies

The command uses:
- `OuraAdapter` from `Tools.adapters.oura`
- `litellm_client` for optional LLM enhancement (requires OpenAI/compatible API key)

## Usage Examples

### Basic Health Summary

```bash
python -m commands.health.summary
```

**Output includes:**
- Overall health status
- Readiness score (with contributors: sleep balance, HRV, recovery, etc.)
- Sleep metrics (duration, efficiency, stages: REM/Deep/Light)
- Stress levels (daytime balance, recovery time)
- Activity score (if available)
- Health insights (evidence-based observations)
- Recommendations (actionable, prioritized advice)

### Enhanced Summary with LLM

```bash
python -m commands.health.summary --llm-enhance
```

Adds personalized insights using GPT-4o-mini:
- Pattern detection across metrics
- Personalized recommendations based on your profile
- Correlation analysis between health factors
- More detailed explanations

### 7-Day Trends Analysis

```bash
python -m commands.health.summary --trends
```

Adds weekly trend visualization showing:
- Average readiness and sleep scores over 7 days
- Min/max ranges for each metric
- Trend direction (improving/declining/stable)
- Pattern detection (e.g., declining recovery, improving sleep)
- Weekly insights and recommendations

**Combined usage:**
```bash
python -m commands.health.summary --trends --llm-enhance
```

This combines trend analysis with personalized LLM insights for maximum context.

## Output Format

### Dashboard Structure

```markdown
# 💚 Health Dashboard - 2026-01-11

## 🟢 Overall Status: Excellent

## 📊 Key Metrics

### 🟢 Readiness: 88/100
**Top Contributors:**
- 🟢 Sleep Balance: 92/100
- 🟢 Previous Day Activity: 85/100
- 🟡 Activity Balance: 78/100
- 🟢 HRV Balance: 89/100
- 🟢 Recovery Index: 91/100

### 🟢 Sleep: 86/100 (8h 0m)
**Sleep Breakdown:**
- Efficiency: 92%
- REM: 2h 0m
- Deep: 1h 36m
- Light: 4h 24m
- Time to Sleep: 8m
- Restless Periods: 8

### 🟢 Stress: Restored
**Daytime Balance:**
- Recovery Time: 6h 30m (65%)
- Stress Time: 3h 30m (35%)

## 💡 Health Insights
- 💪 Body is well-recovered and ready for challenging activities
- 💓 Excellent HRV - strong stress resilience
- ✅ Sleep duration is in optimal range (8-9h)
- ✅ Excellent sleep efficiency (92%)
- ✅ Strong REM sleep (25%)
- ✅ Good deep sleep (20%)
- ✅ Well-managed stress - good balance of activity and recovery
- 🔄 Good recovery time - stress is well-managed

## 🎯 Recommendations
1. 💪 Great recovery state - good day for challenging work or training
```

### Trends Output (--trends flag)

When using `--trends`, an additional section is appended:

```markdown
## 📊 7-Day Trends

**Readiness** 📈
- Average: 82.3 (🟡)
- Range: 72 - 91
- Trend: Improving

**Sleep** ➡️
- Average: 78.5 (🟡)
- Range: 68 - 86
- Trend: Stable

**Patterns Detected:**
- ✅ Positive trend: Both sleep and recovery improving
- 📊 Metrics stable across the week
```

**Trend Direction Indicators:**
- 📈 Improving: Second half of week shows >5% improvement
- 📉 Declining: Second half of week shows >5% decline
- ➡️ Stable: Variation less than 5%

### Status Indicators

**Scores:**
- 🟢 Green (85-100): Excellent
- 🟡 Yellow (70-84): Good
- 🟠 Orange (55-69): Fair
- 🔴 Red (<55): Poor
- ⚪ White: No data

**Stress Levels:**
- 🟢 Restored: Well-managed
- 🟡 Normal: Balanced
- 🔴 Stressed/High: Elevated

## History Files

Each summary is automatically saved to:
```
History/HealthSummaries/health_YYYY-MM-DD.md
```

**Features:**
- Daily file (overwrites if run multiple times per day)
- Includes timestamp of generation
- Full markdown formatting preserved
- Searchable health history

## Integration Notes

### With Personal Assistant Commands

```bash
# Morning routine
python -m commands.health.summary
python -m commands.pa.daily

# Check health before scheduling workouts
python -m commands.health.summary
# If readiness high: schedule intensive work
# If readiness low: plan recovery activities
```

### With Health Agent

The Health agent (`Agents/Health.md`) references health data. Use this command for:
- Quick health status checks
- Morning health assessment
- Pre-workout readiness verification
- Recovery monitoring

### API Integration

The command uses `OuraAdapter.get_today_health()` which provides:
- `readiness`: Recovery and readiness data
- `sleep`: Sleep score and detailed stages
- `stress`: Daytime stress and recovery balance
- `activity`: Activity score and movement data
- `summary`: Overall health status

## Customization

### Modify Analysis Logic

Edit `commands/health/summary.py` to customize:

**Insight Generation:**
- `_analyze_sleep_quality()`: Sleep analysis rules
- `_analyze_readiness()`: Readiness interpretation
- `_analyze_stress()`: Stress pattern detection

**Recommendations:**
- `_generate_recommendations()`: Recommendation logic and prioritization

**Formatting:**
- `format_health_summary()`: Dashboard structure and layout
- `_get_status_emoji()`: Score thresholds
- `_format_duration()`: Time formatting

### LLM Enhancement

Edit the `SYSTEM_PROMPT` to customize the LLM persona:
- Adjust tone (supportive, analytical, motivational)
- Add context about your lifestyle
- Modify recommendation style
- Change output format preferences

## Troubleshooting

### "No Oura access token configured"

**Solution:** Set the `OURA_PERSONAL_ACCESS_TOKEN` environment variable.

```bash
# Check if token is set
echo $OURA_PERSONAL_ACCESS_TOKEN

# Set temporarily
export OURA_PERSONAL_ACCESS_TOKEN="your_token_here"

# Set permanently (add to ~/.bashrc, ~/.zshrc, or .env)
echo 'export OURA_PERSONAL_ACCESS_TOKEN="your_token_here"' >> ~/.zshrc
```

### "Failed to fetch health data"

**Common causes:**
1. Invalid or expired access token
2. Oura API rate limit exceeded
3. No internet connection
4. Oura Ring has no data for today yet

**Solution:** Check Oura Cloud dashboard to verify data is available.

### Missing data in output

**Why:** Oura Ring may not have collected all metrics yet.

**When data is available:**
- Readiness: Available after waking up (requires previous night's sleep)
- Sleep: Available after sync following sleep
- Stress: Updates throughout the day
- Activity: Real-time during the day

**Solution:** Run the command later in the day, or after syncing your ring.

### LLM enhancement not working

**Common causes:**
1. No OpenAI API key configured
2. `litellm_client` not set up
3. Model unavailable

**Solution:** Verify `Tools/litellm_client.py` configuration and API credentials.

### History files not saving

**Cause:** Missing write permissions.

**Solution:** Ensure `History/HealthSummaries/` directory is writable.

```bash
# Check permissions
ls -ld History/HealthSummaries/

# Fix permissions if needed
chmod -R u+w History/HealthSummaries/
```

## Command Patterns

### Daily Health Check

```bash
# Morning: Check recovery status
python -m commands.health.summary

# Before workout: Verify readiness
python -m commands.health.summary | grep "Readiness"

# Evening: Review day's metrics with trends
python -m commands.health.summary --trends
```

### Weekly Review

```bash
# Monday morning: Check weekly trends
python -m commands.health.summary --trends --llm-enhance

# Review health history files
ls -lt History/HealthSummaries/ | head -7
cat History/HealthSummaries/health_*.md

# Compare readiness scores across week
grep "Readiness:" History/HealthSummaries/health_*.md
```

### Integration with Workflows

```bash
# Morning briefing with health check
python -m commands.health.summary > /tmp/health.md
python -m commands.pa.daily

# Health-aware task planning
READINESS=$(python -m commands.health.summary | grep -oP 'Readiness: \K\d+')
if [ $READINESS -ge 85 ]; then
  echo "High energy day - schedule challenging tasks"
else
  echo "Recovery day - focus on maintenance tasks"
fi
```

## Advanced Usage

### Piping and Filtering

```bash
# Extract just the score
python -m commands.health.summary | grep "Readiness:"

# Check if recommendations include rest
python -m commands.health.summary | grep -i "recovery\|rest"

# Save to custom location
python -m commands.health.summary > ~/my_health_$(date +%Y-%m-%d).md
```

### Scheduling with Cron

```bash
# Add to crontab (run at 8 AM daily)
0 8 * * * cd /path/to/thanos && python -m commands.health.summary

# With email notification
0 8 * * * cd /path/to/thanos && python -m commands.health.summary | mail -s "Health Summary" you@example.com
```

### API Integration

```python
# Use programmatically
from commands.health.summary import execute
import asyncio

async def check_health():
    summary = await execute(use_llm_enhancement=False)
    # Process summary string
    return summary

asyncio.run(check_health())
```

## Technical Details

### Data Sources

**OuraAdapter Methods:**
- `get_today_health()`: Complete health snapshot (used for daily summary)
- `get_daily_summary()`: Multi-day data retrieval (used for --trends)
- `get_daily_readiness()`: Detailed readiness data
- `get_daily_sleep()`: Detailed sleep analysis
- `get_daily_stress()`: Stress and recovery metrics

### Models Used

- **LLM Enhancement:** GPT-4o-mini (cost-effective for simple analysis)
- **Temperature:** 0.7 (balanced creativity and consistency)

### Trends Calculation

**Trend Direction Algorithm:**
- Compares first half of week to second half
- **Improving:** Second half average is >5% higher
- **Declining:** Second half average is >5% lower
- **Stable:** Variation is ≤5%

**Pattern Detection:**
- Identifies correlated trends (both sleep and readiness declining)
- Detects specific issues (readiness declining while sleep stable)
- Flags below-optimal averages (<70 for week)
- Provides context-specific recommendations

**Data Range:**
- Fetches last 7 days (including today)
- Calculates min, max, and average for each metric
- Handles missing days gracefully

### File Locations

```
commands/health/
├── __init__.py           # Namespace initialization
├── summary.py            # Main command implementation
└── README.md            # This file

History/HealthSummaries/
└── health_YYYY-MM-DD.md # Daily summaries

tests/unit/
└── test_commands_health.py  # Unit tests (67 tests)
```

## Testing

### Unit Tests

```bash
# Run all health command tests
pytest tests/unit/test_commands_health.py -v

# Run specific test
pytest tests/unit/test_commands_health.py::test_fetch_health_data -v

# Check coverage
pytest tests/unit/test_commands_health.py --cov=commands.health
```

### Manual Testing

See `.auto-claude/specs/005-add-health-metrics-summary-command/manual-testing-guide.md` for comprehensive test scenarios and results.

## Future Enhancements

Potential additions for future development:

1. **Comparison Mode:** Compare to previous days/weeks/months
2. **Goal Tracking:** Track progress toward health goals
3. **Alerts:** Notify when metrics fall below thresholds
4. **Export Formats:** JSON, CSV for data analysis
5. **Charts:** ASCII or image-based visualizations
6. **Advanced Correlations:** Correlate health metrics with productivity, mood, etc.
7. **Integration with Health Agent:** Automatic recommendations for daily planning

## Related Documentation

- **Spec:** `.auto-claude/specs/005-add-health-metrics-summary-command/spec.md`
- **Implementation Plan:** `.auto-claude/specs/005-add-health-metrics-summary-command/implementation_plan.json`
- **Testing Guide:** `.auto-claude/specs/005-add-health-metrics-summary-command/manual-testing-guide.md`
- **Oura Adapter:** `Tools/adapters/oura.py`
- **Main Commands:** `COMMANDS.md`

## Support

For issues or questions:
1. Check Troubleshooting section above
2. Review test files for examples
3. Check Oura API status: https://cloud.ouraring.com/docs/
4. Verify adapter functionality: `python -m Tools.adapters.oura`

---

**Version:** 1.1.0
**Last Updated:** January 12, 2026
**Status:** Production Ready ✅
**New in v1.1.0:** 7-day trends analysis with `--trends` flag
