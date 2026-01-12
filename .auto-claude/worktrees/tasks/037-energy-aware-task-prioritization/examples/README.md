# Energy-Aware Task Prioritization Examples

This directory contains practical Python examples demonstrating the energy-aware task prioritization system in Thanos. These examples show how to integrate health data (Oura Ring) with task management to optimize productivity for ADHD users.

## 📋 Overview

The energy-aware prioritization system helps you:
- **Match tasks to your energy level** - High-cognitive work when energized, admin work when tired
- **Adjust daily goals dynamically** - Reduce targets on low-energy days to prevent burnout
- **Respect your self-knowledge** - Override auto-detection when you know better (medication, urgency)
- **Learn from feedback** - System improves recommendations based on what actually works for you

## 🎯 Example Scripts

### 1. Morning Routine with Energy Check
**File:** `01_morning_routine.py`

**What it demonstrates:**
- Checking current energy context (Oura readiness + sleep scores)
- Automatically adjusting daily goals based on readiness
- Getting energy-matched task recommendations
- Planning your day based on your energy level

**When to use this:**
Start every day with this workflow to align your task list with your capacity.

**Run:**
```bash
python 01_morning_routine.py
```

**Sample Output:**
```
🌅 ENERGY-AWARE MORNING ROUTINE

STEP 1: Check Your Energy Context
🔍 Checking Oura Ring data and energy logs...

✅ Energy Context Retrieved:
   🔋 Energy Level: MEDIUM
   📊 Readiness Score: 77/100
   😴 Sleep Score: 75/100
   📡 Source: oura

STEP 2: Adjust Your Daily Goal
📏 Calculating optimal target for readiness 77...

✅ Daily Goal Adjusted:
   🎯 Original Target: 18 points
   🎯 Adjusted Target: 18 points
   📈 Adjustment: 0%

   💡 Coach Says:
   "Your readiness (77) is in the healthy baseline range. Maintaining standard daily target."

STEP 3: Get Energy-Matched Task Recommendations
🧠 Finding tasks that match your medium energy...

✅ Found 5 tasks ranked by energy match:

1. [MEDIUM] Update API documentation
   Score: 125/165 | ~3.0h | progress
   💡 Perfect match: Medium cognitive load for medium energy. Bonus: Progress tasks ideal for medium energy (+20).

...
```

---

### 2. Task Creation with Cognitive Load
**File:** `02_task_creation_with_cognitive_load.py`

**What it demonstrates:**
- How to choose appropriate cognitive load labels (high/medium/low)
- Creating tasks with cognitive load for better matching
- Updating cognitive load on existing tasks
- How cognitive load affects energy-aware recommendations

**When to use this:**
When creating new tasks or updating existing ones to enable energy-aware prioritization.

**Run:**
```bash
python 02_task_creation_with_cognitive_load.py
```

**Cognitive Load Guide:**

| Load | When to Use | Examples |
|------|-------------|----------|
| **🔴 HIGH** | Deep thinking, complex problems, creative work | "Architect microservice", "Debug memory leak", "Design new API" |
| **🟡 MEDIUM** | Moderate focus, following patterns, testing | "Write tests", "Code review", "Refactor module" |
| **🟢 LOW** | Routine tasks, admin work, communication | "Respond to emails", "Update dependencies", "File tickets" |

