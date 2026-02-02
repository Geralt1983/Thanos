# Configuration

All thresholds, contacts, budgets in one place. Update for your setup.

## Energy Gating

```yaml
energy:
  full:     { min_readiness: 85, max_priorities: 3, stretch_goals: true }
  moderate: { min_readiness: 70, max_priorities: 3, stretch_goals: false }
  low:      { min_readiness: 55, max_priorities: 2, suggest_cancellations: true }
  recovery: { min_readiness: 0,  max_priorities: 1, force_reduced_brief: true }
```

## Schedule

```yaml
schedule:
  timezone: "America/New_York"
  morning_brief:  { workday: "0600", weekend: "0800" }
  vigilance:      { start: "0900", end: "1700", interval: 15, workdays_only: true }
  afternoon_brief: { time: "1700", friday_extended: true }
  quiet_hours:    { start: "2200", end: "0600", allow: ["fire"] }
```

## Clients

```yaml
clients:
  memphis:
    display_name: "Memphis"
    dark_threshold_days: 5
    notes: "Epic contract"
  
  kentucky:
    display_name: "Kentucky"
    dark_threshold_days: 5
    notes: "Epic contract"
  
  raleigh:
    display_name: "Raleigh"
    dark_threshold_days: 5
    notes: "Epic contract"
  
  orlando:
    display_name: "Orlando"
    type: "FTE"
    dark_threshold_days: 7
    notes: "Full-time engagement"
```

## Alert Thresholds

```yaml
alerts:
  fire:
    urgency_keywords:
      - ASAP
      - urgent
      - down
      - broken
      - escalat
      - deadline today
      - emergency
      - critical
      - go-live
      - blocker
      - blocking
    vip_unread_max_hours: 2

  stuck:
    no_progress_hours: 2
    followup_after_minutes: 30

  meeting_prep:
    minutes_before: 15

  energy_crash:
    check_time: "1400"

  spending:
    large_transaction_threshold: 50

  commitment_decay:
    check_interval_hours: 2
    mild: 1.0x
    moderate: 1.5x
    severe: 2.0x
    auto_remove_days: 30

  spiral:
    dumps_per_hour: 5
    completions_required: 0
    topic_switch_threshold: 4

  health:
    sleep_crisis_hours: 6.0
    sleep_crisis_window_days: 3
    readiness_decline_days: 4

  leisure:
    days_without: 7
    social_days_without: 10
```

## Throttling

```yaml
throttling:
  max_alerts_per_hour: 4
  exempt: ["fire", "meeting_prep"]
  min_gap_minutes: 10
  dnd_default_hours: 2
```

## Financial

```yaml
financial:
  budget_total_monthly: 3200  # UPDATE
  categories:
    restaurants: 250
    shopping: 200
    entertainment: 100
    subscriptions: 150
    groceries: 400
    transport: 200
```

## Habits

```yaml
habits:
  exercise: { target_days: 4, minimum: "20 min walk", source: "oura" }
  sleep:    { target_hours: 7.0, critical_low: 6.0, source: "oura" }
  reading:  { target_days: 3, nudge_after: 3, source: "kindle/manual" }
  social:   { target_days: 1, nudge_after: 10, source: "calendar/manual" }
  meditation: { target_days: 0, review_if_inactive_weeks: 4 }
  cooking:  { target_days: 3, nudge: false }

trends:
  window_days: 7
  comparison_days: 14
```

## Brain Dump

```yaml
brain_dump:
  default_category: "thinking"
  task_creation_requires_specificity: true
  commitment_decay_default_days: 7
  idea_review: "monthly"
```

## Telegram

```yaml
telegram:
  max_brief_length: 4000
  shortcuts:
    SEND: send_draft
    EDIT: edit_draft
    SKIP: defer_thread
    TOMORROW: move_to_tomorrow
    QUIET: enable_dnd
    BACK: disable_dnd
    STATUS: mini_status_report
```

## Paths

```yaml
paths:
  incoming_queue: "~/.thanos/incoming"
  memory_root: "memory"
  habits_log: "memory/habits/log.jsonl"
  habits_trends: "memory/habits/trends.md"
  patterns_observations: "memory/patterns/observations.jsonl"
  patterns_insights: "memory/patterns/insights.md"
  commitments_personal: "memory/commitments/personal.jsonl"
  commitments_work: "memory/commitments/work.jsonl"
  daily_log: "memory/daily"
```

## Data Sources

| Source | Purpose | Setup |
|--------|---------|-------|
| Oura MCP | Energy/sleep/activity | MCP server |
| Monarch Money MCP | Financial | MCP server |
| Todoist API | Personal tasks | REST API |
| Calendar | Events | gog CLI or MCP |
| Client Queue | Fires | `~/.thanos/incoming/{client}.jsonl` |
