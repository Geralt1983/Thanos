# Pattern Recognition Engine

Build behavioral pattern library over time. Patterns are data-backed correlations, not assumptions.

## Pattern Sources

| Data | Feeds Pattern |
|------|---------------|
| Readiness + completions | Energy-productivity correlation |
| Meeting count + next-day readiness | Meeting load impact |
| Sleep + spending | Impulse spending triggers |
| Dump frequency + completions | Spiral thresholds |
| Time of day + task type | Peak performance windows |
| Client gaps + fire frequency | Neglect → fire prediction |
| Exercise + readiness trend | Exercise-recovery correlation |
| Calendar density + completion rate | Overcommitment detection |

## Storage

### Raw Observations (nightly, 11pm)

File: `memory/patterns/observations.jsonl`

```json
{
  "date": "2026-02-01",
  "readiness": 81,
  "sleep": 7.2,
  "exercise": true,
  "meetings": 2,
  "tasks_completed": 3,
  "tasks_total": 4,
  "brain_dumps": 8,
  "focus_blocks": 2,
  "daily_spend": 47.00,
  "top_spend_category": "food",
  "clients_active": ["acme", "stlukes"],
  "clients_dark": ["mercy"]
}
```

### Confirmed Patterns

File: `memory/patterns/insights.md`

Only promoted after 5+ observations with consistency.

## Example Patterns

**P001: Meeting Load Crash** (HIGH)
- Rule: 4+ meetings day N → readiness drops avg 15 points day N+1
- Action: Pre-warn in afternoon brief. Block N+2 morning for recovery.

**P002: Exercise-Productivity Link** (HIGH)
- Rule: Exercise day → 3.2 avg completions. No exercise → 1.8.
- Action: Factor into priority count. Mention in habit nudges.

**P003: Sleep-Spending Correlation** (MEDIUM)
- Rule: Sleep <6.5h → restaurant spending +40%
- Action: Low-sleep days, flag spending awareness.

**P004: Spiral Threshold** (HIGH)
- Rule: 5+ dumps / 60 min, 0 completions = spiral
- Action: Trigger intervention.

**P005: Peak Focus Window** (MEDIUM)
- Rule: Most tasks completed 0930-1130
- Action: Protect this window. No meetings.

**P006: Client Neglect → Fire** (MEDIUM)
- Rule: 5+ days no interaction → elevated fire probability
- Action: Afternoon brief flags dark clients.

**P007: Tuesday Productivity** (MEDIUM)
- Rule: Tuesdays consistently highest completion
- Action: Schedule hardest tasks Tuesdays.

**P008: Weekend Recovery** (HIGH)
- Rule: Zero-work weekends → Monday readiness +12 avg
- Action: Weekend brief discourages work.

## Confidence Levels

| Level | Observations | Usage |
|-------|--------------|-------|
| EMERGING | 2-4 | Weekly review only |
| MEDIUM | 5-9 | Briefs as suggestions |
| HIGH | 10+ | Vigilance and gating |

Patterns demoted if not confirmed in 30 days.
Archived if contradicted more than confirmed.

## Weekly Analysis (Sunday)

Calculate 30-day correlations:
- Readiness vs completions
- Meetings vs next-day readiness
- Sleep vs spending
- Peak completion hours
- Day-of-week performance
- Exercise impact
- Client neglect periods

## Surfacing Rules

| Context | Rules |
|---------|-------|
| Morning brief | 1 max, HIGH/MEDIUM only, actionable today |
| Afternoon brief | 1 max, can include EMERGING |
| Vigilance | HIGH patterns can trigger alerts |
| Monthly review | Full report, all levels |

## Manual Pattern Input

```
Jeremy: "I notice I eat junk when stressed about deadlines"
Thanos: Pattern logged: stress_deadlines → junk_food. I'll track it.
```

Manual observations get EMERGING immediately. Accelerate to MEDIUM/HIGH if confirmed.

## Privacy

Health, mental, financial patterns NEVER shared externally.
Local memory only.

If screen-sharing, stay vague:
"Your data suggests lower capacity today" — not specifics.
