# Test Dependencies and Requirements

This document identifies all external dependencies (databases, APIs, services) required by different test categories in the Thanos project.

**Last Updated:** 2026-01-12

---

## Overview

The Thanos test suite is designed with graceful fallbacks to allow most tests to run without external dependencies. Tests are categorized using pytest markers, and external dependencies are required only for specific integration tests.

**Testing Philosophy:**
- **Unit tests:** Mock all external dependencies (can run offline)
- **Integration tests (default):** Mock external APIs, may use temporary local services
- **Integration tests (marked):** Require real external services/APIs

---

## Quick Reference

| Dependency | Required By | Marker | Environment Variable | Can Run Without? |
|------------|-------------|--------|---------------------|------------------|
| **Neo4j** | Pattern recognition, memory tests | *(none, mocked)* | - | ✅ Yes (mocked) |
| **ChromaDB** | Vector storage tests | `integration` | - | ✅ Yes (optional) |
| **OpenAI API** | Embedding generation tests | `requires_openai` | `OPENAI_API_KEY` | ✅ Yes (skipped) |
| **Google Calendar API** | Calendar integration tests | `requires_google_calendar` | `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET` | ✅ Yes (skipped) |
| **Anthropic API** | Claude tests | *(mocked)* | `ANTHROPIC_API_KEY` | ✅ Yes (mocked) |
| **Oura Ring API** | Health data tests | *(mocked)* | `OURA_PERSONAL_ACCESS_TOKEN` | ✅ Yes (mocked) |
| **PostgreSQL/WorkOS** | Database adapter tests | *(mocked)* | - | ✅ Yes (mocked) |

---

## Detailed Dependencies by Category

### 1. Neo4j Database

**Used For:** Graph database operations for commitments, patterns, relationships

**Tests Requiring Neo4j:**
- ⚠️ **IMPORTANT:** All Neo4j tests mock the database connection
- No tests require a real Neo4j instance

**Related Test Files:**
- `tests/integration/test_neo4j_batch_operations.py` - Integration tests (mocked)
- `tests/integration/test_pattern_recognition_integration.py` - Pattern storage (mocked)
- `tests/unit/test_neo4j_*.py` - All unit tests (mocked)
- `tests/benchmarks/test_neo4j_session_performance.py` - Performance tests (mocked)

**Mock Strategy:**
```python
# Neo4j is mocked using unittest.mock
sys.modules['neo4j'] = MagicMock()
from Tools.adapters.neo4j_adapter import Neo4jAdapter

adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")
adapter._driver = Mock()  # Mocked driver
```

**Setup Required:** None (fully mocked)

**Skip If Unavailable:** N/A (tests always run with mocks)

---

### 2. ChromaDB

**Used For:** Vector storage, semantic search, embeddings

**Tests Requiring ChromaDB:**

#### Default Integration Tests (ChromaDB optional)
Most tests mock ChromaDB and will run without installation:
- `tests/unit/test_chroma_adapter.py` - All unit tests (fully mocked)
- `tests/unit/test_memory_integration.py` - Memory system tests (mocked)
- `tests/unit/test_memos.py` - MemOS tests (graceful fallback)

#### Real ChromaDB Tests (ChromaDB required)
These tests use actual ChromaDB instances with temporary directories:
- `tests/integration/test_chroma_adapter_integration.py` - Core batch functionality
  - `TestChromaBatchEmbeddingIntegration` - Batch operations (mocked OpenAI)
  - `TestChromaBatchEmbeddingErrorHandling` - Error scenarios (mocked OpenAI)

**Installation:**
```bash
pip install chromadb
```

**Mock Strategy:**
```python
# Tests check CHROMADB_AVAILABLE flag
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Tests are skipped if ChromaDB unavailable
if not CHROMADB_AVAILABLE:
    pytest.skip("ChromaDB not available")
```

**Setup Required:**
- Install ChromaDB: `pip install chromadb`
- No server setup needed (uses embedded mode)

