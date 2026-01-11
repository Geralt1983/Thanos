# WorkOS MCP Server - Source Architecture

This document explains the modular architecture of the WorkOS MCP server after the refactoring from a monolithic 1,784-line `index.ts` file to a clean domain-driven structure.

## 📁 Directory Structure

```
src/
├── index.ts                    # Main server entry point (~135 lines)
├── schema.ts                   # Database schema definitions
│
├── shared/                     # Shared utilities used across domains
│   ├── db.ts                   # Database connection factory
│   ├── types.ts                # TypeScript types and interfaces
│   └── utils.ts                # Common utility functions
│
├── cache/                      # SQLite caching layer
│   ├── cache.ts                # Cache initialization and CRUD operations
│   ├── sync.ts                 # Database-to-cache synchronization
│   ├── schema.ts               # Cache schema definitions
│   └── index.ts                # Cache exports
│
└── domains/                    # Domain-specific modules
    ├── tasks/                  # Task management (11 tools)
    │   ├── handlers.ts         # Tool handler implementations
    │   ├── tools.ts            # Tool definitions
    │   └── index.ts            # Domain router
    │
    ├── habits/                 # Habit tracking (7 tools)
    │   ├── handlers.ts
    │   ├── tools.ts
    │   └── index.ts
    │
    ├── energy/                 # Energy state logging (2 tools)
    │   ├── handlers.ts
    │   ├── tools.ts
    │   └── index.ts
    │
    ├── brain-dump/             # Brain dump capture (3 tools)
    │   ├── handlers.ts
    │   ├── tools.ts
    │   └── index.ts
    │
    └── personal-tasks/         # Personal task queries (1 tool)
        ├── handlers.ts
        ├── tools.ts
        └── index.ts
```

## 🏗️ Architecture Overview

### Main Entry Point (`index.ts`)

The main `index.ts` file has been reduced from **1,784 lines to 135 lines** (92% reduction). It now serves as a thin orchestration layer that:

1. **Imports domain modules** - Brings in tools and handlers from each domain
2. **Initializes cache** - Sets up the SQLite caching layer at startup
3. **Registers tools** - Combines tool definitions from all domains
4. **Routes requests** - Delegates tool calls to appropriate domain handlers

```typescript
// Example routing logic
if (name.includes("habit")) {
  return await handleHabitTool(name, args, db);
} else if (name.includes("energy")) {
  return await handleEnergyTool(name, args, db);
} else {
  return await handleTaskTool(name, args, db);
}
```

### Domain Modules

Each domain module follows a consistent three-file pattern:

#### 1. `tools.ts` - Tool Definitions
Defines the MCP tool schemas that clients can call:

```typescript
export function getTaskTools(): ToolDefinition[] {
  return [
    {
      name: "workos_get_tasks",
      description: "Retrieve tasks from the database",
      inputSchema: {
        type: "object",
        properties: {
          status: { type: "string", enum: ["active", "queued", "backlog", "done"] },
          clientId: { type: "number" },
          limit: { type: "number" }
        },
        required: []
      }
    },
    // ... more tool definitions
  ];
}
```

#### 2. `handlers.ts` - Implementation Logic
Contains the actual implementation for each tool:

```typescript
/**
 * Retrieves tasks from the database with optional filtering
 */
export async function handleGetTasks(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  // Implementation logic
  return successResponse(tasks);
}
```

Each handler:
- Accepts typed arguments and database instance
- Returns a `ContentResponse` (MCP protocol format)
- Includes comprehensive JSDoc documentation
- Follows consistent error handling patterns

#### 3. `index.ts` - Domain Router
Routes tool calls within the domain to the appropriate handler:

```typescript
export const handleTaskTool: ToolRouter = async (
  name: string,
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> => {
  switch (name) {
    case "workos_get_tasks":
      return handleGetTasks(args, db);
    case "workos_create_task":
      return handleCreateTask(args, db);
    // ... more routes
    default:
      return errorResponse(`Unknown task tool: ${name}`);
  }
};
```

## 🔧 Shared Utilities

The `shared/` directory contains utilities used across all domains:

### `shared/db.ts`
Database connection factory:
```typescript
export function getDb(): Database {
  const connectionString = process.env.DATABASE_URL;
  // Returns configured Neon database instance
}
```

### `shared/types.ts`
Common TypeScript types and interfaces:
- `Database` - Database instance type
- `ToolDefinition` - MCP tool schema structure
- `ContentResponse` - Standard MCP response format
- `ToolHandler` - Handler function signature
- `ToolRouter` - Router function signature
- `successResponse()` - Helper for success responses
- `errorResponse()` - Helper for error responses

### `shared/utils.ts`
Common utility functions:
- **Date/Time utilities**: `getESTNow()`, `getESTTodayStart()`, `getESTDateString()`
- **Frequency utilities**: `isWeekday()`, `getExpectedPreviousDate()`
- **Points calculation**: `calculatePoints()`, `calculateTotalPoints()`

## 💾 Cache Layer

The `cache/` directory implements a high-performance SQLite caching layer:

### Purpose
- **Reduce database load** - Cache-first reads avoid expensive Neon queries
- **Improve latency** - SQLite is co-located with the server
- **Maintain freshness** - Automatic sync when cache is stale

