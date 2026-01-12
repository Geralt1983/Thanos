# Test Inventory

This document provides a comprehensive inventory of all test files in the Thanos project, organized by category with brief descriptions of what each tests.

**Last Updated:** 2026-01-12

---

## Summary

| Category | Count | Location |
|----------|-------|----------|
| **Unit Tests** | 33 | `tests/unit/` |
| **Integration Tests** | 7 | `tests/integration/` |
| **Root-Level Tests** | 6 | `tests/` |
| **Benchmarks** | 5 | `tests/benchmarks/` |
| **Supporting Files** | 3 | `tests/`, `tests/fixtures/` |
| **Total Test Files** | 51 | |

---

## Root-Level Tests (tests/)

These are primary test files for major system components:

### 1. test_commitment_tracker.py
**Category:** Unit
**Description:** Unit tests for CommitmentTracker and related utilities including commitment creation, validation, streak calculation, recurrence pattern handling, data persistence, miss detection, Coach integration, CRUD operations, and edge cases.

**Key Coverage:**
- Commitment creation and validation
- Streak calculation (current, longest, completion rate)
- Recurrence patterns (daily, weekly, weekdays, weekends)
- JSON serialization and data persistence
- Miss detection and Coach integration
- CRUD operations

### 2. test_commitment_integration.py
**Category:** Integration
**Description:** Integration tests for the commitment accountability system covering end-to-end workflows from creation to review.

**Key Coverage:**
- Complete workflow from creation to review
- Coach integration for missed commitments
- Weekly review generation with analytics
- Scheduler and check-in integration
- Data consistency across components

### 3. test_mcp_bridge.py
**Category:** Unit
**Description:** Unit tests for MCP Bridge adapter testing session management, tool listing, tool calling, and error handling.

**Key Coverage:**
- MCP Bridge initialization and configuration
- Session management
- Tool listing and calling
- Error handling
- Transport configurations (stdio, SSE)

### 4. test_mcp_discovery.py
**Category:** Unit
**Description:** Unit tests for MCP server discovery from multiple sources including merging, filtering, and error handling.

**Key Coverage:**
- Configuration discovery from multiple sources
- Config merging and filtering
- Path resolution (project-level and global)
- Error handling

### 5. test_mcp_errors.py
**Category:** Unit
**Description:** Unit tests for MCP error handling including custom exception hierarchy, error classification, logging, and recovery strategies.

**Key Coverage:**
- Custom MCP exception hierarchy
- Error classification and attributes
- Logging and error reporting
- Recovery strategies

### 6. test_time_persistence.py
**Category:** Unit
**Description:** Unit tests for Time Persistence functionality including TimeState.json management and temporal context tracking.

**Key Coverage:**
- TimeState.json creation on first interaction
- Elapsed time calculation for various gaps
- Human-readable time formatting
- Corrupted file handling and recovery
- System prompt temporal context inclusion

---

## Integration Tests (tests/integration/)

### 1. test_calendar_integration.py
**Category:** Integration
**Markers:** `integration`, `requires_google_calendar`
**Description:** Integration tests for Google Calendar adapter with real API interactions validating end-to-end flows.

**Key Coverage:**
- Google Calendar API integration
- OAuth credential handling
- Event CRUD operations
- Conflict detection
- Time-blocking functionality
- Real vs mocked API testing

### 2. test_chroma_adapter_integration.py
**Category:** Integration
**Markers:** `integration`, `requires_openai`
**Description:** Integration tests for ChromaDB adapter with batch embedding generation using actual ChromaDB instances.

**Key Coverage:**
- ChromaDB instance creation
- Batch embedding optimization
- OpenAI API integration for embeddings
- Vector storage and retrieval
- Semantic search functionality

### 3. test_daily_integration.py
**Category:** Integration
**Description:** Integration tests verifying daily.py integration with BriefingEngine maintains backward compatibility.

**Key Coverage:**
- Import validation
- BriefingEngine integration
- Backward compatibility verification
- save_to_history functionality preservation

