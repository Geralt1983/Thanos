# Energy-Aware Task Prioritization

## Overview

The Energy-Aware Task Prioritization system intelligently matches tasks to your current energy levels, helping you work **with** your brain instead of against it. This feature is specifically designed for ADHD users who experience variable capacity throughout the day.

### Key Benefits

- **Automatic energy detection** via Oura Ring readiness scores
- **Smart task matching** that suggests high-cognitive tasks when energy is high, routine tasks when low
- **Dynamic daily goals** that adjust based on your capacity
- **User override capability** for when you know your energy better than metrics
- **Feedback loop** that helps improve recommendations over time

---

## Table of Contents

1. [How the Algorithm Works](#how-the-algorithm-works)
2. [Setting Cognitive Load on Tasks](#setting-cognitive-load-on-tasks)
3. [How Daily Goals Are Adjusted](#how-daily-goals-are-adjusted)
4. [Overriding Energy Suggestions](#overriding-energy-suggestions)
5. [Available MCP Tools](#available-mcp-tools)
6. [Coach Persona Integration](#coach-persona-integration)
7. [Examples & Workflows](#examples--workflows)
8. [Best Practices](#best-practices)

---

## How the Algorithm Works

### Energy Context Detection

The system determines your current energy level using a **priority-based fallback chain**:

1. **Manual energy logs** (highest priority) - You logged your energy today
2. **Oura readiness score** - Today's Oura Ring data from cache
3. **Historical energy states** - Previous energy logs with Oura data
4. **Default to medium** - Graceful fallback if no data available

#### Energy Level Mapping

Oura readiness scores (0-100) map to energy levels:

| Readiness Score | Energy Level | Description |
|----------------|--------------|-------------|
| **85-100** | `high` | Peak performance, ready for complex work |
| **70-84** | `medium` | Good baseline, can handle most tasks |
| **0-69** | `low` | Recovery mode, prioritize easier tasks |

### Task Scoring Algorithm

Each task receives an **energy match score (0-165 points)** based on how well it aligns with your current energy level.

#### Core Matching Logic

**Perfect Match (+100 points):**
- High energy → High cognitive load tasks
- Medium energy → Medium cognitive load tasks
- Low energy → Low cognitive load tasks

**Acceptable Match (+50 points):**
- High energy → Medium cognitive load tasks
- Medium energy → High or low cognitive load tasks
- Low energy → Medium cognitive load tasks

**Poor Match (0 points):**
- High energy → Low cognitive load tasks
- Low energy → High cognitive load tasks

#### Bonus Points

The algorithm adds bonus points for additional alignment factors:

**High Energy Bonuses:**
- Milestone/Deliverable tasks: **+20 points**
- Deep work drain type: **+10 points**
- Large tasks (5+ hours): **+10 points**

**Medium Energy Bonuses:**
- Progress tier tasks: **+20 points**
- Shallow work drain type: **+10 points**
- Medium-sized tasks (2-4 hours): **+5 points**

**Low Energy Bonuses:**
- Checkbox tier tasks: **+20 points**
- Admin work drain type: **+10 points**
- Quick wins (≤2 hours): **+15 points** ← ADHD momentum building
- Personal category: **+5 points**

**Universal Bonuses:**
- Active tasks: **+5 points** ← Encourages finishing started work

#### Example Scores

**High Energy Day (Readiness: 92)**
```
1. [HIGH] Architect new microservice
   Score: 138 points
   - Perfect match: High cognitive load (+100)
   - Milestone work (+20)
   - Deep work (+10)
   - Large task (+10)
   - Active task (-2, not active)

2. [LOW] Respond to team emails
   Score: 15 points
   - Poor match: Low cognitive load when energy high (0)
   - Quick win bonus (+15)
```

**Low Energy Day (Readiness: 58)**
```
1. [LOW] File expense reports
   Score: 145 points
   - Perfect match: Low cognitive load (+100)
   - Checkbox work (+20)
   - Admin work (+10)
   - Quick win (+15)

2. [HIGH] Write technical architecture doc
   Score: 0 points
   - Avoid: High cognitive load when energy low (0)
```

---

## Setting Cognitive Load on Tasks

### What is Cognitive Load?

**Cognitive load** represents the mental complexity required to complete a task, independent of time investment.

| Cognitive Load | Description | Examples |
|----------------|-------------|----------|
| **`low`** | Minimal mental effort, routine work, clear steps | Filing, email replies, scheduling, data entry, basic admin |
| **`medium`** | Moderate thinking required, familiar work with some complexity | Code reviews, documentation updates, bug fixes, implementing features from specs |
| **`high`** | Deep thinking, complex problem-solving, creative work | Architecture design, debugging complex issues, writing specs, research, strategic planning |

### How to Set Cognitive Load

#### When Creating Tasks

Use the `workos_create_task` tool with the `cognitiveLoad` parameter:

```json
{
  "tool": "workos_create_task",
  "args": {
    "title": "Write API documentation for auth endpoints",
    "cognitiveLoad": "medium",
    "valueTier": "progress",
    "drainType": "shallow",
    "effortEstimate": 3
  }
}
```

#### When Updating Existing Tasks

Use the `workos_update_task` tool:

```json
{
  "tool": "workos_update_task",
  "args": {
    "taskId": 42,
    "cognitiveLoad": "high"
  }
}
```

### Guidelines for Choosing Cognitive Load

**Choose `high` for:**
- ✅ Tasks requiring original thinking or creativity
- ✅ Complex problem-solving or debugging
- ✅ Architecture and design decisions
- ✅ Learning new concepts
- ✅ Strategic planning

**Choose `medium` for:**
- ✅ Implementation work from clear specs
- ✅ Code reviews requiring context
- ✅ Writing documentation
- ✅ Refactoring familiar code
- ✅ Moderate troubleshooting

**Choose `low` for:**
- ✅ Administrative tasks
- ✅ Email responses
- ✅ Scheduling and calendar management
- ✅ Filing and organizing
- ✅ Routine data entry

### Default Behavior

If you don't specify `cognitiveLoad`, tasks default to **`medium`**. This ensures they're still considered in energy-aware recommendations.

---

## How Daily Goals Are Adjusted

### Adjustment Algorithm

Your daily target points automatically adjust based on your readiness score to **protect your wellbeing and optimize performance**.

| Readiness Score | Energy Level | Adjustment | Example (18pt base) | Reasoning |
|----------------|--------------|-----------|-------------------|-----------|
| **85-100** | high | **+15%** | 18 → 21 points | Leverage peak energy for higher output |
| **70-84** | medium | **0%** | 18 → 18 points | Maintain standard target |
| **0-69** | low | **-25%** | 18 → 14 points | Reduce target to prevent burnout |

### Adjustment Examples

**High Readiness Day (Readiness: 92, Sleep: 88)**
```
Original Target: 18 points
Adjusted Target: 21 points (+15%)
Reason: High readiness (92/100) - increased target by 15% to leverage
        peak energy. Sleep quality: 88/100.
```

**Medium Readiness Day (Readiness: 77, Sleep: 75)**
```
Original Target: 18 points
Adjusted Target: 18 points (0%)
Reason: Good readiness (77/100) - maintaining standard target.
        Sleep quality: 75/100.
```

**Low Readiness Day (Readiness: 55, Sleep: 62)**
```
Original Target: 18 points
Adjusted Target: 14 points (-25%)
Reason: Low readiness (55/100) - reduced target by 25% to prevent
        burnout and protect wellbeing. Sleep quality: 62/100.
```

### How to Trigger Adjustment

#### Automatic Adjustment

Daily goal adjustment happens automatically in your morning briefing when you use Coach.

#### Manual Adjustment

Use the `workos_adjust_daily_goal` tool:

```json
{
  "tool": "workos_adjust_daily_goal",
  "args": {
    "baseTarget": 18
  }
}
```

This will:
1. Fetch your current Oura readiness & sleep scores
2. Calculate the adjusted target
3. Update today's daily_goals record
4. Return detailed reasoning

**Response:**
```json
{
  "originalTarget": 18,
  "adjustedTarget": 14,
  "adjustmentPercentage": -25,
  "energyLevel": "low",
  "readinessScore": 55,
  "sleepScore": 62,
  "reason": "Low readiness (55/100) - reduced target by 25% to prevent burnout..."
}
```

### ADHD-Specific Benefits

**Prevents Burnout:**
- Automatically reduces expectations on low-energy days
- Protects your streak without forcing you to push through exhaustion

**Leverages Peak Windows:**
- Increases target when energy is high
- Helps you capitalize on good days without guilt

**Removes Decision Fatigue:**
- System handles the "How much should I do today?" question
- One less thing to figure out when energy is low

---

## Overriding Energy Suggestions

### Why Override?

The system auto-detects energy from Oura, but **you know yourself best**. Override when:

- 🔥 **ADHD medication just kicked in** - Oura shows low readiness, but you feel focused
- 😴 **Distracted despite metrics** - Readiness is high, but you're mentally tired
- ☕ **External factors** - Coffee, stressful news, deadline adrenaline
- 🎯 **Urgency overrides capacity** - Must finish high-cognitive task despite low energy

### How to Override

Use the `workos_override_energy_suggestion` tool:

```json
{
  "tool": "workos_override_energy_suggestion",
  "args": {
    "energyLevel": "high",
    "reason": "ADHD medication just kicked in, have 3-hour focus window",
    "adjustDailyGoal": true
  }
}
```

**Parameters:**
- `energyLevel`: `"low"`, `"medium"`, or `"high"` (required)
- `reason`: Why you're overriding (required) - helps future algorithm learning
- `taskId`: Specific task you're planning to work on (optional)
- `adjustDailyGoal`: Recalculate daily target based on override (default: `true`)

### Override Examples

#### Example 1: Medication Window

**Scenario:** Oura readiness is 65 (low), but you just took ADHD meds

```json
{
  "energyLevel": "high",
  "reason": "Medication kicked in, have 4-hour peak focus window",
  "taskId": 123,
  "adjustDailyGoal": true
}
```

**Result:**
- Energy level changes: `low` → `high`
- Daily goal recalculated: 14 pts → 21 pts (+15%)
- Task recommendations updated to prioritize high-cognitive work
- Override logged to `energy_states` table with "OVERRIDE:" prefix

#### Example 2: Distracted Despite Good Sleep

**Scenario:** Oura shows readiness 88 (high), but you're mentally foggy

```json
{
  "energyLevel": "low",
  "reason": "Distracted by family emergency, can only do admin work",
  "adjustDailyGoal": true
}
```

**Result:**
- Energy level changes: `high` → `low`
- Daily goal recalculated: 21 pts → 14 pts (-25%)
- Task recommendations shift to low-cognitive work
- Protects you from overcommitting when capacity is limited

### Override Response

```json
{
  "override": {
    "energyLevel": "high",
    "reason": "Medication kicked in, have 4-hour peak focus window",
    "timestamp": "2026-01-12T10:30:00Z"
  },
  "energyContext": {
    "previousLevel": "low",
    "newLevel": "high",
    "readinessScore": 65,
    "sleepScore": 70
  },
  "task": {
    "id": 123,
    "title": "Architect new microservice",
    "cognitiveLoad": "high",
    "energyScore": 138
  },
  "goalAdjustment": {
    "originalTarget": 14,
    "adjustedTarget": 21,
    "adjustmentPercentage": 15,
    "reason": "Override to high energy - increased target by 15%..."
  }
}
```

### Override Data Storage

Overrides are logged to the `energy_states` table with:
- `level`: Your override energy level
- `note`: Prefixed with "OVERRIDE:" + your reason
- `recordedAt`: Timestamp of override

This data helps:
- **Future algorithm learning** - Patterns in when you override
- **Coach pattern detection** - "You often override to high after medication"
- **Personal insights** - Track what external factors affect your energy

---

## Available MCP Tools

### 1. `workos_get_energy_aware_tasks`

Get tasks ranked by energy match score.

**Parameters:**
- `energyLevel` (optional): Override auto-detection (`"low"`, `"medium"`, `"high"`)
- `limit` (optional): Max number of tasks to return

**Example:**
```json
{
  "tool": "workos_get_energy_aware_tasks",
  "args": {
    "limit": 5
  }
}
```

**Response:**
```json
{
  "energyContext": {
    "energyLevel": "medium",
    "readinessScore": 77,
    "sleepScore": 75,
    "source": "oura"
  },
  "tasks": [
    {
      "id": 42,
      "title": "Update API documentation",
      "cognitiveLoad": "medium",
      "energyScore": 125,
      "matchReason": "Perfect match: Medium cognitive load for medium energy. Bonus: Progress tasks ideal for medium energy."
    }
  ]
}
```

### 2. `workos_adjust_daily_goal`

Manually trigger daily goal adjustment.

**Parameters:**
- `baseTarget` (optional): Base target points (default: 18)

**Example:**
```json
{
  "tool": "workos_adjust_daily_goal",
  "args": {
    "baseTarget": 18
  }
}
```

### 3. `workos_override_energy_suggestion`

Override auto-detected energy level.

**Parameters:**
- `energyLevel` (required): `"low"`, `"medium"`, or `"high"`
- `reason` (required): Why you're overriding
- `taskId` (optional): Task you're planning to work on
- `adjustDailyGoal` (optional): Recalculate goal (default: `true`)

**Example:**
```json
{
  "tool": "workos_override_energy_suggestion",
  "args": {
    "energyLevel": "high",
    "reason": "Medication window - ready for complex work"
  }
}
```

### 4. `workos_provide_energy_feedback`

Record whether energy-task match was helpful.

**Parameters:**
- `taskId` (required): Task that was completed
- `suggestedEnergyLevel` (required): What system suggested
- `actualEnergyLevel` (required): Your actual energy
- `completedSuccessfully` (required): `true` or `false`
- `userFeedback` (optional): Additional notes

**Example:**
```json
{
  "tool": "workos_provide_energy_feedback",
  "args": {
    "taskId": 42,
    "suggestedEnergyLevel": "medium",
    "actualEnergyLevel": "medium",
    "completedSuccessfully": true,
    "userFeedback": "Perfect match, felt engaged throughout"
  }
}
```

### 5. Enhanced Existing Tools

**`workos_create_task`** - Now accepts `cognitiveLoad`:
```json
{
  "title": "Write technical spec",
  "cognitiveLoad": "high",
  "valueTier": "deliverable"
}
```

**`workos_update_task`** - Can update `cognitiveLoad`:
```json
{
  "taskId": 42,
  "cognitiveLoad": "medium"
}
```

**`workos_daily_summary`** - Includes energy context:
```json
{
  "energy": {
    "level": "medium",
    "readinessScore": 77,
    "sleepScore": 75,
    "targetAdjustment": {
      "original": 18,
      "adjusted": 18,
      "difference": 0,
      "reason": "Good readiness - maintaining standard target"
    }
  },
  "recommendations": [
    // Top 5 energy-aware task suggestions
  ]
}
```

---

## Coach Persona Integration

The Coach persona has been enhanced with energy-aware capabilities to help you understand your energy patterns, explain prioritization decisions, and optimize your workflow.

### What Coach Can Do

**1. Explain Prioritization Decisions**

Coach can explain why specific tasks were recommended for your current energy level:

- **Task Suggestion Reasoning** - Why a task is perfect for your current energy
- **Daily Goal Adjustments** - Why your target was increased/reduced today
- **Mismatch Warnings** - When you're working against your energy level

**2. Detect Energy Patterns**

Coach analyzes your historical data to identify patterns:

- **Energy Timing** - When is your energy typically highest/lowest?
- **Task Completion** - What tasks do you complete on high vs low energy days?
- **Sustainability** - Are you pushing through low energy too often?
- **Avoidance** - Are you avoiding high-cognitive tasks when energy is high?
- **Recovery** - How well do you recover from low energy days?

**3. Provide Actionable Insights**

Coach translates data into ADHD-friendly recommendations:

- Personalized strategies based on your patterns
- Specific suggestions for improving energy-task alignment
- Encouragement and validation when you work with your energy
- Gentle accountability when patterns show potential burnout

---

### Questions to Ask Coach

#### Energy-Aware Morning Brief

When you start your day, Coach can provide energy context:

**"What's my energy level today and what should I focus on?"**

Coach will:
- Report your Oura readiness and sleep scores
- Map readiness to energy level (high/medium/low)
- Explain how your daily goal was adjusted and why
- Recommend 3-5 tasks that match your current energy
- Explain the reasoning behind each recommendation

**Example Coach Response:**
```
Your Oura readiness is 58/100 with a sleep score of 62/100. This indicates low
energy today. I've reduced your daily target from 18 to 14 points (-25%) to
prevent burnout and protect your wellbeing.

Given your low energy, here's what I recommend focusing on today:

1. [LOW] File expense reports (Score: 145)
   → Perfect match: Low cognitive load task. This is checkbox work that's
     satisfying to complete and requires minimal mental effort. Quick win
     bonus for momentum building.

2. [LOW] Respond to team emails (Score: 135)
   → Perfect match: Admin work ideal for low energy. Clear, finite tasks
     that you can knock out without draining yourself further.

3. [MEDIUM] Update meeting notes (Score: 65)
   → Acceptable match: Light documentation work that doesn't require deep
     thinking. Save deeper work for when your energy improves.

Remember: Working with your brain today, not against it. These tasks will
help you maintain momentum and protect your streak without pushing through
exhaustion. 🧠✨
```

---

#### Energy Pattern Detection

Ask Coach to analyze your historical patterns:

**"When is my energy highest during the week?"**

Coach analyzes `energy_states` and Oura data from the past 30-90 days:

```
Looking at your energy patterns over the past 60 days:

📊 Your energy peaks:
- Tuesdays and Wednesdays (average readiness: 82)
- Mid-morning (9am-11am) after medication

📉 Your energy dips:
- Mondays (average readiness: 68) - recovery from weekend
- Friday afternoons (average readiness: 71) - accumulated fatigue

💡 Recommendation: Schedule high-cognitive work (architecture, design,
complex debugging) for Tuesday and Wednesday mornings. Save admin work
and meetings for Monday mornings and Friday afternoons.
```

**"What tasks do I complete on high vs low energy days?"**

```
Analyzing your task completion patterns:

⚡ High Energy Days (readiness 85+):
- You complete 2.3x more high-cognitive tasks
- Average: 3 milestone/deliverable tasks completed
- Deep work sessions average 4.2 hours
- 89% success rate on complex tasks

🔋 Low Energy Days (readiness < 70):
- You complete 4.1x more checkbox/admin tasks
- Average: 8 low-cognitive tasks completed
- Quick wins (≤2 hrs) have 94% completion rate
- High-cognitive tasks have only 31% completion rate on these days

📌 Insight: You're effectively working with your energy! On low energy days,
you pivot to admin work rather than forcing complex tasks. This is exactly
the ADHD-friendly approach I recommend.
```

**"Am I pushing through low energy days too often?"**

```
Checking your energy sustainability over the past 30 days:

⚠️ Sustainability Concerns:
- 8 out of 12 low energy days (67%) you still attempted high-cognitive tasks
- Average completion rate on those tasks: 38%
- 5 days where you worked past burnout signals

✅ Good Patterns:
- 4 low energy days where you focused on admin/checkbox work
- 100% completion rate on appropriate energy-task matches
- Faster recovery (1.8 days vs 2.4 days) when you honor low energy

💡 Recommendation: Trust the low energy signals more. When readiness < 70,
pivot to admin work immediately. You'll recover faster and maintain better
long-term productivity. Your brain is asking for rest, not push-through.
```

**"Are there tasks I'm avoiding when my energy is high?"**

```
Analyzing avoidance patterns on high energy days:

🎯 High Energy Opportunities (last 15 days):
- 7 days with readiness >= 85
- You had 12 high-cognitive tasks available

📊 What Actually Happened:
- You completed 3 high-cognitive tasks (25% of opportunities)
- Spent 60% of high-energy time on medium-cognitive work
- 4 high-cognitive tasks marked as "priority" but still incomplete

🚩 Potential Avoidance:
- "Write technical architecture doc" - available on 4 high-energy days, not started
- "Refactor authentication system" - available on 3 high-energy days, not started

💡 Pattern Detected: You may be avoiding complex tasks even when energy is
optimal. This is common with ADHD - the hardest part is starting. Consider:
1. Breaking these into smaller first steps
2. Using high energy for just 1 hour on the avoided task
3. Pairing with a body double or accountability partner

Your brain is capable of this work when energy is high - let's work on the
starting friction. 🧠
```

---

### How Coach Explains Prioritization

#### Task Suggestion Reasoning

When Coach recommends tasks, the explanation includes:

**High Energy Day Example:**
```
Task: "Architect new microservice" (Score: 138)

Why this task matches your HIGH energy:
✓ High cognitive load requirement aligns perfectly with your peak capacity
✓ Milestone-level work (+20 bonus) - great for when you can handle complexity
✓ Deep work drain type (+10 bonus) - you have the focus for this right now
✓ Large task estimate (+10 bonus) - you have sustained energy for extended work

This is exactly the kind of complex, strategic work to tackle when your brain
is firing on all cylinders. Don't waste this energy window on email! 🚀
```

**Low Energy Day Example:**
```
Task: "File expense reports" (Score: 145)

Why this task matches your LOW energy:
✓ Low cognitive load - minimal mental effort required
✓ Checkbox tier (+20 bonus) - satisfying to complete, maintains momentum
✓ Admin work (+10 bonus) - clear steps, no creative thinking needed
✓ Quick win (+15 bonus) - can finish in under 2 hours, build momentum

This is perfect for today. Admin work feels accomplishing without draining
you further. You're working WITH your brain, not against it. 🧠✨
```

#### Daily Goal Adjustment Reasoning

Coach explains goal adjustments with context:

**Increase Goal (+15%):**
```
Your Oura readiness is 92/100 (sleep: 88/100). You're at peak capacity!

I've increased your daily target from 18 to 21 points (+15%) because:
- High readiness indicates you have the energy for higher output
- Sleep quality is excellent - recovery was effective
- This leverages your peak performance window
- You can handle more complex/valuable work today

Use this energy window strategically. Schedule your most important high-cognitive
work for this morning when you're at your best. 💪
```

**Maintain Goal (0%):**
```
Your Oura readiness is 77/100 (sleep: 75/100). Solid baseline!

Your daily target stays at 18 points because:
- Good readiness in the healthy middle range
- Sleep was adequate - you're rested but not exceptional
- Standard target is appropriate for this energy level
- You can handle your usual mix of work

This is a "normal good day" - proceed with your planned tasks. Mix of medium
and some high-cognitive work is fine. ✅
```

**Reduce Goal (-25%):**
```
Your Oura readiness is 55/100 (sleep: 62/100). Recovery mode today.

I've reduced your daily target from 18 to 14 points (-25%) because:
- Low readiness indicates your body needs recovery time
- Sleep wasn't restorative - you need to honor that
- Pushing through low energy leads to burnout and slower recovery
- Protecting your wellbeing and long-term sustainability

This isn't giving up - this is strategic rest. Focus on admin/checkbox work,
maintain your streak, and you'll recover faster. Your brain will thank you. 🛡️
```

#### Energy-Task Mismatch Warnings

Coach detects when you're working against your energy:

**High-Cognitive Task on Low Energy:**
```
⚠️ Energy Mismatch Detected

You're attempting "Debug complex authentication issue" (high cognitive load)
while your energy is LOW (readiness: 58).

This is a poor match because:
- Complex debugging requires sustained focus and deep thinking
- Low energy makes it harder to hold multiple variables in working memory
- Frustration risk is high when capacity doesn't match task demands
- You're likely to spin your wheels and feel discouraged

Alternative approach:
1. Pause this task - it's not going away
2. Switch to admin/checkbox work to build momentum
3. Revisit this tomorrow when energy improves
4. OR override to high energy if medication/coffee just kicked in

Your brain isn't broken - the timing is just wrong. 🧠
```

**Low-Cognitive Tasks on High Energy:**
```
💡 Energy Optimization Suggestion

You've been doing admin work for 2 hours while your energy is HIGH
(readiness: 88). You're underutilizing your peak capacity!

Available high-cognitive tasks that match this energy:
1. "Architect payment processing service" (Score: 138)
2. "Write technical spec for API redesign" (Score: 132)
3. "Debug race condition in scheduler" (Score: 128)

Consider: Can admin work wait until afternoon when energy dips? Your high
energy window is precious - use it for work that requires your best thinking.

This isn't pressure - it's optimization. But if you need easy wins today for
momentum, that's valid too. You're the expert on what you need. 🎯
```

---

### Coach in Morning Briefings

Your morning brief automatically includes energy context when you use the briefing engine:

```
Good morning! Let's plan your Monday.

🧠 Energy & Readiness
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Oura Readiness: 72/100
Sleep Score: 74/100
Energy Level: Medium
Daily Goal: 18 points (no adjustment)

You're at a solid baseline today. Good readiness in the healthy range -
you can handle your usual mix of work. Not a peak day, but definitely not
a recovery day either.

Suggested approach: Mix of medium-cognitive and some high-cognitive tasks.
Start with a quick win to build momentum, then tackle 1-2 important tasks
during your morning focus window.

📋 Recommended Tasks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Based on your medium energy, here are today's top recommendations:

1. [MEDIUM] Implement user profile API endpoints
   → Perfect match for medium energy. Progress tier work that moves projects
     forward without requiring peak cognitive capacity.

2. [MEDIUM] Write documentation for onboarding flow
   → Good medium-cognitive work. Familiar domain, clear structure.

3. [LOW] Review and merge dependency updates
   → Quick win to start - builds momentum without draining energy.

4. [HIGH] Design caching strategy for analytics
   → Stretch goal if you hit flow state. Available if energy peaks.

5. [LOW] Respond to team emails and schedule 1:1s
   → Save for afternoon if energy dips.

🎯 Strategy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Start with #3 (quick win), move to #1 and #2 (medium work), attempt #4 if
you're in flow. Keep #5 in your back pocket for end of day.

Remember: You're working WITH your brain today, not against it. 🧠✨
```

---

### Asking Coach for Pattern Insights

You can ask Coach these questions anytime:

**Energy Timing Patterns:**
- "When is my energy highest during the day?"
- "What days of the week am I most productive?"
- "How long does my medication window last?"
- "Do I have consistent energy dips? When?"

**Task Completion Patterns:**
- "What types of tasks do I complete most on high energy days?"
- "Am I getting enough high-cognitive work done?"
- "What's my completion rate for different cognitive loads?"
- "Which tasks do I avoid even on high energy days?"

**Sustainability & Recovery:**
- "Am I pushing through low energy too often?"
- "How long does it take me to recover from low energy days?"
- "What happens when I ignore low energy signals?"
- "Am I protecting my streak without burning out?"

**Override & Feedback:**
- "When do I most often override energy suggestions?"
- "How accurate are the energy-task matches for me?"
- "What patterns show up in my override reasons?"
- "Does providing feedback help improve recommendations?"

Coach uses data from:
- `energy_states` table (manual logs + Oura snapshots)
- `tasks` table (cognitive load, completion status, timestamps)
- `daily_goals` table (adjustments, actual performance)
- `energy_feedback` table (your feedback on matches)
- Oura cache database (historical readiness and sleep scores)

---

### ADHD-Friendly Coach Features

**Validates Your Experience:**
```
"I see you overrode to high energy 30 minutes after logging low. That's
completely normal with ADHD medication timing! The system doesn't know about
your meds, but YOU do. This override data helps me learn your patterns."
```

**Removes Guilt:**
```
"You've had 4 low energy days this week. That's not laziness - that's biology.
Your Oura readiness has been below 70 all week. Reducing your target isn't
giving up, it's strategic rest. You'll recover faster this way."
```

**Celebrates Working With Energy:**
```
"Great job! You focused on admin work today despite having 3 high-cognitive
tasks available. Your readiness was 62 - low energy. You honored that signal
instead of pushing through. This is exactly the ADHD-friendly approach that
protects long-term productivity. 🎉"
```

**Encourages Starting:**
```
"You've avoided 'Write architecture doc' on 4 high energy days. Your brain CAN
do this work - the hard part is starting. What if you committed to just 30
minutes tomorrow morning when your medication kicks in? Starting is everything
with ADHD. You've got this. 💪"
```

**Provides Context, Not Pressure:**
```
"Your energy is high (readiness: 89), but you've been doing admin work. That's
okay! If you need easy wins today for momentum or emotional reasons, that's
valid. But if you're avoiding hard work out of anxiety, I want you to know:
your capacity is there today if you want to use it. Your choice. 🧠"
```

---

### Implementation Details

**Coach Persona Documentation:**
- Full prompt and pattern detection queries: `Agents/Coach.md`
- Energy explanation templates built into Coach persona
- Pattern detection SQL queries analyze historical data

**Briefing Engine Integration:**
- Energy context automatically included in morning briefs
- `Tools/briefing_engine.py` handles energy context formatting
- Helper methods: `format_energy_context_for_coach()`, `explain_task_suggestion()`, `explain_goal_adjustment()`

**Data Sources:**
- Oura readiness/sleep: `~/.oura-cache/oura-health.db` (via `oura-cache.ts`)
- Energy logs: `energy_states` table in WorkOS database
- Task data: `tasks` table with `cognitive_load` field
- Daily goals: `daily_goals` table with adjustment tracking
- Feedback: `energy_feedback` table for learning

---

### Next Steps with Coach

1. **Start Using Morning Briefs** - Get energy context automatically each day
2. **Ask Pattern Questions** - "When is my energy highest?" to understand your rhythms
3. **Trust the Recommendations** - Especially on low energy days
4. **Override When You Know Better** - Medication, urgency, external factors
5. **Provide Feedback** - Help Coach learn what works for you
6. **Track Patterns Over Time** - Weekly reviews with Coach to spot trends

**Remember:** Coach is your ally in working with your brain, not against it. The goal isn't perfect productivity every day - it's sustainable productivity over time. 🧠✨

---

## Examples & Workflows

### Morning Routine Workflow

**1. Check Energy & Daily Goal**
```json
// Get daily summary (includes energy context)
{ "tool": "workos_daily_summary" }

// Response includes:
{
  "energy": {
    "level": "low",
    "readinessScore": 58,
    "sleepScore": 62,
    "targetAdjustment": {
      "original": 18,
      "adjusted": 14,
      "difference": -4,
      "reason": "Low readiness (58/100) - reduced target by 25%..."
    }
  }
}
```

**2. Get Energy-Matched Tasks**
```json
// Get top 5 tasks matched to current energy
{
  "tool": "workos_get_energy_aware_tasks",
  "args": { "limit": 5 }
}

// Low energy day results:
[
  "[LOW] File expense reports (Score: 145)",
  "[LOW] Respond to emails (Score: 135)",
  "[LOW] Update meeting notes (Score: 120)",
  "[MEDIUM] Review pull request (Score: 65)",
  "[MEDIUM] Update docs (Score: 60)"
]
```

**3. Override if Needed**
```json
// Took medication, ready for complex work
{
  "tool": "workos_override_energy_suggestion",
  "args": {
    "energyLevel": "high",
    "reason": "ADHD meds kicked in, 3hr focus window"
  }
}

// Tasks re-ranked for high energy:
[
  "[HIGH] Architect microservice (Score: 138)",
  "[HIGH] Debug complex issue (Score: 130)",
  "[HIGH] Write tech spec (Score: 125)",
  ...
]
```

### Task Creation with Cognitive Load

```json
// Creating a complex task
{
  "tool": "workos_create_task",
  "args": {
    "title": "Design database schema for analytics",
    "cognitiveLoad": "high",
    "valueTier": "milestone",
    "drainType": "deep",
    "effortEstimate": 6,
    "context": "Needs careful planning, consider scalability"
  }
}

// Creating a routine task
{
  "tool": "workos_create_task",
  "args": {
    "title": "File weekly status report",
    "cognitiveLoad": "low",
    "valueTier": "checkbox",
    "drainType": "admin",
    "effortEstimate": 1
  }
}
```

### Providing Feedback

```json
// After completing a task successfully
{
  "tool": "workos_provide_energy_feedback",
  "args": {
    "taskId": 123,
    "suggestedEnergyLevel": "high",
    "actualEnergyLevel": "high",
    "completedSuccessfully": true,
    "userFeedback": "Perfect timing, completed in flow state"
  }
}

// If energy-task match was wrong
{
  "tool": "workos_provide_energy_feedback",
  "args": {
    "taskId": 124,
    "suggestedEnergyLevel": "medium",
    "actualEnergyLevel": "low",
    "completedSuccessfully": false,
    "userFeedback": "Struggled, should have been marked low cognitive load"
  }
}
```

---

## Best Practices

### For Setting Cognitive Load

**✅ Do:**
- Set cognitive load based on **mental effort**, not time
- Consider your own baseline (what's high cognitive for you)
- Update cognitive load if you misjudged initially
- Use "high" sparingly - reserve for truly complex work

**❌ Don't:**
- Confuse effort estimate (hours) with cognitive load (mental demand)
- Set everything to "high" just because it's important
- Ignore cognitive load - it defaults to medium but explicit is better

### For Using Energy Awareness

**✅ Do:**
- Check your daily summary each morning
- Trust the recommendations, especially when energy is low
- Override when you have information metrics don't (medication, urgency)
- Provide feedback to help improve recommendations
- Celebrate working WITH your energy instead of against it

**❌ Don't:**
- Ignore low-energy warnings - they protect against burnout
- Feel guilty about reduced targets on low-energy days
- Override constantly without providing reasons
- Push through when system suggests easier tasks (unless truly urgent)

### For ADHD Users

**🧠 ADHD-Optimized Strategies:**

**Low Energy Days:**
- Start with quick wins (≤2 hours) to build momentum
- Use checkbox tasks to maintain streak without burnout
- Admin work is perfect - clear, finite, satisfying to check off
- Personal tasks often feel easier when work energy is low

**High Energy Days:**
- Tackle the complex task you've been avoiding
- Use deep work time for architecture/design
- Don't waste peak energy on email
- Protect your focus window - batch admin for later

**Medication Timing:**
- Override to "high" when medication kicks in
- Block high-cognitive work during your peak window
- Set "low" when meds wear off, even if morning was productive
- Use feedback to train system on your medication patterns

**Pattern Recognition:**
- Track when overrides happen (time of day, after what events)
- Ask Coach: "When is my energy highest?"
- Ask Coach: "What tasks do I complete on high vs low energy days?"
- Use insights to plan your week strategically

---

## Technical Details

### Database Schema

**Tasks Table:**
```sql
cognitive_load TEXT CHECK(cognitive_load IN ('low', 'medium', 'high'))
```

**Daily Goals Table:**
```sql
adjusted_target_points INTEGER
readiness_score INTEGER
energy_level TEXT
adjustment_reason TEXT
```

**Energy Feedback Table:**
```sql
task_id INTEGER REFERENCES tasks(id)
suggested_energy_level TEXT
actual_energy_level TEXT
user_feedback TEXT
completed_successfully BOOLEAN
```

### Data Flow

```
Oura Ring → oura-mcp cache → getEnergyContext()
                                     ↓
                         mapReadinessToEnergyLevel()
                                     ↓
                         calculateEnergyScore() for each task
                                     ↓
                         rankTasksByEnergy()
                                     ↓
                         Return top N tasks to user
```

### Fallback Chain

```
1. Manual energy log from today (energy_states table)
   ↓ (if not found)
2. Today's Oura data from cache (~/.oura-cache/oura-health.db)
   ↓ (if not found)
3. Historical Oura data from energy_states
   ↓ (if not found)
4. Default to "medium" energy
```

### Files & Services

**Core Algorithm:**
- `mcp-servers/workos-mcp/src/services/energy-prioritization.ts`

**Oura Integration:**
- `mcp-servers/workos-mcp/src/services/oura-cache.ts`

**Database Schema:**
- `mcp-servers/workos-mcp/src/schema.ts`
- Migrations: `mcp-servers/workos-mcp/migrations/000*.sql`

**Tests:**
- Unit: `mcp-servers/workos-mcp/tests/services/energy-prioritization.test.ts`
- Integration: `mcp-servers/workos-mcp/tests/integration/energy-aware.test.ts`
- Fallback: `mcp-servers/workos-mcp/tests/integration/oura-fallback.test.ts`
- E2E: `mcp-servers/workos-mcp/tests/e2e/energy-workflow.test.ts`

---

## Troubleshooting

### "No energy data available"

**Cause:** No Oura data and no manual energy logs

**Solution:**
- Sync your Oura Ring
- Log energy manually: Create an entry in `energy_states` table
- System defaults to "medium" energy automatically

### "Tasks all have same score"

**Cause:** All tasks have same cognitive load (likely default "medium")

**Solution:** Set explicit `cognitiveLoad` on tasks:
```json
{ "tool": "workos_update_task", "args": { "taskId": 42, "cognitiveLoad": "high" }}
```

### "Override not affecting recommendations"

**Cause:** Need to re-fetch tasks after override

**Solution:**
1. Call `workos_override_energy_suggestion`
2. Then call `workos_get_energy_aware_tasks` to get updated rankings

### "Daily goal not adjusted"

**Cause:** No readiness score available

**Solution:**
- Ensure Oura Ring is synced
- Check `~/.oura-cache/oura-health.db` has today's data
- Manually trigger: `workos_adjust_daily_goal`

---

## Future Enhancements

The following features are planned for future iterations:

1. **Machine Learning Refinement**
   - Use `energy_feedback` data to personalize scoring algorithm
   - Learn individual patterns (e.g., user's "medium" != avg "medium")

2. **Time-of-Day Patterns**
   - Detect if you're a morning person or night owl
   - Suggest optimal times for high-cognitive work

3. **Calendar Integration**
   - Block high-focus time for complex tasks
   - Avoid scheduling meetings during peak energy windows

4. **Streak Protection**
   - Extra goal reduction to protect streaks on very low energy days
   - "Minimum viable day" mode

5. **Energy Forecasting**
   - Predict tomorrow's energy based on today's sleep score
   - Proactive task scheduling

---

## Questions?

For additional help:
- **Algorithm details**: See `src/services/energy-prioritization.ts`
- **Test examples**: See `tests/e2e/energy-workflow.test.ts`
- **Coach integration**: See `Agents/Coach.md` (pattern detection queries)
- **MCP tools**: See `mcp-servers/workos-mcp/README.md`

---

**Built for ADHD brains. Work with your energy, not against it.** 🧠✨
