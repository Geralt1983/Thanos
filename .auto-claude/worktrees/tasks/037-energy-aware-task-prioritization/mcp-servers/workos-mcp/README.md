# WorkOS MCP Server

Model Context Protocol (MCP) server for Thanos productivity system. Provides intelligent task management with energy-aware prioritization designed for ADHD users.

## Overview

The WorkOS MCP server exposes tools for:
- **Task Management** - Create, update, and query tasks
- **Energy-Aware Prioritization** - Match tasks to your current energy level
- **Daily Goal Adjustment** - Automatically adjust targets based on readiness scores
- **Health Integration** - Leverage Oura Ring data for intelligent suggestions
- **Feedback Loop** - Learn from your energy-task matches over time

## Key Features

### 🧠 Energy-Aware Task Prioritization

Intelligently matches tasks to your current energy levels using:
- **Automatic energy detection** via Oura Ring readiness scores
- **Cognitive load tracking** (low, medium, high) on tasks
- **Smart scoring algorithm** (0-165 points) for energy-task matching
- **Dynamic daily goals** that adjust based on your capacity
- **User override capability** for medication windows and external factors

### 📊 ADHD-Optimized Features

- **Quick wins on low energy** - Build momentum with ≤2 hour tasks
- **Momentum bonuses** - Encourages finishing started work
- **Burnout prevention** - Automatic target reduction on low-energy days
- **Medication timing** - Override auto-detection when meds kick in
- **Pattern detection** - Coach persona analyzes energy-task completion patterns

---

## Available MCP Tools

### Energy-Aware Prioritization Tools

#### `workos_get_energy_aware_tasks`

Get tasks ranked by how well they match your current energy level.

**Parameters:**
- `energyLevel` (optional, string): Override auto-detection. Values: `"low"`, `"medium"`, `"high"`
- `limit` (optional, number): Maximum number of tasks to return

**Example Request:**
```json
{
  "tool": "workos_get_energy_aware_tasks",
  "args": {
    "limit": 5
  }
}
```

