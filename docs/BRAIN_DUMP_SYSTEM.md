# Brain Dump System Documentation

Comprehensive documentation for Thanos's AI-powered brain dump capture, classification, and routing system.

## Overview

### What is a Brain Dump?

A brain dump is a quick, friction-free way to capture thoughts, tasks, ideas, and observations as they occur. Rather than forcing you to categorize or format your input at the moment of capture, the brain dump system accepts natural language input and uses AI to intelligently classify and route the content.

### Why It Matters

- **Reduced Cognitive Load**: Capture thoughts without worrying about where they belong
- **Prevents Task Pollution**: Most brain dumps are just thoughts or venting, not actual tasks. The system defaults to NOT creating tasks unless there's clear actionable content
- **Context Preservation**: The original thought is preserved alongside any extracted structure
- **Multi-Channel Capture**: Works via Telegram (text and voice), API, or direct Python integration

### The Pipeline: Capture -> Classify -> Route -> Store

```
                    +------------------+
                    |   INPUT SOURCE   |
                    | (Telegram, API)  |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |   CLASSIFIER     |
                    | (Claude AI)      |
                    | Determines type  |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |     ROUTER       |
                    | Routes to proper |
                    | destination      |
                    +--------+---------+
                             |
        +--------------------+--------------------+
        |          |         |         |         |
        v          v         v         v         v
   +--------+ +--------+ +--------+ +--------+ +--------+
   |Journal | | Tasks  | |  Ideas | | Notes  | |WorkOS  |
   |(all)   | |(action)| |(future)| |(ref)   | |(work)  |
   +--------+ +--------+ +--------+ +--------+ +--------+
```

---

## Classification Types (9 Types)

The classifier uses Claude AI to analyze input and assign one of 9 classification types. The critical principle is: **Default to NOT creating tasks**.

### 1. thinking

Internal reflection, musing, pondering. No action required.

**Examples:**
- "I've been thinking about maybe starting to exercise more"
- "I wonder if we should refactor the authentication system"
- "What if we tried a different approach?"
- "Maybe I need to reconsider my priorities"

**Indicators:**
- "I've been thinking about..."
- "I wonder if..."
- "What if we..."
- "Maybe I need to..."
- Vague intentions without specific actions

**Destination:** Journal only (no task created)

---

### 2. venting

Emotional release, frustration, stress expression. The system acknowledges the emotion without creating tasks.

**Examples:**
- "UGH this stupid API keeps timing out and nobody seems to care!!"
- "I'm so tired of these endless meetings"
- "This is ridiculous, why can't anything work the first time"
- "I can't believe they changed the requirements again"

**Indicators:**
- Emotional language (frustrated, angry, tired, annoyed)
- Complaints without proposed solutions
- Rhetorical questions expressing frustration
- Multiple exclamation points or strong language

**Destination:** Journal only (acknowledged with empathy)

---

### 3. observation

Noting something without action needed. Pattern recognition or factual observations.

**Examples:**
- "I noticed that deployments take longer on Fridays"
- "It seems like the morning standup is less effective now"
- "The new design system looks cleaner than before"
- "Traffic patterns changed after the office move"

**Indicators:**
- "I noticed that..."
- "It seems like..."
- Factual observations without call to action

**Destination:** Journal only

---

### 4. note

Information to remember, not to act on. Reference material, facts, or contact info.

**Examples:**
- "Remember that the staging API key expires on Jan 31"
- "John's phone number is 555-1234"
- "The meeting room passcode is 4521"
- "The API endpoint changed to /v2/users"

**Indicators:**
- "Remember that..."
- Contact information
- Reference data
- Technical specifications

**Destination:** State store (as note) + Journal

---

### 5. idea

Creative thought worth capturing for later consideration. Not immediately actionable.

**Examples:**
- "What if we built a dashboard for real-time metrics?"
- "A cool feature would be voice-activated task creation"
- "We could use machine learning to predict task priorities"
- "Maybe a browser extension would help with capture"

**Indicators:**
- "What if we built..."
- "A cool feature would be..."
- Innovation, invention, improvement ideas
- Future possibilities

**Destination:** State store (as idea) + Journal

---

### 6. personal_task

Clear, specific personal action. Must have a concrete action and context.

**Examples:**
- "Need to call the dentist about my appointment"
- "Pick up groceries on the way home"
- "Pay the electric bill before Friday"
- "Schedule haircut for next week"

**Requirements (ALL must be present):**
- Specific verb (call, buy, pick up, schedule)
- Clear object/target (dentist, groceries, bill)
- Implicit or explicit timeline feasibility

