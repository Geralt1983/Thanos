# Thanos Intelligent Memory Architecture

> ⚠️ **LEGACY DOCUMENT**
>
> **Memory V2 is now the PRIMARY architecture.**
> See [ADR-012: Memory V2](adr/012-memory-v2-voyage-neon-heat.md) for the current implementation.
>
> **Key Changes (2026-01-23):**
> - All memory operations route through `Tools/memory_router.py` (defaults to V2)
> - Memory V2 uses: **mem0 + Neon pgvector + OpenAI embeddings + Heat Decay**
> - Legacy systems (ChromaDB, SQLite) available as explicit fallbacks only
> - Migration utility: `scripts/migrate_to_memory_v2.py`
>
> **Usage:**
> ```python
> from Tools.memory_router import add_memory, search_memory, whats_hot, whats_cold
>
> add_memory("Meeting notes with Orlando", metadata={"client": "Orlando"})
> results = search_memory("What did Orlando say?")
> hot = whats_hot()  # Current focus
> cold = whats_cold()  # What am I neglecting?
> ```

---

## Legacy Architecture (Historical Reference)

The content below describes the original SQLite + ChromaDB architecture. This is retained for historical reference and understanding legacy code paths.

---

## Executive Summary

This document defines the architecture for an intelligent memory system that captures daily activities, detects struggles, recognizes what matters to the user, and provides temporal intelligence for natural language queries. The system builds on Thanos's existing four-pillar architecture (Trust, Capture, Clarity, Resilience) by adding a fifth pillar: **Memory**.

```
                    +---------------------------+
                    |      User Interfaces      |
                    |  CLI | Telegram | Voice   |
                    +-------------+-------------+
                                  |
    +-----------------------------+-----------------------------+
    |              |              |              |              |
    v              v              v              v              v
+--------+    +--------+    +---------+    +---------+    +---------+
| TRUST  |    |CAPTURE |    | CLARITY |    |RESILIENCE|   | MEMORY  |
|        |    |        |    |         |    |          |   |  (NEW)  |
| SQLite |    | Brain  |    | Alert   |    | Circuit  |   | Chroma  |
| State  |    | Dump   |    | Checker |    | Breaker  |   | + SQL   |
+--------+    +--------+    +---------+    +---------+    +---------+
    |              |              |              |              |
    +-----------------------------+-----------------------------+
                                  |
                    +---------------------------+
                    |   Memory Coordination     |
                    |   Layer (Event-Driven)    |
                    +---------------------------+
```

---

## 1. Data Architecture

### 1.1 Dual-Store Design

The memory system uses a **hybrid architecture** combining:

1. **SQLite** - Structured temporal data, activity logs, metrics
2. **ChromaDB** - Semantic embeddings for natural language search

This separation allows:
- Fast temporal queries on SQLite (indexes, date ranges)
- Semantic similarity search on ChromaDB (meaning-based retrieval)
- Joins between stores for rich contextual recall

### 1.2 SQLite Schema - Activity Memory

