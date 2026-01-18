# Thanos Daily Workflow Guide

A practical guide for using the Thanos productivity system throughout your day.

---

## Morning Routine

### 1. Check Your Status

Start your day with a comprehensive status overview:

```bash
cd ~/Projects/Thanos
python -m commands.status
```

This displays:
- **Alerts**: Critical items requiring attention (overdue tasks, commitments due)
- **Tasks**: Active tasks, overdue count, due today
- **Commitments**: Overdue and due-soon commitments with person/context
- **Health**: Oura sleep/readiness/activity scores (if synced)
- **Brain Dump Queue**: Unprocessed items from Telegram captures

**Alternative views:**

```bash
# Quick alerts only
python -m commands.status --alerts-only

# Brief summary (no system info)
python -m commands.status --brief

# Machine-readable JSON
python -m commands.status --json
```

### 2. Understanding Alert Priorities

Alerts are color-coded by priority:

| Icon | Priority | Meaning | Action |
|------|----------|---------|--------|
| `[CRITICAL]` | Critical | Requires immediate attention | Drop everything, handle now |
| `[HIGH]` | High | Urgent, needs attention today | Schedule in first available slot |
| `[MEDIUM]` | Medium | Important but not urgent | Plan for today or tomorrow |
| `[LOW]` | Low | Informational | Review when convenient |

**Common alert types and responses:**

| Alert Type | What It Means | Suggested Action |
|------------|---------------|------------------|
| Commitment overdue | You promised someone something past due | Contact them, complete, or renegotiate |
| Commitment due soon | Within 48 hours | Make time today to complete |
| Task overdue | Past due date | Complete, reschedule, or cancel |
| Task due today | Deadline today | Prioritize in today's work |
| Low sleep score | Oura score below 70 | Plan lighter cognitive load today |
| Low readiness | Oura readiness below 65 | Take it easy, avoid high-intensity work |
| Habit streak at risk | Daily habit not completed | Complete before end of day |

### 3. Generate Daily Briefing

Get an AI-generated summary tailored for ADHD-friendly focus:

```bash
python -m commands.pa.daily
```

This provides:
- Top 3 priorities for the day
- Calendar/meeting summary
- Pending commitments needing attention
- Quick wins to knock out
- One focus recommendation

**With a specific focus area:**

```bash
python -m commands.pa.daily work
python -m commands.pa.daily personal
python -m commands.pa.daily epic
```

### 4. Review Overnight Brain Dumps

Check what you captured via Telegram after hours:

```bash
# Using the Telegram bot's CLI
python Tools/telegram_bot.py --status
```

Or check directly from the status command - the "Brain Dump Queue" section shows unprocessed items grouped by category (thinking, tasks, ideas, etc.).

---

## Throughout the Day

### Using the Telegram Bot for Capture

The Telegram bot is your mobile-first capture interface. Send anything:

**Text messages:**
```
Need to call the dentist tomorrow
```

**Voice messages:**
- Just record and send - Whisper AI transcribes automatically
- Great for quick capture while driving, walking, cooking

**What happens when you send a brain dump:**

1. **Classification**: AI categorizes your input as one of 9 types:
   - `thinking` - Reflection, musing, pondering
   - `venting` - Emotional release, frustration
   - `observation` - Noting something, no action needed
   - `note` - Information to remember
   - `personal_task` - Clear personal action item
   - `work_task` - Clear work action item
   - `idea` - Creative thought worth capturing
   - `commitment` - Promise made to someone
   - `mixed` - Multiple items detected

2. **Smart routing**:
   - Tasks get created automatically with proper context (work/personal)
   - Commitments track the person and deadline
   - Thinking/venting get acknowledged but don't clutter your task list
   - Ideas are captured without creating pressure to act

3. **Response**: You get an acknowledgment showing what was captured and how it was classified.

### Brain Dump Classification Examples

| What You Send | Classification | Result |
|---------------|----------------|--------|
| "Need to call the dentist" | `personal_task` | Task created |
| "Fix the login bug" | `work_task` | Task created (syncs to WorkOS) |
| "I told Sarah I'd review her doc by Friday" | `commitment` | Commitment tracked with deadline |
| "What if we built a feature for..." | `idea` | Idea captured |
| "I've been thinking about our team structure" | `thinking` | Logged, no task created |
| "So frustrated with this meeting culture" | `venting` | Acknowledged, no task |
| "API rate limit is 100 requests/minute" | `note` | Note stored |

### When to Use Brain Dump vs Manual Task

**Use Telegram brain dump when:**
- You're mobile or away from computer
- Quick capture is more important than precision
- You want AI to help categorize
- You're not sure if it's actually a task

