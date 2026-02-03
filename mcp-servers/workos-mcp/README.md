# WorkOS MCP Server

A high-performance [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides AI assistants with comprehensive task management, habit tracking, and productivity tools integrated with Life OS.

[![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)](package.json)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)
[![MCP SDK](https://img.shields.io/badge/MCP%20SDK-1.0-green.svg)](https://github.com/modelcontextprotocol/sdk)

## ✨ Features

- **24+ MCP Tools** across 5 domain modules for task management, habit tracking, energy logging, brain dumps, and personal tasks
- **High-Performance Caching** - SQLite cache layer reduces database load and improves latency
- **Clean Modular Architecture** - Domain-driven design with 92% code reduction in main entry point
- **Type-Safe** - Full TypeScript support with comprehensive type definitions
- **Production-Ready** - Neon Postgres backend with robust error handling

## 🏗️ Modular Architecture

This server was recently refactored from a monolithic 1,784-line file into a clean, maintainable domain-driven architecture:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| `index.ts` size | 1,784 lines | 135 lines | **92% reduction** |
| Code organization | Single file | 5 domains + shared utilities | ✅ Modular |
| Maintainability | Hard to navigate | Easy to maintain | ✅ Improved |

### Architecture Highlights

- **Domain Modules** - Separate modules for Tasks, Habits, Energy, Brain Dump, and Personal Tasks
- **Shared Utilities** - Common database, types, and utility functions
- **Cache Layer** - SQLite caching with cache-first reads and write-through updates
- **Simple Routing** - Clean delegation to domain handlers

📖 **See [src/README.md](src/README.md) for detailed architecture documentation**

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
npm install

# Build the TypeScript project
npm run build
```

### Configuration

Set your database connection string:

```bash
export DATABASE_URL="postgresql://user:password@host/database"
```

### Running the Server

```bash
# Production
npm start

# Development (with hot reload)
npm run dev
```

The server will start and listen for MCP protocol requests over stdio.

## 🔒 Security

The WorkOS MCP server implements comprehensive security measures to protect against abuse, resource exhaustion, and malicious inputs:

### Rate Limiting

Three-tier rate limiting prevents denial of service and resource exhaustion:

- **Global Limit**: 100 requests/minute (all operations combined)
- **Write Operations**: 20 requests/minute (creates, updates, deletes)
- **Read Operations**: 60 requests/minute (queries, retrievals)

Uses a sliding window algorithm to prevent burst traffic at window boundaries.

### Input Validation

All tool inputs are validated with Zod schemas enforcing:

- **String Length Limits**: Task titles (200 chars), descriptions (2000 chars), habit names (100 chars), brain dump content (5000 chars), notes (500 chars)
- **Numeric Ranges**: Query limits (1-100), positive IDs, bounded health metrics
- **Enum Validation**: Status, category, frequency, and other enumerated fields
- **Sanitization**: Automatic string trimming and value normalization

Invalid inputs are rejected immediately with clear, user-friendly error messages.

### Configuration

Rate limits can be adjusted via environment variables:

```bash
# Disable rate limiting (testing only)
export RATE_LIMIT_ENABLED=false

# Adjust global limits
export RATE_LIMIT_GLOBAL_PER_MINUTE=200
export RATE_LIMIT_GLOBAL_PER_HOUR=6000

# Adjust operation-specific limits
export RATE_LIMIT_WRITE_PER_MINUTE=40
export RATE_LIMIT_READ_PER_MINUTE=120
```

📖 **See [VALIDATION.md](VALIDATION.md) for detailed security documentation, validation rules, and examples**

## 🛠️ Available Tools

### Task Management (12 tools)
- `workos_get_server_version` - WorkOS MCP server version and compatibility metadata
- `workos_get_today_metrics` - Daily task completion metrics
- `workos_get_tasks` - Retrieve tasks with filtering
- `workos_get_clients` - List clients and projects
- `workos_create_task` - Create new tasks
- `workos_complete_task` - Mark tasks as complete
- `workos_promote_task` - Promote queued tasks to active
- `workos_get_streak` - Calculate completion streaks
- `workos_get_client_memory` - Retrieve client-specific context
- `workos_daily_summary` - Generate daily summaries
- `workos_update_task` - Update existing tasks
- `workos_delete_task` - Delete tasks

### Habit Tracking (7 tools)
- `workos_get_habits` - Retrieve habit definitions
- `workos_create_habit` - Create new habits
- `workos_complete_habit` - Log habit completions
- `workos_get_habit_streaks` - Calculate habit streaks
- `workos_habit_checkin` - Daily habit check-in
- `workos_habit_dashboard` - Comprehensive habit overview
- `workos_recalculate_streaks` - Recalculate all streaks

### Energy Tracking (2 tools)
- `workos_log_energy` - Log energy state
- `workos_get_energy` - Retrieve energy logs

### Brain Dump (3 tools)
- `workos_brain_dump` - Capture quick thoughts
- `workos_get_brain_dump` - Retrieve brain dumps
- `workos_process_brain_dump` - Process and organize dumps

### Personal Tasks (1 tool)
- `workos_get_personal_tasks` - Retrieve personal task lists

## 📚 Documentation

- **[Architecture Guide](src/README.md)** - Detailed documentation of the modular architecture, domain modules, shared utilities, and cache layer
- **[Testing Guide](TESTING.md)** - Comprehensive testing documentation with automated test suites
- **[Development Docs](docs/)** - Additional development documentation

## 🧪 Testing

The server includes comprehensive automated test suites:

```bash
# Run task domain tests
./test-tasks.mjs

# Run habit domain tests
./test-habits.mjs

# Run remaining domain tests
./test-remaining-domains.mjs

# Run cache integration tests
./test-cache-integration.mjs
```

All 34 tests pass successfully (24 tool tests + 10 cache tests).

📖 **See [TESTING.md](TESTING.md) for detailed testing documentation**

## 🔧 Development

### Project Structure

```
workos-mcp/
├── src/
│   ├── index.ts              # Main server entry point
│   ├── schema.ts             # Database schema
│   ├── shared/               # Shared utilities
│   │   ├── db.ts             # Database connection
│   │   ├── types.ts          # TypeScript types
│   │   └── utils.ts          # Common utilities
│   ├── cache/                # SQLite caching layer
│   └── domains/              # Domain modules
│       ├── tasks/            # Task management
│       ├── habits/           # Habit tracking
│       ├── energy/           # Energy logging
│       ├── brain-dump/       # Brain dump capture
│       └── personal-tasks/   # Personal tasks
├── dist/                     # Compiled JavaScript
├── test-*.mjs                # Test suites
└── TESTING.md                # Testing documentation
```

### Adding New Tools

Follow these steps to add a new tool:

1. **Choose a domain** - Determine which domain module (tasks, habits, etc.) the tool belongs to
2. **Add tool definition** - Define the MCP tool schema in `domains/{domain}/tools.ts`
3. **Implement handler** - Create the handler function in `domains/{domain}/handlers.ts`
4. **Register in router** - Add routing logic in `domains/{domain}/index.ts`
5. **Test** - Build and test your new tool

📖 **See [src/README.md](src/README.md#-adding-new-tools) for detailed instructions**

### Building

```bash
npm run build
```

TypeScript will compile to the `dist/` directory.

### Database Migrations

```bash
# Run Drizzle migrations
npx drizzle-kit push
```

## 💾 Cache Layer

The server includes a high-performance SQLite cache layer that:

- **Reduces database load** - Cache-first reads avoid expensive Neon queries
- **Improves latency** - SQLite is co-located with the server
- **Maintains freshness** - Automatic sync when cache is stale (>5 minutes)

The cache integrates transparently with all domain handlers using:
- **Cache-first read pattern** - Try cache before database
- **Write-through updates** - Keep cache in sync with writes

## 🎯 Benefits of the Modular Architecture

### 1. **Maintainability**
Each domain is self-contained and can be understood independently. No more scrolling through 1,700+ lines to find a specific handler.

### 2. **Testability**
Domain handlers can be tested in isolation with clear interfaces and mock databases.

### 3. **Scalability**
Adding new tools is straightforward with established patterns. New domains can be added without touching existing code.

### 4. **Code Review**
Changes are localized to specific domains, making reviews easier and impact analysis clearer.

### 5. **Developer Experience**
Fast navigation, better IDE support, and consistent patterns reduce cognitive load.

## 📊 Refactoring Metrics

The recent refactoring (Task #026) achieved:

- **92% code reduction** in main entry point (1,784 → 135 lines)
- **Zero functionality changes** - All 24 tools work identically
- **100% test coverage** - All automated tests pass
- **Preserved performance** - Cache integration fully functional

## 🤝 Contributing

When contributing to this project:

1. Follow the established domain module patterns
2. Add JSDoc comments to all exported functions
3. Include tests for new functionality
4. Build and verify TypeScript compilation
5. Update documentation as needed

## 📝 License

This is a private project integrated with Life OS.

## 🔗 Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io) - Protocol specification
- [MCP SDK](https://github.com/modelcontextprotocol/sdk) - TypeScript SDK
- [Neon](https://neon.tech) - Serverless Postgres backend
- [Drizzle ORM](https://orm.drizzle.team) - TypeScript ORM

---

**Version**: 1.1.0
**Last Updated**: 2026-01-11
**Refactoring Task**: #026 - Split massive MCP server index.ts into domain modules
