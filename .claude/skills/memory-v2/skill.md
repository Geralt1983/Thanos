# Memory V2 Skill

**THIS SKILL IS MANDATORY.** Read before any memory operation. Do not reinvent patterns.

## Overview

Memory V2 is Jeremy's vectorized memory system using Neon pgvector + OpenAI embeddings. It stores facts, documents, and context with heat-based decay for ADHD-friendly surfacing.

**🔥 IMPORTANT: Use `memory_router` for all memory operations.** It provides a unified API that routes to Memory V2 by default.

## ⚠️ MemOS Deprecation & Migration

**MemOS has been deprecated** (as of 2026-01-26). All data has been migrated from MemOS (Neo4j + ChromaDB) to Memory V2 (PostgreSQL + pgvector).

### Why the Change?

- **Single source of truth**: One memory system instead of two competing approaches
- **Better ADHD support**: Heat-based decay, whats_hot/cold helpers built-in
- **Simpler architecture**: Unified PostgreSQL storage vs multi-backend complexity
- **Better performance**: 50-60% faster queries, 95% storage reduction
- **Maintained codebase**: Active development vs optional dependencies

### Migration Guide: MemOS → memory_router

**DO THIS** (New unified API):
```python
from Tools.memory_router import add_memory, search_memory, get_context

# Add memory
add_memory("Meeting with Orlando client", metadata={"client": "Orlando"})

# Search memories
results = search_memory("Orlando project status", limit=10)

# Get formatted context for prompts
context = get_context("What's the Orlando project status?")

# ADHD helpers
from Tools.memory_router import whats_hot, whats_cold, pin_memory
hot = whats_hot(limit=10)       # What am I focused on?
cold = whats_cold(limit=10)     # What am I neglecting?
pin_memory(memory_id)            # Never decay this memory
```

**DON'T DO THIS** (Deprecated MemOS API):
```python
# ❌ DEPRECATED - Will show warnings
from Tools.memos import get_memos
memos = get_memos()
await memos.remember("content")
await memos.recall("query")
```

**Key API Changes:**

| MemOS (Old) | memory_router (New) | Notes |
|-------------|---------------------|-------|
| `memos.remember(content)` | `add_memory(content, metadata)` | Sync, no await needed |
| `memos.recall(query)` | `search_memory(query, limit, filters)` | Sync, no await needed |
| `memos.relate(from_id, to_id, type)` | Add `relationships` to metadata | Stored in RelationshipStore |
| `memos.reflect(query)` | `search_memory(query)` + analyze results | No separate reflection API |
| `memos.get_entity_context(name)` | `search_memory(name, filters={'entities': [name]})` | Entity filtering built-in |
| `memos.what_led_to(id)` | Use RelationshipStore directly | Graph traversal preserved |
| `memos.status` | `get_stats()` | System statistics |

**Preserved Features:**

Despite the migration, these MemOS features are still available:

1. **Relationship tracking**: Use `metadata={'relationships': [{'type': 'relates_to', 'target': 'mem_123'}]}`
2. **Entity filtering**: Use `search_memory(query, filters={'entities': ['Ashley']})`
3. **Graph relationships**: SQLite RelationshipStore still available via `Tools/relationships.py`
4. **Specialized memory types**: Use `metadata={'memory_type': 'commitment'}` or `{'memory_type': 'decision'}`

**What Was Lost:**

- Neo4j graph database (was optional, rarely used)
- Multiple ChromaDB collections (consolidated to single table)
- Async API (now sync for simplicity)
- `reflect()` method (use `search_memory()` + analysis instead)

**Convenience Aliases:**

memory_router provides familiar aliases for easy transition:

```python
from Tools.memory_router import remember, recall, get_memory

remember("content", metadata)  # Alias for add_memory()
recall("query", limit)          # Alias for search_memory()
get_memory("query")             # Alias for get_context()
```

## Tiered Memory Architecture

| Layer | Latency | Contents | How to Access |
|-------|---------|----------|---------------|
| **Hot** | 0ms | High-heat items, recently accessed | `ms.whats_hot()` or hot_memory_loader |
| **Warm** | ~0.5s | Semantic search with cached embeddings | `ms.search()` with LRU cache |
| **Cold** | ~1s | Full corpus, low-heat, deep search | Direct DB query or uncached search |

**Hot layer loading (for long sessions use time-based refresh):**
```python
from Tools.hot_memory_loader import load_hot_memories, load_if_stale

# Force load (session start or manual refresh)
context = load_hot_memories(limit=10)

# Only load if cache is stale (for long sessions)
# Returns empty string if loaded within last hour
context = load_if_stale(hours=1, limit=10)
```

**Quick heat summary:**
```bash
python Tools/hot_memory_loader.py --summary
# 📊 Memory: 38623 total | 🔥 415 hot | ❄️ 23471 cold | Avg heat: 0.29
```

## Heat Tracking

