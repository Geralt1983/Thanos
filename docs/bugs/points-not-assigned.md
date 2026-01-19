# Bug Report: pointsFinal NULL on Task Completion

## Status: PARTIALLY FIXED

## Summary
When tasks are marked as completed, `pointsFinal` was staying NULL. This caused:
- Daily metrics to show wrong earned points
- `clientsTouchedToday` to be incorrect
- Points not being recorded at completion time

## Investigation Findings

### Location of Bug Fix
**File**: `/Users/jeremy/Projects/Thanos/mcp-servers/workos-mcp/src/domains/tasks/handlers.ts`

**Lines 455-461** - Points mapping constant:
```typescript
const POINTS_BY_TIER: Record<string, number> = {
  checkbox: 2,
  progress: 4,
  deliverable: 6,
  milestone: 8,
};
```

**Lines 473-544** - `handleCompleteTask` function

### Current Code (Lines 505-517)
The fix has been implemented. The handler now:
1. Fetches the existing task to check `pointsFinal` and `valueTier` (lines 488-496)
2. Calculates `pointsFinal` from `valueTier` if not already set (lines 505-508):
```typescript
const pointsFinal = existingTask.pointsFinal ??
  POINTS_BY_TIER[existingTask.valueTier || 'checkbox'] ??
  POINTS_BY_TIER.checkbox;
```
3. Sets `pointsFinal` in the update (line 516):
```typescript
.set({
  status: "done",
  completedAt: new Date(),
  updatedAt: new Date(),
  pointsFinal,  // <-- Now being set
})
```

## Points Mapping
| valueTier | Points |
|-----------|--------|
| checkbox | 2 |
| progress | 4 |
| deliverable | 6 |
| milestone | 8 |

## Remaining Issues to Investigate

### 1. Historical Tasks with NULL pointsFinal
Tasks completed before this fix still have `pointsFinal = NULL`. Need to:
- Run a migration/backfill to calculate points for historical tasks
- Use: `pointsFinal = POINTS_BY_TIER[valueTier] ?? 2`

### 2. Daily Metrics Calculation
The `handleGetTodayMetrics` function (line 86) uses `calculateTotalPoints()` which has this fallback chain:
```typescript
// From /mcp-servers/workos-mcp/src/shared/utils.ts line 85-86
export function calculatePoints(task: Task): number {
  return task.pointsFinal ?? task.pointsAiGuess ?? task.effortEstimate ?? 2;
}
```

This means daily metrics WILL work even with NULL `pointsFinal` by falling back to `pointsAiGuess`, `effortEstimate`, or default of 2. However, this may give inconsistent results if valueTier differs from these fallbacks.

### 3. Cache Synchronization
The cache sync (`syncSingleTask`) is called after the database update, so the cache should receive the correct `pointsFinal` value.

## Verification Steps
1. Complete a new task and verify `pointsFinal` is populated
2. Check `handleGetTodayMetrics` returns correct `earnedPoints`
3. Consider backfilling historical completed tasks

## Related Files
- `/mcp-servers/workos-mcp/src/domains/tasks/handlers.ts` - Task handlers
- `/mcp-servers/workos-mcp/src/shared/utils.ts` - Points calculation utilities
- `/mcp-servers/workos-mcp/src/schema.ts` - Task schema (pointsFinal field at line 39)
- `/mcp-servers/workos-mcp/src/cache/sync.ts` - Cache synchronization

## Conclusion
The bug fix is already in place in the codebase. If `pointsFinal` is still NULL for newly completed tasks, the issue may be:
1. Running an older/cached version of the MCP server
2. A different code path completing tasks
3. Database connection issues preventing the update

Recommend: Restart the MCP server and test completing a fresh task.
