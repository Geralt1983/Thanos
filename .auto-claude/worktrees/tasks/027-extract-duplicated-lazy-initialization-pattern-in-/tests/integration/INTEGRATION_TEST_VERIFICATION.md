# Integration Test Verification for Command Router Memory Commands

## Overview

This document describes the integration tests created for subtask 3.4, which verify that the command router's memory-related commands (`/memory`, `/recall`, `/remember`) work correctly with the lazy-initialized MemOS adapter.

## Test File

**Location:** `tests/integration/test_command_router_memory.py`

## Test Coverage

### 1. TestMemoryCommand Class (7 tests)

Tests the `/memory` command that displays memory system information:

- ✅ `test_memory_command_basic` - Basic /memory command execution
- ✅ `test_memory_command_with_memos_available` - /memory when MemOS is available
- ✅ `test_memory_command_without_memos` - /memory when MemOS is unavailable
- ✅ `test_memory_command_shows_session_history` - Displays session count
- ✅ `test_memory_command_shows_swarm_memory` - Displays swarm DB info
- ✅ `test_memory_command_shows_hive_memory` - Displays hive-mind DB info

**Purpose:** Verify /memory command displays correct information about all memory systems (MemOS, session history, swarm, hive-mind) and handles MemOS availability gracefully.

### 2. TestRecallCommand Class (8 tests)

Tests the `/recall` command that searches memories:

- ✅ `test_recall_command_no_args` - Shows usage without arguments
- ✅ `test_recall_command_with_memos` - Searches MemOS when available
- ✅ `test_recall_command_without_memos` - Falls back to session search
- ✅ `test_recall_command_sessions_only_flag` - --sessions flag skips MemOS
- ✅ `test_recall_command_handles_memos_failure` - Graceful failure handling
- ✅ `test_recall_command_vector_results` - Displays vector search results
- ✅ `test_recall_command_graph_results` - Displays graph search results

**Purpose:** Verify /recall command performs hybrid search (vector + graph) through MemOS, handles failures gracefully, and falls back to session search when MemOS is unavailable.

### 3. TestRememberCommand Class (11 tests)

Tests the `/remember` command that stores memories:

- ✅ `test_remember_command_no_args` - Shows usage without arguments
- ✅ `test_remember_command_without_memos` - Fails gracefully without MemOS
- ✅ `test_remember_command_stores_observation` - Stores observation memory
- ✅ `test_remember_command_stores_decision` - Stores decision with "decision:" prefix
- ✅ `test_remember_command_stores_pattern` - Stores pattern with "pattern:" prefix
- ✅ `test_remember_command_extracts_entities` - Extracts @entity mentions
- ✅ `test_remember_command_uses_agent_domain` - Maps agent to domain (work/health/personal)
- ✅ `test_remember_command_includes_metadata` - Includes agent and session metadata
- ✅ `test_remember_command_handles_failure` - Handles storage failure gracefully
- ✅ `test_remember_command_handles_none_result` - Handles None result gracefully

**Purpose:** Verify /remember command stores memories in MemOS with correct type classification, entity extraction, domain mapping, and metadata, while handling all failure cases gracefully.

### 4. TestLazyInitialization Class (4 tests)

Tests lazy initialization behavior of MemOS adapter:

- ✅ `test_memos_lazy_initialization_on_memory_command` - MemOS initialized on first use
- ✅ `test_memos_initialization_idempotency` - MemOS initialized only once
- ✅ `test_commands_work_without_memos_available` - Commands work without MemOS
- ✅ `test_memos_initialization_failure_handling` - Handles initialization failures

**Purpose:** Verify that MemOS adapter is lazily initialized (not at CommandRouter construction), initialized only once (idempotency), and all commands handle unavailability or initialization failures gracefully.

## Total Test Count

**30 integration tests** covering all aspects of memory command functionality and lazy initialization.

## Running the Tests

### Option 1: Run all integration tests
```bash
pytest tests/integration/test_command_router_memory.py -v
```

### Option 2: Run specific test class
```bash
pytest tests/integration/test_command_router_memory.py::TestMemoryCommand -v
pytest tests/integration/test_command_router_memory.py::TestRecallCommand -v
pytest tests/integration/test_command_router_memory.py::TestRememberCommand -v
pytest tests/integration/test_command_router_memory.py::TestLazyInitialization -v
```