**Sample Output:**
```
📝 TASK CREATION WITH COGNITIVE LOAD

COGNITIVE LOAD GUIDE

How to choose cognitive load for your tasks:

🔴 HIGH COGNITIVE LOAD:
   • Deep thinking, complex problem-solving
   • Architecture decisions, system design
   • Learning new concepts or technologies
   Examples: 'Architect microservice', 'Debug memory leak', 'Design API'

🟡 MEDIUM COGNITIVE LOAD:
   • Moderate focus required
   • Following established patterns
   • Code reviews, documentation
   Examples: 'Write tests', 'Update docs', 'Refactor module'

🟢 LOW COGNITIVE LOAD:
   • Routine, repetitive tasks
   • Administrative work
   • Simple updates or fixes
   Examples: 'Respond to emails', 'Update dependencies', 'File tickets'

...

EXAMPLE 1: High Cognitive Load Task

Creating task with HIGH cognitive load...

📝 Task: Architect real-time notification system
🔴 Cognitive Load: high
💎 Value Tier: milestone
⏱️  Estimated: 8.0 hours
🧠 Drain Type: deep

✅ Task created with ID: 101

💡 Best scheduled for: HIGH energy days (readiness >= 85)
   This task will score highest when you're at peak performance.
```

---

### 3. Energy-Aware Daily Planning
**File:** `03_energy_aware_daily_planning.py`

**What it demonstrates:**
- Complete daily workflow from morning to evening
- Adapting plans as energy shifts throughout the day
- Overriding auto-detection (ADHD medication timing)
- Providing feedback to improve future recommendations

**When to use this:**
This shows a realistic full-day workflow with multiple energy checks and adjustments.

**Run:**
```bash
python 03_energy_aware_daily_planning.py
```

**Daily Timeline:**
```
8:00 AM  - Morning Planning (Medium Energy)
           ├─ Check Oura readiness
           ├─ Adjust daily goal
           └─ Get task recommendations

1:00 PM  - Mid-day Adjustment (Energy Dip)
           ├─ Recognize post-lunch low energy
           ├─ Switch to admin tasks
           └─ Build momentum with quick wins

3:00 PM  - Medication Override (Energy Boost)
           ├─ ADHD meds kick in
           ├─ Override to high energy
           └─ Tackle complex work

6:00 PM  - End of Day Feedback
           ├─ Review what worked
           ├─ Provide feedback on matches
           └─ Get insights for tomorrow
```

**Sample Output:**
```
📅 ENERGY-AWARE DAILY PLANNING

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
             🌅 MORNING PLANNING - 8:00 AM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Phase 1: Morning Energy Check & Planning

🔍 Checking energy context...

✅ Energy Context:
   🔋 Energy Level: MEDIUM
   📊 Readiness: 76/100
   😴 Sleep: 73/100
   💭 Not your best sleep, but you're functional

...

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
             💊 MEDICATION WINDOW - 3:00 PM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Phase 3: User Override (Medication Boost)

💊 User Input: 'I took my ADHD medication and it just kicked in.'
               'I feel focused and ready to tackle something more complex!'

🔧 Overriding energy detection...

✅ Energy Override Applied:
   🔋 New Energy Level: HIGH
   📊 Oura Readiness: 76 (unchanged)
   💡 Source: USER OVERRIDE (you know your body best!)

...
```

---

## 🚀 Getting Started

### Prerequisites

1. **Thanos MCP Server Running**
   ```bash
   cd mcp-servers/workos-mcp
   npm install
   npm run build
   npm start
   ```

2. **Oura Ring Data** (Optional)
   - Sync your Oura Ring via the oura-mcp server
   - Or use manual energy logs via `workos_log_energy`

3. **Python 3.7+**
   - Examples are pure Python with no dependencies
   - They simulate MCP tool calls for demonstration

### Running the Examples

All examples are self-contained and can run independently:

```bash
# Morning routine
python examples/01_morning_routine.py

# Task creation
python examples/02_task_creation_with_cognitive_load.py

# Full day planning
python examples/03_energy_aware_daily_planning.py
```

### Using in Production

These examples **simulate** MCP tool calls for demonstration purposes. To use the actual system:

1. **Through Claude Desktop** (recommended)
   - Configure the Thanos MCP server in Claude Desktop
   - Ask Claude: "Show me my energy-matched tasks"
   - Claude will call the MCP tools automatically

2. **Direct MCP Protocol** (advanced)
   - Send MCP requests via stdio to the server
   - See `mcp-servers/workos-mcp/README.md` for tool specifications

