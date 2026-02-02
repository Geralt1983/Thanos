## Relations
@structure/memory_system/memory_v2_heat_system.md
@structure/architecture/core_architecture_overview.md

## Raw Concept
**Task:**
Automate episodic memory processing and relationship tracking via Graphiti

**Changes:**
- Implemented automated daily ingestion of memory notes into the Graphiti knowledge graph

**Files:**
- scripts/graphiti-daily-digest.py

**Flow:**
Daily Notes (.md) -> Digest Script -> Docker Exec -> Graphiti API -> Neo4j Knowledge Graph

**Timestamp:** 2026-01-31

## Narrative
### Structure
- Script: scripts/graphiti-daily-digest.py
- Ingestion Target: Neo4j via docker exec mcp-root
- Source Data: memory/*.md files

### Dependencies
- Graphiti Core
- Neo4j Database (bolt://localhost:7687)
- Docker (mcp-root container)
- Memory directory (memory/YYYY-MM-DD.md)

### Features
- Daily cron automation (10pm EST)
- Automated episodic memory ingestion from daily notes
- Extraction of people, projects, decisions, and outcomes
- Complements real-time semantic search (Memory V2) with structured graph relationships
