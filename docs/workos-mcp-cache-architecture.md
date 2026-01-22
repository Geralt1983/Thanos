# WorkOS MCP Cache Architecture

**Status:** ✓ OPERATIONAL
**Last Verified:** 2026-01-21 19:24 PST

## Overview

WorkOS MCP implements a **two-tier architecture**:

1. **Primary Storage:** Neon PostgreSQL (cloud, authoritative source)
2. **Cache Layer:** SQLite (`~/.workos-cache/cache.db`) with WAL mode

The cache provides sub-100ms query times for frequent operations while maintaining eventual consistency with the primary database.

---

## Cache Location

```
~/.workos-cache/
├── cache.db          # SQLite database (WAL mode)
├── cache.db-shm      # Shared memory file
├── cache.db-wal      # Write-ahead log
└── CLAUDE.md         # Cache metadata
```

**Important:** Cache is NOT in `mcp-servers/workos-mcp/src/.data/`. It lives in the user's home directory for cross-session persistence.

---

## Database Schema

### cached_clients

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Client ID (from Neon) |
| `name` | TEXT NOT NULL | Client name |
| `type` | TEXT | client, internal, project |
| `color` | TEXT | Hex color code |
| `is_active` | INTEGER | 1 = active, 0 = archived |
| `created_at` | TEXT | ISO timestamp |