Heat is stored in payload as `heat` field (0.05 to 2.0):
- **New memories:** Start at 1.0
- **Accessed memories:** Boosted by +0.15
- **Mentioned client/project:** Boosted by +0.10
- **Daily decay:** heat *= 0.97 (run via cron)
- **Pinned memories:** Never decay, heat = 2.0

**Heat thresholds:**
- 🔥 Hot: > 0.7 (recent, actively used)
- • Warm: 0.3 - 0.7 (moderate activity)
- ❄️ Cold: < 0.3 (neglected, may need attention)

**Legacy data:** Memories without heat field use recency-based calculation:
- Last 6 hours → 1.0
- Last 24 hours → 0.85
- Last 48 hours → 0.7
- Last 7 days → 0.5
- Older → 0.3

## Deprecated: State Files

**DO NOT rely on these files for current state:**
- `State/CurrentFocus.md` - gets stale, use WorkOS + memory instead
- Other markdown state files - same issue

**Source of truth:**
- Tasks/habits → WorkOS MCP tools
- Context/history → Memory V2 search
- Health/energy → Oura MCP tools

## When to Search Memory

**ALWAYS search memory when:**
- User asks about something that sounds like stored content ("the trip", "that document", "what did I say about...")
- User mentions client names (Orlando, Raleigh, Memphis, Kentucky, VersaCare)
- User references past conversations, decisions, or context
- Questions seem to need historical context
- User explicitly asks to recall/remember something

**Search patterns:**

**✅ RECOMMENDED - Use memory_router (unified API):**
```python
from Tools.memory_router import search_memory, get_context

# Simple search
results = search_memory("trip plans", limit=5)

# Filtered search - within client context
results = search_memory("API integration", limit=10, filters={"client": "Orlando"})

# Filtered search - within project
results = search_memory("authentication", filters={"project": "VersaCare"})

# Filtered search - personal domain only
results = search_memory("family vacation", filters={"domain": "personal"})

# Get formatted context string for prompts
context = get_context("What's the Orlando project status?", limit=5)
```

**Alternative - MCP tools (for use in Claude Desktop):**
```python
# Quick search via MCP tool
mcp__memory-v2__thanos_memory_search(query="trip plans", limit=5)

# Filtered search - within client context
mcp__memory-v2__thanos_memory_search(query="API integration", client="Orlando")

# Filtered search - within project
mcp__memory-v2__thanos_memory_search(query="authentication", project="VersaCare")

# Filtered search - personal domain only
mcp__memory-v2__thanos_memory_search(query="family vacation", domain="personal")
```

**Direct Service Access (advanced use only):**
```python
from Tools.memory_v2.service import MemoryService
ms = MemoryService()
results = ms.search("trip itinerary", limit=10)
results = ms.search("Epic interface", client="Kentucky", project="VersaCare")
```

## Database Structure

**Table:** `thanos_memories`
**Columns:** `id`, `vector`, `payload`

**Payload fields:**
- `data`: The actual content
- `source`: Where it came from (telegram, hey_pocket, manual, brain_dump)
- `content_type`: Type (pdf, voice, text)
- `filename`: For documents
- `client`: Client association
- `project`: Project association
- `domain`: work or personal
- `category`: For personal docs (financial, insurance, medical, travel, etc.)
- `created_at`: Timestamp
- `heat`: Activity score (1.0 = hot, 0.05 = cold) - see Heat Tracking
- `importance`: Manual boost multiplier (default 1.0)
- `pinned`: Boolean, if true never decays
- `access_count`: Number of times accessed
- `last_accessed`: Last access timestamp

## Search Results

Results are ranked by **weighted addition** (not multiplication):
```
effective_score = (0.6 * similarity) + (0.3 * heat) + (0.1 * importance)
```

**Why weighted addition?** The old multiplicative formula (`similarity * heat * importance`) would bury semantically perfect matches if they were cold. A memory with similarity=0.95 but heat=0.1 scored only 0.095. Now it scores ~0.62, ensuring cold-but-relevant memories still surface.

```python
{
    "id": "uuid",
    "memory": "The content",
    "content": "Same as memory",
    "score": 0.85,        # Raw cosine distance (lower = better)
    "similarity": 0.15,   # 1 - score (higher = better)
    "heat": 0.95,         # Activity level (0.05-2.0)
    "importance": 1.0,    # Manual boost (0.5-2.0)
    "effective_score": 0.62,  # Final weighted ranking
    "source": "telegram",
    "client": "Orlando",
    "created_at": "2026-01-24T..."
}
```

## Adding Content

**✅ RECOMMENDED - Use memory_router (unified API):**

**For conversational content (facts, notes):**
```python
from Tools.memory_router import add_memory

add_memory(
    content="Jeremy prefers morning meetings",
    metadata={"source": "manual", "type": "preference", "client": "Orlando"}
)
```
Note: Uses mem0 fact extraction. May return empty for non-conversational content.

**For documents (PDFs, long content):**
```python
from Tools.memory_router import get_v2

# Get direct service access for add_document
ms = get_v2()
ms.add_document(
    content="[PDF: filename.pdf]\n\nDocument content here...",
    metadata={
        "source": "telegram",
        "content_type": "pdf",
        "filename": "filename.pdf",
        "domain": "work",
        "client": "Orlando"
    }
)
```
Note: Bypasses fact extraction, stores content directly with embeddings.

