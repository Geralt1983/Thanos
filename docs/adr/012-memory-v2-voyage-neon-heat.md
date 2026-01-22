# ADR-012: Memory V2 - Voyage + Neon + Heat Decay

**Date:** 2026-01-22
**Status:** Implementation In Progress
**Supersedes:** ADR-001, ADR-005 (previous memory architecture)

## Decision

Migrate Thanos memory from the current fragmented architecture (OpenAI embeddings + ChromaDB + local SQLite) to a unified cloud-first system:

| Component | Old | New |
|-----------|-----|-----|
| Embeddings | OpenAI text-embedding-3-small | **Voyage AI voyage-2** |
| Vector Storage | ChromaDB (local) | **Neon pgvector (cloud)** |
| Fact Extraction | Manual / none | **mem0 (auto-extraction)** |
| Decay System | None | **Heat-based decay** |
| Local Storage | Multiple SQLite DBs | **None (all cloud)** |

## Context

### Current Problems
1. **Fragmented architecture** - 3+ memory systems not integrated
2. **Local storage dependency** - Eating disk on 6GB machine
3. **No fact extraction** - Raw content stored, not distilled
4. **No decay** - All memories equal weight regardless of recency
5. **ChromaDB complexity** - Worker service, separate process

### Why These Choices

**Voyage AI:**
- Anthropic-recommended embeddings
- No local storage
- voyage-2: 1536 dimensions, excellent quality/cost
- Better semantic understanding than OpenAI for personal data

**Neon pgvector:**
- Serverless PostgreSQL - no local disk
- pgvector extension for similarity search
- SQL for metadata queries
- Free tier generous (500MB)

**mem0:**
- Automatic fact extraction from conversations
- Deduplication built-in
- Memory categorization
- Handles embedding + storage coordination

**Heat Decay:**
- Critical for ADHD workflow
- Recent/accessed memories surface naturally
- "What am I forgetting?" queries enabled
- Reduces cognitive load

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT SOURCES                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Hey Pocket    │  Telegram Bot   │   Manual / Claude Code      │
│   (meetings)    │  (quick dumps)  │   (direct input)            │
└────────┬────────┴────────┬────────┴──────────────┬──────────────┘
         │                 │                       │
         ▼                 ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     THANOS INGESTION                            │
