# Unified Task Management Architecture

## Executive Summary

Thanos is a **life management system**, not just a work management system. Personal tasks (home projects, errands, family commitments) belong in the same architecture as work tasks because:

1. **Unified Memory** - Tasks stored outside our architecture can't be recalled contextually
2. **Intelligent Surfacing** - I can suggest the right task based on energy, time, context
3. **ADHD Optimization** - One place to check, nothing falls through cracks
4. **Cross-Domain Awareness** - Understanding total load (work + personal) enables better prioritization

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────┐
                    │              THANOS (Intelligence)          │
                    │   • Classification • Routing • Surfacing    │
                    └─────────────────────┬───────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
              ▼                           ▼                           ▼
      ┌───────────────┐          ┌───────────────┐          ┌───────────────┐
      │    WorkOS     │          │  claude-mem   │          │     Oura      │
      │   (Tasks DB)  │          │   (Memory)    │          │   (Health)    │
      │               │          │               │          │               │
      │ ├── work      │◄────────►│ • Context     │          │ • Readiness   │
      │ │   └ clients │          │ • History     │          │ • Sleep       │
      │ │             │          │ • Patterns    │          │ • HRV         │
      │ ├── personal  │          │ • Learnings   │          └───────────────┘
      │ │   └ home    │          └───────────────┘
      │ │   └ family  │
      │ │   └ health  │
      │ │             │
      │ └── habits    │
      └───────────────┘
```

---

## Task Domains

### Work Tasks (category: "work")

**Characteristics:**
- Linked to clients (clientId)
- Billable/trackable hours
- Value tiers matter (checkbox → milestone)
- Cognitive load tracking for energy matching
- Visible in daily work summaries

**Schema Fields Used:**
```typescript
{
  clientId: number,        // Required for work
  valueTier: string,       // checkbox, progress, deliverable, milestone
  drainType: string,       // deep, shallow, admin
  cognitiveLoad: string,   // low, medium, high
  pointsFinal: number      // Billable value
}
```

### Personal Tasks (category: "personal")

**Characteristics:**
- No client association (clientId: null)
- Not billable
- Simpler value model (usually checkbox)
- Still energy-aware
- Context metadata for intelligent surfacing

**Current Schema (sufficient):**
```typescript
{
  clientId: null,
  category: "personal",
  valueTier: "checkbox",     // Most personal tasks are simple
  drainType: string,         // Still useful for energy matching
  cognitiveLoad: string,     // low/medium/high
  description: string        // Rich context storage
}
```

**Context in Description (convention):**
```
Location: Kitchen
Materials: New grill brush, degreaser
For: House maintenance
Blocked: Need to buy brush first
```

---

## Memory Integration Pattern

### Task Creation Flow

```
User Input ──► Brain Dump ──► Classifier ──► Classification
                                                    │
                    ┌───────────────────────────────┤
                    │                               │
                    ▼                               ▼
              personal_task                    work_task
                    │                               │
                    ▼                               ▼
            WorkOS (personal)              WorkOS (work + client)
                    │                               │
                    └───────────────────────────────┤
                                                    ▼
                                            claude-mem (context)
```

### Memory Storage for Personal Tasks

When creating personal tasks, store enriched context in memory:

```
Observation: "Home project: Hang towel rack in Corin's bathroom"
  - Location: Upstairs bathroom
  - For: Corin
  - Type: Home improvement
  - Tools needed: Drill, level, wall anchors
  - Related: Bathroom renovation series
```

This enables queries like:
- "What home projects are waiting?"
- "What did I promise Corin I'd do?"
- "What needs the drill?"

### Memory Recall Pattern

Before surfacing tasks:
1. Query WorkOS for active/backlog personal tasks
2. Query claude-mem for enriched context on each
3. Combine for intelligent presentation

```python
# Pseudo-flow
tasks = workos.get_tasks(category="personal", status="backlog")
for task in tasks:
    context = memory.search(task.title)
    task.enriched_context = context
