# Thanos Testing Guide

**A practical guide for running and understanding tests in the Thanos project**

**Last Updated:** 2026-01-12

---

## Introduction

Welcome to the Thanos Testing Guide! This document provides comprehensive, practical instructions for running tests in the Thanos project. Unlike high-level testing strategy documents, this guide focuses on the **how** - giving you the exact commands and workflows you need to verify code quality and functionality.

**What you'll find in this guide:**
- Quick start commands to get testing immediately
- Detailed explanations of all test categories and markers
- Instructions for running tests with various filters and options
- Setup instructions for external dependencies (with graceful fallbacks)
- Common mocking patterns and how to use them
- Coverage reporting and analysis
- Troubleshooting for common issues
- CI/CD integration recommendations

**Who this guide is for:**
- New contributors who need to run tests for the first time
- Developers writing new tests or features
- Maintainers setting up CI/CD pipelines
- Anyone debugging test failures or investigating coverage

**Test Infrastructure Status:**
- 📊 **51 test files** total across unit, integration, and benchmark categories
- ✅ **33 unit tests** - Fast, isolated tests with all dependencies mocked
- 🔗 **7 integration tests** - Tests with some external dependencies (most mocked)
- 🎯 **pytest framework** with comprehensive marker system
- 🚀 **Offline-first design** - Most tests run without external services
- 📈 **Coverage reporting** configured and ready to use

---

## Quick Start

**Get started in 30 seconds:**

```bash
# 1. Install test dependencies
pip install -r requirements-test.txt

# 2. Run all tests
pytest

# 3. Run with coverage
pytest --cov=. --cov-report=html

# 4. View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

**Most common commands:**

```bash
# Run only fast unit tests (recommended for development)
pytest -m unit

# Run all tests except slow ones
pytest -m "not slow"

# Run tests for a specific module
pytest tests/unit/test_commitment_tracker.py

# Run with verbose output
pytest -v

# Run in parallel (faster for large test suites)
pytest -n auto
```

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Test Execution Commands](#test-execution-commands)
   - [Running All Tests](#running-all-tests)
   - [Running by Category](#running-by-category)
   - [Running Specific Tests](#running-specific-tests)
   - [Running with Filters](#running-with-filters)
   - [Parallel Execution](#parallel-execution)
3. [Test Categories and Markers](#test-categories-and-markers)
   - [Unit Tests](#unit-tests)
   - [Integration Tests](#integration-tests)
   - [Slow Tests](#slow-tests)
   - [API Tests](#api-tests)
   - [Custom Markers](#custom-markers)
4. [External Dependencies](#external-dependencies)
   - [Overview](#dependencies-overview)
   - [Neo4j](#neo4j-database)
   - [ChromaDB](#chromadb)
   - [OpenAI API](#openai-api)
   - [Google Calendar API](#google-calendar-api)
   - [Other Services](#other-services)
5. [Mocking Patterns and Fixtures](#mocking-patterns-and-fixtures)
   - [Available Fixtures](#available-fixtures)
   - [Common Mocking Patterns](#common-mocking-patterns)
   - [Writing Tests with Mocks](#writing-tests-with-mocks)
6. [Coverage Reporting](#coverage-reporting)
   - [Generating Coverage Reports](#generating-coverage-reports)
   - [Understanding Coverage Metrics](#understanding-coverage-metrics)
   - [Improving Coverage](#improving-coverage)
7. [Troubleshooting](#troubleshooting)
   - [Common Errors](#common-errors)
   - [Import Issues](#import-issues)
   - [Fixture Issues](#fixture-issues)
   - [Async Test Issues](#async-test-issues)
8. [CI/CD Integration](#cicd-integration)
   - [Current Setup](#current-setup)
   - [GitHub Actions Example](#github-actions-example)
   - [Running Tests Without External Services](#running-tests-without-external-services)
9. [Additional Resources](#additional-resources)

---

## Prerequisites

### Python Version

**Minimum Required:** Python 3.8+

```bash
# Check your Python version
python --version
```

If you need to upgrade Python, visit [python.org](https://www.python.org/downloads/).

### Required Dependencies

Install all testing dependencies from `requirements-test.txt`:

```bash
pip install -r requirements-test.txt
```

**What gets installed:**
- **pytest** (>=7.4.0) - Core testing framework
- **pytest-cov** (>=4.1.0) - Coverage reporting
- **pytest-mock** (>=3.11.1) - Enhanced mocking utilities
- **pytest-asyncio** (>=0.21.1) - Async test support
- **coverage[toml]** (>=7.3.0) - Coverage analysis
- **faker** (>=19.6.0) - Test data generation
- **freezegun** (>=1.2.2) - Time mocking utilities
- **responses** (>=0.23.3) - HTTP request mocking

### Optional Dependencies

These are only needed for specific test categories:

**For parallel test execution:**
```bash
pip install pytest-xdist
```

**For integration tests with ChromaDB:**
```bash
pip install chromadb
```

**Note:** Most tests mock external dependencies, so you can run the majority of the test suite without installing services like Neo4j, PostgreSQL, or external APIs.

### Environment Setup

**Basic setup (required):**
```bash
# Copy example environment file
cp .env.example .env

