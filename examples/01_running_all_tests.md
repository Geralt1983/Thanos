# Example 1: Running All Tests

This example shows what happens when you run the complete test suite.

## Command

```bash
pytest
```

Or with more verbosity:

```bash
pytest -v
```

## Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1225 items

tests/unit/test_commitment_tracker.py .....................                        [  1%]
tests/unit/test_task_management.py ..........................                      [  3%]
tests/unit/test_priority_ranking.py ...................                            [  5%]
tests/unit/test_anthropic_client.py ....................................          [  8%]
tests/unit/test_mcp_client.py .................................................   [ 12%]
tests/unit/test_usage_tracker.py ......................................           [ 15%]
tests/unit/test_calendar_integration.py ............................              [ 18%]
tests/unit/test_aggregation.py ..........................................         [ 22%]
tests/unit/test_template_engine.py .............................                  [ 25%]
tests/unit/test_health_metrics.py ...............................                 [ 28%]
tests/unit/test_state_manager.py ..................................               [ 31%]
tests/unit/test_journal_manager.py .............................                  [ 34%]
tests/unit/test_memory_manager.py ..............................                  [ 37%]
tests/unit/test_plugin_system.py .............................                    [ 40%]
tests/unit/test_voice_interface.py ........................                       [ 42%]
tests/unit/test_mobile_sync.py .......................                            [ 44%]
tests/unit/test_briefing_engine.py .................................              [ 48%]
tests/unit/test_pattern_recognition.py ...............................            [ 51%]
tests/unit/test_command_parser.py .............................                   [ 54%]
tests/unit/test_skill_system.py ..............................                    [ 57%]
tests/unit/test_agent_manager.py ..................................               [ 60%]
tests/integration/test_full_workflow.py .....                                     [ 61%]
tests/integration/test_mcp_integration.py ........                                [ 62%]
tests/integration/test_calendar_sync.py .....s                                    [ 63%]
tests/integration/test_anthropic_integration.py ......                            [ 63%]
tests/integration/test_neo4j_integration.py .........                             [ 64%]
tests/integration/test_chromadb_integration.py ....ss                             [ 65%]
tests/integration/test_health_tracking.py .....s                                  [ 65%]
test_mcp_health.py .........................................................      [ 70%]
test_mcp_loadbalancer.py ...................................................      [ 75%]
test_mcp_cache.py ......................................................          [ 80%]
test_mcp_validation.py .................................................          [ 84%]
test_mcp_logging.py ...............................................               [ 88%]
test_mcp_migration.py ..............................................              [ 92%]
test_batch_aggregation.py ..........................................              [ 96%]
test_async_error_handling.py ...............................                      [ 99%]
test_client_shutdown.py .........                                                 [100%]

=========================== 1225 passed, 4 skipped in 45.32s ============================
```

## What This Output Tells You

### Test Discovery
- **collected 1225 items** - pytest found 1,225 individual test functions/methods

### Test Progress
- Each `.` represents a passing test
- Each `s` represents a skipped test
- The percentage shows progress through the suite

### Test Results Summary
- **1225 passed** - All discovered tests passed successfully
- **4 skipped** - Some tests were skipped (usually due to missing optional dependencies)
- **45.32s** - Total execution time

### Skipped Tests
Tests are typically skipped when:
- Optional dependencies are not installed (e.g., OpenAI API key not configured)
- Tests are marked with `@pytest.mark.skipif()` conditions
- Tests require external services that aren't available

## Common Variations

### All Tests Pass
```
========================= 1225 passed in 45.32s =========================
```
✅ Perfect! All tests passed.

### Some Tests Skipped
```
=================== 1220 passed, 5 skipped in 44.12s ===================
```
✅ Still good! Skipped tests are usually for optional features.

### Test Failures
```
================ 1218 passed, 7 failed in 52.18s ========================
```
❌ Something is broken. Scroll up to see failure details.

### Test Errors
```
=============== 1215 passed, 5 failed, 5 errors in 38.91s ===============
```
❌ Errors mean tests couldn't even run (import errors, setup issues, etc.)

## Tips

1. **First Run Takes Longer** - pytest compiles bytecode on first run
2. **Skipped Tests Are Normal** - Most projects have some skipped tests for optional features
3. **Watch for Warnings** - pytest shows warnings at the end; these are important to address
4. **Use `-v` for Details** - Add `-v` flag to see individual test names
5. **Use `-x` to Stop on First Failure** - Add `-x` flag to stop immediately when a test fails

## Next Steps

- To run only fast unit tests: `pytest -m unit`
- To see coverage: `pytest --cov=. --cov-report=html`
- To run specific test files: `pytest tests/unit/test_commitment_tracker.py`
- For troubleshooting failures: See [04_troubleshooting_failed_test.md](04_troubleshooting_failed_test.md)

## Related Documentation

- [TESTING_GUIDE.md](../TESTING_GUIDE.md) - Complete testing guide
- [02_running_by_category.md](02_running_by_category.md) - Run specific test categories