```sql
-- ============================================================================
-- ACTIVITIES - Everything the user did
-- ============================================================================
CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    date DATE GENERATED ALWAYS AS (DATE(timestamp)) STORED,
    hour INTEGER GENERATED ALWAYS AS (CAST(STRFTIME('%H', timestamp) AS INTEGER)) STORED,
    day_of_week INTEGER GENERATED ALWAYS AS (STRFTIME('%w', timestamp)) STORED,

    -- Activity classification
    activity_type TEXT NOT NULL CHECK (activity_type IN (
        'conversation',      -- Chat/interaction with Thanos
        'task_work',         -- Working on a task
        'task_complete',     -- Completed a task
        'brain_dump',        -- Brain dump input
        'command',           -- Explicit command execution
        'calendar_event',    -- Calendar event started/attended
        'health_logged',     -- Health data logged
        'commitment_made',   -- Made a commitment
        'commitment_fulfilled', -- Fulfilled a commitment
        'focus_session',     -- Deep work session
        'break',             -- Break taken
        'context_switch'     -- Switched contexts/projects
    )),

    -- Activity details
    title TEXT NOT NULL,
    description TEXT,
    content TEXT,           -- Full content (for conversations, brain dumps)

    -- Context
    project TEXT,           -- Associated project/client
    domain TEXT CHECK (domain IN ('work', 'personal')),
    energy_level TEXT CHECK (energy_level IN ('high', 'medium', 'low')),

    -- Duration tracking
    duration_minutes INTEGER,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,

    -- Source tracking
    source TEXT NOT NULL,   -- 'telegram', 'cli', 'voice', 'system', 'calendar'
    source_context JSON,    -- Additional source-specific data

    -- Relationships
    related_task_id TEXT,
    related_event_id TEXT,
    related_commitment_id TEXT,
    session_id TEXT,        -- Group activities in a session

    -- Emotional/struggle markers
    sentiment TEXT CHECK (sentiment IN ('positive', 'neutral', 'negative', 'frustrated', 'anxious', 'excited')),
    struggle_detected BOOLEAN DEFAULT FALSE,
    struggle_type TEXT,     -- 'confusion', 'frustration', 'blocked', 'overwhelmed', 'procrastination'

    -- Search optimization
    search_text TEXT,       -- Concatenated searchable text

    -- Metadata
    metadata JSON,
    embedding_id TEXT,      -- Reference to ChromaDB embedding

    FOREIGN KEY (related_task_id) REFERENCES tasks(id),
    FOREIGN KEY (related_event_id) REFERENCES calendar_events(id),
    FOREIGN KEY (related_commitment_id) REFERENCES commitments(id)
);

-- Indexes for temporal queries
CREATE INDEX IF NOT EXISTS idx_activities_timestamp ON activities(timestamp);
CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(date);
CREATE INDEX IF NOT EXISTS idx_activities_hour ON activities(hour);
CREATE INDEX IF NOT EXISTS idx_activities_day_of_week ON activities(day_of_week);
CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_activities_project ON activities(project);
CREATE INDEX IF NOT EXISTS idx_activities_domain ON activities(domain);
CREATE INDEX IF NOT EXISTS idx_activities_session ON activities(session_id);
CREATE INDEX IF NOT EXISTS idx_activities_struggle ON activities(struggle_detected);

-- Full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS activities_fts USING fts5(
    title, description, content, search_text,
    content='activities',
    content_rowid='rowid'
);

-- FTS triggers
CREATE TRIGGER IF NOT EXISTS activities_ai AFTER INSERT ON activities BEGIN
    INSERT INTO activities_fts(rowid, title, description, content, search_text)
    VALUES (NEW.rowid, NEW.title, NEW.description, NEW.content, NEW.search_text);
END;

CREATE TRIGGER IF NOT EXISTS activities_ad AFTER DELETE ON activities BEGIN
    INSERT INTO activities_fts(activities_fts, rowid, title, description, content, search_text)
    VALUES ('delete', OLD.rowid, OLD.title, OLD.description, OLD.content, OLD.search_text);
END;

CREATE TRIGGER IF NOT EXISTS activities_au AFTER UPDATE ON activities BEGIN
    INSERT INTO activities_fts(activities_fts, rowid, title, description, content, search_text)
    VALUES ('delete', OLD.rowid, OLD.title, OLD.description, OLD.content, OLD.search_text);
    INSERT INTO activities_fts(rowid, title, description, content, search_text)
    VALUES (NEW.rowid, NEW.title, NEW.description, NEW.content, NEW.search_text);
END;

-- ============================================================================
-- STRUGGLES - Detected difficulties and blockers
-- ============================================================================
CREATE TABLE IF NOT EXISTS struggles (
    id TEXT PRIMARY KEY,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date DATE GENERATED ALWAYS AS (DATE(detected_at)) STORED,

    -- Struggle classification
    struggle_type TEXT NOT NULL CHECK (struggle_type IN (
        'confusion',        -- User doesn't understand something
        'frustration',      -- User is frustrated
        'blocked',          -- Can't proceed (external dependency)
        'overwhelmed',      -- Too much to do
        'procrastination',  -- Avoiding a task
        'decision_paralysis', -- Can't decide
        'energy_low',       -- Depleted energy
        'context_switch',   -- Too many context switches
        'interruption',     -- External interruptions
        'technical',        -- Technical problem
        'communication',    -- Communication breakdown
        'deadline_pressure' -- Deadline stress
    )),

    -- Details
    title TEXT NOT NULL,
    description TEXT,
    trigger_text TEXT,      -- The text that triggered detection

    -- Context
    project TEXT,
    domain TEXT CHECK (domain IN ('work', 'personal')),
    related_task_id TEXT,

    -- Temporal patterns
    time_of_day TEXT CHECK (time_of_day IN ('morning', 'afternoon', 'evening', 'night')),
    day_of_week INTEGER,

    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,

    -- Pattern tracking
    recurrence_count INTEGER DEFAULT 1,  -- How many times similar struggle detected
    last_occurred TIMESTAMP,

    -- Metadata
    confidence REAL,        -- Detection confidence
    source_activity_id TEXT,
    metadata JSON,

    FOREIGN KEY (related_task_id) REFERENCES tasks(id),
    FOREIGN KEY (source_activity_id) REFERENCES activities(id)
);

CREATE INDEX IF NOT EXISTS idx_struggles_date ON struggles(date);
CREATE INDEX IF NOT EXISTS idx_struggles_type ON struggles(struggle_type);
CREATE INDEX IF NOT EXISTS idx_struggles_project ON struggles(project);
CREATE INDEX IF NOT EXISTS idx_struggles_resolved ON struggles(resolved);
CREATE INDEX IF NOT EXISTS idx_struggles_time ON struggles(time_of_day);

-- ============================================================================
-- VALUES - What matters to the user
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_values (
    id TEXT PRIMARY KEY,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_reinforced TIMESTAMP,

    -- Value details
    value_type TEXT NOT NULL CHECK (value_type IN (
        'priority',         -- Explicitly stated priority
        'relationship',     -- Important person/client
        'commitment',       -- Keeping promises
        'project',          -- Important project
        'goal',             -- Explicit goal
        'principle',        -- How they work
        'boundary',         -- What they won't do
        'preference'        -- How they like things
    )),

    title TEXT NOT NULL,
    description TEXT,

    -- Importance tracking
    mention_count INTEGER DEFAULT 1,
    emotional_weight REAL DEFAULT 0.5,  -- 0-1 based on emotional emphasis
    explicit_importance BOOLEAN DEFAULT FALSE,  -- User explicitly said important

    -- Context
    domain TEXT CHECK (domain IN ('work', 'personal', 'health', 'relationship', 'financial', 'growth')),
    related_entity TEXT,    -- Person, project, or thing this relates to

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Evidence
    source_quotes JSON,     -- Quotes that revealed this value

    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_values_type ON user_values(value_type);
CREATE INDEX IF NOT EXISTS idx_values_domain ON user_values(domain);
CREATE INDEX IF NOT EXISTS idx_values_active ON user_values(is_active);
CREATE INDEX IF NOT EXISTS idx_values_entity ON user_values(related_entity);

-- ============================================================================
-- RELATIONSHIPS - People and entities the user cares about
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_relationships (
    id TEXT PRIMARY KEY,

    -- Entity details
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'client', 'colleague', 'family', 'friend', 'stakeholder', 'vendor', 'other'
    )),

    -- Importance
    importance TEXT CHECK (importance IN ('critical', 'high', 'medium', 'low')),
    mention_count INTEGER DEFAULT 1,
    last_mentioned TIMESTAMP,

    -- Context
    company TEXT,
    role TEXT,
    domain TEXT CHECK (domain IN ('work', 'personal')),

    -- Relationship quality
    sentiment_trend TEXT CHECK (sentiment_trend IN ('positive', 'neutral', 'negative', 'mixed')),

    -- Interaction tracking
    last_interaction_date DATE,
    interaction_frequency TEXT CHECK (interaction_frequency IN ('daily', 'weekly', 'monthly', 'rarely')),

    -- Notes
    notes TEXT,
    key_facts JSON,         -- Important things to remember about them
    commitments_to JSON,    -- Outstanding commitments to this person

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_relationships_name ON memory_relationships(entity_name);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON memory_relationships(entity_type);
CREATE INDEX IF NOT EXISTS idx_relationships_importance ON memory_relationships(importance);
CREATE INDEX IF NOT EXISTS idx_relationships_domain ON memory_relationships(domain);

-- ============================================================================
-- DAILY SUMMARIES - Aggregated daily activity data
-- ============================================================================
CREATE TABLE IF NOT EXISTS daily_summaries (
    date DATE PRIMARY KEY,

    -- Activity counts
    total_activities INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    tasks_created INTEGER DEFAULT 0,
    brain_dumps INTEGER DEFAULT 0,
    commands_executed INTEGER DEFAULT 0,

    -- Time tracking
    first_activity_time TIME,
    last_activity_time TIME,
    total_active_minutes INTEGER DEFAULT 0,

    -- Productivity metrics
    focus_sessions INTEGER DEFAULT 0,
    focus_minutes INTEGER DEFAULT 0,
    context_switches INTEGER DEFAULT 0,

    -- Emotional metrics
    struggles_detected INTEGER DEFAULT 0,
    predominant_sentiment TEXT,
    energy_trend TEXT CHECK (energy_trend IN ('increasing', 'stable', 'decreasing', 'variable')),

    -- Domain breakdown
    work_activities INTEGER DEFAULT 0,
    personal_activities INTEGER DEFAULT 0,

    -- Projects worked on
    projects_touched JSON,  -- ["project1", "project2"]

    -- Highlights
    key_accomplishments JSON,
    notable_struggles JSON,

    -- Health correlation (if Oura data available)
    oura_readiness INTEGER,
    oura_sleep_score INTEGER,
    oura_activity_score INTEGER,

    -- Summary
    generated_summary TEXT,  -- AI-generated summary
    user_reflection TEXT,    -- User's own notes

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- WEEKLY PATTERNS - Aggregated patterns across weeks
-- ============================================================================
CREATE TABLE IF NOT EXISTS weekly_patterns (
    id TEXT PRIMARY KEY,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,

    -- Activity patterns by day of week
    busiest_day INTEGER,           -- 0=Sunday, 6=Saturday
    quietest_day INTEGER,
    avg_tasks_per_day REAL,

    -- Time patterns
    typical_start_hour INTEGER,
    typical_end_hour INTEGER,
    peak_productivity_hours JSON,  -- [9, 10, 14, 15]

    -- Struggle patterns
    common_struggle_types JSON,
    struggle_peak_times JSON,

    -- Project focus
    primary_projects JSON,
    project_time_distribution JSON,

    -- Health correlation
    avg_readiness INTEGER,
    productivity_health_correlation REAL,

    -- Insights
    generated_insights JSON,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_weekly_patterns_week ON weekly_patterns(week_start);

-- ============================================================================
-- MEMORY SESSIONS - Track conversation sessions for context
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_sessions (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,

    -- Session metadata
    source TEXT NOT NULL,   -- 'telegram', 'cli', etc.
    duration_minutes INTEGER,

    -- Activity within session
    activity_count INTEGER DEFAULT 0,
    brain_dumps_count INTEGER DEFAULT 0,
    commands_count INTEGER DEFAULT 0,

    -- Context
    primary_topic TEXT,
    projects_discussed JSON,

    -- Emotional arc
    starting_sentiment TEXT,
    ending_sentiment TEXT,
    struggles_during JSON,

    -- Summary
    summary TEXT,

    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_sessions_started ON memory_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_source ON memory_sessions(source);
```

