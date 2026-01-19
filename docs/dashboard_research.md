# Thanos Dashboard UX Research Report

**Date**: 2026-01-19
**Researcher**: UX Research Agent
**Focus**: ADHD-optimized terminal dashboard design

---

## Executive Summary

This research analyzes the existing Thanos dashboard implementation, available data sources, and ADHD-specific UX requirements to inform a redesign that maximizes glanceability and reduces cognitive load.

---

## 1. Available Data Points and Update Frequency

### 1.1 Health Data (Oura MCP)

| Data Point | Source | Update Frequency | Current Usage |
|------------|--------|------------------|---------------|
| Readiness Score | `get_daily_readiness` | Once daily (overnight) | Yes - displayed |
| Sleep Score | `get_daily_sleep` | Once daily | Yes - displayed |
| HRV Balance | Readiness contributors | Once daily | No - available but unused |
| Resting Heart Rate | Readiness contributors | Once daily | No - available but unused |
| Sleep Regularity | Readiness contributors | Once daily | No - unused |
| Recovery Index | Readiness contributors | Once daily | No - unused |
| Activity Balance | Readiness contributors | Once daily | No - unused |
| Stress Data | `get_daily_stress` | Real-time (when available) | No - often empty |
| Activity Data | `get_daily_activity` | Real-time | No - unused |

**Key Finding**: Oura provides rich contributor data (9 sub-scores) that are currently ignored. The readiness score alone hides valuable context about WHY energy is low.

### 1.2 Productivity Data (WorkOS MCP)

| Data Point | Source | Update Frequency | Current Usage |
|------------|--------|------------------|---------------|
| Points Earned | `workos_get_today_metrics` | Real-time | Yes |
| Target Points | `workos_get_streak` | Daily (adjusted) | Yes |
| Adjusted Target | `workos_get_streak` | On energy change | Partial |
| Pace Status | `workos_get_today_metrics` | Real-time | No - unused |
| Streak Count | `workos_get_streak` | Daily | Yes |
| Active Tasks Count | `workos_get_tasks` | Real-time | Yes |
| Clients Touched | `workos_get_today_metrics` | Real-time | No - unused |
| Total External Clients | `workos_get_today_metrics` | Static | No - unused |
| Daily Debt | `workos_get_streak` | Daily | No - unused |
| Weekly Debt | `workos_get_streak` | Weekly | No - unused |
| Pressure Level | `workos_get_streak` | Calculated | No - unused |
| Energy Level | `workos_get_energy` | On change/manual | Partial |
| Habits | `workos_get_habits` | Real-time | No - unused |
| Brain Dumps | `workos_get_brain_dump` | Real-time | No - unused |

**Key Finding**: WorkOS provides pace status, debt tracking, and pressure level that could drive urgency indicators. The "clients touched" metric is valuable for ADHD users who need variety.

### 1.3 Derived/Calculated Metrics

| Metric | Calculation | ADHD Relevance |
|--------|-------------|----------------|
| Energy Level | Readiness score thresholds | HIGH - primary routing signal |
| Percent of Target | earned/target * 100 | MEDIUM - progress indicator |
| Percent of Minimum | earned/minimum * 100 | HIGH - "safety net" visibility |
| Pace Status | Points vs time of day | HIGH - urgency signal |
| Time Until EOD | Now vs 6pm | MEDIUM - time pressure |

---

## 2. Current Dashboard Limitations

### 2.1 Information Architecture Issues

1. **Flat Hierarchy**: All metrics displayed at equal visual weight
   - Energy level should dominate as the primary routing signal
   - Points progress gets equal space to streak (which is 0)

2. **Missing Context**:
   - Shows readiness=63 but not WHY (sleep balance=45, recovery=49)
   - Shows points=7/18 but not pace (behind/ahead/on-track)
   - No time-of-day context

3. **No Actionable Guidance**:
   - Dashboard shows state but doesn't suggest next action
   - Missing "what should I do next" quick-access

4. **Static Single View**:
   - One-size-fits-all display
   - No progressive disclosure (summary vs. detail)

### 2.2 ADHD-Hostile Patterns

| Issue | Impact | Current State |
|-------|--------|---------------|
| Too many numbers | Overwhelm, analysis paralysis | 6+ numbers displayed |
| No visual hierarchy | Everything competes for attention | Flat pipe-separated list |
| Missing urgency cues | Time blindness not addressed | No pace/time indicators |
| No emotional feedback | Missed dopamine opportunities | Neutral presentation |
| Dense layout | Cognitive overload | Single cramped line |