# No additional configuration needed for basic testing!
# Tests use mocks by default
```

**Optional API keys (for integration tests):**
```bash
# Add to .env only if running tests marked with requires_openai
OPENAI_API_KEY=sk-...

# Add to .env only if running tests marked with requires_google_calendar
GOOGLE_CALENDAR_CLIENT_ID=your-client-id
GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret
```

**Important:** Tests requiring external APIs will automatically skip if credentials are not available. You don't need to set these up unless you specifically want to run those integration tests.

### Verify Installation

Run this command to verify your setup:

```bash
# This should show pytest version and available plugins
pytest --version

# This should list all test files
pytest --collect-only
```

**Expected output:**
```
pytest 7.4.0
plugins: cov-4.1.0, mock-3.11.1, asyncio-0.21.1
```

---

<!-- Section placeholders for future subtasks -->

## Test Execution Commands

This section covers all the ways you can run tests in the Thanos project. From running everything at once to targeting specific test files or categories, these commands give you fine-grained control over test execution.

### Running All Tests

**Basic command:**
```bash
pytest
```

This discovers and runs all tests in the `tests/` directory. With our current test suite of 51 test files, this typically takes 10-30 seconds depending on your system.

**With more detail:**
```bash
# Show verbose output with test names
pytest -v

# Show extra detailed output with full diffs
pytest -vv

# Show test output even for passing tests
pytest -s
```

**Expected output:**
```
============================= test session starts ==============================
platform darwin -- Python 3.11.0, pytest-7.4.0, pluggy-1.3.0
rootdir: /path/to/thanos
configfile: pytest.ini
testpaths: tests
plugins: cov-4.1.0, mock-3.11.1, asyncio-0.21.1
collected 246 items

tests/test_commitment_tracker.py ........................           [  9%]
tests/unit/test_client.py ....................                      [ 19%]
...
======================== 246 passed in 12.45s ===============================
```

---

### Running by Category

The test suite is organized into categories using pytest markers. This lets you run only the tests you need.

**Unit tests only (recommended for development):**
```bash
pytest -m unit
```

Unit tests are fast (typically complete in 5-10 seconds) and have all external dependencies mocked. Perfect for rapid development cycles.

**Integration tests only:**
```bash
pytest -m integration
```

Integration tests may involve external services (though most are mocked) and take longer to run. Use these when testing cross-component functionality.

**All tests in a specific directory:**
```bash
# Run all unit tests
pytest tests/unit/

# Run all integration tests
pytest tests/integration/

# Run all root-level tests
pytest tests/test_*.py
```

---

### Running Specific Tests

**Run a specific test file:**
```bash
pytest tests/unit/test_commitment_tracker.py
```

**Run a specific test class:**
```bash
pytest tests/unit/test_client.py::TestThanos
```

**Run a specific test function:**
```bash
# In a test class
pytest tests/unit/test_client.py::TestThanos::test_initialization

# Standalone function
pytest tests/test_commitment_tracker.py::test_commitment_creation
```

**Run multiple specific files:**
```bash
pytest tests/test_commitment_tracker.py tests/unit/test_client.py
```

**Run tests matching a name pattern:**
```bash
# Run all tests with "commitment" in the name
pytest -k commitment

# Run all tests with "neo4j" in the name
pytest -k neo4j

# Exclude tests with "slow" in the name
pytest -k "not slow"

# Complex patterns with AND/OR
pytest -k "commitment and not integration"
```

---

### Running with Filters

**Skip slow tests (recommended for rapid development):**
```bash
pytest -m "not slow"
```

This skips tests marked with `@pytest.mark.slow`, which are typically integration tests or performance benchmarks that take significant time.

**Skip API tests (tests requiring external APIs):**
```bash
pytest -m "not api"
```

**Skip tests requiring specific services:**
```bash
# Skip OpenAI API tests
pytest -m "not requires_openai"

