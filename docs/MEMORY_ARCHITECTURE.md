# Thanos Memory Architecture

## Overview

Thanos implements a **hybrid memory architecture** combining three complementary storage systems to provide comprehensive memory capabilities:

1. **Neo4j AuraDB** - Knowledge graph for structured relationships
2. **ChromaDB** - Vector store for semantic search
3. **SQLite RelationshipStore** - Lightweight local graph for chain traversal

## Architecture Diagram

```
+--------------------------------------------------------------------+
|                        THANOS MEMORY SYSTEM                         |
+--------------------------------------------------------------------+
                                |
                                v
+--------------------------------------------------------------------+
|                            MemOS                                    |
|              (Memory Operating System - memos.py)                   |
|                                                                     |
|  Core Operations:                                                   |
|  - remember()  : Store to graph + vector                           |
|  - recall()    : Query both and merge results                      |
|  - relate()    : Create relationships                              |
|  - reflect()   : Find patterns across time                         |
+--------------------------------------------------------------------+
                |                   |                    |
                v                   v                    v
+------------------+    +------------------+    +------------------+
|   Neo4j AuraDB   |    |    ChromaDB      |    | RelationshipStore|
|   (Cloud Graph)  |    | (Vector Store)   |    |  (Local SQLite)  |
+------------------+    +------------------+    +------------------+
|                  |    |                  |    |                  |
| Knowledge Graph: |    | Collections:     |    | Tables:          |
| - Commitments    |    | - commitments    |    | - relationships  |
| - Decisions      |    | - decisions      |    | - pattern_cache  |
| - Patterns       |    | - patterns       |    | - insights       |
| - Entities       |    | - observations   |    |                  |
| - Sessions       |    | - conversations  |    | Features:        |
|                  |    | - entities       |    | - Chain traverse |
| Capabilities:    |    |                  |    | - Correlations   |
| - Graph traverse |    | Features:        |    | - Insight store  |
| - Entity context |    | - Semantic search|    | - Proactive surf |
| - Relationship   |    | - Embeddings     |    |                  |
|   queries        |    | - Batch ops      |    | Zero overhead    |
+------------------+    +------------------+    +------------------+
        |                       |                       |
        v                       v                       v
+--------------------------------------------------------------------+
|                    PERSISTENCE LAYER                                |
+--------------------------------------------------------------------+
|                                                                     |
|  State/                     ~/.claude/Memory/       State/          |
|  - TimeState.json          - vectors/             - relationships.db|
|  - OuraCache.json                                                   |
|  - operator_state.db                                                |
|                                                                     |
|  History/Sessions/          Config:                                 |
|  - 2026-01-*.md            - .env (API keys)                       |
|                                                                     |
+--------------------------------------------------------------------+
```

## Component Details

### 1. MemOS (Tools/memos.py)

The central memory orchestration layer that provides a unified interface to all storage backends.

**Core Methods:**
- `remember(content, type, domain, entities)` - Dual-write to graph + vector
- `recall(query, types, domain)` - Unified search across both stores
- `relate(from_id, relationship, to_id)` - Create explicit relationships
- `reflect(topic, timeframe, domain)` - Pattern discovery

**Status Properties:**
- `graph_available` - Neo4j connectivity
- `vector_available` - ChromaDB connectivity
- `relationships_available` - SQLite layer status
- `hybrid_mode` - True when ChromaDB + RelationshipStore active

### 2. Neo4j AuraDB (Tools/adapters/neo4j_adapter.py)

Cloud-hosted knowledge graph for structured relationship storage.

**Node Types:**
- `Commitment` - Promises with deadlines and priorities
- `Decision` - Choices with rationale and alternatives
- `Pattern` - Recurring behaviors and insights
- `Entity` - People, clients, projects
- `Session` - Conversation sessions

**Relationship Types:**
- `MADE_COMMITMENT`, `MADE_DECISION`
- `INVOLVES_ENTITY`, `RELATES_TO`
- `LED_TO`, `CAUSED_BY`

### 3. ChromaDB (Tools/adapters/chroma_adapter.py)

Vector database for semantic similarity search using OpenAI embeddings.

**Collections:**
| Collection | Purpose | Metadata Fields |
|------------|---------|-----------------|
| commitments | Promises/obligations | date, to_whom, deadline, status |
| decisions | Choices with rationale | date, domain, alternatives, confidence |
| patterns | Recurring behaviors | type, domain, frequency, strength |
| observations | Insights/reflections | domain, source, energy_level |
| conversations | Dialogue history | topic, domain, people, agent |
| entities | People/projects | name, type, domain, created_at |

**Features:**
- Batch embedding API (85% latency reduction for 10+ items)
- Semantic search with distance-to-similarity conversion
- Cross-collection search
- Automatic chunking for large batches

