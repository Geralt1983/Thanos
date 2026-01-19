# Thanos Memory System - Comprehensive Documentation

## Overview

The Thanos Memory System is a **hybrid intelligent memory architecture** that combines multiple storage backends to provide semantic search, relationship tracking, and proactive insight surfacing. It is designed with ADHD-friendly principles: zero-friction capture, automatic classification, and intelligent retrieval.

```
                        +----------------------------------+
                        |          User Interactions       |
                        | /remember | /recall | /memory    |
                        +----------------+-----------------+
                                         |
                        +----------------v-----------------+
                        |              MemOS               |
                        |    Memory Operating System       |
                        |  (Tools/memos.py - Orchestrator) |
                        +----------------+-----------------+
                                         |
         +---------------+---------------+---------------+
         |               |               |               |
         v               v               v               v
+----------------+ +------------+ +--------------+ +-----------+
|   ChromaDB     | |   Neo4j    | |    SQLite    | |  Session  |
| Vector Store   | | Graph DB   | | Relationships| |  History  |
| (Semantic)     | | (Optional) | | (Local Graph)| |  (JSON)   |
+----------------+ +------------+ +--------------+ +-----------+
         |               |               |               |
         +---------------+---------------+---------------+
                                         |
                        +----------------v-----------------+
                        |         Storage Layer            |
                        | ~/.claude/Memory/vectors (Chroma)|
                        | Neo4j AuraDB (Cloud)             |
                        | State/relationships.db (SQLite)  |
                        | History/Sessions/*.json          |
                        +----------------------------------+
```

---

## Architecture Components

### 1. MemOS (Memory Operating System)

**Location:** `Tools/memos.py`

The central orchestrator that provides a unified interface to all memory backends. It abstracts the complexity of multiple storage systems behind four simple operations:

| Operation | Description | Use Case |
|-----------|-------------|----------|
| `remember()` | Store to graph + vector | "Remember this decision about X" |
| `recall()` | Query both stores, merge results | "What did I decide about X?" |
| `relate()` | Create relationships between memories | "Link this decision to that outcome" |
| `reflect()` | Find patterns across time | "What patterns do I have around Y?" |

**Initialization Modes:**

```
+------------------+     +------------------+     +------------------+
|   Full Hybrid    |     |  Vector-Only     |     |  Relationship    |
|  Neo4j + Chroma  |     |  ChromaDB Only   |     |  SQLite + Chroma |
|  + Relationships |     |  (Lightweight)   |     |  (Recommended)   |
+------------------+     +------------------+     +------------------+
         |                       |                       |
         v                       v                       v
     Enterprise              Quick Start            Production
     (Cloud DB)              (Local Dev)            (Self-Hosted)
```

### 2. ChromaDB Vector Store

**Location:** `Tools/adapters/chroma_adapter.py`
**Storage:** `~/.claude/Memory/vectors/` (default)

Provides semantic similarity search using OpenAI embeddings (text-embedding-3-small, 1536 dimensions).

**Collections:**

| Collection | Purpose | Metadata Fields |
|------------|---------|-----------------|
| `commitments` | Promises and obligations | date, to_whom, deadline, status, domain, priority |
| `decisions` | Choices with rationale | date, domain, alternatives_considered, confidence |
| `patterns` | Recurring behaviors | date, type, domain, frequency, strength |
| `observations` | Insights and learnings | date, domain, source, energy_level |
| `conversations` | Dialogue history | date, topic, domain, people, agent |
| `entities` | People, projects, organizations | name, type, domain, created_at |

### 3. Neo4j Knowledge Graph (Optional)

**Location:** `Tools/adapters/neo4j_adapter.py`
**Storage:** Neo4j AuraDB (cloud) or local instance

Provides relationship-based queries for "what led to this?" and "what resulted from this?" analysis.

**Node Types:**

```
+---------------+     +---------------+     +---------------+
|  Commitment   |     |   Decision    |     |    Pattern    |
| - content     |     | - content     |     | - description |
| - to_whom     |     | - rationale   |     | - type        |
| - deadline    |     | - alternatives|     | - frequency   |
| - status      |     | - confidence  |     | - strength    |
+-------+-------+     +-------+-------+     +-------+-------+
        |                     |                     |
        +----------+----------+----------+----------+
                   |                     |
           +-------v-------+     +-------v-------+
           |    Session    |     |    Entity     |
           | - agent       |     | - name        |
           | - summary     |     | - type        |
           | - mood        |     | - notes       |
           +---------------+     +---------------+
```

