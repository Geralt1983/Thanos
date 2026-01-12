# Thanos Testing Strategy

**A high-level testing philosophy and roadmap for the Thanos project**

**Last Updated:** 2026-01-12

---

## Overview

This document outlines the testing philosophy, principles, and strategic goals for the Thanos project. For practical "how-to" instructions on running tests, see the **[TESTING_GUIDE.md](TESTING_GUIDE.md)**.

**Purpose of this document:**
- Define our testing philosophy and guiding principles
- Document current test coverage status and identify gaps
- Set measurable coverage goals and targets
- Establish testing standards for new code
- Provide strategic direction for test infrastructure improvements

---

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Testing Principles](#testing-principles)
3. [Current Test Coverage Status](#current-test-coverage-status)
4. [Test Coverage Goals](#test-coverage-goals)
5. [Testing Standards for New Code](#testing-standards-for-new-code)
6. [Test Categories and Strategy](#test-categories-and-strategy)
7. [External Dependencies Strategy](#external-dependencies-strategy)
8. [CI/CD Testing Strategy](#cicd-testing-strategy)
9. [Coverage Improvement Roadmap](#coverage-improvement-roadmap)
10. [Testing Resources](#testing-resources)

---

## Testing Philosophy

### Core Beliefs

**1. Tests Enable Confidence and Velocity**
- Well-tested code allows for fearless refactoring and rapid iteration
- Tests serve as executable documentation of system behavior
- Comprehensive test suites reduce production incidents and enable faster releases

**2. Offline-First Testing**
- Tests should run without external dependencies by default
- Mocking external services enables fast, reliable, deterministic tests
- Integration tests with real services are valuable but should be optional and clearly marked

**3. Fast Feedback Loops**
- Unit tests should execute in milliseconds, not seconds
- Developers should be able to run relevant tests in <5 seconds during development
- Full test suite should complete in reasonable time (<2 minutes for CI)

**4. Pragmatic Coverage**
- 100% coverage is not the goal; testing critical paths and edge cases is
- Focus on high-value tests: core logic, error handling, integration points
- Use coverage tools to find gaps, not as a quality metric
- Some code (config files, simple getters) may not need explicit tests

**5. Testing is a First-Class Activity**
- Tests are code too: they should be maintainable, readable, and well-structured
- Test quality matters as much as production code quality
- Investing in test infrastructure and tooling pays long-term dividends

---

## Testing Principles

### Design Principles

**1. Test Behavior, Not Implementation**
```python
# ✅ GOOD: Tests observable behavior
def test_user_authentication_success():
    result = authenticate_user("valid@email.com", "correct_password")
    assert result.is_authenticated
    assert result.user_id is not None

# ❌ BAD: Tests internal implementation details
def test_user_authentication_calls_hash_function():
    with patch('auth.bcrypt.checkpw') as mock_hash:
        authenticate_user("valid@email.com", "password")
        assert mock_hash.called
```

**2. Arrange-Act-Assert (AAA) Pattern**
```python
def test_commitment_streak_calculation():
    # Arrange: Set up test data
    tracker = CommitmentTracker()
    commitment = tracker.create_commitment("Exercise", "daily")

    # Act: Perform the action being tested
    streak = commitment.calculate_streak()

    # Assert: Verify the expected outcome
    assert streak.current == 0
    assert streak.longest == 0
```

**3. Test Independence**
- Each test should be completely independent
- Tests should not rely on execution order
- Use fixtures and setup/teardown to manage state
- Avoid global state and shared mutable data

**4. Clear Test Names**
```python
# ✅ GOOD: Describes what is being tested and expected outcome
def test_mcp_bridge_reconnects_after_connection_loss():
    pass

def test_commitment_validation_rejects_invalid_recurrence_pattern():
    pass

# ❌ BAD: Vague or implementation-focused names
def test_bridge():
    pass

def test_commitment_1():
    pass
```

**5. Mock at System Boundaries**
- Mock external services (APIs, databases, file systems)
- Don't mock your own code unless it has complex external dependencies
- Use real implementations for internal dependencies when possible

**6. One Logical Assertion Per Test**
- Each test should verify one logical concept
- Multiple `assert` statements are fine if they verify the same concept
- Split complex scenarios into multiple focused tests

---

## Current Test Coverage Status

### Test Infrastructure Metrics

**Test File Distribution** (as of 2026-01-12):

| Category | Count | Location | Status |
|----------|-------|----------|--------|
| **Unit Tests** | 33 files | `tests/unit/` | ✅ Active |
| **Integration Tests** | 7 files | `tests/integration/` | ✅ Active |
| **Root-Level Tests** | 6 files | `tests/` | ✅ Active |
| **Benchmarks** | 5 files | `tests/benchmarks/` | ✅ Active |
| **Supporting Files** | 3 files | `tests/`, `tests/fixtures/` | ✅ Active |
| **Total Test Files** | 51 files | | |

**Test Execution Metrics**:
- **Total Tests**: 1,225 test cases collected
- **Test Collection Errors**: 8 files (import issues - see [Known Issues](#known-issues))
- **Test Framework**: pytest with comprehensive marker system
- **Coverage Tool**: pytest-cov configured and ready

### Coverage by Component

**Well-Covered Components** (>70% estimated coverage):
- ✅ **Commitment Tracking System** - Comprehensive unit and integration tests
- ✅ **MCP Bridge and Discovery** - Full protocol implementation coverage
- ✅ **Adapters** - Good coverage for Oura, WorkOS, ChromaDB, Google Calendar
- ✅ **Neo4j Session Management** - Extensive edge case and security tests
- ✅ **Client Infrastructure** - LiteLLM client and usage tracking well-tested
- ✅ **Command Routing** - Command handlers and routing logic covered

**Moderately Covered Components** (30-70% estimated coverage):
- ⚠️ **Pattern Recognition** - Core logic tested, some analyzers need more coverage
- ⚠️ **Error Handling** - Basic tests exist, more edge cases needed
- ⚠️ **Orchestration** - Main flows tested, some advanced scenarios missing

**Under-Covered Components** (<30% estimated coverage):
- ⚠️ **Session Manager** - Import errors preventing test execution
- ⚠️ **Context Manager** - Import errors preventing test execution
- ⚠️ **Message Handler** - Import errors preventing test execution
- ⚠️ **CLI Interface** - Limited test coverage
- ⚠️ **State Management** - Needs comprehensive testing
- ⚠️ **Memory System** - Needs more integration tests

### Known Issues

**Test Collection Errors** (8 files):
```
ERROR tests/integration/test_pattern_recognition_integration.py
ERROR tests/integration/test_real_data_validation.py
ERROR tests/unit/test_context_manager.py
ERROR tests/unit/test_error_logger.py
ERROR tests/unit/test_litellm_client.py
ERROR tests/unit/test_message_handler.py
ERROR tests/unit/test_retry_middleware.py
ERROR tests/unit/test_session_manager.py
```

**Root Cause**: Module import errors (ModuleNotFoundError: No module named 'Tools.session_manager')

**Impact**: These tests are not currently executable, reducing effective coverage

**Remediation Plan**:
1. Fix import paths or module structure issues (Priority: High)
2. Re-run full test suite to get accurate coverage baseline
3. Update coverage metrics after fixes are applied

---

## Test Coverage Goals

### Short-Term Goals (Q1 2026)

**Primary Objectives**:
1. ✅ **Document Test Infrastructure** - COMPLETED
   - ✅ Create comprehensive testing guide (TESTING_GUIDE.md)
   - ✅ Document all test files and coverage areas (TEST_INVENTORY.md)
   - ✅ Document mocking patterns and fixtures (TEST_MOCKING_PATTERNS.md)
   - ✅ Document external dependencies (TEST_DEPENDENCIES.md)

2. 🎯 **Fix Test Collection Errors** - IN PROGRESS
   - Target: 0 collection errors
   - Current: 8 collection errors
   - Action: Fix import paths in 8 failing test files
   - Timeline: Complete by end of Q1 2026

3. 🎯 **Establish Coverage Baseline** - PENDING
   - Target: Measure actual line/branch coverage for all components
   - Current: No accurate baseline due to collection errors
   - Action: Run `pytest --cov=. --cov-report=html` after fixing errors
   - Timeline: Complete within 1 week of fixing collection errors

4. 🎯 **Implement Automated Testing in CI** - PENDING
   - Target: All PRs run unit tests automatically
   - Current: Only linting in CI (lint.yml workflow)
   - Action: Add test.yml workflow to run unit tests on all PRs
   - Timeline: Complete by end of Q1 2026

### Medium-Term Goals (Q2-Q3 2026)

**Coverage Targets**:
- **Critical Components**: ≥80% line coverage
  - Commitment tracking system
  - MCP bridge and adapter layer
  - Session and state management
  - Core orchestration logic

- **Important Components**: ≥70% line coverage
  - Pattern recognition and analytics
  - Error handling and logging
  - Client infrastructure
  - Command handlers

- **Supporting Components**: ≥50% line coverage
  - CLI interface
  - Configuration management
  - Utility functions

**Quality Targets**:
- All tests passing consistently (no flaky tests)
- Test execution time: <2 minutes for full suite
- Integration test coverage for all major user workflows
- Performance benchmarks for critical paths

### Long-Term Goals (Q4 2026 and beyond)

**Strategic Objectives**:
1. **Continuous Coverage Improvement**
   - Achieve and maintain ≥75% overall line coverage
   - Achieve ≥65% branch coverage for complex logic
   - Zero known critical bugs in production

2. **Advanced Testing Capabilities**
   - Property-based testing for core algorithms
   - Load/stress testing for scalability validation
   - Mutation testing to verify test quality
   - Visual regression testing for UI components

3. **Testing Culture**
   - All new features include comprehensive tests
   - Test-driven development (TDD) for critical components
   - Regular test reviews and refactoring
   - Testing best practices in contributor documentation

---

## Testing Standards for New Code

### Minimum Requirements

**All new code MUST include:**

1. **Unit Tests**
   - Test all public functions and methods
   - Cover happy path and common error cases
   - Include edge cases and boundary conditions
   - Use `@pytest.mark.unit` marker
   - Target: ≥80% line coverage for new code

2. **Integration Tests (where applicable)**
   - Test integration points between components
   - Verify end-to-end workflows for new features
   - Use `@pytest.mark.integration` marker
   - Can use mocks or real services (prefer mocks for CI)

3. **Documentation**
   - Clear test names describing what is being tested
   - Comments explaining complex test setup or assertions
   - Update relevant documentation (TESTING_GUIDE.md, etc.)

### Code Review Checklist

**Before approving a PR, verify:**

- [ ] All new functions/classes have corresponding unit tests
- [ ] Tests follow AAA (Arrange-Act-Assert) pattern
- [ ] Tests are independent and don't rely on execution order
- [ ] Appropriate markers are used (`@pytest.mark.unit`, etc.)
- [ ] External dependencies are mocked appropriately
- [ ] Tests have clear, descriptive names
- [ ] All tests pass locally and in CI
- [ ] Coverage for new code is ≥80% (run `pytest --cov=new_module`)
- [ ] No obvious test gaps or missing edge cases

### When to Write Integration Tests

**Write integration tests when:**
- ✅ Adding new adapter integrations (e.g., new API service)
- ✅ Implementing complex workflows involving multiple components
- ✅ Adding database schema migrations or query changes
- ✅ Implementing authentication/authorization logic
- ✅ Adding new MCP server integrations

**Integration test requirements:**
- Use `@pytest.mark.integration` marker
- Use `@pytest.mark.slow` if test takes >5 seconds
- Use `@pytest.mark.requires_*` if external service required
- Provide clear setup instructions in test docstrings
- Ensure tests can run with mocked dependencies for CI

### When to Write Property-Based Tests

**Consider property-based tests (using Hypothesis) for:**
- Parsers and serialization logic
- Mathematical calculations and algorithms
- Data validation and transformation logic
- Stateful systems with invariants

### Performance Testing Standards

**Write performance tests/benchmarks when:**
- Implementing algorithms with performance requirements
- Optimizing critical paths (hot loops, database queries)
- Adding caching or performance optimization features

**Performance test requirements:**
- Place in `tests/benchmarks/` directory
- Use pytest-benchmark or similar framework
- Document performance baseline and targets
- Run benchmarks before and after optimization

---

## Test Categories and Strategy

### Unit Tests (`@pytest.mark.unit`)

**Purpose**: Verify individual components in isolation

**Characteristics**:
- Fast execution (<100ms per test ideally)
- All external dependencies mocked
- Focused on single function/class/module
- Deterministic and repeatable
- No network calls, no database, no file I/O (except temp files)

**When to Use**:
- Testing business logic and algorithms
- Testing data validation and transformation
- Testing error handling and edge cases
- Testing internal helper functions

**Best Practices**:
- Mock at system boundaries (APIs, databases, filesystem)
- Use pytest fixtures for common test data
- Follow AAA pattern strictly
- One logical concept per test

### Integration Tests (`@pytest.mark.integration`)

**Purpose**: Verify interactions between components

**Characteristics**:
- Slower execution (1-10 seconds per test)
- May use real or mocked external dependencies
- Tests multiple components together
- More complex setup and teardown

**When to Use**:
- Testing adapter integrations with services
- Testing workflows across multiple modules
- Testing database operations with real/temp databases
- Testing MCP server communication

**Best Practices**:
- Use fixtures to manage test data and cleanup
- Prefer mocked dependencies for CI (use markers for real services)
- Test both success and failure scenarios
- Document any required environment setup

### Slow Tests (`@pytest.mark.slow`)

**Purpose**: Mark tests that take significant time to execute

**Characteristics**:
- Execution time >5 seconds
- Often involve I/O, network, or heavy computation
- May use real external services
- Should be skippable for fast development loops

**When to Use**:
- Performance benchmarks
- Large dataset processing
- Real API integration tests
- Comprehensive end-to-end workflows

**Best Practices**:
- Only mark as slow if truly necessary
- Consider optimization before marking slow
- Run separately from main test suite (`pytest -m "not slow"`)
- Include in nightly CI runs or pre-release validation

### API Tests (`@pytest.mark.api`, `@pytest.mark.requires_*`)

**Purpose**: Tests requiring real external service APIs

**Markers**:
- `@pytest.mark.requires_openai` - Requires OpenAI API key
- `@pytest.mark.requires_google_calendar` - Requires Google Calendar credentials
- `@pytest.mark.api` - General API requirement

**Characteristics**:
- Require valid API credentials
- Auto-skip if credentials not configured
- May incur API costs
- Subject to rate limits and network conditions

**When to Use**:
- Validating real API integrations
- Testing against live service changes
- Pre-release validation
- Manual testing during development

**Best Practices**:
- Always provide mocked alternative for CI
- Use test accounts, never production credentials
- Implement rate limiting and retry logic
- Document costs and quota implications
- Use sparingly (prefer mocked tests for regular development)

---

## External Dependencies Strategy

### Philosophy: Graceful Degradation

**Core Principle**: Tests should run successfully without external dependencies by default.

**Implementation**:
1. **Mock by Default**: All external services mocked in unit tests
2. **Optional Integration**: Real service tests marked and auto-skip if unavailable
3. **Clear Marking**: Use pytest markers to indicate dependency requirements
4. **Documentation**: Clear setup instructions for developers who want to run integration tests

### Dependency Categories

**1. Fully Mocked (No Setup Required)**:
- Neo4j database
- Anthropic API
- Oura Ring API
- PostgreSQL / WorkOS
- Internal services and modules

**Strategy**: Mock at import time using `sys.modules` or fixtures. Tests run offline.

**2. Optional Services (Auto-Skip)**:
- OpenAI API (marker: `@pytest.mark.requires_openai`)
- Google Calendar API (marker: `@pytest.mark.requires_google_calendar`)
- ChromaDB (installable with `pip install chromadb`)

**Strategy**: Tests automatically skip if credentials/services not available. Integration tests use temp instances.

**3. Test Utilities**:
- pytest, pytest-cov, pytest-mock, pytest-asyncio
- All managed through `requirements-test.txt`

**Strategy**: Required for all test execution. Documented in TESTING_GUIDE.md.

### Mocking Standards

**When Mocking External Services**:
1. Use fixtures defined in `conftest.py` for consistency
2. Mock at the adapter boundary (not deep in implementation)
3. Return realistic mock data (use `tests/fixtures/` helpers)
4. Test both success and error responses
5. Document mock behavior in test docstrings

**Available Mock Fixtures**:
- `mock_anthropic_client` - Mocked Anthropic API client
- `mock_anthropic_response` - Sample API responses
- `sample_messages` - Realistic message data
- `temp_config_dir` - Temporary configuration directory
- `mock_mcp_client` - Mocked MCP client
- Plus 20+ additional fixtures (see TEST_MOCKING_PATTERNS.md)

---

## CI/CD Testing Strategy

### Current State

**Existing CI Workflows**:
- ✅ **lint.yml**: Runs Ruff linter on all Python files
  - Triggers: Pull requests, pushes to main
  - Purpose: Enforce code style and catch syntax errors
  - Status: Active and working

**Missing CI Workflows**:
- ⚠️ **No automated test execution** in CI
- ⚠️ **No coverage reporting** in CI
- ⚠️ **No integration test validation** for releases

### Recommended CI Strategy

**1. Unit Tests on Every PR** (Fast, Required)
```yaml
name: Unit Tests
on: [pull_request, push]
runs-on: ubuntu-latest

steps:
  - Run unit tests only: pytest -m unit
  - Execution time: <1 minute
  - Blocks merge if failing
  - No external dependencies required
```

**2. Full Test Suite on Main** (Comprehensive, Informational)
```yaml
name: Full Test Suite
on: [push to main]
runs-on: ubuntu-latest

steps:
  - Run all tests: pytest -m "not slow and not api"
  - Generate coverage report
  - Upload to Codecov/Coveralls
  - Execution time: <3 minutes
  - Informational (doesn't block)
```

**3. Integration Tests Nightly** (Thorough, Scheduled)
```yaml
name: Nightly Integration Tests
on: [schedule: '0 0 * * *']
runs-on: ubuntu-latest

steps:
  - Run all tests including slow: pytest
  - Run integration tests with real services (if configured)
  - Performance benchmarks
  - Execution time: <10 minutes
  - Alert on failures
```

### CI Best Practices

**DO**:
- ✅ Run unit tests on every PR (fast feedback)
- ✅ Skip slow and API tests in CI by default
- ✅ Use matrix testing for multiple Python versions (3.8, 3.9, 3.10, 3.11)
- ✅ Cache dependencies to speed up CI
- ✅ Generate and track coverage over time
- ✅ Fail PR if new code has <80% coverage
- ✅ Run linters before tests (fail fast)

**DON'T**:
- ❌ Run tests requiring real API keys in CI (use mocks)
- ❌ Run slow tests on every PR (run nightly instead)
- ❌ Ignore flaky tests (fix or remove them)
- ❌ Let test execution time grow unbounded (optimize or parallelize)
- ❌ Skip tests on main branch
- ❌ Allow coverage to decrease without justification

### Coverage Tracking

**Tools**:
- **Codecov**: Cloud coverage tracking with PR comments
- **Coveralls**: Alternative coverage tracking service
- **Coverage.py**: Local HTML reports for investigation

**Targets**:
- New code: ≥80% coverage required
- Overall project: ≥75% coverage goal
- Critical components: ≥80% coverage enforced

**Implementation**:
```yaml
- name: Run tests with coverage
  run: pytest --cov=. --cov-report=xml --cov-fail-under=75

- name: Upload to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

---

## Coverage Improvement Roadmap

### Phase 1: Fix Foundation (Q1 2026)

**Objectives**:
1. ✅ **Create comprehensive testing documentation** - COMPLETED
   - ✅ TESTING_GUIDE.md with practical instructions
   - ✅ TESTING_STRATEGY.md with strategic direction
   - ✅ TEST_INVENTORY.md cataloging all tests
   - ✅ TEST_DEPENDENCIES.md documenting dependencies
   - ✅ TEST_MOCKING_PATTERNS.md with patterns and examples

2. 🎯 **Fix test collection errors** - HIGH PRIORITY
   - Fix 8 files with ModuleNotFoundError
   - Verify all 1,225 tests can execute
   - Target completion: Within 2 weeks

3. 🎯 **Establish accurate coverage baseline**
   - Run full coverage analysis
   - Document coverage by component
   - Identify critical gaps

4. 🎯 **Implement basic CI testing**
   - Add test.yml workflow for unit tests
   - Set up coverage reporting
   - Target completion: End of Q1 2026

### Phase 2: Fill Critical Gaps (Q2 2026)

**Objectives**:
1. **Increase coverage for under-tested components**
   - Session Manager: Target 70% coverage
   - Context Manager: Target 70% coverage
   - Message Handler: Target 70% coverage
   - CLI Interface: Target 60% coverage
   - State Management: Target 60% coverage

2. **Add missing integration tests**
   - End-to-end workflow tests for major features
   - Real integration tests for all adapters (marked optional)
   - Pattern recognition integration scenarios

3. **Improve test quality**
   - Refactor complex tests for clarity
   - Add property-based tests for algorithms
   - Remove or fix any flaky tests

### Phase 3: Enhance and Optimize (Q3 2026)

**Objectives**:
1. **Advanced testing capabilities**
   - Property-based testing with Hypothesis
   - Performance benchmarking framework
   - Load testing for scalability validation

2. **Optimize test execution**
   - Parallelize slow tests
   - Optimize setup/teardown
   - Target: Full suite under 2 minutes

3. **Improve developer experience**
   - Pre-commit hooks for test execution
   - Test failure analysis tooling
   - Better error messages and debugging

### Phase 4: Maintain and Evolve (Q4 2026+)

**Objectives**:
1. **Sustain high coverage**
   - Enforce 80% coverage for all new code
   - Regular coverage audits
   - Automated coverage regression detection

2. **Continuous improvement**
   - Regular test review and refactoring
   - Update test patterns and fixtures
   - Add tests for newly discovered edge cases

3. **Advanced quality measures**
   - Mutation testing to verify test effectiveness
   - Automated flaky test detection
   - Test performance monitoring

---

## Testing Resources

### Documentation

**Primary Resources**:
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Practical guide for running tests
  - Quick start and common commands
  - Test execution with various filters
  - Coverage reporting instructions
  - Troubleshooting common issues
  - CI/CD integration examples

- **[TEST_INVENTORY.md](TEST_INVENTORY.md)** - Complete test file catalog
  - All 51 test files documented
  - Organized by category and subsystem
  - Brief description of what each tests

- **[TEST_DEPENDENCIES.md](TEST_DEPENDENCIES.md)** - External dependency guide
  - Setup instructions for all external services
  - Mock strategies for each dependency
  - Environment variable documentation

- **[TEST_MOCKING_PATTERNS.md](TEST_MOCKING_PATTERNS.md)** - Mocking patterns and examples
  - 35+ available fixtures documented
  - Common mocking patterns with examples
  - Best practices and anti-patterns

**Configuration Files**:
- **pytest.ini** - pytest configuration and markers
- **requirements-test.txt** - Test dependencies
- **pyproject.toml** - Tool configuration (pytest, coverage)
- **.coveragerc** - Coverage configuration (if present)

### Pytest Markers Reference

Quick reference for test filtering:

```bash
# Run only unit tests (fast, offline)
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests (recommended for development)
pytest -m "not slow"

# Skip API tests (no external services)
pytest -m "not api"

# Skip tests requiring credentials
pytest -m "not requires_openai and not requires_google_calendar"

# Run fast offline tests only
pytest -m "unit and not slow"

# View all available markers
pytest --markers
```

### Useful Commands

**Development Workflow**:
```bash
# Fast feedback during development
pytest -m unit -x --lf

# Run tests for specific module
pytest tests/unit/test_commitment_tracker.py -v

# Run with coverage for specific module
pytest tests/unit/test_commitment_tracker.py --cov=Tools/commitment_tracker

# Debug failing test
pytest tests/unit/test_commitment_tracker.py::test_name -vv -s --pdb
```

**Coverage Analysis**:
```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Check coverage for specific module
pytest --cov=Tools/commitment_tracker --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=. --cov-fail-under=75
```

**CI/CD Commands**:
```bash
# Run tests as CI would (fast)
pytest -m "unit and not slow" --cov=. --cov-report=xml

# Run full suite (comprehensive)
pytest --cov=. --cov-report=html --cov-report=term

# Run with strict markers (catch typos)
pytest --strict-markers
```

### External Resources

**pytest Documentation**:
- [pytest Official Docs](https://docs.pytest.org/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest Markers](https://docs.pytest.org/en/stable/mark.html)
- [pytest Parametrize](https://docs.pytest.org/en/stable/parametrize.html)

**Testing Best Practices**:
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)
- [Effective Python Testing With Pytest](https://realpython.com/pytest-python-testing/)
- [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

**Mocking and Fixtures**:
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-mock Plugin](https://pytest-mock.readthedocs.io/)
- [Mocking in Python](https://realpython.com/python-mock-library/)

**Coverage Tools**:
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [pytest-cov Plugin](https://pytest-cov.readthedocs.io/)
- [Codecov](https://about.codecov.io/)

---

## Conclusion

Testing is a critical investment in the long-term health and maintainability of the Thanos project. This strategy document provides:

✅ **Clear Philosophy** - Why we test and what principles guide our testing approach
✅ **Current Status** - Honest assessment of where we are (51 test files, 1,225 tests, some gaps)
✅ **Measurable Goals** - Specific, achievable targets for coverage and quality
✅ **Practical Standards** - Clear requirements for new code and code reviews
✅ **Strategic Roadmap** - Phased plan for continuous improvement

**Next Steps**:
1. Fix test collection errors (8 files) - HIGH PRIORITY
2. Establish accurate coverage baseline
3. Implement automated testing in CI
4. Follow coverage improvement roadmap
5. Enforce testing standards for all new code

**Remember**:
- Tests enable confidence and velocity
- Focus on high-value tests, not arbitrary coverage percentages
- Invest in test infrastructure and documentation
- Make testing a first-class activity in development workflow

For practical instructions on running tests, see **[TESTING_GUIDE.md](TESTING_GUIDE.md)**.

---

**Document Maintenance**: This strategy should be reviewed and updated quarterly to reflect:
- Progress on coverage goals
- New testing challenges and solutions
- Changes to testing infrastructure
- Lessons learned from testing initiatives

**Questions or Suggestions?** Create an issue or PR with the `testing` label.
