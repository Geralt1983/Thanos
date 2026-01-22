# Operator Daemon Monitors - Implementation Summary

**Date:** 2026-01-20
**Status:** ✅ Complete - All Three Monitors Implemented
**Location:** `/Users/jeremy/Projects/Thanos/Operator/monitors/`

---

## Implementation Overview

Three monitoring components have been implemented for the Operator daemon, following the architecture specified in `ARCHITECTURE.md`:

1. **Health Monitor** (`health.py`) - Oura health metrics
2. **Task Monitor** (`tasks.py`) - WorkOS task deadlines
3. **Pattern Monitor** (`patterns.py`) - Behavioral patterns

All monitors follow the standardized Alert structure and implement graceful error handling.

---

## 1. Health Monitor (`monitors/health.py`)

### Purpose
Monitor Oura Ring health metrics and alert on low readiness, poor sleep, and stress indicators.

### Data Source
- **Primary:** `~/.oura-cache/oura-health.db` (SQLite cache)
- **Fallback:** Direct Oura MCP calls (not yet implemented)
- **Schema:**
  ```
  readiness_data: id, day, data (JSON), cached_at, expires_at
  sleep_data: id, day, data (JSON), cached_at, expires_at
  ```

### Alert Triggers

| Metric | Warning Threshold | Critical Threshold | Severity |
|--------|------------------|-------------------|----------|
| Readiness Score | < 65 | < 50 | warning/critical |
| Sleep Hours | < 6.0h | < 5.0h | warning/critical |
| HRV Deviation | -15% | -25% | warning/critical |
| Stress Level | > 75 | > 85 | warning/critical |

### Alert Examples

**Warning:**
```
Title: Low Readiness Detected
Message: Your readiness is 62 (Low). Consider lighter tasks today.
Severity: warning
Dedup Key: health:readiness:warning:2026-01-20
```

**Critical:**
```
Title: Critical: Severe Sleep Debt
Message: You slept only 4.8 hours (target: 7-9h). Severe sleep debt detected.
Severity: critical
Dedup Key: health:sleep:critical:2026-01-20
```

### Implementation Notes

- ✅ Cache-first strategy for performance
- ✅ JSON blob parsing from Oura cache
- ✅ Graceful degradation on errors (returns empty list)
- ⚠️  HRV baseline calculation not yet implemented
- ⚠️  Stress data not available in current cache schema
- ⚠️  MCP fallback not yet implemented

### Integration Status

- [x] Circuit breaker integration
- [x] SQLite cache reading
- [x] JSON parsing of Oura data
- [ ] Direct MCP fallback
- [ ] HRV baseline tracking

---

## 2. Task Monitor (`monitors/tasks.py`)

### Purpose
Monitor WorkOS tasks for deadlines, overdue items, and milestone tracking.

### Data Source
- **Primary:** WorkOS MCP server (not yet integrated)
- **Expected:** PostgreSQL database via WorkOS MCP
- **Future:** Local cache for offline operation

### Alert Triggers

| Check Type | Condition | Severity | Time of Day |
|------------|-----------|----------|-------------|
| Overdue Tasks | Past deadline | high | Any |
| Due Today | Deadline today | medium | 9am, 2pm |
| Due Tomorrow | Deadline tomorrow | low | 6pm |
| Milestone Overdue | Milestone past due | critical | Any |
| Task Pile-Up | 10+ active tasks | medium | 9am |

### Alert Examples

**High Priority:**
```
Title: 3 Overdue Tasks
Message: You have 3 overdue task(s): Memphis report, Raleigh follow-up, Orlando docs
Severity: high
Dedup Key: task:overdue:2026-01-20
```

**Critical:**
```
Title: Milestone Overdue
Message: Critical: Milestone 'Q1 Planning Document' is overdue. This was a committed deliverable.
Severity: critical
Dedup Key: task:milestone:task_123
```

### Implementation Notes

- ✅ Alert structure and logic implemented
- ✅ Time-of-day filtering for appropriate notifications
- ✅ Milestone detection (valueTier: "milestone")
- ✅ Task pile-up detection
- ⚠️  WorkOS MCP integration pending
- ⚠️  Cache fallback not implemented

### Integration Status

- [x] Circuit breaker integration
- [x] Alert generation logic
- [x] Deadline parsing
- [ ] WorkOS MCP connection
- [ ] Local cache fallback

---

## 3. Pattern Monitor (`monitors/patterns.py`)

### Purpose
Detect procrastination patterns, recurring worries, and stale priorities.

### Data Sources
- `State/brain_dumps.json` - Recurring worries and unprocessed thoughts
- `State/CurrentFocus.md` - Focus areas and priority staleness

### Pattern Detection

| Pattern Type | Threshold | Lookback | Severity |
|--------------|-----------|----------|----------|
| Procrastination | Same task 3+ times | 7 days | medium |
| Recurring Worry | Same entity 3+ times | 7 days | medium |
| Stale Focus | No update | 7+ days | medium |
| High Anxiety | 5+ worries | 7 days | warning |

### Alert Examples

**Procrastination:**
```
Title: Procrastination Pattern Detected
Message: You've mentioned 'call mom' 4 times in the past 7 days without taking action. Block time to complete it?
Severity: medium
Dedup Key: pattern:procrastination:call mom
```

**Recurring Worry:**
```
Title: Recurring Worry Detected
Message: You've expressed concern about 'mom' 3 times recently. This may need attention or action.
Severity: medium
Dedup Key: pattern:recurring_worry:mom
```

