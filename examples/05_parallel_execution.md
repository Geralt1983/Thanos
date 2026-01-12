# Example 5: Parallel Test Execution

This example shows how to run tests in parallel to speed up execution.

## Why Parallel Execution?

Running tests in parallel can significantly reduce total execution time, especially for large test suites:

- **Sequential**: 45 seconds
- **Parallel (4 workers)**: 15 seconds (3x faster!)

---

## Basic Parallel Execution

### Prerequisites

Install pytest-xdist:

```bash
pip install pytest-xdist
```

This is included in `requirements-test.txt`, so you likely already have it.

### Command

```bash
pytest -n auto
```

The `-n auto` flag automatically detects your CPU cores and creates that many worker processes.

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0, xdist-3.5.0
gw0 [1225] / gw1 [1225] / gw2 [1225] / gw3 [1225]
.......................................................................... [  5%]
.......................................................................... [ 11%]
.......................................................................... [ 17%]
.......................................................................... [ 23%]
.......................................................................... [ 29%]
.......................................................................... [ 35%]
.......................................................................... [ 41%]
.......................................................................... [ 47%]
.......................................................................... [ 53%]
.......................................................................... [ 59%]
.......................................................................... [ 65%]
.......................................................................... [ 71%]
.......................................................................... [ 77%]
.......................................................................... [ 83%]
.......................................................................... [ 89%]
.......................................................................... [ 95%]
...................................................                       [100%]

========================= 1225 passed, 4 skipped in 15.42s ============================
```

### What Changed

- **gw0 [1225] / gw1 [1225] / gw2 [1225] / gw3 [1225]** - Four worker processes (gw = gateway worker)
- **15.42s vs 45s** - Execution time reduced by ~66%!

---

## Specifying Number of Workers

### Command: 2 Workers

```bash
pytest -n 2
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0, xdist-3.5.0
gw0 [1225] / gw1 [1225]
.......................................................................... [  5%]
[... output ...]
========================= 1225 passed, 4 skipped in 24.18s ============================
```

### Command: 8 Workers

```bash
pytest -n 8
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0, xdist-3.5.0
gw0 [1225] / gw1 [1225] / gw2 [1225] / gw3 [1225] / gw4 [1225] / gw5 [1225] / gw6 [1225] / gw7 [1225]
.......................................................................... [  5%]
[... output ...]
========================= 1225 passed, 4 skipped in 13.67s ============================
```

### Choosing Worker Count

| Workers | Best For | Notes |
|---------|----------|-------|
| `-n auto` | **Recommended** - General use | Auto-detects CPU cores |
| `-n 2` | CI environments with limited resources | Conservative, low overhead |
| `-n 4` | Typical developer machines | Good balance |
| `-n 8` | High-end machines, large test suites | Diminishing returns beyond CPU count |

---

## Parallel Execution with Coverage

Combining parallel execution with coverage reporting.

### Command

```bash
pytest -n auto --cov=. --cov-report=html
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0, xdist-3.5.0
gw0 [1225] / gw1 [1225] / gw2 [1225] / gw3 [1225]
.......................................................................... [  5%]
[... output ...]
========================= 1225 passed, 4 skipped in 18.89s ============================

----------- coverage: platform darwin, python 3.11.5-final-0 -----------
Coverage HTML written to dir htmlcov

TOTAL                                    8456    658    92%
```

### Notes on Coverage + Parallel

- **Slightly slower** - 18.89s vs 15.42s (coverage adds overhead)
- **Still faster than sequential** - 18.89s vs 48s sequential with coverage
- **Coverage is accurate** - pytest-cov handles parallel execution correctly

---

## Parallel Execution by Category

### Unit Tests in Parallel

```bash
pytest -n auto -m unit
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0, xdist-3.5.0
gw0 [1225] / gw1 [1225] / gw2 [1225] / gw3 [1225]
collected 1225 items / 188 deselected / 1037 selected

.......................................................................... [  7%]
[... output ...]
========================= 1037 passed, 188 deselected in 7.23s ==========================
```

**Result**: 7.23s vs 18.42s sequential (2.5x faster!)

---

## Load Distribution Strategies

pytest-xdist distributes tests across workers using different strategies.

### Default: Load Balancing (Recommended)

```bash
pytest -n auto --dist=load
```

- Tests distributed dynamically as workers become available
- Faster workers get more tests
- **Best for**: Mixed test speeds (some fast, some slow)

### Load File (Group by Module)

```bash
pytest -n auto --dist=loadfile
```

- All tests from a file run on the same worker
- Maintains test isolation within files
- **Best for**: Tests with shared fixtures or state

### Load Group (Custom Groups)

```bash
pytest -n auto --dist=loadgroup
```

- Tests grouped by `@pytest.mark.xdist_group` marker
- **Best for**: Tests that must run together (e.g., database tests)

Example:

```python
import pytest

