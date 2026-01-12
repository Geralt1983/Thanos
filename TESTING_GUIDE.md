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
