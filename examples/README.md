# Test Execution Examples

This directory contains real-world examples of test execution outputs to help you understand what to expect when running tests in the Thanos project.

## Available Examples

1. **[01_running_all_tests.md](01_running_all_tests.md)** - Example of running the full test suite
2. **[02_running_by_category.md](02_running_by_category.md)** - Examples of running tests by category (unit, integration, etc.)
3. **[03_coverage_report.md](03_coverage_report.md)** - Example coverage report output and interpretation
4. **[04_troubleshooting_failed_test.md](04_troubleshooting_failed_test.md)** - Example of debugging a failed test
5. **[05_parallel_execution.md](05_parallel_execution.md)** - Example of running tests in parallel
6. **[06_marker_filtering.md](06_marker_filtering.md)** - Examples of using pytest markers to filter tests

## How to Use These Examples

Each example file contains:
- The exact command used
- The complete or representative output
- Annotations explaining what to look for
- Tips for interpreting the results

These examples are meant to complement the [TESTING_GUIDE.md](../TESTING_GUIDE.md). Refer to the guide for comprehensive instructions and the examples for seeing what the output looks like in practice.

## Running the Examples Yourself

All commands in these examples can be run directly in your terminal from the project root:

```bash
# Example: Run all tests
pytest

# Example: Run unit tests only
pytest -m unit

# Example: Run with coverage
pytest --cov=. --cov-report=html
```

## Note on Output

The outputs in these examples are representative samples taken from actual test runs. Your output may differ based on:
- Which tests are currently in the codebase
- Your local environment and installed dependencies
- Whether you have optional dependencies installed (OpenAI, Google Calendar, etc.)
- Test execution order and timing

The principles and patterns shown remain consistent across runs.