### 1.3 ChromaDB Collections - Semantic Memory

```python
MEMORY_COLLECTIONS = {
    "activities": {
        "description": "All user activities for semantic search",
        "metadata_fields": [
            "date", "activity_type", "project", "domain",
            "sentiment", "struggle_detected"
        ]
    },
    "conversations": {
        "description": "Full conversation content for context recall",
        "metadata_fields": [
            "date", "session_id", "topic", "sentiment"
        ]
    },
    "struggles": {
        "description": "Detected struggles for pattern matching",
        "metadata_fields": [
            "date", "struggle_type", "project", "resolved"
        ]
    },
    "values": {
        "description": "User values and priorities for relevance matching",
        "metadata_fields": [
            "value_type", "domain", "importance", "active"
        ]
    },
    "insights": {
        "description": "Generated insights and learnings",
        "metadata_fields": [
            "date", "insight_type", "domain"
        ]
    },
    "daily_summaries": {
        "description": "Daily summary embeddings for historical recall",
        "metadata_fields": [
            "date", "day_of_week", "productivity_score"
        ]
    }
}
```

---

## 2. Memory Capture System

### 2.1 Automatic Capture Triggers

The memory system captures data automatically through event hooks:

```
+------------------+     +-------------------+     +------------------+
|   Event Source   | --> |  Memory Capture   | --> | Storage Layers   |
+------------------+     +-------------------+     +------------------+
| - Brain Dump     |     | - Classify Event  |     | - SQLite (struct)|
| - Command Exec   |     | - Extract Context |     | - ChromaDB (vec) |
| - Task Complete  |     | - Detect Patterns |     | - Journal (audit)|
| - Calendar Sync  |     | - Generate Embed  |     +------------------+
| - Health Import  |     | - Link Relations  |
| - Conversation   |     +-------------------+
+------------------+
```