**Relationship Types:**

| Type | Description | Example |
|------|-------------|---------|
| `LEADS_TO` | Causal connection | Decision -> Commitment |
| `INVOLVES` | Entity participation | Commitment -> Entity |
| `LEARNED_FROM` | Pattern source | Pattern -> Session |
| `DURING` | Temporal context | Decision -> Session |
| `IMPACTS` | Effect relationship | Decision -> Commitment |
| `PRECEDED_BY` | Sequence | Session -> Session |
| `AT_ENERGY` | Energy state | Session -> EnergyState |

### 4. SQLite Relationship Store

**Location:** `Tools/relationships.py`
**Storage:** `State/relationships.db`

A lightweight, always-available relationship layer that complements ChromaDB when Neo4j is not configured. Enables graph-like queries without cloud dependencies.

**Relationship Types:**

```python
class RelationType(Enum):
    # Causal
    CAUSED = "caused"           # A caused B
    PREVENTED = "prevented"     # A prevented B
    ENABLED = "enabled"         # A made B possible

    # Temporal
    PRECEDED = "preceded"       # A happened before B
    FOLLOWED = "followed"       # A happened after B
    CONCURRENT = "concurrent"   # A and B happened together

    # Semantic
    RELATED_TO = "related_to"   # General relationship
    CONTRADICTS = "contradicts" # A conflicts with B
    SUPPORTS = "supports"       # A provides evidence for B
    ELABORATES = "elaborates"   # A adds detail to B

    # Domain
    BELONGS_TO = "belongs_to"   # A is part of B
    IMPACTS = "impacts"         # A affects B

    # Learning
    LEARNED_FROM = "learned_from"     # Pattern from experience
    APPLIED_TO = "applied_to"         # Pattern used in situation
    INVALIDATED_BY = "invalidated_by" # Pattern disproven
```

---

## Data Flow

### Memory Storage Flow

```
User Input: "/remember decision: Use FastAPI for the API server"
         |
         v
+-------------------+
| MemoryHandler     |
| (parse type,      |
|  extract entities,|
|  detect domain)   |
+--------+----------+
         |
         v
+-------------------+
|     MemOS         |
|   remember()      |
+--------+----------+
         |
    +----+----+----+
    |         |    |
    v         v    v
+-------+ +-----+ +------+
| Neo4j | |Chroma| |SQLite|
| (graph)| |(vec) | |(rel) |
+-------+ +-----+ +------+
    |         |    |
    v         v    v
+-------+ +-----+ +------+
|create | |embed | |link  |
|node   | |+store| |memory|
+-------+ +-----+ +------+
```

### Memory Retrieval Flow

```
User Query: "/recall FastAPI decision"
         |
         v
+-------------------+
| MemoryHandler     |
|   handle_recall() |
+--------+----------+
         |
         v
+-------------------+
|     MemOS         |
|    recall()       |
+--------+----------+
         |
    +----+----+----+
    |         |    |
    v         v    v
+-------+ +-------+ +--------+
| Neo4j | | Chroma| | Session|
| query | | search| | search |
+-------+ +-------+ +--------+
    |         |         |
    v         v         v
+-------+ +-------+ +--------+
|graph  | |vector | |history |
|results| |results| |matches |
+-------+ +-------+ +--------+
    |         |         |
    +----+----+----+----+
         |
         v
+-------------------+
|   MemoryResult    |
| (deduplicated,    |
|  scored, merged)  |
+-------------------+
```

---

## Database Schemas

### 1. ChromaDB Collections

Each collection stores documents with:

```json
{
  "id": "decision_20260118123456",
  "document": "Use FastAPI for the API server",
  "embedding": [0.1, -0.2, ...],  // 1536 dimensions
  "metadata": {
    "type": "decision",
    "domain": "work",
    "stored_at": "2026-01-18T12:34:56Z",
    "agent": "ops",
    "entities": "FastAPI,API"
  }
}
```

### 2. SQLite Relationships Database

**File:** `State/relationships.db`

#### relationships table