### 4. test_neo4j_batch_operations.py
**Category:** Integration
**Markers:** `integration`
**Description:** Integration tests for Neo4j batch operations and session pooling with shared sessions.

**Key Coverage:**
- Multiple operations sharing a session
- Session pooling reducing overhead
- Batch operations with shared sessions
- Atomic transactions (commit/rollback)
- Non-atomic batch operations (partial success)

### 5. test_pattern_recognition_integration.py
**Category:** Integration
**Description:** Integration tests for complete pattern recognition pipeline from data aggregation to insight generation.

**Key Coverage:**
- Data aggregation → analysis → insight generation
- End-to-end pattern recognition workflow
- Neo4j pattern storage and retrieval
- Weekly review integration
- Full pipeline validation

### 6. test_real_data_validation.py
**Category:** Integration
**Description:** Integration test validating pattern recognition against actual historical data from sessions and commitments.

**Key Coverage:**
- Real historical data analysis
- Task completion data processing
- Commitment tracking validation
- Mock health data integration
- Confidence threshold tuning
- Statistical significance validation

### 7. test_spinner_integration.py
**Category:** Integration
**Markers:** `integration`
**Description:** Integration tests for spinner behavior with actual ThanosOrchestrator calls in different modes.

**Key Coverage:**
- Spinner with run_command() (streaming/non-streaming)
- Spinner with chat() (streaming/non-streaming)
- TTY vs non-TTY environment behavior
- Error handling during spinner operation
- Spinner lifecycle (start/stop/ok/fail)

---

## Unit Tests (tests/unit/)

### Adapter Tests

#### 1. test_adapters_base.py
**Description:** Unit tests for Tools/adapters/base.py testing ToolResult dataclass and BaseAdapter abstract base class.

**Key Coverage:**
- ToolResult dataclass creation and validation
- BaseAdapter interface definition
- Success/error result handling

#### 2. test_adapters_oura.py
**Description:** Unit tests for OuraAdapter class for Oura Ring API integration.

**Key Coverage:**
- Oura API authentication
- Sleep data retrieval
- Readiness score fetching
- Activity data processing
- API error handling

#### 3. test_adapters_workos.py
**Description:** Unit tests for WorkOSAdapter class for PostgreSQL database integration.

**Key Coverage:**
- PostgreSQL connection handling
- AsyncPG integration
- Query execution
- Database error handling
- Connection pooling

#### 4. test_chroma_adapter.py
**Description:** Unit tests for ChromaDB adapter for vector storage operations with semantic search.

**Key Coverage:**
- ChromaDB initialization
- Vector storage operations
- Semantic search functionality
- Batch embedding generation
- Graceful fallback when unavailable

#### 5. test_google_calendar_adapter.py
**Description:** Unit tests for GoogleCalendarAdapter class covering authentication, event CRUD, and error scenarios.

**Key Coverage:**
- Google Calendar authentication flow
- Event creation, reading, updating, deletion
- Conflict detection
- Time-blocking functionality
- OAuth credential management
- Error handling and retries

#### 6. test_memory_integration.py
**Description:** Unit tests for MemorySystem class wrapping Neo4j and ChromaDB adapters with graceful fallback.

**Key Coverage:**
- MemoryResult dataclass
- Unified memory system interface
- Neo4j and ChromaDB integration
- Graceful fallback handling
- Backend availability detection

### LiteLLM/Client Tests

#### 7. test_client.py
**Description:** Unit tests for LiteLLMClient class testing model routing, API integration, caching, and usage tracking.

**Key Coverage:**
- Client initialization
- Model routing logic
- API integration
- Caching functionality
- Usage tracking
- Module-level functions (get_client, init_client)

#### 8. test_litellm_client.py
**Description:** Comprehensive unit tests for LiteLLM client module including all major components.

**Key Coverage:**
- LiteLLMClient class
- UsageTracker functionality
- AsyncUsageWriter
- ComplexityAnalyzer
- ResponseCache
- ModelResponse dataclass

