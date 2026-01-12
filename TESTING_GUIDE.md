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

*This section will be completed in subtask 2.2*

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