### Option 3: Run single test
```bash
pytest tests/integration/test_command_router_memory.py::TestLazyInitialization::test_memos_initialization_idempotency -v
```

### With coverage report
```bash
pytest tests/integration/test_command_router_memory.py --cov=Tools.command_router --cov-report=term-missing
```

## Manual Verification Steps

If you want to manually verify the commands work in the actual Thanos interactive mode:

### 1. Test /memory command
```bash
$ ./thanos.py interactive
Thanos> /memory
```
**Expected:** Should display memory system information including MemOS, Neo4j, ChromaDB, session history, swarm, and hive-mind status.

### 2. Test /remember command
```bash
Thanos> /remember Team meeting scheduled for tomorrow
Thanos> /remember decision: Use PostgreSQL for user data
Thanos> /remember pattern: Daily standup at 9 AM
Thanos> /remember Meeting with @John about @ProjectX
```
**Expected:** Each command should store the memory in MemOS and display confirmation with type, domain, entities, graph ID, and vector status.

### 3. Test /recall command
```bash
Thanos> /recall meeting
Thanos> /recall PostgreSQL decision
Thanos> /recall --sessions standup
```
**Expected:** Should search MemOS (hybrid vector + graph search) and display results with content, type, and similarity scores. The --sessions flag should skip MemOS and search only session history.

### 4. Test lazy initialization idempotency
```bash
Thanos> /memory          # First call - initializes MemOS
Thanos> /remember test   # Uses existing MemOS instance
Thanos> /recall test     # Uses existing MemOS instance
Thanos> /memory          # Uses existing MemOS instance
```
**Expected:** MemOS should be initialized only once (on first command), and all subsequent commands should reuse the same instance.

### 5. Test graceful degradation without MemOS
```bash
# Temporarily rename/disable Neo4j environment variables
$ NEO4J_URI="" ./thanos.py interactive
Thanos> /memory
Thanos> /remember test
Thanos> /recall test
```
**Expected:** Commands should execute without crashing. /memory should show "MemOS not available", /remember should fail with helpful message, /recall should fall back to session search.

## Requirements Verified

✅ **Lazy Initialization:** MemOS adapter is initialized on first use, not at construction
✅ **Idempotency:** MemOS is only initialized once, reused across multiple commands
✅ **Graceful Degradation:** Commands work (or fail gracefully) when MemOS unavailable
✅ **Command Functionality:** /memory, /recall, /remember all work as expected
✅ **Error Handling:** All failure scenarios handled without crashes
✅ **Integration:** Commands properly integrate with MemOS hybrid search (Neo4j + ChromaDB)
✅ **Type Classification:** /remember correctly handles observation, decision, pattern types
✅ **Entity Extraction:** @entity mentions properly extracted
✅ **Domain Mapping:** Agent context correctly maps to memory domain
✅ **Metadata:** Agent and session info included in stored memories

## Key Features Tested

1. **Hybrid Search:** Vector (ChromaDB) + Graph (Neo4j) search in /recall
2. **Type Prefixes:** `decision:`, `pattern:`, `commitment:`, `entity:` in /remember
3. **Entity Mentions:** @entity syntax for relationship mapping
4. **Agent Context:** ops→work, health→health, coach→personal domain mapping
5. **Session Integration:** Session ID included in memory metadata
6. **Availability Flags:** MEMOS_AVAILABLE flag controls initialization
7. **Async Support:** Proper async/await handling for MemOS operations
8. **Fallback Behavior:** Session history search when MemOS unavailable

## Dependencies

- **Required Packages:** pytest, pytest-mock, pytest-asyncio
- **MemOS Components:** Neo4j, ChromaDB, Tools.memos module
- **Environment Variables:** NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, OPENAI_API_KEY (for embeddings)

## Success Criteria

All 30 integration tests pass, demonstrating that:
- Commands execute successfully with lazy-initialized adapters
- MemOS initialization is lazy and idempotent
- Graceful degradation works when MemOS unavailable
- All memory operations (store, search, display) function correctly
- Error handling prevents crashes in all failure scenarios

## Notes

- Tests use extensive mocking to isolate command router behavior
- Async operations properly handled with AsyncMock
- Fixtures provide reusable test components
- Capsys fixture captures and verifies printed output
- Tmp_path fixture creates isolated test directories