## 💡 Best Practices

### For ADHD Users

1. **Morning Routine**
   - Check energy FIRST before planning
   - Adjust daily goal based on readiness
   - Don't fight low energy days - adjust targets

2. **Cognitive Load Labeling**
   - High: Deep work requiring peak focus
   - Medium: Steady progress work
   - Low: Admin tasks for energy dips
   - When in doubt, start with "medium" and adjust

3. **Energy Monitoring**
   - Check energy 2-3 times per day
   - Morning (8-10 AM): Initial planning
   - Post-lunch (1-2 PM): Catch energy dips
   - Afternoon (3-5 PM): Medication windows

4. **Override When Needed**
   - Medication timing: Override to high when meds kick in
   - Deadline pressure: Override if urgency provides focus
   - Hyperfocus state: Capture it when it happens
   - Trust yourself over metrics

5. **Provide Feedback**
   - After completing tasks, rate the energy match
   - This teaches the system YOUR patterns
   - Algorithm learns medication timing, energy cycles, etc.

### Daily Workflow

```
🌅 Start of Day
   └─ Run 01_morning_routine.py or check energy in Claude
   └─ Get your energy-matched task list
   └─ Plan your morning based on energy

☀️ Mid-Day Check
   └─ If energy shifts, recheck recommendations
   └─ Switch to appropriate cognitive load tasks

💊 Medication Window (if applicable)
   └─ Override energy level when meds kick in
   └─ Tackle high-cognitive tasks during this window

🌙 End of Day
   └─ Provide feedback on task-energy matches
   └─ Review patterns and insights from Coach
```

## 🧪 Understanding the Algorithm

### Energy Level Mapping

| Readiness Score | Energy Level | Task Recommendations |
|----------------|--------------|---------------------|
| **85-100** | HIGH | Complex work, deep thinking, milestone tasks |
| **70-84** | MEDIUM | Steady progress, testing, documentation |
| **0-69** | LOW | Admin work, emails, quick wins, routine tasks |

### Task Scoring (0-165 points)

- **Perfect Match**: +100 points (cognitive load matches energy)
- **Value Tier Bonus**: +20 points (milestone/progress/checkbox)
- **Drain Type Bonus**: +10 points (deep/shallow/admin)
- **Effort Bonus**: +15 points (quick wins on low energy)
- **Active Task Bonus**: +5 points (finish what you started)

### Daily Goal Adjustment

- **Readiness ≥ 85**: +15% target (optional increase)
- **Readiness 70-84**: 0% (maintain standard target)
- **Readiness < 70**: -25% target (burnout prevention)

## 📚 Additional Resources

- **[Full Documentation](../docs/energy-aware-prioritization.md)** - Complete feature guide
- **[MCP Server README](../mcp-servers/workos-mcp/README.md)** - Tool specifications
- **[Coach Persona](../Agents/Coach.md)** - Pattern detection and explanations
- **[Tests](../mcp-servers/workos-mcp/tests/)** - Algorithm validation and examples

## 🤝 Contributing

Found an issue or have a suggestion? These examples are part of the Thanos codebase. Follow the project contribution guidelines.

## ⚡ Quick Reference

### Available MCP Tools

1. `workos_get_energy_aware_tasks` - Get ranked task recommendations
2. `workos_adjust_daily_goal` - Trigger daily goal adjustment
3. `workos_override_energy_suggestion` - Manual energy override
4. `workos_provide_energy_feedback` - Record task-energy feedback
5. `workos_create_task` - Create task with cognitive load
6. `workos_update_task` - Update task cognitive load
7. `workos_daily_summary` - Morning brief with energy context

### Energy Sources (Priority Order)

1. **Manual logs** - You logged energy today (highest priority)
2. **Oura readiness** - Today's Oura Ring data
3. **Historical** - Previous energy states
4. **Default** - Medium energy fallback

---

**Happy energy-aware planning! 🚀**

Work with your brain, not against it.
