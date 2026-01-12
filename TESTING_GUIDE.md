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

Understanding test markers is crucial for running the right tests at the right time. Markers let you categorize tests and run specific subsets based on speed, dependencies, or purpose. This section explains all available markers and when to use each one.

### Marker Overview

All markers are registered in `pytest.ini` and enforced with the `--strict-markers` flag. This prevents typos and ensures consistency across the test suite.

**Quick marker reference:**

| Marker | Purpose | Auto-Skip? | Typical Count |
|--------|---------|------------|---------------|
| `@pytest.mark.unit` | Fast, isolated unit tests | No | ~200+ tests |
| `@pytest.mark.integration` | Tests with external dependencies | No | ~50+ tests |
| `@pytest.mark.slow` | Tests taking >5 seconds | No | ~20 tests |
| `@pytest.mark.api` | Tests requiring API access | No | ~15 tests |
| `@pytest.mark.requires_openai` | Tests requiring OpenAI API key | Yes* | ~10 tests |
| `@pytest.mark.requires_google_calendar` | Tests requiring Google Calendar credentials | Yes* | ~8 tests |
| `@pytest.mark.asyncio` | Async tests (auto-applied) | No | ~100+ tests |

*Auto-skip means tests automatically skip themselves if the required credentials are not available.

---

### @pytest.mark.unit

**Purpose:** Marks fast, isolated unit tests with all external dependencies mocked.

**Characteristics:**
- ⚡ **Fast** - Typically complete in milliseconds
- 🔒 **Isolated** - No external services, databases, or APIs
- 🎭 **Fully mocked** - All dependencies are mocked or stubbed
- ✅ **Reliable** - No flaky behavior from external factors
- 🚀 **CI-friendly** - Perfect for rapid feedback in CI/CD

**When to use:**
- Testing individual functions, classes, or methods
- Testing business logic without external dependencies
- Testing error handling and edge cases
- Any test that can run with mocked dependencies

**Example:**

```python
import pytest
from core.commitment_tracker import CommitmentTracker

@pytest.mark.unit
def test_commitment_creation():
    """Test that commitments are created with correct properties."""
    tracker = CommitmentTracker()
    commitment = tracker.create_commitment(
        title="Complete project",
        due_date="2024-12-31"
    )
    assert commitment.title == "Complete project"
    assert commitment.status == "pending"
```

**Run unit tests:**

```bash
# All unit tests
pytest -m unit

# Unit tests excluding slow ones
pytest -m "unit and not slow"

# Unit tests with coverage
pytest -m unit --cov=. --cov-report=html

# Specific unit test file
pytest -m unit tests/unit/test_commitment_tracker.py
```

**Best practices:**
- Use for the majority of your tests (80%+ of test suite)
- Mock all external dependencies (databases, APIs, file systems)
- Keep tests fast (<100ms per test)
- Test one thing per test function
- Use descriptive test names that explain what's being tested

---

### @pytest.mark.integration

**Purpose:** Marks integration tests that verify interactions between components or with external systems.

**Characteristics:**
- 🔗 **Cross-component** - Tests multiple components working together
- 🐌 **Slower** - May take seconds rather than milliseconds
- 🌐 **External dependencies** - May use real or mocked external services
- 🎯 **End-to-end scenarios** - Tests realistic workflows
- ⚙️ **System-level** - Tests configuration, initialization, teardown

**When to use:**
- Testing interactions between multiple components
- Testing adapters with real external services (when safe)
- Testing complex workflows that span multiple modules
- Verifying system-level behavior
- Testing configuration and initialization logic

**Example:**

```python
import pytest
from adapters.google_calendar_adapter import GoogleCalendarAdapter
from core.session_manager import SessionManager

@pytest.mark.integration
@pytest.mark.asyncio
async def test_calendar_integration_workflow():
    """Test complete workflow of fetching and processing calendar events."""
    # This test uses mocked Google Calendar API
    adapter = GoogleCalendarAdapter()
    session_manager = SessionManager()

    events = await adapter.fetch_events()
    session = await session_manager.create_session(events)

    assert len(session.events) > 0
    assert session.status == "active"
```

**Run integration tests:**

```bash
# All integration tests
pytest -m integration

# Integration tests with verbose output
pytest -m integration -v

# Integration tests excluding external API requirements
pytest -m "integration and not requires_openai and not requires_google_calendar"

# Specific integration test file
pytest tests/integration/test_calendar_integration.py
```

**Best practices:**
- Use for tests that verify component interactions
- Mock external services when possible (most integration tests do)
- Keep integration tests focused on specific workflows
- Use fixtures to set up complex test scenarios
- Consider using temporary databases or in-memory storage
- Combine with other markers (`@pytest.mark.slow`, `@pytest.mark.requires_openai`) as needed

---

### @pytest.mark.slow

**Purpose:** Marks tests that take significant time to run (>5 seconds).

**Characteristics:**
- ⏱️ **Time-consuming** - Takes >5 seconds to complete
- 🔄 **Performance tests** - May include benchmarks or stress tests
- 📊 **Large datasets** - May process significant amounts of data
- 🧪 **Complex scenarios** - Multi-step workflows or comprehensive tests

**When to use:**
- Performance benchmarks and profiling tests
- Tests that process large amounts of data
- Complex multi-step integration scenarios
- Tests that intentionally wait (rate limiting, retries)
- Comprehensive end-to-end tests

**Example:**

```python
import pytest
from integration.chroma_adapter_integration import ChromaIntegration

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_large_scale_embedding_generation():
    """Test generating embeddings for 1000+ documents."""
    integration = ChromaIntegration()
    documents = [f"Document {i}" for i in range(1000)]

    embeddings = await integration.generate_embeddings(documents)

    assert len(embeddings) == 1000
    # This test takes ~10 seconds due to embedding generation
```

**Run or skip slow tests:**

```bash
# Skip slow tests (recommended for development)
pytest -m "not slow"

# Run only slow tests
pytest -m slow

# Run unit tests but skip slow ones (fastest feedback)
pytest -m "unit and not slow"

# Run all tests including slow ones
pytest  # (slow tests are included by default)
```

**Best practices:**
- Always combine with `@pytest.mark.unit` or `@pytest.mark.integration`
- Use for tests that genuinely need time (don't mark tests slow just because they're integration tests)
- Consider splitting slow tests into smaller, focused tests when possible
- Document why the test is slow in the docstring
- Run slow tests in CI but skip during local development

---

### @pytest.mark.api

**Purpose:** General marker for tests that require network access or external API calls.

**Characteristics:**
- 🌐 **Network dependent** - Requires internet connectivity
- 🔑 **May need credentials** - Might require API keys or tokens
- 🎲 **Potentially flaky** - Network issues can cause intermittent failures
- 💰 **May have costs** - Some API calls may incur charges

**When to use:**
- Tests making real HTTP requests to external services
- Tests that require internet connectivity
- Tests that interact with third-party APIs (when not using more specific markers)
- Tests that have external rate limits

**Example:**

```python
import pytest
import requests

@pytest.mark.api
def test_external_service_health():
    """Test that external service is reachable."""
    response = requests.get("https://api.example.com/health")
    assert response.status_code == 200
```

**Run or skip API tests:**

```bash
# Skip all API tests (recommended for offline development)
pytest -m "not api"

# Run only API tests
pytest -m api

# Run integration tests but skip API tests
pytest -m "integration and not api"
```

**Best practices:**
- Use more specific markers when available (`requires_openai`, `requires_google_calendar`)
- Mock API calls in most tests; only use real APIs when absolutely necessary
- Implement auto-skip logic if credentials are missing
- Consider VCR/cassette libraries to record/replay API responses
- Be mindful of rate limits and API costs

---

### @pytest.mark.requires_openai

**Purpose:** Marks tests that require a valid OpenAI API key to run.

**Characteristics:**
- 🔑 **Requires API key** - Needs `OPENAI_API_KEY` environment variable
- ✅ **Auto-skip** - Tests automatically skip if API key not provided
- 💰 **Incurs costs** - Makes real API calls that cost money
- 🎯 **Real integration** - Tests actual OpenAI API behavior
- 🌐 **Network dependent** - Requires internet connectivity

**When to use:**
- Testing OpenAI-specific features (embeddings, completions, chat)
- Verifying integration with OpenAI's API
- Testing behavior with real AI model responses
- Validating error handling for OpenAI-specific errors

**Example:**

```python
import pytest
import os
from adapters.chroma_adapter import ChromaAdapter

@pytest.mark.requires_openai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_embedding_generation():
    """Test generating embeddings using real OpenAI API.

    Requires OPENAI_API_KEY environment variable.
    Skips automatically if not provided.
    """
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not configured")

    adapter = ChromaAdapter()
    embedding = await adapter.generate_embedding("Test document")

    assert isinstance(embedding, list)
    assert len(embedding) == 1536  # OpenAI embedding dimension
```

**Setup:**

```bash
# Add to .env file
OPENAI_API_KEY=sk-your-api-key-here

# Or set temporarily for one test run
OPENAI_API_KEY=sk-your-key pytest -m requires_openai
```

**Run or skip OpenAI tests:**

```bash
# Skip OpenAI tests (default for local development)
pytest -m "not requires_openai"

# Run only OpenAI tests
pytest -m requires_openai

# Run all tests except those requiring external APIs
pytest -m "not requires_openai and not requires_google_calendar"

# Run integration tests but skip OpenAI tests
pytest -m "integration and not requires_openai"
```

**Best practices:**
- Always implement auto-skip logic (check for API key presence)
- Document in test docstring that API key is required
- Use sparingly - most tests should use mocked OpenAI responses
- Consider using recorded responses (VCR cassettes) instead
- Be mindful of API costs when running these tests
- Combine with `@pytest.mark.integration` and `@pytest.mark.slow` if appropriate

---

### @pytest.mark.requires_google_calendar

**Purpose:** Marks tests that require Google Calendar API credentials to run.

**Characteristics:**
- 🔑 **Requires credentials** - Needs Google Calendar OAuth2 credentials
- ✅ **Auto-skip** - Tests automatically skip if credentials not configured
- 🌐 **Network dependent** - Requires internet connectivity
- 📅 **Real calendar data** - May interact with real calendar events (use test calendars!)
- 🎯 **OAuth flow** - Tests authentication and authorization

**When to use:**
- Testing Google Calendar adapter integration
- Verifying OAuth2 authentication flow
- Testing calendar event fetching, creation, or updates
- Validating error handling for Google Calendar API errors

**Example:**

```python
import pytest
import os
from adapters.google_calendar_adapter import GoogleCalendarAdapter

@pytest.mark.requires_google_calendar
@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_calendar_events():
    """Test fetching events from Google Calendar.

    Requires Google Calendar API credentials:
    - GOOGLE_CALENDAR_CLIENT_ID
    - GOOGLE_CALENDAR_CLIENT_SECRET

    Skips automatically if not configured.
    """
    if not (os.getenv("GOOGLE_CALENDAR_CLIENT_ID") and
            os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")):
        pytest.skip("Google Calendar credentials not configured")

    adapter = GoogleCalendarAdapter()
    events = await adapter.fetch_events(days_ahead=7)

    assert isinstance(events, list)
```

**Setup:**

```bash
# Add to .env file
GOOGLE_CALENDAR_CLIENT_ID=your-client-id
GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret

# Follow Google Calendar API setup guide
# https://developers.google.com/calendar/api/quickstart/python
```

