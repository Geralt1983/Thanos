# Thanos Memory V2

**ADHD-optimized vector memory with intelligent heat decay, unified capture, and automatic deduplication.**

## Quick Start

```python
from Tools.memory_v2.service import get_memory_service
from Tools.memory_v2.unified_capture import capture
from Tools.memory_v2.heat import get_heat_service

# Add memory (auto-routes to Memory V2 + Graphiti)
capture("Jeremy decided to use Voyage embeddings for better search quality")

# Search with heat-boosted ranking
ms = get_memory_service()
results = ms.search("embeddings", client="Personal", limit=10)

# ADHD helpers
hs = get_heat_service()
hot = hs.whats_hot(limit=10)    # What's top of mind?
cold = hs.whats_cold(limit=10)  # What am I forgetting?
```

## Notes

- `USE_VOYAGE=true` uses `voyage-3` (1024 dims). Set `USE_VOYAGE=false` to use OpenAI `text-embedding-3-small` (1536 dims).
- mem0 is used for **fact extraction only** and always uses OpenAI embeddings internally.

## Architecture

```
Memory V2 Architecture
│
├── Embeddings (Voyage voyage-3, 1024 dims)
│   ├── Query embeddings (cached)
│   └── Document embeddings (on-demand)
│   └── Fallback to OpenAI text-embedding-3-small when USE_VOYAGE=false
│
├── Storage (Neon PostgreSQL + pgvector)
│   ├── Vector search (cosine similarity)
│   └── JSONB payload (metadata, heat, access tracking)
│
├── Unified Capture
│   ├── Auto-detect content type
│   ├── Route to Memory V2 (facts, patterns)
│   ├── Route to Graphiti (entities, relationships)
│   └── Route to BOTH (decisions, learnings)
│
├── Heat Decay (ADHD-optimized)
│   ├── Time-based decay (exponential)
│   ├── Access frequency boost (logarithmic)
│   └── Manual importance multiplier
│
└── Auto-Deduplication
    ├── Cosine similarity detection (>0.95)
    ├── Smart merge (keep recent, combine metadata)
    └── Periodic maintenance (weekly)
```

## Components

### 1. Memory Service (`service.py`)

Core memory operations with heat-based ranking.

```python
from Tools.memory_v2.service import get_memory_service

ms = get_memory_service()

# Add memory
ms.add("Content here", metadata={
    "client": "Orlando",
    "project": "ScottCare",
    "source": "telegram",
    "memory_type": "decision"
})

# Search with filters
results = ms.search(
    "API integration",
    client="Orlando",
    project="ScottCare",
    domain="work",
    limit=10
)

# Get context for prompts
context = ms.get_context_for_query("authentication", limit=5)

# ADHD helpers
hot = ms.whats_hot(limit=10)
cold = ms.whats_cold(threshold=0.3, min_age_days=7)

# Pin critical memories
ms.pin("memory_id")
```

### 2. Unified Capture (`unified_capture.py`)

Single entry point for Memory V2 + Graphiti.

```python
from Tools.memory_v2.unified_capture import capture, CaptureType

# Auto-detect type
capture("Jeremy works with Ashley on VersaCare project")

# Explicit type
capture(
    "API authentication uses OAuth 2.0",
    capture_type=CaptureType.FACT,
    metadata={"project": "VersaCare"}
)

# Batch capture
from Tools.memory_v2.unified_capture import get_unified_capture

uc = get_unified_capture()
results = uc.capture_batch([
    {
        "content": "Decision to migrate to Voyage embeddings",
        "type": "DECISION",
        "metadata": {"project": "Thanos"}
    },
    {
        "content": "Jeremy reports to Ashley",
        "type": "RELATIONSHIP"
    }
])
```

**Content Type Routing:**

| Type | Memory V2 | Graphiti | Example |
|------|-----------|----------|---------|
| DECISION | ✓ | ✓ | "Decided to use Voyage embeddings" |
| FACT | ✓ | - | "API key stored in .env" |
| PATTERN | ✓ | - | "User always prefers async APIs" |
| RELATIONSHIP | - | ✓ | "Jeremy works with Ashley" |
| LEARNING | ✓ | ✓ | "Voyage embeddings perform better" |
| NOTE | ✓ | - | "Remember to update docs" |

### 3. Heat Service (`heat.py`)

Time + access-based relevance scoring.