**Skip If Unavailable:**
- Tests automatically skip if ChromaDB not installed
- Run tests: `pytest tests/integration/test_chroma_adapter_integration.py -v`

---

### 3. OpenAI API

**Used For:** Generating embeddings for semantic search

**Tests Requiring OpenAI API:**

#### Tests with Mocked OpenAI (default, no API key needed)
Most tests mock the OpenAI client:
- `tests/integration/test_chroma_adapter_integration.py` - Most integration tests
- `tests/unit/test_chroma_adapter.py` - All unit tests
- All other tests referencing OpenAI

#### Tests Requiring Real OpenAI API (marked with `requires_openai`)
These tests make actual API calls and require a valid API key:
- `tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI`
  - `test_real_batch_embedding_generation` - Real batch embeddings
  - `test_real_embeddings_quality` - Embedding quality validation
  - `test_performance_improvement_real_api` - Performance benchmarks

**Environment Variable:**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

**Detection Logic:**
```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HAS_OPENAI_CREDENTIALS = OPENAI_AVAILABLE and OPENAI_API_KEY is not None

# Tests check this flag
if not HAS_OPENAI_CREDENTIALS:
    pytest.skip("OpenAI API key not available (set OPENAI_API_KEY env var)")
```

**Run Tests:**
```bash
# Run only OpenAI-requiring tests
pytest -m requires_openai tests/integration/ -v

# Skip OpenAI tests
pytest -m "not requires_openai" tests/integration/ -v
```

**Skip If Unavailable:**
- Tests marked with `@pytest.mark.requires_openai` are automatically skipped
- No failures if API key not set

**Cost Warning:** Real OpenAI tests make actual API calls and will incur charges

---

### 4. Google Calendar API

**Used For:** Calendar integration, event management, time blocking

**Tests Requiring Google Calendar API:**

#### Tests with Mocked Google Calendar (default, no credentials needed)
Most tests mock the Google API client:
- `tests/unit/test_google_calendar_adapter.py` - All unit tests (fully mocked)
- `tests/integration/test_calendar_integration.py` - Most integration tests (mocked)

**Mock Strategy:**
```python
# Google modules are mocked before import
sys.modules["google.auth.transport.requests"] = Mock()
sys.modules["google.oauth2.credentials"] = Mock()
sys.modules["google_auth_oauthlib.flow"] = Mock()
sys.modules["googleapiclient.discovery"] = Mock()
sys.modules["googleapiclient.errors"] = Mock()
```

#### Tests Requiring Real Google Calendar API (marked with `requires_google_calendar`)
These tests make actual API calls with OAuth credentials:
- `tests/integration/test_calendar_integration.py::TestGoogleCalendarRealAPI`
  - `test_real_authentication_flow` - OAuth flow validation
  - `test_real_event_crud_operations` - Create/read/update/delete events
  - `test_real_conflict_detection` - Calendar conflict detection

**Environment Variables:**
```bash
export GOOGLE_CALENDAR_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CALENDAR_CLIENT_SECRET="your-client-secret"
export GOOGLE_CALENDAR_REDIRECT_URI="http://localhost:8080/oauth2callback"
```

**Detection Logic:**
```python
GOOGLE_CALENDAR_CLIENT_ID = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
GOOGLE_CALENDAR_CLIENT_SECRET = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")
HAS_GOOGLE_CREDENTIALS = (
    GOOGLE_CALENDAR_CLIENT_ID is not None
    and GOOGLE_CALENDAR_CLIENT_SECRET is not None
    and not GOOGLE_CALENDAR_CLIENT_ID.startswith("your-")
)

# Tests check this flag
if not HAS_GOOGLE_CREDENTIALS:
    pytest.skip("Google Calendar credentials not available")
```

**Setup Instructions:**
1. Create a Google Cloud project
2. Enable Google Calendar API
3. Create OAuth 2.0 credentials (Desktop app)
4. Set environment variables with credentials
5. First test run will open browser for OAuth consent

