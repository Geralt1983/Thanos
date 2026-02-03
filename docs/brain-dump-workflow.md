# Brain Dump Workflow Guide

## Table of Contents

- [Overview](#overview)
- [The Workflow](#the-workflow)
- [Getting Started](#getting-started)
- [Capturing Brain Dumps](#capturing-brain-dumps)
- [Processing Brain Dumps](#processing-brain-dumps)
- [Understanding Categorization](#understanding-categorization)
- [Best Practices](#best-practices)
- [Example Workflows](#example-workflows)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Overview

The brain dump workflow is a **capture-first, process-later** system designed to help you quickly capture thoughts, ideas, tasks, and worries without friction, then intelligently organize them later.

### The Philosophy

**Capture everything, decide nothing (at capture time).**

When inspiration strikes or anxiety creeps in, you shouldn't need to decide:
- Is this a task?
- Where does this fit?
- How urgent is this?
- What category does this belong to?

Just capture it. Let AI help you process it later.

### Key Benefits

1. **Low Friction Capture**: No categorization overhead during creative/busy moments
2. **AI-Assisted Processing**: Intelligent categorization and task conversion
3. **Reduced Mental Overhead**: Offload organization to dedicated processing time
4. **Nothing Falls Through Cracks**: Every thought gets captured and reviewed
5. **Pattern Recognition**: Learn what makes effective tasks vs casual thoughts

## The Workflow

The brain dump workflow has two phases:

```
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 1: CAPTURE                         │
│                                                              │
│  Thought/Idea/Task/Worry → Quick Capture → Brain Dump DB    │
│                                                              │
│  • No categorization required                               │
│  • No decision making                                       │
│  • Maximum speed                                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 2: PROCESS                          │
│                                                              │
│  Brain Dump DB → AI Analysis → Task or Archive              │
│                                                              │
│  • Batch processing                                         │
│  • AI categorization                                        │
│  • Intelligent task extraction                              │
│  • Archive non-actionable items                             │
└─────────────────────────────────────────────────────────────┘
```

## Getting Started

### Prerequisites

1. **WorkOS MCP Server**: Must be running and configured
2. **Database Access**: PostgreSQL database with brain_dump and tasks tables
3. **LiteLLM Configuration**: Claude API access configured

### Quick Start

```bash
# Capture a thought
/pa:braindump "Remember to review the new API documentation"

# Later, process all unprocessed entries
/pa:process
```

That's it! You're using the brain dump workflow.

## Capturing Brain Dumps

### Using the Brain Dump Command

The capture phase uses the MCP server's `workos-mcp__brain_dump` tool or the `/pa:braindump` command:

#### Via MCP Tool (in Claude conversation)
```
I want to capture this thought: "Explore using Redis for caching"
```

Claude will use the `workos-mcp__brain_dump` tool automatically.

#### Via Direct Command (future)
```bash
/pa:braindump "Explore using Redis for caching"
```

### What to Capture

**Capture anything that crosses your mind:**

#### ✅ Good Candidates for Brain Dump

- **Random Tasks**: "Reply to Sarah's email about the project"
- **Ideas**: "What if we gamified the onboarding process?"
- **Worries**: "Concerned about the deployment timeline"
- **Thoughts**: "The new UI feels more intuitive"
- **Questions**: "Why is the cache hit rate so low?"
- **Reminders**: "Don't forget to review PR #234"
- **Inspirations**: "That conference talk about DDD was interesting"

#### ❌ Don't Overthink It

- Don't worry about formatting
- Don't categorize while capturing
- Don't prioritize at capture time
- Don't decide if it's "worth" capturing
- Just dump it and move on

### Capture Tips

1. **Be Specific**: "Review authentication flow docs" > "Check docs"
2. **Include Context**: "Reply to client about API rate limits" > "Reply to email"
3. **Don't Filter**: When in doubt, capture it
4. **Keep It Flowing**: Don't break your flow to organize

## Processing Brain Dumps

### Running the Process Command

The process phase uses the `/pa:process` command with AI-powered categorization:

```bash
# Preview what would happen (recommended first time)
/pa:process --dry-run

# Process default batch (10 entries)
/pa:process

# Process more entries at once
/pa:process --limit 20

# Process small batch
/pa:process --limit 5
```

### What Happens During Processing

For each unprocessed brain dump entry, the system:

1. **Fetches Entry**: Retrieves content and metadata
2. **AI Analysis**: Sends to Claude Haiku for categorization
3. **Decision**: Determines if it should become a task or be archived
4. **Action**:
   - **→ TASK**: Creates task in backlog with full context
   - **→ ARCHIVE**: Marks as processed without task creation
5. **Display**: Shows you the decision and reasoning

### Process Output Example

```
🧠 Brain Dump Processing
📡 Using anthropic/claude-3-5-haiku-20241022
📊 Limit: 10 entries

----------------------------------------------------------------------

📝 Entry 1/3
   Created: 2024-01-11 15:30:00

   Content: Review the new authentication flow and update docs
            to include the refresh token handling

   Category: TASK
   Decision: → TASK
   Reasoning: Clear action item with specific deliverable
   ✅ Created: [work] Review authentication flow and update docs (ID: 42)


📝 Entry 2/3
   Created: 2024-01-11 16:45:00

   Content: Wondering if we should explore GraphQL for the API...

   Category: IDEA
   Decision: → ARCHIVE
   Reasoning: Interesting idea but not a concrete action item
   📦 Archived


📝 Entry 3/3
   Created: 2024-01-11 17:20:00

   Content: The new UI animations feel smoother than before

   Category: THOUGHT
   Decision: → ARCHIVE
   Reasoning: Casual observation without action required
   📦 Archived


----------------------------------------------------------------------

📊 Summary
   Total processed: 3
   Tasks created: 1
   Archived: 2
```

### When to Process

#### Daily Pattern
```bash
# End of day: Process today's captures
/pa:process --limit 5
```

Process at the end of each day to clear your mental inbox.

#### Weekly Pattern
```bash
# Sunday/Monday: Clear the backlog
/pa:process --limit 20
```

During weekly planning, process accumulated entries in larger batches.

#### After Brainstorming
```bash
# After ideation session: Process fresh ideas
/pa:process --dry-run  # Preview first
/pa:process           # Then process
```

After creative sessions, process captured ideas while they're fresh.

#### Continuous Processing
```bash
# Process as you go (if you prefer)
/pa:process --limit 3
```

Some prefer processing in small batches throughout the day.

## Understanding Categorization

### The Four Categories

The AI categorizes each brain dump entry into one of four categories:

#### 1. 💭 Thought

**What**: Random observations, reflections, or musings
**Action**: Almost always archived
**Examples**:
- "The new code review process is working well"
- "Interesting pattern in how users navigate the app"
- "I like the way the team collaborated today"

#### 2. ✅ Task

**What**: Clear, concrete action items
**Action**: Usually converted to tasks
**Examples**:
- "Review and respond to PR #123 comments"
- "Update the deployment documentation"
- "Schedule 1:1 with Sarah to discuss Q2 goals"

#### 3. 💡 Idea

**What**: Creative concepts, potential projects, inspiration
**Action**: Usually archived (unless clearly actionable)
**Examples**:
- "Could we build a dashboard showing real-time metrics?"
- "What about gamifying the onboarding process?"
- "Maybe we should explore microservices architecture"

**Note**: Ideas are archived because they typically need refinement before becoming tasks. You can review archived ideas during planning sessions.

#### 4. 😰 Worry

**What**: Concerns, anxieties, potential problems
**Action**: Usually archived (converted if actionable)
**Examples**:
- "Worried about meeting the deadline for the Epic project"
- "Concerned the API might not scale under load"
- "Anxious about the client presentation tomorrow"

**Note**: Worries are typically archived to acknowledge them. If a worry suggests an action (e.g., "Schedule stress test for API"), it becomes a task.

### Decision Philosophy: Conservative Task Creation

The AI is intentionally **conservative** about creating tasks:

#### Why Conservative?

- **Better to archive potential tasks** than clutter your task list
- **Easy to manually create tasks** from archived entries later
- **Reduces noise** in your task management system
- **Prevents task list overwhelm**

#### What This Means

- **When in doubt → Archive**
- **Vague ideas → Archive**
- **Philosophical thoughts → Archive**
- **Only clear actions → Tasks**

#### Override if Needed

If the AI archives something you think should be a task:
1. Review the archived entry in the database
2. Manually create a task with refined details
3. Over time, you'll learn what makes a good task

## Best Practices

### Capture Phase Best Practices

#### 1. **Capture Immediately**
Don't wait. Capture when the thought appears.

❌ Bad: "I'll remember to capture this later"
✅ Good: Capture right now, even mid-conversation

#### 2. **No Self-Censoring**
Don't judge whether something is "worth" capturing.

❌ Bad: "This thought isn't important enough"
✅ Good: Capture everything, filter later

#### 3. **Include Context**
Add enough detail for future-you to understand.

❌ Bad: "Fix the bug"
✅ Good: "Fix the authentication timeout bug in production"

#### 4. **Don't Categorize**
Resist the urge to categorize while capturing.

❌ Bad: Spending time deciding if it's a task or idea
✅ Good: Just dump it and keep moving

#### 5. **Trust the Process**
Believe that you'll process it later.

❌ Bad: Worrying about forgetting to process
✅ Good: Schedule regular processing time

### Processing Phase Best Practices

#### 1. **Preview First (Dry Run)**
When processing a large batch, preview first.

```bash
# See what would happen
/pa:process --limit 20 --dry-run

# If it looks good, process for real
/pa:process --limit 20
```

#### 2. **Start Small**
Build confidence with small batches.

```bash
# First time? Process just 5
/pa:process --limit 5
```

#### 3. **Process Regularly**
Don't let unprocessed entries pile up.

**Daily**: 5-10 entries at end of day
**Weekly**: Clear backlog (20+ entries)

#### 4. **Review AI Decisions**
Pay attention to what the AI categorizes.

- Learn what makes a good task
- Understand the categorization patterns
- Adjust your capture style if needed

#### 5. **Manual Override is OK**
If AI misses a task, create it manually.

The AI is good, but not perfect. Your judgment is the final authority.

#### 6. **Archive is Not Delete**
Archived entries are still in the database.

- Review during weekly planning
- Search for old ideas
- Track thought patterns over time

### Workflow Integration

#### Daily Routine

```bash
# Morning
/pa:daily                    # Get briefing

# Throughout the day
# ... capture brain dumps as needed ...

# End of day
/pa:process --limit 5        # Process today's captures
/pa:tasks review             # Review new tasks
```

#### Weekly Routine

```bash
# Sunday/Monday planning
/pa:weekly plan              # Weekly review
/pa:process --limit 20       # Clear brain dump backlog
/pa:tasks focus              # Plan the week
```

#### After Brainstorming

```bash
# During session
# ... rapid-fire brain dump captures ...

# After session (while fresh)
/pa:process --dry-run        # Preview categorization
/pa:process                  # Process and create tasks
/pa:brainstorm "next topic"  # Continue ideation
```

## Example Workflows

### Scenario 1: Developer's Daily Flow

**Context**: Software developer juggling multiple priorities

#### Morning (8:00 AM)
```bash
/pa:daily  # Get briefing and focus
```

#### Throughout the day (capturing as thoughts arise)
- 9:15 AM: *Reading PR* → "Review error handling in authentication PR #234"
- 11:30 AM: *Design discussion* → "What if we cached user preferences in Redis?"
- 2:45 PM: *Bug found* → "Users can't reset password when email has special chars"
- 4:20 PM: *Random thought* → "The new CI pipeline is much faster"
- 5:30 PM: *Reminder* → "Reply to Sarah's Slack about API documentation"

#### End of day (6:00 PM)
```bash
/pa:process --dry-run  # Preview
/pa:process            # Process all 5 entries
```

**Results**:
- ✅ **Tasks created** (3): PR review, bug fix, reply to Sarah
- 📦 **Archived** (2): Redis idea, CI observation

### Scenario 2: Product Manager's Weekly Review

**Context**: PM clearing backlog during weekly planning

#### Sunday Evening (7:00 PM)

**Step 1**: Check backlog size
```bash
# In Claude: "How many unprocessed brain dumps do I have?"
# Claude uses workos-mcp__get_brain_dump tool
```

**Step 2**: Preview batch
```bash
/pa:process --limit 30 --dry-run
```

**Step 3**: Process in chunks
```bash
# Process 10 at a time for better control
/pa:process --limit 10   # Batch 1
/pa:process --limit 10   # Batch 2
/pa:process --limit 10   # Batch 3
```

**Step 4**: Review created tasks
```bash
/pa:tasks focus  # See new tasks and prioritize
```

### Scenario 3: Creative Brainstorming Session

**Context**: Exploring ideas for new feature

#### During Session (rapid capture)
- "Gamification for user onboarding"
- "Progressive disclosure of advanced features"
- "AI-powered smart suggestions"
- "Dark mode for better late-night usage"
- "Mobile app companion"
- "Integration with Slack notifications"
- "Keyboard shortcuts for power users"
- "Update onboarding docs with new flow"
- "Schedule user testing for prototypes"

#### After Session (while fresh)
```bash
# Preview what AI thinks
/pa:process --dry-run

# Process the captures
/pa:process
```

**Expected Results**:
- ✅ **Tasks** (2): Update docs, schedule user testing
- 📦 **Ideas archived** (7): Features for future consideration
- 💡 **Benefit**: Ideas preserved for planning, actionable items in task list

### Scenario 4: Anxious Late Night

**Context**: Can't sleep, worried about project

#### Late Night (11:30 PM - capturing worries)
- "Worried we won't finish the API migration by deadline"
- "Concerned about database performance under load"
- "Anxious about tomorrow's client presentation"
- "Need to prepare talking points about timeline"
- "What if they ask about the recent outage?"

#### Next Morning (processing with clear head)
```bash
/pa:process
```

**Results**:
- ✅ **Tasks** (1): Prepare presentation talking points
- 📦 **Worries archived** (4): Acknowledged but not actionable
- 💭 **Benefit**: Worries externalized, sleep easier, actionable items identified

## Troubleshooting

### Common Issues

#### Issue: AI Archives Everything
**Problem**: All entries getting archived, no tasks created
**Solutions**:
- Make captures more specific and actionable
- Use clear action verbs: "Review", "Update", "Schedule", "Fix"
- Include concrete deliverables
- Example: "Think about API design" → "Review API design and propose improvements"

#### Issue: AI Creates Too Many Tasks
**Problem**: Task list getting cluttered
**Solutions**:
- The AI is already conservative; this is rare
- Review task quality - are they truly actionable?
- Use `--dry-run` to preview before processing
- Consider if your captures are too action-oriented

#### Issue: Wrong Categorization
**Problem**: AI puts tasks in wrong category
**Solutions**:
- This is rare but can happen
- Review the reasoning in the output
- Manually create task if needed
- Over time, pattern becomes clear

#### Issue: Forgetting to Process
**Problem**: Hundreds of unprocessed entries accumulating
**Solutions**:
- Set recurring calendar reminder
- Process during existing routines (daily standup, weekly review)
- Start with small batches: `--limit 5`
- Make it part of end-of-day shutdown ritual

#### Issue: Database Connection Errors
**Problem**: Can't connect to database
**Solutions**:
- Verify WorkOS MCP server is running
- Check database connection string
- Verify credentials in environment
- Review MCP server logs

## Advanced Usage

### Reviewing Archived Entries

Archived entries are not deleted - they're marked as processed in the database.

```sql
-- View archived entries
SELECT * FROM brain_dump
WHERE processed = 1
  AND converted_to_task_id IS NULL
ORDER BY created_at DESC;

-- Search archived ideas
SELECT * FROM brain_dump
WHERE category = 'idea'
  AND processed = 1
ORDER BY created_at DESC;
```

### Batch Size Strategy

Choose batch size based on context:

| Scenario | Batch Size | Reasoning |
|----------|------------|-----------|
| **First Time** | `--limit 5` | Build confidence in AI |
| **Daily** | `--limit 10` | Default, manageable |
| **Weekly** | `--limit 20-30` | Clear backlog efficiently |
| **After Brainstorm** | `--limit 15` | Fresh context in mind |
| **Large Backlog** | `--limit 10` (multiple runs) | Better control, avoid overwhelm |

### Dry Run Workflow

Always preview large batches:

```bash
# Step 1: Preview
/pa:process --limit 30 --dry-run

# Step 2: Review output carefully

# Step 3: Process if it looks good
/pa:process --limit 30

# Or adjust and try smaller batch
/pa:process --limit 10
```

### Integration with Other Commands

The brain dump workflow integrates with other `pa` commands:

#### With Tasks
```bash
# Process brain dumps → creates tasks
/pa:process

# Then focus on tasks
/pa:tasks focus
```

#### With Daily Briefing
```bash
# Morning routine
/pa:daily              # Get briefing
/pa:process --limit 5  # Clear overnight captures
/pa:tasks focus        # Plan the day
```

#### With Weekly Review
```bash
# Weekly planning
/pa:weekly review      # Review week
/pa:process --limit 30 # Clear backlog
/pa:weekly plan        # Plan next week
```

#### With Brainstorming
```bash
# Ideation workflow
/pa:brainstorm "topic" # Structured ideation
# ... also do rapid brain dumps during session ...
/pa:process           # Process everything together
```

### Database Schema Reference

For advanced users who want to query directly:

```sql
-- brain_dump table
CREATE TABLE brain_dump (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,              -- The captured thought
  category TEXT,                      -- thought/task/idea/worry
  processed INTEGER DEFAULT 0,        -- 0 = unprocessed, 1 = processed
  processed_at TIMESTAMP,             -- When it was processed
  converted_to_task_id INTEGER,       -- Link to task if converted
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- tasks table (where converted entries go)
CREATE TABLE tasks (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  category TEXT,                      -- work/personal
  status TEXT DEFAULT 'backlog',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Performance Tips

#### For Large Backlogs
If you have 100+ unprocessed entries:

```bash
# Process in small batches
for i in {1..10}; do
  /pa:process --limit 10
  # Review results between batches
done
```

#### For High-Volume Capture
If you capture 50+ entries per day:

```bash
# Process twice daily
/pa:process --limit 15  # Midday
/pa:process --limit 15  # End of day
```

#### Cost Optimization
Claude Haiku is already cost-effective, but for extreme volume:

- Batch processing is more efficient than one-by-one
- Default limit (10) balances cost and usability
- Larger batches (20-30) are only slightly more expensive

## Summary

The brain dump workflow is designed to **reduce friction during capture** and **leverage AI during processing**.

### Key Takeaways

1. **Capture everything** - no filtering, no categorization
2. **Process regularly** - daily or weekly, with AI assistance
3. **Trust the AI** - conservative task creation prevents clutter
4. **Preview first** - use `--dry-run` for large batches
5. **Manual override** - your judgment is final
6. **Archive ≠ Delete** - archived entries are preserved
7. **Build routine** - integrate into daily/weekly workflows

### Quick Reference Commands

```bash
# Capture (via Claude conversation)
"Capture this thought: [content]"

# Process
/pa:process                    # Default (10 entries)
/pa:process --dry-run          # Preview
/pa:process --limit 5          # Small batch
/pa:process --limit 20         # Large batch

# Integration
/pa:daily                      # Morning briefing
/pa:tasks focus                # Task planning
/pa:weekly review              # Weekly review
```

---

**Remember**: The brain dump workflow is about **capturing now, organizing later**. Don't let perfect organization prevent quick capture. The AI is here to help you make sense of it all.

Happy dumping! 🧠✨
