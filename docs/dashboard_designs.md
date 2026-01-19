# Thanos Dashboard Design Specifications

## Design Philosophy

**ADHD-Optimized Principles:**
1. **Instant comprehension** - Status visible in under 2 seconds
2. **Energy-first** - Lead with what matters most for task selection
3. **Progress motivation** - Show momentum, not just numbers
4. **No cognitive load** - Emojis convey meaning, not decoration
5. **Dynamic context** - Changes based on time and state

---

## Data Sources

| Metric | Source | Update Frequency |
|--------|--------|------------------|
| Energy Level | Oura readiness score (85+=high, 70-84=medium, <70=low) | Daily |
| Sleep Score | Oura sleep cache | Daily |
| Readiness | Oura readiness cache | Daily |
| Points | WorkOS daily_goals.earned_points | Real-time |
| Target | WorkOS (adjusted by readiness) | Daily |
| Streak | WorkOS daily_goals.current_streak | Daily |
| Active Tasks | WorkOS tasks WHERE status='active' | Real-time |
| Clients | WorkOS distinct client_id from today's tasks | Real-time |

---

## Design Variations

### Design 1: Energy-Centric (Recommended)

**Philosophy:** Lead with energy state since it determines what tasks are appropriate.

```
HIGH [87] | 8/18 pts (44%) | 3 active | 7d
```

**Full format with streak celebration:**
```
HIGH [87] | 8/18 pts (44%) | 3 active | 7d
```

**Format string:**
```python
f"{energy_emoji} {energy_level.upper()} [{readiness}] | {earned}/{target} pts ({pct}%) | {active} active | {streak}d {streak_emoji}"
```

**Dynamic elements:**
- `energy_emoji`: (HIGH), (MEDIUM), (LOW)
- `streak_emoji`: (streak >= 7), (streak >= 14), (streak >= 30)
- Color coding: GREEN for high energy / on track, YELLOW for medium / behind, RED for low / struggling

**Examples by state:**

| State | Display |
|-------|---------|
| High energy, on track | `HIGH [87] | 12/21 pts (57%) | 2 active | 14d` |
| Medium energy, behind | `MED [74] | 4/18 pts (22%) | 5 active | 3d` |
| Low energy, protected | `LOW [62] | 6/14 pts (43%) | 1 active | 21d` |
| No Oura data | `MED [--] | 8/18 pts (44%) | 3 active | 7d` |

**Rationale:**
- Energy level is the gate for task selection
- Readiness score in brackets gives precision without clutter
- Points fraction shows progress at a glance
- Active task count tells you scope of current work
- Streak with fire emoji provides subtle motivation

---

### Design 2: Progress Bar Visual

**Philosophy:** Visual progress is more motivating than numbers for ADHD brains.

```
MED [74] | [====------] 40% | 3 tasks | 7d
```

**Format string:**
```python
filled = int(pct / 10)
bar = "=" * filled + "-" * (10 - filled)
f"{energy_emoji} {energy_level[:3].upper()} [{readiness}] | [{bar}] {pct}% | {active} tasks | {streak}d {streak_emoji}"
```

**Examples:**

| Progress | Display |
|----------|---------|
| 0% | `HIGH [85] | [----------] 0% | 4 tasks | 5d` |
| 50% | `MED [72] | [=====-----] 50% | 2 tasks | 12d` |
| 100%+ | `HIGH [88] | [==========] 115% | 0 tasks | 23d` |
| Minimum only | `LOW [65] | [====------] 40%* | 1 tasks | 8d` |

**Rationale:**
- Visual bar is instantly parsed
- Asterisk (*) after % indicates minimum-only pace
- Compact but visually engaging
- Good for terminal-heavy workflows

---

### Design 3: Time-Aware Context

**Philosophy:** Time of day context helps calibrate expectations.

```
AM | MED [74] | 4/18 pts | 3 active | 12d
```

**Time segments:**
- `AM` (6:00-11:59) - Morning momentum phase
- `MID` (12:00-14:59) - Midday maintenance
- `PM` (15:00-17:59) - Afternoon push
- `EVE` (18:00-21:59) - Evening wind-down
- `LATE` (22:00-5:59) - Rest indicator

**Format string:**
```python
f"{time_segment} | {energy_emoji} {energy_level[:3].upper()} [{readiness}] | {earned}/{target} pts | {active} active | {streak}d"
```

**Smart additions based on time:**
- Morning: Shows if on pace for the day
- Afternoon: Shows if minimum reached
- Evening: Shows if target hit, nudges rest

**Rationale:**
- Time context helps ADHD brains calibrate
- Different expectations for morning vs evening
- Implicit permission to rest when appropriate

---

### Design 4: Client Coverage Focus

**Philosophy:** For consulting/client work, client diversity matters.

```
HIGH [87] | 8 pts (3 clients) | 7d
```

**Format string:**
```python
f"{energy_emoji} {energy_level[:3].upper()} [{readiness}] | {earned} pts ({clients_touched} clients) | {streak}d {streak_emoji}"
```

**Client coverage indicator:**
- `(0 clients)` - No external client work yet
- `(1 client)` - Single client focus
- `(2+ clients)` - Good diversity
- `(3+ clients)` - Excellent coverage

**Rationale:**
- Points alone don't show client diversity
- Important for service businesses
- Quick check on business distribution

---

### Design 5: Minimal Zen Mode