### 2.2 Capture Event Types

| Event | Capture Trigger | Data Captured |
|-------|-----------------|---------------|
| Brain Dump | `brain_dump_received` | Raw text, classification, sentiment, entities |
| Command | `command_executed` | Command, result, context, duration |
| Task Work | `task_updated` (status change) | Task context, time spent, project |
| Task Complete | `task_completed` | Full task data, duration, blockers |
| Calendar | `event_started`, `event_ended` | Event details, attendees, notes |
| Health | `health_metric_logged` | Oura scores, correlations |
| Conversation | Every user message | Full content, sentiment, entities |

### 2.3 Memory Capture Pipeline

```python
class MemoryCapturePipeline:
    """Processes events through the memory capture pipeline."""

    async def capture(self, event: Dict) -> CaptureResult:
        """
        Main capture entry point.

        Pipeline:
        1. Classify event
        2. Extract entities and context
        3. Detect struggles
        4. Detect values
        5. Generate embeddings
        6. Store in both layers
        7. Update relationships
        """

        # Step 1: Classify the event
        activity_type = self._classify_event(event)

        # Step 2: Extract context
        context = await self._extract_context(event)

        # Step 3: Detect struggles (if applicable)
        struggle = await self._detect_struggle(event, context)

        # Step 4: Detect values (if applicable)
        value = await self._detect_value(event, context)

        # Step 5: Generate embedding
        embedding_text = self._generate_embedding_text(event, context)
        embedding_id = await self._store_embedding(embedding_text, context)

        # Step 6: Store activity in SQLite
        activity_id = await self._store_activity(
            event, activity_type, context, struggle, embedding_id
        )

        # Step 7: Update relationships if entities detected
        if context.entities:
            await self._update_relationships(context.entities, event)

        return CaptureResult(
            activity_id=activity_id,
            embedding_id=embedding_id,
            struggle_detected=struggle is not None,
            values_detected=value is not None
        )
```

---

## 3. Struggle Detection System

### 3.1 Detection Signals

The system detects struggles through multiple signals:

| Signal Type | Examples | Weight |
|-------------|----------|--------|
| **Linguistic** | "frustrated", "stuck", "confused", "can't", "don't understand" | High |
| **Emotional** | Multiple exclamation marks, caps, expletives | High |
| **Behavioral** | Same task touched 3+ times, long pauses, context switching | Medium |
| **Temporal** | Late night work, weekend work, unusual hours | Medium |
| **Health** | Low readiness score, poor sleep, high stress | Medium |
| **Explicit** | "I'm struggling with...", "This is hard", "Help" | Very High |