return prioritize(tasks, energy_level, time_of_day)
```

---

## Context-Aware Surfacing Rules

### Time-Based Context

| Time | Mode | Suggest |
|------|------|---------|
| Weekday 9am-5pm | Work mode | Work tasks only (unless explicitly asked) |
| Weekday evening | Personal time | Personal tasks, especially quick wins |
| Weekend | Mixed | Both, prefer personal projects |
| Late night (after 10pm) | Recovery | Only if explicitly requested |

### Energy-Based Context

| Energy | Personal Task Types |
|--------|---------------------|
| High (85+) | Complex projects (ceiling fan, organizing) |
| Medium (70-84) | Standard tasks (grill cleaning, errands) |
| Low (<70) | Simple checkbox items only, or defer |

### Surfacing Examples

**User asks: "What should I do tonight?"**
```
[Check: Time=7pm, Day=Thursday, Energy=72]

### DESTINY // 7:00 PM

Evening. Medium energy. The universe suggests:

Personal sacrifices within reach:
[ ] Clean grill (low drain, 20 min)
[ ] Review weekend plans

Home projects (better for weekend):
[ ] Hang Corin's towel rack (needs drill, focused time)
[ ] Install ceiling fan (high effort, needs ladder)

Work can wait until tomorrow. The balance demands rest.
```

**User asks: "What home projects are pending?"**
```
Query: WorkOS personal tasks + memory context

### HOME PROJECTS // Backlog

Active (tonight):
[ ] Clean grill - Low drain

Waiting:
[ ] Hang Corin's towel rack - Upstairs bathroom
    └ Need: Drill, level, wall anchors
[ ] Install ceiling fan - [which room?]
    └ Note: Need to confirm room, may need electrician

The projects await their moment.
```

---

## Implementation: No Schema Changes Needed

The current architecture **already supports** personal tasks correctly:

1. **WorkOS `tasks` table** has `category` field (work/personal)
2. **Brain dump classifier** distinguishes personal_task vs work_task
3. **`life_get_personal_tasks`** tool exists and works
4. **Memory** can store enriched context about any task

**What needs to happen:**

1. **Convention**: Store rich context in task `description` field
2. **Memory**: Store related context as observations
3. **Surfacing**: Thanos applies time/energy rules when suggesting

---

## Personal Task Metadata Convention

Since we don't need schema changes, use structured description:

```markdown
## Task: Hang Corin's towel rack

**Location:** Upstairs bathroom (Corin's)
**For:** Corin
**Materials:** Towel rack (purchased), wall anchors, screws
**Tools:** Drill, level, stud finder
**Blocked:** None
**Estimated time:** 30 minutes
**Notes:** She mentioned wanting this done before her parents visit
```

Or compact format for simple tasks:
```
Location: Kitchen | Est: 20min | Tools: Grill brush
```

---

## Recall Queries

### "What home projects need doing?"
```
1. WorkOS: life_get_personal_tasks(status="backlog")
2. Filter: Tasks with "project" indicators (tools, location, materials)
3. Enrich: Search memory for each task title
4. Present: Grouped by complexity/readiness
```

### "What did I say I'd do for Corin?"
```
1. Memory: search("Corin commitment promise")
2. WorkOS: search personal tasks for "Corin"
3. Combine and present
```

### "What can I do in 15 minutes?"
```
1. WorkOS: active + queued personal tasks
2. Filter: cognitiveLoad=low, estimated_effort=quick
3. Present top 3
```

---

## Migration: Current Personal Tasks

The 3 tasks I just created are already in WorkOS with `category: "personal"`.

They're fine where they are. What we should do going forward:

1. **Richer capture**: When you mention a home project, I'll ask clarifying questions:
   - What room/location?
   - What tools/materials needed?
   - Who is it for?
   - Any blockers?

2. **Memory storage**: I'll create memory observations for rich context

3. **Intelligent recall**: When you ask about projects, I'll pull from both systems

---

## Summary

**Keep personal tasks in WorkOS.** The architecture already supports it. What changes:

| Before | After |
|--------|-------|
| Create task with minimal info | Ask clarifying questions, store rich context |
| Tasks exist in isolation | Memory observations link related context |
| Manual recall ("show backlog") | Intelligent surfacing based on time/energy/context |
| Flat list | Grouped by domain (home, family, health, errands) |

The system isn't broken. It just needs me to be smarter about capture and surfacing.

---

*Document created: 2026-01-22*
*Next: Implement memory observation patterns for personal task context*
