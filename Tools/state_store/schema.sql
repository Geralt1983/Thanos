-- Thanos Unified State Store Schema
-- SQLite database schema for life operating system
-- Version: 1.0.0

-- ============================================================================
-- TASKS - Unified personal and work tasks
-- ============================================================================
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'queued', 'backlog', 'done', 'cancelled')),
    priority TEXT CHECK (priority IN ('critical', 'high', 'medium', 'low', NULL)),
    due_date DATE,
    due_time TIME,
    domain TEXT NOT NULL CHECK (domain IN ('work', 'personal')),
    context TEXT,  -- @home, @office, @errands, @phone, etc.
    energy_level TEXT CHECK (energy_level IN ('high', 'medium', 'low', NULL)),
    estimated_minutes INTEGER,
    actual_minutes INTEGER,
    source TEXT NOT NULL,  -- 'workos', 'telegram', 'brain_dump', 'manual', 'calendar', etc.
    source_id TEXT,  -- Original ID from source system
    parent_task_id TEXT REFERENCES tasks(id),
    project_id TEXT,
    tags JSON,  -- ["tag1", "tag2"]
    recurrence JSON,  -- {"frequency": "daily", "interval": 1, "until": "2026-12-31"}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSON  -- Flexible storage for source-specific data
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_domain ON tasks(domain);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_source ON tasks(source, source_id);
CREATE INDEX IF NOT EXISTS idx_tasks_context ON tasks(context);
CREATE INDEX IF NOT EXISTS idx_tasks_energy ON tasks(energy_level);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);

-- ============================================================================
-- CALENDAR_EVENTS - Synced calendar events
-- ============================================================================
CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    all_day BOOLEAN DEFAULT FALSE,
    calendar_id TEXT,
    calendar_name TEXT,
    event_type TEXT CHECK (event_type IN ('meeting', 'focus', 'personal', 'travel', 'reminder', 'other')),
    attendees JSON,  -- [{"email": "...", "name": "...", "status": "accepted"}]
    conferencing JSON,  -- {"type": "zoom", "url": "..."}
    reminders JSON,  -- [{"method": "popup", "minutes": 15}]
    recurrence_rule TEXT,  -- RRULE string
    source TEXT DEFAULT 'google',
    source_id TEXT,
    status TEXT DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'tentative', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_calendar_start ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_end ON calendar_events(end_time);
CREATE INDEX IF NOT EXISTS idx_calendar_source ON calendar_events(source, source_id);
CREATE INDEX IF NOT EXISTS idx_calendar_type ON calendar_events(event_type);

-- ============================================================================
-- COMMITMENTS - Promises to others (ADHD accountability)
-- ============================================================================
CREATE TABLE IF NOT EXISTS commitments (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    person TEXT NOT NULL,  -- Who you committed to
    person_email TEXT,
    commitment_type TEXT CHECK (commitment_type IN ('deliverable', 'meeting', 'followup', 'response', 'review', 'other')),
    due_date DATE,
    due_time TIME,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'broken', 'renegotiated', 'cancelled')),
    priority TEXT CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    context TEXT,  -- Where/how this was committed
    reminder_sent BOOLEAN DEFAULT FALSE,
    reminder_count INTEGER DEFAULT 0,
    last_reminder_at TIMESTAMP,
    related_task_id TEXT REFERENCES tasks(id),
    related_event_id TEXT REFERENCES calendar_events(id),
    source TEXT DEFAULT 'manual',
    source_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_commitments_person ON commitments(person);
CREATE INDEX IF NOT EXISTS idx_commitments_due ON commitments(due_date);
CREATE INDEX IF NOT EXISTS idx_commitments_status ON commitments(status);
CREATE INDEX IF NOT EXISTS idx_commitments_type ON commitments(commitment_type);

