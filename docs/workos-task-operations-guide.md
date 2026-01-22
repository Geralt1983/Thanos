# WorkOS Task Operations Guide

**Quick reference for Raleigh client work tracking**

---

## Client IDs

| Client | ID | Color | Type |
|--------|----|----- |------|
| **Raleigh** | 7 | #3B82F6 (Blue) | Client |
| Orlando | 8 | #10B981 (Green) | Client |
| Memphis | 9 | #F59E0B (Orange) | Client |
| Kentucky | 10 | #8B5CF6 (Purple) | Client |
| Revenue | 11 | - | Internal |
| General Admin | 13 | - | Internal |

---

## MCP Tools

### Create Task

```typescript
workos_create_task({
  title: "Task description",
  clientId: 7,                    // Raleigh
  valueTier: "deliverable",       // quick-win | progress | deliverable | milestone | checkbox
  drainType: "mental",            // mental | physical | emotional
  effortEstimate: 3,              // 1-5 scale
  status: "active",               // active | queued | backlog | done
  cognitiveLoad: "high",          // low | medium | high (optional)
  description: "Details..."       // optional
})
```

**Value Tiers:**
- `checkbox` - Quick admin task (1-2pts)
- `quick-win` - Fast deliverable (2-3pts)
- `progress` - Solid progress (3-5pts)
- `deliverable` - Complete feature (5-8pts)
- `milestone` - Major achievement (8-13pts)

### Get Tasks

```typescript
// All active tasks
workos_get_tasks({ status: 'active' })

// Raleigh tasks only
workos_get_tasks({ status: 'active', clientId: 7 })

// All tasks for today
workos_get_tasks({ status: 'active', limit: 50 })

// Backlog
workos_get_tasks({ status: 'backlog', clientId: 7 })
```

### Complete Task

```typescript
workos_complete_task({
  taskId: 298,
  effortActual: 3,      // optional: 1-5 scale
  pointsFinal: 5        // optional: override AI guess
})
```

### Update Task

```typescript
workos_update_task({
  taskId: 298,
  status: 'queued',     // move to queue
  valueTier: 'milestone', // upgrade importance
  effortEstimate: 4     // adjust estimate
})
```

### Daily Summary

```typescript
workos_daily_summary()

// Returns:
// {
//   date: "2026-01-21",
//   earnedPoints: 12,
//   targetPoints: 18,
//   taskCount: 5,
//   breakdown: {
//     raleigh: 8,
//     orlando: 2,
//     personal: 2
//   },
//   streak: 3
// }
```

---

## Direct SQL Queries

### Recent Work (Last 10 Tasks)

```bash
sqlite3 ~/.workos-cache/cache.db \
  "SELECT id, title, status, value_tier, updated_at
   FROM cached_tasks
   WHERE client_id = 7
   ORDER BY updated_at DESC
   LIMIT 10;"
```

### Active Raleigh Tasks

```bash
sqlite3 ~/.workos-cache/cache.db \
  "SELECT id, title, value_tier, effort_estimate, drain_type
   FROM cached_tasks
   WHERE client_id = 7 AND status = 'active'
   ORDER BY sort_order, created_at;"
```

### Today's Progress

```bash
sqlite3 ~/.workos-cache/cache.db \
  "SELECT
     date,
     earned_points || '/' || target_points as progress,
     task_count,
     current_streak
   FROM cached_daily_goals
   WHERE date = date('now');"
```

### Completed Today

```bash
sqlite3 ~/.workos-cache/cache.db \
  "SELECT title, points_final, completed_at
   FROM cached_tasks
   WHERE client_id = 7
     AND DATE(completed_at) = DATE('now')
   ORDER BY completed_at DESC;"
```

### Client Workload

```bash
sqlite3 ~/.workos-cache/cache.db \
  "SELECT
     c.name,
     COUNT(CASE WHEN t.status = 'active' THEN 1 END) as active,
     COUNT(CASE WHEN t.status = 'queued' THEN 1 END) as queued,
     COUNT(CASE WHEN t.status = 'backlog' THEN 1 END) as backlog
   FROM cached_clients c
   LEFT JOIN cached_tasks t ON c.id = t.client_id
   WHERE c.is_active = 1
   GROUP BY c.id, c.name;"
```

---

## Task Status Workflow

```
backlog → queued → active → done
   ↑         ↓        ↓
   ←─────────┴────────┘
      (can move back)
```

**States:**
- `backlog` - Ideas/future work, not prioritized
- `queued` - Ready to work, waiting for capacity
- `active` - Currently in progress, limited to 3-5 tasks
- `done` - Completed and point-awarded

---

## Common Workflows

### Start New Raleigh Task

```typescript
// 1. Check current active count
const active = workos_get_tasks({ status: 'active', clientId: 7 });
console.log(`Currently active: ${active.length}/3`);

// 2. If room, move from queue
if (active.length < 3) {
  const queued = workos_get_tasks({ status: 'queued', clientId: 7, limit: 1 });
  workos_update_task({
    taskId: queued[0].id,
    status: 'active'
  });
}
```

### Complete and Move Next

```typescript
// 1. Complete current task
workos_complete_task({ taskId: 298, pointsFinal: 5 });

// 2. Check daily progress
const summary = workos_daily_summary();
console.log(`Progress: ${summary.earnedPoints}/${summary.targetPoints}`);

// 3. Auto-start next if under limit
const active = workos_get_tasks({ status: 'active', clientId: 7 });
if (active.length < 3) {
  const next = workos_get_tasks({ status: 'queued', clientId: 7, limit: 1 });
  if (next.length > 0) {
    workos_update_task({ taskId: next[0].id, status: 'active' });
  }
}
```

