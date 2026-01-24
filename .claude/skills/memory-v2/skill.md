# Memory V2 Skill

**THIS SKILL IS MANDATORY.** Read before any memory operation. Do not reinvent patterns.

## Overview

Memory V2 is Jeremy's vectorized memory system using Neon pgvector + OpenAI embeddings. It stores facts, documents, and context with heat-based decay for ADHD-friendly surfacing.

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
```python
# Quick search via MCP tool
mcp__memory-v2__thanos_memory_search(query="trip plans", limit=5)

# Or via Python for more control
from Tools.memory_v2.service import MemoryService
ms = MemoryService()
results = ms.search("trip itinerary", limit=10)
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

Results are ranked by `effective_score = similarity * heat * importance`

```python
{
    "id": "uuid",
    "memory": "The content",
    "content": "Same as memory",
    "score": 0.85,        # Raw similarity
    "heat": 0.95,         # Activity level
    "importance": 1.0,    # Manual boost
    "effective_score": 0.81,  # Final ranking
    "source": "telegram",
    "client": "Orlando",
    "created_at": "2026-01-24T..."
}
```

## Adding Content

**For conversational content (facts, notes):**
```python
ms.add(
    content="Jeremy prefers morning meetings",
    metadata={"source": "manual", "type": "preference"}
)
```
Note: Uses mem0 fact extraction. May return empty for non-conversational content.

**For documents (PDFs, long content):**
```python
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

## ADHD Helpers

**What's hot (current focus):**
```python
mcp__memory-v2__thanos_memory_whats_hot(limit=10)
```

**What's cold (neglected/forgotten):**
```python
mcp__memory-v2__thanos_memory_whats_cold(limit=10, threshold=0.2)
```

**Pin critical memory (never decays):**
```python
mcp__memory-v2__thanos_memory_pin(memory_id="uuid")
```

## Environment

- **Database URL:** `THANOS_MEMORY_DATABASE_URL` in `.env`
- **Embeddings:** OpenAI text-embedding-3-small (1536 dims)
- **Fact extraction:** GPT-4o-mini via mem0

## Common Patterns

**Before answering contextual questions:**
```python
# Search for relevant context
results = ms.search(user_question, limit=5)
if results and results[0]['effective_score'] > 0.3:
    # Use this context in response
    context = results[0]['memory']
```

**Checking if content exists:**
```python
results = ms.search(f"filename:{filename}", limit=1)
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

## Family Context

Watch for these names (personal domain):
- **Corin** - daughter, EF Tours France/England trip
- **Chayah** - daughter, EF Tours France/England trip
- **Sullivan** - son (baby), sleep training

## Self-Improvement

**Update this skill when you learn:**
- New gotchas or type issues
- Better search patterns
- Missing payload fields
- Context that helps future queries