**Example Response:**
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
    },
    {
      "id": 38,
      "title": "Review pull request",
      "cognitiveLoad": "medium",
      "energyScore": 120,
      "matchReason": "Perfect match: Medium cognitive load for medium energy. Bonus: Quick win for building momentum."
    }
  ]
}
```

**Use Cases:**
- Morning planning: "What should I work on today?"
- Mid-day check-in: "What matches my current energy?"
- Override auto-detection when you know your energy better (medication, coffee, urgency)

---

#### `workos_adjust_daily_goal`

Manually trigger daily goal adjustment based on current energy/readiness.

**Parameters:**
- `baseTarget` (optional, number): Base target points. Default: `18`

**Example Request:**
```json
{
  "tool": "workos_adjust_daily_goal",
  "args": {
    "baseTarget": 18
  }
}
```

**Example Response:**
```json
{
  "originalTarget": 18,
  "adjustedTarget": 14,
  "adjustmentPercentage": -25,
  "energyLevel": "low",
  "readinessScore": 55,
  "sleepScore": 62,
  "reason": "Low readiness (55/100) - reduced target by 25% to prevent burnout and protect wellbeing. Sleep quality: 62/100."
}
```

**Adjustment Algorithm:**

| Readiness Score | Energy Level | Adjustment | Example |
|----------------|--------------|-----------|---------|
| **85-100** | high | **+15%** | 18 → 21 points |
| **70-84** | medium | **0%** | 18 → 18 points |
| **0-69** | low | **-25%** | 18 → 14 points |

**Use Cases:**
- Morning briefing: Automatically adjust today's goal
- Manual recalculation after override
- Check what your capacity is for the day

---

#### `workos_override_energy_suggestion`

Override auto-detected energy level when you know your energy better than metrics.

**Parameters:**
- `energyLevel` (required, string): Override value. Values: `"low"`, `"medium"`, `"high"`
- `reason` (required, string): Why you're overriding (helps future learning)
- `taskId` (optional, number): Specific task you're planning to work on
- `adjustDailyGoal` (optional, boolean): Recalculate daily target. Default: `true`

**Example Request:**
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

**Example Response:**
```json
{
  "override": {
    "energyLevel": "high",
    "reason": "ADHD medication just kicked in, have 3-hour focus window",
    "timestamp": "2026-01-12T10:30:00Z"
  },
  "energyContext": {
    "previousLevel": "low",
    "newLevel": "high",
    "readinessScore": 65,
    "sleepScore": 70
  },
  "goalAdjustment": {
    "originalTarget": 14,
    "adjustedTarget": 21,
    "adjustmentPercentage": 15,
    "reason": "Override to high energy - increased target by 15% to leverage peak energy window..."
  }
}
```

**Common Override Scenarios:**
- 🔥 **ADHD medication kicks in** - Oura shows low, but you feel focused
- 😴 **Distracted despite metrics** - Readiness high, but mentally exhausted
- ☕ **External factors** - Coffee, stressful news, deadline adrenaline
- 🎯 **Urgency overrides capacity** - Must finish complex task despite low energy

**Data Storage:**
Overrides are logged to `energy_states` table with "OVERRIDE:" prefix for future algorithm learning and Coach pattern detection.

---

#### `workos_provide_energy_feedback`

Record whether energy-based task suggestion was helpful. Data used to refine algorithm over time.

**Parameters:**
- `taskId` (required, number): Task that was completed
- `suggestedEnergyLevel` (required, string): What system suggested. Values: `"low"`, `"medium"`, `"high"`
- `actualEnergyLevel` (required, string): Your actual energy. Values: `"low"`, `"medium"`, `"high"`
- `completedSuccessfully` (required, boolean): Whether task was completed successfully
- `userFeedback` (optional, string): Additional notes

**Example Request (Perfect Match):**
```json
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
```

**Example Request (Mismatch):**
```json
{
  "tool": "workos_provide_energy_feedback",
  "args": {
    "taskId": 124,
    "suggestedEnergyLevel": "medium",
    "actualEnergyLevel": "low",
    "completedSuccessfully": false,
    "userFeedback": "Struggled with this, should have been marked low cognitive load"
  }
}
```

**Example Response:**
```json
{
  "feedbackRecorded": true,
  "task": {
    "id": 123,
    "title": "Architect new microservice",
    "cognitiveLoad": "high"
  },
  "energyMatch": {
    "suggested": "high",
    "actual": "high",
    "match": true,
    "delta": 0
  },
  "analysis": "Perfect energy match! High energy for high cognitive task led to successful completion. This validates the energy-aware prioritization algorithm."
}
```

**Why Provide Feedback:**
- Helps refine the energy-task matching algorithm
- Enables Coach to detect patterns in your energy-task completion
- Validates cognitive load assignments on tasks
- Identifies tasks that may need cognitive load updates

---

### Enhanced Existing Tools

#### `workos_create_task`

**New Parameter:**
- `cognitiveLoad` (optional, string): Mental effort required. Values: `"low"`, `"medium"`, `"high"`. Default: `"medium"`

**Example:**
```json
{
  "tool": "workos_create_task",
  "args": {
    "title": "Write technical architecture document",
    "cognitiveLoad": "high",
    "valueTier": "milestone",
    "drainType": "deep",
    "effortEstimate": 6
  }
}
```

**Cognitive Load Guidelines:**
- **`high`**: Complex problem-solving, architecture, creative work, deep debugging
- **`medium`**: Implementation from specs, code reviews, documentation, refactoring
- **`low`**: Admin tasks, email, scheduling, filing, data entry

---

#### `workos_update_task`

**New Parameter:**
- `cognitiveLoad` (optional, string): Update mental effort required. Values: `"low"`, `"medium"`, `"high"`

**Example:**
```json
{
  "tool": "workos_update_task",
  "args": {
    "taskId": 42,
    "cognitiveLoad": "medium"
  }
}
```

---

#### `workos_daily_summary`

**Enhanced Response:**
Now includes `energy` section with readiness, sleep scores, target adjustment, and top 5 energy-aware task recommendations.

**Example Response:**
```json
{
  "date": "2026-01-12",
  "energy": {
    "level": "medium",
    "readinessScore": 77,
    "sleepScore": 75,
    "source": "oura",
    "targetAdjustment": {
      "original": 18,
      "adjusted": 18,
      "difference": 0,
      "reason": "Good readiness (77/100) - maintaining standard target. Sleep quality: 75/100."
    }
  },
  "recommendations": [
    {
      "id": 42,
      "title": "Update API documentation",
      "cognitiveLoad": "medium",
      "energyScore": 125,
      "matchReason": "Perfect match: Medium cognitive load for medium energy..."
    }
  ],
  "tasks": {
    "total": 23,
    "completed": 5,
    "active": 8
  },
  "streakInfo": {
    "current": 12,
    "longestEver": 28
  }
}
```

---

## Workflows & Examples

### Morning Routine

**1. Get Daily Summary (includes energy context)**
```json
{ "tool": "workos_daily_summary" }
```

**2. Get Energy-Matched Tasks**
```json
{
  "tool": "workos_get_energy_aware_tasks",
  "args": { "limit": 5 }
}
```

**3. Override if Needed (e.g., medication)**
```json
{
  "tool": "workos_override_energy_suggestion",
  "args": {
    "energyLevel": "high",
    "reason": "ADHD meds kicked in, ready for complex work"
  }
}
```

### Task Creation with Cognitive Load

```json
{
  "tool": "workos_create_task",
  "args": {
    "title": "Design database schema for analytics",
    "cognitiveLoad": "high",
    "valueTier": "milestone",
    "drainType": "deep",
    "effortEstimate": 6
  }
}
```

### Providing Feedback After Task Completion

```json
{
  "tool": "workos_provide_energy_feedback",
  "args": {
    "taskId": 123,
    "suggestedEnergyLevel": "high",
    "actualEnergyLevel": "high",
    "completedSuccessfully": true,
    "userFeedback": "Perfect timing - completed in flow state"
  }
}
```

---

## Energy Detection & Fallback Chain

The system determines energy level using a **4-level priority fallback chain**:

1. **Manual energy log from today** (highest priority)
   - You explicitly logged your energy in `energy_states` table
2. **Today's Oura data from cache**
   - Reads from `~/.oura-cache/oura-health.db`
   - Auto-synced by oura-mcp server
3. **Historical energy states with Oura**
   - Previous days' energy logs that include readiness scores
4. **Default to "medium"** (graceful fallback)
   - System always works, even without any data

### Readiness to Energy Mapping

| Readiness Score | Energy Level |
|----------------|--------------|
| **85-100** | `high` |
| **70-84** | `medium` |
| **0-69** | `low` |

---

## Task Scoring Algorithm

Each task receives an **energy match score (0-165 points)** based on:

### Core Matching (+0 to +100 points)

- **Perfect match (+100)**: High energy → High cognitive load
- **Acceptable match (+50)**: High energy → Medium cognitive load
- **Poor match (0)**: High energy → Low cognitive load

### Bonus Points

**High Energy Bonuses:**
- Milestone/Deliverable tasks: +20
- Deep work: +10
- Large tasks (5+ hours): +10

**Medium Energy Bonuses:**
- Progress tier: +20
- Shallow work: +10
- Medium tasks (2-4 hours): +5

**Low Energy Bonuses:**
- Checkbox tier: +20
- Admin work: +10
- Quick wins (≤2 hours): +15
- Personal tasks: +5

**Universal Bonuses:**
- Active tasks: +5 (finish what you started)

---

## Database Schema

### Tasks Table

```sql
ALTER TABLE tasks ADD COLUMN cognitive_load TEXT
  CHECK(cognitive_load IN ('low', 'medium', 'high'))
  DEFAULT 'medium';