**Alternative - Direct Service Access (advanced use only):**
```python
from Tools.memory_v2.service import MemoryService

ms = MemoryService()

# For conversational content
ms.add(
    content="Jeremy prefers morning meetings",
    metadata={"source": "manual", "type": "preference"}
)

# For documents
ms.add_document(
    content="[PDF: filename.pdf]\n\nDocument content here...",
    metadata={
        "source": "telegram",
        "content_type": "pdf",
        "filename": "filename.pdf",
        "domain": "work",
        "client": "Orlando"
    }
)
```

## ADHD Helpers

**✅ RECOMMENDED - Use memory_router (unified API):**

```python
from Tools.memory_router import whats_hot, whats_cold, pin_memory, unpin_memory

# What's hot (current focus)?
hot = whats_hot(limit=10)

# What's cold (neglected/forgotten)?
cold = whats_cold(threshold=0.3, limit=10)

# Pin critical memory (never decays)
pin_memory(memory_id="uuid")

# Unpin memory (allow normal decay)
unpin_memory(memory_id="uuid")
```

**Alternative - MCP tools (for use in Claude Desktop):**

**What's hot (current focus):**
```python
mcp__memory-v2__thanos_memory_whats_hot(limit=10)
```

**What's cold (neglected/forgotten):**
```python
# Default: cold memories older than 7 days (truly neglected, not just new)
mcp__memory-v2__thanos_memory_whats_cold(limit=10, threshold=0.3)

# More aggressive: include memories neglected for 3+ days
mcp__memory-v2__thanos_memory_whats_cold(limit=10, threshold=0.3, min_age_days=3)
```
Note: `min_age_days` prevents surfacing brand-new memories that are "cold" simply because they're new, not because they're neglected.

**Pin critical memory (never decays):**
```python
mcp__memory-v2__thanos_memory_pin(memory_id="uuid")
```

**Boost context (prime memory system when switching context):**
```python
# Starting work on a specific client - boost all related memories
mcp__memory-v2__thanos_memory_boost_context(filter_key="client", filter_value="Orlando")

# Deep dive into a project
mcp__memory-v2__thanos_memory_boost_context(filter_key="project", filter_value="VersaCare", boost=0.2)

# Starting work day - boost all work memories
mcp__memory-v2__thanos_memory_boost_context(filter_key="domain", filter_value="work")

# Via Python (direct service access)
from Tools.memory_v2.heat import get_heat_service
hs = get_heat_service()
hs.boost_by_filter("client", "Orlando", boost=0.15)
```
Use this when switching contexts to surface relevant memories in subsequent searches.

## Environment

- **Database URL:** `THANOS_MEMORY_DATABASE_URL` in `.env`
- **Embeddings:** OpenAI text-embedding-3-small (1536 dims)
- **Fact extraction:** GPT-4o-mini via mem0

## Common Patterns

**Before answering contextual questions:**
```python
from Tools.memory_router import search_memory, get_context

# Option 1: Search and check scores
results = search_memory(user_question, limit=5)
if results and results[0]['effective_score'] > 0.3:
    # Use this context in response
    context = results[0]['memory']

# Option 2: Get formatted context string
context = get_context(user_question, limit=5)
# Returns formatted string with heat indicators, ready for prompt
```

**Checking if content exists:**
```python
from Tools.memory_router import search_memory

results = search_memory(f"filename:{filename}", limit=1)
exists = len(results) > 0 and filename in results[0].get('memory', '')
```

## Priority: Memory > State Files

**CRITICAL:** When checking current state (tasks, focus, what's done):
1. Search memory FIRST for recent updates
2. State files (CurrentFocus.md, etc.) get stale quickly
3. Memory has real-time task completions, state files may lag

Example: User says "we finished the passports" - memory will have it, CurrentFocus.md may still show "pending".

## Troubleshooting

**Empty search results:**
- Check query is meaningful (not too short)
- Try broader search terms
- Verify database connection

**add() returns empty:**
- Content may not have extractable facts
- Use `add_document()` for documents/long content

**Can't find recent content:**
- Heat decay may have lowered ranking
- Search with exact terms from content
- Check `source` filter if applicable

**created_at is datetime object:**
```python
# Wrong - will error
print(r['created_at'][:10])

# Right - format datetime
created = r.get('created_at', '')
if hasattr(created, 'strftime'):
    created = created.strftime('%Y-%m-%d')
print(created)
```

**Search results missing payload fields:**
Search returns: id, memory, content, score, heat, importance, effective_score, source, client, created_at

For full payload (filename, content_type, category, etc.), query DB directly:
```python
cur.execute("SELECT payload FROM thanos_memories WHERE id = %s", (memory_id,))
```

## Self-Improvement

**Update this skill when you learn:**
- New gotchas or type issues
- Better search patterns
- Missing payload fields
- Context that helps future queries
