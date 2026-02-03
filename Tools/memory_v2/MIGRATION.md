# Memory V2 Architecture Migration Guide

## Overview

This document describes the major architecture improvements implemented for Thanos Memory V2:

1. **Voyage AI Embeddings** - Switched from OpenAI to Voyage voyage-3
2. **Unified Capture Interface** - Single entry point for Memory V2 + Graphiti
3. **Advanced Heat Decay** - Time + access-based relevance scoring
4. **Auto-Deduplication** - Intelligent duplicate detection and merging

### Embedding Migration Decision (2026-02-02)

**Current State:**
- 38,000 memories stored with OpenAI embeddings (1536 dimensions)
- Voyage AI embeddings are 1024 dimensions

**Decision:** Stay on OpenAI embeddings until a re-embedding script is run.

**Rationale:**
- Dimension mismatch (1536 vs 1024)
- Risk of losing semantic context during direct conversion
- Performance overhead of full re-embedding
- Existing memories continue to work with current approach

**Future Action:**
Use the re-embedding script to create a Voyage-compatible table and
switch usage only after the re-embed completes.

## 1. Voyage AI Embeddings

### What Changed

- **Old**: OpenAI `text-embedding-3-small` (1536 dimensions)
- **New**: Voyage AI `voyage-3` (1024 dimensions)
- **Why**: Better semantic understanding, optimized for retrieval tasks

### Configuration

Set in `.env`:
```bash
VOYAGE_API_KEY=your_key_here
USE_VOYAGE=true  # Set to false to use OpenAI
```

### Backward Compatibility

The system automatically falls back to OpenAI if:
- `VOYAGE_API_KEY` is not set
- `USE_VOYAGE=false` in .env

### Vector Dimension Change

**Important**: Voyage embeddings are **1024 dimensions** vs OpenAI's **1536 dimensions**.

**Migration Options:**

1. **Stay on OpenAI (Current default)**:
   - Keeps 1536-dim embeddings in `thanos_memories`
   - Zero migration risk

2. **Re-embed into Voyage table** (Recommended if you want Voyage):
   - Create `thanos_memories_voyage` with vector(1024)
   - Re-embed content using Voyage
   - Switch reads/writes only after migration completes
   ```bash
   python Tools/memory_v2/migrate_embeddings.py --dry-run
   python Tools/memory_v2/migrate_embeddings.py --confirm
   ```

**Important:** pgvector columns require a fixed dimension. You cannot mix
1536-dim and 1024-dim vectors in the same table.

### Usage

No code changes required! The system automatically uses Voyage:

```python
from Tools.memory_v2.service import get_memory_service

ms = get_memory_service()
ms.add("Your content here")  # Uses Voyage embeddings
results = ms.search("query")  # Uses Voyage embeddings
```

## 2. Unified Capture Interface

### What Is It?

Single entry point that intelligently routes content to:
- **Memory V2** (vector store) for searchable facts
- **Graphiti** (knowledge graph) for entities and relationships
- **BOTH** for important content like decisions and learnings

### Routing Logic

| Content Type | Memory V2 | Graphiti |
|--------------|-----------|----------|
| Decisions    | ✓         | ✓        |
| Facts        | ✓         | -        |
| Patterns     | ✓         | -        |
| Relationships| -         | ✓        |
| Learnings    | ✓         | ✓        |
| Notes        | ✓         | -        |

### Usage

```python
from Tools.memory_v2.unified_capture import capture, CaptureType

# Automatic routing (detects type from content)
capture("Jeremy decided to switch to Voyage embeddings")

# Explicit type
capture(
    "API key stored in .env",
    capture_type=CaptureType.FACT,
    metadata={"project": "Thanos", "client": "Personal"}
)

# Batch capture
from Tools.memory_v2.unified_capture import get_unified_capture

uc = get_unified_capture()
uc.capture_batch([
    {"content": "Decision made", "type": "DECISION"},
    {"content": "Jeremy works with Ashley", "type": "RELATIONSHIP"}
])
```

### Integration with Heartbeat