#### 9. test_complexity_analyzer.py
**Description:** Unit tests for ComplexityAnalyzer class testing prompt complexity analysis and model tier routing.

**Key Coverage:**
- Simple vs complex prompt detection
- Complexity scoring algorithm
- Keyword weight calculation
- Token count estimation
- History length impact
- Model tier recommendations

#### 10. test_response_cache.py
**Description:** Unit tests for ResponseCache class with TTL-based response caching.

**Key Coverage:**
- Cache initialization
- TTL-based expiration
- Cache hit/miss logic
- Cache invalidation
- Storage and retrieval

#### 11. test_usage_tracker.py
**Description:** Unit tests for UsageTracker class testing usage tracking, cost calculation, and statistics.

**Key Coverage:**
- Usage recording
- Cost calculation by model
- Statistics aggregation
- Historical usage tracking
- Report generation

#### 12. test_models.py
**Description:** Unit tests for ModelResponse dataclass testing creation and metadata handling.

**Key Coverage:**
- ModelResponse initialization
- Metadata fields
- Dataclass validation

### Neo4j Tests

#### 13. test_neo4j_adapter_backward_compatibility.py
**Description:** Unit tests verifying Neo4j adapter methods work correctly without optional session parameter after session pooling refactor.

**Key Coverage:**
- Backward compatibility validation
- Methods work without session parameter
- Automatic session creation
- No breaking changes in API

#### 14. test_neo4j_edge_cases.py
**Description:** Comprehensive edge case tests for Neo4j adapter methods.

**Key Coverage:**
- Empty filters (empty dict, no filters)
- Null values in optional parameters
- Empty strings vs None handling
- Zero values for integers
- Boundary conditions (min/max values)
- Special character handling
- Mixed edge cases

#### 15. test_neo4j_relationship_validation.py
**Description:** Unit tests for Neo4j relationship type validation ensuring only whitelisted types can be used.

**Key Coverage:**
- Relationship type whitelist validation
- Injection attempt blocking
- Valid relationship type acceptance
- Security validation

#### 16. test_neo4j_security_injection_prevention.py
**Description:** Comprehensive security tests for Neo4j adapter injection prevention through validation and parameterization.

**Key Coverage:**
- WHERE clause injection prevention
- Cypher injection attempts
- Parameterization validation
- Relationship method security
- Edge cases and attack vectors

#### 17. test_neo4j_session_leak_detection.py
**Description:** Unit tests for Neo4j session leak detection and error handling.

**Key Coverage:**
- Session cleanup on errors
- Context manager exception handling
- No session leaks under any circumstances
- Proper resource cleanup

#### 18. test_neo4j_session_pool.py
**Description:** Unit tests for Neo4j session pooling (Neo4jSessionContext) class.

**Key Coverage:**
- Session lifecycle management
- Error handling in sessions
- Transaction batching
- Cleanup verification
- Session reuse

#### 19. test_neo4j_batch_operations.py
**Note:** Also listed in Integration Tests - tests both unit and integration scenarios.

### Core Engine Tests

#### 20. test_briefing_engine.py
**Description:** Unit tests for BriefingEngine core functionality covering data gathering, parsing, and context generation.

**Key Coverage:**
- Data gathering from State files
- Context parsing and generation
- Template rendering (with Jinja2)
- Briefing formatting
- Date handling

#### 21. test_context_manager.py
**Description:** Unit tests for ContextManager testing token estimation and history trimming.

**Key Coverage:**
- Token estimation with tiktoken
- Fallback token estimation
- Message token counting
- History trimming logic
- Context window limits
- Usage reporting

#### 22. test_session_manager.py
**Description:** Unit tests for SessionManager testing message handling and history management.

**Key Coverage:**
- Message addition and token tracking
- Sliding window history (MAX_HISTORY)
- History trimming logic
- Session statistics
- Agent switching
- History clearing
- Session persistence

#### 23. test_memos.py
**Description:** Unit tests for MemOS (Memory Operating System) testing memory operations.