```sql
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,      -- ChromaDB ID or observation ID
    target_id TEXT NOT NULL,      -- Target memory ID
    rel_type TEXT NOT NULL,       -- RelationType enum value
    strength REAL DEFAULT 1.0,    -- 0.0-1.0 confidence
    metadata TEXT,                -- JSON additional context
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_id, target_id, rel_type)
);

-- Indexes for fast traversal
CREATE INDEX idx_source ON relationships(source_id);
CREATE INDEX idx_target ON relationships(target_id);
CREATE INDEX idx_rel_type ON relationships(rel_type);
CREATE INDEX idx_strength ON relationships(strength);
```

#### pattern_cache table

```sql
CREATE TABLE pattern_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_key TEXT UNIQUE NOT NULL,  -- Cache key
    memory_ids TEXT NOT NULL,          -- JSON array of memory IDs
    pattern_type TEXT NOT NULL,        -- Pattern category
    confidence REAL DEFAULT 0.5,       -- Pattern strength
    hit_count INTEGER DEFAULT 1,       -- Access frequency
    last_hit TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

#### insights table

```sql
CREATE TABLE insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_type TEXT NOT NULL,        -- pattern, correlation, warning, opportunity
    content TEXT NOT NULL,             -- Human-readable insight
    source_memories TEXT NOT NULL,     -- JSON array of supporting memory IDs
    confidence REAL DEFAULT 0.5,       -- 0.0-1.0 confidence
    surfaced BOOLEAN DEFAULT FALSE,    -- Has been shown to user?
    surfaced_at TEXT,
    created_at TEXT NOT NULL
);
```

### 3. Neo4j Graph Schema

**Node Labels:**
- Commitment, Decision, Pattern, Session, Entity, EnergyState

**Node Properties:** (see GRAPH_SCHEMA in `neo4j_adapter.py`)

**Relationship Types:**
- LEADS_TO, INVOLVES, LEARNED_FROM, DURING, IMPACTS, PRECEDED_BY, AT_ENERGY

---

## User Guide

### Memory Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/remember <content>` | Store a memory | `/remember Decided to use TypeScript` |
| `/remember decision: <text>` | Store as decision | `/remember decision: Use FastAPI` |
| `/remember pattern: <text>` | Store as pattern | `/remember pattern: Better focus after exercise` |
| `/remember commitment: <text>` | Store as commitment | `/remember commitment: Review @Sarah's PR by Friday` |
| `/recall <query>` | Search memories | `/recall FastAPI decisions` |
| `/recall --sessions <query>` | Search only sessions | `/recall --sessions project kickoff` |
| `/memory` | Show memory status | `/memory` |

### What Gets Automatically Captured

1. **Brain Dumps** - All input classified and archived
2. **Session History** - Full conversation logs
3. **Decisions** - When using decision: prefix
4. **Patterns** - When using pattern: prefix
5. **Commitments** - When using commitment: prefix
6. **Entity Mentions** - Words starting with @

### Entity Extraction

Mention entities with @ to automatically link them:

```
/remember commitment: Review @Sarah's PR for the @AuthService
```

This creates:
- A commitment node
- Entity nodes for Sarah and AuthService
- INVOLVES relationships between them

### Domain Detection

Domains are automatically detected based on current agent:

| Agent | Domain |
|-------|--------|
| ops | work |
| strategy | work |
| coach | personal |
| health | health |
| (default) | general |

### Querying Memories

**Hybrid Search** (default):
```
/recall authentication decisions
```
Returns results from both vector similarity and graph relationships.

**Session-Only Search**:
```
/recall --sessions client meeting
```
Returns only matches from session history files.

---

## Developer Guide

### Extending the Memory System

#### Adding a New Memory Type

1. **Add to ChromaDB collections** in `chroma_adapter.py`:

```python
VECTOR_SCHEMA = {
    "collections": {
        "my_new_type": {
            "description": "Description of the memory type",
            "metadata_fields": ["field1", "field2", ...]
        }
    }
}
```

2. **Add handling in MemOS** `remember()`:

```python
async def remember(self, content, memory_type="observation", ...):
    if memory_type == "my_new_type":
        if self._neo4j:
            result = await self._neo4j.call_tool(
                "my_custom_handler",
                {"content": content, ...}
            )
        # Store in vector
        ...
```

3. **Add command prefix** in `memory_handler.py`:

```python
type_prefixes = {
    "decision:": "decision",
    "pattern:": "pattern",
    "my_new_type:": "my_new_type",  # Add here
}
```

#### Adding a New Relationship Type

1. **Add to RelationType enum** in `relationships.py`:

