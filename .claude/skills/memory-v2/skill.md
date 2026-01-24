# Memory V2 Skill

## Overview

Memory V2 is Jeremy's vectorized memory system using Neon pgvector + OpenAI embeddings. It stores facts, documents, and context with heat-based decay for ADHD-friendly surfacing.

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
- `heat`: Activity score (1.0 = hot, 0.05 = cold)

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
