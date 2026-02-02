# Morning & Afternoon Briefs

## Morning Brief (SITREP)

**Trigger:** 6am Mon-Fri, 8am Sat-Sun, or "sitrep"/"morning brief"

### Execution Order (strict sequence)

#### Step 1: Energy State
Query Oura: readiness, sleep, activity.
```
ENERGY: [FULL/MODERATE/LOW/RECOVERY] — Readiness {score}
Sleep: {hours}h ({quality})
Yesterday: {active_calories} cal, {steps} steps
```

If RECOVERY (<55):
```
RECOVERY MODE. Emergency tasks only. One must-do per client.
Cancel or defer everything else. Non-negotiable.
```

#### Step 2: Client Fires
Read `~/.thanos/incoming/{client}.jsonl`. Filter unprocessed since last brief.
```
CLIENT FIRES:
• Acme: Dr. Chen replied (Teams, 11pm). Needs response.
• Mercy: Quiet overnight.
```

#### Step 3: Calendar
All calendars for today.
```
TODAY:
0900 — Acme standup (Teams)
1100 — Build review ⚠️ Prep needed
1400 — StLukes call
```
Flags: ⚠️ Prep needed | 🔴 Conflict | 🔄 Recurring

#### Step 4: Financial Pulse
Query Monarch Money for balances and spending.
```bash
cd ~/Projects/Thanos && node skills/monarch-money/dist/cli/index.js acc list --json
```

**Balances:**
```
💰 BALANCES:
Liquid Cash: $X,XXX (Checking $X,XXX + MM $XXX + Share $XXX)
Credit Cards: -$X,XXX (Amex Plat -$XXX, Amex Gold -$XXX)
Net Worth: -$XXX,XXX
```

**Spending (Budget: $2,750/mo):**
```
SPENDING:
MTD: $X,XXX / $2,750
⚠️ Over budget: {category} ${amt} / ${budget}

Key categories:
• Groceries: ${amt}/$500
• Baby: ${amt}/$600
• Gas: ${amt}/$250
• Restaurants: ${amt}/$200
```

See [budgets.md](budgets.md) for full category budgets.

#### Step 5: Weather & Task Recommendations
Run weather and task monitoring tools:
```bash
cd ~/Projects/Thanos
.venv/bin/python Tools/weather_monitor.py
.venv/bin/python Tools/energy_aware_tasks.py
```

**Weather Brief:**
```
🌦️ MORNING WEATHER:
Temp: {temperature}°F (Feels like {feels_like}°F)
Conditions: {description}

🚗 ACTION ITEMS:
• {action1}
• {action2}
• {action3}
• {action4}
```

**Tasks Matched to Energy:**
```
MATCHED TO ENERGY ({count} tasks):
💼 ● [Client] Task title (simple)
🏠 ●● Task title (moderate)
💼 ●●● [Client] Task title (complex)

DEFER ({count} tasks):
💼 ●●● [Client] Complex task beyond today's energy
```

**Selection Rules:**
1. Weather dictates preparation
2. Deadline TODAY → auto-include
3. Urgent fires → auto-include
4. Match tasks to energy level
5. RECOVERY mode: Simple tasks only

#### Step 6: Personal Commitments
From Todoist + `memory/commitments/personal.jsonl`. Show aging items.
```
PERSONAL:
• Call mom — Day 5 of "this week." Do it today.
• Oil change — 2 weeks overdue.
```

#### Step 7: Habit Trends
7-day snapshot. Trend language only (no streaks).
```
HABITS (7d):
Exercise: 4/7 ↑ | Sleep avg: 6.8h ↓ | Reading: 2 days since
```

### Morning Template
```
═══════════════════════════════
SITREP — {day} {date}
═══════════════════════════════
ENERGY: {level} — Readiness {score}
Sleep: {hours}h | Activity: {steps} steps

CLIENT FIRES:
• {client}: {summary}

TODAY:
{time} — {event}

💰 BALANCES:
Cash: ${liquid} | Cards: -${debt} | Net: ${net_worth}

SPENDING:
Yesterday: ${amt} | MTD: ${amt}/${budget}

TOP 3:
1. {task}
2. {task}
3. {task}

PERSONAL:
• {commitment — age}

HABITS (7d):
Exercise {x}/7 | Sleep {x}h | Reading {status}
═══════════════════════════════
```

---

## Afternoon Brief (DEBRIEF)

**Trigger:** 5pm Mon-Fri, or "debrief"/"wrap up"

### Execution Order

#### Step 1: Scorecard
```
SCORECARD: 2/3
1. ✅ Respond to Dr. Chen (10:23am)
2. ✅ Submit validation (2:15pm)
3. ❌ Draft preference list (not started)
```

If 0/3:
```
SCORECARD: 0/3.
Not judgment. What happened? Energy? Fires? Drift?
```

#### Step 2: Client Summary
One line per client.
```
CLIENTS:
Acme: Order set approved. Next: go-live prep.
Mercy: No activity. 0 messages.
StLukes: Validation submitted. Awaiting response.
```

#### Step 3: Unresolved Threads
```
UNRESOLVED:
1. Dr. Chen email (3:42pm) — SEND?
2. IT ticket comment — needs review

Reply SEND 1 / DRAFT 2 / SKIP 3 / TOMORROW 4
```

#### Step 4: Financial Summary
```
MONEY:
Today: $83 | Week: $412/$800 | Month: $2,223/$3,200
⚠️ Restaurants: $90 over
```

#### Step 5: Personal Tasks
```
PERSONAL:
✅ Confirmed dentist
❌ Call mom (Day 5)
⏳ Oil change (2 weeks overdue)
```

#### Step 6: Tomorrow Preview
```
TOMORROW:
0900 — Acme standup
1030 — Mercy kickoff (NEW — prep needed)
Deadlines: Migration doc (48h)

Recommendation: Use 1400 free block for Mercy prep.
```

#### Step 7: Habit Status
```
HABITS:
Exercise: ✅ | Sleep: 7.2h | Reading: ❌ 3 days
```

#### Step 8: Energy Trend (7-Day)
```
ENERGY (7d):
Mon ████████░░ 82
Tue █████████░ 91
Wed ██████░░░░ 63 ← crash
Thu █████░░░░░ 52 ← recovery
Fri ███████░░░ 74
```

#### Step 9: Pattern Insight
One max. Only if actionable. Skip if nothing relevant.

#### Step 10: Friday Weekend Preview
```
WEEKEND:
Saturday: Haircut 10am
Sunday: Free

WEEK REVIEW:
Completed: 14/18 (78%)
Best: Tuesday (readiness 91)
Worst: Thursday (readiness 52)

Rest. Recharge for Monday.
```

### Afternoon Template
```
═══════════════════════════════
DEBRIEF — {day} {date}
═══════════════════════════════
SCORECARD: {x}/{total}
1. {emoji} {task}

CLIENTS:
{client}: {summary}

UNRESOLVED:
{n}. {thread} — {action}

MONEY:
${today} | ${mtd}/${budget}

PERSONAL:
{emoji} {item}

TOMORROW:
{time} — {event}
Deadlines: {list}

HABITS:
Exercise {emoji} | Sleep {hours}h | Reading {status}

ENERGY (7d): {sparkline}
{pattern_insight if any}
═══════════════════════════════
{closing}
═══════════════════════════════
```

Closing lines:
- "Rest up. Tomorrow's a grind."
- "Light day ahead. Use it."
- "You crushed it. Maintain."
- "Rough one. Reset tonight."
- "Weekend. Unplug."