```python
class RelationType(Enum):
    # Existing types...
    MY_NEW_RELATION = "my_new_relation"
```

2. **Add to mapping** in `memos.py`:

```python
rel_type_map = {
    "MY_NEW_RELATION": RelationType.MY_NEW_RELATION,
}
```

3. **Add to Neo4j** (if using):

Update `GRAPH_SCHEMA["relationships"]` in `neo4j_adapter.py`.

#### Integration Hooks

**Pre-storage hook:**
```python
# In your custom adapter
async def pre_store_hook(self, content, metadata):
    # Add automatic enrichment
    metadata["analyzed_at"] = datetime.utcnow().isoformat()
    return content, metadata
```

**Post-retrieval hook:**
```python
# In your custom handler
def post_recall_hook(self, results):
    # Add scoring, filtering, etc.
    return sorted(results, key=lambda x: x.get("relevance", 0), reverse=True)
```

### API Reference

#### MemOS Class

```python
from Tools.memos import MemOS, get_memos

# Initialize
memos = MemOS(
    neo4j_uri="neo4j+s://xxx.databases.neo4j.io",
    neo4j_username="neo4j",
    neo4j_password="xxx",
    chroma_path="~/.claude/Memory/vectors",
    openai_api_key="sk-xxx"
)

# Or use singleton
memos = get_memos()

# Store memory
result = await memos.remember(
    content="Use FastAPI for API server",
    memory_type="decision",
    domain="work",
    entities=["FastAPI", "API"],
    metadata={"rationale": "Performance and async support"}
)

# Recall memories
result = await memos.recall(
    query="API framework",
    memory_types=["decision", "pattern"],
    domain="work",
    limit=10,
    use_graph=True,
    use_vector=True
)

# Create relationships
result = await memos.relate(
    from_id="decision_abc123",
    relationship="LEADS_TO",
    to_id="commitment_xyz789",
    properties={"strength": 0.9}
)

# Find patterns
result = await memos.reflect(
    topic="productivity",
    timeframe_days=30,
    domain="work"
)

# Chain traversal (SQLite)
causes = memos.what_led_to("memory_id", max_depth=5)
effects = memos.what_resulted_from("memory_id", max_depth=5)
correlations = memos.find_correlations(["mem1", "mem2"])

# Insights
insight_id = memos.store_insight(
    insight_type="pattern",
    content="Exercise improves focus",
    source_memories=["obs_1", "obs_2"],
    confidence=0.8
)
pending = memos.get_pending_insights(min_confidence=0.5)
memos.mark_insight_shown(insight_id)
```

#### RelationshipStore Class

```python
from Tools.relationships import RelationshipStore, RelationType, get_relationship_store

# Initialize
store = get_relationship_store()

# Create relationship
rel = store.link_memories(
    source_id="memory_123",
    target_id="memory_456",
    rel_type=RelationType.CAUSED,
    strength=0.9,
    metadata={"context": "sprint planning"}
)

# Get related memories
related = store.get_related(
    memory_id="memory_123",
    rel_type=RelationType.CAUSED,
    direction="both",  # or "outgoing", "incoming"
    min_strength=0.5,
    limit=50
)

# Traverse chains
chain = store.traverse_chain(
    start_id="memory_456",
    direction="backward",  # find causes
    rel_types=[RelationType.CAUSED, RelationType.ENABLED],
    max_depth=10,
    min_strength=0.3
)

# Find paths between memories
paths = store.find_paths(
    source_id="memory_123",
    target_id="memory_789",
    max_depth=5
)

# Find correlation candidates
candidates = store.get_correlation_candidates(
    memory_ids=["poor_sleep", "missed_commitment"],
    min_shared_connections=2
)

# Get statistics
stats = store.get_stats()
# Returns: {
#   "total_relationships": 150,
#   "by_type": {"caused": 45, "related_to": 80, ...},
#   "unique_memories_linked": 200,
#   "pending_insights": 5,
#   "db_size_kb": 256
# }
```

#### ChromaAdapter Class

