# Usage Examples - Oura Health Metrics MCP Server

This guide provides practical examples of using the Oura MCP server with Claude Desktop and other AI assistants.

## Table of Contents

- [Getting Started](#getting-started)
- [Basic Health Queries](#basic-health-queries)
- [Advanced Analysis](#advanced-analysis)
- [Health-Aware Task Management](#health-aware-task-management)
- [Pattern Recognition](#pattern-recognition)
- [Workout Planning](#workout-planning)
- [API Usage Examples](#api-usage-examples)

## Getting Started

Make sure you've completed the [setup](./SETUP.md) and your Oura MCP server is connected to Claude Desktop.

### Verify Connection

First, verify the server is working:

**Prompt:**
```
Run the oura_health_check tool
```

**Expected Response:**
```
Your Oura MCP server is healthy! Here's the status:

Overall Status: ✅ Healthy

API Status:
- Connected to Oura API
- Response time: 245ms
- Rate limit: 4,892 / 5,000 requests remaining

Cache Status:
- 127 total entries
- Readiness: 45 entries
- Sleep: 42 entries
- Activity: 40 entries
- Last sync: 2026-01-11
- Today's data: ✅ Available

Recommendations:
✅ System is healthy and ready. Today's data is available.
```

## Basic Health Queries

### Check Today's Readiness

**Prompt:**
```
What's my readiness score today?
```

**What Claude sees:**
```json
{
  "date": "2026-01-11",
  "score": 85,
  "interpretation": "Good - Ready for moderate activity",
  "contributors": {
    "sleep_score": { "score": 88, "meaning": "Good sleep quality" },
    "hrv_balance": { "score": 92, "meaning": "Excellent recovery" }
  }
}
```

**Claude's Response:**
```
Your readiness score today is 85 - that's in the "Good" range!

This means you're ready for moderate activity. Your body shows excellent
recovery with an HRV balance score of 92, and you had good sleep quality
(score: 88). Your resting heart rate is 52 bpm and HRV is 55ms, both
indicating good cardiovascular recovery.

You're in great shape for a productive day!
```

### Check Last Night's Sleep

**Prompt:**
```
How did I sleep last night?
```

**Claude's Response:**
```
You had a good night's sleep! Here's the breakdown:

Sleep Score: 82 (Good - Quality restorative sleep)

Duration:
- Total: 7h 15m
- REM: 1h 45m (24%)
- Deep: 1h 30m (21%)
- Light: 4h 0m (55%)

Sleep Efficiency: 91% - Excellent! You spent minimal time awake.

Key Metrics:
- You fell asleep quickly (latency score: 90)
- Good sleep timing
- Heart rate average: 48 bpm
- HRV: 62ms
- Respiratory rate: 14 breaths/min

Overall, you got quality restorative sleep with good REM and deep sleep
percentages. This should set you up well for the day ahead!
```

### View Weekly Trends

**Prompt:**
```
Show me my health trends for the past week
```

**Claude's Response:**
```
Here are your health trends for the past 7 days (Jan 4-10, 2026):

📈 READINESS (Average: 82)
- Trend: Improving (+15.3%)
- Range: 68 → 92
- Pattern: Steady improvement throughout the week

😴 SLEEP (Average: 79)
- Trend: Stable (+2.1%)
- Range: 65 → 88
- Pattern: Consistent sleep quality with minor fluctuations

🏃 ACTIVITY (Average: 75)
- Trend: Declining (-8.2%)
- Range: 85 → 60
- Pattern: Decreased activity levels

KEY INSIGHTS:
⚠️ Your activity has declined while readiness is improving - this suggests
good recovery balance. You're letting your body recover properly.

✅ Sleep quality is stable with consistent scores - good sleep hygiene!

✅ Readiness improving significantly (+15.3%) - your body is recovering well.
```

## Advanced Analysis

### Sleep Pattern Analysis

**Prompt:**
```
Analyze my sleep patterns over the past two weeks. What trends do you see?
```

**Claude will:**
1. Use `oura_get_weekly_trends` with `days: 14`
2. Analyze sleep scores, durations, and efficiency
3. Identify patterns in REM/deep sleep
4. Provide actionable insights

### Recovery Assessment

**Prompt:**
```
Based on my readiness and HRV, am I recovered enough for a hard workout today?
```

**Claude's Analysis:**
```
Let me check your recovery status...

[Calls oura_get_today_readiness]

Based on your metrics:
- Readiness: 85 (Good)
- HRV: 55ms (within your normal range)
- HRV Balance: 92 (Excellent)
- Sleep Quality: 88 (Good)
- Resting HR: 52 bpm (Good)

RECOMMENDATION: ✅ YES - You're well-recovered for a hard workout

Your excellent HRV balance (92) and good readiness (85) indicate your body
has recovered well. However, consider:

1. Warm up thoroughly given your body temperature is slightly elevated
2. Stay hydrated
3. Monitor how you feel - if energy is low, scale back intensity
4. Your activity balance (78) suggests moderate recent activity, so you're
   not overtrained

Go for it, but listen to your body during the session!
```

### Energy Level Prediction

**Prompt:**
```
When will my energy likely be highest today based on my circadian rhythm and readiness?
```

**Claude's Response:**
```
Based on your Oura data and circadian science:

Current Readiness: 85
Sleep Quality: 82
Sleep Timing: Bedtime 22:30, Wake 06:15

PREDICTED ENERGY LEVELS:

🌅 Morning (6:00-10:00): ⭐⭐⭐⭐⭐ PEAK
- You're a natural early riser (bedtime at 22:30)
- Good sleep quality supports morning alertness
- High readiness means you woke up recovered
- Best time for: Complex tasks, workouts, creative work

☀️ Midday (10:00-14:00): ⭐⭐⭐⭐
- Sustained good energy
- Best time for: Meetings, collaboration, execution

🌤️ Afternoon (14:00-17:00): ⭐⭐⭐
- Natural circadian dip
- Best time for: Routine tasks, admin work

🌙 Evening (17:00-22:00): ⭐⭐⭐
- Moderate energy
- Best time for: Light exercise, planning, reflection

RECOMMENDATION: Schedule your most important work between 7:00-11:00 AM when
your cognitive performance will peak.
```

## Health-Aware Task Management

### Task Prioritization

**Prompt:**
```
I have these tasks today:
1. Write quarterly strategy document (3 hours, high mental effort)
2. Review team pull requests (1 hour, moderate effort)
3. Team standup meeting (30 min, low effort)
4. Gym workout (1 hour, high physical effort)
5. Answer emails (1 hour, low effort)

Based on my readiness and energy, how should I prioritize these?
```

**Claude's Recommendation:**
```
Based on your readiness score of 85 and good sleep (82), here's your
optimized schedule:

MORNING (7:00-11:00) - Peak Energy 🌅
1. Write quarterly strategy document (7:00-10:00)
   → High readiness + morning peak = best time for complex cognitive work
   → Your HRV (55ms) shows good mental clarity

2. Gym workout (10:00-11:00)
   → High readiness (85) = good recovery for hard workout
   → Excellent HRV balance (92) = safe to train hard
   → Before lunch = optimal for performance

MIDDAY (11:00-14:00) ☀️
3. Team standup meeting (11:00-11:30)
   → Post-workout, still high energy

4. Review team pull requests (11:30-12:30)
   → Good focus, less mentally taxing than strategy work

AFTERNOON (14:00-17:00) 🌤️
5. Answer emails (14:00-15:00)
   → Circadian dip = good for routine tasks
   → Low cognitive load

REASONING:
✅ Complex work first when cortisol and readiness are highest
✅ Workout when recovered but before depleting mental energy
✅ Routine tasks during natural energy dip
✅ Your sleep timing (22:30-06:15) aligns with this schedule

This schedule optimizes for both your biological readiness AND circadian rhythm!
```

### Low Readiness Day Planning

**Prompt:**
```
My readiness is only 62 today. How should I adjust my plans?
```

**Claude's Advice:**
```
With a readiness of 62 (Pay Attention range), your body is asking for recovery.
Let me check what's contributing...

[Calls oura_get_today_readiness]

Low contributors:
- Sleep Score: 58 (Poor)
- HRV Balance: 45 (Low)
- Activity Balance: 40 (Needs recovery)

RECOMMENDED ADJUSTMENTS:

❌ SKIP OR POSTPONE:
- High-intensity workouts (do light yoga/walk instead)
- Long, complex meetings
- Starting new, challenging projects
- Late nights or social obligations

✅ PRIORITIZE:
- Recovery: Extra sleep, naps if possible
- Light movement: 20-30 min walk
- Routine, familiar tasks you can do on autopilot
- Hydration and nutrition
- Stress reduction techniques

📅 SCHEDULE RESTRUCTURING:
- Move critical meetings to later in the week
- Focus on administrative tasks today
- Delegate complex work if possible
- Plan for an earlier bedtime tonight (aim for 9:30 PM)

🎯 GOAL FOR TODAY:
Your only job is to recover. Your readiness will bounce back if you rest properly.
One recovery day now prevents three sick days later!
```

## Pattern Recognition

### Sleep Quality Correlation

**Prompt:**
```
Is there a correlation between my activity levels and sleep quality over the past two weeks?
```

**Claude's Analysis:**
```
Let me analyze 14 days of data...

[Calls oura_get_weekly_trends with days: 14]

FINDINGS:

📊 CORRELATION ANALYSIS:
- Days with Activity 75+: Sleep average = 82
- Days with Activity 60-75: Sleep average = 79
- Days with Activity <60: Sleep average = 72

✅ POSITIVE CORRELATION DETECTED

Your sleep quality improves on days with moderate-to-high activity (75+):
- Better sleep efficiency (avg 89% vs 82%)
- More deep sleep (avg 95 min vs 78 min)
- Higher sleep scores

⚠️ INTERESTING PATTERN:
- Days with very high activity (>90): Sleep slightly disrupted
- Sweet spot: Activity score 75-85

RECOMMENDATIONS:
1. Aim for consistent moderate activity (target: 75-85)
2. Avoid very high intensity late in the day
3. Your best sleep follows days with morning/midday exercise
4. Rest days (<60 activity) correlate with poorer sleep - light activity helps!

The data suggests regular moderate exercise is key to your sleep quality!
```

### Stress Recovery Patterns

**Prompt:**
```
How long does it typically take me to recover after a high-stress week?
```

**Claude's Analysis:**
```
Analyzing your recovery patterns...

[Calls oura_get_weekly_trends and analyzes HRV, readiness, and sleep data]

YOUR RECOVERY PROFILE:

After High-Stress Periods (Readiness <70):
- Day 1-2: Readiness remains low (avg 68)
- Day 3-4: Gradual improvement (avg 75)
- Day 5-6: Return to baseline (avg 82)

KEY RECOVERY INDICATORS:
1. HRV normalizes first (2-3 days)
2. Sleep efficiency improves next (3-4 days)
3. Readiness fully recovers last (5-6 days)

WHAT HELPS YOUR RECOVERY:
✅ Sleep >7.5 hours (you recover 1 day faster)
✅ Light activity on recovery days (walks, yoga)
✅ Consistency in sleep timing

WHAT SLOWS RECOVERY:
❌ Additional hard workouts during recovery
❌ Sleep <7 hours
❌ High stress maintained >5 days

RECOMMENDATION:
After a high-stress week, plan 5-6 buffer days before your next major deadline
or intense workout. Your body needs nearly a week to fully bounce back.
```

## Workout Planning

### Weekly Training Plan

**Prompt:**
```
Create an optimal workout plan for next week based on my current recovery trends
```

**Claude's Plan:**
```
Analyzing your trends and creating a personalized training plan...

[Calls oura_get_weekly_trends and oura_get_today_readiness]

YOUR CURRENT STATE:
- Readiness trend: Improving (+15.3%)
- Recent activity: Declining (-8.2%)
- Sleep: Stable and good (avg 79)

📅 OPTIMIZED TRAINING PLAN (Jan 12-18):

MONDAY (Predicted Readiness: 86)
- Morning: High-intensity strength training (60 min)
- Why: Coming off weekend recovery, readiness high

TUESDAY (Predicted: 80)
- Morning: Moderate cardio (45 min)
- Why: Active recovery maintains readiness

WEDNESDAY (Predicted: 83)
- Rest day or light yoga (30 min)
- Why: Prevent accumulated fatigue

THURSDAY (Predicted: 85)
- Morning: High-intensity interval training (45 min)
- Why: Mid-week peak, well-recovered

FRIDAY (Predicted: 78)
- Evening: Moderate strength training (50 min)
- Why: Moderate intensity before weekend

SATURDAY (Predicted: 75)
- Light activity: Hike or bike ride (60-90 min)
- Why: Active recovery, enjoyment

SUNDAY (Predicted: 82)
- Rest day: Mobility work (20 min)
- Why: Full recovery before Monday

⚠️ DYNAMIC ADJUSTMENTS:
Each morning, check readiness:
- Readiness >80: Proceed as planned
- Readiness 70-80: Reduce intensity 25%
- Readiness <70: Switch to light activity or rest

This plan balances your improving readiness trend with adequate recovery!
```

### Pre-Workout Check

**Prompt:**
```
Should I do my planned HIIT workout today? Check my recovery status.
```

**Claude's Assessment:**
```
Let me check your recovery for HIIT training...

[Calls oura_get_today_readiness]

RECOVERY STATUS:

Overall Readiness: 68 ⚠️
- Sleep: 72 (Fair)
- HRV Balance: 48 (Low)
- Resting HR: 58 bpm (elevated)
- Activity Balance: 45 (Needs recovery)

HIIT WORKOUT ASSESSMENT: ❌ NOT RECOMMENDED

Here's why:
1. Low HRV (48) indicates nervous system stress
2. Elevated resting HR suggests incomplete recovery
3. Low activity balance means you need rest
4. Sleep wasn't optimal

ALTERNATIVE WORKOUT:
✅ 30-minute easy walk or light yoga
✅ Focus on mobility and stretching
✅ Swim or bike at conversational pace

WHEN TO RESCHEDULE HIIT:
- Wait for readiness >75
- HRV balance >70
- Resting HR back to baseline (~52)
- Likely: 2-3 days

TONIGHT'S FOCUS:
- Bed by 10 PM
- 8+ hours sleep goal
- Hydration
- Light dinner

Remember: Missing one hard workout for recovery prevents missing a week due
to injury or burnout. Train smart!
```

## API Usage Examples

### Programmatic Access

If you're building custom applications:

#### Get Today's Readiness

```typescript
import { handleGetTodayReadiness } from './src/tools/readiness.js';

async function checkReadiness() {
  const result = await handleGetTodayReadiness({});

  if (result.score > 80) {
    console.log("High readiness - schedule important tasks!");
  } else if (result.score < 70) {
    console.log("Low readiness - prioritize recovery");
  }

  return result;
}
```

#### Get Sleep Summary

```typescript
import { handleGetSleepSummary } from './src/tools/sleep.js';

async function analyzeSleep(date?: string) {
  const result = await handleGetSleepSummary({
    date: date || new Date().toISOString().split('T')[0]
  });

  console.log(`Sleep score: ${result.score}`);
  console.log(`Total sleep: ${result.duration.total_formatted}`);
  console.log(`Efficiency: ${result.efficiency.percentage}%`);

  return result;
}
```

#### Get Weekly Trends

```typescript
import { handleGetWeeklyTrends } from './src/tools/trends.js';

async function getHealthTrends(days: number = 7) {
  const result = await handleGetWeeklyTrends({
    days,
    end_date: new Date().toISOString().split('T')[0]
  });

  console.log("Readiness trend:", result.readiness.trend);
  console.log("Sleep trend:", result.sleep.trend);
  console.log("Activity trend:", result.activity.trend);
  console.log("\nPatterns:", result.patterns);

  return result;
}
```

#### Health Check

```typescript
import { handleHealthCheck } from './src/tools/health-check.js';

async function systemHealth() {
  const result = await handleHealthCheck({
    include_cache_samples: false
  });

  console.log("System status:", result.overall_status);
  console.log("API:", result.components.api.status);
  console.log("Cache:", result.components.cache.status);

  if (result.overall_status !== 'healthy') {
    console.error("Issues:", result.diagnostics.recommendations);
  }

  return result;
}
```

## Advanced Use Cases

### Integration with Calendar

**Prompt:**
```
Based on my readiness scores over the past week, when should I schedule my most important meetings next week?
```

### Recovery Prediction

**Prompt:**
```
I have a marathon in 30 days. Based on my recent recovery patterns, create a taper plan.
```

### Sleep Optimization

**Prompt:**
```
What's the ideal bedtime for me based on my sleep patterns and wake time?
```

### Stress Management

**Prompt:**
```
My HRV has been declining. What recovery strategies should I prioritize?
```

## Tips for Best Results

### Be Specific

❌ "How am I doing?"
✅ "What's my readiness score today and should I do my planned workout?"

### Provide Context

❌ "Should I rest?"
✅ "I have a HIIT workout planned and a big presentation tomorrow. Given my readiness, what should I prioritize?"

### Ask for Trends

❌ "How did I sleep?"
✅ "How has my sleep quality trended over the past two weeks? Any patterns?"

### Request Actionable Advice

❌ "What's my HRV?"
✅ "Based on my HRV trends, what should I adjust in my training plan?"

## Next Steps

- Explore [Health Persona Integration](./README.md#health-persona-integration)
- Set up [health-aware task prioritization](./README.md)
- Read the [full API documentation](./README.md#available-tools)
- Check [troubleshooting guide](./README.md#troubleshooting) if you have issues

---

**Have a great example to share?** Contribute to this guide!