@pytest.mark.xdist_group("database")
def test_db_insert():
    pass

@pytest.mark.xdist_group("database")
def test_db_query():
    pass
```

---

## When NOT to Use Parallel Execution

### 1. Debugging Failures

```bash
# DON'T: Hard to see which test failed
pytest -n auto -v

# DO: Run sequentially for clearer output
pytest -v
```

### 2. Tests with Shared Resources

If tests modify shared files, databases, or global state:

```bash
# Sequential to avoid race conditions
pytest tests/integration/test_database.py
```

### 3. Very Small Test Suites

```bash
# Small suite (< 10 tests): Overhead not worth it
pytest tests/unit/test_small_module.py  # 0.5s sequential
pytest -n auto tests/unit/test_small_module.py  # 0.8s parallel (slower!)
```

### 4. Analyzing Output in Detail

```bash
# DON'T: Verbose output is jumbled with parallel execution
pytest -n auto -vv

# DO: Run sequentially for readable output
pytest -vv
```

---

## Troubleshooting Parallel Execution

### Issue 1: Tests Fail in Parallel but Pass Sequentially

**Symptom**:
```bash
pytest tests/unit/test_mymodule.py  # ✅ Passes
pytest -n auto tests/unit/test_mymodule.py  # ❌ Fails
```

**Causes**:
- Tests sharing global state
- Tests modifying the same files
- Tests with timing dependencies

**Solution**:
- Isolate test data (use fixtures with unique identifiers)
- Use temporary directories per test
- Fix race conditions

### Issue 2: "OSError: [Errno 24] Too many open files"

**Symptom**:
```bash
pytest -n 8
OSError: [Errno 24] Too many open files
```

**Solution**:
```bash
# Reduce worker count
pytest -n 4

# Or increase file descriptor limit (macOS/Linux)
ulimit -n 4096
```

### Issue 3: One Worker Hangs

**Symptom**:
```
gw0 [1225] / gw1 [1225] / gw2 [1225] / gw3 [hang...]
```

**Causes**:
- Slow/hanging test
- Deadlock in test code
- Infinite loop

**Solution**:
```bash
# Add timeout to identify hanging tests
pytest -n auto --timeout=30

# Or run with verbose to see which test hangs
pytest -n auto -v
```

---

## Performance Comparison

Real measurements from Thanos test suite:

| Configuration | Time | Speedup |
|---------------|------|---------|
| Sequential | 45.32s | 1.0x (baseline) |
| `-n 2` | 24.18s | 1.9x |
| `-n 4` | 15.42s | 2.9x |
| `-n auto` (4 cores) | 15.42s | 2.9x |
| `-n 8` | 13.67s | 3.3x |
| `-n auto` with coverage | 18.89s | 2.4x |

**Observations**:
- Sweet spot is around 4 workers for this machine
- Beyond CPU count, diminishing returns
- Coverage adds ~20% overhead even with parallel

---

## Recommended Workflows

### Development: Fast Feedback

```bash
# Run unit tests in parallel
pytest -n auto -m unit
```

**Time**: ~7s (vs 18s sequential)

### Pre-Commit: Full Suite

```bash
# Run all tests in parallel with coverage
pytest -n auto --cov=. --cov-report=html
```

**Time**: ~19s (vs 48s sequential)

### CI/CD: Comprehensive

```bash
# Parallel with all reporting
pytest -n auto --cov=. --cov-report=term --cov-report=xml --junitxml=junit.xml
```

**Time**: ~21s (vs 52s sequential)

### Debugging: Sequential

```bash
# No parallel for clarity
pytest -vv --tb=short
```

---

## Configuration in pytest.ini

Make parallel execution default:

```ini
[pytest]
addopts =
    -n auto
    --dist=load
```

Now just run `pytest` and it automatically uses parallel execution!

**Note**: You can override with `-n 0` to force sequential:

```bash
pytest -n 0  # Force sequential even with addopts
```

---

## Tips

1. **Use `-n auto` as default** - It adapts to your machine
2. **Parallel + coverage works** - pytest-cov handles it correctly
3. **Sequential for debugging** - Much easier to read output
4. **Watch for flaky tests** - Parallel execution can expose hidden dependencies
5. **Monitor resource usage** - More workers ≠ always faster
6. **CI benefits most** - CI machines often have many cores

---

## Related Documentation

- [TESTING_GUIDE.md - Parallel Execution](../TESTING_GUIDE.md#parallel-execution)
- [01_running_all_tests.md](01_running_all_tests.md)
- [04_troubleshooting_failed_test.md](04_troubleshooting_failed_test.md)
