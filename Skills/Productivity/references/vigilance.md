# Vigilance — Continuous Monitoring

**Trigger:** Every 15 min, Mon-Fri 9am-5pm

**Core Principle:** SILENT by default. Interrupt-only alerts.

Jeremy does NOT want: status updates, encouragement, every email forwarded.
Jeremy DOES want: fires, drift detection, accountability, health intervention.

## Alert Types (Priority Order)

### 1. 🔥 FIRE — Immediate Forward
**Check:** Incoming queue every 15 min

**Fire criteria (ANY match):**
- High importance flag
- Sender on VIP list
- Urgency keywords: ASAP, urgent, down, broken, escalat, deadline today, emergency, critical, go-live, blocker
- VIP message unread >2 hours

```
🔥 ACME — Dr. Chen (VIP)
"The pharmacy order set is blocking go-live."
Received: 43 min ago

DRAFT: "Dr. Chen — I'll review and have recommendations by 11am..."

Reply SEND / EDIT
```

### 2. 📅 MEETING PREP — Pre-Meeting Context
**Trigger:** 15 min before calendar event

```
📅 Acme build review in 15 min

Last discussion: Pharmacy preference lists
Open items: Frequency defaults, therapeutic sub alerts
Key contact: Dr. Chen (concise updates, hates slides)
```

### 3. 🚨 SPIRAL/SCATTER — ADHD Intervention
**Trigger:** On each brain dump

- 5+ dumps / 60 min + 0 completions = **SPIRAL**
- 4+ topics / 30 min = **SCATTER**

Spiral:
```
5 dumps in the last hour. Zero completions.
You're spiraling. Stop. Walk 10 minutes.
When you're back: ONE thing. I'll pick it.
```

Scatter:
```
4 topics in 30 minutes. Brain everywhere.
Close everything except: {priority}
```

### 4. ⚠️ DRIFT — Wrong Priority
**Check:** Every 15 min. Compare current work vs morning priorities.

```
Wrong target. You're on {current}.
Priority is {actual}. {reason}
```

### 5. ⏰ STUCK — No Progress
**Check:** Every 15 min. No task status change in 2 hours.

```
Status. No movement in {hours}h.
Current priority: {task}
What's blocking you?
```

30 min later if no response:
```
Still nothing. Pick one:
1. {priority_1}
2. {priority_2}
Or tell me what you're doing.
```

### 6. 🔋 ENERGY CRASH — 2pm Check
**Trigger:** 2pm daily if 0/3 completed.

```
2pm. None of your three done.
Pick one. Now.

1. {highest_priority}

That one. Go.
```

If already LOW energy:
```
Low energy day. You've done what you can.
Wrap up by 4. Tomorrow's a reset.
```

### 7. 💰 SPENDING — Real-Time Financial
**Trigger:** Monarch periodic check.

```
💰 $127 at Amazon. Planned? (yes/no)
Shopping: $180/$200 — close to limit.
```

### 8. 📋 COMMITMENT DECAY
**Trigger:** Every 2 hours. Check Todoist + commitments.

| Severity | Timeframe | Response |
|----------|-----------|----------|
| Mild | 1-1.5x expected | "Reminder: {item}. Day {age}. Today?" |
| Moderate | 1.5-2x | "{item} — {age} days. Rotting. Do it or kill it." |
| Severe | 2x+ | "{item} — {age} days. Removing in 24h unless you act." |

### 9. 💤 HEALTH NUDGE — Oura-Driven
**Trigger:** 10am and 2pm check.

Sleep crisis (<6h avg, 3 nights):
```
Sleep avg under 6h for 3 nights.
In bed by 10pm tonight. No screens after 9:30.
Tomorrow: 1 priority if this continues.
```

Burnout warning (readiness declining 4+ days):
```
Readiness declining 4 days: {scores}
Heading toward a wall. Cut tomorrow's calendar 50%.
What can we cancel?
```

### 10. 🎮 LEISURE BALANCE
**Trigger:** 5pm daily if 7+ days since non-work activity.

```
{days} days since something not-work.
Schedule something this weekend.
```

## Throttling

- Max 4 alerts/hour (except FIRE and MEETING PREP)
- No back-to-back within 10 min
- Quiet hours 10pm-6am: FIRE only
- Weekend: FIRE + COMMITMENT DECAY only

## Do Not Disturb

```
Jeremy: quiet
Thanos: Silent 2 hours. Fires only.

Jeremy: dnd until 3
Thanos: Dark until 1500. Fires only.

Jeremy: back
Thanos: Online. 2 queued:
• Acme follow-up (1h ago)
• Stuck: no progress since 1100
```
