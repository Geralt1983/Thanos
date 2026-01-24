# ADR-012: Memory V2 - OpenAI + Neon + Heat Decay

**Date:** 2026-01-22
**Updated:** 2026-01-24
**Status:** Implemented (PRIMARY ARCHITECTURE)
**Supersedes:** ADR-001, ADR-005 (previous memory architecture)

## Decision

Migrate Thanos memory from the current fragmented architecture (local ChromaDB + SQLite) to a unified cloud-first system:

| Component | Old | New |
|-----------|-----|-----|
| Embeddings | ChromaDB default | **OpenAI text-embedding-3-small** |
| Vector Storage | ChromaDB (local) | **Neon pgvector (cloud)** |
| Fact Extraction | Manual / none | **mem0 (auto-extraction)** |
| Decay System | None | **Heat-based decay** |
| Local Storage | Multiple SQLite DBs | **None (all cloud)** |

## Implementation Status (as of 2026-01-24)

**Memory V2 is now the PRIMARY architecture.** All new memory operations route through V2 by default.

| Artifact | Status | Location |
|----------|--------|----------|
| MemoryService | ✅ Complete | `Tools/memory_v2/service.py` |
| HeatService | ✅ Complete | `Tools/memory_v2/heat.py` |
| Hot Memory Loader | ✅ Complete | `Tools/hot_memory_loader.py` |
| MCP Tools | ✅ Complete | `mcp-servers/memory-v2/` |
| Skill Documentation | ✅ Complete | `.claude/skills/memory-v2/skill.md` |
| Legacy Systems | ⚠️ Fallback Only | `Tools/memory/`, `memory/` |

### Current Stats (2026-01-24)

- **38,624 memories** in production
- **416 hot** (recent/active)
- **23,471 cold** (neglected, may need attention)
- **1 pinned** (skill documentation)
- **3 unique clients** tracked

---

## Architecture

### Tiered Memory System

```
┌─────────────────────────────────────────────────────────────────┐
│                     TIERED MEMORY ACCESS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  HOT LAYER (0ms latency)                                │   │
│  │  - Pre-loaded high-heat memories                        │   │
│  │  - Time-based refresh (hourly for long sessions)        │   │
│  │  - Access: hot_memory_loader.py                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  WARM LAYER (~0.5s latency)                             │   │
│  │  - Semantic search with LRU-cached embeddings           │   │
│  │  - On-demand queries                                    │   │
│  │  - Access: ms.search(query)                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  COLD LAYER (~1s latency)                               │   │
│  │  - Full corpus deep search                              │   │
│  │  - Uncached embeddings                                  │   │
│  │  - Access: Direct DB query                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

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
              ┌──────────────┴──────────────┐
              ▼                             ▼
       ┌───────────────┐         ┌────────────────────┐
       │  ms.add()     │         │  ms.add_document() │
       │  (with mem0)  │         │  (direct embed)    │
       └───────┬───────┘         └──────────┬─────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         MEM0                                    │
│  - Automatic fact extraction (conversational content)           │
│  - OR direct OpenAI embedding (documents/PDFs)                  │
│  - Deduplication via content hash                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│       OPENAI            │   │      NEON POSTGRES      │
│  (embeddings API)       │   │  (pgvector storage)     │
│                         │   │                         │
│  - text-embedding-3-sm  │   │  - thanos_memories      │
│  - 1536 dimensions      │   │  - payload JSON         │
│  - LRU cache (256)      │   │  - Full-text + vector   │
└─────────────────────────┘   └─────────────────────────┘
```

---

## Database Schema

### Actual Implementation (thanos_memories)

Memory V2 uses a single table with payload JSON for flexibility:

```sql
-- Core memories table (managed by mem0)
CREATE TABLE thanos_memories (
    id UUID PRIMARY KEY,
    vector VECTOR(1536),
    payload JSONB NOT NULL
);

-- Primary index for vector similarity
CREATE INDEX ON thanos_memories USING ivfflat (vector vector_cosine_ops);
```