### 3.2 Struggle Detection Prompt

```python
STRUGGLE_DETECTION_PROMPT = '''
Analyze this user input for signs of struggle. Look for:

1. **Confusion** - Not understanding something
   - "I don't get...", "What does X mean?", "How do I..."

2. **Frustration** - Emotional difficulty
   - Exclamation marks, complaints, "ugh", "argh"

3. **Blocked** - External dependency stopping progress
   - "Waiting for...", "Can't proceed until...", "Dependent on..."

4. **Overwhelmed** - Too much to handle
   - Lists of many things, "so much", "everything", "all the..."

5. **Procrastination** - Avoiding something
   - Returning to same task repeatedly, "I should...", task avoidance patterns

6. **Decision Paralysis** - Can't decide
   - "Should I X or Y?", weighing options repeatedly

7. **Energy Low** - Depleted
   - "tired", "exhausted", "need a break", "drained"

Return JSON:
{
  "struggle_detected": true/false,
  "struggle_type": "type or null",
  "confidence": 0.0-1.0,
  "reasoning": "why this was detected",
  "severity": "low/medium/high",
  "suggested_response": "empathetic acknowledgment"
}
'''
```

### 3.3 Pattern Recognition

The system tracks struggle patterns over time:

```python
class StrugglePatternAnalyzer:
    """Analyzes struggle patterns to identify recurring issues."""

    def analyze_patterns(self, user_id: str, days: int = 30) -> PatternAnalysis:
        """
        Analyze struggle patterns over time.

        Returns:
        - Time-based patterns (when struggles occur)
        - Type-based patterns (what kinds of struggles)
        - Project-based patterns (where struggles occur)
        - Health correlations (struggles vs. readiness)
        """

        struggles = self._get_struggles(user_id, days)

        return PatternAnalysis(
            time_patterns=self._analyze_time_patterns(struggles),
            type_frequency=self._analyze_type_frequency(struggles),
            project_correlation=self._analyze_project_correlation(struggles),
            health_correlation=self._analyze_health_correlation(struggles),
            recurring_struggles=self._find_recurring_struggles(struggles)
        )
```

---

## 4. Value Recognition System

### 4.1 Value Detection Signals

| Signal | Detection Method | Example |
|--------|-----------------|---------|
| Explicit Priority | Keywords + emphasis | "This is really important", "Priority is..." |
| Repeated Mention | Frequency tracking | Mentioning "Memphis" project 10+ times |
| Emotional Emphasis | Sentiment + intensity | "I LOVE working on...", "This matters to me" |
| Commitment Pattern | Promise tracking | Consistent commitment fulfillment to person X |
| Time Investment | Activity tracking | Most time spent on project Y |
| Protective Language | Boundary detection | "I don't work weekends", "Family time is sacred" |

### 4.2 Value Detection Pipeline

```python
class ValueDetector:
    """Detects and tracks user values and priorities."""

    DETECTION_PROMPT = '''
    Analyze this input for signals of user values:

    1. **Explicit Priorities** - Direct statements of importance
    2. **Relationships** - People who matter (clients, family, colleagues)
    3. **Commitments** - What they commit to and follow through on
    4. **Projects** - Work they care deeply about
    5. **Principles** - How they prefer to work
    6. **Boundaries** - What they won't compromise on

    Return JSON:
    {
      "value_detected": true/false,
      "value_type": "type",
      "title": "short title",
      "description": "what this value represents",
      "emotional_weight": 0.0-1.0,
      "explicit": true/false,
      "evidence_quote": "the text that revealed this"
    }
    '''

    def detect(self, text: str, context: Dict) -> Optional[DetectedValue]:
        """Detect values in user input."""
        # AI-powered detection
        result = self._ai_detect(text)

        if result.value_detected:
            # Check if this reinforces existing value
            existing = self._find_similar_value(result)
            if existing:
                self._reinforce_value(existing, result)
            else:
                self._create_value(result)

        return result
```

### 4.3 Relationship Tracking

```python
class RelationshipTracker:
    """Tracks people and entities the user mentions."""

    def track_mention(self, entity_name: str, context: Dict):
        """
        Track a mention of a person/entity.

        - Increment mention count
        - Update last_mentioned timestamp
        - Analyze sentiment of mention
        - Track any commitments made
        - Update importance based on patterns
        """

        relationship = self._get_or_create(entity_name)

        relationship.mention_count += 1
        relationship.last_mentioned = datetime.now()

        # Update sentiment trend
        if context.sentiment:
            self._update_sentiment_trend(relationship, context.sentiment)

        # Check for commitments
        if context.commitment_detected:
            self._add_commitment(relationship, context.commitment)

        # Re-evaluate importance
        self._reevaluate_importance(relationship)

        self._save(relationship)
```

---

## 5. Temporal Intelligence

