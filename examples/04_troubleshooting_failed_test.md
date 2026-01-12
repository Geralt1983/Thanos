# Example 4: Troubleshooting a Failed Test

This example walks through debugging a failed test from discovery to resolution.

## Scenario: Test Fails After Code Change

You've just modified `Tools/commitment_tracker.py` and now a test is failing.

---

## Step 1: Identify the Failure

### Command

```bash
pytest tests/unit/test_commitment_tracker.py
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 21 items

tests/unit/test_commitment_tracker.py ..................F..                      [100%]

======================================== FAILURES ========================================
________________________ TestCommitmentTracker.test_update_commitment _________________________

self = <tests.unit.test_commitment_tracker.TestCommitmentTracker object at 0x105a3c4d0>

    def test_update_commitment(self):
        """Test updating an existing commitment"""
        tracker = CommitmentTracker()

        # Create initial commitment
        commitment_id = tracker.create_commitment(
            title="Daily Exercise",
            frequency="daily",
            target_days=30
        )

        # Update the commitment
        updated = tracker.update_commitment(
            commitment_id=commitment_id,
            title="Morning Exercise",
            target_days=60
        )

>       assert updated["title"] == "Morning Exercise"
E       AssertionError: assert 'Daily Exercise' != 'Morning Exercise'
E         - Morning Exercise
E         + Daily Exercise

tests/unit/test_commitment_tracker.py:87: AssertionError
=========================== 1 failed, 20 passed in 3.12s ==============================
```

### What This Tells You

1. **Test Location**: `tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment`
2. **Problem**: The `title` wasn't updated - it's still "Daily Exercise" instead of "Morning Exercise"
3. **Line Number**: The assertion failed at line 87
4. **Status**: 1 test failed, 20 passed

---

## Step 2: Run with More Verbosity

Get more context about the failure.

### Command

```bash
pytest tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment -v
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1 item

tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment FAILED [100%]

======================================== FAILURES ========================================
________________________ TestCommitmentTracker.test_update_commitment _________________________

self = <tests.unit.test_commitment_tracker.TestCommitmentTracker object at 0x105a3c4d0>

    def test_update_commitment(self):
        """Test updating an existing commitment"""
        tracker = CommitmentTracker()

        # Create initial commitment
        commitment_id = tracker.create_commitment(
            title="Daily Exercise",
            frequency="daily",
            target_days=30
        )

        # Update the commitment
        updated = tracker.update_commitment(
            commitment_id=commitment_id,
            title="Morning Exercise",
            target_days=60
        )

>       assert updated["title"] == "Morning Exercise"
E       AssertionError: assert 'Daily Exercise' != 'Morning Exercise'
E         - Morning Exercise
E         + Daily Exercise

tests/unit/test_commitment_tracker.py:87: AssertionError
=========================== short test summary info ===================================
FAILED tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment
=========================== 1 failed in 0.82s ==============================
```

---

## Step 3: Add Print Debugging

Sometimes you need to see the actual values.

### Modified Test (Temporarily)

```python
def test_update_commitment(self):
    """Test updating an existing commitment"""
    tracker = CommitmentTracker()

    commitment_id = tracker.create_commitment(
        title="Daily Exercise",
        frequency="daily",
        target_days=30
    )

    # Add debug output
    print(f"\n🐛 Created commitment: {tracker.get_commitment(commitment_id)}")

    updated = tracker.update_commitment(
        commitment_id=commitment_id,
        title="Morning Exercise",
        target_days=60
    )

    # Add debug output
    print(f"🐛 Updated result: {updated}")
    print(f"🐛 Current state: {tracker.get_commitment(commitment_id)}")

    assert updated["title"] == "Morning Exercise"
```

### Command

```bash
pytest tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment -s
```

Note: `-s` flag shows print output

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1 item

tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment
🐛 Created commitment: {'id': 'cmt_123', 'title': 'Daily Exercise', 'frequency': 'daily', 'target_days': 30}
🐛 Updated result: {'id': 'cmt_123', 'title': 'Daily Exercise', 'frequency': 'daily', 'target_days': 60}
🐛 Current state: {'id': 'cmt_123', 'title': 'Daily Exercise', 'frequency': 'daily', 'target_days': 60}
FAILED

======================================== FAILURES ========================================
[... same failure output ...]
```

### Insight

Now we can see:
- ✅ `target_days` **was** updated (30 → 60)
- ❌ `title` was **not** updated ("Daily Exercise" unchanged)
- The bug is in `update_commitment()` method - it's not updating the title field

---

## Step 4: Use Python Debugger (pdb)

Drop into interactive debugger at the failure point.

### Command

```bash
pytest tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment --pdb
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1 item

tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> entering PDB >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
> /Users/jeremy/Projects/Thanos/tests/unit/test_commitment_tracker.py(87)test_update_commitment()
-> assert updated["title"] == "Morning Exercise"
(Pdb) updated
{'id': 'cmt_123', 'title': 'Daily Exercise', 'frequency': 'daily', 'target_days': 60}
(Pdb) tracker.get_commitment(commitment_id)
{'id': 'cmt_123', 'title': 'Daily Exercise', 'frequency': 'daily', 'target_days': 60}
(Pdb) # Let's check the update_commitment method
(Pdb) import inspect
(Pdb) print(inspect.getsource(tracker.update_commitment))
    def update_commitment(self, commitment_id: str, **kwargs) -> Dict[str, Any]:
        """Update commitment fields"""
        commitment = self.commitments.get(commitment_id)
        if not commitment:
            raise ValueError(f"Commitment {commitment_id} not found")

        # BUG: Only updating target_days, not other fields!
        if "target_days" in kwargs:
            commitment["target_days"] = kwargs["target_days"]

        return commitment

