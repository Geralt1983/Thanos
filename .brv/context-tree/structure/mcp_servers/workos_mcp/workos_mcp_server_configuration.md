## Relations
@structure/mcp_servers/workos_mcp/workos_tasks_domain.md

## Raw Concept
**Task:**
Register WorkOS MCP Server configuration and capabilities

**Changes:**
- Integration of WorkOS task management tools via MCP
- Local stdio execution for OpenClaw/Thanos access

**Files:**
- /Users/jeremy/Projects/WorkOS-v3/mcp-server/

**Flow:**
Thanos -> OpenClaw -> Local MCP Server (WorkOS) via mcporter

**Timestamp:** 2026-02-03

## Narrative
### Structure
Server location: /Users/jeremy/Projects/WorkOS-v3/mcp-server/
Start command: cd /Users/jeremy/Projects/WorkOS-v3 && bun run mcp:start
Call via mcporter: mcporter call --stdio "bun run mcp:start" tool_name args

### Dependencies
Requires WorkOS-v3 repository and Bun runtime. MCP runs locally via stdio.

### Features
Exposes full WorkOS task management: pipelines, search, create, update, complete, delete, promote, demote, suggest next, avoidance reports, and history.