### 4. RelationshipStore (Tools/relationships.py)

Lightweight SQLite layer for graph-like operations without Neo4j overhead.

**Tables:**
- `relationships` - Source/target ID pairs with type and strength
- `pattern_cache` - Frequently accessed chains
- `insights` - Discovered patterns for proactive surfacing

**Relationship Types:**
```python
class RelationType(Enum):
    # Causal
    CAUSED = "caused"
    PREVENTED = "prevented"
    ENABLED = "enabled"

    # Temporal
    PRECEDED = "preceded"
    FOLLOWED = "followed"
    CONCURRENT = "concurrent"

    # Semantic
    RELATED_TO = "related_to"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"

    # Learning
    LEARNED_FROM = "learned_from"
    INVALIDATED_BY = "invalidated_by"
```

**Key Operations:**
- `link_memories(source, target, type, strength)` - Create relationship
- `traverse_chain(start, direction, max_depth)` - BFS chain traversal
- `find_paths(source, target)` - All paths between memories
- `get_correlation_candidates(ids)` - Cross-domain correlation discovery
- `store_insight()` / `get_unsurfaced_insights()` - Proactive surfacing

## Data Flow

### Remember Flow
```
User Statement
      |
      v
   MemOS.remember()
      |
      +---> Neo4j (if available)
      |         - Create node
      |         - Link to entities
      |
      +---> ChromaDB
      |         - Generate embedding
      |         - Store with metadata
      |
      +---> RelationshipStore
                - Link to previous memory
                - Update insight candidates
```

### Recall Flow
```
User Query
      |
      v
   MemOS.recall()
      |
      +---> Neo4j Graph Query
      |         - Filter by type/domain
      |         - Get related nodes
      |
      +---> ChromaDB Semantic Search
      |         - Generate query embedding
      |         - Find similar documents
      |
      v
   Merge & Deduplicate
      |
      v
   Return Combined Results
```

## Caching Strategy

### Oura Health Cache (State/OuraCache.json)
- **Purpose:** Reduce API calls for health data
- **TTL:** 24 hours per day's data
- **Retention:** 7 days rolling
- **Validation:** Data date must match query date

### TimeState (State/TimeState.json)
- **Purpose:** Track file modification times
- **Scope:** Project-wide file activity
- **Use:** Context awareness, activity patterns

### Session History (History/Sessions/*.md)
- **Purpose:** Conversation persistence
- **Format:** Markdown with structured metadata
- **Retention:** Indefinite, organized by date

## Test Results (2026-01-18)

| Component | Status | Details |
|-----------|--------|---------|
| MemOS Status | PASSED | Hybrid mode active |
| Neo4j | CONNECTED | AuraDB cloud instance |
| ChromaDB | CONNECTED | Server at localhost:8000 |
| RelationshipStore | CONNECTED | 4 relationships, 1 insight |
| Vector Operations | PASSED | Store, search, delete working |
| Chain Traversal | PASSED | Forward/backward BFS working |
| Insight Storage | PASSED | Proactive surfacing ready |
| Cross-Session | PASSED | SQLite persistence verified |
| Session History | VALID | 116 sessions tracked |

## Usage Examples

### Store a Memory
```python
from Tools.memos import get_memos

memos = get_memos()
result = await memos.remember(
    content="Decided to use hybrid memory architecture",
    memory_type="decision",
    domain="technical",
    entities=["Thanos", "MemOS"],
    metadata={"confidence": 0.9}
)
```

### Query Memories
```python
result = await memos.recall(
    query="memory architecture decisions",
    memory_types=["decision", "pattern"],
    domain="technical",
    limit=10
)
```

### Chain Traversal
```python
from Tools.relationships import get_relationship_store

store = get_relationship_store()
chain = store.traverse_chain(
    start_id="decision_123",
    direction="backward",
    max_depth=5
)
# Returns: What led to this decision?
```

### Store Insight
```python
insight_id = store.store_insight(
    insight_type="correlation",
    content="Poor sleep correlates with missed commitments",
    source_memories=["sleep_log_1", "commitment_missed_1"],
    confidence=0.85
)
```

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Single embed | ~200ms | OpenAI API call |
| Batch embed (10) | ~300ms | 85% faster than sequential |
| ChromaDB query | ~50ms | Local server |
| SQLite traverse | <10ms | Local file |
| Neo4j query | ~100ms | Cloud latency |

## Graceful Degradation

The system degrades gracefully when components are unavailable:

1. **Neo4j unavailable** → Vector-only mode (ChromaDB + SQLite)
2. **ChromaDB unavailable** → Graph-only mode (Neo4j only)
3. **OpenAI unavailable** → No semantic search, metadata-only queries
4. **All cloud down** → SQLite relationship store still functional