### 5.1 Query Parser

The system parses natural language temporal queries:

```python
TEMPORAL_PATTERNS = {
    # Specific day references
    r"(last|this) (monday|tuesday|wednesday|thursday|friday|saturday|sunday)": "specific_day",
    r"yesterday": "yesterday",
    r"today": "today",
    r"(last|this) week": "week",
    r"(last|this) month": "month",

    # Relative references
    r"(\d+) days? ago": "days_ago",
    r"(\d+) weeks? ago": "weeks_ago",
    r"the past (\d+) days?": "past_days",

    # Activity-based
    r"when did I (last )?(work on|touch|update) (.+)": "last_activity_on",
    r"when was the last time I (.+)": "last_time_action",

    # Pattern queries
    r"what (did|have) I (been )?doing (.+)": "activity_query",
    r"show me my (.+) (pattern|trend|history)": "pattern_query",
}

class TemporalQueryParser:
    """Parses natural language queries into temporal parameters."""

    def parse(self, query: str) -> TemporalQuery:
        """
        Parse a natural language query.

        Examples:
        - "What did I do last Tuesday?" -> date range for last Tuesday
        - "When did I last work on Memphis?" -> search for Memphis activities
        - "Show me my productivity pattern this week" -> week pattern analysis
        """

        # Detect query type
        query_type = self._detect_query_type(query)

        # Extract temporal parameters
        date_range = self._extract_date_range(query, query_type)

        # Extract filters
        filters = self._extract_filters(query)

        return TemporalQuery(
            query_type=query_type,
            original_query=query,
            date_range=date_range,
            filters=filters
        )
```

### 5.2 Query Types

| Query Type | Example | Resolution |
|------------|---------|------------|
| `day_recall` | "What did I do last Tuesday?" | Activities for specific date |
| `project_history` | "When did I last work on Memphis?" | Last activity matching project |
| `pattern_analysis` | "Show me my productivity this week" | Weekly pattern analysis |
| `struggle_recall` | "What was I struggling with yesterday?" | Struggles for date range |
| `accomplishment` | "What did I accomplish this week?" | Completed tasks and milestones |
| `comparison` | "Am I more productive mornings or afternoons?" | Pattern comparison |

### 5.3 Query Execution

```python
class MemoryQueryExecutor:
    """Executes temporal queries against the memory system."""

    async def execute(self, query: TemporalQuery) -> QueryResult:
        """
        Execute a parsed temporal query.

        Strategy:
        1. SQLite for structured temporal data
        2. ChromaDB for semantic matching
        3. Combine results with relevance ranking
        """

        # Get structured results from SQLite
        sql_results = await self._execute_sql_query(query)

        # Get semantic results from ChromaDB
        if query.needs_semantic_search:
            semantic_results = await self._execute_semantic_query(query)
            results = self._merge_results(sql_results, semantic_results)
        else:
            results = sql_results

        # Generate summary if requested
        if query.wants_summary:
            summary = await self._generate_summary(results, query)
            return QueryResult(results=results, summary=summary)

        return QueryResult(results=results)
```

---

## 6. Memory Retrieval API

### 6.1 Command Interface

```bash
# Memory Commands
/memory search <query>          # Semantic search across all memory
/memory today                   # Today's activity summary
/memory week                    # This week's summary and patterns
/memory struggles               # Recent struggles and patterns
/memory values                  # Recognized user values
/memory <entity>                # Everything about a person/project
/memory when <action>           # When did I last do X?
/memory compare <a> vs <b>      # Compare time periods or projects
```

### 6.2 Python API

```python
class MemoryService:
    """Main API for the memory system."""

    # === Search APIs ===

    async def search(
        self,
        query: str,
        date_range: Optional[Tuple[date, date]] = None,
        activity_types: Optional[List[str]] = None,
        projects: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[MemoryResult]:
        """Semantic search across all memory."""
        pass

    async def search_similar(
        self,
        reference: str,
        limit: int = 10
    ) -> List[MemoryResult]:
        """Find memories similar to reference text."""
        pass

    # === Temporal APIs ===

    async def get_day(self, target_date: date) -> DaySummary:
        """Get summary for a specific day."""
        pass

    async def get_week(self, week_start: date) -> WeekSummary:
        """Get summary for a specific week."""
        pass

    async def get_activity_history(
        self,
        project: Optional[str] = None,
        entity: Optional[str] = None,
        days: int = 30
    ) -> List[Activity]:
        """Get activity history with optional filters."""
        pass

    async def when_last(self, action: str) -> Optional[Activity]:
        """Find when an action was last performed."""
        pass

    # === Pattern APIs ===

    async def get_productivity_pattern(
        self,
        days: int = 14
    ) -> ProductivityPattern:
        """Analyze productivity patterns over time."""
        pass

    async def get_struggle_patterns(
        self,
        days: int = 30
    ) -> StrugglePattern:
        """Analyze struggle patterns over time."""
        pass

    # === Context APIs ===

    async def get_relevant_context(
        self,
        current_input: str,
        limit: int = 5
    ) -> List[MemoryResult]:
        """Get memories relevant to current conversation."""
        pass

    async def get_entity_context(
        self,
        entity_name: str
    ) -> EntityContext:
        """Get all context about a person/project."""
        pass

    # === Value APIs ===

    async def get_values(
        self,
        value_type: Optional[str] = None
    ) -> List[UserValue]:
        """Get recognized user values."""
        pass

    async def get_relationships(
        self,
        importance: Optional[str] = None
    ) -> List[Relationship]:
        """Get tracked relationships."""
        pass
```