```

### Daily Goals Table

```sql
ALTER TABLE daily_goals ADD COLUMN adjusted_target_points INTEGER;
ALTER TABLE daily_goals ADD COLUMN readiness_score INTEGER;
ALTER TABLE daily_goals ADD COLUMN energy_level TEXT;
ALTER TABLE daily_goals ADD COLUMN adjustment_reason TEXT;
```

### Energy Feedback Table

```sql
CREATE TABLE energy_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER REFERENCES tasks(id),
  suggested_energy_level TEXT NOT NULL,
  actual_energy_level TEXT NOT NULL,
  user_feedback TEXT,
  completed_successfully BOOLEAN NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Architecture & Services

### Core Services

**Energy Prioritization Service** (`src/services/energy-prioritization.ts`):
- `getEnergyContext()` - Retrieve current energy from Oura/manual logs
- `mapReadinessToEnergyLevel()` - Convert readiness scores to energy levels
- `calculateEnergyScore()` - Score task-energy match (0-165 points)
- `rankTasksByEnergy()` - Sort tasks by energy score
- `calculateDailyGoalAdjustment()` - Compute target adjustment
- `applyDailyGoalAdjustment()` - Persist adjustment to database

**Oura Cache Service** (`src/services/oura-cache.ts`):
- Read-only access to `~/.oura-cache/oura-health.db`
- Fetches today's readiness and sleep scores
- Avoids file locking conflicts with oura-mcp server

### Tool Definitions & Handlers

**Task Tools** (`src/domains/tasks/`):
- Tool definitions in `tools.ts`
- Handlers in `handlers.ts`
- Route registration in `index.ts`

**Energy Tools** (`src/domains/energy/`):
- Override and feedback tools
- Specialized energy-aware handlers

---

## Testing

### Test Coverage

**Unit Tests** (`tests/services/energy-prioritization.test.ts`):
- Pure function testing
- Algorithm validation
- Edge cases (null values, empty arrays)
- Scoring accuracy (0-165 range)