Update `HEARTBEAT.md` to use unified capture:

```bash
# Old way (manual routing)
mcporter call "node mcp-servers/memory-v2-mcp/dist/index.js" thanos_memory_add ...
mcporter call "http://localhost:8000/sse.add_episode" ...

# New way (automatic routing)
python -c "from Tools.memory_v2.unified_capture import capture; capture('...')"
```

## 3. Advanced Heat Decay

### What Changed

**Old Formula**: Simple linear decay
```
heat *= 0.97  # Daily
```

**New Formula**: Time + access frequency
```
heat = base_score * decay_factor^days * log(access_count + 1)
```

### Why This Is Better

The new formula balances:
- **Time decay**: Exponential based on age
- **Access frequency**: Frequently accessed memories stay hot longer
- **Importance**: Manual boost for critical items

**Example**: A memory accessed 100 times stays relevant even if old.

### Configuration

Heat decay runs automatically via cron:

```bash
# Add to crontab
0 3 * * * cd /path/to/Thanos && .venv/bin/python -c "from Tools.memory_v2.heat import apply_decay; apply_decay()"
```

### Usage

```python
from Tools.memory_v2.heat import get_heat_service

hs = get_heat_service()

# Apply decay (run daily via cron)
hs.apply_decay(use_advanced_formula=True)

# Get hot memories (what's top of mind)
hot = hs.whats_hot(limit=10)

# Get cold memories (what am I forgetting?)
cold = hs.whats_cold(threshold=0.3, min_age_days=7)

# Pin critical memories (never decay)
hs.pin_memory("memory_id")
```

### Tracked Metrics

The system now tracks:
- `created_at`: Timestamp (for time-based decay)
- `access_count`: How many times retrieved (for popularity boost)
- `last_accessed`: Last retrieval time
- `heat`: Current relevance score (0.05 - 2.0)
- `importance`: Manual boost (0.5 - 2.0)
- `pinned`: Flag to prevent decay

All stored in `payload` JSONB column - no schema changes needed!

## 4. Auto-Deduplication

### What Is It?

Automatically finds and merges duplicate or highly similar memories based on vector similarity.

### How It Works

1. **Detection**: Finds memory pairs with cosine similarity > threshold (default 0.95)
2. **Merge Strategy**:
   - Keep most recent memory
   - Combine metadata (tags, sources, entities)
   - Sum access counts
   - Take maximum heat/importance
   - Track merge history

### Usage

```python
from Tools.memory_v2.deduplication import deduplicate_memories

# Dry run (see what would be merged)
results = deduplicate_memories(dry_run=True)
print(f"Found {results['duplicates_found']} duplicates")

# Execute deduplication
results = deduplicate_memories(similarity_threshold=0.95)
print(f"Merged {results['duplicates_merged']} duplicates")

# Process only top 10 most similar
results = deduplicate_memories(limit=10)
```

### CLI Usage

```bash
# Dry run
python Tools/memory_v2/deduplication.py --dry-run --verbose

# Execute with custom threshold
python Tools/memory_v2/deduplication.py --threshold 0.97

# Process limited pairs
python Tools/memory_v2/deduplication.py --limit 20
```

### Scheduled Maintenance

Add to cron for weekly cleanup:

```bash
# Every Sunday at 3am
0 3 * * 0 cd /path/to/Thanos && .venv/bin/python Tools/memory_v2/deduplication.py --threshold 0.95
```

### Merge History

Merged memories track their history:

```json
{
  "merged_from": [
    {
      "id": "uuid-of-removed-memory",
      "created_at": "2026-01-15T10:30:00",
      "merged_at": "2026-02-01T03:00:00"
    }
  ]
}
```

## Testing

### Test All Components

```bash
cd /Users/jeremy/Projects/Thanos

# Test Voyage embeddings
.venv/bin/python -c "
from Tools.memory_v2.service import _cached_query_embedding
embedding = _cached_query_embedding('test')
print(f'Embedding dimensions: {len(embedding)}')
"

# Test unified capture
.venv/bin/python Tools/memory_v2/unified_capture.py "Test capture"

# Test deduplication (dry run)
.venv/bin/python Tools/memory_v2/deduplication.py --dry-run

# Test heat decay
.venv/bin/python -c "from Tools.memory_v2.heat import apply_decay; apply_decay()"
```