### 2.3 Technical Issues

1. **Watch Mode Refresh**: 30-second default is too slow for feeling "live"
2. **Error Handling**: Silent failures when data unavailable
3. **No Caching**: Re-fetches all data even when unchanged
4. **Single Format**: Can't switch between compact/expanded views

---

## 3. ADHD-Specific UX Recommendations

### 3.1 Information Hierarchy (Priority Order)

**Tier 1 - Instant Glance (< 1 second)**
1. Energy State - Single dominant visual (color block or large indicator)
2. Progress Ring - Points as visual progress, not numbers
3. Pace Indicator - "on track" / "behind" / "crushing it"

**Tier 2 - Quick Scan (2-3 seconds)**
4. Active Task Count - How many things in flight
5. Streak (if > 0) - Gamification motivator
6. Time Context - "Morning deep work" / "Afternoon admin"

**Tier 3 - Detail on Demand**
7. Specific scores (readiness, sleep)
8. Contributor breakdown (why energy is low)
9. Client touch status
10. Debt/pressure metrics

### 3.2 Visual Design Principles

```
+--[ ADHD Dashboard Design Principles ]--+

1. COLOR AS PRIMARY SIGNAL
   - Green/Yellow/Red zones immediately visible
   - Energy level = dominant color theme
   - Avoid blue (too neutral, no urgency)

2. PROGRESS OVER NUMBERS
   - Use progress bars instead of "7/18"
   - Visual fill is faster to parse than math
   - Show "how far to go" not "how much done"

3. CELEBRATE SMALL WINS
   - Animate/highlight when points increase
   - Show "+2" badges when tasks complete
   - Micro-celebrations for reaching milestones

4. TIME BLINDNESS COMPENSATION
   - Always show current time prominently
   - Show "3hrs until EOD" not just the time
   - Pace indicator: "need 2pts/hr to hit target"

5. REDUCE DECISION FATIGUE
   - One obvious "next action" suggestion
   - Hide complexity behind expand gesture
   - Default to most important, not most complete

+----------------------------------------+
```

### 3.3 Recommended Layout (80-column terminal)

```
COMPACT VIEW (default - 3 lines)
+==============[ THANOS ]==============+
| [###----] 39%     HIGH     3 tasks  |
| Need 2 pts/hr  |  Memphis waiting   |
+=====================================+

EXPANDED VIEW (on keypress - 8 lines)
+==============[ THANOS ]==============+
|                                     |
|   ENERGY: HIGH      PROGRESS: 39%   |
|   [===============----]  7/18 pts   |
|                                     |
|   Ready: 63  Sleep: 64  Streak: 0   |
|   Pace: BEHIND (need 2 pts/hr)      |
|   Tip: Memphis not touched today    |
|                                     |
+=====================================+
```

### 3.4 Micro-Interactions for ADHD

| Trigger | Feedback | Purpose |
|---------|----------|---------|
| Task complete | Flash green, show "+X pts" | Dopamine hit |
| Hit daily target | Celebration animation | Achievement recognition |
| Behind pace | Gentle amber pulse | Non-anxious urgency |
| Streak continues | Fire emoji grows | Gamification |
| Energy drops | Suggest break | Self-care nudge |

---

## 4. Data Hierarchy Recommendations

### 4.1 What's Most Important at a Glance

**CRITICAL (Always Visible)**
1. Energy Level - Determines what tasks are appropriate
2. Progress Toward Goal - Am I winning today?
3. Pace Status - Am I falling behind?

**IMPORTANT (Visible in Compact)**
4. Active Task Count - What's on my plate
5. Time Context - Morning/afternoon/evening

**SECONDARY (Expanded View Only)**
6. Specific Scores - Readiness, sleep numbers
7. Streak Count - Gamification (only if > 0)
8. Client Coverage - Who needs attention

**HIDDEN (Detail Drill-Down)**
9. Contributor Breakdown - Why is readiness low
10. Historical Trends - Week/month patterns
11. Debt Metrics - Accumulated shortfall

### 4.2 Energy-Aware Display Modes

| Energy | Dashboard Theme | Emphasis |
|--------|-----------------|----------|
| HIGH | Green accents | Show challenging tasks, maximize potential |
| MEDIUM | Yellow accents | Balance, suggest mix of task types |
| LOW | Red/amber accents | Protect energy, show only easy wins |

---

## 5. Technical Constraints

### 5.1 Terminal Limitations