### 6.3 Contextual Auto-Surface

The system automatically surfaces relevant memories during conversations:

```python
class ContextualMemory:
    """Automatically surfaces relevant memories during conversation."""

    async def get_context_for_input(
        self,
        user_input: str,
        session_history: List[str]
    ) -> ContextualSurface:
        """
        Analyze user input and surface relevant memories.

        Returns memories that are:
        1. Semantically similar to current input
        2. Related to mentioned entities
        3. Related to detected project/domain
        4. Related to similar past struggles
        """

        # Extract entities from input
        entities = await self._extract_entities(user_input)

        # Get semantic matches
        semantic_matches = await self._semantic_search(user_input, limit=3)

        # Get entity-related memories
        entity_memories = []
        for entity in entities:
            memories = await self._get_entity_memories(entity)
            entity_memories.extend(memories)

        # Check for struggle similarity
        if await self._detect_struggle_signal(user_input):
            similar_struggles = await self._get_similar_struggles(user_input)
        else:
            similar_struggles = []

        # Score and rank all memories
        all_memories = semantic_matches + entity_memories + similar_struggles
        ranked = self._rank_by_relevance(all_memories, user_input)

        return ContextualSurface(
            primary_memory=ranked[0] if ranked else None,
            related_memories=ranked[1:4],
            entities_found=entities,
            struggle_pattern=similar_struggles[0] if similar_struggles else None
        )
```

---

## 7. Integration Points

### 7.1 Brain Dump Integration

```python
# In Tools/brain_dump/router.py

async def route_brain_dump(dump: ClassifiedBrainDump, ...) -> RoutingResult:
    """Route brain dump with memory capture."""

    # Existing routing logic...
    result = await _existing_routing(dump)

    # Add memory capture
    memory_service = get_memory_service()
    await memory_service.capture_brain_dump(
        content=dump.raw_text,
        classification=dump.classification,
        sentiment=dump.sentiment,
        source=dump.source,
        extracted_data={
            'task': dump.task,
            'commitment': dump.commitment,
            'idea': dump.idea,
            'note': dump.note
        }
    )

    return result
```

### 7.2 Journal Integration

```python
# In Tools/journal.py

def log(self, event_type: EventType, ...) -> int:
    """Log event with memory capture."""

    # Existing logging...
    entry_id = self._log_to_journal(...)

    # Capture to memory system
    if self._should_capture_to_memory(event_type):
        asyncio.create_task(
            self._capture_to_memory(event_type, source, title, data)
        )

    return entry_id
```

### 7.3 Conversation Integration

```python
# In conversation handler (Telegram bot, CLI, etc.)

async def handle_message(user_input: str, session_id: str):
    """Handle message with memory context."""

    memory_service = get_memory_service()

    # Get relevant context before responding
    context = await memory_service.get_context_for_input(
        user_input=user_input,
        session_history=get_session_history(session_id)
    )

    # Capture the conversation
    await memory_service.capture_conversation(
        content=user_input,
        session_id=session_id,
        context=context
    )

    # Include context in response generation
    response = await generate_response(user_input, context)

    return response
```

---

## 8. Privacy and Storage

### 8.1 Local-Only Storage

All memory data is stored locally:

```
State/
  +-- memory/
      +-- activities.db        # SQLite activities database
      +-- summaries.db         # SQLite summaries database
      +-- vectors/             # ChromaDB vector storage
          +-- activities/
          +-- conversations/
          +-- struggles/
          +-- values/
      +-- backups/             # Daily backups
```

### 8.2 Data Retention

```python
RETENTION_POLICY = {
    "activities": {
        "full_detail": 90,      # Keep full details for 90 days
        "summary_only": 365,    # Keep summaries for 1 year
        "embeddings": 365       # Keep embeddings for 1 year
    },
    "struggles": {
        "full_detail": 180,     # 6 months
        "patterns": "forever"   # Keep patterns indefinitely
    },
    "values": {
        "all": "forever"        # Never delete recognized values
    },
    "daily_summaries": {
        "all": "forever"        # Never delete summaries
    }
}
```

### 8.3 Export and Backup

```python
class MemoryBackup:
    """Backup and export memory data."""

    async def export_all(self, format: str = "json") -> Path:
        """Export all memory data."""
        pass

    async def backup_daily(self):
        """Create daily backup of memory databases."""
        pass

    async def restore(self, backup_path: Path):
        """Restore from backup."""
        pass
```

---

## 9. Performance Considerations