-- ============================================================================
-- FOCUS_AREAS - Current priorities and goals
-- ============================================================================
CREATE TABLE IF NOT EXISTS focus_areas (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    domain TEXT NOT NULL CHECK (domain IN ('work', 'personal', 'health', 'relationship', 'financial', 'growth')),
    timeframe TEXT CHECK (timeframe IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
    priority INTEGER DEFAULT 0,  -- For ordering
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    target_date DATE,
    success_criteria TEXT,
    key_results JSON,  -- OKR-style: [{"description": "...", "target": 100, "current": 50}]
    parent_focus_id TEXT REFERENCES focus_areas(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_focus_domain ON focus_areas(domain);
CREATE INDEX IF NOT EXISTS idx_focus_timeframe ON focus_areas(timeframe);
CREATE INDEX IF NOT EXISTS idx_focus_status ON focus_areas(status);
CREATE INDEX IF NOT EXISTS idx_focus_parent ON focus_areas(parent_focus_id);

-- ============================================================================
-- IDEAS - Someday/Maybe list
-- ============================================================================
CREATE TABLE IF NOT EXISTS ideas (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT CHECK (category IN ('project', 'feature', 'content', 'business', 'personal', 'learning', 'other')),
    domain TEXT CHECK (domain IN ('work', 'personal')),
    status TEXT DEFAULT 'captured' CHECK (status IN ('captured', 'researching', 'planned', 'rejected', 'converted')),
    potential_value TEXT CHECK (potential_value IN ('high', 'medium', 'low', 'unknown')),
    effort_estimate TEXT CHECK (effort_estimate IN ('trivial', 'small', 'medium', 'large', 'huge', 'unknown')),
    related_focus_id TEXT REFERENCES focus_areas(id),
    converted_to_task_id TEXT REFERENCES tasks(id),
    source TEXT DEFAULT 'brain_dump',
    tags JSON,
    links JSON,  -- [{"url": "...", "title": "..."}]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,  -- Last time this was reviewed in weekly review
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_ideas_category ON ideas(category);
CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
CREATE INDEX IF NOT EXISTS idx_ideas_domain ON ideas(domain);
CREATE INDEX IF NOT EXISTS idx_ideas_value ON ideas(potential_value);

-- ============================================================================
-- NOTES - Reference material and documentation
-- ============================================================================
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    content_type TEXT DEFAULT 'markdown' CHECK (content_type IN ('markdown', 'plain', 'html', 'json')),
    category TEXT CHECK (category IN ('reference', 'meeting', 'project', 'person', 'process', 'learning', 'other')),
    tags JSON,
    related_task_id TEXT REFERENCES tasks(id),
    related_event_id TEXT REFERENCES calendar_events(id),
    related_person TEXT,
    source TEXT DEFAULT 'manual',
    source_id TEXT,
    pinned BOOLEAN DEFAULT FALSE,
    archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category);
CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned);
CREATE INDEX IF NOT EXISTS idx_notes_archived ON notes(archived);
CREATE INDEX IF NOT EXISTS idx_notes_person ON notes(related_person);

-- Full-text search for notes content
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title, content, tags,
    content='notes',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, content, tags)
    VALUES (NEW.rowid, NEW.title, NEW.content, NEW.tags);
END;

CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
    VALUES ('delete', OLD.rowid, OLD.title, OLD.content, OLD.tags);
END;

CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
    VALUES ('delete', OLD.rowid, OLD.title, OLD.content, OLD.tags);
    INSERT INTO notes_fts(rowid, title, content, tags)
    VALUES (NEW.rowid, NEW.title, NEW.content, NEW.tags);
END;

-- ============================================================================
-- HEALTH_METRICS - Oura and other health data
-- ============================================================================
CREATE TABLE IF NOT EXISTS health_metrics (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    metric_type TEXT NOT NULL CHECK (metric_type IN (
        'sleep', 'readiness', 'activity', 'hrv', 'heart_rate',
        'spo2', 'stress', 'resilience', 'workout', 'weight', 'other'
    )),
    score INTEGER,  -- Primary score (0-100 for Oura metrics)
    value REAL,  -- Raw value (e.g., HRV in ms, weight in kg)
    unit TEXT,
    details JSON,  -- Full metric breakdown
    source TEXT DEFAULT 'oura',
    source_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP,
    metadata JSON,
    UNIQUE(date, metric_type, source)
);

CREATE INDEX IF NOT EXISTS idx_health_date ON health_metrics(date);
CREATE INDEX IF NOT EXISTS idx_health_type ON health_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_health_source ON health_metrics(source);
CREATE INDEX IF NOT EXISTS idx_health_score ON health_metrics(score);

-- ============================================================================
-- FINANCE - Accounts, balances, and transactions
-- ============================================================================
CREATE TABLE IF NOT EXISTS finance_accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    institution TEXT,
    account_type TEXT CHECK (account_type IN (
        'checking', 'savings', 'credit', 'investment', 'loan',
        'mortgage', 'retirement', 'crypto', 'other'
    )),
    currency TEXT DEFAULT 'USD',
    is_active BOOLEAN DEFAULT TRUE,
    source TEXT,  -- 'plaid', 'manual', etc.
    source_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_finance_accounts_type ON finance_accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_finance_accounts_active ON finance_accounts(is_active);

CREATE TABLE IF NOT EXISTS finance_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES finance_accounts(id),
    balance REAL NOT NULL,
    available_balance REAL,
    as_of_date DATE NOT NULL,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    UNIQUE(account_id, as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_finance_balances_account ON finance_balances(account_id);
CREATE INDEX IF NOT EXISTS idx_finance_balances_date ON finance_balances(as_of_date);

CREATE TABLE IF NOT EXISTS finance_transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES finance_accounts(id),
    date DATE NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    description TEXT,
    merchant TEXT,
    category TEXT,
    subcategory TEXT,
    transaction_type TEXT CHECK (transaction_type IN ('debit', 'credit', 'transfer')),
    is_pending BOOLEAN DEFAULT FALSE,
    is_recurring BOOLEAN DEFAULT FALSE,
    tags JSON,
    source TEXT,
    source_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_finance_trans_account ON finance_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_finance_trans_date ON finance_transactions(date);
CREATE INDEX IF NOT EXISTS idx_finance_trans_category ON finance_transactions(category);
CREATE INDEX IF NOT EXISTS idx_finance_trans_merchant ON finance_transactions(merchant);
CREATE INDEX IF NOT EXISTS idx_finance_trans_recurring ON finance_transactions(is_recurring);

-- ============================================================================
-- JOURNAL - Append-only event log for system events
-- ============================================================================
CREATE TABLE IF NOT EXISTS journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,  -- 'task_created', 'commitment_completed', 'focus_updated', etc.
    entity_type TEXT,  -- 'task', 'commitment', 'calendar_event', etc.
    entity_id TEXT,
    action TEXT NOT NULL,  -- 'create', 'update', 'delete', 'complete', 'sync', etc.
    actor TEXT DEFAULT 'system',  -- 'user', 'system', 'sync', 'telegram', etc.
    changes JSON,  -- {"field": {"old": "...", "new": "..."}}
    context JSON,  -- Additional context about the event
    session_id TEXT,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal(timestamp);
CREATE INDEX IF NOT EXISTS idx_journal_type ON journal(event_type);
CREATE INDEX IF NOT EXISTS idx_journal_entity ON journal(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_journal_action ON journal(action);
CREATE INDEX IF NOT EXISTS idx_journal_actor ON journal(actor);
CREATE INDEX IF NOT EXISTS idx_journal_session ON journal(session_id);

-- ============================================================================
-- BRAIN_DUMPS - Raw input archive
-- ============================================================================
CREATE TABLE IF NOT EXISTS brain_dumps (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'telegram', 'voice', 'cli', 'web', etc.
    source_context JSON,  -- {"chat_id": "...", "message_id": "..."}
    category TEXT CHECK (category IN ('thought', 'task', 'idea', 'worry', 'note', 'question', 'other')),
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    processing_result JSON,  -- {"converted_to": "task", "task_id": "..."}
    sentiment TEXT CHECK (sentiment IN ('positive', 'neutral', 'negative', 'mixed', NULL)),
    urgency TEXT CHECK (urgency IN ('immediate', 'today', 'soon', 'someday', NULL)),
    domain TEXT CHECK (domain IN ('work', 'personal', NULL)),
    tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_brain_dumps_source ON brain_dumps(source);
CREATE INDEX IF NOT EXISTS idx_brain_dumps_processed ON brain_dumps(processed);
CREATE INDEX IF NOT EXISTS idx_brain_dumps_category ON brain_dumps(category);
CREATE INDEX IF NOT EXISTS idx_brain_dumps_created ON brain_dumps(created_at);
CREATE INDEX IF NOT EXISTS idx_brain_dumps_urgency ON brain_dumps(urgency);

-- Full-text search for brain dumps
CREATE VIRTUAL TABLE IF NOT EXISTS brain_dumps_fts USING fts5(
    content, tags,
    content='brain_dumps',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS brain_dumps_ai AFTER INSERT ON brain_dumps BEGIN
    INSERT INTO brain_dumps_fts(rowid, content, tags)
    VALUES (NEW.rowid, NEW.content, NEW.tags);
END;

CREATE TRIGGER IF NOT EXISTS brain_dumps_ad AFTER DELETE ON brain_dumps BEGIN
    INSERT INTO brain_dumps_fts(brain_dumps_fts, rowid, content, tags)
    VALUES ('delete', OLD.rowid, OLD.content, OLD.tags);
END;

CREATE TRIGGER IF NOT EXISTS brain_dumps_au AFTER UPDATE ON brain_dumps BEGIN
    INSERT INTO brain_dumps_fts(brain_dumps_fts, rowid, content, tags)
    VALUES ('delete', OLD.rowid, OLD.content, OLD.tags);
    INSERT INTO brain_dumps_fts(rowid, content, tags)
    VALUES (NEW.rowid, NEW.content, NEW.tags);
END;

-- ============================================================================
-- HABITS - Habit tracking (from WorkOS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS habits (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    emoji TEXT,
    frequency TEXT DEFAULT 'daily' CHECK (frequency IN ('daily', 'weekly', 'weekdays')),
    time_of_day TEXT CHECK (time_of_day IN ('morning', 'evening', 'anytime')),
    target_count INTEGER DEFAULT 1,
    category TEXT CHECK (category IN ('health', 'productivity', 'relationship', 'personal')),
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    source TEXT DEFAULT 'workos',
    source_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_habits_active ON habits(is_active);
CREATE INDEX IF NOT EXISTS idx_habits_category ON habits(category);
CREATE INDEX IF NOT EXISTS idx_habits_frequency ON habits(frequency);

CREATE TABLE IF NOT EXISTS habit_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id TEXT NOT NULL REFERENCES habits(id),
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date DATE NOT NULL,
    count INTEGER DEFAULT 1,
    note TEXT,
    source TEXT DEFAULT 'manual',
    metadata JSON,
    UNIQUE(habit_id, date)
);

CREATE INDEX IF NOT EXISTS idx_habit_completions_habit ON habit_completions(habit_id);
CREATE INDEX IF NOT EXISTS idx_habit_completions_date ON habit_completions(date);

-- ============================================================================
-- RELATIONSHIPS - People and interactions (for CRM-like features)
-- ============================================================================
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company TEXT,
    role TEXT,
    relationship_type TEXT CHECK (relationship_type IN ('client', 'colleague', 'friend', 'family', 'acquaintance', 'other')),
    importance TEXT CHECK (importance IN ('high', 'medium', 'low')),
    last_contact_date DATE,
    next_contact_date DATE,
    contact_frequency TEXT CHECK (contact_frequency IN ('daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly')),
    notes TEXT,
    tags JSON,
    source TEXT DEFAULT 'manual',
    source_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name);
CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company);
CREATE INDEX IF NOT EXISTS idx_contacts_type ON contacts(relationship_type);
CREATE INDEX IF NOT EXISTS idx_contacts_next ON contacts(next_contact_date);

-- ============================================================================
-- SYNC_STATE - Track sync status with external systems
-- ============================================================================
CREATE TABLE IF NOT EXISTS sync_state (
    id TEXT PRIMARY KEY,  -- 'google_calendar', 'workos', 'oura', etc.
    last_sync_at TIMESTAMP,
    last_sync_status TEXT CHECK (last_sync_status IN ('success', 'partial', 'failed')),
    last_sync_error TEXT,
    sync_cursor TEXT,  -- For incremental sync
    items_synced INTEGER DEFAULT 0,
    next_sync_at TIMESTAMP,
    config JSON,  -- Sync-specific configuration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- EXISTING TABLES - Preserved from original schema
-- ============================================================================

-- State table for key-value storage (preserved from original)
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Turn logs for tracking API usage (preserved from original)
CREATE TABLE IF NOT EXISTS turn_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    latency_ms REAL DEFAULT 0.0,
    tool_call_count INTEGER DEFAULT 0,
    state_size INTEGER DEFAULT 0,
    prompt_bytes INTEGER DEFAULT 0,
    response_bytes INTEGER DEFAULT 0
);

-- Tool summaries for recent actions (preserved from original)
CREATE TABLE IF NOT EXISTS tool_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tool_name TEXT,
    summary TEXT,
    result_type TEXT
);

-- ============================================================================
-- VIEWS - Useful aggregated views
-- ============================================================================

-- Today's agenda: tasks and events for today
CREATE VIEW IF NOT EXISTS v_today_agenda AS
SELECT
    'task' as item_type,
    t.id,
    t.title,
    t.description,
    t.due_time as time,
    t.priority,
    t.domain,
    t.status,
    t.energy_level,
    t.context
FROM tasks t
WHERE t.due_date = DATE('now')
  AND t.status NOT IN ('done', 'cancelled')
UNION ALL
SELECT
    'event' as item_type,
    e.id,
    e.title,
    e.description,
    TIME(e.start_time) as time,
    NULL as priority,
    CASE e.event_type
        WHEN 'personal' THEN 'personal'
        ELSE 'work'
    END as domain,
    e.status,
    NULL as energy_level,
    e.location as context
FROM calendar_events e
WHERE DATE(e.start_time) = DATE('now')
  AND e.status != 'cancelled'
ORDER BY time;

-- Overdue items
CREATE VIEW IF NOT EXISTS v_overdue AS
SELECT
    'task' as item_type,
    id, title, due_date, priority, domain
FROM tasks
WHERE due_date < DATE('now')
  AND status NOT IN ('done', 'cancelled')
UNION ALL
SELECT
    'commitment' as item_type,
    id, title, due_date, priority, 'work' as domain
FROM commitments
WHERE due_date < DATE('now')
  AND status = 'active'
ORDER BY due_date;

-- Weekly health summary
CREATE VIEW IF NOT EXISTS v_weekly_health AS
SELECT
    date,
    MAX(CASE WHEN metric_type = 'sleep' THEN score END) as sleep_score,
    MAX(CASE WHEN metric_type = 'readiness' THEN score END) as readiness_score,
    MAX(CASE WHEN metric_type = 'activity' THEN score END) as activity_score,
    MAX(CASE WHEN metric_type = 'hrv' THEN value END) as hrv_avg,
    MAX(CASE WHEN metric_type = 'stress' THEN score END) as stress_score
FROM health_metrics
WHERE date >= DATE('now', '-7 days')
GROUP BY date
ORDER BY date DESC;

-- Active commitments by person
CREATE VIEW IF NOT EXISTS v_commitments_by_person AS
SELECT
    person,
    COUNT(*) as total_commitments,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'broken' THEN 1 ELSE 0 END) as broken,
    MIN(due_date) as next_due
FROM commitments
GROUP BY person
ORDER BY active DESC, next_due;

-- Focus progress
CREATE VIEW IF NOT EXISTS v_focus_progress AS
SELECT
    id,
    title,
    domain,
    timeframe,
    progress_percent,
    target_date,
    CASE
        WHEN target_date IS NOT NULL AND target_date < DATE('now') THEN 'overdue'
        WHEN progress_percent >= 100 THEN 'complete'
        WHEN progress_percent >= 75 THEN 'on_track'
        WHEN progress_percent >= 50 THEN 'at_risk'
        ELSE 'behind'
    END as health
FROM focus_areas
WHERE status = 'active'
ORDER BY timeframe, priority;

-- Net worth calculation
CREATE VIEW IF NOT EXISTS v_net_worth AS
SELECT
    fa.account_type,
    SUM(fb.balance) as total_balance,
    COUNT(DISTINCT fa.id) as account_count
FROM finance_accounts fa
JOIN finance_balances fb ON fa.id = fb.account_id
WHERE fa.is_active = TRUE
  AND fb.as_of_date = (
      SELECT MAX(as_of_date)
      FROM finance_balances fb2
      WHERE fb2.account_id = fb.account_id
  )
GROUP BY fa.account_type;

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'Initial unified state store schema');