**Run Tests:**
```bash
# Run only Google Calendar tests
pytest -m requires_google_calendar tests/integration/ -v

# Skip Google Calendar tests
pytest -m "not requires_google_calendar" tests/integration/ -v
```

**Skip If Unavailable:**
- Tests marked with `@pytest.mark.requires_google_calendar` are automatically skipped
- No failures if credentials not set

---

### 5. Anthropic API (Claude)

**Used For:** LLM interactions via LiteLLM client

**Tests Using Anthropic:**
- `tests/unit/test_client.py` - LiteLLM client tests
- `tests/unit/test_litellm_client.py` - Comprehensive client tests
- `tests/conftest.py` - Mock Anthropic client fixture

**Mock Strategy:**
All tests use mocked Anthropic client - **no real API calls are made**:
```python
@pytest.fixture
def mock_anthropic_client(monkeypatch):
    """Mock Anthropic client for testing."""
    mock_client = Mock()
    mock_client.messages.create = Mock(return_value=mock_response)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    return mock_client
```

**Environment Variable:**
```bash
export ANTHROPIC_API_KEY="test-key"  # Tests use mock values
```

**Setup Required:** None (fully mocked)

**Skip If Unavailable:** N/A (tests always run with mocks)

---

### 6. Oura Ring API

**Used For:** Health data integration (sleep, readiness, activity)

**Tests Using Oura API:**
- `tests/unit/test_adapters_oura.py` - Oura adapter tests

**Mock Strategy:**
All tests use mocked HTTP responses - **no real API calls are made**:
```python
@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment with Oura token."""
    monkeypatch.setenv("OURA_PERSONAL_ACCESS_TOKEN", "test_token_12345")
```

**Environment Variable:**
```bash
export OURA_PERSONAL_ACCESS_TOKEN="test_token"  # Tests use mock values
```

**Setup Required:** None (fully mocked)

**Skip If Unavailable:** N/A (tests always run with mocks)

---

### 7. PostgreSQL / WorkOS

**Used For:** Database operations in WorkOS adapter

**Tests Using PostgreSQL:**
- `tests/unit/test_adapters_workos.py` - WorkOS adapter tests

**Mock Strategy:**
All tests mock asyncpg and database connections - **no real database needed**:
```python
@pytest.fixture
def mock_db_pool():
    """Mock asyncpg connection pool."""
    mock_pool = AsyncMock()
    mock_pool.acquire = AsyncMock()
    return mock_pool
```

**Setup Required:** None (fully mocked)

**Skip If Unavailable:** N/A (tests always run with mocks)

---

## Environment Variables Summary

### Required for Real API Tests Only

```bash
# OpenAI (optional - for marked tests only)
export OPENAI_API_KEY="sk-your-openai-api-key"

# Google Calendar (optional - for marked tests only)
export GOOGLE_CALENDAR_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CALENDAR_CLIENT_SECRET="your-client-secret"
export GOOGLE_CALENDAR_REDIRECT_URI="http://localhost:8080/oauth2callback"
```

### Not Required (Mocked in Tests)

```bash
# These are set by tests with mock values
ANTHROPIC_API_KEY="test-key"
OURA_PERSONAL_ACCESS_TOKEN="test_token"
```

---

## Running Tests by Dependency

### Run All Tests (No External Services Required)
```bash
pytest tests/ -v
```
- All unit tests run with mocks
- Integration tests with mocked dependencies run
- Tests requiring real APIs are automatically skipped

### Run Only Unit Tests (Guaranteed No External Dependencies)
```bash
pytest -m unit tests/ -v
```

### Run Integration Tests with Mocked Dependencies
```bash
pytest -m "integration and not requires_openai and not requires_google_calendar" tests/ -v
```

### Run Tests Requiring Real OpenAI API
```bash
export OPENAI_API_KEY="sk-..."
pytest -m requires_openai tests/ -v
```

