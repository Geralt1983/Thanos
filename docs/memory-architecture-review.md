# Thanos Memory Architecture Review

## 1. Memory V2 (Vector Store)

### Location
- Primary directory: `Tools/memory_v2/`
- Key components found in MEMORY.md and HEARTBEAT.md

### Embedding Generation
- **Provider:** Voyage AI
- **Purpose:** Semantic search and content vectorization
- **Implementation:** Not fully detailed in current documentation

### Vector Storage
- **Backend:** Neon PostgreSQL with pgvector extension
- **Connection:** Configured for local PostgreSQL instance
- **Key Interface:** `mcp-servers/memory-v2-mcp/` with stdio communication

### Heat Decay Mechanism
- **Not Explicitly Defined:** Current implementation lacks a clear heat decay strategy
- **Potential Improvement:** Implement time-based relevance scoring
- **Recommendation:** Add decay factor to reduce importance of older memories over time

### MCP (Message Control Protocol) Tools Interface
- **Communication:** Stdio-based communication
- **Example Command:** 
  ```bash
  mcporter call --stdio "node mcp-servers/memory-v2-mcp/dist/index.js" \
    thanos_memory_add \
    content="<memory content>" \
    source="openclaw" \
    memory_type="<fact|decision|pattern|note>"
  ```
- **Memory Types Supported:**
  - Fact
  - Decision
  - Pattern
  - Note

## 2. Graphiti (Knowledge Graph)

### Episode Capture
- **Trigger:** Heartbeat-based capture
- **Endpoint:** `http://localhost:8000/sse.add_episode`
- **Capture Strategy:** 
  ```bash
  mcporter call "http://localhost:8000/sse.add_episode" \
    name="<descriptive name>" \
    episode_body="<facts and context>" \
    source_description="OpenClaw main session"
  ```

### Entity Extraction
- **Process:** Automatic during heartbeat
- **Sources:** Conversation context, meaningful interactions
- **Skips:** Routine status checks, ephemeral chatter

### Relationship Mapping
- **Storage:** Neo4j Graph Database
- **Credentials:** 
  - User: neo4j
  - Password: graphiti_thanos_2026
  - Local UI: http://localhost:7474

### Storage Architecture
- **Database:** Neo4j
- **Startup Script:** `scripts/start-graphiti.sh`
- **Recommended Access:** Via MCP server at `http://localhost:8000/sse`

## 3. File-based Memory

### MEMORY.md Structure
- Long-term, curated memory
- Contains technical lessons, infrastructure notes, credentials
- Updated periodically with distilled wisdom
- Serves as a persistent knowledge base

### Daily Notes (memory/*.md)
- Created daily: `memory/YYYY-MM-DD.md`
- Raw conversation logs and context
- Serves as a source for MEMORY.md updates

### USER.md
- Personal facts about Jeremy
- Contains behavioral guidelines
- Used for context and interaction strategy

### HEARTBEAT.md Integration
- Defines memory capture process
- Specifies what to capture in different memory systems
- Provides automated capture and maintenance strategy

## 4. Integration Points

### Cross-System Capture Strategy
| Type | Graphiti | Memory V2 | File-based |
|------|----------|-----------|------------|
| Decisions | ✅ | ✅ | ✅ |
| Technical Learnings | ✅ | ✅ | ✅ |
| People/Relationships | ✅ | - | - |
| Entity Connections | ✅ | - | - |
| Searchable Facts | - | ✅ | - |
| Patterns | - | ✅ | ✅ |

### Gaps and Redundancies
1. **Potential Overlap:** Multiple systems capture similar information
2. **Decay Mechanism Missing:** No clear strategy for memory importance
3. **Manual Curation Required:** Relies on periodic human review

### Recommendations for Improvement
1. **Unified Capture Interface:** Create a single entry point for memory addition
2. **Implement Heat Decay:** Add time-based relevance scoring
3. **Automated Deduplication:** Develop a mechanism to identify and merge redundant memories
4. **Enhanced Search Capability:** Improve cross-system search functionality
5. **Automated Curation:** Develop an AI-driven system to periodically review and optimize memories

## Conclusion
The current memory architecture provides a robust, multi-layered approach to memory management. The combination of vector store, knowledge graph, and file-based systems offers flexibility and depth. However, there's significant room for optimization in integration, decay mechanisms, and automated curation.

---

**Last Reviewed:** 2026-02-01
**Review Status:** Initial Comprehensive Assessment