### Payload Structure

All metadata is stored in the `payload` JSONB column:

```json
{
  "data": "The actual memory content...",
  "hash": "md5-hash-for-deduplication",
  "user_id": "jeremy",
  "created_at": "2026-01-24T08:00:00Z",

  "source": "telegram | hey_pocket | manual | brain_dump",
  "content_type": "text | pdf | voice",
  "filename": "document.pdf",
  "client": "Orlando | Raleigh | Memphis | Kentucky",
  "project": "VersaCare | ScottCare",
  "domain": "work | personal",
  "category": "financial | insurance | medical | travel",

  "heat": 1.0,
  "importance": 1.0,
  "pinned": false,
  "access_count": 0,
  "last_accessed": "2026-01-24T08:00:00Z"
}
```

---

## Heat Decay System

### Constants

```python
HEAT_CONFIG = {
    "initial_heat": 1.0,          # New memories start here
    "decay_rate": 0.97,           # 3% daily decay
    "access_boost": 0.15,         # Added when retrieved
    "mention_boost": 0.10,        # Added when entity mentioned
    "min_heat": 0.05,             # Floor - never forgotten
    "max_heat": 2.0,              # Ceiling (pinned memories)
    "decay_interval_hours": 24,
}
```

### Heat Thresholds

| Indicator | Heat Range | Meaning |
|-----------|------------|---------|
| 🔥 Hot | > 0.7 | Recent, actively used |
| • Warm | 0.3 - 0.7 | Moderate activity |
| ❄️ Cold | < 0.3 | Neglected, may need attention |

### Legacy Data Fallback

For memories without heat field, recency-based calculation:

| Age | Calculated Heat |
|-----|-----------------|
| Last 6 hours | 1.0 |
| Last 24 hours | 0.85 |
| Last 48 hours | 0.7 |
| Last 7 days | 0.5 |
| Older | 0.3 |

### Ranking Formula

```python
effective_score = similarity * heat * importance
```

Where:
- `similarity` = 1 - cosine_distance (0 to 1)
- `heat` = decay-adjusted activity score (0.05 to 2.0)
- `importance` = manual boost multiplier (default 1.0)

---

## Skill Enforcement (4-Layer Defense)

To ensure proper Memory V2 usage, a 4-layer defense-in-depth system is implemented:

### Layer 1: Self-Teaching Memory

The Memory V2 skill is stored as a **pinned memory** at heat 2.0. It surfaces in searches automatically.

```python
# Skill is pinned and always appears in search results
ms.search("MEMORY V2 SKILL READ BEFORE")  # Returns skill documentation
```

### Layer 2: Hard Gate Rule (CLAUDE.md)

```markdown
## Memory Protocol - HARD GATE

**STOP. Before ANY memory operation, you MUST do ONE of these:**

1. **Read the skill file:** `.claude/skills/memory-v2/skill.md`
2. **OR search for the skill:** `ms.search("MEMORY V2 SKILL READ BEFORE")`
```

### Layer 3: Session Start Context

`hooks/session-start/thanos-start.sh` includes a skill reminder:

```bash
📚 **Skills (read before operations):**
- memory-v2: Search "MEMORY V2 SKILL" or read .claude/skills/memory-v2/skill.md
```

### Layer 4: Code Gate Reminder

`MemoryService` logs a reminder on first use per session:

```python
def _ensure_skill_reminder(self):
    """Show skill reminder on first use per session."""
    if not MemoryService._skill_reminded:
        MemoryService._skill_reminded = True
        logger.info("📚 Memory V2: Skill patterns available. Search 'MEMORY V2 SKILL' for docs.")
```

---

## API Reference

### MemoryService