### Key Files

#### `cache/cache.ts`
Cache initialization and CRUD operations:
- `initCache()` - Initialize SQLite database
- `getCachedTasks()`, `getCachedClients()`, `getCachedHabits()` - Read operations
- `syncSingleTask()`, `removeCachedTask()` - Write-through operations
- `getCacheStats()` - Cache metadata and staleness detection

#### `cache/sync.ts`
Database-to-cache synchronization:
- `syncAll()` - Sync all entities from Neon to SQLite
- `syncClients()`, `syncTasks()`, `syncHabits()` - Entity-specific sync
- Automatically triggered when cache is empty or stale (>5 minutes)

### Cache Integration Pattern

Handlers use a **cache-first read** pattern:

```typescript
// 1. Try cache first
const cached = await getCachedTasks({ status, clientId, limit });
if (cached.length > 0) {
  return successResponse(cached);
}

// 2. Fall back to database if cache miss
const tasks = await db.select().from(schema.tasks)...;
return successResponse(tasks);
```

Write operations use a **write-through** pattern to keep cache in sync.

## 📊 Current Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| `index.ts` lines | 1,784 | 135 | **92% reduction** |
| Largest file | 1,784 lines | 705 lines | **60% reduction** |
| Total tools | 24+ | 24+ | ✅ Preserved |
| Cache integration | ✅ | ✅ | ✅ Preserved |

### Domain Distribution
- **Tasks**: 11 tools (705 LOC handlers, 228 LOC tools)
- **Habits**: 7 tools (610 LOC handlers, 109 LOC tools)
- **Energy**: 2 tools (66 LOC handlers, 40 LOC tools)
- **Brain Dump**: 3 tools (122 LOC handlers, 52 LOC tools)
- **Personal Tasks**: 1 tool (38 LOC handlers, 26 LOC tools)

## ➕ Adding New Tools

### 1. Choose or Create a Domain
Determine which domain the tool belongs to, or create a new domain if it represents a new area of functionality.

### 2. Add Tool Definition
In `domains/{domain}/tools.ts`, add the tool schema:

```typescript
{
  name: "workos_my_new_tool",
  description: "What this tool does",
  inputSchema: {
    type: "object",
    properties: {
      param1: { type: "string", description: "First parameter" },
      param2: { type: "number", description: "Second parameter" }
    },
    required: ["param1"]
  }
}
```

### 3. Implement Handler
In `domains/{domain}/handlers.ts`, create the handler function:

```typescript
/**
 * Handles my new tool
 * @param args - Tool arguments
 * @param db - Database instance
 * @returns MCP ContentResponse with result data
 */
export async function handleMyNewTool(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  try {
    const { param1, param2 } = args;

    // Your implementation here
    const result = await db.select()...;

    return successResponse(result);
  } catch (error) {
    return errorResponse(
      "Failed to execute my new tool",
      error instanceof Error ? error.message : String(error)
    );
  }
}
```

### 4. Register in Router
In `domains/{domain}/index.ts`, add a case to the switch statement:

```typescript
case "workos_my_new_tool":
  return handleMyNewTool(args, db);
```

### 5. Test
Build and test your new tool:

```bash
npm run build
# Test using MCP inspector or your client application
```

## 🎯 Benefits of This Architecture

### 1. **Maintainability**
- Each domain is self-contained and can be understood independently
- No more scrolling through 1,700+ lines to find a specific handler
- Clear separation of concerns

### 2. **Testability**
- Domain handlers can be tested in isolation
- Mock database and test individual functions
- Clear interfaces make testing straightforward

### 3. **Scalability**
- Adding new tools is straightforward with established patterns
- New domains can be added without touching existing code
- Each domain can be optimized independently

### 4. **Code Review**
- Changes are localized to specific domains
- Easier to review small, focused files
- Clear impact analysis

### 5. **Developer Experience**
- Fast navigation to relevant code
- IDE autocomplete and type checking work better
- Consistent patterns reduce cognitive load

## 🔍 Code Patterns and Conventions

### Import Patterns
- Always use `.js` extensions for local imports (TypeScript ESM requirement)
- Import shared utilities from `shared/` directory
- Import types from `shared/types.js`

### Error Handling
- Use try-catch blocks in handlers
- Return `errorResponse()` with descriptive messages
- Include error details when helpful for debugging

### Documentation
- Add JSDoc comments to all exported functions
- Document parameters with `@param` tags
- Document return values with `@returns` tags

### TypeScript
- Use strong typing throughout
- Leverage `ToolHandler` and `ToolRouter` signatures
- Avoid `any` type where possible

### Response Format
- Always return `ContentResponse` from handlers
- Use `successResponse()` for successful operations
- Use `errorResponse()` for errors
- Serialize data as JSON with proper formatting

## 📚 Related Documentation

- See `../TESTING.md` for testing strategies and test suite
- See individual domain `handlers.ts` files for tool-specific documentation
- See `cache/CLAUDE.md` for cache layer implementation details

---

**Last Updated**: 2026-01-11
**Refactoring Task**: #026 - Split massive MCP server index.ts into domain modules