**Run or skip Google Calendar tests:**

```bash
# Skip Google Calendar tests (default for local development)
pytest -m "not requires_google_calendar"

# Run only Google Calendar tests
pytest -m requires_google_calendar

# Run all tests except those requiring external APIs
pytest -m "not requires_openai and not requires_google_calendar"

# Run integration tests but skip Google Calendar tests
pytest -m "integration and not requires_google_calendar"
```

**Best practices:**
- Always implement auto-skip logic (check for credentials)
- Use test/sandbox Google Calendar accounts, never production calendars
- Document credential setup in test docstring
- Most tests should use mocked Google Calendar responses
- Use recorded API responses when possible
- Combine with `@pytest.mark.integration` marker
- Be careful about modifying real calendar data

---

### @pytest.mark.asyncio

**Purpose:** Marks async tests that use `async`/`await` syntax.

**Characteristics:**
- 🔄 **Async execution** - Tests async functions and coroutines
- ⚙️ **Auto-applied** - pytest-asyncio plugin handles event loop setup
- 🎯 **Async patterns** - Tests async code paths and concurrent execution
- 📦 **Plugin-managed** - Requires pytest-asyncio plugin (included in requirements-test.txt)

**When to use:**
- Testing async functions (any function defined with `async def`)
- Testing code that uses `await`
- Testing concurrent operations
- Testing async context managers or generators

**Example:**

```python
import pytest
from core.session_manager import SessionManager

@pytest.mark.asyncio
async def test_async_session_creation():
    """Test asynchronous session creation."""
    manager = SessionManager()
    session = await manager.create_session()

    assert session.id is not None
    assert session.status == "active"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test multiple async operations running concurrently."""
    manager = SessionManager()

    # Run multiple operations concurrently
    sessions = await asyncio.gather(
        manager.create_session(),
        manager.create_session(),
        manager.create_session()
    )

    assert len(sessions) == 3
    assert all(s.status == "active" for s in sessions)
```

**Configuration:**

The `@pytest.mark.asyncio` marker is automatically recognized by the pytest-asyncio plugin (installed via requirements-test.txt). No additional configuration needed!

**Best practices:**
- Combine with `@pytest.mark.unit` or `@pytest.mark.integration`
- Use `AsyncMock` from `unittest.mock` for mocking async functions
- Test both successful async execution and async exceptions
- Be aware of event loop configuration (handled automatically by pytest-asyncio)
- Use `await` for all async operations in tests

---

### Combining Markers

Tests can have multiple markers to precisely categorize them:

**Common marker combinations:**

```python
# Fast unit test (no external dependencies)
@pytest.mark.unit
def test_simple_function():
    pass

# Integration test with async code
@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_integration():
    pass

# Slow integration test requiring OpenAI
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_expensive_ai_operation():
    pass

# Unit test that's slow (performance benchmark)
@pytest.mark.unit
@pytest.mark.slow
def test_performance_benchmark():
    pass
```

**Filtering with combined markers:**

```bash
# Fast unit tests only (exclude slow)
pytest -m "unit and not slow"

# Integration tests without external API requirements
pytest -m "integration and not requires_openai and not requires_google_calendar"

# Only tests that require OpenAI (likely integration and slow)
pytest -m requires_openai

# All tests except slow and API-dependent
pytest -m "not slow and not api and not requires_openai and not requires_google_calendar"
```

---

### Writing Tests: Which Marker Should I Use?

Use this decision tree when writing new tests:

```
1. Does the test use async/await?
   ├─ Yes → Add @pytest.mark.asyncio
   └─ No → Continue

2. Does the test require external API calls?
   ├─ Yes → Which API?
   │   ├─ OpenAI → Add @pytest.mark.requires_openai
   │   ├─ Google Calendar → Add @pytest.mark.requires_google_calendar
   │   └─ Other → Add @pytest.mark.api
   └─ No → Continue

3. Does the test integrate multiple components?
   ├─ Yes → Add @pytest.mark.integration
   └─ No → Add @pytest.mark.unit

4. Does the test take >5 seconds?
   ├─ Yes → Add @pytest.mark.slow
   └─ No → Done!
```

**Examples:**

- **Simple function test:** `@pytest.mark.unit`
- **Async function test:** `@pytest.mark.unit` + `@pytest.mark.asyncio`
- **Component integration:** `@pytest.mark.integration` + `@pytest.mark.asyncio`
- **OpenAI integration:** `@pytest.mark.integration` + `@pytest.mark.requires_openai` + `@pytest.mark.asyncio`
- **Slow benchmark:** `@pytest.mark.unit` + `@pytest.mark.slow`

---

### Marker Best Practices

**DO:**
- ✅ Mark all unit tests with `@pytest.mark.unit`
- ✅ Mark all integration tests with `@pytest.mark.integration`
- ✅ Mark tests requiring external APIs with specific markers
- ✅ Implement auto-skip logic for tests requiring credentials
- ✅ Combine markers to precisely categorize tests
- ✅ Document in test docstrings when special setup is required

**DON'T:**
- ❌ Skip markers - they enable powerful test filtering
- ❌ Mark tests with both `unit` and `integration` (choose one)
- ❌ Overuse `slow` marker (try to keep tests fast)
- ❌ Make real API calls without appropriate markers
- ❌ Use custom markers (stick to registered markers in pytest.ini)

**Example of good test marking:**

```python
import pytest
import os
from core.commitment_tracker import CommitmentTracker
from adapters.google_calendar_adapter import GoogleCalendarAdapter

# Good: Simple unit test
@pytest.mark.unit
def test_commitment_creation():
    tracker = CommitmentTracker()
    commitment = tracker.create("Test")
    assert commitment.title == "Test"

# Good: Integration test with auto-skip
@pytest.mark.integration
@pytest.mark.requires_google_calendar
@pytest.mark.asyncio
async def test_calendar_sync():
    """Sync commitments with Google Calendar.

    Requires Google Calendar API credentials.
    Skips automatically if not configured.
    """
    if not (os.getenv("GOOGLE_CALENDAR_CLIENT_ID")):
        pytest.skip("Google Calendar not configured")

    adapter = GoogleCalendarAdapter()
    result = await adapter.sync_events()
    assert result.success

# Good: Performance benchmark marked as slow
@pytest.mark.unit
@pytest.mark.slow
def test_large_dataset_processing():
    """Test processing 10,000 items (benchmark)."""
    tracker = CommitmentTracker()
    items = [f"Item {i}" for i in range(10000)]
    result = tracker.process_batch(items)
    assert len(result) == 10000
```

---

### Viewing Available Markers

**See all registered markers:**

```bash
pytest --markers
```

**Output:**
```
@pytest.mark.unit: Unit tests (fast, isolated)
@pytest.mark.integration: Integration tests (slower, external dependencies)
@pytest.mark.slow: Slow running tests
@pytest.mark.api: Tests requiring API access
@pytest.mark.requires_google_calendar: Tests requiring Google Calendar API credentials
@pytest.mark.requires_openai: Tests requiring OpenAI API key
@pytest.mark.asyncio: Mark async test functions
...
```

**Count tests by marker:**

```bash
# See how many tests have each marker
pytest --collect-only -q | grep "<Module" | wc -l  # Total tests
pytest -m unit --collect-only -q | wc -l           # Unit tests
pytest -m integration --collect-only -q | wc -l    # Integration tests
pytest -m slow --collect-only -q | wc -l           # Slow tests
```

---

### Summary

Markers are your primary tool for organizing and filtering tests. The Thanos test suite uses a clear, hierarchical marking system:

1. **Primary category:** Every test is either `unit` or `integration`
2. **Execution time:** Slow tests get `slow` marker
3. **External dependencies:** Tests requiring APIs get specific markers (`requires_openai`, `requires_google_calendar`, or generic `api`)
4. **Async support:** Async tests automatically get `asyncio` marker

This system enables powerful test filtering for different workflows:
- **Development:** `pytest -m "unit and not slow"` (fastest feedback)
- **Pre-commit:** `pytest -m "not slow and not requires_openai and not requires_google_calendar"` (comprehensive but quick)
- **CI/CD:** `pytest` (everything, including slow tests)
- **Integration:** `pytest -m integration` (verify component interactions)