(Pdb) # Found the bug! The method only handles target_days
(Pdb) quit
```

### What We Learned

The `update_commitment()` method only updates `target_days`, ignoring other fields like `title`. This is the root cause!

---

## Step 5: Fix the Code

### Original Code (Buggy)

```python
def update_commitment(self, commitment_id: str, **kwargs) -> Dict[str, Any]:
    """Update commitment fields"""
    commitment = self.commitments.get(commitment_id)
    if not commitment:
        raise ValueError(f"Commitment {commitment_id} not found")

    # BUG: Only updating target_days
    if "target_days" in kwargs:
        commitment["target_days"] = kwargs["target_days"]

    return commitment
```

### Fixed Code

```python
def update_commitment(self, commitment_id: str, **kwargs) -> Dict[str, Any]:
    """Update commitment fields"""
    commitment = self.commitments.get(commitment_id)
    if not commitment:
        raise ValueError(f"Commitment {commitment_id} not found")

    # FIX: Update all provided fields
    for key, value in kwargs.items():
        if key in commitment:
            commitment[key] = value

    return commitment
```

---

## Step 6: Verify the Fix

### Command

```bash
pytest tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment -v
```

### Sample Output

```
================================== test session starts ===================================
platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: /Users/jeremy/Projects/Thanos
configfile: pytest.ini
plugins: asyncio-0.21.1, cov-4.1.0, mock-3.12.0
collected 1 item

tests/unit/test_commitment_tracker.py::TestCommitmentTracker::test_update_commitment PASSED [100%]

=========================== 1 passed in 0.72s ==============================
```

✅ **Test now passes!**

---

## Step 7: Run Full Test Suite

Make sure your fix didn't break other tests.

### Command

```bash
pytest tests/unit/test_commitment_tracker.py
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

=========================== 21 passed in 2.94s ==============================
```

✅ **All tests pass!**

---

## Common Failure Patterns

### Pattern 1: Import Error

```
E   ImportError: cannot import name 'process_data' from 'Tools.data_processor'
```

**Cause**: Function was renamed or moved
**Solution**: Update import statement or fix function name

### Pattern 2: Attribute Error

```
E   AttributeError: 'NoneType' object has no attribute 'get'
```

**Cause**: Object is None when it shouldn't be
**Solution**: Check object initialization or add None checks

### Pattern 3: Assertion Error with Mocks

```
E   AssertionError: Expected 'mock_client.send' to be called once. Called 0 times.
```

**Cause**: Mock expectation not met
**Solution**: Code path didn't call the expected method - check logic

### Pattern 4: Async Test Error

```
E   RuntimeError: coroutine 'test_async_function' was never awaited
```

**Cause**: Missing `@pytest.mark.asyncio` decorator
**Solution**: Add decorator to async test functions

### Pattern 5: Fixture Not Found

```
E   fixture 'mock_anthropic_client' not found
```

**Cause**: Test file doesn't have access to fixture
**Solution**: Import from conftest.py or check fixture scope

---

## Debugging Commands Quick Reference

| Command | Purpose |
|---------|---------|
| `pytest -v` | Verbose output with test names |
| `pytest -s` | Show print statements |
| `pytest -x` | Stop on first failure |
| `pytest --lf` | Run only last failed tests |
| `pytest --pdb` | Drop into debugger on failure |
| `pytest -k pattern` | Run tests matching pattern |
| `pytest --tb=short` | Shorter traceback |
| `pytest --tb=line` | One-line traceback |
| `pytest -vv` | Extra verbose (show full diff) |

---

## Best Practices for Debugging

### 1. Start Specific, Then Go Broader

```bash
# Start with the failing test
pytest tests/unit/test_mymodule.py::test_specific_function

# If that passes, run the whole file
pytest tests/unit/test_mymodule.py

# If that passes, run the whole suite
pytest
```

### 2. Use --lf to Iterate Quickly

```bash
# First run (some tests fail)
pytest

# Fix attempt 1
pytest --lf  # Only runs failed tests

# Fix attempt 2
pytest --lf  # Only runs failed tests

# Final verification
pytest  # Run everything
```

### 3. Add Temporary Debug Output

```python
def test_something():
    result = process_data()
    print(f"\n🐛 DEBUG: result = {result}")  # Temporary
    assert result == expected
```

Run with: `pytest -s` to see the output

**Remember to remove debug prints before committing!**

### 4. Use pdb for Complex Issues

```python
def test_something():
    result = process_data()

    import pdb; pdb.set_trace()  # Temporary breakpoint

    assert result == expected
```

Or use `--pdb` flag to auto-break on failures.

---

## Tips

1. **Read the error message carefully** - The first line often tells you exactly what's wrong
2. **Check the line number** - Go straight to the failing line
3. **Use -v for context** - Verbose mode shows which test failed
4. **Use -s to see prints** - Sometimes you need to see intermediate values
5. **Use --pdb for complex issues** - Interactive debugging is powerful
6. **Run tests in isolation** - Use `-k` or full path to run one test at a time
7. **Check recent changes** - The bug is likely in code you just modified

---

## Related Documentation

- [TESTING_GUIDE.md - Troubleshooting](../TESTING_GUIDE.md#troubleshooting)
- [01_running_all_tests.md](01_running_all_tests.md)
- [02_running_by_category.md](02_running_by_category.md)