**Integration Tests** (`tests/integration/energy-aware.test.ts`):
- MCP tool simulation
- Realistic task datasets
- High/medium/low energy scenarios
- Override functionality

**Fallback Tests** (`tests/integration/oura-fallback.test.ts`):
- Graceful degradation
- Oura API down scenarios
- Missing data handling
- Default fallback behavior

**E2E Tests** (`tests/e2e/energy-workflow.test.ts`):
- Complete user workflows
- Monday recovery day (low energy)
- Friday sprint day (high energy)
- ADHD medication override scenarios

### Running Tests

```bash
# Run all tests
npx tsx tests/**/*.test.ts

# Run specific test suite
npx tsx tests/services/energy-prioritization.test.ts
npx tsx tests/integration/energy-aware.test.ts
npx tsx tests/e2e/energy-workflow.test.ts
```

---

## Best Practices

### Setting Cognitive Load

**✅ Do:**
- Set based on **mental effort**, not time
- Use "high" sparingly - reserve for truly complex work
- Update if you misjudged initially
- Consider your own baseline

**❌ Don't:**
- Confuse effort estimate (hours) with cognitive load (mental demand)
- Set everything to "high" just because it's important
- Ignore cognitive load - explicit is better than default "medium"

### Using Energy Awareness

**✅ Do:**
- Check daily summary each morning
- Trust recommendations, especially when energy is low
- Override when you have info metrics don't (medication, urgency)
- Provide feedback to improve recommendations
- Celebrate working WITH your energy

**❌ Don't:**
- Ignore low-energy warnings (they prevent burnout)
- Feel guilty about reduced targets on low-energy days
- Override constantly without reasons
- Push through when system suggests easier tasks (unless urgent)

### ADHD-Specific Tips

**Low Energy Days:**
- Start with quick wins (≤2 hours) to build momentum
- Use checkbox tasks to maintain streak without burnout
- Admin work is perfect - clear, finite, satisfying
- Personal tasks often feel easier when work energy is low

**High Energy Days:**
- Tackle the complex task you've been avoiding
- Use deep work time for architecture/design
- Don't waste peak energy on email
- Protect your focus window - batch admin for later

**Medication Timing:**
- Override to "high" when medication kicks in
- Block high-cognitive work during peak window
- Set "low" when meds wear off
- Use feedback to train system on medication patterns

---

## Documentation

### Additional Resources

- **[Energy-Aware Prioritization Guide](../../docs/energy-aware-prioritization.md)** - Comprehensive documentation
- **[Coach Persona Documentation](../../Agents/Coach.md)** - Energy pattern detection
- **[Test Documentation](./tests/)** - Test suite details and examples

### Related Systems

- **[Oura MCP Server](../oura-mcp/)** - Health data integration
- **[Coach Agent](../../Agents/Coach.md)** - AI persona for insights
- **[Briefing Engine](../../Tools/briefing_engine.py)** - Morning brief integration

---

## Troubleshooting

### "No energy data available"

**Cause:** No Oura data and no manual energy logs

**Solution:**
- Sync your Oura Ring
- Log energy manually in `energy_states` table
- System defaults to "medium" automatically

### "Tasks all have same score"

**Cause:** All tasks have default "medium" cognitive load

**Solution:**
```json
{ "tool": "workos_update_task", "args": { "taskId": 42, "cognitiveLoad": "high" }}
```

### "Override not affecting recommendations"

**Cause:** Need to re-fetch tasks after override

**Solution:**
1. Call `workos_override_energy_suggestion`
2. Then call `workos_get_energy_aware_tasks` to get updated rankings

---

## Future Enhancements

Planned features for future iterations:

1. **Machine Learning Refinement**
   - Use `energy_feedback` data to personalize scoring
   - Learn individual patterns and preferences

2. **Time-of-Day Patterns**
   - Detect morning person vs night owl
   - Suggest optimal times for high-cognitive work

3. **Calendar Integration**
   - Block focus time for complex tasks
   - Avoid meetings during peak energy windows

4. **Streak Protection**
   - Extra goal reduction to protect streaks on very low energy days
   - "Minimum viable day" mode

5. **Energy Forecasting**
   - Predict tomorrow's energy from today's sleep score
   - Proactive task scheduling

---

## Contributing

When adding new MCP tools:

1. Define tool schema in `src/domains/*/tools.ts`
2. Implement handler in `src/domains/*/handlers.ts`
3. Register in domain's `index.ts` router
4. Add unit tests in `tests/services/`
5. Add integration tests in `tests/integration/`
6. Update this README with tool documentation

---

## License

Part of the Thanos productivity system.

**Built for ADHD brains. Work with your energy, not against it.** 🧠✨
