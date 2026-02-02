## Relations
@structure/architecture/core_architecture_overview.md

## Raw Concept
**Task:**
Define the interface contract for Thanos capabilities

**Changes:**
- Established MCP as the ONLY approved interface for system capabilities

**Files:**
- ARCHITECTURE.md
- mcp-servers/README.md (implied)

**Flow:**
Claude Code -> Call Tool -> MCP Server -> Business Logic -> JSON Result -> Claude Code

**Timestamp:** 2026-01-31

## Narrative
### Structure
- mcp-servers/workos-mcp: Tasks, habits, energy
- mcp-servers/oura-mcp: Biometric data
- mcp-servers/memory-v2-mcp: Semantic memory
- mcp-servers/openweathermap-mcp: Weather data

### Dependencies
- MCP SDK
- WorkOS API/Database
- Oura API
- Vector DB/Search libraries

### Features
- Standardization: All capabilities exposed as tools
- Separation: Logic resides in servers, presentation in Claude Code
- Extensibility: New features added as tools, not CLI commands