**Stale Focus:**
```
Title: Stale Focus Priorities
Message: Your CurrentFocus.md hasn't been updated in 8 days. Time for a priority review?
Severity: medium
Dedup Key: pattern:stale_focus:2026-01-20
```

### Implementation Notes

- ✅ Brain dump pattern analysis
- ✅ Recurring worry detection
- ✅ Stale focus checking
- ✅ File-based data sources (no external dependencies)
- ✅ Entity extraction from parsed data
- ✅ High anxiety volume detection

### Integration Status

- [x] JSON file parsing
- [x] Pattern matching algorithms
- [x] Entity counting and analysis
- [x] File modification time tracking
- [x] All features implemented

---

## Shared Alert Structure

All monitors use the standardized `Alert` dataclass:

```python
@dataclass
class Alert:
    type: str              # 'health', 'task', 'pattern'
    severity: str          # 'info', 'warning', 'critical'
    title: str             # Brief alert title
    message: str           # Detailed message
    data: Dict[str, Any]   # Additional context
    timestamp: str         # ISO-8601 timestamp
    dedup_key: Optional[str] = None  # For deduplication
    priority: Optional[str] = None   # Maps to severity
```

### Deduplication Keys

Each alert includes a `dedup_key` to prevent spam:

- **Health:** `health:{metric}:{severity}:{date}`
- **Tasks:** `task:{check_type}:{identifier}`
- **Patterns:** `pattern:{pattern_type}:{entity}`

Deduplication window: **1 hour** (configurable)

---

## Error Handling Strategy

All monitors implement graceful degradation:

```python
async def check(self) -> List[Alert]:
    try:
        # Monitor logic
        return alerts
    except Exception as e:
        logger.error(f"Monitor check failed: {e}", exc_info=True)
        return []  # Empty list, not failure
```

### Benefits

- Daemon continues running even if one monitor fails
- Circuit breakers prevent cascading failures
- Comprehensive logging for debugging
- No user-facing errors

---

## Testing Results

### Dry Run Test
```bash
python3 Operator/daemon.py --dry-run --once --verbose
```

**Output:**
```
✓ HealthMonitor initialized
✓ TaskMonitor initialized
✓ PatternMonitor initialized
Initialized with 3 monitors, 0 alerters

Check cycle complete: 0 alerts sent (0.00s)
```

### Current Limitations

1. **Health Monitor:**
   - Cache database may be empty (no recent Oura data)
   - MCP fallback not implemented
   - HRV baseline calculation pending

2. **Task Monitor:**
   - WorkOS MCP integration not yet connected
   - Needs MCP server communication protocol
   - Cache fallback pending

3. **Pattern Monitor:**
   - ✅ Fully functional
   - Depends on brain_dumps.json having data
   - Works with file system only

---

## Next Steps

### Immediate (High Priority)

1. **WorkOS MCP Integration**
   - Connect TaskMonitor to WorkOS MCP server
   - Implement MCP protocol calls
   - Add local cache fallback

2. **Oura MCP Integration**
   - Implement direct MCP fallback for HealthMonitor
   - Handle empty cache gracefully
   - Add HRV baseline calculation

3. **Alerter Implementation**
   - Telegram alerter for high/critical
   - macOS notification alerter
   - Journal logger (always-on)

### Future Enhancements

1. **Energy-Task Matching**
   - Cross-reference health data with task assignments
   - Alert when high-cognitive tasks scheduled on low-energy days

2. **Advanced Patterns**
   - Burnout risk score (combine multiple metrics)
   - Client balance tracking
   - Context switching detection

3. **Machine Learning**
   - Personalized threshold learning
   - Predictive deadline alerts
   - Smart scheduling suggestions

---

## File Structure

```
Operator/
├── daemon.py                    # Main daemon process
├── monitors/
│   ├── __init__.py             # Monitor exports
│   ├── health.py               # ✅ Health Monitor (implemented)
│   ├── tasks.py                # ✅ Task Monitor (implemented)
│   └── patterns.py             # ✅ Pattern Monitor (implemented)
├── alerters/                   # TODO: Implement alerters
│   └── __init__.py
├── config.yaml                 # Configuration
└── ARCHITECTURE.md             # Architecture documentation
```

---

## Configuration

Monitors are configured in `Operator/config.yaml`:

```yaml
monitors:
  health:
    enabled: true
    thresholds:
      readiness_critical: 50
      readiness_warning: 65
      sleep_hours_critical: 5.0
      sleep_hours_warning: 6.0

  tasks:
    enabled: true
    checks:
      - overdue_tasks
      - due_today
      - due_tomorrow
      - commitment_violations

  patterns:
    enabled: true
    lookback_days: 7
    thresholds:
      procrastination_count: 3
      stale_focus_days: 7
```

---

## Logging

All monitors use structured logging:

```python
logger.info(f"Health checks complete: {len(alerts)} alerts generated")
logger.warning("No health data available - skipping health checks")
logger.error(f"Health monitor check failed: {e}", exc_info=True)
```

Log levels:
- **DEBUG:** Detailed diagnostics
- **INFO:** Normal operations
- **WARNING:** Non-critical issues (graceful degradation)
- **ERROR:** Failures with recovery

---

## Summary

✅ **All three monitors successfully implemented**
✅ **Graceful error handling throughout**
✅ **Standardized Alert structure**
✅ **Circuit breaker integration**
✅ **Comprehensive logging**
⚠️  **MCP integration pending (WorkOS & Oura)**
⚠️  **Alerters not yet implemented**

The foundation is solid. Next phase: MCP integration and alerter implementation.
