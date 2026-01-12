# MCP Component Unit Tests

Comprehensive test suite for MCP (Model Context Protocol) integration components.

## Test Coverage

### test_mcp_errors.py
Tests for MCP error handling system:
- Custom exception hierarchy (MCPError and subclasses)
- Error context and metadata
- Tool-related errors
- Configuration errors
- Availability errors
- Error classification and recovery strategies
- Error logging and formatting
- Error chaining and causation

### test_mcp_discovery.py
Tests for MCP server discovery mechanism:
- Server discovery from multiple sources
- Configuration file loading (.mcp.json, .claude.json)
- Configuration merging and precedence
- Server filtering (disabled, tags)
- Nested directory config discovery
- Environment variable interpolation
- Error handling (missing files, malformed JSON)
- Edge cases and permission handling

### test_mcp_bridge.py
Tests for MCPBridge adapter:
- Bridge initialization with different transports
- Transport creation (stdio, SSE)
- Session lifecycle management
- Tool listing and caching
- Tool execution and result parsing
- Capability negotiation and checking
- Error handling and recovery
- Health checks
- Performance metrics and logging
- BaseAdapter interface compliance
- Concurrent operations

### conftest.py
Shared test fixtures and utilities:
- Mock MCP SDK components
- Test configuration files
- Sample server configurations
- Tool definitions and test data
- Error scenario fixtures
- Async testing utilities

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run specific test file:
```bash
pytest tests/test_mcp_bridge.py
```

### Run with coverage:
```bash
pytest tests/ --cov=Tools/adapters --cov-report=html
```

### Run with verbose output:
```bash
pytest tests/ -v
```

### Run specific test class:
```bash
pytest tests/test_mcp_bridge.py::TestToolCalling -v
```

### Run specific test:
```bash
pytest tests/test_mcp_bridge.py::TestToolCalling::test_call_tool_success -v
```

## Test Requirements

These tests require:
- pytest>=7.0.0
- pytest-asyncio>=0.21.0 (for async tests)
- pytest-mock>=3.10.0 (for mocking)

Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

## Test Design Principles

### Mock MCP Servers
Tests use mock MCP servers to avoid external dependencies. This ensures:
- Fast test execution
- Reliable and deterministic results
- No network dependencies
- Ability to test error scenarios

### Comprehensive Coverage
Tests cover:
- Happy path scenarios
- Error conditions
- Edge cases
- Concurrent operations
- Performance characteristics
- Interface compliance

### Isolation
Each test is isolated:
- No shared state between tests
- Temporary directories for file operations
- Mock objects reset between tests
- Independent async event loops

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_mcp_bridge.py       # MCPBridge tests (~300 lines)
├── test_mcp_discovery.py    # Discovery tests (~400 lines)
├── test_mcp_errors.py       # Error handling tests (~250 lines)
└── README.md                # This file
```

## Coverage Goals

Target coverage: > 80% for MCP modules
- mcp_bridge.py
- mcp_discovery.py
- mcp_errors.py
- mcp_config.py
- mcp_capabilities.py

## Continuous Integration

These tests are designed to run in CI environments:
- No external service dependencies
- Fast execution (< 5 seconds)
- Clear failure messages
- Comprehensive reporting

## Adding New Tests

When adding new tests:

1. **Use existing fixtures** from conftest.py
2. **Follow naming conventions**: test_<feature>_<scenario>
3. **Include docstrings** explaining what is being tested
4. **Test both success and failure** cases
5. **Mock external dependencies** (MCP SDK, file system, etc.)
6. **Use appropriate markers** (@pytest.mark.asyncio for async tests)

Example:
```python
@pytest.mark.asyncio
async def test_new_feature_success(self, mock_client_session):
    """Test successful execution of new feature."""
    # Arrange
    session = mock_client_session

    # Act
    result = await session.new_feature()

    # Assert
    assert result is not None
```

## Debugging Tests

### Run with print statements:
```bash
pytest tests/ -s
```

### Run with pdb debugger:
```bash
pytest tests/ --pdb
```

### Show local variables on failure:
```bash
pytest tests/ -l
```

### Run only failed tests from last run:
```bash
pytest tests/ --lf
```

## Test Performance

Typical test execution times:
- test_mcp_errors.py: < 1s
- test_mcp_discovery.py: < 2s
- test_mcp_bridge.py: < 2s
- Total: < 5s

## Known Limitations

1. **Sparse Worktree**: Tests are designed to work in sparse worktrees where MCP implementation files may not be checked out. Tests validate interfaces and behavior rather than importing actual modules.

2. **Mock-based**: Tests use mocks rather than real MCP servers. Integration tests with real servers are in `tests/integration/`.

3. **Platform-specific**: Some tests (e.g., file permissions) may behave differently on Windows vs Unix-like systems.

## Future Improvements

- [ ] Add integration tests with real MCP servers
- [ ] Add performance benchmarks
- [ ] Add load testing for concurrent operations
- [ ] Add mutation testing to verify test quality
- [ ] Add property-based testing with hypothesis