```python
from Tools.memory_v2.service import MemoryService

ms = MemoryService()

# Add conversational content (uses mem0 fact extraction)
ms.add(content="Meeting with Orlando about API integration",
       metadata={"source": "telegram", "client": "Orlando"})

# Add document (bypasses fact extraction, stores verbatim)
ms.add_document(content="[PDF: contract.pdf]\n\nDocument content...",
                metadata={"source": "telegram", "content_type": "pdf",
                          "filename": "contract.pdf", "client": "Orlando"})

# Semantic search (ranked by effective_score)
results = ms.search("What did Orlando say about the API?", limit=10)

# Get formatted context for prompts
context = ms.get_context_for_query("Orlando API discussion")

# ADHD helpers
hot = ms.whats_hot(limit=10)      # Current focus
cold = ms.whats_cold(limit=10)    # What am I neglecting?

# Pin critical memories
ms.pin(memory_id)
```

### HeatService

```python
from Tools.memory_v2.heat import HeatService

hs = HeatService()

# Apply daily decay (run via cron)
hs.apply_decay()

# Boost when memory accessed
hs.boost_on_access(memory_id)

# Boost related memories when entity mentioned
hs.boost_related("Orlando", boost_type="mention")

# Pin/unpin
hs.pin_memory(memory_id)
hs.unpin_memory(memory_id)

# Get memories by heat
hot = hs.get_hot_memories(limit=20)
cold = hs.get_cold_memories(threshold=0.2, limit=20)

# Statistics
stats = hs.get_heat_stats()
```

### Hot Memory Loader

For long-running sessions, use time-based refresh:

```python
from Tools.hot_memory_loader import load_hot_memories, load_if_stale

# Force load (session start)
context = load_hot_memories(limit=10)

# Time-based refresh (only loads if stale)
context = load_if_stale(hours=1, limit=10)  # Returns "" if fresh
```

### MCP Tools

```python
# Via MCP
mcp__memory-v2__thanos_memory_search(query="trip plans", limit=5)
mcp__memory-v2__thanos_memory_add(content="Note to remember", source="manual")
mcp__memory-v2__thanos_memory_context(query="Orlando project status")
mcp__memory-v2__thanos_memory_whats_hot(limit=10)
mcp__memory-v2__thanos_memory_whats_cold(limit=10, threshold=0.2)
mcp__memory-v2__thanos_memory_pin(memory_id="uuid")
```

---

## Configuration

### Environment Variables

```bash
# Neon (Postgres + pgvector)
THANOS_MEMORY_DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/thanos

# OpenAI (for mem0 LLM extraction AND embeddings)
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
        "provider": "openai",
        "config": {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "text-embedding-3-small"
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "url": os.getenv("THANOS_MEMORY_DATABASE_URL"),
            "collection_name": "thanos_memories"
        }
    },
    "version": "v1.1"
}
```

---

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
| `skill` | System skills | "Memory V2 usage patterns" |

---

## Performance Optimizations

### Query Embedding Cache

LRU cache (256 entries) for repeated queries:

```python
@lru_cache(maxsize=256)
def _cached_query_embedding(query: str) -> Tuple[float, ...]:
    """Cache query embeddings to reduce OpenAI API latency."""
```

### Persistent Database Connection

Connection reuse avoids ~300ms TCP handshake per query:

```python
def _get_connection(self):
    """Reuse persistent connection for speed."""
    if self._persistent_conn is None or self._persistent_conn.closed:
        self._persistent_conn = psycopg2.connect(self.database_url)
    return self._persistent_conn
```

### Fetch More for Re-Ranking

Search fetches 3x limit to ensure good results after heat re-ranking:

```python
cur.execute("... LIMIT %(limit)s", {"limit": limit * 3})
ranked = self._apply_heat_ranking(results)
return ranked[:limit]
```

---

## Family Context

Watch for these names (personal domain):
- **Corin** - daughter, EF Tours France/England trip
- **Chayah** - daughter, EF Tours France/England trip
- **Sullivan** - son (baby), sleep training

---

## Future (Phase 2)

- Neo4j Aura for relationship graph
- "What's blocking X?" queries via Cypher
- Entity extraction and linking
- Cross-session memory summarization

---

**Prepared by:** Thanos
**Initial Implementation:** 2026-01-22
**Heat System Overhaul:** 2026-01-24