**Destination:** State store (as task, domain="personal") + Journal

---

### 7. work_task

Clear, specific work action. Professional context with concrete action.

**Examples:**
- "Review Sarah's PR for the auth changes"
- "Send the quarterly report to the client"
- "Fix the login bug before the release"
- "Update the API documentation for v2"

**Requirements:**
- Work-related context (clients, projects, PRs, code, team)
- Specific action (review, send, fix, update)
- Clear target (specific PR, report, bug)

**Destination:** State store (as task, domain="work") + WorkOS sync (if configured) + Journal

---

### 8. commitment

Promise made to someone. Involves another person and a commitment.

**Examples:**
- "I told Sarah I'd have the design ready by Friday"
- "I promised Mike to help with the migration"
- "I committed to reviewing the proposal by end of day"
- "I agreed to mentor the new intern starting Monday"

**Requirements:**
- Another person involved (to_whom)
- Explicit or implicit promise/commitment
- Often includes a deadline

**Destination:** State store (as commitment) + Journal

---

### 9. mixed

Contains multiple distinct items that need separate handling.

**Examples:**
- "I should probably clean my desk at some point. Also need to buy milk."
- "The meeting was boring. Remind me to follow up with John about the contract."
- "I'm frustrated with the API issues. Actually, I need to file a bug report."

**Processing:**
Each segment is classified separately and routed independently.

**Destination:** Each segment routed to its appropriate destination

---

## Routing Rules

### What Happens to Each Classification Type

| Classification | Creates Task? | Journal Entry | State Store | WorkOS Sync |
|---------------|---------------|---------------|-------------|-------------|
| thinking      | No            | Yes           | Archive     | No          |
| venting       | No            | Yes           | Archive     | No          |
| observation   | No            | Yes           | Archive     | No          |
| note          | No*           | Yes           | Notes table | No          |
| idea          | No*           | Yes           | Ideas table | No          |
| personal_task | Yes           | Yes           | Tasks table | No          |
| work_task     | Yes           | Yes           | Tasks table | Yes         |
| commitment    | Yes**         | Yes           | Commitments | No          |
| mixed         | Varies        | Yes           | Per segment | Per segment |

*Notes and ideas are stored but not as actionable tasks
**Commitments create commitment records, not tasks

### Auto-Conversion to Tasks

Tasks are ONLY created when:
1. There is a **specific verb** (call, buy, fix, send, review)
2. There is a **clear object/target** (the dentist, groceries, the bug)
3. The timeline is **feasible** (implicit or explicit)

Tasks are NOT created for:
- Vague intentions ("I should probably...")
- Wishful thinking ("Maybe I need to...")
- Reflections ("I've been thinking about...")
- Emotional expressions

### WorkOS Sync Integration

Work tasks are automatically synced to WorkOS when:
1. Classification is `work_task`
2. WorkOS adapter is configured (`WORKOS_DATABASE_URL` environment variable)
3. The sync operation succeeds

WorkOS sync includes:
- Task title (from extracted task or first line)
- Task description (full brain dump content)
- Status: "backlog" (default)
- Effort estimate (mapped from priority)

Priority to effort mapping:
| Priority | Effort Estimate |
|----------|-----------------|
| critical | 5               |
| high     | 4               |
| medium   | 3               |
| low      | 2               |

---

## Telegram Bot Usage

### Setup Requirements

#### Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
ANTHROPIC_API_KEY=sk-ant-...

# Optional - for voice transcription
OPENAI_API_KEY=sk-...

# Optional - for WorkOS sync
WORKOS_DATABASE_URL=postgresql://...

# Optional - restrict to specific users
TELEGRAM_ALLOWED_USERS=123456789,987654321
```

#### Python Dependencies

```bash
pip install python-telegram-bot anthropic httpx asyncpg python-dotenv
```

#### Creating the Bot

1. Talk to [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token to `TELEGRAM_BOT_TOKEN`
4. Find your user ID (talk to [@userinfobot](https://t.me/userinfobot))
5. Add your user ID to `TELEGRAM_ALLOWED_USERS` for security

### Running the Bot

```bash
# From the Tools directory
python telegram_bot.py

# Or with test capture (no Telegram connection)
python telegram_bot.py --test-capture "Need to call the dentist"

# Or check status
python telegram_bot.py --status
```

### Text Message Handling

Simply send any text message to the bot. The flow is:

1. **Receive** - Bot receives your text message
2. **Classify** - AI classifier analyzes the content
3. **Route** - Router sends to appropriate destinations
4. **Respond** - Bot sends acknowledgment with classification

Example responses:

```
# For thinking/venting
"That's a good thing to consider. When you're ready to make it concrete, let me know."

