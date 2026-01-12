# Example 2: Running Tests by Category

This example demonstrates how to run tests filtered by category using pytest markers.

## Example 2a: Running Only Unit Tests

Unit tests are fast, isolated tests with all external dependencies mocked.

### Command

```bash
pytest -m unit
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1225 items / 188 deselected / 1037 selected

tests/unit/test_commitment_tracker.py .....................                        [  2%]
tests/unit/test_task_management.py ..........................                      [  4%]
tests/unit/test_priority_ranking.py ...................                            [  6%]
tests/unit/test_anthropic_client.py ....................................          [ 10%]
tests/unit/test_mcp_client.py .................................................   [ 14%]
tests/unit/test_usage_tracker.py ......................................           [ 18%]
tests/unit/test_calendar_integration.py ............................              [ 21%]
tests/unit/test_aggregation.py ..........................................         [ 25%]
tests/unit/test_template_engine.py .............................                  [ 28%]
tests/unit/test_health_metrics.py ...............................                 [ 31%]
tests/unit/test_state_manager.py ..................................               [ 34%]
tests/unit/test_journal_manager.py .............................                  [ 37%]
tests/unit/test_memory_manager.py ..............................                  [ 40%]
tests/unit/test_plugin_system.py .............................                    [ 43%]
tests/unit/test_voice_interface.py ........................                       [ 45%]
tests/unit/test_mobile_sync.py .......................                            [ 47%]
tests/unit/test_briefing_engine.py .................................              [ 50%]
tests/unit/test_pattern_recognition.py ...............................            [ 53%]
tests/unit/test_command_parser.py .............................                   [ 56%]
tests/unit/test_skill_system.py ..............................                    [ 59%]
tests/unit/test_agent_manager.py ..................................               [ 62%]
test_batch_aggregation.py ..........................................              [ 95%]
test_async_error_handling.py ...............................                      [ 98%]
test_client_shutdown.py .........                                                 [100%]

========================= 1037 passed, 188 deselected in 18.42s =========================
```

### What to Notice

- **188 deselected** - pytest found 1,225 tests but filtered to run only 1,037 unit tests
- **18.42s** - Much faster than running all tests (45s in Example 1)
- Unit tests typically complete in under 30 seconds

---

## Example 2b: Running Only Integration Tests

Integration tests may interact with external services (though most are mocked).

### Command

```bash
pytest -m integration
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1225 items / 1174 deselected / 51 selected

tests/integration/test_full_workflow.py .....                                     [  9%]
tests/integration/test_mcp_integration.py ........                                [ 25%]
tests/integration/test_calendar_sync.py .....s                                    [ 37%]
tests/integration/test_anthropic_integration.py ......                            [ 49%]
tests/integration/test_neo4j_integration.py .........                             [ 67%]
tests/integration/test_chromadb_integration.py ....ss                             [ 79%]
tests/integration/test_health_tracking.py .....s                                  [100%]

======================= 47 passed, 4 skipped, 1174 deselected in 8.15s ===================
```

### What to Notice

- **51 selected** - Only 51 integration tests out of 1,225 total
- **4 skipped** - Some integration tests require optional external services
- **8.15s** - Integration tests are still relatively fast due to mocking

---

## Example 2c: Running Tests by Directory

Run all tests in a specific directory:

### Command

```bash
pytest tests/unit/
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 982 items

tests/unit/test_commitment_tracker.py .....................                        [  2%]
tests/unit/test_task_management.py ..........................                      [  4%]
tests/unit/test_priority_ranking.py ...................                            [  6%]
[... output truncated ...]

========================= 982 passed in 16.23s =========================
```

---

## Example 2d: Excluding Slow Tests

Run all tests except those marked as slow:

### Command

```bash
pytest -m "not slow"
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1225 items / 89 deselected / 1136 selected

[... tests run ...]

======================= 1136 passed, 89 deselected in 35.18s ========================
```

### What to Notice

- **89 deselected** - 89 slow tests were excluded
- **35.18s vs 45s** - Saved about 10 seconds by skipping slow tests
- Perfect for rapid development cycles

---

## Example 2e: Running Only API Tests

Run only tests that interact with external APIs:

### Command

```bash
pytest -m api
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1225 items / 1203 deselected / 22 selected

tests/integration/test_calendar_sync.py .....s                                    [ 27%]
tests/integration/test_anthropic_integration.py ......                            [ 54%]
tests/unit/test_anthropic_client.py ........                                      [100%]

======================= 16 passed, 6 skipped, 1203 deselected in 3.82s ===================
```

### What to Notice

- **6 skipped** - Tests requiring actual API keys were auto-skipped
- **3.82s** - Very fast because most API tests use mocks
- Use this to verify API integration code without hitting real APIs

---

## Common Marker Combinations

### Run unit tests that aren't slow

```bash
pytest -m "unit and not slow"
```

### Run integration tests that don't require APIs

```bash
pytest -m "integration and not api"
```

### Run all tests that require OpenAI (will skip if no API key)

```bash
pytest -m requires_openai
```

### Run all tests except those requiring external services

```bash
pytest -m "not requires_openai and not requires_google_calendar"
```

---

## Quick Reference Table

| Command | What It Runs | Typical Time |
|---------|--------------|--------------|
| `pytest -m unit` | Only unit tests | 15-20s |
| `pytest -m integration` | Only integration tests | 8-12s |
| `pytest -m "not slow"` | All non-slow tests | 30-35s |
| `pytest -m slow` | Only slow tests | 10-15s |
| `pytest -m api` | Only API integration tests | 3-5s |
| `pytest tests/unit/` | All tests in unit directory | 15-20s |
| `pytest tests/integration/` | All tests in integration directory | 8-12s |

---

## Tips

1. **Use unit tests during development** - They're fastest and catch most issues
2. **Run integration tests before committing** - Verify everything works together
3. **Combine markers for precision** - Use `and`, `or`, `not` to filter exactly what you need
4. **Check pytest.ini for available markers** - Run `pytest --markers` to see all available markers

## Related Documentation

- [TESTING_GUIDE.md - Test Categories](../TESTING_GUIDE.md#test-categories-and-markers)
- [01_running_all_tests.md](01_running_all_tests.md) - Running the full suite
- [06_marker_filtering.md](06_marker_filtering.md) - Advanced marker filtering
