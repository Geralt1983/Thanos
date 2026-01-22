# pa:daily

Generate comprehensive morning briefing to start the day with clarity and focus.

## Workflow

Execute the following steps to generate the daily briefing:

### Step 1: Get Weather
Get current weather for King, NC using OpenWeatherMap:
```
Use mcp__openweathermap__get_current_weather with location="King,NC,US"
```

### Step 2: Get Oura Readiness Data
Check current energy/readiness using Oura ring data:
```
Use mcp__oura__get_daily_readiness with today's date for startDate and endDate
```

### Step 3: Get WorkOS Daily Summary
Fetch the comprehensive daily summary from WorkOS:
```
Use mcp__workos__workos_daily_summary()
```

### Step 4: Get Habits Due
Check morning habits that need attention:
```
Use mcp__workos__workos_habit_checkin(timeOfDay='morning')
```

### Step 5: Format Output

Present the briefing in Thanos format:

```markdown
### DESTINY // [TIME]
[Time of day message based on hour]

---

**WEATHER:** [temp]°F, [conditions] | Feels like [feels_like]°F
[Wind info if notable]

---

**READINESS: [SCORE]** — [Energy assessment]

| Contributor | Score |
|-------------|-------|
| [Key metrics from Oura contributors] |

---

**PROGRESS: [earned] / [target] points**
```
[progress bar visualization]
```

---

**TODAY'S SACRIFICES** ([total] pts queued)

| # | Task | Client | Pts |
|---|------|--------|-----|
| [Active tasks with client and value] |

---

**RITUALS AWAITING**
[Habits due for check-in with emoji]

---

**RECOMMENDATION:** [Single actionable focus recommendation based on energy, weather, and priorities]

The universe awaits your command.
```

## Parameters
- `focus` (optional): Specific area to emphasize (work | personal | epic | all)
- `--quick`: Abbreviated 2-minute version
- `--verbose`: Include full details

## Examples
```bash
# Standard morning briefing
/pa:daily

# Focus on Epic work
/pa:daily epic

# Quick version
/pa:daily --quick
```

## Integration Points
- OpenWeatherMap (weather, air quality, alerts)
- Oura Ring (readiness, sleep data)
- WorkOS MCP (tasks, habits, energy)
- State files (CurrentFocus.md, Commitments.md)