### Run Tests Requiring Real Google Calendar API
```bash
export GOOGLE_CALENDAR_CLIENT_ID="..."
export GOOGLE_CALENDAR_CLIENT_SECRET="..."
pytest -m requires_google_calendar tests/ -v
```

### Run All Tests Including Real APIs
```bash
export OPENAI_API_KEY="sk-..."
export GOOGLE_CALENDAR_CLIENT_ID="..."
export GOOGLE_CALENDAR_CLIENT_SECRET="..."
pytest tests/ -v
```

---

## Pytest Markers Reference

Tests use these markers for selective execution:

```python
@pytest.mark.unit                      # Unit tests (fast, no external deps)
@pytest.mark.integration               # Integration tests (may use local services)
@pytest.mark.slow                      # Slow running tests
@pytest.mark.api                       # Tests requiring API access
@pytest.mark.requires_openai           # Requires OPENAI_API_KEY
@pytest.mark.requires_google_calendar  # Requires Google Calendar credentials
@pytest.mark.asyncio                   # Async tests (uses pytest-asyncio)
```

**View All Markers:**
```bash
pytest --markers
```

---

## CI/CD Recommendations

### Minimal CI (No External Services)
```yaml
- name: Run Tests
  run: |
    pytest tests/ -v -m "not requires_openai and not requires_google_calendar"
```
- All unit tests run
- Integration tests with mocked dependencies run
- Real API tests are skipped

### CI with OpenAI (Optional)
```yaml
- name: Run Tests with OpenAI
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    pytest tests/ -v
```
- All tests run including real OpenAI API tests
- Google Calendar tests still skipped (unless credentials provided)

### Full CI (All Services)
```yaml
- name: Run All Tests
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    GOOGLE_CALENDAR_CLIENT_ID: ${{ secrets.GOOGLE_CALENDAR_CLIENT_ID }}
    GOOGLE_CALENDAR_CLIENT_SECRET: ${{ secrets.GOOGLE_CALENDAR_CLIENT_SECRET }}
  run: |
    pytest tests/ -v
```
- All tests run including real API tests
- ⚠️ **Warning:** May incur API costs

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'chromadb'"
```bash
# Install ChromaDB
pip install chromadb

# Or install all test dependencies
pip install -r requirements-test.txt
```

### "OpenAI API key not available" (tests skipped)
This is expected behavior. Tests requiring OpenAI API are automatically skipped.

To run them:
```bash
export OPENAI_API_KEY="sk-your-key-here"
pytest -m requires_openai tests/ -v
```

### "Google Calendar credentials not available" (tests skipped)
This is expected behavior. Tests requiring Google Calendar are automatically skipped.

To run them:
1. Set up Google Cloud project and OAuth credentials
2. Export environment variables
3. Run: `pytest -m requires_google_calendar tests/ -v`

### Tests fail with "Neo4j connection error"
This should not happen - all Neo4j tests use mocks. If you see this:
1. Check if mock is properly configured in test
2. Verify `sys.modules['neo4j'] = MagicMock()` is called before import

---

## Summary

**Key Takeaways:**
1. ✅ **Most tests require NO external dependencies** - all mocked by default
2. ✅ **ChromaDB is optional** - only integration tests need it (temporary instances)
3. ✅ **Real APIs are opt-in** - tests auto-skip if credentials not provided
4. ✅ **No database servers needed** - Neo4j, PostgreSQL all mocked
5. ✅ **CI-friendly** - can run all tests without external services

**Dependencies by Test Type:**
- **Unit tests (33 files):** No external dependencies (all mocked)
- **Integration tests (7 files):** Optional ChromaDB, optional real APIs
- **Benchmarks (5 files):** No external dependencies (all mocked)

**Required Installations:**
- `pytest` and `pytest-asyncio` (always)
- `chromadb` (optional, for ChromaDB integration tests)
- No database servers or external services required

---

*For test execution instructions, see TESTING_GUIDE.md (to be created in next phase)*
