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
6. [Examples & Workflows](#examples--workflows)
7. [Best Practices](#best-practices)

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