**Philosophy:** Maximum information density, minimal visual noise.

```
87 | 8/18 | 3 | 7
```

**Expanded with labels on hover/request:**
```
R:87 | P:8/18 | T:3 | S:7
```

**Format string:**
```python
# Minimal
f"{readiness or '--'} | {earned}/{target} | {active} | {streak}"

# Labeled
f"R:{readiness or '--'} | P:{earned}/{target} | T:{active} | S:{streak}"
```

**Rationale:**
- For users who want extreme minimalism
- Relies on position memory
- Good for status bar integration
- Least distracting option

---

## Recommendation: Design 1 (Energy-Centric)

**Why Design 1 wins for ADHD:**

1. **Energy gates everything** - The most important decision for ADHD is "what CAN I do right now?" Energy answers that.

2. **Readiness precision** - The bracketed number gives actual data without requiring interpretation.

3. **Fraction is clearer than bar** - `8/18` instantly tells you "I need 10 more" - the bar requires counting.

4. **Streak with fire** - Subtle gamification that motivates without overwhelming.

5. **Active task count** - Helps with scope awareness ("I have 5 things going - no wonder I feel scattered").

**Implementation Notes:**

```python
def generate_dashboard_line(health: HealthMetrics, productivity: ProductivityMetrics) -> str:
    """Generate single-line dashboard for Thanos."""

    # Energy emoji and level
    energy_map = {
        "high": ("🟢", "HIGH"),
        "medium": ("🟡", "MED"),
        "low": ("🔴", "LOW"),
        None: ("⚪", "MED")
    }
    emoji, level = energy_map.get(health.energy_level, ("⚪", "MED"))

    # Readiness display
    readiness = f"[{health.readiness_score}]" if health.readiness_score else "[--]"

    # Points and percentage
    earned = productivity.points_earned
    target = productivity.target_points
    pct = int((earned / target) * 100) if target > 0 else 0

    # Streak with motivation emoji
    streak = productivity.current_streak
    if streak >= 30:
        streak_display = f"🏆 {streak}d"
    elif streak >= 14:
        streak_display = f"🔥 {streak}d"
    elif streak >= 7:
        streak_display = f"✨ {streak}d"
    elif streak > 0:
        streak_display = f"{streak}d"
    else:
        streak_display = "0d"

    # Combine
    return f"{emoji} {level} {readiness} | {earned}/{target} pts ({pct}%) | {productivity.active_tasks} active | {streak_display}"
```

---

## State-Based Variations

### Morning (6 AM - 12 PM)
```
🟢 HIGH [87] | 0/21 pts (0%) | 4 active | 14d 🔥
```
*Shows boosted target (+15%) for high energy day*

### Afternoon Behind (12 PM - 6 PM)
```
🟡 MED [74] | 6/18 pts (33%) ⚠️ | 3 active | 7d ✨
```
*Warning indicator when behind pace*

### Evening Wind-Down (6 PM+)
```
🟢 HIGH [85] | 19/18 pts (106%) ✅ | 0 active | 15d 🔥
```
*Checkmark shows target exceeded*

### Low Energy Protected Mode
```
🔴 LOW [62] | 8/14 pts (57%) | 1 active | 21d 🏆
```
*Shows reduced target (14 vs 18) to protect streak*

---

## Color Scheme (for Rich/Terminal)

| Element | High Energy | Medium Energy | Low Energy |
|---------|-------------|---------------|------------|
| Energy indicator | `[green]` | `[yellow]` | `[red]` |
| Points (on track) | `[green]` | `[white]` | `[white]` |
| Points (behind) | `[yellow]` | `[yellow]` | `[dim]` |
| Streak (active) | `[cyan]` | `[cyan]` | `[cyan]` |
| Streak (at risk) | `[red blink]` | `[red]` | `[red]` |

---

## Integration Points

### Shell Prompt Integration
```bash
# Add to .zshrc or .bashrc
thanos_status() {
    python /Users/jeremy/Projects/Thanos/commands/status/dashboard.py --minimal 2>/dev/null || echo "THANOS: offline"
}
PROMPT='$(thanos_status) > '
```

### tmux Status Bar
```bash
# In .tmux.conf
set -g status-right '#(python ~/Projects/Thanos/commands/status/dashboard.py --minimal)'
```

### Claude Code Session Start
```bash
# In hooks/thanos-status.sh
echo "$(python ~/Projects/Thanos/commands/status/dashboard.py)"
```

---

## Future Enhancements

1. **HRV Trend Indicator** - Arrow showing HRV direction (improving/declining)
2. **Meeting Awareness** - Dim/hide when in focus time
3. **Peak Window** - Show Vyvanse peak window if tracked
4. **Weekly Trend** - Mini sparkline of 7-day performance
5. **Client Names** - Show which clients touched today on expansion

---

## Summary Table

| Design | Best For | Char Width | Key Feature |
|--------|----------|------------|-------------|
| 1. Energy-Centric | General use, ADHD | ~50 chars | Energy gates decisions |
| 2. Progress Bar | Visual thinkers | ~55 chars | Instant visual feedback |
| 3. Time-Aware | Schedule-driven | ~52 chars | Contextual expectations |
| 4. Client Focus | Consultants | ~45 chars | Business distribution |
| 5. Minimal Zen | Minimalists | ~20 chars | Maximum density |

**Recommendation: Start with Design 1, allow user preference selection.**