# For a personal task
Personal Task
Domain: personal
Priority: medium
Task created

# For a work task with WorkOS
Work Task
Domain: work
Priority: high
Task created
Synced to WorkOS
```

### Voice Message Handling

Voice messages use OpenAI Whisper for transcription:

1. **Download** - Bot downloads the voice file (.ogg format)
2. **Transcribe** - Whisper API converts speech to text
3. **Process** - Same pipeline as text messages
4. **Respond** - Shows transcription + classification

Example flow:
```
User: [Voice message: "Remind me to review the quarterly report"]

Bot:
Transcription:
_Remind me to review the quarterly report_

Work Task
Domain: work
Task created
```

### Bot Commands

| Command   | Description                    |
|-----------|--------------------------------|
| `/start`  | Welcome message and help       |
| `/status` | View pending brain dump items  |

### Work/Personal Context Detection

The classifier automatically detects context:

**Work indicators:**
- Client mentions
- Project names
- PR/code references
- Meeting mentions
- Team member names
- Technical terms (deploy, release, sprint)

**Personal indicators:**
- Family references
- Health/medical mentions
- Errands (grocery, pharmacy)
- Home tasks
- Personal appointments
- Hobbies/entertainment

---

## API Reference

### BrainDumpClassifier

Main class for AI-powered classification.

```python
from Tools.brain_dump import BrainDumpClassifier

# Initialize
classifier = BrainDumpClassifier(
    api_key="sk-ant-...",  # Optional, uses ANTHROPIC_API_KEY env var
    model="claude-sonnet-4-20250514"  # Default model
)

# Async classification
result = await classifier.classify(
    text="Need to call the dentist",
    source="telegram"  # or "manual", "voice", "api"
)

# Sync classification (wrapper)
result = classifier.classify_sync(
    text="Need to call the dentist",
    source="manual"
)
```

#### ClassifiedBrainDump Result

```python
@dataclass
class ClassifiedBrainDump:
    id: str                          # Unique identifier
    raw_text: str                    # Original input
    source: str                      # Input source
    classification: str              # One of 9 types
    confidence: float                # 0.0 - 1.0
    reasoning: str                   # Why this classification
    acknowledgment: Optional[str]    # User-friendly response
    task: Optional[Dict]             # Extracted task data
    commitment: Optional[Dict]       # Extracted commitment data
    idea: Optional[Dict]             # Extracted idea data
    note: Optional[Dict]             # Extracted note data
    segments: Optional[List[Dict]]   # For mixed classification
    timestamp: str                   # ISO timestamp
```

#### Methods

```python
# Check if actionable
result.is_actionable()  # True for personal_task, work_task, commitment

# Check for extracted data
result.has_task()       # True if task was extracted
result.has_commitment() # True if commitment was extracted

# Convert to dictionary
result.to_dict()        # Full dict representation
```

### BrainDumpRouter

Routes classified brain dumps to appropriate destinations.

```python
from Tools.brain_dump import BrainDumpRouter
from Tools.unified_state import StateStore
from Tools.journal import Journal

# Initialize
state = StateStore()
journal = Journal()
router = BrainDumpRouter(
    state=state,
    journal=journal,
    workos_adapter=None  # Optional WorkOS adapter
)

# Route a classified dump
result = await router.route(classified_dump)
```

#### RoutingResult

```python
@dataclass
class RoutingResult:
    dump_id: str                     # Brain dump ID
    tasks_created: List[str]         # Created task IDs
    commitment_created: Optional[str] # Created commitment ID
    idea_created: Optional[str]      # Created idea ID
    note_created: Optional[str]      # Created note ID
    journal_entry: Optional[int]     # Journal entry ID
    acknowledgment: Optional[str]    # User-facing message
    workos_task_id: Optional[int]    # WorkOS task ID (if synced)
    errors: List[str]                # Any errors during routing
```

#### Methods

```python
# Check success
result.success              # True if no errors

# Get summary
result.summary()            # "1 task(s) created, synced to WorkOS (#123)"

# Merge results (for mixed classification)
result.merge(other_result)  # Combines results
```

### Integration Examples

#### Basic Classification and Routing

```python
import asyncio
from Tools.brain_dump import BrainDumpClassifier, BrainDumpRouter
from Tools.unified_state import get_state_store
from Tools.journal import Journal

