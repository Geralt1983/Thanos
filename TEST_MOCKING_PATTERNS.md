# Test Mocking Patterns Guide

**Documentation of common mocking patterns used across the Thanos test suite**

This document catalogs the mocking strategies, fixtures, and patterns used throughout the test infrastructure to help developers write consistent, maintainable tests.

## Table of Contents

1. [Overview](#overview)
2. [Shared Fixtures (conftest.py)](#shared-fixtures-conftestpy)
3. [MCP Fixtures (conftest_mcp.py)](#mcp-fixtures-conftest_mcppy)
4. [Calendar Test Fixtures](#calendar-test-fixtures)
5. [unittest.mock Patterns](#unittestmock-patterns)
6. [pytest-mock Patterns](#pytest-mock-patterns)
7. [Async Test Patterns](#async-test-patterns)
8. [Database Mocking Patterns](#database-mocking-patterns)
9. [Temporary Directory Patterns](#temporary-directory-patterns)
10. [Environment Variable Mocking](#environment-variable-mocking)
11. [Module-level Import Mocking](#module-level-import-mocking)
12. [Best Practices](#best-practices)

---

## Overview

The Thanos test suite uses a combination of:
- **pytest fixtures** for reusable test components
- **unittest.mock** for mocking objects and methods
- **pytest-mock** (mocker fixture) for pytest-style mocking
- **AsyncMock** for async function mocking
- **sys.modules** mocking for unavailable dependencies
- **Temporary directories** for isolated test storage

**Philosophy:** Tests should be isolated, fast, and not require external services by default. External API calls are mocked unless specifically testing integration with those services.

---

## Shared Fixtures (conftest.py)

Located in `tests/conftest.py`, these fixtures are available to all tests.

### Core Fixtures

#### `project_root_path`
Returns the project root directory path.

```python
def test_something(project_root_path):
    config_path = project_root_path / "config.json"
```

#### `mock_anthropic_response`
Provides a standard Anthropic API response dictionary.

```python
def test_api_response(mock_anthropic_response):
    assert mock_anthropic_response["model"] == "claude-sonnet-4-5-20250929"
    assert mock_anthropic_response["role"] == "assistant"
```

#### `mock_anthropic_client`
Returns a fully mocked Anthropic client with pre-configured responses.

**Uses pytest-mock's `mocker` fixture internally.**

```python
def test_client(mock_anthropic_client):
    # Client already configured with mock responses
    response = mock_anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        messages=[{"role": "user", "content": "Test"}]
    )
    assert response.content[0].text == "Test response"
```

#### `sample_messages`
Provides a list of sample conversation messages.

```python
def test_conversation(sample_messages):
    assert len(sample_messages) == 4
    assert sample_messages[0]["role"] == "user"
```

#### `temp_config_dir`
Creates a temporary configuration directory using pytest's `tmp_path`.

```python
def test_config(temp_config_dir):
    config_file = temp_config_dir / "settings.json"
    config_file.write_text('{"key": "value"}')
```

#### `mock_api_config`
Creates a mock API configuration JSON file in a temporary directory.

```python
def test_api_setup(mock_api_config):
    # mock_api_config is a Path object pointing to api.json
    import json
    config = json.loads(mock_api_config.read_text())
    assert "anthropic_api_key" in config
```

### MCP-Specific Fixtures

#### `mock_server_config`
Creates a mock MCP server configuration object.

```python
def test_mcp_server(mock_server_config):
    assert mock_server_config.name == "test-server"
    assert mock_server_config.command == "python"
```

#### `mock_mcp_client`
Creates a mock MCP client with AsyncMock for async methods.

```python
@pytest.mark.asyncio
async def test_mcp_tools(mock_mcp_client):
    tools = await mock_mcp_client.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "test_tool"
```

#### `mock_mcp_discovery`
Creates a mock MCP server configuration file in JSON format.

```python
def test_discovery(mock_mcp_discovery):
    import json
    with open(mock_mcp_discovery) as f:
        config = json.load(f)
    assert "mcpServers" in config
```

---

## MCP Fixtures (conftest_mcp.py)

Located in `tests/conftest_mcp.py`, these provide comprehensive MCP testing infrastructure.

### Event Loop Configuration

#### `event_loop`
Session-scoped event loop for async tests.

```python
@pytest.mark.asyncio
async def test_async_operation(event_loop):
    result = await some_async_function()
    assert result is not None
```

### Mock MCP SDK Components

#### `mock_client_session`
Comprehensive mock of MCP ClientSession with pre-configured responses.

```python
@pytest.mark.asyncio
async def test_session(mock_client_session):
    init_result = await mock_client_session.initialize()
    assert init_result.protocolVersion == "2024-11-05"

    tools_result = await mock_client_session.list_tools()
    assert len(tools_result.tools) == 1

    tool_result = await mock_client_session.call_tool("test_tool", {"arg1": "value"})
    assert not tool_result.isError
```

#### `mock_transport`
Mock transport for MCP communication.

```python
@pytest.mark.asyncio
async def test_transport(mock_transport):
    async for read_stream, write_stream in mock_transport.connect():
        # Test communication
        pass
```

### Test Configuration Files

#### `temp_dir`
Function-scoped temporary directory.

```python
def test_files(temp_dir):
    test_file = temp_dir / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()
```

#### `sample_mcp_json`
Creates a complete `.mcp.json` configuration file.

```python
def test_mcp_config(sample_mcp_json):
    import json
    config = json.loads(sample_mcp_json.read_text())
    assert "test-server" in config["mcpServers"]
    assert config["mcpServers"]["test-server"]["enabled"] is True
```

#### `nested_project_structure`
Creates a nested directory structure for testing config discovery.

```python
def test_config_discovery(nested_project_structure):
    root = nested_project_structure["root"]
    current = nested_project_structure["current"]
    assert current.exists()
```

### Sample Data Fixtures

#### `sample_tools`
Provides sample tool definitions in Thanos format.

```python
def test_tool_schema(sample_tools):
    assert len(sample_tools) == 2
    assert sample_tools[0]["name"] == "get_tasks"
    assert "parameters" in sample_tools[0]
```

#### `error_scenarios`
Common error scenarios for testing error handling.

```python
def test_error_handling(error_scenarios):
    timeout_error = error_scenarios["timeout_error"]
    assert timeout_error["retryable"] is True
    assert timeout_error["timeout_seconds"] == 30.0
```

### Helper Functions

#### `create_mock_mcp_server(name, tools)`
Factory function for creating mock MCP servers.

```python
def test_custom_server():
    tools = [{"name": "custom_tool", "description": "Custom tool"}]
    server = create_mock_mcp_server("custom-server", tools)
    assert server.name == "custom-server"
```

---

## Calendar Test Fixtures

Located in `tests/fixtures/calendar_fixtures.py`, these provide realistic Google Calendar test data.

### Helper Functions

All calendar fixtures are **functions, not pytest fixtures**. They return mock data.

#### `get_mock_credentials_data()`
Returns mock OAuth credentials.

```python
def test_auth():
    creds = get_mock_credentials_data()
    assert creds["token"] == "mock_access_token_abc123"
    assert "scopes" in creds
```

#### `get_mock_event(...)`
Creates a mock calendar event with flexible parameters.

```python
def test_event_creation():
    from datetime import datetime

    event = get_mock_event(
        summary="Team Meeting",
        start_time=datetime.now(),
        duration_minutes=60,
        event_id="meeting_123"
    )
    assert event["summary"] == "Team Meeting"
    assert event["status"] == "confirmed"
```

#### `get_workday_events()`
Returns a realistic set of workday events.

```python
def test_schedule():
    events = get_workday_events()
    assert len(events) == 5
    assert events[0]["summary"] == "Morning Standup"
```

#### Other Helpers
- `get_mock_calendar()` - Mock calendar object
- `get_mock_calendar_list()` - List of calendars
- `get_mock_events_response(events)` - API response wrapper
- `get_all_day_event()` - All-day event
- `get_recurring_event()` - Recurring event
- `get_conflicting_event()` - Event for conflict testing
- `get_mock_filter_config()` - Calendar filter configuration
- `get_mock_http_error(status, reason)` - HTTP error response

---

## unittest.mock Patterns

The primary mocking library used across tests.

### Basic Mock Objects

```python
from unittest.mock import Mock, MagicMock, AsyncMock

def test_basic_mock():
    # Create a simple mock
    mock_obj = Mock()
    mock_obj.method.return_value = "result"

    assert mock_obj.method() == "result"
    mock_obj.method.assert_called_once()
```

### Mock with Specifications

```python
def test_mock_with_spec():
    # Mock that matches an interface
    mock_client = Mock(spec=["connect", "disconnect", "send"])
    mock_client.connect.return_value = True

    # This would raise AttributeError:
    # mock_client.nonexistent_method()
```

### MagicMock for Magic Methods

```python
def test_magic_mock():
    # Use MagicMock when mocking __len__, __iter__, etc.
    mock_list = MagicMock()
    mock_list.__len__.return_value = 5
    mock_list.__iter__.return_value = iter([1, 2, 3])

    assert len(mock_list) == 5
    assert list(mock_list) == [1, 2, 3]
```

### AsyncMock for Async Methods

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_mock():
    mock_service = Mock()
    mock_service.async_method = AsyncMock(return_value="async result")

    result = await mock_service.async_method()
    assert result == "async result"
    mock_service.async_method.assert_awaited_once()
```

### Patch Decorator

```python
from unittest.mock import patch

@patch('module.external_api_call')
def test_with_patch(mock_api):
    mock_api.return_value = {"status": "ok"}

    # Code that calls module.external_api_call
    result = my_function()

    mock_api.assert_called_once()
    assert result is not None
```

### Patch Context Manager

```python
def test_with_patch_context():
    with patch('module.external_api_call') as mock_api:
        mock_api.return_value = {"status": "ok"}

        result = my_function()

        assert result is not None
```

### Patch Object

```python
from unittest.mock import patch

def test_patch_object():
    obj = MyClass()

    with patch.object(obj, 'method', return_value="mocked"):
        result = obj.method()
        assert result == "mocked"
```

### Mock Multiple Attributes

```python
def test_mock_attributes():
    mock_client = Mock()
    mock_client.status = "connected"
    mock_client.get_status.return_value = "connected"
    mock_client.disconnect.return_value = None

    assert mock_client.status == "connected"
    assert mock_client.get_status() == "connected"
```

### Side Effects

```python
def test_side_effects():
    mock = Mock()

    # Different return values for successive calls
    mock.get_next.side_effect = [1, 2, 3, StopIteration]

    assert mock.get_next() == 1
    assert mock.get_next() == 2
    assert mock.get_next() == 3
    with pytest.raises(StopIteration):
        mock.get_next()
```

### Verify Mock Calls

```python
from unittest.mock import call

def test_verify_calls():
    mock = Mock()

    mock.method("arg1", kwarg="value1")
    mock.method("arg2", kwarg="value2")

    # Verify specific call
    mock.method.assert_any_call("arg1", kwarg="value1")

    # Verify all calls
    assert mock.method.call_count == 2
    assert mock.method.call_args_list == [
        call("arg1", kwarg="value1"),
        call("arg2", kwarg="value2")
    ]
```

---

## pytest-mock Patterns

The `mocker` fixture provides pytest-style mocking (pytest-mock plugin).

**Note:** Used sparingly in this codebase. Most tests use unittest.mock directly.

### Basic Usage

```python
def test_with_mocker(mocker):
    # Create a mock
    mock_obj = mocker.Mock()
    mock_obj.method.return_value = "result"

    assert mock_obj.method() == "result"
```

### Patch with mocker

```python
def test_mocker_patch(mocker):
    mock_api = mocker.patch('module.external_api_call')
    mock_api.return_value = {"status": "ok"}

    result = my_function()
    assert result is not None
```

### AsyncMock with mocker

```python
@pytest.mark.asyncio
async def test_async_mocker(mocker):
    mock_service = mocker.AsyncMock()
    mock_service.fetch_data.return_value = {"data": "value"}

    result = await mock_service.fetch_data()
    assert result["data"] == "value"
```

---

## Async Test Patterns

Testing asynchronous code requires special handling.

### Basic Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

### Async Mock Methods

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_mock():
    mock_client = Mock()
    mock_client.fetch = AsyncMock(return_value="data")

    result = await mock_client.fetch()
    assert result == "data"
    mock_client.fetch.assert_awaited_once()
```

### Event Loop Fixture

```python
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

### Async Context Managers

```python
@pytest.mark.asyncio
async def test_async_context_manager():
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    async with mock_context as ctx:
        assert ctx is mock_context

    mock_context.__aenter__.assert_awaited_once()
    mock_context.__aexit__.assert_awaited_once()
```

### Testing Async Generators

```python
@pytest.mark.asyncio
async def test_async_generator():
    async def mock_generator():
        yield 1
        yield 2
        yield 3

    results = []
    async for value in mock_generator():
        results.append(value)

    assert results == [1, 2, 3]
```

---

## Database Mocking Patterns

Testing database interactions without requiring actual database servers.

### Neo4j Driver Mocking

Mock the neo4j module before importing the adapter:

```python
import sys
from unittest.mock import MagicMock

# Mock neo4j before importing the adapter
mock_neo4j = MagicMock()
sys.modules['neo4j'] = mock_neo4j

# Now import the adapter
from Tools.adapters.neo4j_adapter import Neo4jSessionContext

def test_neo4j_session():
    mock_adapter = Mock()
    mock_adapter._driver = Mock()

    context = Neo4jSessionContext(mock_adapter)
    assert context._database == "neo4j"
```

### Mock Database Session

```python
@pytest.mark.asyncio
async def test_db_session():
    mock_session = Mock()
    mock_session.run.return_value = Mock(single=Mock(return_value={"result": "data"}))

    mock_adapter = Mock()
    mock_adapter._driver = Mock()
    mock_adapter._driver.session = Mock(return_value=mock_session)

    context = Neo4jSessionContext(mock_adapter)
    async with context as session:
        result = session.run("MATCH (n) RETURN n")
        data = result.single()
        assert data["result"] == "data"
```

### ChromaDB Mocking

```python
def test_chroma_adapter():
    with patch('Tools.adapters.chroma_adapter.CHROMADB_AVAILABLE', True):
        mock_client = MagicMock()

        with patch('chromadb.PersistentClient', return_value=mock_client):
            from Tools.adapters.chroma_adapter import ChromaAdapter
            adapter = ChromaAdapter(persist_directory="/tmp/test")

            assert adapter._client is mock_client
```

### PostgreSQL/asyncpg Mocking

```python
import sys
from unittest.mock import Mock

# Mock asyncpg module
sys.modules['asyncpg'] = Mock()

from Tools.adapters.workos_adapter import WorkOSAdapter

def test_workos_adapter():
    adapter = WorkOSAdapter()
    assert adapter is not None
```

---

## Temporary Directory Patterns

Creating isolated temporary storage for tests.

### Using pytest tmp_path

```python
def test_with_tmp_path(tmp_path):
    """pytest's built-in tmp_path fixture."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    assert test_file.exists()
    assert test_file.read_text() == "content"
    # Automatic cleanup after test
```

### Using tempfile Module

```python
import tempfile
import shutil

@pytest.fixture
def temp_dir():
    """Create a temporary directory with manual cleanup."""
    temp_dir = tempfile.mkdtemp(prefix="test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_with_tempfile(temp_dir):
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()
```

### Temporary Config Files

```python
@pytest.fixture
def mock_config_file(tmp_path):
    """Create a temporary configuration file."""
    import json

    config = {
        "setting1": "value1",
        "setting2": "value2"
    }

    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config, indent=2))

    return config_file
```

### ChromaDB Integration Test Pattern

```python
@pytest.fixture(scope="function")
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB storage."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_integration_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture(scope="function")
def chroma_client(temp_chroma_dir):
    """Create a ChromaDB client with temporary storage."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")

    client = chromadb.PersistentClient(path=temp_chroma_dir)
    yield client
    # Client cleanup happens when temp_chroma_dir is removed
```

---

## Environment Variable Mocking

Testing code that depends on environment variables.

### Using monkeypatch

```python
def test_env_variables(monkeypatch):
    """pytest's built-in monkeypatch fixture."""
    monkeypatch.setenv("API_KEY", "test_key_123")
    monkeypatch.setenv("DEBUG_MODE", "true")

    import os
    assert os.getenv("API_KEY") == "test_key_123"
    assert os.getenv("DEBUG_MODE") == "true"
```

### Multiple Environment Variables

```python
@pytest.fixture
def mock_env_credentials(monkeypatch):
    """Set up mock Google Calendar credentials in environment."""
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:8080/oauth2callback")

def test_credentials(mock_env_credentials):
    import os
    assert os.getenv("GOOGLE_CALENDAR_CLIENT_ID") == "test_client_id"
```

### Deleting Environment Variables

```python
def test_missing_env_var(monkeypatch):
    # Ensure env var is not set
    monkeypatch.delenv("OPTIONAL_API_KEY", raising=False)

    import os
    assert os.getenv("OPTIONAL_API_KEY") is None
```

### Using patch.dict

```python
from unittest.mock import patch
import os

def test_env_with_patch():
    with patch.dict(os.environ, {"API_KEY": "test_key"}):
        assert os.getenv("API_KEY") == "test_key"

    # Env var is restored after context
    assert os.getenv("API_KEY") != "test_key"
```

---

## Module-level Import Mocking

Mocking modules that may not be installed or should not be imported during tests.

### Mocking Unavailable Dependencies

```python
import sys
from unittest.mock import Mock

# Mock Google API modules before importing
sys.modules["google.auth.transport.requests"] = Mock()
sys.modules["google.oauth2.credentials"] = Mock()
sys.modules["google_auth_oauthlib.flow"] = Mock()
sys.modules["googleapiclient.discovery"] = Mock()

# Now can safely import code that depends on these
from Tools.adapters.google_calendar import GoogleCalendarAdapter
```

### Creating Mock Exception Classes

```python
import sys
from unittest.mock import Mock

# Create a mock HttpError exception class
class HttpError(Exception):
    """Mock HttpError for testing."""
    def __init__(self, resp, content):
        self.resp = resp
        self.content = content
        super().__init__(f"HTTP {resp.status}")

# Add to mock module
mock_errors = Mock()
mock_errors.HttpError = HttpError
sys.modules["googleapiclient.errors"] = mock_errors
```

### Conditional Imports in Tests

```python
# Import ChromaDB if available
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Skip tests if not available
@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="ChromaDB not installed")
def test_chroma_feature():
    # Test code here
    pass
```

### Using pytest.skip in Fixtures

```python
@pytest.fixture
def chroma_client():
    """Create a ChromaDB client."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")

    import chromadb
    client = chromadb.Client()
    yield client
```

---

## Best Practices

### 1. Prefer Fixtures Over Repetitive Setup

**Bad:**
```python
def test_feature_a():
    mock_client = Mock()
    mock_client.method.return_value = "result"
    # test code

def test_feature_b():
    mock_client = Mock()
    mock_client.method.return_value = "result"
    # test code
```

**Good:**
```python
@pytest.fixture
def mock_client():
    client = Mock()
    client.method.return_value = "result"
    return client

def test_feature_a(mock_client):
    # test code

def test_feature_b(mock_client):
    # test code
```

### 2. Use Specific Assertions

**Bad:**
```python
def test_mock_called(mock_api):
    my_function()
    assert mock_api.call_count > 0
```

**Good:**
```python
def test_mock_called(mock_api):
    my_function()
    mock_api.assert_called_once_with(expected_arg="value")
```

### 3. Mock at the Right Level

Mock at the boundary of your code, not deep inside:

**Bad:** Mocking internal implementation details
```python
@patch('module.internal_helper_function')
def test_feature(mock_helper):
    # Testing implementation, not behavior
    pass
```

**Good:** Mocking external dependencies
```python
@patch('module.external_api_call')
def test_feature(mock_api):
    # Testing behavior with mocked external dependency
    pass
```

### 4. Use AsyncMock for Async Code

**Bad:**
```python
mock_client.fetch = Mock(return_value="data")
# This will fail - can't await a regular Mock
await mock_client.fetch()
```

**Good:**
```python
mock_client.fetch = AsyncMock(return_value="data")
await mock_client.fetch()
mock_client.fetch.assert_awaited_once()
```

### 5. Clean Up Resources

**Bad:**
```python
def test_with_file():
    temp_file = "/tmp/test.txt"
    Path(temp_file).write_text("test")
    # File persists after test
```

**Good:**
```python
def test_with_file(tmp_path):
    temp_file = tmp_path / "test.txt"
    temp_file.write_text("test")
    # Automatic cleanup
```

### 6. Use Fixture Scopes Appropriately

```python
@pytest.fixture(scope="function")  # Default: new instance per test
def function_scoped():
    return create_resource()

@pytest.fixture(scope="module")  # Shared across module tests
def module_scoped():
    return create_expensive_resource()

@pytest.fixture(scope="session")  # Shared across entire test session
def session_scoped():
    return create_very_expensive_resource()
```

### 7. Skip Tests Gracefully

```python
@pytest.mark.skipif(not HAS_API_KEY, reason="API key not available")
def test_api_integration():
    # Test that requires API key
    pass

# Or in a fixture
@pytest.fixture
def api_client():
    if not HAS_API_KEY:
        pytest.skip("API key not available")
    return create_client()
```

### 8. Use Markers for Test Organization

```python
@pytest.mark.unit
def test_unit_logic():
    pass

@pytest.mark.integration
def test_integration_flow():
    pass

@pytest.mark.asyncio
async def test_async_operation():
    pass

@pytest.mark.slow
def test_expensive_operation():
    pass
```

### 9. Document Complex Mocks

```python
@pytest.fixture
def mock_complex_client():
    """
    Create a mock client with realistic behavior.

    The client simulates:
    - Initial connection with retry logic
    - Rate limiting (3 requests per second)
    - Exponential backoff on errors
    """
    client = Mock()
    # Setup complex mock behavior
    return client
```

### 10. Verify Mock Behavior

```python
def test_with_verification(mock_api):
    result = my_function(arg="value")

    # Verify the mock was called correctly
    mock_api.assert_called_once_with(arg="value")

    # Verify return value was used
    assert result == expected_result

    # Verify side effects
    assert some_state_changed
```

---

## Quick Reference

### Common Imports

```python
# unittest.mock
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call, mock_open

# pytest
import pytest

# Async testing
import asyncio

# Temporary files
import tempfile
from pathlib import Path
```

### Common Patterns

```python
# Basic mock
mock = Mock()
mock.method.return_value = "value"

# Async mock
mock.async_method = AsyncMock(return_value="value")

# Patch decorator
@patch('module.function')
def test(mock_func):
    pass

# Patch context
with patch('module.function') as mock_func:
    pass

# Temp directory
def test(tmp_path):
    file = tmp_path / "test.txt"

# Environment variable
def test(monkeypatch):
    monkeypatch.setenv("KEY", "value")

# Async test
@pytest.mark.asyncio
async def test():
    result = await async_function()
```

---

## Summary

The Thanos test suite employs a comprehensive mocking strategy that:

1. **Isolates tests** - External dependencies are mocked by default
2. **Provides reusable fixtures** - Common mocks in conftest.py files
3. **Supports async testing** - AsyncMock and event loop fixtures
4. **Handles missing dependencies gracefully** - sys.modules mocking and pytest.skip
5. **Uses temporary storage** - tmp_path and tempfile for file operations
6. **Maintains consistency** - Standard patterns across all tests

**Key Takeaway:** When writing new tests, check conftest.py files first for existing fixtures, follow established patterns, and mock external dependencies at the boundary of your code.

---

**Related Documentation:**
- [TEST_INVENTORY.md](TEST_INVENTORY.md) - Complete catalog of all test files
- [TEST_DEPENDENCIES.md](TEST_DEPENDENCIES.md) - External dependencies and setup
- [pytest.ini](pytest.ini) - Test configuration and markers
- [conftest.py](tests/conftest.py) - Shared test fixtures
- [conftest_mcp.py](tests/conftest_mcp.py) - MCP-specific fixtures