| Constraint | Value | Impact |
|------------|-------|--------|
| Minimum Width | 80 columns | Must fit standard terminal |
| Maximum Width | 120 columns | Can expand on wide terminals |
| Color Support | 256 colors (Rich) | Full color available |
| Unicode Support | Full emoji | Use sparingly (alignment issues) |
| Refresh Rate | 100ms minimum | Rich Live supports smooth updates |
| Line Height | Fixed | Cannot use sub-line positioning |

### 5.2 Performance Considerations

| Operation | Current Latency | Target |
|-----------|-----------------|--------|
| Oura data fetch | ~500ms (cached SQLite) | < 100ms |
| WorkOS data fetch | ~200ms (async PostgreSQL) | < 100ms |
| Full refresh | ~700ms | < 200ms |
| Watch mode update | 30s interval | 5-10s for responsiveness |

### 5.3 Rich Library Capabilities

Available components that could enhance the dashboard:
- `Panel` - Bordered sections with titles (currently used)
- `Table` - Structured data display
- `Progress` - Progress bars and spinners
- `Live` - Real-time updates (currently used)
- `Layout` - Multi-column layouts
- `Text` - Styled text with markup
- `Columns` - Side-by-side content
- `Sparkline` - Mini trend charts (via `rich-pixels`)

---

## 6. Recommended Implementation Approach

### 6.1 Phase 1: Core Improvements

1. **Add progress bar** instead of "7/18 pts"
2. **Add pace indicator** ("behind" / "on track")
3. **Color-code energy** as dominant visual
4. **Add time context** ("2:30pm - 3.5hrs left")

### 6.2 Phase 2: ADHD Optimizations

5. **Tiered display** - compact default, expand on demand
6. **Next action suggestion** - "Work on Memphis task"
7. **Client coverage indicator** - who needs attention
8. **Celebration animations** - task completion feedback

### 6.3 Phase 3: Advanced Features

9. **Contributor drill-down** - why energy is what it is
10. **Historical sparklines** - mini trends
11. **Habit integration** - show habit streaks
12. **Brain dump count** - unprocessed thoughts indicator

---

## 7. Key Insights from EnergyAwareRouting Workflow

The existing workflow (`/Skills/Orchestrator/workflows/EnergyAwareRouting.md`) provides valuable algorithms that should inform dashboard design:

1. **Energy-Task Matrix**: Dashboard should visualize the match between current energy and available tasks

2. **Time-of-Day Adjustment**: Dashboard should reflect whether it's "deep work time" (morning) vs "admin time" (afternoon)

3. **Client Touch Bonus**: Dashboard should highlight clients not touched today

4. **Prioritization Algorithm**: Dashboard could show the top recommended task based on this algorithm

5. **Override Flow**: Dashboard should make energy override easy to access

---

## 8. Appendix: Sample Data Structures

### Current Dashboard Data (from MCP calls)

```json
{
  "health": {
    "readiness": 63,
    "sleep": 64,
    "contributors": {
      "sleep_balance": 45,
      "recovery_index": 49,
      "hrv_balance": 52,
      "sleep_regularity": 85
    }
  },
  "productivity": {
    "earned": 7,
    "target": 18,
    "adjusted_target": 21,
    "minimum": 12,
    "pace": "behind",
    "percent_of_target": 39,
    "streak": 0,
    "active_tasks": 1,
    "clients_touched": 1,
    "total_clients": 4
  },
  "derived": {
    "energy_level": "medium",
    "time_of_day": "afternoon",
    "hours_remaining": 3.5,
    "points_per_hour_needed": 3.1
  }
}
```

### Recommended Display Priority

```
Priority 1: energy_level (MEDIUM)
Priority 2: percent_of_target (39%) as progress bar
Priority 3: pace (behind)
Priority 4: active_tasks (1)
Priority 5: hours_remaining (3.5)
Priority 6: clients_touched vs total (1/4)
Priority 7: readiness/sleep scores
Priority 8: streak (hidden if 0)
```

---

## 9. References

- `/Users/jeremy/Projects/Thanos/commands/status/dashboard.py` - Current implementation
- `/Users/jeremy/Projects/Thanos/Tools/rich_output.py` - Rich formatting utilities
- `/Users/jeremy/Projects/Thanos/Skills/Orchestrator/workflows/EnergyAwareRouting.md` - Energy routing logic
- `/Users/jeremy/Projects/Thanos/docs/terminal-styling-spec.md` - Existing terminal styling spec

---

*End of Research Report*
