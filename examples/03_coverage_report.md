# Example 3: Coverage Report

This example shows how to generate and interpret test coverage reports.

## Example 3a: Terminal Coverage Report

The simplest way to see coverage.

### Command

```bash
pytest --cov=. --cov-report=term
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1225 items

tests/unit/test_commitment_tracker.py .....................                        [  1%]
tests/unit/test_task_management.py ..........................                      [  3%]
[... output truncated ...]

========================= 1225 passed, 4 skipped in 48.21s ============================

----------- coverage: platform darwin, python 3.11.5-final-0 -----------
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
Tools/__init__.py                          15      0   100%
Tools/aggregation.py                      245     18    93%
Tools/anthropic_client.py                 186     12    94%
Tools/calendar_integration.py             234     45    81%
Tools/commitment_tracker.py               156      8    95%
Tools/health_metrics.py                   198     32    84%
Tools/journal_manager.py                  142     15    89%
Tools/mcp_client.py                       312     24    92%
Tools/memory_manager.py                   178     22    88%
Tools/pattern_recognition.py              267     54    80%
Tools/plugin_system.py                    145     18    88%
Tools/priority_ranking.py                 123      6    95%
Tools/state_manager.py                    198     28    86%
Tools/task_management.py                  234     19    92%
Tools/template_engine.py                  167     14    92%
Tools/usage_tracker.py                    189     11    94%
Tools/voice_interface.py                  134     28    79%
commands/__init__.py                       45      3    93%
commands/briefing.py                      156     24    85%
commands/commit.py                         98      8    92%
[... more files ...]
-----------------------------------------------------------
TOTAL                                    8456    658    92%
```

### Understanding the Output

#### Column Meanings

- **Stmts** (Statements) - Total number of executable code statements in the file
- **Miss** (Missed) - Number of statements not executed by any test
- **Cover** (Coverage %) - Percentage of statements executed: `(Stmts - Miss) / Stmts * 100`

#### Example: Tools/commitment_tracker.py
```
Tools/commitment_tracker.py     156      8    95%
```
- 156 total statements
- 8 statements not covered by tests
- 95% coverage (148 out of 156 statements executed)

#### Total Summary
```
TOTAL                           8456    658    92%
```
- **92% overall coverage** - Very good! Most projects aim for 80-90%
- 658 statements across the entire codebase are not covered by tests

---

## Example 3b: HTML Coverage Report (Recommended)

The most detailed and useful coverage report format.

### Command

```bash
pytest --cov=. --cov-report=html
```

### Sample Output

```
================================== test session starts ===================================
[... test output ...]
========================= 1225 passed, 4 skipped in 48.21s ============================

----------- coverage: platform darwin, python 3.11.5-final-0 -----------
Coverage HTML written to dir htmlcov
```

### Opening the Report

```bash
# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html

# Windows
start htmlcov/index.html
```

### HTML Report Features

The HTML report provides:

1. **Interactive File Browser**
   - Click any file to see line-by-line coverage
   - Sort by filename, statements, coverage percentage

2. **Color-Coded Lines**
   - **Green** - Executed by tests ✅
   - **Red** - Not executed by tests ❌
   - **Yellow** - Partially executed (e.g., only one branch of an if/else)
   - **Gray** - Not executable (comments, blank lines, etc.)

3. **Coverage Details**
   - See exact lines that need test coverage
   - Identify missing branches in conditional logic
   - Find untested exception handlers

### Example: Viewing a Specific File

When you open `Tools/calendar_integration.py` in the HTML report, you might see:

```python
# Line 45 - Green background (covered)
def sync_calendar_events(self):
    """Sync events from Google Calendar"""

# Line 48 - Red background (not covered)
    if not self.credentials:
        raise ValueError("No credentials configured")

# Line 51 - Green background (covered)
    events = self.client.fetch_events()

# Line 54 - Red background (not covered)
    except APIError as e:
        logger.error(f"Calendar sync failed: {e}")
        raise
```

This tells you:
- The main sync flow is tested ✅
- Error handling for missing credentials is NOT tested ❌
- Error handling for API failures is NOT tested ❌

---

## Example 3c: Coverage for Specific Module

Generate coverage for just one module.

### Command

```bash
pytest tests/unit/test_commitment_tracker.py --cov=Tools.commitment_tracker --cov-report=term-missing
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 21 items

tests/unit/test_commitment_tracker.py .....................                      [100%]

========================= 21 passed in 2.15s ============================

----------- coverage: platform darwin, python 3.11.5-final-0 -----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
Tools/commitment_tracker.py         156      8    95%   234-237, 298-301
---------------------------------------------------------------
TOTAL                               156      8    95%
```

### Understanding "Missing" Column

The **Missing** column shows the exact line numbers not covered:
- **234-237** - Lines 234 through 237 need tests
- **298-301** - Lines 298 through 301 need tests

This is extremely useful for targeted test writing!

---

## Example 3d: Coverage with Branch Coverage

Include branch coverage to find untested conditional paths.

### Command