```python
from Tools.memory_v2.heat import get_heat_service

hs = get_heat_service()

# Apply decay (run daily via cron)
hs.apply_decay(use_advanced_formula=True)

# ADHD helpers
hot = hs.whats_hot(limit=20)
cold = hs.whats_cold(threshold=0.3, limit=20)

# Boost related memories (context switching)
hs.boost_by_filter("client", "Orlando", boost=0.15)
hs.boost_related("VersaCare", boost_type="mention")

# Pin critical memories
hs.pin_memory("memory_id")
hs.set_importance("memory_id", importance=2.0)

# Statistics
stats = hs.get_heat_stats()
report = hs.heat_report()
```

**Heat Formula:**

```
heat = base_score * decay_factor^days * log(access_count + 1)
```

Where:
- `base_score`: Initial heat (1.0) or manual importance (0.5-2.0)
- `decay_factor`: 0.97 (3% daily decay)
- `days`: Days since creation
- `access_count`: Number of times retrieved

**Example Heat Values:**

| Age | Accesses | Heat |
|-----|----------|------|
| 1 day | 0 | 0.97 |
| 1 day | 10 | 2.30 |
| 7 days | 0 | 0.81 |
| 7 days | 50 | 3.28 |
| 30 days | 0 | 0.40 |
| 30 days | 100 | 2.01 |

### 4. Deduplication (`deduplication.py`)

Automatic duplicate detection and merging.

```python
from Tools.memory_v2.deduplication import deduplicate_memories

# Dry run (no changes)
results = deduplicate_memories(
    similarity_threshold=0.95,
    dry_run=True
)

print(f"Found {results['duplicates_found']} duplicates")
print(f"Would merge: {results['duplicates_merged']}")

# Execute deduplication
results = deduplicate_memories(similarity_threshold=0.95)

# Process top N most similar
results = deduplicate_memories(limit=10)
```

**CLI Usage:**

```bash
# Dry run with details
python Tools/memory_v2/deduplication.py --dry-run --verbose

# Execute with custom threshold
python Tools/memory_v2/deduplication.py --threshold 0.97

# Weekly maintenance (cron)
0 3 * * 0 cd /path/to/Thanos && .venv/bin/python Tools/memory_v2/deduplication.py --threshold 0.95
```

**Merge Strategy:**

1. **Keep most recent** (by created_at)
2. **Combine metadata:**
   - Sum: `access_count`
   - Max: `heat`, `importance`
   - Union: `tags`, `entities`, `sources`
   - Append: `client`, `project` (if different)
3. **Track history** in `merged_from` array

### 5. Configuration (`config.py`)

```python
from Tools.memory_v2.config import (
    USE_VOYAGE,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    HEAT_CONFIG
)

print(f"Provider: {'Voyage' if USE_VOYAGE else 'OpenAI'}")
print(f"Model: {EMBEDDING_MODEL}")
print(f"Dimensions: {EMBEDDING_DIMENSIONS}")
```

**Environment Variables:**

```bash
# Required
THANOS_MEMORY_DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...  # For mem0 fact extraction

# Optional
VOYAGE_API_KEY=pa-...  # For Voyage embeddings
USE_VOYAGE=true        # Set false to use OpenAI
```

## Installation

```bash
cd Tools/memory_v2
pip install -r requirements.txt
```

**Requirements:**
- Python 3.9+
- PostgreSQL with pgvector extension
- Voyage API key (or OpenAI API key)

## MCP Integration

Memory V2 is exposed via MCP server:

```bash
# Start MCP server
cd mcp-servers/memory-v2-mcp
npm start

# Call via mcporter (stdio)
mcporter call --stdio "node mcp-servers/memory-v2-mcp/dist/index.js" \
  thanos_memory_add \
  content="Memory content" \
  source="openclaw" \
  memory_type="fact"

# Search
mcporter call --stdio "node mcp-servers/memory-v2-mcp/dist/index.js" \
  thanos_memory_search \
  query="search query" \
  limit=10
```

## Scheduled Maintenance

Add to crontab:

```bash
# Heat decay (daily at 3am)
0 3 * * * cd /path/to/Thanos && .venv/bin/python -c "from Tools.memory_v2.heat import apply_decay; apply_decay()"

# Deduplication (weekly Sunday 3am)
0 3 * * 0 cd /path/to/Thanos && .venv/bin/python Tools/memory_v2/deduplication.py --threshold 0.95
```

## Usage Patterns

### Morning Brief

```python
from Tools.memory_v2.heat import get_heat_service

hs = get_heat_service()

# What's top of mind?
hot = hs.whats_hot(limit=5)
for mem in hot:
    print(f"🔥 {mem['content'][:50]}... (heat: {mem['heat']:.2f})")

# What am I forgetting?
cold = hs.whats_cold(threshold=0.3, min_age_days=7, limit=5)
for mem in cold:
    print(f"❄️ {mem['content'][:50]}... (heat: {mem['heat']:.2f})")
```