async def process_brain_dump(text: str):
    # Initialize components
    classifier = BrainDumpClassifier()
    state = get_state_store()
    journal = Journal()
    router = BrainDumpRouter(state, journal)

    # Classify
    classified = await classifier.classify(text, source="api")

    # Route
    result = await router.route(classified)

    return {
        "classification": classified.classification,
        "confidence": classified.confidence,
        "acknowledgment": result.acknowledgment,
        "tasks_created": result.tasks_created
    }

# Run
output = asyncio.run(process_brain_dump("Review the PR for auth changes"))
print(output)
```

#### Convenience Functions

```python
from Tools.brain_dump import classify_brain_dump, classify_brain_dump_sync

# Async
result = await classify_brain_dump("Need to call dentist")

# Sync
result = classify_brain_dump_sync("Need to call dentist")
```

#### Full Pipeline with WorkOS

```python
from Tools.brain_dump import BrainDumpClassifier, BrainDumpRouter
from Tools.unified_state import get_state_store
from Tools.journal import Journal
from Tools.adapters.workos import WorkOSAdapter

async def full_pipeline(text: str):
    classifier = BrainDumpClassifier()
    state = get_state_store()
    journal = Journal()

    # Setup WorkOS adapter if configured
    workos_adapter = WorkOSAdapter() if os.getenv('WORKOS_DATABASE_URL') else None

    router = BrainDumpRouter(state, journal, workos_adapter)

    # Process
    classified = await classifier.classify(text, source="api")
    result = await router.route(classified)

    return result
```

### StateStore Brain Dump Methods

The unified state store provides methods for brain dump storage:

```python
from Tools.state_store import get_db

store = get_db()

# Create brain dump entry
store.create_brain_dump(
    content="Need to review the PR",
    source="telegram",
    category="work_task",
    domain="work",
    metadata={
        "entry_id": "bd_123",
        "confidence": 0.95
    }
)

# Add task (called by router for task classifications)
task_id = store.add_task(
    title="Review the PR",
    description="Need to review the PR for auth changes",
    priority="medium",
    source="brain_dump",
    metadata={"dump_id": "abc123", "domain": "work"}
)

# Add commitment
commitment_id = store.add_commitment(
    title="Have design ready",
    description="I told Sarah I'd have the design ready by Friday",
    stakeholder="Sarah",
    deadline=date(2026, 1, 24),
    metadata={"dump_id": "def456"}
)
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for classification |
| `TELEGRAM_BOT_TOKEN` | For bot | Telegram bot token |
| `OPENAI_API_KEY` | For voice | Whisper API key for transcription |
| `TELEGRAM_ALLOWED_USERS` | Recommended | Comma-separated user IDs |
| `WORKOS_DATABASE_URL` | For WorkOS | PostgreSQL connection string |

### Classification Model

Default: `claude-sonnet-4-20250514`

Can be changed when initializing the classifier:

```python
classifier = BrainDumpClassifier(model="claude-3-5-sonnet-latest")
```

### Storage Locations

| Data | Location |
|------|----------|
| Brain dump archive | `State/thanos_unified.db` (state table) |
| Tasks | `State/thanos_unified.db` (tasks table) |
| Commitments | `State/thanos_unified.db` (commitments table) |
| Legacy entries | `State/brain_dumps.json` |
| Journal | `State/journal/` directory |

---

## Troubleshooting

### Classification Always Returns "thinking"

- Check `ANTHROPIC_API_KEY` is set correctly
- Verify API key has sufficient credits
- Check logs for classification errors
- The system defaults to "thinking" when classification fails

### Voice Messages Not Transcribing

- Verify `OPENAI_API_KEY` is set
- Check if `httpx` package is installed: `pip install httpx`
- Confirm API key has Whisper API access
- Check logs for transcription errors

### WorkOS Sync Failing

- Verify `WORKOS_DATABASE_URL` is correct
- Check if `asyncpg` is installed: `pip install asyncpg`
- Ensure database is accessible and SSL is configured
- Check for connection timeout issues

### Bot Not Responding

- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check if your user ID is in `TELEGRAM_ALLOWED_USERS`
- Ensure `python-telegram-bot` is installed
- Check bot logs for errors

---

## File Locations

| File | Purpose |
|------|---------|
| `/Users/jeremy/Projects/Thanos/Tools/brain_dump/classifier.py` | AI classification logic |
| `/Users/jeremy/Projects/Thanos/Tools/brain_dump/router.py` | Routing to destinations |
| `/Users/jeremy/Projects/Thanos/Tools/telegram_bot.py` | Telegram bot integration |
| `/Users/jeremy/Projects/Thanos/Tools/unified_state.py` | State storage methods |