### End of Day Review

```typescript
// 1. Get summary
const summary = workos_daily_summary();

// 2. List uncompleted active tasks
const incomplete = workos_get_tasks({ status: 'active' });

// 3. Decision: keep active or return to queue
incomplete.forEach(task => {
  // If stalled, return to queue for tomorrow
  if (task.updatedAt < yesterday) {
    workos_update_task({ taskId: task.id, status: 'queued' });
  }
});
```

---

## Energy-Aware Task Selection

```typescript
// 1. Get current energy
const energy = workos_get_energy();
// Returns: { level: 'high' | 'medium' | 'low', source: 'oura' | 'manual' }

// 2. Get Raleigh tasks
const tasks = workos_get_tasks({ status: 'active', clientId: 7 });

// 3. Filter by cognitive load
const suitable = tasks.filter(task => {
  if (energy.level === 'high') return task.cognitiveLoad === 'high';
  if (energy.level === 'medium') return task.cognitiveLoad !== 'high';
  return task.cognitiveLoad === 'low';
});

// 4. Suggest top match
console.log(`Recommended: ${suitable[0].title}`);
```

---

## Brain Dump Integration

```typescript
// Capture loose thought about Raleigh work
workos_brain_dump({
  content: "Need to follow up with Dr. Sykes about transport scheduling issue",
  category: "task",
  context: "work"
});

// Later: Convert to task
const dumps = workos_get_brain_dumps({ processed: 0, limit: 10 });
const sykesDump = dumps.find(d => d.content.includes('Sykes'));

workos_create_task({
  title: "Follow up: Dr. Sykes transport scheduling",
  clientId: 7,
  valueTier: "progress",
  description: sykesDump.content,
  status: 'queued'
});

workos_mark_brain_dump_processed({ dumpId: sykesDump.id });
```

---

## Habit Tracking

```typescript
// Morning check-in
workos_habit_checkin({ timeOfDay: 'morning' });
// Returns habits due this morning with completion status

// Complete habit
workos_complete_habit({ habitId: 1 });

// Get habit stats
workos_get_habits();
// Returns all active habits with streaks
```

---

## Cache Management

### Check Cache Status

```bash
# Last sync time
sqlite3 ~/.workos-cache/cache.db \
  "SELECT value FROM cache_meta WHERE key = 'lastSyncAt';"

# Cache stats
sqlite3 ~/.workos-cache/cache.db \
  "SELECT
     (SELECT COUNT(*) FROM cached_tasks) as tasks,
     (SELECT COUNT(*) FROM cached_clients) as clients,
     (SELECT COUNT(*) FROM cached_habits) as habits;"
```

### Force Cache Refresh

```bash
cd /Users/jeremy/Projects/Thanos/mcp-servers/workos-mcp
npm run sync
```

### Clear Cache (Nuclear Option)

```bash
rm -rf ~/.workos-cache/cache.db*
# Next query will rebuild from Neon
```

---

## Troubleshooting

### Task Not Appearing

```bash
# Check if in cache
sqlite3 ~/.workos-cache/cache.db \
  "SELECT * FROM cached_tasks WHERE title LIKE '%ECT%';"

# If missing, force sync
cd mcp-servers/workos-mcp && npm run sync
```

### Points Not Updating

```bash
# Check daily goal record
sqlite3 ~/.workos-cache/cache.db \
  "SELECT * FROM cached_daily_goals WHERE date = date('now');"

# If stale, trigger sync
workos_daily_summary()  # This triggers cache check
```

### Client Not Found

```bash
# List all clients
sqlite3 ~/.workos-cache/cache.db \
  "SELECT * FROM cached_clients WHERE is_active = 1;"

# Raleigh should be ID 7
# If missing, check Neon database directly
```

---

## Example Session

```typescript
// Morning startup
const energy = workos_get_energy();
console.log(`Energy: ${energy.level} (Oura readiness: ${energy.ouraReadiness})`);

// Get Raleigh work
const tasks = workos_get_tasks({ status: 'active', clientId: 7 });
console.log(`Active Raleigh tasks: ${tasks.length}`);

// Pick task matching energy
const task = tasks.find(t => t.cognitiveLoad === energy.level);
console.log(`Working on: ${task.title}`);

// [... work happens ...]

// Complete task
workos_complete_task({ taskId: task.id, effortActual: 3 });

// Check progress
const summary = workos_daily_summary();
console.log(`Daily progress: ${summary.earnedPoints}/${summary.targetPoints} points`);

// Brain dump before break
workos_brain_dump({
  content: "Need to verify BCA backup report cross-mapping next",
  category: "task",
  context: "work"
});
```

---

## Quick Reference Card

| Need | Command |
|------|---------|
| **Create Raleigh task** | `workos_create_task({ title, clientId: 7, valueTier, status })` |
| **Get active tasks** | `workos_get_tasks({ status: 'active', clientId: 7 })` |
| **Complete task** | `workos_complete_task({ taskId, pointsFinal })` |
| **Daily summary** | `workos_daily_summary()` |
| **Brain dump** | `workos_brain_dump({ content, category: 'task' })` |
| **Check energy** | `workos_get_energy()` |
| **Force sync** | `cd workos-mcp && npm run sync` |
| **Direct SQL** | `sqlite3 ~/.workos-cache/cache.db "SELECT ..."` |

---

**Database Location:** `~/.workos-cache/cache.db`
**MCP Server:** `mcp-servers/workos-mcp/`
**Raleigh Client ID:** 7

**The tools exist. Execute.**