### Context Switching

```python
from Tools.memory_v2.heat import get_heat_service
from Tools.memory_v2.service import get_memory_service

hs = get_heat_service()
ms = get_memory_service()

# Switching to Orlando project
hs.boost_by_filter("client", "Orlando", boost=0.20)

# Search becomes Orlando-focused
results = ms.search("API integration", limit=10)
# Orlando memories now rank higher!
```

### Heartbeat Capture

```python
from Tools.memory_v2.unified_capture import capture

# Capture recent conversation
recent_conversation = """
Jeremy discussed switching to Voyage embeddings with Ashley.
Decision made to use voyage-3 model for better semantic search.
Ashley manages the infrastructure team.
"""

# Auto-routes to Memory V2 (decision, facts) and Graphiti (relationship)
result = capture(
    recent_conversation,
    metadata={
        "source": "openclaw",
        "project": "Thanos",
        "entities": ["Jeremy", "Ashley"]
    }
)
```

## Testing

```bash
cd /Users/jeremy/Projects/Thanos

# Test embeddings
.venv/bin/python -c "
from Tools.memory_v2.service import _cached_query_embedding
emb = _cached_query_embedding('test')
print(f'✓ Embedding dims: {len(emb)}')
"

# Test capture
.venv/bin/python Tools/memory_v2/unified_capture.py "Test memory"

# Test deduplication
.venv/bin/python Tools/memory_v2/deduplication.py --dry-run

# Test heat
.venv/bin/python -c "from Tools.memory_v2.heat import apply_decay; apply_decay()"

# Integration test
.venv/bin/python -c "
from Tools.memory_v2.service import get_memory_service
ms = get_memory_service()
print('Stats:', ms.stats())
"
```

## Migration

See **[MIGRATION.md](./MIGRATION.md)** for:
- Voyage embeddings migration
- Backward compatibility
- Rollback procedures
- Performance considerations

## Troubleshooting

### Embeddings Not Working

```bash
# Check config
python Tools/memory_v2/config.py

# Verify API keys
echo $VOYAGE_API_KEY
echo $OPENAI_API_KEY

# Test embedding generation
python -c "
from Tools.memory_v2.service import _cached_query_embedding
try:
    emb = _cached_query_embedding('test')
    print(f'✓ Working: {len(emb)} dims')
except Exception as e:
    print(f'✗ Error: {e}')
"
```

### Deduplication Issues

```bash
# Always dry-run first!
python Tools/memory_v2/deduplication.py --dry-run --verbose

# Check for false positives
python -c "
from Tools.memory_v2.deduplication import get_deduplicator
dedup = get_deduplicator()
dups = dedup.find_duplicates(similarity_threshold=0.95, limit=5)
for m1, m2, sim in dups:
    print(f'Similarity: {sim:.3f}')
    print(f'  1: {m1[\"content\"][:50]}...')
    print(f'  2: {m2[\"content\"][:50]}...')
    print()
"
```

### Heat Decay Not Running

```bash
# Check cron
crontab -l | grep heat

# Manual run
python -c "from Tools.memory_v2.heat import apply_decay; apply_decay()"

# Check logs
tail -f logs/memory_v2.log
```

## Performance Tips

1. **Cache query embeddings**: Already implemented via `@lru_cache(maxsize=256)`
2. **Batch operations**: Use `batch_boost_on_access()` instead of individual boosts
3. **Search caching**: Search results cached for 5 minutes
4. **Deduplication limits**: Use `--limit` flag for large datasets
5. **Heat decay**: Run during low-traffic times (3am)

## File Structure

```
Tools/memory_v2/
├── __init__.py           # Package initialization
├── config.py             # Configuration and environment
├── service.py            # Core memory service
├── unified_capture.py    # Unified Memory V2 + Graphiti capture
├── heat.py               # Heat decay and ADHD helpers
├── deduplication.py      # Duplicate detection and merging
├── search_cache.py       # Search result caching
├── mcp_tools.py          # MCP server integration
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── MIGRATION.md          # Migration and rollback guide
```

## API Reference

See individual component files for detailed API documentation:
- **service.py**: Memory operations, search, ADHD helpers
- **unified_capture.py**: Capture routing, content type detection
- **heat.py**: Heat decay, boost operations, statistics
- **deduplication.py**: Duplicate detection, merging
- **config.py**: Configuration, environment variables

## Support

For issues or questions:
1. Check configuration: `python Tools/memory_v2/config.py`
2. Run tests: See Testing section above
3. Review logs: `tail -f logs/memory_v2.log`
4. See migration guide: `Tools/memory_v2/MIGRATION.md`
