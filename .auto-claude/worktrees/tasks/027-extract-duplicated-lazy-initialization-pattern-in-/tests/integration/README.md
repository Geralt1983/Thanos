# Integration Tests

## Overview

This directory contains integration tests that verify end-to-end functionality of Thanos components with real (or realistically mocked) dependencies.

## Test Files

### test_command_router_memory.py

**Purpose:** Integration tests for CommandRouter memory commands (`/memory`, `/recall`, `/remember`)

**Coverage:**
- 30 integration tests across 4 test classes
- Tests lazy initialization of MemOS adapter
- Verifies command execution with real dependencies
- Tests graceful degradation when dependencies unavailable

**Test Classes:**
1. `TestMemoryCommand` (7 tests) - /memory command functionality
2. `TestRecallCommand` (8 tests) - /recall search functionality
3. `TestRememberCommand` (11 tests) - /remember storage functionality
4. `TestLazyInitialization` (4 tests) - Lazy initialization behavior

**Running:**
```bash
./run_integration_tests.sh
```

See `INTEGRATION_TEST_VERIFICATION.md` for detailed test documentation.

## Requirements

- pytest
- pytest-mock
- pytest-asyncio

Install with:
```bash
pip install pytest pytest-mock pytest-asyncio
```

## Integration Test Best Practices

1. **Use realistic mocks:** Mock external dependencies but keep business logic real
2. **Test full workflows:** Test complete user scenarios, not just isolated functions
3. **Verify side effects:** Check that commands produce expected outputs and state changes
4. **Test error scenarios:** Verify graceful degradation and error handling
5. **Use fixtures:** Share setup code across tests with pytest fixtures
6. **Isolate tests:** Each test should be independent and not rely on other tests
7. **Mock external services:** Don't make real API calls in integration tests

## Directory Structure

```
tests/
├── integration/
│   ├── __init__.py
│   ├── README.md                           # This file
│   ├── INTEGRATION_TEST_VERIFICATION.md    # Detailed test documentation
│   └── test_command_router_memory.py       # Memory command integration tests
├── unit/
│   └── test_command_router.py              # Unit tests for CommandRouter
└── conftest.py                              # Shared pytest fixtures
```

## Future Integration Tests

Consider adding integration tests for:
- [ ] WorkOS adapter commands
- [ ] Oura adapter commands
- [ ] AdapterManager unified interface
- [ ] Agent switching and routing
- [ ] Session management and branching
- [ ] Pattern recognition and analytics
- [ ] Full interactive mode workflows
