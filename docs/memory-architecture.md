# Thanos Memory Architecture

*Last updated: 2026-02-01*

## Overview

Thanos uses a **dual-memory architecture** combining vector-based semantic search with graph-based relationship tracking. This mirrors how human memory works: fast pattern matching (vectors) plus structured knowledge of entities and their connections (graph).

```
┌─────────────────────────────────────────────────────────────────┐
│                      THANOS MEMORY SYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐       ┌─────────────────────────────┐ │
│  │   MEMORY V2         │       │   GRAPHITI                  │ │
│  │   (Vector Store)    │       │   (Knowledge Graph)         │ │
│  │                     │       │                             │ │
│  │  • Semantic search  │       │  • Entity extraction        │ │
│  │  • Heat ranking     │       │  • Relationship tracking    │ │
│  │  • Fact extraction  │       │  • Temporal edges           │ │
│  │  • pgvector/Neon    │       │  • Community detection      │ │
│  │                     │       │  • Neo4j                    │ │
│  └─────────────────────┘       └─────────────────────────────┘ │
│           ▲                               ▲                    │
│           │                               │                    │
│           └───────────┬───────────────────┘                    │
│                       │                                        │
│              ┌────────▼────────┐                               │
│              │   HEARTBEAT     │                               │
│              │   CAPTURE       │                               │
│              │                 │                               │
│              │  Extracts from  │                               │
│              │  conversations  │                               │
│              └─────────────────┘                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   FILE-BASED MEMORY                      │   │
│  │                                                          │   │
│  │  MEMORY.md          - Long-term curated knowledge        │   │
│  │  memory/YYYY-MM-DD  - Daily session logs                 │   │
│  │  HEARTBEAT.md       - Capture instructions               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: File-Based Memory (Immediate)

Human-readable markdown files for quick access and manual editing.

| File | Purpose | Loaded When |
|------|---------|-------------|
| `MEMORY.md` | Curated long-term knowledge | Main session only |
| `memory/YYYY-MM-DD.md` | Daily session logs | Every session (today + yesterday) |
| `memory/heartbeat-state.json` | Capture tracking | Heartbeats |

### When to Use
- Quick lookups during conversation
- Manual review and editing
- Session continuity (what happened today/yesterday)

---

## Layer 2: Memory V2 (Semantic Search)

Vector embeddings with heat-based ranking for relevance decay.

### Storage
- **Database:** Neon PostgreSQL with pgvector
- **Embeddings:** OpenAI text-embedding-3-small
- **MCP Server:** `mcp-servers/memory-v2-mcp/`

### Tools

| Tool | Purpose |
|------|---------|
| `memory_search` | Semantic similarity search |
| `memory_add` | Store new memory with embedding |
| `memory_context` | Get contextual memories for topic |
| `memory_whats_hot` | Recently accessed memories |
| `memory_whats_cold` | Stale memories (candidates for archival) |
| `memory_pin` | Pin important memories (prevent decay) |
| `memory_stats` | Usage statistics |

### Heat Ranking
Memories decay over time unless accessed. Heat score = f(recency, access_count, pinned).
- Hot memories surface faster in search
- Cold memories may be archived or refreshed
- Pinned memories never decay

### When to Use
- "What do I know about X?"
- Finding related context for a topic
- Surfacing forgotten but relevant memories

---

## Layer 3: Graphiti (Knowledge Graph)

Temporal knowledge graph for entities, relationships, and facts.

### Storage
- **Database:** Neo4j 5.26 (localhost:7474, bolt://localhost:7687)
- **MCP Server:** Graphiti on localhost:8000/sse
- **Credentials:** neo4j / graphiti_thanos_2026

### Current Graph State

| Node Type | Count | Description |
|-----------|-------|-------------|
| Entity | 19 | People, systems, concepts |
| Community | 16 | Clustered entity groups |
| Episodic | 3 | Captured episodes/events |
| Tool | 3 | Software tools |
| Procedure | 2 | Processes/workflows |
| Resource | 1 | Resources/assets |

### Tools

| Tool | Purpose |
|------|---------|
| `add_episode` | Ingest text, extract entities/relationships |
| `search_nodes` | Find entities by query |
| `search_facts` | Find relationships/facts |
| `get_episodes` | Retrieve stored episodes |
| `delete_episode` | Remove episode |
| `clear_graph` | Reset (dangerous) |

### What Gets Extracted
From each episode, Graphiti automatically extracts:
- **Entities:** People, projects, tools, concepts
- **Relationships:** How entities connect (USES, WORKS_ON, CREATED, etc.)
- **Facts:** Timestamped statements about entities
- **Communities:** Clusters of related entities

### When to Use
- "How is X related to Y?"
- "What do I know about this person?"
- Tracing project dependencies
- Understanding decision history

---

## Capture Strategy: Heartbeat-Based

Memory capture happens during OpenClaw heartbeats (every ~30 min when active).

### Process
1. **Check:** Has meaningful conversation occurred since last capture?
2. **Extract:** Key facts, decisions, entities, relationships
3. **Store:** Push episode to Graphiti via mcporter
4. **Log:** Update daily notes + heartbeat state

### Capture Command
```bash
mcporter call "http://localhost:8000/sse.add_episode" \
  name="<descriptive name>" \
  episode_body="<facts and context>" \
  source_description="OpenClaw main session" \
  --allow-http
```

### What to Capture
- Decisions made
- Technical learnings
- People/projects mentioned
- Plans and intentions
- Relationships discovered

### What to Skip
- Routine status checks
- Already-captured content
- Ephemeral chatter

---

## Services

### Graphiti MCP Server
- **URL:** http://localhost:8000/sse
- **Auto-start:** `~/Library/LaunchAgents/com.thanos.graphiti.plist`
- **Manual start:** `scripts/start-graphiti.sh`
- **Logs:** `/tmp/graphiti.log`, `/tmp/graphiti.err`

### Neo4j
- **Container:** `neo4j` (Docker)
- **UI:** http://localhost:7474
- **Bolt:** bolt://localhost:7687
- **Auth:** neo4j / graphiti_thanos_2026

### Control Commands
```bash
# Graphiti
launchctl start com.thanos.graphiti
launchctl stop com.thanos.graphiti

# Neo4j
docker start neo4j
docker stop neo4j
```

---

## Query Patterns

### "What do I know about X?"
1. `memory_search` → semantic matches
2. `search_nodes` → entity details
3. `search_facts` → relationships

### "How are X and Y connected?"
1. `search_facts` with both entities
2. Check shared communities

### "What happened on date X?"
1. Read `memory/YYYY-MM-DD.md`
2. `get_episodes` filtered by date

### "What's been on my mind lately?"
1. `memory_whats_hot` → frequently accessed
2. Recent episodes from Graphiti

---

## Future Considerations

1. ~~**Memory V2 activation**~~ - ✅ RESOLVED: Working as of 2026-02-01. Uses venv Python.
2. **Cross-layer sync** - Ensure file notes propagate to vector/graph
3. **Archival strategy** - What happens to cold memories?
4. **Mac Mini migration** - Move services to always-on machine
5. **Entity definitions** - Custom entity types for Thanos domain (Epic modules, family, etc.)
