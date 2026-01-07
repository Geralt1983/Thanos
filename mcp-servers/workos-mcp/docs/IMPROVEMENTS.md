# Thanos System Improvements - January 7, 2026

Three system improvements deployed via parallel agent swarm.

---

## 1. SQLite Cache Layer

**Location**: `src/cache/`
**Purpose**: Local caching for faster queries and offline fallback

### Architecture

```
┌─────────────────┐    ┌─────────────────┐
│  MCP Server     │───▶│  Neon (Remote)  │
│  (index.ts)     │    │  PostgreSQL     │
└────────┬────────┘    └─────────────────┘
         │
         │ cache miss / stale
         ▼
┌─────────────────┐
│  SQLite Cache   │
│  ~/.workos-cache│
│  /cache.db      │
└─────────────────┘
```

### Files

| File | Purpose |
|------|---------|
| `schema.ts` | Drizzle schema mirroring Neon tables |
| `cache.ts` | Cache manager (init, read, write, invalidate) |
| `sync.ts` | Neon → SQLite sync operations |
| `index.ts` | Re-exports for clean imports |

### Key Features

- **Write-through caching**: Updates hit Neon first, then sync to SQLite
- **Staleness threshold**: 15 minutes (configurable)
- **WAL mode**: Enabled for concurrent access
- **Indexed**: Status, client_id, completed_at for fast queries

### Usage in MCP Server

```typescript
import { initCache, getCachedTasks, isCacheStale } from "./cache/cache.js";
import { syncAll } from "./cache/sync.js";

// On startup
if (!cacheInitialized) {
  initCache();
  if (isCacheStale()) {
    await syncAll();
  }
}

// For reads - try cache first
const tasks = getCachedTasks("active", 50);
```

### Cache Statistics

```typescript
getCacheStats() → {
  taskCount: number,
  clientCount: number,
  dailyGoalCount: number,
  habitCount: number,
  lastSyncAt: string | null,
  isStale: boolean
}
```

---

## 2. Habit Tracking Improvements

**Location**: `src/schema.ts` + `drizzle/0001_add_habit_fields.sql`
**Purpose**: Better streak tracking and habit categorization

### New Fields

| Field | Type | Purpose |
|-------|------|---------|
| `last_completed_date` | date | Accurate streak tracking |
| `time_of_day` | text | morning/afternoon/evening/anytime |
| `category` | text | health/productivity/personal/etc |

### Migration

```sql
ALTER TABLE "habits" ADD COLUMN "last_completed_date" date;
ALTER TABLE "habits" ADD COLUMN "time_of_day" text DEFAULT 'anytime';
ALTER TABLE "habits" ADD COLUMN "category" text;
```

### Streak Fix Logic

Previous issue: Streaks broke when completing habits multiple times per day.

Fix: Use `last_completed_date` (date only, not timestamp) to determine if a day counts as completed, independent of completion count.

```typescript
// Streak increments only when:
// 1. last_completed_date is yesterday (consecutive day)
// 2. OR last_completed_date is null (first completion)
// Streak resets when:
// - last_completed_date is > 1 day ago
```

---

## 3. Vigilance Daemon

**Location**: `~/.claude/Tools/vigilance-daemon.js`
**Purpose**: Proactive monitoring and phone alerts via ntfy.sh

### Schedule

Runs via launchd every 2 hours (7am-9pm):
- 7am, 9am, 11am, 1pm, 3pm, 5pm, 7pm, 9pm

### Monitors

| Check | Alert Trigger | Thanos Quote |
|-------|---------------|--------------|
| Critical items (🔴) | `inevitable` | "I am inevitable" |
| Overdue commitments | `destiny` | "Dread it, run from it..." |
| Client staleness >7d | `snap` | "I'll do it myself" |
| Points behind pace | `hard` | "The hardest choices..." |
| Today's deadlines | `balanced` | "Perfectly balanced" |

### Alert Flow

```
Vigilance Daemon
      │
      ▼
  Parse sources:
  - Commitments.md
  - client_memory table
  - daily_goals table
      │
      ▼
  Prioritize & dedupe
      │
      ▼
  ~/bin/thanos-say <trigger>
      │
      ▼
  ntfy.sh → Phone notification
  (plays Thanos audio quote)
```

### Logs

| File | Purpose |
|------|---------|
| `~/.claude/Logs/vigilance/vigilance-YYYY-MM-DD.log` | Daily log |
| `~/.claude/Logs/vigilance/latest-summary.json` | Last run summary |

### Manual Test

```bash
/opt/homebrew/bin/node ~/.claude/Tools/vigilance-daemon.js
```

### launchd Plist

Location: `~/Library/LaunchAgents/com.jeremy.thanos-vigilance.plist`

Control:
```bash
launchctl load ~/Library/LaunchAgents/com.jeremy.thanos-vigilance.plist
launchctl unload ~/Library/LaunchAgents/com.jeremy.thanos-vigilance.plist
launchctl list | grep vigilance
```

---

## Deployment Status

| Component | Status | Verified |
|-----------|--------|----------|
| SQLite Cache | ✅ Integrated | Files exist, imports in index.ts |
| Habit Fields | ✅ Migrated | Confirmed in DB schema |
| Vigilance Daemon | ✅ Running | launchd loaded, logs generating |

---

## Future Improvements

1. **Cache**: Add TTL per entity type (tasks shorter, clients longer)
2. **Habits**: Add reminder times and notification integration
3. **Vigilance**: Add weekly summary, pattern detection (e.g., "you always fall behind on Mondays")
