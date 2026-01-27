#!/usr/bin/env python3
"""Run StateStore tests to verify no regressions."""
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Try to run pytest programmatically
try:
    import pytest
    
    print("=" * 70)
    print("Running StateStore Tests")
    print("=" * 70)
    print()
    
    # Run pytest programmatically
    exit_code = pytest.main([
        "tests/unit/test_state_store.py",
        "-v",
        "--tb=short"
    ])
    
    print()
    print("=" * 70)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED - No regressions detected!")
        print("=" * 70)
    else:
        print(f"❌ TESTS FAILED - Exit code: {exit_code}")
        print("=" * 70)
    
    sys.exit(exit_code)
    
except ImportError:
    print("❌ Error: pytest not found")
    print()
    print("Please install test dependencies first:")
    print(f"  {sys.executable} -m pip install -r requirements-test.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error running tests: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
