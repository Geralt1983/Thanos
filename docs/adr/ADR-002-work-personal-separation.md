# ADR-002: Work/Personal Data Separation Architecture

## Status

Proposed

## Date

2026-01-19

## Context

### Problem Statement

Currently ALL brain dumps flow to WorkOS (a work-focused task management system), mixing work tasks and personal concerns in the same system. This creates several issues:

1. **Domain pollution**: Personal worries about family, health, and finances clutter the work task list
2. **Inappropriate metrics**: Personal items get the same point-based value tracking as client work
3. **Lost context**: Thoughts, ideas, and observations go to WorkOS but are never mined for patterns
4. **Worry amplification**: Worries become tasks rather than being processed through journaling/reframing

### Current State

| Component | Purpose | Status |
|-----------|---------|--------|
| **WorkOS MCP** | Tasks, habits, energy, clients, brain dumps | Active - receives everything |
| **MemOS/ChromaDB** | Vector store for semantic search | Exists but underutilized |
| **Tools/accountability/processor.py** | Classification, domain detection, impact scoring | Built but bypassed |
| **Tools/brain_dump/router.py** | Routing logic for different destinations | Built but bypassed |
| **State/thanos_unified.db** | SQLite state store with tasks, commitments | Exists |

### What Already Exists

The `BrainDumpProcessor` in `Tools/accountability/processor.py` already provides:

- **Classification**: thought, project, task, worry, observation, idea
- **Domain Detection**: work vs personal with confidence scores (0-1)
- **Impact Scoring**: health, stress, financial, relationship dimensions (0-10 each)
- **AI Oversight**: confidence thresholds, needs_review flags, review reasons

The `BrainDumpRouter` in `Tools/brain_dump/router.py` provides:

- **Route-specific handlers**: thinking, venting, observation, note, idea, personal_task, work_task, commitment, mixed
- **State store integration**: Creates tasks, commitments, notes in local SQLite
- **WorkOS sync**: Only syncs work_task classification to WorkOS
- **Journal logging**: Records all brain dumps for audit trail

The `ChromaAdapter` in `Tools/adapters/chroma_adapter.py` provides:

- **Collections**: commitments, decisions, patterns, observations, conversations, entities, personal_memories
- **Semantic search**: Cross-collection search with similarity scoring
- **Batch operations**: Efficient embedding generation

## Decision

We will implement a **domain-separated data architecture** that routes brain dumps to appropriate storage backends based on classification and domain:

### Storage Mapping

| Classification | Domain | Primary Storage | Secondary Storage | Rationale |
|---------------|--------|-----------------|-------------------|-----------|
| **work_task** | work | WorkOS | Local SQLite (backup) | Work tasks need client tracking, point values, streak metrics |
| **personal_task** | personal | Local SQLite | - | Personal tasks need impact scoring, not work metrics |
| **commitment** | any | Local SQLite | ChromaDB | Commitments need stakeholder tracking and semantic search |
| **thought** | any | ChromaDB | - | Thoughts are pattern-mined, not actioned |
| **idea** | any | ChromaDB | Local SQLite (if actionable later) | Ideas need semantic discovery |
| **observation** | any | ChromaDB | - | Observations inform future decisions |
| **worry** | personal | Journal + ChromaDB | Converted task (after reframing) | Worries need processing, not just task creation |
| **habit** | any | Local SQLite | - | Habits are personal, not work - keep local |

### Data Flow Diagram

```
                              +------------------+
                              |   Brain Dump     |
                              |   (raw input)    |
                              +--------+---------+
                                       |
                                       v
                    +------------------+------------------+
                    |     BrainDumpClassifier (AI)       |
                    |  - Classification (9 types)        |
                    |  - Confidence scoring              |
                    |  - Entity extraction               |
                    +------------------+-----------------+
                                       |
                                       v
                    +------------------+------------------+
                    |     BrainDumpProcessor             |
                    |  - Domain detection (work/personal)|
                    |  - Impact scoring (personal)       |
                    |  - Work prioritization (work)      |
                    +------------------+-----------------+
                                       |
                    +------------------+------------------+
                    |                                     |
                    v                                     v
          +-----------------+                   +-----------------+
          | work_task       |                   | personal_task   |
          | commitment(work)|                   | commitment(pers)|
          +-----------------+                   +-----------------+
                    |                                     |
                    v                                     v
          +-----------------+                   +-----------------+
          |    WorkOS MCP   |                   | Local SQLite    |
          | - Tasks table   |                   | - tasks table   |
          | - Client assoc. |                   | - domain='pers' |
          | - Point values  |                   | - impact_score  |
          +-----------------+                   +-----------------+

                    +------------------+------------------+
                    |                                     |
                    v                                     v
          +-----------------+                   +-----------------+
          | thought         |                   | worry           |
          | idea            |                   +-----------------+
          | observation     |                             |
          +-----------------+                             v
                    |                           +-----------------+
                    v                           |   Journal       |
          +-----------------+                   | - Reframing     |
          |  ChromaDB       |                   | - Processing    |
          | - Embeddings    |<------------------+ - Pattern link  |
          | - Collections   |                   +-----------------+
          | - Semantic srch |                             |
          +-----------------+                             v
                                               +-----------------+
                                               | Converted Task  |
                                               | (if actionable) |
                                               +-----------------+
```