**Next section:** [External Dependencies](#external-dependencies) explains how to set up optional external services for integration tests.

## External Dependencies

This section explains how to set up external dependencies for integration testing. The good news: **most tests require NO external dependencies** and run with mocks by default!

### Overview

The Thanos test suite is designed with a **graceful fallback strategy**:

- ✅ **Unit tests (33 files):** All external dependencies mocked - runs offline
- ✅ **Integration tests (7 files):** Most dependencies mocked - minimal setup required
- ⚡ **Real API tests:** Opt-in only - auto-skip if credentials not available

**Philosophy:**
- **Mock by default** - Tests use mocked dependencies unless explicitly marked
- **Auto-skip pattern** - Tests requiring external services skip gracefully if unavailable
- **No database servers** - Neo4j, PostgreSQL, and other databases are fully mocked
- **CI-friendly** - Can run entire test suite without external services

---

### Dependency Categories

External dependencies fall into three categories:

| Category | Examples | Setup Required | Tests Skip if Missing |
|----------|----------|----------------|----------------------|
| **Fully Mocked** | Neo4j, Anthropic, Oura, PostgreSQL | None | N/A (always mocked) |
| **Optional Services** | ChromaDB | `pip install chromadb` | Yes |
| **Optional APIs** | OpenAI, Google Calendar | API credentials | Yes |

---

### Neo4j Database

**Status:** ✅ Fully mocked - no setup required

**What it's used for:**
- Graph database operations for commitments
- Pattern recognition and relationship storage
- Memory graph queries

**Do I need to install Neo4j?**
No! All Neo4j tests use mocks. You don't need to install or run a Neo4j database server.

**Related tests:**
- `tests/integration/test_neo4j_batch_operations.py` (mocked)
- `tests/unit/test_neo4j_*.py` (all mocked)
- `tests/benchmarks/test_neo4j_session_performance.py` (mocked)

**How it works:**
```python
# Tests mock Neo4j before importing the adapter
sys.modules['neo4j'] = MagicMock()
from Tools.adapters.neo4j_adapter import Neo4jAdapter

# All database operations use the mock
adapter = Neo4jAdapter(uri="bolt://localhost:7687", username="neo4j", password="test")
adapter._driver = Mock()  # Mocked driver
```

**Run Neo4j tests:**
```bash
# All Neo4j tests run with mocks
pytest tests/unit/test_neo4j_session_pool.py -v
pytest tests/integration/test_neo4j_batch_operations.py -v
```

---

### ChromaDB

**Status:** 📦 Optional - install for integration tests

**What it's used for:**
- Vector storage and semantic search
- Embedding management
- Memory retrieval

**Do I need to install ChromaDB?**
Only if you want to run ChromaDB integration tests. Most tests mock ChromaDB and run without it.

**Installation:**
```bash
# Install ChromaDB
pip install chromadb

# Verify installation
python -c "import chromadb; print(chromadb.__version__)"
```

**No server setup needed!** Tests use embedded ChromaDB with temporary directories.

**Related tests:**
- **Unit tests (mocked):**
  - `tests/unit/test_chroma_adapter.py` - All unit tests use mocks
  - `tests/unit/test_memory_integration.py` - Memory system tests (mocked)

- **Integration tests (require ChromaDB):**
  - `tests/integration/test_chroma_adapter_integration.py` - Batch operations with real ChromaDB

**Run ChromaDB tests:**
```bash
# Run integration tests (requires ChromaDB installed)
pytest tests/integration/test_chroma_adapter_integration.py -v

# Skip if ChromaDB not installed
# Tests automatically skip with message: "ChromaDB not available"
```

**Auto-skip behavior:**
```python
# Tests check for ChromaDB availability
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Tests skip gracefully if not available
if not CHROMADB_AVAILABLE:
    pytest.skip("ChromaDB not available")
```

---

### OpenAI API

**Status:** 🔑 Optional - requires API key for marked tests

**What it's used for:**
- Generating embeddings for semantic search
- Vector representations of text
- Integration testing with real OpenAI models

**Do I need an OpenAI API key?**
Only if you want to run tests marked with `@pytest.mark.requires_openai`. Most tests use mocked OpenAI responses.

**Cost Warning:** ⚠️ Tests marked with `requires_openai` make **real API calls** and will incur charges on your OpenAI account.

**Setup:**

**Step 1: Get an API key**
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

**Step 2: Set environment variable**

```bash
# Add to .env file (recommended)
echo 'OPENAI_API_KEY=sk-your-actual-api-key-here' >> .env

# Or export temporarily
export OPENAI_API_KEY="sk-your-actual-api-key-here"

# Verify it's set
echo $OPENAI_API_KEY
```

**Step 3: Verify setup**
```bash
# This should not skip
pytest -m requires_openai tests/integration/ -v

# If API key is not set, you'll see:
# SKIPPED [1] OpenAI API key not available (set OPENAI_API_KEY env var)
```

**Related tests:**

- **Unit tests (mocked - no API key needed):**
  - `tests/unit/test_chroma_adapter.py` - All unit tests use mocks
  - All other tests referencing OpenAI

- **Integration tests (require API key):**
  - `tests/integration/test_chroma_adapter_integration.py::TestChromaBatchEmbeddingWithRealOpenAI`
    - `test_real_batch_embedding_generation`
    - `test_real_embeddings_quality`
    - `test_performance_improvement_real_api`

**Run OpenAI tests:**
```bash
# Run only tests requiring OpenAI API (will skip if key not set)
pytest -m requires_openai -v

# Skip OpenAI tests (default for local development)
pytest -m "not requires_openai" -v

# Run integration tests but skip OpenAI
pytest -m "integration and not requires_openai" -v
```

**Auto-skip behavior:**
```python
# Tests check for API key presence
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HAS_OPENAI_CREDENTIALS = OPENAI_API_KEY is not None

# Tests skip gracefully if not available
if not HAS_OPENAI_CREDENTIALS:
    pytest.skip("OpenAI API key not available (set OPENAI_API_KEY env var)")
```

---

### Google Calendar API

**Status:** 🔑 Optional - requires OAuth credentials for marked tests

**What it's used for:**
- Calendar integration and event management
- Time blocking and scheduling
- Conflict detection

**Do I need Google Calendar credentials?**
Only if you want to run tests marked with `@pytest.mark.requires_google_calendar`. Most tests use mocked Google Calendar responses.

**Setup:**

**Step 1: Create Google Cloud Project**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable Google Calendar API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

**Step 2: Create OAuth 2.0 Credentials**
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Configure consent screen if prompted (internal or external)
4. Application type: **Desktop app**
5. Name: "Thanos Test Client" (or any name)
6. Click "Create"
7. Copy the **Client ID** and **Client Secret**

**Step 3: Set environment variables**

```bash
# Add to .env file (recommended)
cat >> .env <<EOF
GOOGLE_CALENDAR_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret
GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:8080/oauth2callback
EOF

# Or export temporarily
export GOOGLE_CALENDAR_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CALENDAR_CLIENT_SECRET="your-client-secret"
export GOOGLE_CALENDAR_REDIRECT_URI="http://localhost:8080/oauth2callback"
```

**Step 4: First-time OAuth flow**

The first time you run Google Calendar tests, a browser window will open for OAuth consent:
```bash
pytest -m requires_google_calendar tests/integration/ -v
```

1. Browser opens automatically
2. Sign in with your Google account
3. Grant calendar access permissions
4. Browser redirects to localhost (will show "cannot connect" - this is normal)
5. Tests continue automatically

Credentials are saved locally for future test runs.

**Step 5: Verify setup**
```bash
# This should not skip
pytest -m requires_google_calendar tests/integration/ -v

# If credentials not set, you'll see:
# SKIPPED [1] Google Calendar credentials not available
```

**Related tests:**

- **Unit tests (mocked - no credentials needed):**
  - `tests/unit/test_google_calendar_adapter.py` - All unit tests use mocks

- **Integration tests (require credentials):**
  - `tests/integration/test_calendar_integration.py::TestGoogleCalendarRealAPI`
    - `test_real_authentication_flow`
    - `test_real_event_crud_operations`
    - `test_real_conflict_detection`

**Run Google Calendar tests:**
```bash
# Run only tests requiring Google Calendar (will skip if credentials not set)
pytest -m requires_google_calendar -v

# Skip Google Calendar tests (default for local development)
pytest -m "not requires_google_calendar" -v

# Run integration tests but skip Google Calendar
pytest -m "integration and not requires_google_calendar" -v
```

**Auto-skip behavior:**
```python
# Tests check for credentials
import os
GOOGLE_CALENDAR_CLIENT_ID = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
GOOGLE_CALENDAR_CLIENT_SECRET = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")
HAS_GOOGLE_CREDENTIALS = (
    GOOGLE_CALENDAR_CLIENT_ID is not None
    and GOOGLE_CALENDAR_CLIENT_SECRET is not None
    and not GOOGLE_CALENDAR_CLIENT_ID.startswith("your-")
)

# Tests skip gracefully if not available
if not HAS_GOOGLE_CREDENTIALS:
    pytest.skip("Google Calendar credentials not available")
```

**Important:** Use a **test Google account**, not your personal calendar! Integration tests may create/modify calendar events.

---

### Other Services (Fully Mocked)

These services are **always mocked** in tests - no setup required:

#### Anthropic API (Claude)
- **Used for:** LLM interactions via LiteLLM client
- **Tests:** `tests/unit/test_client.py`, `tests/unit/test_litellm_client.py`
- **Setup:** None - uses `mock_anthropic_client` fixture from `conftest.py`
- **Environment variable:** `ANTHROPIC_API_KEY` (tests use mock value "test-key")

```python
# All tests use this mock fixture
@pytest.fixture
def mock_anthropic_client(monkeypatch):
    mock_client = Mock()
    mock_client.messages.create = Mock(return_value=mock_response)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    return mock_client
```

#### Oura Ring API
- **Used for:** Health data integration (sleep, readiness, activity)
- **Tests:** `tests/unit/test_adapters_oura.py`
- **Setup:** None - uses mocked HTTP responses
- **Environment variable:** `OURA_PERSONAL_ACCESS_TOKEN` (tests use mock value "test_token_12345")

#### PostgreSQL / WorkOS
- **Used for:** Database operations in WorkOS adapter
- **Tests:** `tests/unit/test_adapters_workos.py`
- **Setup:** None - uses mocked asyncpg connection pool
- **Database:** No PostgreSQL server needed

---

### Environment Variables Summary

**Quick reference for all environment variables:**

```bash
# Optional - for OpenAI integration tests only
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional - for Google Calendar integration tests only
GOOGLE_CALENDAR_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret
GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:8080/oauth2callback

# Not needed - tests provide mock values
# ANTHROPIC_API_KEY=test-key  (mocked)
# OURA_PERSONAL_ACCESS_TOKEN=test_token  (mocked)
```

**Create a .env file:**
```bash
# Copy example (if available)
cp .env.example .env

# Or create new one
cat > .env <<EOF
# Optional: Only set these if running real API tests
# OPENAI_API_KEY=sk-your-key-here
# GOOGLE_CALENDAR_CLIENT_ID=your-client-id
# GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret
# GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:8080/oauth2callback
EOF
```

**Verify environment variables:**
```bash
# Check what's set
env | grep -E '(OPENAI|GOOGLE_CALENDAR|ANTHROPIC|OURA)'

# Or use Python
python -c "import os; print('OpenAI:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
python -c "import os; print('Google Calendar:', 'SET' if os.getenv('GOOGLE_CALENDAR_CLIENT_ID') else 'NOT SET')"
```

---

### Skip vs Mock Strategies

Understanding when tests skip vs when they use mocks:

**Always Mocked (Never Skip):**
- **Neo4j** - All tests use `sys.modules['neo4j'] = MagicMock()`
- **Anthropic** - All tests use `mock_anthropic_client` fixture
- **Oura** - All tests use mocked HTTP responses
- **PostgreSQL** - All tests use mocked `asyncpg` pool

Tests run normally with mocked behavior. No external services needed.

**Auto-Skip When Missing:**
- **OpenAI API** - Tests marked `@pytest.mark.requires_openai` skip if `OPENAI_API_KEY` not set
- **Google Calendar** - Tests marked `@pytest.mark.requires_google_calendar` skip if credentials not set
- **ChromaDB** - Integration tests skip if `import chromadb` fails

Tests skip gracefully with informative message. No test failures.

**Strategy Decision Matrix:**

| Dependency | Unit Tests | Integration Tests (unmarked) | Integration Tests (marked) |
|------------|-----------|----------------------------|---------------------------|
| Neo4j | Mock | Mock | Mock |
| ChromaDB | Mock | Mock or Skip | Require (skip if missing) |
| OpenAI | Mock | Mock | Require (skip if missing) |
| Google Calendar | Mock | Mock | Require (skip if missing) |
| Anthropic | Mock | Mock | Mock |
| Oura | Mock | Mock | Mock |
| PostgreSQL | Mock | Mock | Mock |

**When to use each strategy:**

**Mock (Default):**
- Fastest execution
- No external dependencies
- Consistent, reproducible results
- Perfect for unit tests and most integration tests
- Use for 95%+ of your tests

**Auto-skip (Opt-in):**
- Testing real API integrations
- Validating authentication flows
- Checking actual API behavior
- Performance testing with real services
- Use sparingly due to cost and reliability concerns

---

### Common Workflows

**Development (no external services):**
```bash
# Run all tests with default mocks
pytest -v

# Or explicitly skip API tests
pytest -m "not requires_openai and not requires_google_calendar" -v
```

**Testing with ChromaDB:**
```bash
# Install ChromaDB
pip install chromadb

# Run ChromaDB integration tests
pytest tests/integration/test_chroma_adapter_integration.py -v
```

**Testing with OpenAI (incurs costs):**
```bash
# Set API key
export OPENAI_API_KEY="sk-your-key-here"

# Run only OpenAI tests
pytest -m requires_openai -v

# Or run all tests (includes OpenAI)
pytest -v
```

**Testing with Google Calendar:**
```bash
# Set credentials
export GOOGLE_CALENDAR_CLIENT_ID="your-client-id"
export GOOGLE_CALENDAR_CLIENT_SECRET="your-secret"

# Run only Google Calendar tests
pytest -m requires_google_calendar -v

# First run will open browser for OAuth
```

**CI/CD (minimal dependencies):**
```bash
# Run everything except real API tests
pytest -m "not requires_openai and not requires_google_calendar" --cov=. -v
```

**Full integration testing:**
```bash
# Set all credentials
export OPENAI_API_KEY="sk-..."
export GOOGLE_CALENDAR_CLIENT_ID="..."
export GOOGLE_CALENDAR_CLIENT_SECRET="..."

# Install optional dependencies
pip install chromadb

# Run everything
pytest -v --cov=. --cov-report=html
```

---

### Troubleshooting Dependencies

**"ModuleNotFoundError: No module named 'chromadb'"**

This is expected if ChromaDB isn't installed. Either:
```bash
# Install ChromaDB
pip install chromadb

# Or skip ChromaDB tests (they auto-skip anyway)
pytest -v  # ChromaDB tests will skip automatically
```

**"OpenAI API key not available" (tests skipped)**

This is normal behavior. Tests are skipping because `OPENAI_API_KEY` is not set.

To run these tests:
```bash
export OPENAI_API_KEY="sk-your-key-here"
pytest -m requires_openai -v
```

**"Google Calendar credentials not available" (tests skipped)**

This is normal behavior. Tests are skipping because credentials aren't configured.

To run these tests:
1. Follow setup steps in [Google Calendar API](#google-calendar-api) section
2. Run: `pytest -m requires_google_calendar -v`

**"Invalid API key" or "401 Unauthorized"**

Your API credentials are set but invalid:
- **OpenAI:** Verify key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Google Calendar:** Regenerate OAuth credentials in Google Cloud Console

**"Rate limit exceeded"**

You're making too many API calls:
```bash
# Skip real API tests to avoid rate limits
pytest -m "not requires_openai and not requires_google_calendar" -v

# Or run specific tests one at a time
pytest tests/integration/test_chroma_adapter_integration.py::test_real_batch_embedding_generation -v
```

**Tests fail with "Neo4j connection error"**

This shouldn't happen - all Neo4j tests use mocks. If you see this:
1. Check test file imports mocks before adapter
2. Verify `sys.modules['neo4j'] = MagicMock()` is called
3. Report as a bug if issue persists

---

### Summary

**Key Takeaways:**

1. ✅ **Most tests need NO external dependencies** - mocked by default
2. ✅ **No database servers required** - Neo4j, PostgreSQL fully mocked
3. ✅ **Optional dependencies auto-skip** - no test failures if missing
4. ✅ **CI-friendly design** - runs without external services
5. 📦 **ChromaDB is optional** - install only for integration tests
6. 🔑 **Real APIs are opt-in** - requires explicit credentials and markers

**Installation checklist:**

- [x] **Always required:** `pip install -r requirements-test.txt`
- [ ] **Optional:** `pip install chromadb` (for ChromaDB integration tests)
- [ ] **Optional:** Set `OPENAI_API_KEY` (for real OpenAI tests, incurs costs)
- [ ] **Optional:** Set Google Calendar credentials (for real calendar tests)

**Most common setup (runs 95% of tests):**
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests (API tests auto-skip)
pytest -v
```

**Next section:** [Mocking Patterns and Fixtures](#mocking-patterns-and-fixtures) explains how to write tests using the mocking strategies described here.

## Mocking Patterns and Fixtures

This section explains the mocking infrastructure available in the Thanos test suite and provides practical examples for writing tests. The test suite provides comprehensive fixtures and patterns to mock external dependencies, making tests fast, isolated, and reliable.

### Overview

**Mocking Philosophy:**
- **Mock by default** - All external dependencies are mocked in tests
- **Fixtures for reusability** - Common mocks are provided as pytest fixtures
- **Isolated tests** - Each test runs independently with clean mocks
- **Fast execution** - No network calls or external services in unit tests

**What's available:**
- **35+ pytest fixtures** in `conftest.py` and `conftest_mcp.py`
- **unittest.mock** patterns (Mock, AsyncMock, patch)
- **Temporary directories** for file-based tests
- **Environment variable mocking** with monkeypatch
- **Module-level import mocking** for unavailable dependencies

---

### Available Fixtures

The test suite provides fixtures in three main files:

#### Core Fixtures (tests/conftest.py)

These fixtures are available to all tests automatically:

**`mock_anthropic_client`** - Mocked Anthropic API client
```python
def test_llm_interaction(mock_anthropic_client):
    """Test using the mock Anthropic client."""
    # Client is pre-configured with mock responses
    response = mock_anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        messages=[{"role": "user", "content": "Test"}]
    )
    assert response.content[0].text == "Test response"
```

**`mock_anthropic_response`** - Standard API response dictionary
```python
def test_response_parsing(mock_anthropic_response):
    """Test parsing Anthropic API responses."""
    assert mock_anthropic_response["model"] == "claude-sonnet-4-5-20250929"
    assert mock_anthropic_response["role"] == "assistant"
    assert len(mock_anthropic_response["content"]) > 0
```

**`sample_messages`** - List of conversation messages
```python
def test_conversation_flow(sample_messages):
    """Test with realistic conversation data."""
    assert len(sample_messages) == 4
    assert sample_messages[0]["role"] == "user"
    assert sample_messages[1]["role"] == "assistant"
```

**`temp_config_dir`** - Temporary configuration directory
```python
def test_config_storage(temp_config_dir):
    """Test storing configuration files."""
    config_file = temp_config_dir / "settings.json"
    config_file.write_text('{"key": "value"}')
    assert config_file.exists()
    # Automatic cleanup after test
```

**`mock_api_config`** - Mock API configuration file
```python
def test_api_setup(mock_api_config):
    """Test with pre-configured API settings."""
    import json
    config = json.loads(mock_api_config.read_text())
    assert "anthropic_api_key" in config
    assert config["anthropic_api_key"] == "test-key-123"
```

**`project_root_path`** - Project root directory
```python
def test_file_locations(project_root_path):
    """Test accessing project files."""
    readme = project_root_path / "README.md"
    assert readme.exists()
```

#### MCP Fixtures (tests/conftest_mcp.py)

For testing MCP (Model Context Protocol) functionality:

**`mock_client_session`** - Comprehensive MCP ClientSession mock
```python
@pytest.mark.asyncio
async def test_mcp_tools(mock_client_session):
    """Test MCP tool listing and execution."""
    # Initialize MCP session
    init_result = await mock_client_session.initialize()
    assert init_result.protocolVersion == "2024-11-05"

    # List available tools
    tools_result = await mock_client_session.list_tools()
    assert len(tools_result.tools) == 1

    # Call a tool
    tool_result = await mock_client_session.call_tool(
        "test_tool",
        {"arg1": "value"}
    )
    assert not tool_result.isError
```

**`sample_mcp_json`** - Mock `.mcp.json` configuration
```python
def test_mcp_config(sample_mcp_json):
    """Test MCP configuration parsing."""
    import json
    config = json.loads(sample_mcp_json.read_text())
    assert "test-server" in config["mcpServers"]
    assert config["mcpServers"]["test-server"]["enabled"] is True
```

**`sample_tools`** - Sample tool definitions
```python
def test_tool_schema(sample_tools):
    """Test tool schema validation."""
    assert len(sample_tools) == 2
    assert sample_tools[0]["name"] == "get_tasks"
    assert "parameters" in sample_tools[0]
```

**`event_loop`** - Session-scoped event loop for async tests
```python
@pytest.mark.asyncio
async def test_async_operation(event_loop):
    """Test async code with managed event loop."""
    result = await some_async_function()
    assert result is not None
```

#### Calendar Fixtures (tests/fixtures/calendar_fixtures.py)

Helper functions (not pytest fixtures) for Google Calendar testing:

**`get_mock_event(...)`** - Create mock calendar events
```python
def test_calendar_event():
    """Test with mock calendar events."""
    from tests.fixtures.calendar_fixtures import get_mock_event
    from datetime import datetime

    event = get_mock_event(
        summary="Team Meeting",
        start_time=datetime.now(),
        duration_minutes=60
    )
    assert event["summary"] == "Team Meeting"
    assert event["status"] == "confirmed"
```

**`get_workday_events()`** - Realistic workday schedule
```python
def test_schedule_parsing():
    """Test parsing a full day's schedule."""
    from tests.fixtures.calendar_fixtures import get_workday_events

    events = get_workday_events()
    assert len(events) == 5
    assert events[0]["summary"] == "Morning Standup"
    assert events[1]["summary"] == "Deep Work Block"
```

**Other helpers:**
- `get_mock_credentials_data()` - OAuth credentials
- `get_mock_calendar()` - Calendar object
- `get_all_day_event()` - All-day event
- `get_recurring_event()` - Recurring event
- `get_conflicting_event()` - Overlapping event for testing conflict detection

---

### Common Mocking Patterns

#### Basic Mock Objects

Use `Mock` for simple object mocking:

```python
from unittest.mock import Mock

def test_basic_mock():
    """Test with a simple mock object."""
    mock_service = Mock()
    mock_service.get_data.return_value = {"status": "ok"}

    result = mock_service.get_data()

    assert result["status"] == "ok"
    mock_service.get_data.assert_called_once()
```

#### Async Mocking with AsyncMock

For async functions, use `AsyncMock`:

```python
from unittest.mock import Mock, AsyncMock
import pytest

@pytest.mark.asyncio
async def test_async_mock():
    """Test async functions with AsyncMock."""
    mock_client = Mock()
    mock_client.fetch_data = AsyncMock(return_value={"data": "value"})

    result = await mock_client.fetch_data()

    assert result["data"] == "value"
    mock_client.fetch_data.assert_awaited_once()
```

#### Patching Functions with @patch

Mock external dependencies at the import boundary:

```python
from unittest.mock import patch

@patch('module.external_api_call')
def test_with_patch(mock_api):
    """Test with patched external API."""
    mock_api.return_value = {"status": "success"}

    result = my_function()  # Calls module.external_api_call internally

    mock_api.assert_called_once()
    assert result is not None
```

#### Patching with Context Manager

For more control, use patch as a context manager:

```python
from unittest.mock import patch

def test_with_context():
    """Test with patch context manager."""
    with patch('module.external_api_call') as mock_api:
        mock_api.return_value = {"status": "success"}

        result = my_function()

        mock_api.assert_called_once_with(expected_arg="value")
        assert result is not None
```

#### Mock Multiple Return Values

Use `side_effect` for different return values on successive calls:

```python
from unittest.mock import Mock

def test_side_effect():
    """Test mock with multiple return values."""
    mock = Mock()
    mock.get_next.side_effect = [1, 2, 3, StopIteration]

    assert mock.get_next() == 1
    assert mock.get_next() == 2
    assert mock.get_next() == 3

    with pytest.raises(StopIteration):
        mock.get_next()
```

#### Environment Variable Mocking

Use pytest's `monkeypatch` fixture:

```python
def test_env_variables(monkeypatch):
    """Test with mocked environment variables."""
    monkeypatch.setenv("API_KEY", "test_key_123")
    monkeypatch.setenv("DEBUG_MODE", "true")

    import os
    assert os.getenv("API_KEY") == "test_key_123"
    assert os.getenv("DEBUG_MODE") == "true"
    # Automatic cleanup after test
```

#### Temporary Directory Pattern

Use pytest's `tmp_path` for file operations:

```python
def test_file_operations(tmp_path):
    """Test with temporary directory."""
    # Create test file
    test_file = tmp_path / "data.json"
    test_file.write_text('{"key": "value"}')

    # Verify file exists
    assert test_file.exists()

    # Read and verify content
    import json
    data = json.loads(test_file.read_text())
    assert data["key"] == "value"

    # Automatic cleanup after test
```

---

### Writing Tests with Mocks

#### Example 1: Testing a Function with External API

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

@pytest.mark.unit
@pytest.mark.asyncio
@patch('Tools.adapters.chroma_adapter.CHROMADB_AVAILABLE', True)
async def test_embedding_generation():
    """Test generating embeddings with mocked ChromaDB."""
    # Mock the ChromaDB client
    with patch('chromadb.PersistentClient') as mock_client_class:
        mock_client = Mock()
        mock_collection = Mock()

        # Configure mock behavior
        mock_client_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.add = AsyncMock()

        # Import and test the adapter
        from Tools.adapters.chroma_adapter import ChromaAdapter
        adapter = ChromaAdapter(persist_directory="/tmp/test")

        # Add document (uses mock)
        await adapter.add_document("Test document", metadata={"source": "test"})

        # Verify mock was called correctly
        mock_collection.add.assert_called_once()
```

#### Example 2: Testing with Multiple Fixtures

```python
import pytest

@pytest.mark.unit
def test_client_initialization(mock_anthropic_client, temp_config_dir):
    """Test client initialization with mocked dependencies."""
    # Use temp directory for config
    config_file = temp_config_dir / "client.json"
    config_file.write_text('{"model": "claude-sonnet-4-5-20250929"}')

    # Use mock client
    from core.client import ThanosCLient
    client = ThanosClient(
        config_path=config_file,
        api_client=mock_anthropic_client
    )

    # Verify initialization
    assert client.model == "claude-sonnet-4-5-20250929"
    assert client.api_client is mock_anthropic_client
```

#### Example 3: Testing Async Code with AsyncMock

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_workflow():
    """Test async workflow with mocked async dependencies."""
    # Create mock with async methods
    mock_adapter = Mock()
    mock_adapter.fetch_events = AsyncMock(return_value=[
        {"id": "1", "title": "Meeting"},
        {"id": "2", "title": "Standup"}
    ])
    mock_adapter.process_event = AsyncMock(return_value={"status": "processed"})

    # Import and test
    from core.session_manager import SessionManager
    manager = SessionManager(calendar_adapter=mock_adapter)

    # Test async operations
    events = await manager.fetch_and_process_events()

    # Verify async calls
    mock_adapter.fetch_events.assert_awaited_once()
    assert mock_adapter.process_event.await_count == 2
    assert len(events) == 2
```

#### Example 4: Testing Database Operations

```python
import pytest
import sys
from unittest.mock import Mock, MagicMock

# Mock Neo4j before importing adapter
sys.modules['neo4j'] = MagicMock()

from Tools.adapters.neo4j_adapter import Neo4jAdapter

@pytest.mark.unit
def test_neo4j_operations():
    """Test Neo4j operations with mocked driver."""
    # Create adapter with mock driver
    adapter = Neo4jAdapter(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test"
    )

    # Mock the driver's session
    mock_session = Mock()
    mock_result = Mock()
    mock_result.single.return_value = {"count": 42}
    mock_session.run.return_value = mock_result

    adapter._driver = Mock()
    adapter._driver.session = Mock(return_value=mock_session)

    # Test database operation
    with adapter._driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as count")
        count = result.single()["count"]

    assert count == 42
    mock_session.run.assert_called_once()
```

#### Example 5: Testing with Environment Variables

```python
import pytest

@pytest.mark.unit
def test_api_key_loading(monkeypatch, temp_config_dir):
    """Test API key loading from environment."""
    # Set environment variables
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    monkeypatch.setenv("CONFIG_DIR", str(temp_config_dir))

    # Import after setting env vars
    from core.config import load_config
    config = load_config()

    assert config.api_key == "test-key-123"
    assert config.config_dir == temp_config_dir
```

#### Example 6: Integration Test with Real ChromaDB

```python
import pytest
import tempfile
import shutil

# Check if ChromaDB is available
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

@pytest.fixture
def temp_chroma_dir():
    """Create temporary ChromaDB directory."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.mark.integration
@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="ChromaDB not installed")
def test_chroma_integration(temp_chroma_dir):
    """Test with real ChromaDB instance."""
    import chromadb

    # Create client with temporary storage
    client = chromadb.PersistentClient(path=temp_chroma_dir)
    collection = client.get_or_create_collection("test")

    # Add documents
    collection.add(
        documents=["Test document 1", "Test document 2"],
        ids=["id1", "id2"]
    )

    # Query
    results = collection.query(query_texts=["Test"], n_results=2)

    assert len(results["ids"][0]) == 2
    # Automatic cleanup via fixture
```

---

### Best Practices

**✅ DO:**

1. **Use fixtures for common mocks** - Don't repeat mock setup
   ```python
   @pytest.fixture
   def mock_client():
       client = Mock()
       client.connect.return_value = True
       return client
   ```

2. **Mock at the boundary** - Mock external dependencies, not internal functions
   ```python
   # Good: Mock external API
   @patch('adapters.external_api.fetch_data')

   # Bad: Mock internal helper
   @patch('module.internal_helper')
   ```

3. **Use AsyncMock for async code** - Regular Mock won't work with await
   ```python
   mock.async_method = AsyncMock(return_value="result")
   await mock.async_method()
   ```

4. **Verify mock behavior** - Assert mocks were called correctly
   ```python
   mock_api.assert_called_once_with(expected_arg="value")
   mock_api.assert_awaited_once()  # For AsyncMock
   ```

5. **Use temporary directories** - Never write to fixed paths
   ```python
   def test_file_ops(tmp_path):
       test_file = tmp_path / "test.txt"
       # Automatic cleanup
   ```

**❌ DON'T:**

1. **Don't use real external services in unit tests**
   ```python
   # Bad: Real API call
   result = requests.get("https://api.example.com")

   # Good: Mocked API call
   with patch('requests.get') as mock_get:
       mock_get.return_value.json.return_value = {"data": "value"}
   ```

2. **Don't forget to clean up resources**
   ```python
   # Bad: Manual file creation
   Path("/tmp/test.txt").write_text("test")

   # Good: Use tmp_path fixture
   def test(tmp_path):
       (tmp_path / "test.txt").write_text("test")
   ```

3. **Don't mock what you're testing**
   ```python
   # Bad: Mocking the function under test
   @patch('module.function_to_test')
   def test_function(mock_func):
       # You're not actually testing anything!
   ```

4. **Don't use vague assertions**
   ```python
   # Bad: Vague check
   assert mock.call_count > 0

   # Good: Specific check
   mock.assert_called_once_with(arg="expected_value")
   ```

---

### Quick Reference

**Common patterns at a glance:**

```python
# Basic mock
mock = Mock()
mock.method.return_value = "value"
assert mock.method() == "value"

# Async mock
mock.async_method = AsyncMock(return_value="value")
result = await mock.async_method()

# Patch decorator
@patch('module.function')
def test(mock_func):
    mock_func.return_value = "value"

# Patch context manager
with patch('module.function') as mock_func:
    mock_func.return_value = "value"

# Environment variables
def test(monkeypatch):
    monkeypatch.setenv("VAR", "value")

# Temporary directory
def test(tmp_path):
    file = tmp_path / "test.txt"
    file.write_text("content")

# Using fixtures
def test(mock_anthropic_client, temp_config_dir):
    # Fixtures are automatically injected
    pass

# Module mocking
sys.modules['unavailable_module'] = MagicMock()
```

---

### Additional Resources

For comprehensive mocking documentation, see:
- **[TEST_MOCKING_PATTERNS.md](./TEST_MOCKING_PATTERNS.md)** - Complete mocking reference with all patterns
- **[tests/conftest.py](./tests/conftest.py)** - All shared fixtures
- **[tests/conftest_mcp.py](./tests/conftest_mcp.py)** - MCP-specific fixtures
- **[tests/fixtures/calendar_fixtures.py](./tests/fixtures/calendar_fixtures.py)** - Calendar test helpers

**External documentation:**
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
- [pytest fixtures documentation](https://docs.pytest.org/en/stable/fixture.html)

---

**Next section:** [Coverage Reporting](#coverage-reporting) explains how to measure and improve test coverage.

## Coverage Reporting

Code coverage measures how much of your codebase is executed during testing. This section explains how to generate coverage reports, interpret the metrics, and use coverage data to improve your test suite.

### Overview

**What is coverage?**

Coverage analysis tracks which lines of code are executed when tests run. It helps identify:
- ✅ **Well-tested code** - Code that's covered by tests
- ⚠️ **Untested code** - Code that never executes during tests
- 📊 **Coverage gaps** - Areas where more tests are needed
- 🎯 **Test effectiveness** - How thoroughly your tests exercise the codebase

**Coverage tools:**
- **pytest-cov** - pytest plugin for coverage (installed via requirements-test.txt)
- **coverage.py** - Underlying coverage measurement tool
- **HTML reports** - Interactive, detailed coverage visualization

**Important:** High coverage doesn't guarantee quality tests, but low coverage definitely indicates untested code!

---

### Quick Start: Generate Coverage Report

**Fastest way to see coverage:**

```bash
# Run tests with coverage and generate HTML report
pytest --cov=. --cov-report=html

# Open the report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

This gives you a beautiful, interactive HTML report showing exactly which lines are covered and which aren't.

---

### Generating Coverage Reports

#### Terminal Reports

**Basic coverage output:**
```bash
# Simple coverage summary
pytest --cov=.

# Output:
# ---------- coverage: platform darwin, python 3.11.0 -----------
# Name                                      Stmts   Miss  Cover
# -------------------------------------------------------------
# core/client.py                              156     42    73%
# core/commitment_tracker.py                   89     12    87%
# Tools/adapters/chroma_adapter.py            234     89    62%
# ...
# -------------------------------------------------------------
# TOTAL                                      2456    678    72%
```

**Detailed terminal report with missing lines:**
```bash
# Show which lines are not covered
pytest --cov=. --cov-report=term-missing

# Output:
# Name                                      Stmts   Miss  Cover   Missing
# -----------------------------------------------------------------------
# core/client.py                              156     42    73%   45-52, 78-89, 145
# core/commitment_tracker.py                   89     12    87%   34, 67-71, 98-101
```

This shows exactly which line numbers aren't covered, helping you target new tests effectively.

**Compact terminal output:**
```bash
# Shorter output without line numbers
pytest --cov=. --cov-report=term
```

#### HTML Reports (Recommended)

**Generate interactive HTML report:**
```bash
# Create HTML report in htmlcov/ directory
pytest --cov=. --cov-report=html

# Open in browser
open htmlcov/index.html
```

**What's in the HTML report:**
- **Index page** - Summary of all modules with coverage percentages
- **File pages** - Each source file with line-by-line coverage
- **Color coding:**
  - 🟢 **Green** - Lines covered by tests
  - 🔴 **Red** - Lines not covered
  - 🟡 **Yellow** - Lines partially covered (branches)
  - ⚪ **White** - Non-executable lines (comments, blank lines)
- **Interactive** - Click files to see detailed line coverage
- **Sortable** - Sort by coverage percentage, filename, etc.

**HTML report with unit tests only (faster):**
```bash
# Generate coverage from only unit tests
pytest -m unit --cov=. --cov-report=html
```

#### XML Reports (for CI/CD)

**Generate XML report for CI tools:**
```bash
# Create coverage.xml for CI/CD integration
pytest --cov=. --cov-report=xml

# Often used with coverage badges or quality gates
```

XML reports are machine-readable and work with:
- GitHub Actions coverage reports
- Codecov / Coveralls services
- SonarQube / Code Climate integration
- GitLab coverage visualization

#### JSON Reports (for automation)

**Generate JSON report for programmatic access:**
```bash
# Create coverage.json
pytest --cov=. --cov-report=json
```

Useful for custom scripts or automated analysis.

#### Multiple Report Types

**Generate several report types at once:**
```bash
# Terminal + HTML + XML
pytest --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml

# Or shorter
pytest --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml
```

**Skip coverage output to terminal:**
```bash
# Only generate HTML, don't print to terminal
pytest --cov=. --cov-report=html --cov-report=''
```

---

### Targeting Specific Modules

Instead of measuring coverage for the entire codebase, target specific modules:

#### Single Module Coverage

```bash
# Coverage for core/ module only
pytest --cov=core --cov-report=html

# Coverage for adapters/ module only
pytest --cov=adapters --cov-report=html

# Coverage for Tools/ module only
pytest --cov=Tools --cov-report=html
```

#### Multiple Module Coverage

```bash
# Coverage for core and adapters only
pytest --cov=core --cov=adapters --cov-report=html

# Coverage for specific files
pytest --cov=core/client --cov=core/commitment_tracker --cov-report=html
```

#### Coverage for Specific Test Suite

**Unit tests coverage:**
```bash
# What does our unit test suite cover?
pytest -m unit --cov=. --cov-report=html
```

**Integration tests coverage:**
```bash
# What additional coverage do integration tests provide?
pytest -m integration --cov=. --cov-report=html
```

**Specific test file coverage:**
```bash
# Coverage from running one test file
pytest tests/unit/test_client.py --cov=core/client --cov-report=term-missing
```

This helps answer: "Do I have enough tests for module X?"

---

### Understanding Coverage Metrics

Coverage reports show several key metrics:

#### Statements (Stmts)

**Total number of executable lines** in the code.

```python
# This file has 5 statements:
def add(a, b):          # Statement 1: function definition
    result = a + b      # Statement 2: assignment
    if result > 10:     # Statement 3: if condition
        print("big")    # Statement 4: print
    return result       # Statement 5: return
```

#### Miss

**Number of statements not executed** during tests.

If only 3 of the 5 statements above run during tests, Miss = 2.

#### Cover (Coverage Percentage)

**Percentage of statements executed:**

```
Cover = (Stmts - Miss) / Stmts * 100
```

Example: `(5 - 2) / 5 * 100 = 60%`

**What's a good coverage percentage?**
- **80%+** - Good coverage (recommended minimum)
- **90%+** - Excellent coverage
- **95%+** - Very thorough coverage
- **100%** - Complete coverage (rare and not always necessary)

**Note:** Coverage percentage alone doesn't guarantee quality! You can have 100% coverage with poor tests that don't assert anything meaningful.

#### Branch Coverage

**Branch coverage** tracks whether both paths of conditional statements are tested:

```python
def check_value(x):
    if x > 0:           # Branch point
        return "positive"    # Branch 1
    else:
        return "negative"    # Branch 2
```

Full branch coverage means tests execute both the `if` and `else` paths.

**Enable branch coverage:**
```bash
# Add branch coverage tracking
pytest --cov=. --cov-branch --cov-report=html
```

In the HTML report, yellow highlighting indicates branches that weren't fully tested.

#### Missing Lines

**Specific line numbers not covered:**

```
Missing: 45-52, 78-89, 145
```

This means:
- Lines 45 through 52 not covered (range)
- Lines 78 through 89 not covered (range)
- Line 145 not covered (single line)

Use this to identify exactly where to add tests!

---

### Viewing and Interpreting HTML Reports

#### Opening the HTML Report

After running:
```bash
pytest --cov=. --cov-report=html
```

Open `htmlcov/index.html` in your browser:
```bash
# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html

# Windows
start htmlcov/index.html

# Or use Python's HTTP server
cd htmlcov && python -m http.server 8000
# Then visit http://localhost:8000 in browser
```

#### Understanding the Index Page

**Main dashboard shows:**

1. **Total coverage** - Overall percentage for entire codebase
2. **Module list** - All Python files with individual coverage
3. **Columns:**
   - **Module** - File path
   - **statements** - Total executable lines
   - **missing** - Lines not covered
   - **excluded** - Lines explicitly excluded from coverage
   - **coverage** - Percentage covered

**Visual indicators:**
- 🟢 **Green bar** - High coverage (typically >80%)
- 🟡 **Yellow bar** - Medium coverage (50-80%)
- 🔴 **Red bar** - Low coverage (<50%)

**Sorting:**
- Click column headers to sort
- Find lowest coverage files first
- Identify high-priority areas for new tests

#### Understanding File Detail Pages

Click any module to see line-by-line coverage:

**Color coding:**
```python
# Green (covered) - This line was executed during tests
def covered_function():
    return "tested"

# Red (uncovered) - This line was NOT executed
def uncovered_function():
    return "not tested"

# Yellow (partial) - Only some branches were tested
def partial_coverage(x):
    if x > 0:
        return "positive"  # Covered
    else:
        return "negative"  # Not covered (yellow highlighting on 'if')
```

**Line numbers:**
- Click line numbers to get permalink
- Share specific lines with team members
- Reference in pull request comments

**Context:**
- See surrounding code for context
- Understand why lines might not be covered
- Identify dead code vs. edge cases

#### Finding Coverage Gaps

**Strategy for improving coverage:**

1. **Sort by coverage percentage** - Start with lowest-covered files
2. **Check missing lines** - See what's not tested
3. **Prioritize critical code:**
   - Core business logic (should have >90% coverage)
   - Error handling paths
   - Edge cases and boundary conditions
4. **Ignore less critical code:**
   - CLI argument parsing (hard to test)
   - Debug/logging code
   - Deprecated functions

---

### Coverage Configuration

#### .coveragerc Configuration

Coverage behavior is configured in `.coveragerc` or `pyproject.toml`:

**Example `.coveragerc`:**
```ini
[run]
# Which directories to measure
source = .

# Exclude test files from coverage measurement
omit =
    */tests/*
    */test_*.py
    */__pycache__/*
    */venv/*
    */env/*

# Enable branch coverage
branch = True

[report]
# Precision for coverage percentages
precision = 2

# Show missing line numbers
show_missing = True

# Sort report by coverage percentage
sort = Cover

[html]
# Output directory for HTML reports
directory = htmlcov

[xml]
# Output file for XML reports
output = coverage.xml
```

**Or in `pyproject.toml`:**
```toml
[tool.coverage.run]
source = ["."]
omit = ["*/tests/*", "*/test_*.py", "*/__pycache__/*"]
branch = true

[tool.coverage.report]
precision = 2
show_missing = true
sort = "Cover"

[tool.coverage.html]
directory = "htmlcov"
```

#### Excluding Code from Coverage

**Exclude specific lines:**
```python
def debug_function():
    if DEBUG:  # pragma: no cover
        print("Debug info")
```

The `# pragma: no cover` comment tells coverage to ignore this line.

**Exclude entire blocks:**
```python
if TYPE_CHECKING:  # pragma: no cover
    from typing import SomeType
```

**Exclude functions:**
```python
def deprecated_function():  # pragma: no cover
    """Old function, don't test."""
    pass
```

**When to exclude:**
- Debug/development code
- Type checking imports
- Defensive programming that can't be triggered
- Platform-specific code
- Deprecated functions

**When NOT to exclude:**
- Production code paths
- Error handling
- Business logic
- Anything that runs in production

---

### Setting Coverage Thresholds

#### Fail Tests if Coverage Too Low

**Enforce minimum coverage:**
```bash
# Fail if coverage below 80%
pytest --cov=. --cov-fail-under=80

# Output if fails:
# FAIL Required test coverage of 80% not reached. Total coverage: 72.45%
```

**Use in CI/CD:**
```yaml
# .github/workflows/test.yml
- name: Run tests with coverage threshold
  run: pytest --cov=. --cov-fail-under=80 --cov-report=xml
```

This ensures coverage never drops below acceptable levels.

#### Module-Specific Thresholds

Test specific modules with higher standards:

```bash
# Core module must have 90%+ coverage
pytest tests/unit/test_client.py --cov=core/client --cov-fail-under=90

# Integration tests need at least 70%
pytest -m integration --cov=. --cov-fail-under=70
```

#### Progressive Coverage Goals

**Strategy for improving coverage over time:**

1. **Establish baseline:** `pytest --cov=. --cov-report=term` (say 65%)
2. **Set achievable goal:** `--cov-fail-under=70`
3. **Write tests to reach goal**
4. **Increase threshold:** `--cov-fail-under=75`
5. **Repeat until target reached** (e.g., 85%)

This prevents coverage from decreasing while gradually improving it.

---

### Common Coverage Workflows

#### Development Workflow

**While writing new features:**

```bash
# 1. Run tests for your new module with coverage
pytest tests/unit/test_new_feature.py --cov=core/new_feature --cov-report=term-missing

# 2. See what's not covered
# Missing: 45-52, 89

# 3. Write tests for missing lines
# (add tests)

# 4. Re-run to verify
pytest tests/unit/test_new_feature.py --cov=core/new_feature --cov-report=term-missing

# 5. Repeat until satisfied with coverage
```

#### Pre-Commit Workflow

**Before committing:**

```bash
# Check coverage for changed files
pytest --cov=. --cov-report=term-missing --cov-fail-under=75

# If coverage too low, add tests before committing
```

#### CI/CD Workflow

**In continuous integration:**

```bash
# Run full test suite with coverage
pytest -v \
  --cov=. \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-report=html \
  --cov-fail-under=80

# Upload coverage report to service (e.g., Codecov)
# bash <(curl -s https://codecov.io/bash)
```

#### Coverage Investigation Workflow

**Find and fix coverage gaps:**

```bash
# 1. Generate comprehensive HTML report
pytest --cov=. --cov-report=html --cov-branch

# 2. Open report and identify low-coverage files
open htmlcov/index.html

# 3. For each low-coverage file, run tests and see what's missing
pytest tests/unit/test_low_coverage_module.py --cov=module --cov-report=term-missing -v

# 4. Add tests for uncovered lines
# 5. Verify improvement
pytest --cov=module --cov-report=term-missing
```

---

### Best Practices for Coverage

**✅ DO:**

1. **Aim for 80%+ overall coverage** - Good baseline for quality
   ```bash
   pytest --cov=. --cov-fail-under=80
   ```

2. **Focus on critical code first** - Core business logic needs highest coverage
   ```bash
   pytest --cov=core --cov-fail-under=90
   ```

3. **Use HTML reports for exploration** - Visual interface is easier to navigate
   ```bash
   pytest --cov=. --cov-report=html && open htmlcov/index.html
   ```

4. **Enable branch coverage** - Catch untested conditional paths
   ```bash
   pytest --cov=. --cov-branch --cov-report=html
   ```

5. **Run coverage regularly** - Track trends over time
   ```bash
   # Add to pre-commit hook or CI pipeline
   pytest --cov=. --cov-fail-under=80
   ```

6. **Use coverage to find missing tests** - Not as quality metric alone
   ```bash
   # Find what's not tested, then write meaningful tests
   pytest --cov=. --cov-report=term-missing
   ```

**❌ DON'T:**

1. **Don't obsess over 100% coverage** - Diminishing returns after ~90%
   - Some code is hard to test (CLI parsing, error paths)
   - Focus on meaningful tests, not coverage numbers

2. **Don't test just for coverage** - Write tests that verify behavior
   ```python
   # Bad: Test that adds no value
   def test_coverage_only():
       my_function()  # No assertions!

   # Good: Test that verifies behavior
   def test_behavior():
       result = my_function()
       assert result == expected_value
   ```

3. **Don't ignore coverage in tests themselves** - Tests can have bugs too
   ```bash
   # Consider test quality, not just coverage
   pytest --cov=tests --cov-report=html  # See test coverage
   ```

4. **Don't exclude code without good reason** - `# pragma: no cover` should be rare
   ```python
   # Bad: Excluding production code
   def important_function():  # pragma: no cover
       return critical_calculation()

   # Good: Excluding debug code
   if DEBUG:  # pragma: no cover
       print("Debug output")
   ```

5. **Don't skip edge cases** - High coverage with no edge case tests = false confidence
   ```python
   # Make sure to test boundaries
   def test_edge_cases():
       assert function(0) == expected_zero
       assert function(-1) == expected_negative
       assert function(MAX_INT) == expected_max
   ```

---

### Understanding Coverage Limitations

**What coverage DOES tell you:**
- ✅ Which lines execute during tests
- ✅ Which code paths are completely untested
- ✅ Where to focus testing efforts

**What coverage DOESN'T tell you:**
- ❌ Whether tests are meaningful
- ❌ Whether assertions are correct
- ❌ Whether edge cases are covered
- ❌ Code quality or design issues

**Example:**

```python
def divide(a, b):
    return a / b

# Bad test: 100% coverage but no value
def test_divide():
    result = divide(10, 2)
    # No assertion! Test passes but verifies nothing

# Good test: Same coverage, verifies behavior
def test_divide():
    assert divide(10, 2) == 5
    assert divide(1, 2) == 0.5

# Better test: Also tests edge cases
def test_divide_edge_cases():
    assert divide(10, 2) == 5
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)  # Edge case!
```

All three have 100% coverage, but quality varies dramatically!

---

### Troubleshooting Coverage Issues

#### "Coverage not showing for my module"

**Check --cov path:**
```bash
# Wrong: Module not found
pytest --cov=nonexistent_module

# Right: Valid module path
pytest --cov=core --cov=adapters
```

**Check omit patterns:**
Coverage might be excluding your files. Check `.coveragerc` or `pyproject.toml`.

#### "No coverage data collected"

**Make sure pytest-cov is installed:**
```bash
pip install pytest-cov

# Verify
pytest --version
# Should show: plugins: cov-4.1.0, ...
```

**Check that tests actually run:**
```bash
# This should show tests running
pytest -v --cov=.
```

#### "Coverage seems wrong/inaccurate"

**Clear coverage cache:**
```bash
# Remove old coverage data
rm -rf .coverage htmlcov/ coverage.xml

# Re-run tests
pytest --cov=. --cov-report=html
```

**Check for import-time side effects:**
Code that runs on import may be covered even if not tested:
```python
# This runs when module is imported
print("Module loaded")  # Shows as covered even if not tested
```

#### "HTML report shows red lines that ARE tested"

**Possible causes:**
1. **Tests skip without running code** - Check `pytest.skip()` calls
2. **Code in `if __name__ == "__main__"`** - Not executed during tests
3. **Import guards** - Code behind `if TYPE_CHECKING:` blocks
4. **Defensive code** - Error paths that can't be triggered in tests

#### "Coverage slows down tests significantly"

**Coverage adds overhead:**
```bash
# Tests without coverage: 10 seconds
pytest

# Tests with coverage: 15 seconds
pytest --cov=.
```

**Strategies:**
- Run coverage only when needed, not on every test run
- Use faster coverage: `pytest --cov=. --no-cov-on-fail`
- Target specific modules: `pytest --cov=core` instead of `--cov=.`
- Run in parallel: `pytest -n auto --cov=.`

---

### Quick Reference

**Common coverage commands:**

| Goal | Command |
|------|---------|
| Basic coverage | `pytest --cov=.` |
| HTML report | `pytest --cov=. --cov-report=html` |
| Show missing lines | `pytest --cov=. --cov-report=term-missing` |
| Branch coverage | `pytest --cov=. --cov-branch` |
| Specific module | `pytest --cov=core` |
| Multiple modules | `pytest --cov=core --cov=adapters` |
| Coverage threshold | `pytest --cov=. --cov-fail-under=80` |
| XML for CI | `pytest --cov=. --cov-report=xml` |
| Multiple reports | `pytest --cov=. --cov-report=html --cov-report=xml` |
| Unit tests coverage | `pytest -m unit --cov=. --cov-report=html` |

**Quick workflow:**
```bash
# Generate and view HTML report (recommended)
pytest --cov=. --cov-report=html && open htmlcov/index.html

# Terminal report with missing lines
pytest --cov=. --cov-report=term-missing

# Enforce minimum coverage
pytest --cov=. --cov-fail-under=80
```

---

### Summary

Coverage reporting helps you:
1. 📊 **Measure test completeness** - See what's tested and what's not
2. 🎯 **Identify gaps** - Find code that needs more tests
3. 📈 **Track progress** - Monitor coverage trends over time
4. ✅ **Enforce standards** - Use thresholds to maintain quality

**Remember:**
- Coverage is a **tool**, not a **goal**
- High coverage ≠ good tests (but low coverage = untested code)
- Focus on **meaningful tests**, not just hitting coverage numbers
- Use HTML reports for detailed analysis
- Aim for 80%+ overall coverage with 90%+ for critical code

**Next section:** [Troubleshooting](#troubleshooting) addresses common issues when running tests.

## Troubleshooting

This section covers common issues you might encounter when running tests and how to resolve them.

### Quick Troubleshooting Checklist

Before diving into specific errors, try these common fixes:

```bash
# 1. Update test dependencies
pip install -r requirements-test.txt

# 2. Clear pytest cache
pytest --cache-clear

# 3. Verify Python version (3.8+ required)
python --version

# 4. Run a simple test to verify setup
pytest tests/unit/test_client.py -v
```

---

### Missing Dependencies

#### Error: ModuleNotFoundError: No module named 'pytest'

**Cause:** Test dependencies not installed.

**Solution:**
```bash
# Install all test dependencies
pip install -r requirements-test.txt

# Or install individually
pip install pytest pytest-cov pytest-mock pytest-asyncio
```

**Verification:**
```bash
pytest --version
# Should show: pytest 7.4.0 or higher
```

---

#### Error: ModuleNotFoundError: No module named 'chromadb'

**Cause:** ChromaDB is an optional dependency not installed.

**Solution:**

**Option 1: Skip ChromaDB tests (recommended for most development)**
```bash
# ChromaDB tests are integration tests, skip them
pytest -m "not integration"

# Or run only unit tests
pytest -m unit
```

**Option 2: Install ChromaDB for integration testing**
```bash
pip install chromadb

# Then run integration tests
pytest -m integration
```

**Note:** Most tests mock ChromaDB, so you don't need it installed for normal development.

---

#### Error: No module named 'google.auth' or 'googleapiclient'

**Cause:** Google Calendar API dependencies not installed.

**Solution:**

These are automatically mocked in unit tests. If you see this error:

1. **For unit tests:** The test should be using `sys.modules` mocking. Example:
   ```python
   # This should already be in the test file
   sys.modules["google.oauth2.credentials"] = Mock()
   sys.modules["googleapiclient.discovery"] = Mock()
   ```

2. **For integration tests:** Install Google Calendar dependencies:
   ```bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   ```

3. **Or skip these tests:**
   ```bash
   pytest -m "not requires_google_calendar"
   ```

---

#### Error: coverage.py error: No data was collected

**Cause:** Coverage can't find source code, or no tests ran.

**Solution:**

1. **Check if tests actually ran:**
   ```bash
   # Run without coverage first
   pytest -v
   ```

2. **Use correct coverage path:**
   ```bash
   # Correct: specify source directory
   pytest --cov=. --cov-report=term

   # Or target specific modules
   pytest --cov=Tools --cov=Engine
   ```

3. **Check .coveragerc configuration:**
   ```bash
   # If .coveragerc exists, ensure [run] section includes:
   # source = .
   # omit = tests/*, venv/*, .venv/*
   ```

---

### API Key and Credential Errors

#### Tests with @pytest.mark.requires_openai are skipped

**Cause:** OpenAI API key not configured.

**Expected Behavior:** This is normal! Tests requiring OpenAI are **automatically skipped** if no API key is set.

**To run OpenAI tests (optional):**
```bash
# Set your API key
export OPENAI_API_KEY='sk-your-key-here'

# Run OpenAI tests
pytest -m requires_openai -v
```

**See test output:**
```
tests/integration/test_chroma_adapter_integration.py::test_semantic_search SKIPPED
Reason: OpenAI API key not configured
```

**Note:**
- These tests will incur API costs if you run them
- Most development doesn't require running these tests
- CI/CD should skip these tests unless specifically configured

---

#### Tests with @pytest.mark.requires_google_calendar are skipped

**Cause:** Google Calendar credentials not configured.

**Expected Behavior:** This is normal! Tests requiring Google Calendar are **automatically skipped** if credentials aren't set.

**To run Google Calendar tests (optional):**

1. **Set up credentials (see External Dependencies section)**
2. **Set environment variables:**
   ```bash
   export GOOGLE_CALENDAR_CLIENT_ID='your-client-id'
   export GOOGLE_CALENDAR_CLIENT_SECRET='your-client-secret'
   export GOOGLE_CALENDAR_REDIRECT_URI='http://localhost:8080/oauth2callback'
   ```

3. **Run the tests:**
   ```bash
   pytest -m requires_google_calendar -v
   ```

**Note:** Use a test Google account, not your production account!

---

#### Error: pytest.skip("Google Calendar credentials not available...")

**Cause:** Test is checking for credentials and explicitly skipping.

**This is expected!** The test is working correctly by skipping when credentials aren't available.

**If you want to run the test:**
- Follow the setup in the "External Dependencies" section
- Or accept that these tests are optional for most development

---

### Database Connection Errors

#### Error: neo4j.exceptions.ServiceUnavailable: Failed to establish connection

**Cause:** Test is trying to connect to a real Neo4j database.

**Solution:**

**This should NOT happen!** All Neo4j connections are mocked in the test suite.

1. **Check the test is using mocks:**
   ```python
   # Tests should have this pattern:
   sys.modules["neo4j"] = Mock()
   ```

2. **If you see this in a new test you're writing:**
   - Add Neo4j mocking in the test file
   - See `tests/unit/test_neo4j_session_pool.py` for examples

3. **For integration tests:**
   - Neo4j is still mocked, not a real connection
   - Check conftest.py fixtures

**Note:** The Thanos test suite does NOT require a real Neo4j database.

---

#### Error: Connection to ChromaDB failed

**Cause:** Integration test trying to use ChromaDB, but it's not available.

**Solution:**

1. **For development, skip integration tests:**
   ```bash
   pytest -m "not integration"
   ```

2. **To run ChromaDB integration tests:**
   ```bash
   # Install ChromaDB
   pip install chromadb

   # Run integration tests
   pytest tests/integration/test_chroma_adapter_integration.py -v
   ```

**Note:** ChromaDB integration tests use temporary, in-memory instances - no persistent database needed.

---

### Import Errors

#### Error: ImportError: cannot import name 'X' from 'Tools.adapters.Y'

**Cause:** Import path incorrect or module not in PYTHONPATH.

**Solution:**

1. **Verify you're running pytest from project root:**
   ```bash
   # Check current directory
   pwd
   # Should be: /path/to/Thanos

   # Run from project root
   cd /path/to/Thanos
   pytest
   ```

2. **Check PYTHONPATH (usually not needed):**
   ```bash
   # pytest should find modules automatically
   # If not, try:
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   pytest
   ```

3. **Verify the module exists:**
   ```bash
   # Check the file exists
   ls -l Tools/adapters/
   ```

4. **Check for circular imports:**
   ```bash
   # Run a single test file to isolate the issue
   pytest tests/unit/test_client.py -v
   ```

---

#### Error: ImportError: attempted relative import with no known parent package

**Cause:** Running test file directly instead of using pytest.

**Solution:**

**Don't do this:**
```bash
python tests/unit/test_client.py  # ❌ Wrong
```

**Do this:**
```bash
pytest tests/unit/test_client.py  # ✅ Correct
```

**Why:** Pytest sets up the import paths correctly; running Python directly doesn't.

---

#### Error: fixture 'X' not found

**Cause:** Fixture defined in wrong conftest.py or not in test's scope.

**Solution:**

1. **Check fixture location:**
   ```bash
   # Fixtures in tests/conftest.py are available to all tests
   # Fixtures in tests/unit/conftest.py only available to tests/unit/
   grep -r "def mock_anthropic_client" tests/
   ```

2. **Common fixtures and their locations:**
   - `mock_anthropic_client` → `tests/conftest.py`
   - `mock_client_session` → `tests/conftest_mcp.py`
   - `get_mock_event` → `tests/fixtures/calendar_fixtures.py`

3. **For calendar fixtures, import explicitly:**
   ```python
   # In your test file
   from tests.fixtures.calendar_fixtures import get_mock_event

   def test_something():
       event = get_mock_event()  # Function, not fixture
   ```

4. **Create conftest.py if missing:**
   ```bash
   # For a new test directory
   touch tests/new_directory/conftest.py
   ```

5. **Check fixture spelling:**
   ```python
   # Common typo:
   def test_something(mock_antropic_client):  # ❌ Wrong
   def test_something(mock_anthropic_client):  # ✅ Correct
   ```

---

### Async Test Errors

#### Error: RuntimeError: no running event loop

**Cause:** Async test missing `@pytest.mark.asyncio` decorator.

**Solution:**

Add the `@pytest.mark.asyncio` marker:

```python
# ❌ Wrong - missing marker
async def test_async_function():
    result = await some_async_function()
    assert result is not None

# ✅ Correct - with marker
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

**Check pytest-asyncio is installed:**
```bash
pip install pytest-asyncio
pytest --version  # Should show pytest-asyncio plugin
```

---

#### Error: coroutine 'X' was never awaited

**Cause:** Called async function without `await` keyword.

**Solution:**

```python
# ❌ Wrong - missing await
@pytest.mark.asyncio
async def test_async_function():
    result = some_async_function()  # Wrong!
    assert result is not None

# ✅ Correct - with await
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()  # Correct!
    assert result is not None
```

---

#### Error: Task was destroyed but it is pending!

**Cause:** Async test not properly cleaning up tasks.

**Solution:**

1. **Use AsyncMock for mocking async functions:**
   ```python
   from unittest.mock import AsyncMock

   @pytest.mark.asyncio
   async def test_with_async_mock():
       mock_func = AsyncMock(return_value="result")
       result = await mock_func()
       mock_func.assert_awaited_once()
   ```

2. **Ensure all async operations complete:**
   ```python
   @pytest.mark.asyncio
   async def test_cleanup():
       client = AsyncClient()
       try:
           result = await client.fetch_data()
       finally:
           await client.close()  # Ensure cleanup
   ```

3. **Check conftest.py event loop configuration:**
   ```bash
   grep -A 10 "event_loop" tests/conftest_mcp.py
   ```

---

#### Error: assert_awaited_once() vs assert_called_once()

**Cause:** Using wrong assertion method for async mocks.

**Solution:**

```python
from unittest.mock import AsyncMock, Mock

# For async functions - use AsyncMock and assert_awaited
mock_async = AsyncMock()
await mock_async()
mock_async.assert_awaited_once()  # ✅ Correct

# For regular functions - use Mock and assert_called
mock_sync = Mock()
mock_sync()
mock_sync.assert_called_once()  # ✅ Correct

# ❌ Wrong combinations:
# mock_async.assert_called_once()  # Wrong!
# mock_sync.assert_awaited_once()  # Wrong!
```

---

### Test Collection and Discovery Errors

#### Warning: PytestUnknownMarkWarning: Unknown pytest.mark.X

**Cause:** Marker used but not registered in pytest.ini.

**Solution:**

1. **Check if marker is in pytest.ini:**
   ```bash
   grep "markers" pytest.ini
   ```

2. **Add missing marker to pytest.ini:**
   ```ini
   markers =
       unit: Unit tests (fast, isolated)
       integration: Integration tests (slower, external dependencies)
       slow: Slow running tests
       your_new_marker: Description of your marker
   ```

3. **Or use `--strict-markers` to enforce registration:**
   ```bash
   pytest --strict-markers  # Fail on unknown markers
   ```

---

#### Error: No tests ran / Empty test suite

**Cause:** Pytest can't find test files or functions.

**Solution:**

1. **Check test discovery patterns:**
   ```bash
   # pytest.ini specifies:
   # python_files = test_*.py
   # python_classes = Test*
   # python_functions = test_*
   ```

2. **Verify file names follow convention:**
   ```bash
   # ✅ These will be discovered:
   # test_client.py
   # test_integration_calendar.py

   # ❌ These will NOT be discovered:
   # client_test.py
   # my_tests.py
   ```

3. **Check function names:**
   ```python
   # ✅ Discovered
   def test_something():
       pass

   class TestClient:
       def test_init(self):
           pass

   # ❌ NOT discovered
   def check_something():  # Missing 'test_' prefix
       pass

   class ClientTests:  # Should be 'TestClient'
       pass
   ```

4. **See what pytest would collect:**
   ```bash
   pytest --collect-only
   ```

---

### Performance and Timeout Issues

#### Tests are very slow

**Solution:**

1. **Run tests in parallel:**
   ```bash
   # Install pytest-xdist
   pip install pytest-xdist

   # Run with parallel workers
   pytest -n auto
   ```

2. **Skip slow tests during development:**
   ```bash
   pytest -m "not slow"
   ```

3. **Identify slowest tests:**
   ```bash
   pytest --durations=10
   ```

4. **Run only unit tests (fastest):**
   ```bash
   pytest -m unit
   ```

---

#### Test hangs or times out

**Cause:** Test waiting indefinitely for async operation or external service.

**Solution:**

1. **Add timeout to specific test:**
   ```python
   @pytest.mark.timeout(5)  # 5 second timeout
   def test_something():
       pass
   ```

2. **Check for unmocked external calls:**
   ```bash
   # Run with verbose output to see where it hangs
   pytest -v -s tests/path/to/test.py
   ```

3. **For async tests, ensure proper event loop:**
   ```python
   @pytest.mark.asyncio
   async def test_with_timeout():
       import asyncio
       try:
           result = await asyncio.wait_for(
               some_async_function(),
               timeout=5.0
           )
       except asyncio.TimeoutError:
           pytest.fail("Operation timed out")
   ```

---

### Coverage Reporting Issues

#### Coverage report shows 0% for everything

**Cause:** Coverage not measuring the right files, or tests not running.

**Solution:**

1. **Verify tests ran successfully:**
   ```bash
   pytest -v  # First run without coverage
   ```

2. **Check coverage source path:**
   ```bash
   # Use explicit source paths
   pytest --cov=Tools --cov=Engine --cov-report=term
   ```

3. **Check omit patterns in .coveragerc:**
   ```ini
   [run]
   source = .
   omit =
       tests/*
       venv/*
       .venv/*
       */site-packages/*
   ```

4. **Ensure source files are being imported:**
   ```bash
   # Run with coverage debug
   coverage debug sys
   ```

---

#### Can't see HTML coverage report

**Cause:** HTML report not generated or browser can't open it.

**Solution:**

1. **Generate HTML report explicitly:**
   ```bash
   pytest --cov=. --cov-report=html
   ```

2. **Check htmlcov directory was created:**
   ```bash
   ls -la htmlcov/
   ```

3. **Open report manually:**
   ```bash
   # macOS
   open htmlcov/index.html

   # Linux
   xdg-open htmlcov/index.html

   # Windows
   start htmlcov/index.html
   ```

---

### General Debugging Tips

#### Run a single test for debugging

```bash
# Run one specific test
pytest tests/unit/test_client.py::TestThanos::test_initialization -v

# Run with print statements visible
pytest tests/unit/test_client.py::test_specific -v -s

# Drop into debugger on failure
pytest tests/unit/test_client.py --pdb

# Drop into debugger on first line of test
pytest tests/unit/test_client.py --trace
```

---

#### See detailed error output

```bash
# Show full diff for assertions
pytest -vv

# Show full traceback
pytest --tb=long

# Show local variables in traceback
pytest -l

# Combine options
pytest -vv -l --tb=long
```

---

#### Check test environment

```bash
# Show pytest version and plugins
pytest --version

# Show which tests would run
pytest --collect-only

# Show available fixtures
pytest --fixtures

# Show available markers
pytest --markers
```

---

### Still Having Issues?

If you're still encountering problems:

1. **Clear all caches:**
   ```bash
   # Clear pytest cache
   pytest --cache-clear

   # Remove __pycache__ directories
   find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

   # Remove .pyc files
   find . -type f -name "*.pyc" -delete
   ```

2. **Reinstall test dependencies:**
   ```bash
   pip uninstall pytest pytest-cov pytest-mock pytest-asyncio -y
   pip install -r requirements-test.txt
   ```

3. **Check Python version:**
   ```bash
   python --version
   # Requires Python 3.8 or higher
   ```

4. **Run from project root:**
   ```bash
   cd /path/to/Thanos
   pwd  # Verify location
   pytest
   ```

5. **Check for conflicting packages:**
   ```bash
   pip list | grep -i pytest
   pip list | grep -i test
   ```

6. **Consult existing test documentation:**
   - [TEST_INVENTORY.md](./TEST_INVENTORY.md) - What tests exist
   - [TEST_DEPENDENCIES.md](./TEST_DEPENDENCIES.md) - Dependency details
   - [TEST_MOCKING_PATTERNS.md](./TEST_MOCKING_PATTERNS.md) - How mocking works
   - [tests/integration/README.md](./tests/integration/README.md) - Integration test specifics

7. **Check recent changes:**
   ```bash
   git status
   git diff
   ```

---

**Remember:** Most test errors are due to:
1. Missing `@pytest.mark.asyncio` for async tests
2. Running from wrong directory
3. Missing test dependencies
4. Typos in fixture names

The test suite is designed to be offline-first with extensive mocking, so you should rarely need external services!

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
