# Example 6: Advanced Marker Filtering

This example demonstrates advanced pytest marker filtering techniques to run exactly the tests you need.

## Available Markers in Thanos

```bash
pytest --markers
```

```
@pytest.mark.unit: Unit tests - fast, isolated, all dependencies mocked
@pytest.mark.integration: Integration tests - may use external services (mostly mocked)
@pytest.mark.slow: Tests that take longer than 5 seconds to run
@pytest.mark.api: Tests that interact with external APIs
@pytest.mark.requires_openai: Tests requiring OpenAI API key (auto-skip if not available)
@pytest.mark.requires_google_calendar: Tests requiring Google Calendar credentials (auto-skip if not available)
@pytest.mark.asyncio: Tests for async functions (auto-applied by pytest-asyncio)
```

---

## Basic Marker Filtering

### Run Only Unit Tests

```bash
pytest -m unit
```

### Run Only Integration Tests

```bash
pytest -m integration
```

### Run Only Slow Tests

```bash
pytest -m slow
```

### Run Only API Tests

```bash
pytest -m api
```

---

## Logical Combinations

### AND: Tests that are BOTH unit AND slow

```bash
pytest -m "unit and slow"
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 1187 deselected / 38 selected

tests/unit/test_aggregation.py .........................                         [ 65%]
tests/unit/test_pattern_recognition.py .............                             [100%]

======================= 38 passed, 1187 deselected in 8.42s ==========================
```

**What this finds**: Unit tests that are marked as slow (e.g., large data processing)

---

### OR: Tests that are EITHER unit OR integration

```bash
pytest -m "unit or integration"
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 137 deselected / 1088 selected

tests/unit/test_commitment_tracker.py .....................                        [  1%]
[... all unit and integration tests ...]
tests/integration/test_health_tracking.py .....s                                  [100%]

======================= 1084 passed, 4 skipped, 137 deselected in 28.73s ===================
```

**What this finds**: All tests in either category (most of the test suite)

---

### NOT: Exclude Certain Markers

#### Exclude Slow Tests

```bash
pytest -m "not slow"
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 89 deselected / 1136 selected

[... all non-slow tests ...]

======================= 1136 passed, 89 deselected in 35.18s ==========================
```

**Use case**: Fast feedback during development

#### Exclude API Tests

```bash
pytest -m "not api"
```

**What this finds**: All tests that don't interact with external APIs

#### Exclude Tests Requiring External Services

```bash
pytest -m "not requires_openai and not requires_google_calendar"
```

**Use case**: Running tests without any API keys configured

---

## Complex Marker Combinations

### Unit Tests That Aren't Slow

```bash
pytest -m "unit and not slow"
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 226 deselected / 999 selected

[... fast unit tests only ...]

======================= 999 passed, 226 deselected in 12.34s ==========================
```

**Use case**: Fastest possible test feedback during development
**Time saved**: ~6 seconds vs all unit tests

---

### Integration Tests Without External APIs

```bash
pytest -m "integration and not api"
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 1203 deselected / 22 selected

tests/integration/test_full_workflow.py .....                                     [ 22%]
tests/integration/test_neo4j_integration.py .........                             [ 63%]
tests/integration/test_health_tracking.py .....                                   [100%]

======================= 22 passed, 1203 deselected in 4.12s ==========================
```

**Use case**: Integration testing without network dependencies

---

### Slow OR API Tests (For Parallel Execution)

```bash
pytest -m "slow or api" -n auto
```

**Use case**: Run the time-consuming tests in parallel while working on other things

---

### Unit Tests Requiring OpenAI

```bash
pytest -m "unit and requires_openai"
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 1217 deselected / 8 selected

tests/unit/test_anthropic_client.py ........s                                     [100%]

======================= 7 passed, 1 skipped, 1217 deselected in 1.89s ===================
```

**What happened**:
- 8 tests selected
- 7 passed (using mocks)
- 1 skipped (requires actual API key, not available)

---

## Practical Workflows with Markers

### Workflow 1: Rapid Development Loop

You're working on `Tools/commitment_tracker.py`.

```bash
# Step 1: Run only the relevant unit tests (fastest)
pytest tests/unit/test_commitment_tracker.py

# Step 2: Run all fast unit tests to catch regressions
pytest -m "unit and not slow"

# Step 3: Before committing, run everything
pytest
```

**Time progression**: 2s → 12s → 45s

---

### Workflow 2: Pre-Commit Checks

Before committing, verify different test categories:

```bash
# Fast tests (should be immediate)
pytest -m "unit and not slow"  # 12s

# Slow tests (acceptable wait)
pytest -m slow  # 15s

# All tests (comprehensive)
pytest  # 45s
```

---

### Workflow 3: CI/CD Pipeline Stages

Organize CI stages by marker:

```yaml
# .github/workflows/test.yml

jobs:
  fast-tests:
    - name: Fast unit tests
      run: pytest -m "unit and not slow"
      timeout: 2min

  integration-tests:
    - name: Integration tests
      run: pytest -m integration
      timeout: 5min

  slow-tests:
    - name: Slow tests
      run: pytest -m slow
      timeout: 10min
```

---

### Workflow 4: Debugging API Integration

You're debugging OpenAI API integration:

```bash
# Step 1: Run just the OpenAI tests
pytest -m requires_openai -v

# Step 2: Run with API key to test actual integration
export OPENAI_API_KEY="sk-..."
pytest -m requires_openai -v

# Step 3: Run related unit tests
pytest -m "unit and api" -v
```

---

## Filtering by Test Name Pattern

Combine markers with `-k` for name-based filtering.

### Tests with "commit" in the name