### Schema Extensions

#### Local SQLite (thanos_unified.db)

Add to existing `tasks` table:

```sql
ALTER TABLE tasks ADD COLUMN domain TEXT DEFAULT 'personal';
ALTER TABLE tasks ADD COLUMN impact_health REAL;
ALTER TABLE tasks ADD COLUMN impact_stress REAL;
ALTER TABLE tasks ADD COLUMN impact_financial REAL;
ALTER TABLE tasks ADD COLUMN impact_relationship REAL;
ALTER TABLE tasks ADD COLUMN impact_composite REAL;
ALTER TABLE tasks ADD COLUMN classification TEXT;
ALTER TABLE tasks ADD COLUMN classification_confidence REAL;
ALTER TABLE tasks ADD COLUMN brain_dump_id TEXT;

CREATE INDEX idx_tasks_domain ON tasks(domain);
CREATE INDEX idx_tasks_classification ON tasks(classification);
```

New `worries` table:

```sql
CREATE TABLE worries (
    id TEXT PRIMARY KEY,
    raw_content TEXT NOT NULL,
    reframed_content TEXT,
    converted_task_id TEXT,
    journal_entry_id INTEGER,
    chroma_memory_id TEXT,
    status TEXT DEFAULT 'unprocessed', -- unprocessed, processing, resolved, converted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (converted_task_id) REFERENCES tasks(id)
);
```

#### ChromaDB Collections

Use existing `personal_memories` collection with enhanced metadata:

```python
{
    "source": "brain_dump",
    "classification": "thought|idea|observation|worry",
    "timestamp": "ISO8601",
    "domains": ["health", "relationship", ...],  # from impact scoring
    "energy_level": "high|medium|low",
    "entity_count": 3,
    "linked_task_id": "uuid",  # if converted to task
    "linked_worry_id": "uuid"  # if this is a worry's memory
}
```

### Routing Rules

1. **Confidence Gate**: Items with `confidence < 0.6` go to review queue, not auto-routed
2. **Domain Ambiguity**: Items with both work AND personal indicators get `needs_review=True`
3. **Worry Processing**: All worries get journaled FIRST, then optionally converted
4. **Pattern Mining**: Thoughts/ideas/observations immediately stored in ChromaDB
5. **Work Sync**: Only `work_task` classification syncs to WorkOS

### API Changes

New unified entry point in `Tools/brain_dump/`:

```python
async def process_brain_dump(
    content: str,
    source: str = "direct",
    skip_classification: bool = False
) -> ProcessingResult:
    """
    Process brain dump through the full pipeline.

    Returns:
        ProcessingResult with:
        - classification
        - domain
        - impact_score (if personal)
        - destinations (where data was stored)
        - needs_review (if confidence low)
        - acknowledgment (user-facing message)
    """
```

## Consequences

### Positive

1. **Clean separation**: Work tasks stay in WorkOS with appropriate metrics; personal tasks stay local with impact scoring
2. **Pattern discovery**: Thoughts/ideas/observations flow to ChromaDB for semantic mining
3. **Worry management**: Worries get proper processing (journal + reframe) instead of becoming anxiety-inducing tasks
4. **Reduced noise**: WorkOS task list becomes focused on actual work
5. **ADHD-friendly**: Personal tasks can be prioritized by impact (health > stress > financial > relationship)

### Negative

1. **Increased complexity**: Multiple storage backends to maintain
2. **Sync challenges**: Need to handle offline/online states for WorkOS
3. **Migration effort**: Existing brain dumps in WorkOS need classification
4. **Query complexity**: Finding "all tasks" requires querying multiple sources

### Mitigation Strategies

| Risk | Mitigation |
|------|------------|
| Multiple backends | Unified query layer in StateStore |
| Sync issues | Local-first with async WorkOS sync |
| Migration | One-time script with manual review |
| Query complexity | Aggregated views in SQLite |

## Implementation Phases

### Phase 1: Enable Existing Router (Week 1)
- Wire `BrainDumpClassifier` and `BrainDumpRouter` into the main brain dump flow
- Keep WorkOS as fallback for work items
- Log all routing decisions for validation

### Phase 2: Local Personal Tasks (Week 2)
- Extend SQLite schema with impact scoring columns
- Implement personal task storage with impact scores
- Create CLI commands for personal task management

### Phase 3: ChromaDB Pattern Storage (Week 3)
- Wire thoughts/ideas/observations to ChromaDB
- Implement pattern mining queries
- Add "similar thoughts" retrieval

### Phase 4: Worry Processing (Week 4)
- Implement worry -> journal -> reframe flow
- Add worry-to-task conversion with tracking
- Build worry resolution analytics

### Phase 5: Unified Queries (Week 5)
- Build aggregated task views
- Add cross-store search
- Implement dashboard integration

## References

- `Tools/accountability/processor.py` - Existing classification and impact scoring
- `Tools/brain_dump/router.py` - Existing routing logic
- `Tools/brain_dump/classifier.py` - AI-powered classification
- `Tools/adapters/chroma_adapter.py` - Vector storage operations
- `Tools/unified_state.py` - SQLite state store