```bash
pytest --cov=. --cov-report=term --cov-branch
```

### Sample Output

```
----------- coverage: platform darwin, python 3.11.5-final-0 -----------
Name                                    Stmts   Miss Branch  BrPart  Cover
---------------------------------------------------------------------------
Tools/commitment_tracker.py               156      8     42       6    94%
Tools/task_management.py                  234     19     68      12    90%
Tools/mcp_client.py                       312     24     98      18    88%
---------------------------------------------------------------------------
TOTAL                                    8456    658   2134     286    89%
```

### Understanding Branch Coverage

- **Branch** - Total number of conditional branches (if/else, try/except, etc.)
- **BrPart** (Branch Partial) - Branches where only one path was taken
- **Cover** - Includes both statement and branch coverage

#### Example: Tools/commitment_tracker.py
```
Stmts   Miss  Branch  BrPart  Cover
  156      8      42       6    94%
```
- 42 conditional branches total
- 6 branches only partially tested (e.g., if tested but not else)
- 94% overall coverage (down from 95% statement-only coverage)

**Branch partial** example:
```python
if user.is_authenticated:  # ← This branch
    process_data()         # ← Only this path tested
else:
    raise AuthError()      # ← This path NOT tested (BrPart = 1)
```

---

## Example 3e: Setting Coverage Thresholds

Fail the test suite if coverage drops below a threshold.

### Command

```bash
pytest --cov=. --cov-report=term --cov-fail-under=80
```

### Sample Output (Passing)

```
========================= 1225 passed, 4 skipped in 48.21s ============================

----------- coverage: platform darwin, python 3.11.5-final-0 -----------
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
[... files ...]
-----------------------------------------------------------
TOTAL                                    8456    658    92%

Required test coverage of 80.0% reached. Total coverage: 92.00%
```

✅ Coverage is 92%, exceeds 80% threshold

### Sample Output (Failing)

```
========================= 1225 passed, 4 skipped in 48.21s ============================

----------- coverage: platform darwin, python 3.11.5-final-0 -----------
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
[... files ...]
-----------------------------------------------------------
TOTAL                                    8456    658    78%

FAIL Required test coverage of 80%, not reached. Total coverage: 78.00%
```

❌ Coverage is 78%, below 80% threshold. This will cause CI to fail!

---

## Interpreting Coverage Numbers

### Coverage Levels

| Coverage % | Interpretation | Action |
|------------|----------------|--------|
| **90-100%** | Excellent | Maintain this level |
| **80-89%** | Good | Standard for production code |
| **70-79%** | Fair | Improve for critical modules |
| **Below 70%** | Poor | Prioritize adding tests |

### What Good Coverage Looks Like

✅ **High-value code is well tested**
- Core business logic: 90%+
- API endpoints: 85%+
- Data processing: 85%+

✅ **Edge cases are covered**
- Error handling paths tested
- Boundary conditions tested
- All branches of conditionals tested

### What Coverage Doesn't Tell You

❌ **Coverage is NOT quality**
- 100% coverage doesn't mean bug-free code
- Tests might not test the right things
- Tests might not have proper assertions

❌ **Some low coverage is OK**
- Generated code
- Simple getters/setters
- Deprecated code
- Development utilities

---

## Common Coverage Workflows

### 1. Development: Check Local Changes

```bash
# Before making changes
pytest tests/unit/test_mymodule.py --cov=Tools.mymodule --cov-report=term-missing

# After making changes
pytest tests/unit/test_mymodule.py --cov=Tools.mymodule --cov-report=term-missing

# Compare the "Missing" lines to see what needs tests
```

### 2. Pre-Commit: Verify Coverage Threshold

```bash
# Ensure coverage meets minimum threshold before committing
pytest --cov=. --cov-report=term --cov-fail-under=80
```

### 3. Investigation: Find Untested Code

```bash
# Generate HTML report
pytest --cov=. --cov-report=html

# Open and browse for red lines
open htmlcov/index.html
```

### 4. CI/CD: Generate Multiple Report Formats

```bash
# Terminal for logs, HTML for artifacts, XML for coverage services
pytest --cov=. --cov-report=term --cov-report=html --cov-report=xml
```

---

## Tips

1. **Use HTML reports for investigation** - Much easier to find gaps than terminal output
2. **Use term-missing for quick checks** - Shows line numbers directly in terminal
3. **Don't chase 100% coverage** - Focus on high-value code first
4. **Branch coverage reveals more** - Finds untested conditional paths
5. **Coverage trends matter** - Watch for decreasing coverage over time
6. **Configure in pytest.ini** - Set default coverage options project-wide

## Configuration Example

Add to `pytest.ini`:

```ini
[pytest]
addopts =
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

Now just run `pytest` and coverage is automatic!

---

## Related Documentation

- [TESTING_GUIDE.md - Coverage Reporting](../TESTING_GUIDE.md#coverage-reporting)
- [01_running_all_tests.md](01_running_all_tests.md)
- [04_troubleshooting_failed_test.md](04_troubleshooting_failed_test.md)