│  - Transcript parsing                                           │
│  - Source tagging                                               │
│  - Timestamp normalization                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         MEM0                                    │
│  - Automatic fact extraction                                    │
│  - Deduplication                                                │
│  - Memory categorization                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│      VOYAGE AI          │   │      NEON POSTGRES      │
│  (embeddings API)       │   │  (pgvector storage)     │
│                         │   │                         │
│  - voyage-2 model       │   │  - memories table       │
│  - 1536 dimensions      │   │  - metadata + heat      │
│  - Remote, no local     │   │  - Full-text + vector   │
└─────────────────────────┘   └─────────────────────────┘
```

## Schema

### Neon/pgvector Tables

```sql
-- Core memories table (managed by mem0)
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    memory_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Extended metadata with heat decay
CREATE TABLE memory_metadata (
    memory_id UUID PRIMARY KEY REFERENCES memories(id),
    source VARCHAR(50),
    source_file VARCHAR(255),
    original_timestamp TIMESTAMP,
    client VARCHAR(100),
    project VARCHAR(100),
    tags TEXT[],

    -- Heat Decay System
    heat FLOAT DEFAULT 1.0,
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INT DEFAULT 0,
    importance FLOAT DEFAULT 1.0,
    pinned BOOLEAN DEFAULT FALSE,

    -- Future: Neo4j integration
    neo4j_node_id VARCHAR(255),

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_memories_user ON memories(user_id);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_metadata_heat ON memory_metadata(heat DESC);
CREATE INDEX idx_metadata_client ON memory_metadata(client);
CREATE INDEX idx_metadata_source ON memory_metadata(source);
CREATE INDEX idx_metadata_last_accessed ON memory_metadata(last_accessed);
```

## Heat Decay System

### Constants

```python
HEAT_CONFIG = {
    "initial_heat": 1.0,          # New memories start here
    "decay_rate": 0.97,           # 3% daily decay
    "access_boost": 0.15,         # Added when retrieved
    "mention_boost": 0.10,        # Added when entity mentioned
    "min_heat": 0.05,             # Floor - never forgotten
    "max_heat": 2.0,              # Ceiling
    "decay_interval_hours": 24,
}
```

### Formulas

**Decay (daily):**
```
new_heat = max(min_heat, current_heat * decay_rate)
```

**Access boost:**
```
new_heat = min(max_heat, current_heat + access_boost)
```

**Effective score (for ranking):**
```
effective_score = similarity * heat * importance
```

### Behavior

| Event | Heat Change |
|-------|-------------|
| Memory created | heat = 1.0 |
| Memory accessed | heat += 0.15 |
| Related entity mentioned | heat += 0.10 |
| Daily decay | heat *= 0.97 |
| Pinned | Never decays |

## Configuration

### Environment Variables

```bash
# Neon (Postgres + pgvector)
NEON_DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/thanos

# Voyage AI (embeddings)
VOYAGE_API_KEY=pa-xxxxxxxxxxxx

# OpenAI (for mem0 LLM extraction)
OPENAI_API_KEY=sk-xxxxxxxxxxxx
```

### mem0 Configuration

```python
MEM0_CONFIG = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY")
        }
    },
    "embedder": {
        "provider": "voyage",
        "config": {
            "api_key": os.getenv("VOYAGE_API_KEY"),
            "model": "voyage-2"
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "url": os.getenv("NEON_DATABASE_URL"),
            "collection_name": "thanos_memories"
        }
    },
    "version": "v1.1"
}
```

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `preference` | Likes/dislikes | "Prefers working late" |
| `personal` | Self facts | "Has ADHD, takes Vyvanse" |
| `professional` | Work facts | "Epic consultant, 13+ years" |
| `relationship` | People | "Ashley is partner" |
| `client` | Client info | "Orlando offered $98k" |
| `project` | Project details | "ScottCare blocked by routing" |
| `goal` | Objectives | "Targeting $500k+ annually" |
| `pattern` | Behaviors | "Task paralysis on Mondays" |
| `health` | Health info | "High-risk pregnancy" |

## API

### MemoryService

```python
class MemoryService:
    def add(content: str, metadata: dict) -> dict
    def search(query: str, limit: int = 10) -> list
    def get_context_for_query(query: str) -> str
    def whats_hot(limit: int = 10) -> list
    def whats_cold(threshold: float = 0.2, limit: int = 10) -> list
    def pin(memory_id: str) -> None
```

### HeatService

```python
class HeatService:
    def apply_decay() -> None  # Daily cron
    def boost_on_access(memory_id: str) -> None
    def boost_related(entity: str) -> None
    def pin_memory(memory_id: str) -> None
    def get_hot_memories(limit: int) -> list
    def get_cold_memories(threshold: float, limit: int) -> list
```

### MCP Tools

```python
memory_search(query: str, limit: int) -> list
memory_add(content: str, source: str, type: str) -> dict
memory_context(query: str) -> str
memory_whats_hot(limit: int) -> list
memory_whats_cold(threshold: float, limit: int) -> list
memory_pin(memory_id: str) -> dict
```

## Migration Plan

### Files to Remove
- `Tools/adapters/chroma_adapter.py`
- `Tools/intelligent_memory.py`
- `State/thanos_memory.db`
- ChromaDB dependencies from requirements.txt

### Files to Create
- `Tools/memory_v2/config.py` - mem0 + Voyage + Neon config
- `Tools/memory_v2/service.py` - MemoryService
- `Tools/memory_v2/heat.py` - HeatService
- `Tools/memory_v2/mcp_tools.py` - MCP tool definitions
- `scripts/setup_neon.sql` - Database schema
- `scripts/run_decay.py` - Daily decay cron

### Files to Update
- `requirements.txt` - Add mem0ai, remove chromadb
- `.env` - Add VOYAGE_API_KEY, NEON_DATABASE_URL

## Implementation Order

1. Create Neon database + schema
2. Implement MemoryService with mem0/Voyage/Neon
3. Implement HeatService
4. Update search to re-rank by heat
5. Create MCP tools
6. Remove old ChromaDB code
7. Add decay cron
8. Test end-to-end

## Future (Phase 2)

- Neo4j Aura for relationship graph
- "What's blocking X?" queries via Cypher
- Entity extraction and linking

---

**Prepared by:** Thanos
**Implementation Target:** 2026-01-22
