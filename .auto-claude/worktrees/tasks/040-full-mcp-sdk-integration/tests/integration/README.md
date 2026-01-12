# MCP Integration Tests

This directory contains integration tests for the MCP SDK implementation. These tests validate end-to-end functionality with **real MCP servers**, not mocks.

## Overview

Integration tests cover:

- **WorkOS MCP Server Integration** (`test_mcp_workos.py`)
  - Server connection and initialization
  - Tool discovery and listing
  - Tool execution with real data
  - Error handling
  - Session management
  - Performance benchmarks
  - AdapterManager integration

- **MCP Lifecycle Management** (`test_mcp_lifecycle.py`)
  - Full lifecycle: init → list → call → shutdown
  - Reconnection and error recovery
  - Multiple concurrent servers
  - Connection pooling
  - Health monitoring
  - Performance benchmarks

## Prerequisites

### 1. MCP Python SDK

Ensure MCP SDK is installed:

```bash
pip install mcp>=1.0.0
```

### 2. WorkOS MCP Server

Build the WorkOS MCP server:

```bash
cd mcp-servers/workos-mcp
npm install
npm run build
```

### 3. Database Configuration

Set up database connection:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/lifeos"
# or
export WORKOS_DATABASE_URL="postgresql://user:pass@localhost/lifeos"
```

### 4. Server Path Configuration

Set the server path (if not in default location):

```bash
export WORKOS_MCP_PATH="/path/to/mcp-servers/workos-mcp/dist/index.js"
```

## Running Tests

### Run All Integration Tests

```bash
pytest tests/integration/ -v
```

### Run WorkOS Tests Only

```bash
pytest tests/integration/test_mcp_workos.py -v
```

### Run Lifecycle Tests Only

```bash
pytest tests/integration/test_mcp_lifecycle.py -v
```

### Run with Detailed Logging

```bash
pytest tests/integration/ -v -s --log-cli-level=INFO
```

### Run Performance Benchmarks Only

```bash
pytest tests/integration/ -v -m benchmark
```

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.integration` - All integration tests
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.benchmark` - Performance benchmark tests

### Run Only Benchmarks

```bash
pytest tests/integration/ -v -m benchmark
```

### Skip Benchmarks

```bash
pytest tests/integration/ -v -m "not benchmark"
```

## Test Configuration

### Environment Variables

Required:
- `DATABASE_URL` or `WORKOS_DATABASE_URL` - Database connection string
- `WORKOS_MCP_PATH` - Path to WorkOS MCP server (if not in default location)

Optional:
- `MCP_TEST_TIMEOUT` - Test timeout in seconds (default: 30)
- `MCP_TEST_ITERATIONS` - Number of benchmark iterations (default: varies)

### Test Servers Configuration

Create `tests/integration/test_servers.json` for custom test server configurations:

```json
{
  "servers": [
    {
      "name": "test-server-1",
      "transport": {
        "type": "stdio",
        "command": "node",
        "args": ["${WORKOS_MCP_PATH}"],
        "env": {
          "DATABASE_URL": "${DATABASE_URL}",
          "NODE_ENV": "test"
        }
      },
      "enabled": true,
      "tags": ["test", "primary"]
    }
  ]
}
```

## Test Skipping

Tests will automatically skip when:

1. **MCP SDK Not Available**
   - Skip message: "MCP SDK not available"
   - Solution: Install with `pip install mcp`

2. **WorkOS Server Not Found**
   - Skip message: "WorkOS MCP server not found"
   - Solution: Build server with `cd mcp-servers/workos-mcp && npm run build`

3. **Database Not Configured**
   - Skip message: "Database not configured"
   - Solution: Set `DATABASE_URL` environment variable

4. **Server Not Available**
   - Skip message: "Test server not configured"
   - Solution: Set `WORKOS_MCP_PATH` environment variable

## Expected Results

### Successful Test Run

When all prerequisites are met, you should see:

```
tests/integration/test_mcp_workos.py::TestWorkosMCPConnection::test_bridge_creation PASSED
tests/integration/test_mcp_workos.py::TestWorkosMCPToolDiscovery::test_list_tools PASSED
tests/integration/test_mcp_workos.py::TestWorkosMCPToolExecution::test_call_get_tasks PASSED
...
tests/integration/test_mcp_lifecycle.py::TestMCPLifecycle::test_complete_lifecycle PASSED
tests/integration/test_mcp_lifecycle.py::TestMultipleConcurrentServers::test_multiple_bridges_concurrent PASSED
...