**Key Coverage:**
- MemOS initialization with/without backends
- MemoryResult dataclass
- remember() operation
- recall() operation
- relate() operation
- reflect() operation
- get_entity_context()
- health_check()
- Graceful fallback when backends unavailable

### Routing and Command Tests

#### 24. test_command_handlers.py
**Description:** Unit tests for Command Handlers testing each handler module in isolation with mocked dependencies.

**Key Coverage:**
- AgentHandler, SessionHandler, StateHandler
- MemoryHandler, AnalyticsHandler, ModelHandler
- CoreHandler
- CommandAction and CommandResult
- Error handling and output formatting

#### 25. test_command_router.py
**Description:** Unit tests for CommandRouter testing command routing, execution, and handlers.

**Key Coverage:**
- Command routing logic
- Command execution
- Handler integration
- Error handling
- Output formatting

#### 26. test_routing.py
**Description:** Unit tests for Routing modules testing PersonaRouter and CommandRegistry.

**Key Coverage:**
- PersonaRouter agent detection
- CommandRegistry registration
- Routing logic validation
- Agent and trigger matching

#### 27. test_intent_matcher.py
**Description:** Unit tests for KeywordMatcher class for efficient intent detection with pre-compiled regex patterns.

**Key Coverage:**
- Keyword matching with regex
- Priority levels (high, medium, low)
- Pre-compiled pattern efficiency
- Word boundary matching
- MatchResult dataclass

#### 28. test_thanos_orchestrator.py
**Description:** Integration tests for ThanosOrchestrator's find_agent method with optimized KeywordMatcher.

**Key Coverage:**
- Agent routing (ops, coach, strategy, health)
- Keyword matching at all priority levels
- Trigger phrase matching
- Edge cases (empty strings, special characters)
- Multi-keyword scenarios
- Fallback behavior

### Message and Error Handling Tests

#### 29. test_message_handler.py
**Description:** Unit tests for MessageHandler testing streaming, retry logic, and error handling.

**Key Coverage:**
- Message streaming
- Retry logic with exponential backoff
- Error handling
- Token tracking
- Rate limit handling

#### 30. test_error_logger.py
**Description:** Unit tests for error logging, warning logging, and log rotation functionality.

**Key Coverage:**
- Error logging
- Warning logging
- Log rotation (size-based)
- Log file management
- Max backups enforcement

#### 31. test_retry_middleware.py
**Description:** Unit tests for RetryMiddleware testing retry logic and error handling.

**Key Coverage:**
- Successful operation on first attempt
- Exponential backoff calculation
- Retry on specific errors
- Callback invocation
- Max retries exhaustion
- Different error types

### UI and CLI Tests

#### 32. test_spinner.py
**Description:** Unit tests for spinner utilities covering TTY detection, context manager lifecycle, and error handling.

**Key Coverage:**
- TTY detection and behavior
- Context manager lifecycle
- Error handling during operation
- Success/failure indicators
- Manual start/stop control
- Text update functionality
- Factory functions
- Graceful fallback when yaspin unavailable

#### 33. test_thanos_cli.py
**Description:** Unit tests for thanos.py CLI entry point covering command routing and interface.

**Key Coverage:**
- Command shortcuts mapping (daily → pa:daily)
- Natural language detection
- System command routing
- Interactive mode launch
- Chat and agent commands
- Usage, agents, commands display
- Help display

### Backward Compatibility Tests

#### 34. test_backward_compatibility.py
**Description:** Backward compatibility tests validating KeywordMatcher implementation preserves core routing behavior.

**Key Coverage:**
- Correct agent selection for typical messages
- Word boundary matching validation
- Fallback behavior for edge cases
- Intentional behavior improvements documentation

---

## Benchmarks (tests/benchmarks/)

### 1. bench_comparison.py
**Description:** Benchmark comparing old O(n*m) implementation vs new O(m) regex-based implementation.