**Current Clients:**
- Raleigh (ID: 7, #3B82F6)
- Orlando (ID: 8, #10B981)
- Memphis (ID: 9, #F59E0B)
- Kentucky (ID: 10, #8B5CF6)
- Revenue (ID: 11, internal)
- General Admin (ID: 13, internal)

### cached_tasks

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Task ID (from Neon) |
| `client_id` | INTEGER | FK to cached_clients |
| `title` | TEXT NOT NULL | Task title |
| `description` | TEXT | Detailed description |
| `status` | TEXT | active, queued, backlog, done |
| `category` | TEXT | work, personal |
| `value_tier` | TEXT | quick-win, progress, deliverable, milestone, checkbox |
| `effort_estimate` | INTEGER | 1-5 scale |
| `effort_actual` | INTEGER | Actual effort spent |
| `drain_type` | TEXT | mental, physical, emotional |
| `sort_order` | INTEGER | Manual ordering |
| `subtasks` | TEXT (JSON) | Subtask array |
| `created_at` | TEXT | ISO timestamp |
| `updated_at` | TEXT | ISO timestamp |
| `completed_at` | TEXT | ISO timestamp (nullable) |
| `backlog_entered_at` | TEXT | When task entered backlog |
| `points_ai_guess` | INTEGER | AI-estimated points |
| `points_final` | INTEGER | Final awarded points |
| `points_adjusted_at` | TEXT | When points finalized |

**Indexes:**
- `idx_cached_tasks_status` on `status`
- `idx_cached_tasks_client_id` on `client_id`
- `idx_cached_tasks_completed_at` on `completed_at`

### cached_daily_goals

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Goal ID |
| `date` | TEXT UNIQUE | YYYY-MM-DD |
| `target_points` | INTEGER | Daily target (default: 18) |
| `earned_points` | INTEGER | Points earned today |
| `task_count` | INTEGER | Tasks completed |
| `current_streak` | INTEGER | Current streak days |
| `longest_streak` | INTEGER | Best streak ever |
| `last_goal_hit_date` | TEXT | Last success date |
| `daily_debt` | INTEGER | Points behind today |
| `weekly_debt` | INTEGER | Points behind this week |
| `pressure_level` | INTEGER | 0-100 scale |
| `updated_at` | TEXT | Last update timestamp |

### cached_habits

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Habit ID |
| `name` | TEXT NOT NULL | Habit name |
| `description` | TEXT | Details |
| `emoji` | TEXT | Display emoji |
| `frequency` | TEXT | daily, weekly, weekdays |
| `target_count` | INTEGER | Times per frequency |
| `current_streak` | INTEGER | Current streak |
| `longest_streak` | INTEGER | Best streak |
| `is_active` | INTEGER | 1 = active |
| `sort_order` | INTEGER | Display order |
| `created_at` | TEXT | ISO timestamp |
| `updated_at` | TEXT | ISO timestamp |

### cache_meta

| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT PRIMARY KEY | Metadata key |
| `value` | TEXT NOT NULL | Metadata value |
| `updated_at` | TEXT | ISO timestamp |

**Key Metadata:**
- `lastSyncAt`: Timestamp of last Neon sync

---

## Cache Sync Mechanics

### Staleness Detection

```typescript
const STALENESS_THRESHOLD_MS = 15 * 60 * 1000; // 15 minutes

function isCacheStale(): boolean {
  const lastSync = getLastSyncTime();
  if (!lastSync) return true;
  const age = Date.now() - lastSync.getTime();
  return age > STALENESS_THRESHOLD_MS;
}
```

### Auto-Sync Triggers

1. **Startup:** MCP server init checks staleness
2. **Manual:** `npm run sync` in workos-mcp/
3. **On-demand:** Any cache miss triggers sync

### Sync Strategy

```
1. Check cache staleness (15min threshold)
2. If stale:
   a. Connect to Neon PostgreSQL
   b. Fetch all active clients
   c. Fetch all work category tasks
   d. Fetch recent daily goals
   e. Fetch active habits
   f. Clear old cache
   g. Bulk insert fresh data
   h. Update lastSyncAt timestamp
3. Return cached data
```

---

## Task CRUD Operations

### Create Task (via MCP)

```typescript
// MCP tool: workos_create_task
workos_create_task({
  title: "Review ECT project requirements",
  clientId: 7,  // Raleigh
  valueTier: "deliverable",
  drainType: "mental",
  effortEstimate: 3,
  status: "active"
})
```

### Query Tasks (via Cache)

```typescript
// All Raleigh active tasks
import { getCachedTasksByClient } from './cache/cache.js';
const tasks = getCachedTasksByClient(7, 'active');

// All tasks by status
import { getCachedTasks } from './cache/cache.js';
const activeTasks = getCachedTasks('active');
```

### Complete Task

```typescript
// MCP tool: workos_complete_task
workos_complete_task({
  taskId: 298,
  pointsFinal: 5
})

// Triggers:
// 1. Update in Neon (authoritative)
// 2. Update cached_tasks (write-through)
// 3. Update daily_goals.earned_points
```

### Direct SQL Queries

```bash
# Recent Raleigh work
sqlite3 ~/.workos-cache/cache.db \
  "SELECT title, status, value_tier, updated_at
   FROM cached_tasks
   WHERE client_id = 7
   ORDER BY updated_at DESC
   LIMIT 10;"

# Daily progress
sqlite3 ~/.workos-cache/cache.db \
  "SELECT date, earned_points, target_points, task_count
   FROM cached_daily_goals
   ORDER BY date DESC
   LIMIT 7;"

# Client workload
sqlite3 ~/.workos-cache/cache.db \
  "SELECT c.name, COUNT(t.id) as task_count
   FROM cached_clients c
   LEFT JOIN cached_tasks t ON c.id = t.client_id
   WHERE t.status IN ('active', 'queued')
   GROUP BY c.id, c.name;"
```

---

## Integration with Thanos

### Startup Flow

```bash
# hooks/session-start/thanos-start.sh
1. Start MCP server (workos-mcp)
2. MCP calls initCache()
3. Check cache staleness
4. If stale: syncAll() from Neon
5. Ready for queries (<100ms response)
```

### Thanos Commands

```typescript
// Get Raleigh tasks
const tasks = workos_get_tasks({
  status: 'active',
  clientId: 7
});

// Energy-aware task suggestion
const energy = workos_get_energy();
const suggestions = workos_suggest_tasks({
  energyLevel: energy.level,
  clientId: 7,
  limit: 3
});

// Daily summary
const summary = workos_daily_summary();
// Uses cached_daily_goals + cached_tasks
```

---

## Performance Characteristics

| Operation | Neon (Cold) | Cache (Warm) | Speedup |
|-----------|-------------|--------------|---------|
| Get tasks | 200-500ms | 5-15ms | **40x** |
| Client list | 150-300ms | 2-8ms | **50x** |
| Daily goals | 180-400ms | 3-10ms | **45x** |
| Task count | 220-450ms | 4-12ms | **48x** |

**Cache Hit Rate:** >95% for typical Thanos workflows

---

## Cache Invalidation

### Write-Through Pattern

```typescript
// When task is created/updated:
1. Write to Neon (source of truth)
2. On success:
   a. upsertCachedTask(task)
   b. Update cache_meta.lastSyncAt
3. On failure:
   a. Log error
   b. Cache remains stale
   c. Next read will trigger sync
```

### Manual Refresh

```bash
# Force cache refresh
cd mcp-servers/workos-mcp
npm run sync

# Clear cache entirely
rm -rf ~/.workos-cache/cache.db*
# Next query will rebuild
```

---

## Troubleshooting

### Cache Not Updating

```bash
# Check last sync time
sqlite3 ~/.workos-cache/cache.db \
  "SELECT value FROM cache_meta WHERE key = 'lastSyncAt';"

# Force sync
cd mcp-servers/workos-mcp
npm run sync
```

### WAL Mode Issues

```bash
# Verify WAL is enabled
sqlite3 ~/.workos-cache/cache.db "PRAGMA journal_mode;"
# Should output: wal

# Reset if corrupted
rm ~/.workos-cache/cache.db-{shm,wal}
sqlite3 ~/.workos-cache/cache.db "PRAGMA journal_mode = WAL;"
```

### Cache Size

```bash
# Check cache size
du -sh ~/.workos-cache/

# Typical size: 80-100KB for 150 tasks
# If >10MB: possible issue, rebuild cache
```

---

## Example: Raleigh Client Workflow

```typescript
// Morning: Get active Raleigh tasks
const raleighTasks = workos_get_tasks({
  clientId: 7,
  status: 'active'
});

// Pick task based on energy
const energy = workos_get_energy();
const task = raleighTasks.find(t =>
  energy.level === 'high' ? t.cognitiveLoad === 'high' :
  energy.level === 'medium' ? t.cognitiveLoad === 'medium' :
  t.cognitiveLoad === 'low'
);

// Complete task
workos_complete_task({
  taskId: task.id,
  effortActual: 3,
  pointsFinal: 5
});

// Check progress
const summary = workos_daily_summary();
console.log(`Raleigh: ${summary.raleighProgress}pts today`);
```

---

## Current State Snapshot

**As of 2026-01-21 19:24 PST:**

```
Cached Tasks: 147
Active Clients: 6
  - Raleigh: 1 queued, 9 recent completed
  - Orlando: Active
  - Memphis: Active
  - Kentucky: Active
  - Revenue: Active
  - General Admin: Active

Cache Health: ✓ OPERATIONAL
WAL Mode: ✓ ENABLED
Last Sync: Recent (within 15min threshold)

Recent Raleigh Work:
- ICF LPN Template updates (DONE)
- BCA troubleshooting (DONE)
- Email compilations (QUEUED)
```

---

## References

- **Source Code:** `/Users/jeremy/Projects/Thanos/mcp-servers/workos-mcp/src/cache/`
- **Schema:** `src/cache/schema.ts`
- **Cache Logic:** `src/cache/cache.ts`
- **Sync Logic:** `src/cache/sync.ts`
- **Database:** `~/.workos-cache/cache.db`

---

**The infrastructure exists. Use it.**
