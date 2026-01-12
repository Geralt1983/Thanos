# /pa:process - Brain Dump Processing Command

Intelligently categorize and process brain dump entries, converting them to tasks or archiving them.

## Usage
```
/pa:process [options]
```

## Overview

The process command uses AI to analyze unprocessed brain dump entries and automatically:
- Categorize each entry (thought, task, idea, worry)
- Determine if it should become a task or be archived
- Create tasks for actionable items
- Archive non-actionable entries

This command leverages the existing `brainDump` table infrastructure with the `processed` flag, providing an automated workflow for managing brain dumps.

## Workflow

### 1. Fetch Unprocessed Entries
Retrieves brain dump entries where `processed = 0`, ordered by creation date.

### 2. AI Analysis
For each entry, uses LLM to:
- Categorize the content
- Assess actionability
- Extract task details if applicable

### 3. Process Entry
Based on AI recommendation:
- **Convert to Task**: Creates task in backlog with full context
- **Archive**: Marks as processed without creating task

### 4. Display Results
Shows detailed progress for each entry with:
- Category assignment
- Decision reasoning
- Task details (if converted)
- Processing status

## Categorization Logic

### Categories

#### thought
Random observations, reflections, or musings that don't require action.
- Example: "Interesting how the new UI pattern is catching on"
- Action: Archive

#### task
Clear, concrete action items that need doing.
- Example: "Review and respond to PR #123 comments"
- Action: Convert to task

#### idea
Creative concepts, potential projects, or inspiration.
- Example: "Could we build a dashboard showing real-time metrics?"
- Action: Usually archive (unless clearly actionable)

#### worry
Concerns, anxieties, or potential problems.
- Example: "Worried about meeting the deadline for the Epic project"
- Action: Archive (or convert if actionable, e.g., "Schedule meeting to discuss deadline")

### Decision Philosophy

**Conservative Task Creation**: The AI is designed to be conservative with task creation.
- Only well-defined actions become tasks
- When in doubt, entries are archived
- Better to archive potential tasks than clutter the task list
- Users can always manually create tasks from archived entries

### Task Details (When Converting)

When converting to a task, the AI extracts:
- **Title**: Clear, concise task name (max 100 chars)
- **Description**: Full context from brain dump entry
- **Category**: "work" or "personal" based on content
- **Status**: Always created in "backlog" status

## Output Format

```markdown
🧠 Brain Dump Processing
📡 Using claude-3-5-haiku-20241022
📊 Limit: 10 entries

----------------------------------------------------------------------

📝 Entry 1/3
   Created: 2024-01-11 15:30:00

   Content: Review the new authentication flow and update docs...

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


----------------------------------------------------------------------

📊 Summary
   Total processed: 3
   Tasks created: 1
   Archived: 2
```

## Flags

### `--dry-run`
Preview processing without making database changes.
- Shows what would happen without actually creating tasks or updating entries
- Useful for testing categorization logic
- Example: `/pa:process --dry-run`

### `--limit N`
Process only N entries at a time (default: 10).
- Controls batch size for processing
- Prevents overwhelming the task list
- Example: `/pa:process --limit 5`

## Usage Examples

### Process with preview
```bash
/pa:process --dry-run
```
See what would happen without making changes.

### Process small batch
```bash
/pa:process --limit 5
```
Process only 5 entries at a time.

### Process default batch
```bash
/pa:process
```
Process up to 10 entries.

### Process larger batch
```bash
/pa:process --limit 20
```
Process up to 20 entries in one go.

### Preview large batch
```bash
/pa:process --limit 20 --dry-run
```
See what would happen with 20 entries without making changes.

## AI Model

**Model**: `claude-3-5-haiku-20241022`
- Fast classification optimized for this task
- Cost-effective for high-volume processing
- Temperature: 0.3 for consistent categorization
- Structured JSON output for reliable parsing

## Integration Points

### Database Tables
- **brain_dump**: Source of unprocessed entries
- **tasks**: Target for converted entries
- Links tasks back to brain dump via `converted_to_task_id`

### Related Commands
- `/pa:braindump`: Capture new brain dump entries
- `/pa:tasks`: Manage and view created tasks

## Best Practices

### When to Run
- **Daily**: Process accumulated brain dumps from the day
- **Weekly Review**: Clear backlog during weekly planning
- **After Brainstorming**: Process ideas captured during sessions

### Workflow Tips
1. **Capture freely**: Use brain dump for quick captures without filtering
2. **Process regularly**: Don't let unprocessed entries pile up
3. **Review dry-run**: Check categorization before processing large batches
4. **Adjust limit**: Start small (--limit 5) to build confidence in AI decisions
5. **Manual override**: If AI misses tasks, adjust prompts or create manually

## Error Handling

The command handles errors gracefully:
- **JSON Parse Errors**: Falls back to archiving entry
- **Database Errors**: Reports specific failures without stopping batch
- **LLM Errors**: Safe fallback to archive category
- **Connection Issues**: Detailed error messages with cleanup

All errors are reported in the summary with specific details for debugging.