**Key Coverage:**
- Performance comparison of old vs new matching
- Nested loops vs pre-compiled regex
- 92 keywords across 4 agents benchmark
- Iteration timing and statistics

### 2. bench_intent_detection.py
**Description:** Benchmark measuring find_agent intent detection performance with optimized KeywordMatcher.

**Key Coverage:**
- find_agent method performance
- Pre-compiled regex patterns (O(m))
- Single pass finditer() efficiency
- Word boundary match performance

### 3. bench_matcher_comparison.py
**Description:** Benchmark comparing Regex vs Trie-based keyword matching approaches.

**Key Coverage:**
- KeywordMatcher (Regex) performance
- TrieKeywordMatcher (Aho-Corasick) performance
- O(m) vs O(m + z) complexity comparison

### 4. benchmark_usage_tracker.py
**Description:** Performance benchmark comparing synchronous vs async file I/O for UsageTracker.

**Key Coverage:**
- Latency of record() calls (sync vs async)
- Impact on streaming response
- Throughput for high-frequency calls
- I/O operation count
- Target: <1ms blocking time

### 5. test_neo4j_session_performance.py
**Description:** Performance benchmarks for Neo4j session pooling implementation.

**Key Coverage:**
- Session creation overhead (before pooling)
- Session reuse overhead (after pooling)
- Multi-operation scenario improvements
- Batch operation performance
- Throughput measurements

---

## Supporting Files

### 1. conftest.py
**Location:** `tests/conftest.py`
**Description:** Main pytest configuration and fixtures for all tests.

**Provides:**
- Common test fixtures
- Mock Anthropic client
- Temporary directories
- Test utilities

### 2. conftest_mcp.py
**Location:** `tests/conftest_mcp.py`
**Description:** MCP-specific pytest fixtures for MCP-related tests.

**Provides:**
- MCP configuration fixtures
- Sample server configurations
- Transport configuration (stdio, SSE)
- Mock MCP responses

### 3. fixtures/calendar_fixtures.py
**Location:** `tests/fixtures/calendar_fixtures.py`
**Description:** Shared fixtures for Google Calendar testing.

**Provides:**
- Mock calendar list data
- Mock credentials data
- Mock event data
- Mock events responses
- Workday event fixtures
- Mock task data

---

## Test Markers

Tests use pytest markers for categorization and selective execution:

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (may require external services)
- `@pytest.mark.slow` - Tests that take longer to execute
- `@pytest.mark.api` - Tests requiring API access
- `@pytest.mark.requires_openai` - Tests requiring OpenAI API key
- `@pytest.mark.requires_google_calendar` - Tests requiring Google Calendar credentials
- `@pytest.mark.asyncio` - Async tests requiring pytest-asyncio

---

## External Dependencies by Test Category

### Tests Requiring Neo4j
- Most tests mock Neo4j, but the following may need a real instance:
  - `tests/integration/test_neo4j_batch_operations.py` (uses mocks but validates real behavior)
  - Benchmark tests in some scenarios

### Tests Requiring OpenAI API
- `tests/integration/test_chroma_adapter_integration.py` (with marker `requires_openai`)

### Tests Requiring Google Calendar API
- `tests/integration/test_calendar_integration.py` (with marker `requires_google_calendar`)

### Tests Requiring ChromaDB
- `tests/integration/test_chroma_adapter_integration.py`
- `tests/unit/test_chroma_adapter.py` (mocked, but validates ChromaDB patterns)

---

## Notes

1. **Total Test Count:** 51 test files (excluding helper scripts like `run_backward_compat_test.py`)
2. **Unit Tests:** 33 files provide fast, isolated testing
3. **Integration Tests:** 7 files test end-to-end workflows
4. **Mocking Strategy:** Most tests use comprehensive mocking to avoid external dependencies
5. **Benchmark Tests:** 5 performance benchmarks validate optimization improvements
6. **Coverage:** Tests cover adapters, engines, routing, CLI, error handling, and core functionality

This inventory was created by analyzing all test files in the `tests/` directory and extracting descriptions from docstrings and test class names.
