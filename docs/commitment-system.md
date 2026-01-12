# Commitment Accountability System - User Guide

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Core Concepts](#core-concepts)
4. [Command Reference](#command-reference)
5. [Use Cases & Examples](#use-cases--examples)
6. [Automatic Features](#automatic-features)
7. [Coach Integration](#coach-integration)
8. [Weekly Reviews](#weekly-reviews)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices for ADHD Users](#best-practices-for-adhd-users)

---

## Overview

The Commitment Accountability System is designed to be your reliable accountability partner, addressing the common challenge of follow-through without relying on others. Built specifically with ADHD-friendly features, it provides:

- **Automatic follow-ups** on commitments so nothing falls through the cracks
- **Streak tracking** to motivate consistent habits
- **Empathetic accountability** through Coach persona integration
- **Weekly reviews** with performance trends and insights
- **Morning digests** to start your day with clarity

### Why This System?

Traditional commitment tracking often fails because:
- It requires you to remember to check it
- It doesn't adapt to your patterns
- It lacks empathy when you miss something
- It doesn't celebrate your wins

This system solves these problems by being **proactive, adaptive, and empathetic**.

---

## Getting Started

### Prerequisites

The commitment system is already integrated into your Thanos environment. All tools are available in the `Tools/` and `commands/` directories.

### Your First Commitment

Let's add a simple habit to get started:

```bash
# Interactive mode (easiest for beginners)
python3 commands/commitment_add.py --interactive

# Or directly specify all details
python3 commands/commitment_add.py \
  --title "Morning meditation" \
  --type habit \
  --recurrence daily \
  --domain health \
  --priority 1
```

### Viewing Your Commitments

```bash
# List all commitments
python3 commands/commitment_list.py

# See what's due today
python3 commands/commitment_list.py --due-today

# Check your active streaks
python3 commands/commitment_list.py --streaks
```

### Completing a Commitment

```bash
# Mark as complete (this updates your streak!)
python3 commands/commitment_update.py <commitment_id> --complete

# Add a note about how it went
python3 commands/commitment_update.py <commitment_id> --complete --notes "Felt great!"
```

---

## Core Concepts

### Commitment Types

The system supports three types of commitments, each with different tracking behavior:

#### 1. **Habits** (Recurring behaviors)
- **Purpose**: Track daily/regular practices you want to build
- **Features**: Streak tracking, recurrence patterns, completion rate
- **Examples**: Morning workout, meditation, journaling
- **Best for**: Building long-term behaviors

```bash
python3 commands/commitment_add.py \
  --title "Daily workout" \
  --type habit \
  --recurrence daily \
  --domain health
```

#### 2. **Goals** (Milestone-based achievements)
- **Purpose**: Track specific outcomes you want to achieve
- **Features**: Due dates, progress tracking, milestone celebration
- **Examples**: Learn Python, Complete certification, Read 12 books this year
- **Best for**: Outcome-oriented objectives

```bash
python3 commands/commitment_add.py \
  --title "Complete React course" \
  --type goal \
  --due "+30d" \
  --domain learning
```

#### 3. **Tasks** (One-time actions)
- **Purpose**: Track specific to-dos with deadlines
- **Features**: Due dates, status tracking, overdue alerts
- **Examples**: Submit report, Schedule dentist appointment
- **Best for**: Discrete actions that need to be done once

```bash
python3 commands/commitment_add.py \
  --title "Submit quarterly report" \
  --type task \
  --due "2026-01-15" \
  --domain work \
  --priority 1
```

### Recurrence Patterns

For habits, you can specify how often they should occur:

- **daily**: Every day (default for habits)
- **weekly**: Once per week
- **weekdays**: Monday through Friday
- **weekends**: Saturday and Sunday
- **custom**: Define your own pattern (e.g., "Mon,Wed,Fri")
- **none**: No recurrence (for goals and tasks)

### Priority Levels

Commitments can have priority levels from 1-5:

- **1** (⚡ Highest): Critical, urgent, non-negotiable
- **2** (🔴 High): Important, should be done today
- **3** (🟡 Medium): Normal priority (default)
- **4** (🟢 Low): Nice to have
- **5** (⚪ Lowest): Optional, when time permits

### Domains

Organize commitments into life domains:

- **work**: Professional commitments
- **personal**: Personal life and relationships
- **health**: Physical and mental health
- **learning**: Education and skill development
- **general**: Uncategorized (default)

### Status Values

Commitments move through different states:

- **pending**: Not started yet
- **in_progress**: Currently working on it
- **completed**: Successfully finished
- **missed**: Not completed when due
- **cancelled**: No longer relevant

### Streaks

For recurring commitments (habits), the system tracks:

- **Current Streak**: Consecutive days/weeks you've completed it
- **Longest Streak**: Your personal record
- **Completion Rate**: Percentage of expected completions

Streak milestones are celebrated at: 1, 3, 7, 14, 21, 30, 60, 90, and 100+ days!

---

## Command Reference

### Adding Commitments

**Command**: `python3 commands/commitment_add.py [options]`

#### Basic Usage

```bash
# Interactive mode (guided prompts)
python3 commands/commitment_add.py --interactive

# Quick add with minimal options
python3 commands/commitment_add.py --title "Read for 30 minutes" --type habit
```

#### All Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--title` | `-t` | Commitment title (required) | `--title "Morning run"` |
| `--type` | | Type: habit, goal, task | `--type habit` |
| `--due` | `-d` | Due date (ISO, relative, or natural) | `--due "2026-01-15"` or `--due "+3d"` |
| `--recurrence` | `-r` | Recurrence pattern | `--recurrence daily` |
| `--priority` | `-p` | Priority level (1-5) | `--priority 1` |
| `--domain` | | Life domain | `--domain health` |
| `--tags` | | Comma-separated tags | `--tags "morning,exercise"` |
| `--notes` | `-n` | Additional notes | `--notes "Use workout app"` |
| `--interactive` | `-i` | Interactive mode | `--interactive` |
| `--state-dir` | | Custom state directory | `--state-dir ./custom/path` |

#### Date Formats

The `--due` flag accepts multiple formats:

```bash
# ISO format
--due "2026-01-15"

# Relative dates
--due "today"
--due "tomorrow"
--due "+3d"      # 3 days from now
--due "+2w"      # 2 weeks from now

# Natural language
--due "Jan 15"
--due "January 15 2026"
```

#### Examples

```bash
# Daily habit with high priority
python3 commands/commitment_add.py \
  --title "Morning workout" \
  --type habit \
  --recurrence daily \
  --priority 1 \
  --domain health \
  --tags "exercise,morning"

# Goal with deadline
python3 commands/commitment_add.py \
  --title "Complete online course" \
  --type goal \
  --due "+30d" \
  --domain learning

# Work task due tomorrow
python3 commands/commitment_add.py \
  --title "Review pull requests" \
  --type task \
  --due "tomorrow" \
  --domain work \
  --priority 2

# Weekday-only habit
python3 commands/commitment_add.py \
  --title "Daily standup" \
  --type habit \
  --recurrence weekdays \
  --domain work
```

### Updating Commitments

**Command**: `python3 commands/commitment_update.py <commitment_id> [options]`

#### Quick Actions

```bash
# Mark as complete
python3 commands/commitment_update.py abc123 --complete

# Mark as complete with notes
python3 commands/commitment_update.py abc123 --complete --notes "Great session!"

# Mark as missed
python3 commands/commitment_update.py abc123 --missed --notes "Overslept"

# Cancel commitment
python3 commands/commitment_update.py abc123 --cancel

# Delete permanently
python3 commands/commitment_update.py abc123 --delete
```

#### All Options

| Option | Description | Example |
|--------|-------------|---------|
| `--complete` | Mark as completed | `--complete` |
| `--missed` | Mark as missed | `--missed` |
| `--cancel` | Mark as cancelled | `--cancel` |
| `--delete` | Delete permanently | `--delete` |
| `--status` | Update status | `--status in_progress` |
| `--reschedule` | Change due date | `--reschedule "+3d"` |
| `--title` | Update title | `--title "New title"` |
| `--priority` | Update priority | `--priority 1` |
| `--domain` | Update domain | `--domain work` |
| `--tags` | Update tags | `--tags "tag1,tag2"` |
| `--notes` | Add/update notes | `--notes "Additional context"` |
| `--interactive` | Interactive mode | `--interactive` |

#### Examples

```bash
# Start working on a task
python3 commands/commitment_update.py abc123 --status in_progress

# Reschedule to next week
python3 commands/commitment_update.py abc123 --reschedule "+1w"

# Update multiple fields at once
python3 commands/commitment_update.py abc123 \
  --title "Updated title" \
  --priority 1 \
  --tags "urgent,review"

# Interactive update (guided prompts)
python3 commands/commitment_update.py abc123 --interactive
```

### Listing Commitments

**Command**: `python3 commands/commitment_list.py [filters] [options]`

#### Basic Usage

```bash
# List all commitments
python3 commands/commitment_list.py

# List in table format
python3 commands/commitment_list.py --format table

# Export as JSON
python3 commands/commitment_list.py --format json
```

#### Filtering Options

| Option | Description | Example |
|--------|-------------|---------|
| `--type` | Filter by type | `--type habit` |
| `--status` | Filter by status | `--status pending` |
| `--domain` | Filter by domain | `--domain health` |
| `--tags` | Filter by tags (AND logic) | `--tags "exercise,morning"` |
| `--priority` | Filter by priority | `--priority 1` |
| `--overdue` | Show only overdue | `--overdue` |
| `--due-today` | Show only due today | `--due-today` |
| `--streaks` | Show only with active streaks | `--streaks` |

#### Sorting Options

| Option | Description |
|--------|-------------|
| `--sort-by due` | Sort by due date (earliest first) |
| `--sort-by priority` | Sort by priority (highest first) |
| `--sort-by streak` | Sort by streak count (longest first) |
| `--sort-by created` | Sort by creation date |
| `--sort-by title` | Sort alphabetically |
| `--reverse` | Reverse sort order |

#### Display Options

| Option | Description |
|--------|-------------|
| `--format list` | Simple checkbox list (default) |
| `--format table` | Comprehensive table view |
| `--format json` | JSON output for scripting |
| `--details` | Show additional metadata |

#### Examples

```bash
# Show all pending habits
python3 commands/commitment_list.py --type habit --status pending

# Show overdue items sorted by priority
python3 commands/commitment_list.py --overdue --sort-by priority

# Show work commitments due today
python3 commands/commitment_list.py --domain work --due-today

# Show active streaks in table format
python3 commands/commitment_list.py --streaks --format table

# Filter by multiple tags
python3 commands/commitment_list.py --tags "urgent,review" --format table

# Export health commitments as JSON
python3 commands/commitment_list.py --domain health --format json

# Show detailed view of all commitments
python3 commands/commitment_list.py --details --format table
```

### Daily Digest

**Command**: `python3 Tools/commitment_digest.py [options]`

Generates a morning summary of your commitments for the day.

#### Options

| Option | Description |
|--------|-------------|
| `--detailed` | Show full details including notes and completion rates |
| `--json` | Output as JSON |
| `--state-dir` | Custom state directory |

#### Examples

```bash
# Generate today's digest
python3 Tools/commitment_digest.py

# Detailed view
python3 Tools/commitment_digest.py --detailed

# JSON format for scripting
python3 Tools/commitment_digest.py --json
```

The digest includes:
- Overdue items with urgency indicators
- Commitments due today
- Habits scheduled for today
- Active streaks and milestones
- Contextual encouragement messages
- Day-specific motivation (e.g., "Monday motivation!")

### Weekly Review

**Command**: `python3 Tools/commitment_review.py [options]`

Generates a comprehensive weekly performance review.

#### Options

| Option | Description | Example |
|--------|-------------|---------|
| `--week-offset` | Review past weeks | `--week-offset 1` (last week) |
| `--compare-weeks` | Number of weeks to compare | `--compare-weeks 4` |
| `--detailed` | Show detailed statistics | `--detailed` |
| `--json` | Output as JSON | `--json` |
| `--output` | Save to file | `--output review.md` |
| `--state-dir` | Custom state directory | `--state-dir ./path` |

#### Examples

```bash
# Current week review
python3 Tools/commitment_review.py

# Last week's review
python3 Tools/commitment_review.py --week-offset 1

# Detailed review with 8-week trend
python3 Tools/commitment_review.py --detailed --compare-weeks 8

# Save to file
python3 Tools/commitment_review.py --output History/CommitmentReviews/week-$(date +%Y-%m-%d).md

# Export as JSON
python3 Tools/commitment_review.py --json
```

The review includes:
- Overall grade (A+ to F) and completion rate
- Coach's summary message
- Wins and highlights
- Areas for improvement
- Weekly statistics by type
- Trend analysis (improving/stable/declining)
- Streak milestones achieved
- Reflection prompts for self-awareness
- Key insights and recommendations

### Commitment Check

**Command**: `python3 Tools/commitment_check.py [options]`

Checks for commitments needing attention (used by session-start hook).

#### Options

| Option | Description |
|--------|-------------|
| `--all` | Show all prompts including habit reminders |
| `--overdue` | Show only overdue commitments |
| `--dry-run` | Don't update reminder timestamps |
| `--json` | Output as JSON |
| `--quiet-hours` | Respect quiet hours configuration |
| `--summary` | Quick summary only |

#### Examples

```bash
# Check what needs attention
python3 Tools/commitment_check.py

# Show everything including habits
python3 Tools/commitment_check.py --all

# Test without updating timestamps
python3 Tools/commitment_check.py --dry-run

# Quick summary
python3 Tools/commitment_check.py --summary
```

### Coach Check-in

**Command**: `python3 Tools/coach_checkin.py [options]`

Generates Coach persona check-ins for missed commitments.

#### Options

| Option | Description | Example |
|--------|-------------|---------|
| `<commitment_id>` | Check-in on specific commitment | `coach_checkin.py abc123` |
| `--list` | List all commitments needing Coach | `--list` |
| `--all` | Check-in on all needing attention | `--all` |
| `--detailed` | Show detailed check-in report | `--detailed` |
| `--prompt` | Generate Coach prompt format | `--prompt` |
| `--json` | Output as JSON | `--json` |
| `--summary` | Quick summary statistics | `--summary` |

#### Examples

```bash
# List commitments needing Coach attention
python3 Tools/coach_checkin.py --list

# Get Coach check-in for specific commitment
python3 Tools/coach_checkin.py abc123 --prompt

# Detailed check-in with pattern analysis
python3 Tools/coach_checkin.py abc123 --detailed

# Summary of all commitments needing intervention
python3 Tools/coach_checkin.py --summary
```

---

## Use Cases & Examples

### Building a Morning Routine

**Scenario**: You want to establish a consistent morning routine with multiple habits.

```bash
# 1. Add morning habits
python3 commands/commitment_add.py \
  --title "Wake up at 6am" \
  --type habit \
  --recurrence weekdays \
  --priority 1 \
  --domain personal \
  --tags "morning,routine"

python3 commands/commitment_add.py \
  --title "Morning meditation (10 min)" \
  --type habit \
  --recurrence daily \
  --priority 1 \
  --domain health \
  --tags "morning,mindfulness"

python3 commands/commitment_add.py \
  --title "Review daily plan" \
  --type habit \
  --recurrence daily \
  --priority 2 \
  --domain work \
  --tags "morning,planning"

# 2. Check your morning routine each day
python3 commands/commitment_list.py --tags "morning" --status pending

# 3. Complete them as you go
# (Get the ID from the list command above)
python3 commands/commitment_update.py <meditation_id> --complete --notes "Felt centered"

# 4. Track your streak
python3 commands/commitment_list.py --tags "morning" --streaks
```

### Managing Work Projects

**Scenario**: You have a project with multiple tasks and a deadline.

```bash
# 1. Create the main goal
python3 commands/commitment_add.py \
  --title "Launch new feature by end of month" \
  --type goal \
  --due "2026-01-31" \
  --domain work \
  --priority 1 \
  --tags "project,launch"

# 2. Break down into tasks
python3 commands/commitment_add.py \
  --title "Complete API implementation" \
  --type task \
  --due "+7d" \
  --domain work \
  --priority 1 \
  --tags "project,development"

python3 commands/commitment_add.py \
  --title "Write tests" \
  --type task \
  --due "+10d" \
  --domain work \
  --priority 2 \
  --tags "project,testing"

python3 commands/commitment_add.py \
  --title "Update documentation" \
  --type task \
  --due "+14d" \
  --domain work \
  --priority 2 \
  --tags "project,docs"

# 3. Check work commitments daily
python3 commands/commitment_list.py --domain work --status pending --sort-by due

# 4. Update as you progress
python3 commands/commitment_update.py <api_task_id> --status in_progress
python3 commands/commitment_update.py <api_task_id> --complete
```

### Tracking Health Goals

**Scenario**: You want to improve your health with exercise and nutrition habits.

```bash
# 1. Set health goals
python3 commands/commitment_add.py \
  --title "Lose 10 pounds" \
  --type goal \
  --due "+90d" \
  --domain health \
  --tags "fitness,weight"

# 2. Add supporting habits
python3 commands/commitment_add.py \
  --title "30-minute workout" \
  --type habit \
  --recurrence weekdays \
  --priority 1 \
  --domain health \
  --tags "fitness,exercise"

python3 commands/commitment_add.py \
  --title "Log meals in app" \
  --type habit \
  --recurrence daily \
  --priority 2 \
  --domain health \
  --tags "nutrition,tracking"

python3 commands/commitment_add.py \
  --title "Drink 8 glasses of water" \
  --type habit \
  --recurrence daily \
  --priority 2 \
  --domain health \
  --tags "nutrition,hydration"

# 3. Check health commitments
python3 commands/commitment_list.py --domain health --format table

# 4. Track your progress
python3 commands/commitment_list.py --domain health --streaks
```

### Learning New Skills

**Scenario**: You want to learn programming with structured practice.

```bash
# 1. Set the learning goal
python3 commands/commitment_add.py \
  --title "Complete Python course" \
  --type goal \
  --due "+60d" \
  --domain learning \
  --priority 1 \
  --tags "coding,python"

# 2. Add daily practice
python3 commands/commitment_add.py \
  --title "Code for 1 hour" \
  --type habit \
  --recurrence daily \
  --priority 1 \
  --domain learning \
  --tags "coding,practice"

python3 commands/commitment_add.py \
  --title "Complete one coding challenge" \
  --type habit \
  --recurrence weekdays \
  --priority 2 \
  --domain learning \
  --tags "coding,exercises"

# 3. Track weekly progress
python3 Tools/commitment_review.py --detailed
```

### Handling Recurring Misses

**Scenario**: You keep missing a commitment and need Coach's help.

```bash
# 1. Check for commitments needing Coach intervention
python3 Tools/coach_checkin.py --list

# 2. Get detailed check-in for the problematic commitment
python3 Tools/coach_checkin.py <commitment_id> --detailed

# This will show:
# - Consecutive miss count
# - Pattern analysis (which days you typically miss)
# - Suggested Coach approach (gentle curiosity -> direct confrontation)
# - Reflection prompts

# 3. Based on the patterns, you might:
# - Reschedule to a better time
python3 commands/commitment_update.py <commitment_id> --notes "Works better in evening"

# - Or adjust the commitment to be more realistic
python3 commands/commitment_update.py <commitment_id> --title "Workout 3x per week"
```

---

## Automatic Features

The commitment system includes several automatic features that work without manual intervention.

### Session-Start Prompts

When you start a new Claude session, the system automatically:

1. Checks for overdue commitments
2. Shows what's due today
3. Displays habit reminders
4. Highlights active streaks

This is integrated into `hooks/session-start/init.ts` and runs every time you start working with Thanos.

**Example Output:**

```
🔔 Commitment Check:

Overdue (2):
  ⚠️  [3 days] Morning workout (Habit) - Last completed: Jan 8
  🚨 [7 days] Submit report (Task) - Due: Jan 5

Due Today (1):
  📅 Review pull requests (Task) - Priority: High

Active Streaks:
  🔥 7 days - Daily meditation
  ⭐ 14 days - Log meals
```

### Morning Digest

The system can be configured to generate a morning digest automatically. This is configured in `config/commitment_schedule.json`:

```json
{
  "check_ins": {
    "morning_digest": {
      "enabled": true,
      "time": "07:00",
      "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    }
  }
}
```

### Coach Interventions

When you miss a commitment multiple times (2+ consecutive misses), the Coach persona automatically:

1. Detects the pattern
2. Prepares a contextual check-in
3. Offers empathetic support without judgment
4. Helps you identify what's not working

The Coach uses escalating approaches:

- **First miss (1-2 times)**: Gentle curiosity - "What got in the way?"
- **Second miss (3-4 times)**: Pattern acknowledgment - "I'm noticing a pattern..."
- **Third miss (5-7 times)**: Direct confrontation - "Let's be real about this commitment"
- **Chronic pattern (8+ times)**: Values alignment check - "Is this still important to you?"

### Weekly Reviews

Configured to run automatically (Sunday 8:00 PM or Monday 8:00 AM), the weekly review:

1. Calculates your completion rate
2. Identifies trends (improving/stable/declining)
3. Celebrates streak milestones
4. Provides reflection prompts
5. Generates actionable insights

Reviews are saved to `History/CommitmentReviews/` for historical tracking.

### Quiet Hours

The system respects quiet hours (default: 10 PM - 7 AM) to avoid notifications during rest time. This is configured in `config/commitment_schedule.json`:

```json
{
  "quiet_hours": {
    "enabled": true,
    "start": "22:00",
    "end": "07:00"
  }
}
```

---

## Coach Integration

The Coach persona provides empathetic accountability when you miss commitments. Unlike harsh reminders, Coach uses a warm-but-direct approach that's supportive and growth-oriented.

### Coach's Approach

**Core Principles:**
- No shame, no judgment
- Curiosity over disappointment
- Data-driven pattern recognition
- Focus on what's working AND what's not
- ADHD-aware language and solutions

### When Coach Gets Involved

Coach automatically intervenes when:
- You've missed a commitment 2+ consecutive times
- A commitment has a low completion rate (<50%)
- Patterns emerge (e.g., always miss Monday workouts)

### Coach Check-In Style

**For First Misses** (Gentle Curiosity):
```
"I noticed you missed [commitment] for the first time in a while.
No judgment - just curious: what got in the way?"

Patterns I see:
- Your streak was going strong (X days) before this
- You typically complete this on [days of week]

Quick reflection: Was this a one-off, or is something shifting?
```

**For Repeated Misses** (Pattern Acknowledgment):
```
"Okay, real talk: you've missed [commitment] 4 times in a row now.
That's not random - there's a pattern here.

What I notice:
- You tend to miss on [specific days]
- Your completion rate dropped from X% to Y%
- This started around [date]

Let's figure out what's not working. Is it:
- Wrong time of day?
- Too ambitious?
- Lost motivation?
- Something else changed?
```

**For Chronic Patterns** (Values Alignment Check):
```
"We need to talk about [commitment]. You've missed it 10+ times,
and your completion rate is X%. That's telling us something important.

Two possibilities:
1. This commitment doesn't actually align with what you value right now
2. The way we've set it up isn't working for your life

Which is it? And what would need to change for this to work -
or should we let it go?
```

### Using Coach Check-ins

```bash
# See which commitments need Coach intervention
python3 Tools/coach_checkin.py --list

# Get Coach's analysis for a specific commitment
python3 Tools/coach_checkin.py <commitment_id> --detailed

# Generate Coach's opening prompt
python3 Tools/coach_checkin.py <commitment_id> --prompt
```

### Coach's Pattern Analysis

Coach analyzes temporal patterns to provide targeted support:

```bash
python3 Tools/coach_checkin.py abc123 --detailed
```

**Output might show:**
```
Pattern Analysis:
- Mondays: 0/4 completed (0%)
- Tuesdays: 3/4 completed (75%)
- Wednesdays: 4/4 completed (100%)
- Thursdays: 3/4 completed (75%)
- Fridays: 1/4 completed (25%)

Insight: You struggle most on Mondays and Fridays.
Consider: Are these high-stress days? Low-energy days?
Could you move this commitment to mid-week when you're more consistent?
```

---

## Weekly Reviews

Weekly reviews help you step back and see the bigger picture of your commitment performance.

### What's Included

A comprehensive review includes:

1. **Overall Grade** (A+ to F based on completion rate)
2. **Coach's Summary Message** (honest, growth-oriented feedback)
3. **Wins & Highlights** (what went well)
4. **Areas for Improvement** (what needs attention)
5. **Weekly Statistics** (breakdown by type: habit/goal/task)
6. **Trend Analysis** (comparing to previous weeks)
7. **Streak Milestones** (celebrations for achievements)
8. **Reflection Prompts** (questions for deeper awareness)
9. **Key Insights** (actionable recommendations)

### Generating a Review

```bash
# Current week
python3 Tools/commitment_review.py

# Save to file
python3 Tools/commitment_review.py --output History/CommitmentReviews/week-$(date +%Y-%m-%d).md

# Detailed view with 8-week trend
python3 Tools/commitment_review.py --detailed --compare-weeks 8
```

### Understanding Your Grade

Grades are based on your overall completion rate:

- **A+ (95-100%)**: Outstanding consistency! 🌟
- **A (90-94%)**: Excellent work! 💪
- **B (80-89%)**: Good progress 👍
- **C (70-79%)**: Room for improvement 📈
- **D (60-69%)**: Needs attention ⚠️
- **F (<60%)**: Let's reassess 🔄

### Reflection Prompts

Each review includes 5 reflection prompts to deepen self-awareness:

**Wins Category:**
```
"What commitment am I most proud of this week, and why did it work?"
→ This helps identify your success patterns
```

**Struggles Category:**
```
"Which commitment felt hardest, and what made it difficult?"
→ This reveals obstacles you might not have noticed
```

**Patterns Category:**
```
"When do I tend to complete commitments most consistently?"
→ This helps optimize timing and conditions
```

**Redesign Category:**
```
"If I could redesign one commitment to work better, what would I change?"
→ This encourages proactive problem-solving
```

**Values Category:**
```
"Are my commitments reflecting what actually matters to me right now?"
→ This ensures alignment with your true priorities
```

### Trend Analysis

The review compares your current week to previous weeks:

```
Trend Analysis (Last 4 Weeks):
Week of Jan 6:  78% (26/33 completed) ⬆️ IMPROVING
Week of Dec 30: 65% (22/34 completed)
Week of Dec 23: 71% (24/34 completed)
Week of Dec 16: 69% (23/33 completed)

Average (previous 3 weeks): 68%
This week vs average: +10% 🎉
```

**Trend Indicators:**
- ⬆️ **IMPROVING**: Completion rate increased by 5%+
- ➡️ **STABLE**: Rate changed by less than 5%
- ⬇️ **DECLINING**: Rate decreased by 5%+

### Using Reviews for Growth

**Best Practice Workflow:**

1. **Generate the review** on Sunday evening or Monday morning
2. **Read Coach's summary** for honest feedback
3. **Celebrate your wins** - acknowledge what worked
4. **Analyze struggles** - identify specific obstacles
5. **Answer reflection prompts** - write your responses
6. **Implement insights** - adjust commitments based on learnings
7. **Save the review** - keep for historical reference

```bash
# Generate and save review
python3 Tools/commitment_review.py --detailed --output History/CommitmentReviews/$(date +%Y-%m-%d)-review.md

# Read and reflect (open in your editor)
# Then make adjustments based on insights:

# Example: Lower priority on struggling commitments
python3 commands/commitment_update.py <id> --priority 3

# Example: Reschedule to better time
python3 commands/commitment_update.py <id> --notes "Moving to afternoon - works better"

# Example: Cancel commitments that no longer align
python3 commands/commitment_update.py <id> --cancel --notes "No longer a priority"
```

---

## Troubleshooting

### Common Issues

#### "No commitments found"

**Cause**: Either no commitments exist, or the data file is missing.

**Solution**:
```bash
# Check if data file exists
ls -la State/CommitmentData.json

# If missing, add your first commitment
python3 commands/commitment_add.py --interactive

# Or check state directory location
python3 commands/commitment_list.py --state-dir ./State
```

#### "Commitment not found" when updating

**Cause**: Invalid commitment ID or commitment was deleted.

**Solution**:
```bash
# List all commitments with IDs
python3 commands/commitment_list.py --format table

# Use the exact ID from the list
python3 commands/commitment_update.py <correct_id> --complete
```

#### Streaks not updating

**Cause**: Commitment not marked as complete, or completion date not recorded.

**Solution**:
```bash
# Always use --complete flag to properly update streaks
python3 commands/commitment_update.py <id> --complete

# Check current streak
python3 commands/commitment_list.py --streaks --format table

# If streak is incorrect, it auto-recalculates on next completion
```

#### Weekly review shows no data

**Cause**: No completions recorded in the date range, or completion history is empty.

**Solution**:
```bash
# Check if commitments have completion history
python3 commands/commitment_list.py --format json | grep -A5 completion_history

# Complete some commitments to build history
python3 commands/commitment_update.py <id> --complete
```

#### Coach check-in not showing missed commitments

**Cause**: Commitments not actually overdue, or consecutive miss count is less than 2.

**Solution**:
```bash
# Check current miss status
python3 Tools/coach_checkin.py --summary

# List all commitments to see status
python3 commands/commitment_list.py --format table

# Coach only triggers on 2+ consecutive misses
# Mark as missed to record the miss
python3 commands/commitment_update.py <id> --missed --notes "Reason"
```

#### Session-start hook not showing commitments

**Cause**: Hook not properly configured, or path to commitment_check.py is incorrect.

**Solution**:
```bash
# Test commitment check manually
python3 Tools/commitment_check.py

# Check hook configuration
cat hooks/session-start/init.ts | grep -A10 "checkCommitments"

# Verify Python path in hook
which python3
```

#### Date parsing errors

**Cause**: Invalid date format provided.

**Solution**:
```bash
# Use supported formats:
--due "2026-01-15"      # ISO format (YYYY-MM-DD)
--due "today"           # Literal today
--due "tomorrow"        # Literal tomorrow
--due "+3d"             # Relative days
--due "+2w"             # Relative weeks
--due "Jan 15"          # Natural language
--due "January 15 2026" # Full natural language

# Check if date was parsed correctly
python3 commands/commitment_list.py --format table
```

### Data Recovery

If your commitment data becomes corrupted:

```bash
# 1. Check if backup exists
ls -la State/CommitmentData.json.backup

# 2. Restore from backup if available
cp State/CommitmentData.json.backup State/CommitmentData.json

# 3. If no backup, the system will create a fresh file
# Your Commitments.md file still exists as a reference
cat Commitments.md

# 4. Verify data loaded correctly
python3 commands/commitment_list.py
```

### Performance Issues

If commands are running slowly:

```bash
# Check file size
ls -lh State/CommitmentData.json

# If file is very large (>1MB), consider archiving old commitments
# Export current data
python3 commands/commitment_list.py --format json > commitments-backup.json

# Delete cancelled/old completed commitments manually or create archive script
```

### Getting Help

If you encounter issues not covered here:

1. Check the implementation plan for technical details:
   ```bash
   cat .auto-claude/specs/035-commitment-accountability-system/implementation_plan.json
   ```

2. Review the test files for examples:
   ```bash
   cat tests/test_commitment_tracker.py
   cat tests/test_commitment_integration.py
   ```

3. Check the build progress for known issues:
   ```bash
   cat .auto-claude/specs/035-commitment-accountability-system/build-progress.txt
   ```

---

## Best Practices for ADHD Users

This system was designed specifically with ADHD in mind. Here are best practices to make it work for you:

### 1. Start Small

**Don't add 20 commitments on day one.** Your brain will reject it.

```bash
# Start with 2-3 keystone habits
python3 commands/commitment_add.py --title "Morning meditation" --type habit --recurrence daily
python3 commands/commitment_add.py --title "Review daily plan" --type habit --recurrence weekdays
python3 commands/commitment_add.py --title "Evening wind-down" --type habit --recurrence daily

# Add more only after these are consistent
```

### 2. Use Visual Indicators

The system provides emoji-based indicators because they're easier for ADHD brains to scan:

- ⚡ = High priority (your focus)
- 🔥 = Active streak (your motivation)
- 🚨 = Overdue (needs immediate attention)
- 📅 = Due today (plan for it)

Always use `--format table` for visual scanning:

```bash
python3 commands/commitment_list.py --format table
```

### 3. Leverage Morning Digest

Use the morning digest as your daily launchpad:

```bash
# Make this part of your morning routine
python3 Tools/commitment_digest.py --detailed
```

The digest gives you:
- What absolutely must get done (overdue items)
- What's on tap for today
- Your current momentum (streaks)
- Encouragement to start strong

### 4. Celebrate Streaks

ADHD brains need immediate reward. Streaks provide that:

```bash
# Check your streaks daily
python3 commands/commitment_list.py --streaks

# Celebrate milestones
# Day 7: You made it a week! 🌟
# Day 21: Habit forming territory! 💪
# Day 30: This is who you are now! 🔥
```

### 5. Use Coach Without Shame

When you miss commitments, **don't avoid Coach**. The Coach approach is designed to be:
- Curious, not judgmental
- Pattern-focused, not shame-based
- Solution-oriented, not critical

```bash
# When you're struggling, ask for help
python3 Tools/coach_checkin.py <commitment_id> --detailed

# Coach will help you see:
# - When you tend to succeed (do more of that)
# - When you tend to struggle (adjust for that)
# - Whether the commitment itself needs to change
```

### 6. Weekly Reviews as Metacognition

ADHD makes it hard to see patterns. Weekly reviews provide that bird's-eye view:

```bash
# Sunday night or Monday morning
python3 Tools/commitment_review.py --detailed

# Read it with curiosity:
# - What worked this week?
# - What patterns emerged?
# - What needs to change?
```

**Pro tip**: Keep your reviews in a folder and occasionally read old ones. You'll see long-term patterns you'd never notice day-to-day.

### 7. Adjust Freely, No Guilt

Your ADHD brain won't perform consistently every day. **That's okay.** Adjust as needed:

```bash
# Having a rough week? Lower priorities
python3 commands/commitment_update.py <id> --priority 3

# Found a better time? Reschedule
python3 commands/commitment_update.py <id> --notes "Works better at 2pm"

# Not working at all? Cancel it
python3 commands/commitment_update.py <id> --cancel --notes "Revisit later"
```

### 8. Use Domains for Context Switching

ADHD struggles with context switching. Use domains to group related commitments:

```bash
# Workday? Check work domain
python3 commands/commitment_list.py --domain work

# Weekend? Check personal/health
python3 commands/commitment_list.py --domain personal --domain health
```

### 9. Tags for Hyperfocus

Use tags to batch similar tasks when you're in hyperfocus mode:

```bash
# In coding mode? Knock out all coding tasks
python3 commands/commitment_list.py --tags coding --status pending

# In admin mode? Clear all admin tasks
python3 commands/commitment_list.py --tags admin,email --status pending
```

### 10. Automation is Your Friend

Let the system do the remembering:

- ✅ Session-start hook shows commitments automatically
- ✅ Morning digest structures your day
- ✅ Coach intervenes when patterns emerge
- ✅ Weekly reviews provide reflection time
- ✅ Streak tracking provides motivation

**Your only job**: Mark things complete when you do them.

```bash
python3 commands/commitment_update.py <id> --complete
```

### 11. Habit Stacking

Attach new commitments to existing routines:

```bash
# After morning coffee (existing routine)
python3 commands/commitment_add.py \
  --title "Review commitments while drinking coffee" \
  --type habit \
  --recurrence daily \
  --tags "morning,coffee"

# After workout (existing habit)
python3 commands/commitment_add.py \
  --title "Protein shake after workout" \
  --type habit \
  --recurrence weekdays \
  --tags "health,post-workout"
```

### 12. The 2-Day Rule

For ADHD, missing one day is normal. Missing two days is a pattern breaking.

The system enforces this with Coach interventions at 2+ consecutive misses.

**Your rule**: If you miss twice, either:
1. Get back on track immediately
2. Adjust the commitment to be more realistic

```bash
# Check for 2+ miss patterns
python3 Tools/coach_checkin.py --list

# Then decide:
python3 commands/commitment_update.py <id> --complete  # Get back on
# OR
python3 commands/commitment_update.py <id> --notes "Reducing to 3x per week"
```

### 13. Friday Review as Week-Ender

In addition to weekly reviews, do a quick Friday check:

```bash
# Friday afternoon
python3 commands/commitment_list.py --domain work --status pending

# Reschedule anything that didn't happen
python3 commands/commitment_update.py <id> --reschedule "next Monday"

# Celebrate your week
python3 commands/commitment_list.py --streaks
```

This prevents the "Monday panic" when you realize what didn't get done.

### 14. Use Notes Liberally

Capture context when it's fresh:

```bash
# When completing
python3 commands/commitment_update.py <id> --complete --notes "Felt energized, morning works better"

# When missing
python3 commands/commitment_update.py <id> --missed --notes "Kid was sick, unavoidable"

# When rescheduling
python3 commands/commitment_update.py <id> --reschedule "+3d" --notes "Need to finish X first"
```

Future-you (and Coach) will thank you for the context.

### 15. Progress Over Perfection

**You will not hit 100% completion.** That's not the goal.

Goals for ADHD success:
- **60-70%**: You're building real habits
- **70-80%**: You're doing great
- **80%+**: You're crushing it

The system's analytics show you trends, not absolutes. A 65% week after a 55% week is **improvement**, and that's what matters.

```bash
# Check your trend, not your absolute score
python3 Tools/commitment_review.py --detailed --compare-weeks 4

# Look for the ⬆️ IMPROVING indicator
# That's your win
```

---

## Conclusion

The Commitment Accountability System is designed to be your reliable accountability partner. It works by:

- **Tracking** what you commit to
- **Reminding** you proactively (not passively waiting)
- **Celebrating** your wins with streak tracking
- **Supporting** you empathetically through Coach when you struggle
- **Analyzing** patterns to help you optimize
- **Adapting** to your reality, not forcing you into rigidity

**Remember**: This system exists to serve you, not to judge you. Use it as a tool for self-awareness and growth, not as another source of shame.

Start small. Track consistently. Adjust frequently. Celebrate progress.

You've got this. 🚀

---

## Quick Reference Card

```bash
# DAILY COMMANDS

# Morning: Check what's on tap
python3 Tools/commitment_digest.py

# Complete a commitment (updates streaks!)
python3 commands/commitment_update.py <id> --complete

# View today's commitments
python3 commands/commitment_list.py --due-today

# Check current streaks
python3 commands/commitment_list.py --streaks


# WEEKLY COMMANDS

# Sunday/Monday: Weekly review
python3 Tools/commitment_review.py --detailed

# Friday: Week wrap-up
python3 commands/commitment_list.py --domain work --status pending


# MANAGEMENT COMMANDS

# Add new commitment (interactive)
python3 commands/commitment_add.py --interactive

# Update commitment
python3 commands/commitment_update.py <id> [options]

# List commitments
python3 commands/commitment_list.py [filters]

# Get Coach help
python3 Tools/coach_checkin.py --list


# QUICK FILTERS

# Show overdue
python3 commands/commitment_list.py --overdue

# Show work items
python3 commands/commitment_list.py --domain work

# Show high priority
python3 commands/commitment_list.py --priority 1

# Show by tags
python3 commands/commitment_list.py --tags "urgent,review"
```

---

**Version**: 1.0
**Last Updated**: January 2026
**For Questions**: See developer documentation at `docs/commitment-system-architecture.md`