# Skip Google Calendar tests
pytest -m "not requires_google_calendar"

# Skip both
pytest -m "not requires_openai and not requires_google_calendar"
```

**Run only fast unit tests (development workflow):**
```bash
pytest -m "unit and not slow"
```

This gives you the fastest feedback loop - typically 5 seconds or less.

**Combine multiple filters:**
```bash
# Unit tests only, exclude slow and API tests
pytest -m "unit and not slow and not api"

# Integration tests but skip those requiring external APIs
pytest -m "integration and not requires_openai and not requires_google_calendar"
```

---

### Running with Coverage Reporting

**Run tests with coverage analysis:**
```bash
# Basic coverage report
pytest --cov=.

# Coverage with terminal report
pytest --cov=. --cov-report=term

# Coverage with missing lines shown
pytest --cov=. --cov-report=term-missing

# Coverage with HTML report (recommended)
pytest --cov=. --cov-report=html

# After running, open the HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**Target specific modules for coverage:**
```bash
# Coverage for core engine only
pytest --cov=core --cov-report=html

# Coverage for adapters only
pytest --cov=adapters --cov-report=html

# Multiple modules
pytest --cov=core --cov=adapters --cov-report=html
```

**Set coverage failure threshold:**
```bash
# Fail if coverage is below 80%
pytest --cov=. --cov-fail-under=80
```

**Coverage with unit tests only (faster):**
```bash
pytest -m unit --cov=. --cov-report=html
```

---

### Running with Verbose Output

**Different verbosity levels:**
```bash
# Level 1: Show test file and progress
pytest

# Level 2: Show individual test names (-v)
pytest -v

# Level 3: Show detailed output (-vv)
pytest -vv

# Show print statements and logging (useful for debugging)
pytest -s

# Combine verbose and output capture
pytest -vv -s
```

**Show test durations:**
```bash
# Show 10 slowest tests
pytest --durations=10

# Show all test durations
pytest --durations=0

# Show only tests slower than 1 second
pytest --durations-min=1.0
```

**Show local variables on failure:**
```bash
pytest -l

# Or with more verbose traceback
pytest -l --tb=long
```

**Control traceback style:**
```bash
# Short traceback (default in pytest.ini)
pytest --tb=short

# Long traceback with full context
pytest --tb=long

# No traceback, only assertion errors
pytest --tb=line

# Only show first and last entry
pytest --tb=native
```

---

### Parallel Execution

Running tests in parallel can significantly speed up large test suites.

**Install pytest-xdist (one-time setup):**
```bash
pip install pytest-xdist
```

**Run tests in parallel:**
```bash
# Automatic worker count (uses all CPU cores)
pytest -n auto

# Specific number of workers
pytest -n 4

# Run with coverage (requires pytest-cov compatibility)
pytest -n auto --cov=. --cov-report=html
```

**Performance tips:**
- Parallel execution is most effective with 20+ tests
- Some tests with shared resources may fail in parallel
- Integration tests may not parallelize well
- Unit tests are ideal for parallel execution

**Example timing comparison:**
```bash
# Sequential (baseline)
pytest -m unit
# Time: 12.45s

# Parallel with 4 workers
pytest -m unit -n 4
# Time: 3.82s (3.2x faster)

# Parallel with auto workers (8 cores)
pytest -m unit -n auto
# Time: 2.15s (5.8x faster)
```

---

### Advanced Filtering and Options

**Stop on first failure:**
```bash
# Stop immediately on first failure
pytest -x

# Stop after N failures
pytest --maxfail=3
```

**Run only failed tests from last run:**
```bash
# First run (some tests fail)
pytest

# Re-run only the failed tests
pytest --lf

# Run failed tests first, then all others
pytest --ff
```

**Rerun flaky tests:**
```bash
# Install pytest-rerunfailures
pip install pytest-rerunfailures

# Rerun failed tests up to 3 times
pytest --reruns 3

# Rerun with delay
pytest --reruns 3 --reruns-delay 1
```

**Control test discovery:**
```bash
# Collect tests but don't run them
pytest --collect-only

# Show why tests were selected/deselected
pytest -v --collect-only

# Dry-run: show what would be run
pytest --collect-only -q
```

**Run tests in random order:**
```bash
# Install pytest-random-order
pip install pytest-random-order

# Run tests in random order
pytest --random-order

# Use specific seed for reproducibility
pytest --random-order-seed=12345
```

---

### Common Test Execution Workflows

Here are some recommended command combinations for different scenarios:

**Development workflow (fast feedback):**
```bash
# Run only fast unit tests
pytest -m "unit and not slow" -v

# Or with file watching (requires pytest-watch)
pip install pytest-watch
ptw -- -m "unit and not slow"
```

**Pre-commit workflow (comprehensive but quick):**
```bash
# All tests except slow ones and external APIs
pytest -m "not slow and not requires_openai and not requires_google_calendar" --cov=. --cov-report=term-missing
```

**Full test suite with coverage (CI/CD):**
```bash
# Run everything with HTML coverage report
pytest -v --cov=. --cov-report=html --cov-report=term-missing --durations=10

# Or in parallel for CI
pytest -n auto --cov=. --cov-report=xml --cov-report=term-missing
```

**Debugging specific test failures:**
```bash
# Run specific test with verbose output and prints
pytest tests/unit/test_client.py::TestThanos::test_initialization -vv -s -l

# With Python debugger (pdb)
pytest tests/unit/test_client.py::TestThanos::test_initialization --pdb

# Drop into debugger on failure
pytest --pdb -x
```

**Integration testing workflow:**
```bash
# Run integration tests with required APIs only
pytest -m "integration and not requires_openai" -v

# Or all integration tests if APIs are configured
pytest -m integration -v --cov=adapters --cov=core
```

**Coverage improvement workflow:**
```bash
# 1. Generate coverage report
pytest --cov=. --cov-report=html

# 2. Open report and identify uncovered files
open htmlcov/index.html

# 3. Run specific test file to see coverage change
pytest tests/unit/test_new_feature.py --cov=core/new_feature --cov-report=term-missing
```

---

### Quick Reference Table

| Goal | Command |
|------|---------|
| Run all tests | `pytest` |
| Run unit tests only | `pytest -m unit` |
| Run integration tests | `pytest -m integration` |
| Run specific file | `pytest tests/unit/test_client.py` |
| Run specific test | `pytest tests/unit/test_client.py::test_name` |
| Skip slow tests | `pytest -m "not slow"` |
| Skip API tests | `pytest -m "not api"` |
| Run with coverage | `pytest --cov=. --cov-report=html` |
| Verbose output | `pytest -v` |
| Show print statements | `pytest -s` |
| Parallel execution | `pytest -n auto` (requires pytest-xdist) |
| Stop on first failure | `pytest -x` |
| Rerun failed tests | `pytest --lf` |
| Show test durations | `pytest --durations=10` |
| Debug with pdb | `pytest --pdb` |

---

**💡 Pro Tips:**

1. **Create aliases** for common commands in your shell profile:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   alias ptu='pytest -m "unit and not slow" -v'
   alias ptc='pytest --cov=. --cov-report=html'
   alias pta='pytest -n auto'
   ```

2. **Use pytest.ini** to set default options (already configured in this project)

3. **Watch mode** for continuous testing during development:
   ```bash
   pip install pytest-watch
   ptw -- -m unit
   ```

4. **Combine with git** to test only changed code:
   ```bash
   # Test files changed in current branch
   pytest $(git diff --name-only main | grep "\.py$" | sed 's/\.py$//')
   ```

5. **Environment variables** for pytest behavior:
   ```bash
   # Skip slow tests by default
   export PYTEST_ADDOPTS="-m 'not slow'"

   # Always show coverage
   export PYTEST_ADDOPTS="--cov=. --cov-report=term-missing"
   ```

## Test Categories and Markers

*This section will be completed in subtask 2.3*

## External Dependencies

*This section will be completed in subtask 2.4*

## Mocking Patterns and Fixtures

*This section will be completed in subtask 2.5*

## Coverage Reporting

*This section will be completed in subtask 2.6*

## Troubleshooting

*This section will be completed in subtask 2.7*

## CI/CD Integration

*This section will be completed in subtask 2.8*

## Additional Resources

- **[TEST_INVENTORY.md](./TEST_INVENTORY.md)** - Complete catalog of all test files
- **[TEST_DEPENDENCIES.md](./TEST_DEPENDENCIES.md)** - Detailed dependency documentation
- **[TEST_MOCKING_PATTERNS.md](./TEST_MOCKING_PATTERNS.md)** - Comprehensive mocking reference
- **[INTEGRATION_TEST_GUIDE.md](./INTEGRATION_TEST_GUIDE.md)** - Integration testing best practices
- **[pytest documentation](https://docs.pytest.org/)** - Official pytest docs

---

*This guide is maintained alongside the test infrastructure. If you find errors or have suggestions for improvement, please update this document or create an issue.*