### Integration Test

```bash
# Full workflow test
.venv/bin/python -c "
from Tools.memory_v2.service import get_memory_service
from Tools.memory_v2.unified_capture import capture
from Tools.memory_v2.heat import get_heat_service
from Tools.memory_v2.deduplication import deduplicate_memories

# Add memory via unified capture
result = capture('Test memory for integration test', source='test')
print('Capture:', result)

# Search
ms = get_memory_service()
results = ms.search('integration test')
print('Search results:', len(results))

# Check heat
hs = get_heat_service()
hot = hs.whats_hot(limit=5)
print('Hot memories:', len(hot))

# Dedup (dry run)
dedup = deduplicate_memories(dry_run=True)
print('Duplicates found:', dedup['duplicates_found'])
"
```

## Performance Considerations

### Voyage API Latency

- **Query embeddings**: Cached via `@lru_cache(maxsize=256)`
- **Document embeddings**: Generated on-demand for new memories
- **Batch operations**: Use unified capture batch methods

### Deduplication Cost

- **Computation**: O(n²) for full comparison (expensive on large datasets)
- **Recommendation**: Run weekly with `--limit` flag
- **Alternative**: Partition by date ranges or metadata filters

### Heat Decay

- **Computation**: O(n) linear scan (efficient)
- **Frequency**: Daily at 3am (low-traffic time)
- **Impact**: Minimal - single SQL UPDATE

## Rollback Plan

If you need to revert:

### Switch Back to OpenAI Embeddings

```bash
# In .env
USE_VOYAGE=false
```

System automatically falls back to OpenAI.

### Disable Unified Capture

Continue using direct Memory V2 / Graphiti calls:

```python
from Tools.memory_v2.service import get_memory_service
ms = get_memory_service()
ms.add("content", metadata={...})
```

### Disable Advanced Heat Decay

```python
from Tools.memory_v2.heat import get_heat_service
hs = get_heat_service()
hs.apply_decay(use_advanced_formula=False)  # Use simple formula
```

### Undo Deduplication

Merged memories are tracked in `merged_from` field. To restore:

1. Check merge history in `payload->merged_from`
2. Manual restoration if needed (not automated)
3. **Prevention**: Always use `--dry-run` first!

## Monitoring

### Key Metrics

```python
from Tools.memory_v2.service import get_memory_service
from Tools.memory_v2.heat import get_heat_service

ms = get_memory_service()
hs = get_heat_service()

# Memory stats
stats = ms.stats()
print(f"Total memories: {stats['total']}")
print(f"Unique clients: {stats['unique_clients']}")

# Heat distribution
heat_stats = hs.get_heat_stats()
print(f"Average heat: {heat_stats['avg_heat']}")
print(f"Hot memories: {heat_stats['hot_count']}")
print(f"Cold memories: {heat_stats['cold_count']}")
```

### Health Checks

```bash
# Embedding provider check
python Tools/memory_v2/config.py

# Service health
python -c "from Tools.memory_v2.service import get_memory_service; ms = get_memory_service(); print('✓ Memory V2 healthy')"

# Heat service
python -c "from Tools.memory_v2.heat import get_heat_service; hs = get_heat_service(); print('✓ Heat service healthy')"
```

## Support

For issues or questions:
1. Check logs: `tail -f logs/memory_v2.log`
2. Test components individually (see Testing section)
3. Verify configuration: `python Tools/memory_v2/config.py`

## Summary

✅ **Voyage embeddings**: Better semantic search (1024 dims)  
✅ **Unified capture**: Automatic Memory V2 + Graphiti routing  
✅ **Advanced heat decay**: Time + access frequency formula  
✅ **Auto-deduplication**: Intelligent duplicate merging  

All changes are **backward compatible** with optional feature flags!
