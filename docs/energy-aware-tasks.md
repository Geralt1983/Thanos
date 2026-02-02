# Energy-Aware Task System

Automatically weights all tasks against your Oura energy levels. Complex tasks are deferred on low-energy days; simple tasks surface when you're tired.

## Philosophy

**Your body knows better than your calendar.**

If your Oura readiness is 45, you shouldn't be tackling complex architecture work. The system enforces this automatically.

## How It Works

### 1. Energy State (Oura)
- **Readiness score** (primary signal)
- Sleep score
- Activity score

### 2. Task Sources
- **WorkOS** - Work tasks with points/client
- **Todoist** - Personal tasks

### 3. Complexity Classification
Tasks are auto-classified as:
- **Simple** (●): Email, calls, updates, quick reviews
- **Moderate** (●●): Writing, analysis, coordination, planning
- **Complex** (●●●): Implementation, architecture, migration, building

Classification uses:
- Keywords in title
- Point values (WorkOS)
- Manual override possible

### 4. Energy Matching
- **High energy (70+)**: All tasks available
- **Moderate energy (50-69)**: Simple + moderate tasks
- **Low energy (<50)**: Simple tasks only, defer complex

## Usage

### Command Line
```bash
cd ~/Projects/Thanos
.venv/bin/python Tools/energy_aware_tasks.py
```

### Output
```
============================================================
ENERGY-AWARE TASK RECOMMENDATIONS
============================================================

Energy State: MODERATE (Readiness: 60)
Sleep: 56 | Activity: 69

🔋 Moderate energy (readiness 60). Handle 0 moderate tasks. 
Save complex work for higher energy days.

────────────────────────────────────────────────────────────
MATCHED TO YOUR ENERGY (8 tasks)
────────────────────────────────────────────────────────────
💼 ● [Memphis] Orion updates - especially the Lab/Rad
💼 ● [Raleigh] Import Harry emails into NotebookLM
🏠 ● Do dishes
🏠 ● Put up drinks from store

────────────────────────────────────────────────────────────
DEFER UNTIL HIGHER ENERGY (1 tasks)
────────────────────────────────────────────────────────────
💼 ●●● [Orlando] PCT: Migrate Alabama records to TST
```

### Integrated into Briefs
Morning briefs automatically include energy-aware recommendations (see `skills/Productivity/references/briefs.md`).

### On-Demand via Chat
Just ask:
- "What should I work on?"
- "Show me my tasks"
- "What matches my energy?"

I'll run the system and present recommendations.

## Complexity Rules

You can customize classification by editing `Tools/energy_aware_tasks.py`:

```python
self.complexity_keywords = {
    'simple': ['email', 'call', 'schedule', 'update', ...],
    'moderate': ['write', 'analyze', 'document', ...],
    'complex': ['implement', 'architect', 'design', 'migrate', ...]
}
```

## Energy Thresholds

Current thresholds (editable in code):
- **Low energy**: Readiness < 50
- **Moderate energy**: Readiness 50-69
- **High energy**: Readiness ≥ 70

## Future Enhancements

Planned:
- [ ] Learn complexity from user feedback
- [ ] Time-of-day energy curves
- [ ] Historical pattern analysis (e.g., "Mondays are always high energy")
- [ ] Integration with calendar (block complex tasks on low-energy days)
- [ ] Auto-reschedule deferred tasks to predicted high-energy days

## Philosophy Notes

### Why This Matters
ADHD + variable energy = productivity disaster without guardrails.

You'll **always** feel like you should be doing the hardest thing. Your brain lies. Your Oura ring doesn't.

### The Defer Mechanism
Deferred tasks aren't "failed tasks." They're **smartly queued** for when your body can actually handle them.

Readiness 45 trying to implement a complex system = frustration, poor quality, burnout.  
Readiness 75 tackling that same task = flow state, quality work, satisfaction.

### Energy Budgeting
Think of energy like money:
- Simple tasks cost 1 energy
- Moderate tasks cost 3 energy
- Complex tasks cost 10 energy

Low-energy day (readiness 50) = 15 energy budget total.  
You can do 15 simple tasks OR 5 moderate tasks OR 1-2 complex tasks.

The system prevents you from overspending.

## Troubleshooting

**"I have high energy but system says defer"**
- Check if task points are misclassified
- Update complexity keywords for your domain
- Manual override: do it anyway, but note if it drained you

**"System says I can do complex tasks but I'm exhausted"**
- Oura might be lagging (sleep last night doesn't always show until noon)
- Trust your body over the ring
- Use `/quiet` to suppress recommendations until you recover

**"Personal tasks not showing"**
- Check Todoist CLI: `todoist today`
- Verify tasks are in "today" view
- Check `.env` has TODOIST token

**"Work tasks not showing"**
- Verify WorkOS database connection
- Check `.env` has WORKOS_DATABASE_URL
- Test: `.venv/bin/python -c "from Tools.adapters.workos import WorkOSAdapter; import asyncio; asyncio.run(WorkOSAdapter().call_tool('get_tasks', {'status': 'active'}))"`

## Files

- **Main system**: `Tools/energy_aware_tasks.py`
- **Morning brief integration**: `skills/Productivity/references/briefs.md`
- **Heartbeat integration**: `HEARTBEAT.md`
- **Memory**: `MEMORY.md` (Energy-Aware Task System section)

---

**Remember: Tasks are ALWAYS weighted against energy. No exceptions. Your body decides the priority, not your ambition.**