```python
from Tools.adapters.chroma_adapter import ChromaAdapter

adapter = ChromaAdapter(
    persist_directory="~/.claude/Memory/vectors",
    openai_api_key="sk-xxx"
)

# Store single memory
result = await adapter.call_tool("store_memory", {
    "content": "Meeting notes from client call",
    "collection": "conversations",
    "metadata": {"topic": "Q4 planning", "people": "Alice, Bob"}
})

# Batch storage (optimized)
result = await adapter.call_tool("store_batch", {
    "items": [
        {"content": "Note 1", "metadata": {"date": "2026-01-18"}},
        {"content": "Note 2", "metadata": {"date": "2026-01-18"}},
    ],
    "collection": "observations"
})

# Semantic search
result = await adapter.call_tool("semantic_search", {
    "query": "client planning meetings",
    "collection": "conversations",
    "limit": 10,
    "where": {"topic": "Q4 planning"}  # Optional filter
})

# Search all collections
result = await adapter.call_tool("search_all_collections", {
    "query": "important decisions",
    "limit": 5
})

# Get statistics
result = await adapter.call_tool("get_collection_stats", {
    "collection": "decisions"
})
```

---

## Privacy and Data Location

### Local Storage

| Data | Location | Format |
|------|----------|--------|
| Vector embeddings | `~/.claude/Memory/vectors/` | ChromaDB SQLite + HNSW index |
| Relationships | `State/relationships.db` | SQLite |
| Session history | `History/Sessions/*.json` | JSON files |
| Pattern cache | `State/relationships.db` | SQLite (pattern_cache table) |
| Insights | `State/relationships.db` | SQLite (insights table) |

### Cloud Storage (Optional)

| Service | Data Stored | Purpose |
|---------|-------------|---------|
| Neo4j AuraDB | Knowledge graph nodes & relationships | Relationship queries |
| OpenAI API | Embedding requests (not stored) | Vector generation |

### Data Isolation

- All local data stays in `~/.claude/` and `Thanos/State/`
- Session data is project-specific
- No automatic cloud sync unless Neo4j is configured
- Embeddings are generated via API but vectors stored locally

### Clearing Memory

```bash
# Clear vector store
rm -rf ~/.claude/Memory/vectors/

# Clear relationships
rm State/relationships.db

# Clear session history
rm -rf History/Sessions/

# Full reset
rm -rf ~/.claude/Memory/ State/*.db History/Sessions/
```

---

## Performance Considerations

### Embedding Generation

- **Model:** text-embedding-3-small (1536 dimensions)
- **Batch optimization:** 85% latency reduction for 10+ items
- **API limit:** 2048 items per request (auto-chunked)

### Search Performance

| Operation | Typical Latency |
|-----------|-----------------|
| Vector search (10 results) | 50-100ms |
| Relationship traversal (depth 5) | 10-50ms |
| Session history search | 100-500ms (file I/O) |
| Combined recall | 200-500ms |

### Index Strategy

**ChromaDB:**
- HNSW index for approximate nearest neighbor search
- Cosine similarity metric

**SQLite Relationships:**
- B-tree indexes on source_id, target_id, rel_type, strength
- Unique constraint for deduplication

### Recommended Usage

1. **Batch writes** when storing multiple memories
2. **Use filters** (domain, type) to narrow search scope
3. **Limit depth** in chain traversals (default: 5-10)
4. **Periodic cleanup** of old sessions and low-confidence insights

---

## Troubleshooting

### Common Issues

**"MemOS not available"**
- Check Neo4j credentials in `.env`
- Verify ChromaDB is installed: `pip install chromadb`
- Check OpenAI API key for embeddings

**No vector results**
- Ensure OpenAI API key is configured
- Check collection exists: `/memory` command
- Verify embedding generation: check for API errors in logs

**Relationship store errors**
- Check `State/` directory exists and is writable
- Verify SQLite is available (usually built-in)

**Slow queries**
- Reduce search limit
- Add domain/type filters
- Consider periodic index optimization

### Debug Mode

```python
# Enable verbose logging
import logging
logging.getLogger("chromadb").setLevel(logging.DEBUG)
logging.getLogger("Tools.memos").setLevel(logging.DEBUG)
```

---

## Summary

The Thanos Memory System provides:

| Feature | Benefit |
|---------|---------|
| Hybrid storage | Best of graph + vector search |
| Automatic classification | Zero-friction capture |
| Relationship tracking | "What led to this?" queries |
| Proactive insights | Surfaced patterns and correlations |
| Local-first design | Privacy with optional cloud |
| Extensible architecture | Easy to add new memory types |

The system is designed to be a "second brain" that remembers everything, finds connections you might miss, and proactively surfaces relevant insights when you need them.