**Use manual task creation when:**
- You know exactly what the task is
- You need to set specific metadata (due date, priority, tags)
- You're doing a planning session
- Task involves complex details

### Telegram Bot Commands

In Telegram, send:
- `/start` - Get intro and help
- `/status` - View pending brain dump items by category

---

## Evening Routine

### 1. Review Completed Tasks

Check what you accomplished today:

```bash
# List completed tasks
python -m commands.commitment_list --status completed

# View today's activity in the journal
python -m commands.status
```

### 2. Process Unprocessed Brain Dumps

Review items that need decisions:

```bash
# See pending brain dumps
python Tools/telegram_bot.py --status
```

For each item, decide:
- **Keep**: Leave for tomorrow's processing
- **Process**: Convert to task/commitment manually if needed
- **Delete**: If no longer relevant

### 3. Commitment Check-Ins

Review your active commitments:

```bash
# List all active commitments
python -m commands.commitment_list

# Filter to see overdue only
python -m commands.commitment_list --overdue

# See what's due soon
python -m commands.commitment_list --sort-by due
```

**Weekly commitment review:**

```bash
python -m commands.pa.weekly
```

---

## Commands Reference

### Status Commands

```bash
# Full status report
python -m commands.status

# Alerts only
python -m commands.status --alerts-only

# Brief (no system info)
python -m commands.status --brief

# JSON output for scripts
python -m commands.status --json
```

### Commitment Commands

```bash
# List all commitments
python -m commands.commitment_list

# Filter by type
python -m commands.commitment_list --type habit
python -m commands.commitment_list --type task
python -m commands.commitment_list --type goal

# Filter by status
python -m commands.commitment_list --status pending
python -m commands.commitment_list --status completed

# Show overdue only
python -m commands.commitment_list --overdue

# Show active streaks (for habits)
python -m commands.commitment_list --streaks

# Filter by domain
python -m commands.commitment_list --domain work
python -m commands.commitment_list --domain personal

# Sort options
python -m commands.commitment_list --sort-by due       # By due date
python -m commands.commitment_list --sort-by priority  # By priority
python -m commands.commitment_list --sort-by streak    # By streak count

# Output formats
python -m commands.commitment_list --format list   # Simple list (default)
python -m commands.commitment_list --format table  # Detailed table
python -m commands.commitment_list --format json   # JSON for scripts

# Show detailed info
python -m commands.commitment_list --details
```

### Personal Assistant (PA) Commands

```bash
# Daily briefing
python -m commands.pa.daily
python -m commands.pa.daily work      # Focus on work
python -m commands.pa.daily personal  # Focus on personal

# Weekly review
python -m commands.pa.weekly

# Task management
python -m commands.pa.tasks

# Calendar view
python -m commands.pa.calendar

# Process items
python -m commands.pa.process

# Brainstorm assistance
python -m commands.pa.brainstorm
```

### Health Commands

```bash
# Health summary from Oura
python -m commands.health.summary
```

### Alert Management

```bash
# Run alert check manually
python Tools/alert_checker.py --check

# List active alerts
python Tools/alert_checker.py --list

# JSON output
python Tools/alert_checker.py --list --json
```

### Brain Dump CLI

```bash
# View pending brain dumps
python Tools/telegram_bot.py --status

# Test capture (without Telegram)
python Tools/telegram_bot.py --test-capture "Need to buy groceries"
```

---

## Quick Reference Card

### Morning (5 min)
1. `python -m commands.status` - See what needs attention
2. `python -m commands.pa.daily` - Get your briefing
3. Review any overnight brain dumps

### During Day
- Send anything to Telegram bot
- Let AI classify and route
- Focus on execution, not organization

### Evening (5 min)
1. `python -m commands.commitment_list --sort-by due` - Check commitments
2. Process any brain dumps that need decisions
3. Mark completed items done

### Weekly
- `python -m commands.pa.weekly` - Full weekly review
- `python -m commands.commitment_list --overdue` - Clear overdue items
- `python -m commands.commitment_list --streaks` - Celebrate wins

---

## Tips for ADHD-Friendly Usage

1. **Don't overthink brain dumps** - Just send it, let AI categorize
2. **Check status first thing** - Before distractions hit
3. **Use voice messages** - Lower friction than typing
4. **Trust the classification** - Most "should I" thoughts are thinking, not tasks
5. **Batch process** - Review brain dumps once a day, not constantly
6. **Celebrate streaks** - Use `--streaks` to see habit progress
7. **One focus at a time** - Daily briefing gives you ONE recommendation
