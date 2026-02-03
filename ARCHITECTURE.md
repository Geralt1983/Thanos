# Thanos Architecture

## Overview

Thanos is a **backend service** designed to provide AI-powered orchestration capabilities for personal productivity, task management, and life optimization. It is explicitly **NOT** a user-facing application or chatbot. Thanos sits between **OpenClaw (orchestrator)** and **WorkOS (Epic consult task storage)** as the architecture layer that unifies context, state, and integrations.

## Core Architectural Principle

**OpenClaw is the sole orchestrator** of all Thanos capabilities.

Users do not interact directly with Thanos. Instead, all user interaction flows through OpenClaw (Codex/Claude front-ends), which consumes Thanos as a backend service through well-defined interfaces.

## Architecture Layers

```
┌─────────────────────────────────────────┐
│         User (Jeremy)                   │
│                                         │
└────────────┬────────────────────────────┘
             │
             │ Natural Language
             │
             ▼
┌─────────────────────────────────────────┐
│   OpenClaw (Primary Orchestrator)       │
│                                         │
│  - Natural language interface           │
│  - Personality layer (Thanos persona)   │
│  - Context management                   │
│  - Decision making                      │
└────────┬────────────────────────────────┘
         │
         │ MCP Protocol (Model Context Protocol)
         │
         ▼
┌─────────────────────────────────────────┐
│      Thanos (Architecture Layer)        │
│                                         │
│  - State management (State/)            │
│  - Memory storage (memory/)             │
│  - External API integrations            │
│  - MCP server implementations           │
│  - Business logic                       │
└────────┬────────────────────────────────┘
         │
         │ MCP / DB Integration
         │
         ▼
┌─────────────────────────────────────────┐
│      WorkOS (Task Storage)              │
│      Epic Consult Work Tasks            │
└─────────────────────────────────────────┘
```

## Interface Contract: MCP-Only

**The ONLY approved interface** to Thanos is through **MCP (Model Context Protocol)** tools and file-based state.

### MCP Servers

Thanos capabilities are exposed through MCP servers located in `mcp-servers/`:

| Server | Purpose | Tools Exposed |
|--------|---------|---------------|
| **workos-mcp** | Task management, habits, energy tracking, clients | `workos_get_tasks`, `workos_create_task`, `workos_complete_task`, `workos_habit_checkin`, etc. |
| **oura-mcp** | Health and biometric data from Oura Ring | `oura__get_daily_readiness`, `oura__get_daily_sleep`, `oura__get_daily_activity` |
| **memory-v2-mcp** | Semantic memory search and storage | `search_memory`, `add_memory`, `whats_hot`, `whats_cold` |
| **openweathermap-mcp** | Weather data | `get_weather` |

### State and Memory Files

OpenClaw reads directly from Thanos state files:

| Directory | Contents |
|-----------|----------|
| `State/` | Current system state, critical facts, focus documents |
| `memory/` | Vector embeddings, semantic search indices |
| `History/` | Session logs, daily briefings |

### What is NOT Allowed

❌ **Direct CLI interaction** - No `thanos.py interactive` or similar commands
❌ **User-facing prompts** - Thanos code should never use `input()` or prompt users
❌ **Chat interfaces** - No chatbot functionality in Thanos itself
❌ **Interactive loops** - No REPL-style interfaces

All user interaction must flow through OpenClaw as the orchestrator.

## Why This Architecture?

### 1. Single Responsibility Principle

- **OpenClaw**: Handles natural language understanding, personality, user interaction
- **Thanos**: Handles state management, external integrations, business logic

### 2. ADHD-Optimized Workflows

- Natural language is more accessible than CLI commands for ADHD users
- OpenClaw can adapt tone, pacing, and suggestions based on context
- File-based state provides external working memory

### 3. Maintainability

- Clear separation of concerns
- MCP provides a stable, versioned interface contract
- No tight coupling between user experience and backend logic

### 4. Extensibility

- New capabilities are added as MCP tools
- OpenClaw can compose tools in intelligent ways
- State files can be read by any system (not just OpenClaw)

## Historical Context: The Interactive Mode Experiment

An earlier version of Thanos included an "interactive mode" (`thanos.py interactive` / `ti` script) that attempted to provide direct CLI interaction. **This was an architectural mistake** and has been removed.

### Why It Failed

1. **Duplicated Orchestration Logic**: Created parallel command routing outside OpenClaw
2. **Poor User Experience**: CLI commands less natural than conversational AI
3. **Maintenance Burden**: Two interfaces to maintain instead of one
4. **Violated Single Responsibility**: Thanos became both backend AND frontend

### The Correct Pattern

Instead of building user-facing interfaces into Thanos:

1. ✅ Expose capabilities as **MCP tools**
2. ✅ Write state to **files** that OpenClaw reads
3. ✅ Let **OpenClaw orchestrator** handle all user interaction
4. ✅ Keep Thanos as a **backend service** focused on business logic

## Developer Guidelines

### Adding New Features

When adding new functionality to Thanos:

1. **Create an MCP tool** in the appropriate server (or create new server)
2. **Write state to files** in `State/` directory if needed
3. **Update CLAUDE.md** to teach OpenClaw how to use the new tool
4. **Do NOT** create new CLI commands that interact directly with users

### Testing

- Unit tests: Test business logic in isolation
- Integration tests: Test MCP tool interfaces
- End-to-end tests: Use OpenClaw to verify full workflow

### Documentation

- MCP tools: Document in server README and CLAUDE.md
- State files: Document schema in relevant README
- Architecture decisions: Document in this file (ARCHITECTURE.md)

## Migration Path

If you're working on code that violates this architecture:

1. Identify direct user interaction (e.g., `input()`, interactive loops)
2. Convert to MCP tool that returns data to OpenClaw
3. Let OpenClaw handle user prompts and responses
4. Remove interactive code from Thanos

## Questions?

If you're unsure whether something violates this architecture, ask:

- **Does this code prompt the user for input?** → ❌ Belongs in OpenClaw
- **Does this code present information to the user?** → ❌ Return data; let OpenClaw present it
- **Does this code make decisions about user experience?** → ❌ Belongs in OpenClaw
- **Does this code manage state or call external APIs?** → ✅ Belongs in Thanos

---

**Remember: OpenClaw is the orchestrator. Thanos is the architecture layer. WorkOS is the task store. MCP is the interface.**
