-- Thanos Memory System Schema
-- SQLite database schema for intelligent memory storage
-- Version: 1.0.0

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
    struggle_type TEXT,     -- 'confusion', 'frustration', 'blocked', etc.

    -- Search optimization
    search_text TEXT,       -- Concatenated searchable text

    -- Metadata
    metadata JSON,
    embedding_id TEXT       -- Reference to ChromaDB embedding
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
CREATE INDEX IF NOT EXISTS idx_activities_sentiment ON activities(sentiment);

-- Full-text search for activities
CREATE VIRTUAL TABLE IF NOT EXISTS activities_fts USING fts5(
    title, description, content, search_text,
    content='activities',
    content_rowid='rowid'
);

-- FTS triggers for activities
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
    recurrence_count INTEGER DEFAULT 1,
    last_occurred TIMESTAMP,

    -- Metadata
    confidence REAL,
    source_activity_id TEXT REFERENCES activities(id),
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_struggles_date ON struggles(date);
CREATE INDEX IF NOT EXISTS idx_struggles_type ON struggles(struggle_type);
CREATE INDEX IF NOT EXISTS idx_struggles_project ON struggles(project);
CREATE INDEX IF NOT EXISTS idx_struggles_resolved ON struggles(resolved);
CREATE INDEX IF NOT EXISTS idx_struggles_time ON struggles(time_of_day);
CREATE INDEX IF NOT EXISTS idx_struggles_day ON struggles(day_of_week);

-- ============================================================================
-- USER_VALUES - What matters to the user
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
    emotional_weight REAL DEFAULT 0.5,
    explicit_importance BOOLEAN DEFAULT FALSE,

    -- Context
    domain TEXT CHECK (domain IN ('work', 'personal', 'health', 'relationship', 'financial', 'growth')),
    related_entity TEXT,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Evidence
    source_quotes JSON,

    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_values_type ON user_values(value_type);
CREATE INDEX IF NOT EXISTS idx_values_domain ON user_values(domain);
CREATE INDEX IF NOT EXISTS idx_values_active ON user_values(is_active);
CREATE INDEX IF NOT EXISTS idx_values_entity ON user_values(related_entity);

-- ============================================================================
-- MEMORY_RELATIONSHIPS - People and entities the user cares about
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_relationships (
    id TEXT PRIMARY KEY,

    -- Entity details
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'client', 'colleague', 'family', 'friend', 'stakeholder', 'vendor', 'other'
    )),

    -- Importance
    importance TEXT CHECK (importance IN ('critical', 'high', 'medium', 'low')) DEFAULT 'medium',
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
    key_facts JSON,
    commitments_to JSON,

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
-- DAILY_SUMMARIES - Aggregated daily activity data
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
    projects_touched JSON,

    -- Highlights
    key_accomplishments JSON,
    notable_struggles JSON,

    -- Health correlation
    oura_readiness INTEGER,
    oura_sleep_score INTEGER,
    oura_activity_score INTEGER,

    -- Summary
    generated_summary TEXT,
    user_reflection TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- WEEKLY_PATTERNS - Aggregated patterns across weeks
-- ============================================================================
CREATE TABLE IF NOT EXISTS weekly_patterns (
    id TEXT PRIMARY KEY,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,

    -- Activity patterns
    busiest_day INTEGER,
    quietest_day INTEGER,
    avg_tasks_per_day REAL,

    -- Time patterns
    typical_start_hour INTEGER,
    typical_end_hour INTEGER,
    peak_productivity_hours JSON,

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
-- MEMORY_SESSIONS - Track conversation sessions
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_sessions (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,

    -- Session metadata
    source TEXT NOT NULL,
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

-- ============================================================================
-- VIEWS - Useful aggregated views
-- ============================================================================

-- Today's activities
CREATE VIEW IF NOT EXISTS v_today_activities AS
SELECT *
FROM activities
WHERE date = DATE('now')
ORDER BY timestamp DESC;

-- Recent struggles
CREATE VIEW IF NOT EXISTS v_recent_struggles AS
SELECT *
FROM struggles
WHERE date >= DATE('now', '-7 days')
ORDER BY detected_at DESC;

-- Active values
CREATE VIEW IF NOT EXISTS v_active_values AS
SELECT *
FROM user_values
WHERE is_active = TRUE
ORDER BY emotional_weight DESC, mention_count DESC;

-- Important relationships
CREATE VIEW IF NOT EXISTS v_important_relationships AS
SELECT *
FROM memory_relationships
WHERE importance IN ('critical', 'high')
ORDER BY mention_count DESC;

-- Struggle patterns by time
CREATE VIEW IF NOT EXISTS v_struggle_time_patterns AS
SELECT
    time_of_day,
    struggle_type,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM struggles
WHERE date >= DATE('now', '-30 days')
GROUP BY time_of_day, struggle_type
ORDER BY count DESC;

-- Project activity summary
CREATE VIEW IF NOT EXISTS v_project_activity AS
SELECT
    project,
    COUNT(*) as activity_count,
    SUM(CASE WHEN activity_type = 'task_complete' THEN 1 ELSE 0 END) as tasks_completed,
    SUM(CASE WHEN struggle_detected THEN 1 ELSE 0 END) as struggles,
    MAX(timestamp) as last_activity
FROM activities
WHERE project IS NOT NULL
GROUP BY project
ORDER BY last_activity DESC;

-- ============================================================================
-- SCHEMA VERSION
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT OR IGNORE INTO memory_schema_version (version, description)
VALUES (1, 'Initial memory system schema');
