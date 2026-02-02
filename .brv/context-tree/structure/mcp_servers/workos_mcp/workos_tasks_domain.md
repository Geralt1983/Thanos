## Relations
@structure/mcp_servers/mcp_server_infrastructure.md

## Raw Concept
**Task:**
Expose task management and productivity tools via MCP

**Changes:**
- Centralized task routing in workos-mcp tasks domain

**Files:**
- mcp-servers/workos-mcp/src/domains/tasks/index.ts

**Flow:**
Call Tool -> Router (switch) -> Handler -> DB Operation -> ContentResponse

**Timestamp:** 2026-01-31

## Narrative
### Structure
- mcp-servers/workos-mcp/src/domains/tasks/index.ts: Router/Entry point
- mcp-servers/workos-mcp/src/domains/tasks/handlers.ts: Implementation logic
- mcp-servers/workos-mcp/src/domains/tasks/tools.ts: Tool definitions

### Dependencies
- Database instance (Neon/PostgreSQL)
- ToolRouter and ContentResponse types
- Domain handlers and tool definitions

### Features
- Task CRUD operations
- Energy-aware task filtering
- Metric tracking (today, specific dates)
- Client-specific memory retrieval
- Daily goal adjustment and summaries