==================== X passed in Y.YYs ====================
```

### Performance Benchmarks

Benchmark tests document performance characteristics:

- **Tool Listing**: <100ms (cached: <10ms)
- **Tool Call**: <1000ms (varies by tool complexity)
- **Initialization**: <500ms
- **Concurrent Operations**: Near-linear scaling

## Troubleshooting

### "MCP SDK not available"

```bash
pip install mcp>=1.0.0
```

### "WorkOS MCP server not found"

```bash
cd mcp-servers/workos-mcp
npm install
npm run build
```

### "Database not configured"

```bash
export DATABASE_URL="postgresql://localhost/lifeos"
```

### Connection Timeouts

Increase timeout or check database connectivity:

```bash
psql $DATABASE_URL -c "SELECT 1"
```

### Server Process Errors

Check server runs manually:

```bash
node $WORKOS_MCP_PATH
# Should wait for MCP protocol messages on stdin
```

### Permission Errors

Ensure executable permissions:

```bash
chmod +x $WORKOS_MCP_PATH
```

## Writing New Integration Tests

### Test Structure

```python
@pytest.mark.asyncio
@pytest.mark.integration
class TestMyIntegration:
    """Test my integration scenario."""

    async def test_my_scenario(self, test_bridge):
        """Test description."""
        # Arrange
        # Act
        result = await test_bridge.call_tool("tool_name", {})
        # Assert
        assert result.success
```

### Using Fixtures

Available fixtures:
- `test_bridge` - Configured test MCP bridge
- `skip_if_mcp_unavailable` - Skip if MCP not available
- `skip_if_server_unavailable` - Skip if server not available
- `workos_bridge` - WorkOS-specific bridge

### Adding Benchmarks

Mark with `@pytest.mark.benchmark`:

```python
@pytest.mark.benchmark
async def test_performance(self, test_bridge):
    """Benchmark performance."""
    import time

    start = time.time()
    await test_bridge.call_tool("tool", {})
    elapsed = time.time() - start

    logger.info(f"Operation took {elapsed*1000:.2f}ms")
```

## Continuous Integration

### GitHub Actions

```yaml
- name: Run Integration Tests
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
    WORKOS_MCP_PATH: ./mcp-servers/workos-mcp/dist/index.js
  run: |
    pytest tests/integration/ -v --junitxml=results.xml
```

### Skip in CI

Use environment variable to skip when servers unavailable:

```python
@pytest.mark.skipif(
    os.getenv("CI") == "true" and not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests disabled in CI"
)
```

## Coverage

Generate coverage report:

```bash
pytest tests/integration/ --cov=Tools.adapters --cov-report=html
```

View report:

```bash
open htmlcov/index.html
```

## Support

For issues with integration tests:

1. Check prerequisites are met
2. Review test logs with `-v -s --log-cli-level=DEBUG`
3. Test server manually outside pytest
4. Check database connectivity
5. Consult docs/mcp-integration-guide.md

## Acceptance Criteria

These integration tests fulfill the following acceptance criteria for subtask 5.4:

- ✅ **Integration test with WorkOS MCP server**
  - Comprehensive test suite in `test_mcp_workos.py`
  - Tests connection, tool discovery, execution, errors, performance

- ✅ **Test full lifecycle (init, list tools, call tool, shutdown)**
  - `TestMCPLifecycle::test_complete_lifecycle` in `test_mcp_lifecycle.py`
  - Tests all lifecycle phases with assertions

- ✅ **Test reconnection and error recovery**
  - `TestMCPReconnection` class in `test_mcp_lifecycle.py`
  - Tests reconnection after close, connection errors, timeouts

- ✅ **Test with multiple concurrent servers**
  - `TestMultipleConcurrentServers` class in `test_mcp_lifecycle.py`
  - Tests sequential and concurrent multi-server usage

- ✅ **Performance benchmarks documented**
  - `TestWorkosMCPPerformance` in `test_mcp_workos.py`
  - `TestMCPLifecyclePerformance` in `test_mcp_lifecycle.py`
  - Results logged and assertions on acceptable performance
