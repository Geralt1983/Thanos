# Habit Tracker — Trend-Based

**Core Principle: No streaks. No points. No badges. No gamification.**

Gamification exploits ADHD dopamine-seeking. Streaks feel amazing until they break, then the system gets abandoned.

## Trend Language

- "4 of the last 7 days" — not "4-day streak"
- "Trending up" — not "Level 5!"
- "Declining since Tuesday" — not "You lost your streak!"

Trends are forgiving. Miss a day? Barely moves.

## Tracked Habits

### Automatic (no input)
| Habit | Source |
|-------|--------|
| Sleep hours | Oura |
| Sleep quality | Oura |
| Exercise | Oura (active_calories > 150) |
| Steps | Oura |
| Readiness | Oura |
| Spending | Monarch |
| Resting HR | Oura |

### Semi-Automatic (behavior detected)
| Habit | Detection |
|-------|-----------|
| Reading | Kindle clippings mod time |
| Personal project | Git commit activity |
| Social | Calendar social events |
| Focus blocks | 90+ min no context switch |

### Manual (brain dump keywords)
| Habit | Keywords |
|-------|----------|
| Meditation | "meditated", "breathwork", "mindfulness" |
| Hydration | "water", "hydrat", "drank" |
| Cooking | "cooked", "made dinner", "meal prep" |

```
Jeremy: "Made dinner instead of ordering"
Thanos: 🍳 Logged. Cooking: 2 of last 7 days.
```

## Daily Log Entry

File: `memory/habits/log.jsonl`

```json
{
  "date": "2026-02-01",
  "sleep_hours": 7.2,
  "sleep_quality": "good",
  "readiness": 81,
  "exercise": true,
  "active_calories": 320,
  "steps": 8432,
  "reading": false,
  "reading_days_since": 3,
  "meditation": false,
  "cooking": true,
  "social": false,
  "social_days_since": 5,
  "focus_blocks": 2,
  "daily_spend": 47.00,
  "tasks_completed": 3,
  "tasks_total": 4
}
```

## Trend Templates

**Improving:**
```
Exercise: 5/7 days ↑ — best week this month.
```

**Stable:**
```
Sleep avg: 7.0h → — consistent. Keep it.
```

**Declining (mild):**
```
Reading: 2/7 days ↓ — slipping. 20 min tonight?
```

**Declining (concerning):**
```
Sleep avg: 5.8h ↓↓ — third declining week.
Capping tomorrow to 2 priorities until sleep recovers.
```

**Absent (7+ days):**
```
Meditation: 0 days in 3 weeks.
Restart or tell me to stop tracking it. No guilt.
```

## Intervention Thresholds

| Condition | Action |
|-----------|--------|
| Sleep <6h avg (3 days) | Reduce max priorities to 2 |
| Exercise <2 days (7 days) | Nudge: "Walk 20 min" |
| Daily spend >2x average | Alert |
| Category over budget | Morning brief flag |
| Social 0 days (10 days) | Afternoon nudge |
| Focus blocks 0 by 2pm | Alert |

## ADHD Design Principles

**Why streaks fail:**
1. All-or-nothing: "missed one day, system broken"
2. Dopamine crash when streak breaks
3. Perfectionism trap: won't start unless "right"
4. Shame spiral: missed → guilt → avoidance → more missed

**What works:**
1. Trend framing: "4 of 7" is success
2. Minimum viable: "20 min" not "1 hour gym"
3. Forgiveness: 3/7 is fine
4. Remove, don't shame: not doing it? stop tracking
5. Correlation over judgment: let data motivate
6. Energy-gating: bad readiness → expectations drop

## Monthly Review (1st Sunday)

```
MONTHLY REVIEW — January 2026

STRONGEST: Exercise 22/31 (71%)
WEAKEST: Meditation 3/31 (10%) — still tracked?

CORRELATIONS:
• Exercise days: 3.2 avg completions
• No exercise: 1.8 avg completions
• Readiness >80: 2.9 completions

RECOMMENDATION:
Drop meditation or try 2-min version.
Exercise is highest-leverage. Keep it.
```