```bash
pytest -k commit
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 1167 deselected / 58 selected

tests/unit/test_commitment_tracker.py .....................                        [ 36%]
test_batch_aggregation.py ..........................................              [100%]

======================= 58 passed, 1167 deselected in 4.82s ==========================
```

---

### Unit tests with "async" in the name

```bash
pytest -m unit -k async
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 1198 deselected / 27 selected

tests/unit/test_mcp_client.py .................                                   [ 62%]
test_async_error_handling.py ..........                                           [100%]

======================= 27 passed, 1198 deselected in 3.12s ==========================
```

**What this finds**: Unit tests with "async" in the test name or class name

---

### Integration tests excluding "calendar"

```bash
pytest -m integration -k "not calendar"
```

**Use case**: Run integration tests but skip calendar-related tests

---

## Combining with Other Options

### Parallel + Markers

```bash
pytest -m "unit and not slow" -n auto
```

**Result**: Fast unit tests running in parallel (very fast feedback!)

---

### Coverage + Markers

```bash
pytest -m unit --cov=Tools --cov-report=html
```

**Result**: Coverage report for just unit-tested code

---

### Verbose + Markers

```bash
pytest -m "integration and api" -v
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 1209 deselected / 16 selected

tests/integration/test_calendar_sync.py::TestCalendarSync::test_sync_events PASSED [  6%]
tests/integration/test_calendar_sync.py::TestCalendarSync::test_sync_with_conflicts PASSED [ 12%]
tests/integration/test_calendar_sync.py::TestCalendarSync::test_sync_error_handling SKIPPED [ 18%]
tests/integration/test_anthropic_integration.py::test_generate_completion PASSED [ 25%]
[... more verbose output ...]

======================= 15 passed, 1 skipped, 1209 deselected in 4.32s ===================
```

---

## Marker Best Practices

### ✅ DO: Use Markers for Logical Grouping

```python
@pytest.mark.unit
@pytest.mark.slow
def test_large_data_processing():
    """Process 10,000 records"""
    pass
```

### ✅ DO: Combine Markers Meaningfully

```python
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_openai
def test_anthropic_completion():
    """Test actual API call"""
    pass
```

### ✅ DO: Use `not` to Exclude Categories

```bash
# Run everything except slow tests
pytest -m "not slow"
```

### ❌ DON'T: Over-Complicate Marker Logic

```bash
# Too complex, hard to understand
pytest -m "(unit or integration) and (api or slow) and not requires_openai"
```

### ❌ DON'T: Forget Quotes for Complex Expressions

```bash
# WRONG: Will cause parse error
pytest -m unit and not slow

# CORRECT: Use quotes
pytest -m "unit and not slow"
```

---

## Debugging Marker Selection

### See Which Tests Would Run (Without Running)

```bash
pytest -m unit --collect-only
```

**Sample Output**:

```
================================== test session starts ===================================
collected 1225 items / 188 deselected / 1037 selected

<Module tests/unit/test_commitment_tracker.py>
  <Class TestCommitmentTracker>
    <Function test_create_commitment>
    <Function test_update_commitment>
    <Function test_delete_commitment>
    [... all collected tests listed ...]

======================= 1037/1225 tests collected (188 deselected) in 0.84s ==============
```

**Use case**: Verify your marker selection before running

---

### Count Tests by Marker

```bash
# Count unit tests
pytest -m unit --collect-only -q

# Count slow tests
pytest -m slow --collect-only -q

# Count API tests
pytest -m api --collect-only -q
```

**Sample Output**:

```
1037/1225 tests collected (188 deselected) in 0.62s
```

---

## Quick Reference Table

| Marker Expression | What It Runs | Use Case |
|-------------------|--------------|----------|
| `-m unit` | Only unit tests | Development |
| `-m integration` | Only integration tests | Pre-commit |
| `-m "not slow"` | All non-slow tests | Fast feedback |
| `-m "unit and not slow"` | Fast unit tests only | Rapid iteration |
| `-m "integration and not api"` | Integration without APIs | Offline testing |
| `-m slow` | Only slow tests | Parallel execution |
| `-m api` | Only API tests | API debugging |
| `-m requires_openai` | OpenAI-dependent tests | API integration testing |
| `-m "unit or integration"` | Most tests | General testing |
| `-m "not requires_openai and not requires_google_calendar"` | No external services | No credentials needed |

---

## Performance Comparison

Based on Thanos test suite (1,225 tests total):

| Command | Tests Run | Time | Use Case |
|---------|-----------|------|----------|
| `pytest` | 1,225 | 45s | Full suite |
| `pytest -m unit` | 1,037 | 18s | Unit tests |
| `pytest -m "unit and not slow"` | 999 | 12s | Fast unit tests |
| `pytest -m integration` | 51 | 8s | Integration tests |
| `pytest -m slow` | 89 | 15s | Slow tests |
| `pytest -m api` | 22 | 4s | API tests |
| `pytest -m "not slow"` | 1,136 | 35s | Skip slow tests |

---

## Tips

1. **Use `--collect-only` to preview** - See what will run without running it
2. **Quote complex expressions** - Always use quotes for `and`, `or`, `not`
3. **Combine with `-k` for precision** - Filter by marker AND name pattern
4. **Use `-v` to verify selection** - See exactly which tests run
5. **Document custom markers** - Add to pytest.ini so `pytest --markers` shows them
6. **Start specific, then broader** - Run small subset first, expand if passing

---

## Related Documentation

- [TESTING_GUIDE.md - Test Categories and Markers](../TESTING_GUIDE.md#test-categories-and-markers)
- [02_running_by_category.md](02_running_by_category.md)
- [05_parallel_execution.md](05_parallel_execution.md)
