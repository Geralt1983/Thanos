# Health Commands

A suite of health monitoring commands for tracking wellness metrics using Oura Ring data integration.

## Quick Start

```bash
# Generate health summary
python -m commands.health.summary

# Generate enhanced summary with LLM insights
python -m commands.health.summary --llm-enhance
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

# Evening: Review day's metrics
python -m commands.health.summary
```

### Weekly Review

```bash
# Review health trends
ls -lt History/HealthSummaries/ | head -7
cat History/HealthSummaries/health_*.md

# Compare readiness scores
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
- `get_today_health()`: Complete health snapshot (used by this command)
- `get_daily_readiness()`: Detailed readiness data
- `get_daily_sleep()`: Detailed sleep analysis
- `get_daily_stress()`: Stress and recovery metrics
- `get_weekly_trends()`: 7-day trend data (future enhancement)

### Models Used

- **LLM Enhancement:** GPT-4o-mini (cost-effective for simple analysis)
- **Temperature:** 0.7 (balanced creativity and consistency)

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

Potential additions (currently optional):

1. **Weekly Trends:** Show 7-day trend visualizations
2. **Comparison Mode:** Compare to previous days/weeks
3. **Goal Tracking:** Track progress toward health goals
4. **Alerts:** Notify when metrics fall below thresholds
5. **Export Formats:** JSON, CSV for data analysis
6. **Charts:** ASCII or image-based visualizations

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

**Version:** 1.0.0
**Last Updated:** January 11, 2026
**Status:** Production Ready ✅