### 9.1 Embedding Strategy

- Use `text-embedding-3-small` for cost efficiency
- Batch embeddings for bulk operations
- Cache frequently accessed embeddings
- Lazy-load embeddings on demand

### 9.2 Query Optimization

- SQLite indexes on all temporal columns
- FTS5 for full-text search
- ChromaDB HNSW index for vector search
- Query result caching with TTL

### 9.3 Background Processing

- Async capture pipeline
- Daily summary generation runs overnight
- Pattern analysis runs weekly
- Embedding generation in background queue

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] SQLite schema for activities, struggles, values
- [ ] Basic activity capture from brain dumps
- [ ] ChromaDB collection setup
- [ ] `/memory today` command

### Phase 2: Detection (Week 3-4)
- [ ] Struggle detection pipeline
- [ ] Value recognition system
- [ ] Relationship tracking
- [ ] Sentiment analysis integration

### Phase 3: Temporal Intelligence (Week 5-6)
- [ ] Natural language query parser
- [ ] Date range resolution
- [ ] Pattern analysis
- [ ] `/memory search` and `/memory when` commands

### Phase 4: Context & Retrieval (Week 7-8)
- [ ] Contextual auto-surface
- [ ] Conversation integration
- [ ] Daily/weekly summary generation
- [ ] Full command suite

### Phase 5: Polish (Week 9-10)
- [ ] Performance optimization
- [ ] Backup system
- [ ] Documentation
- [ ] Testing and refinement

---

## Appendix A: Example Queries and Responses

### Query: "What did I do last Tuesday?"

```json
{
  "date": "2026-01-14",
  "day_of_week": "Tuesday",
  "summary": "Productive day focused on Memphis project",
  "activities": [
    {"time": "09:15", "type": "brain_dump", "title": "Planning Memphis API integration"},
    {"time": "10:30", "type": "task_complete", "title": "Reviewed Sarah's auth PR"},
    {"time": "14:00", "type": "calendar_event", "title": "Weekly sync with Mike"},
    {"time": "15:30", "type": "task_work", "title": "Working on Memphis dashboard"},
    {"time": "17:00", "type": "commitment_made", "title": "Promised Mike design by Friday"}
  ],
  "metrics": {
    "tasks_completed": 3,
    "focus_time_minutes": 180,
    "context_switches": 4
  },
  "health": {
    "readiness": 78,
    "sleep_score": 82
  }
}
```

### Query: "What was I struggling with yesterday?"

```json
{
  "date": "2026-01-18",
  "struggles_detected": 2,
  "struggles": [
    {
      "type": "frustration",
      "time": "11:30",
      "context": "API timeout issues",
      "trigger_text": "UGH this stupid API keeps timing out",
      "severity": "medium",
      "resolved": true
    },
    {
      "type": "decision_paralysis",
      "time": "15:45",
      "context": "Choosing between two design approaches",
      "trigger_text": "Can't decide if we should use REST or GraphQL",
      "severity": "low",
      "resolved": false
    }
  ],
  "pattern_note": "You've had similar API frustrations 3 times this month, typically around 11am"
}
```

### Query: "When did I last work on Memphis?"

```json
{
  "project": "Memphis",
  "last_activity": {
    "date": "2026-01-18",
    "time": "16:30",
    "type": "task_work",
    "title": "Memphis dashboard component styling",
    "duration_minutes": 45
  },
  "recent_history": [
    {"date": "2026-01-18", "activities": 3, "focus_minutes": 120},
    {"date": "2026-01-17", "activities": 5, "focus_minutes": 180},
    {"date": "2026-01-16", "activities": 2, "focus_minutes": 60}
  ],
  "total_time_this_week": "6h 15m",
  "related_commitments": [
    {"to": "Mike", "what": "Design ready by Friday", "due": "2026-01-24"}
  ]
}
```

---

## Appendix B: Struggle Detection Examples

| Input | Detected Struggle | Confidence |
|-------|-------------------|------------|
| "I've been staring at this code for an hour and it still doesn't make sense" | confusion | 0.92 |
| "WHY does this keep breaking?!?" | frustration | 0.95 |
| "Can't do anything until the client responds" | blocked | 0.88 |
| "I have like 50 things to do and no idea where to start" | overwhelmed | 0.91 |
| "I really should work on that report... maybe I'll check email first" | procrastination | 0.78 |
| "Should I use approach A or B? Both have pros and cons..." | decision_paralysis | 0.84 |
| "I'm exhausted, been at this all day" | energy_low | 0.90 |

---

## Appendix C: Value Detection Examples

| Input | Detected Value | Type |
|-------|----------------|------|
| "Family dinner is non-negotiable on Sundays" | Family Sunday dinner | boundary |
| "Mike is my most important client right now" | Mike (client) | relationship |
| "I really care about code quality" | Code quality | principle |
| "Getting the Memphis launch right is crucial" | Memphis launch | priority |
| "I promised I'd never miss another deadline with Sarah" | Deadline reliability with Sarah | commitment |

