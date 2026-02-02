## Relations
@design/mcp_integration.md
@structure/state_management.md
@structure/memory_system.md

## Raw Concept
**Task:**
Define core architectural principles and layers of Thanos v2.0

**Changes:**
- Removed legacy interactive mode (thanos.py interactive)
- Consolidated all user interaction into Claude Code via MCP tools

**Files:**
- ARCHITECTURE.md
- CLAUDE.md

**Flow:**
User -> Claude Code (NL) -> MCP Protocol -> Thanos (Backend) -> State/Memory/APIs

**Timestamp:** 2026-01-31

## Narrative
### Structure
- mcp-servers/: Tool implementations (workos-mcp, oura-mcp, memory-v2-mcp)
- State/: Current system state and critical facts
- memory/: Semantic search indices and vector embeddings
- History/: Session logs and briefings

### Dependencies
- Claude Code (Primary Orchestrator)
- Model Context Protocol (MCP) as the communication interface
- File-based state storage (State/ directory)
- Vector memory storage (memory/ directory)

### Features
- Backend-only service (no user-facing UI or direct CLI)
- AI-powered orchestration for task/life management
- ADHD-optimized workflows via natural language
- Single Responsibility: Claude Code handles UX, Thanos handles state/logic
