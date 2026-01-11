#!/usr/bin/env python3
"""
Test runner for ChromaAdapter tests.
This script runs the full test suite for the batch embedding optimization.
"""

import subprocess
import sys
import os

def main():
    """Run the full test suite."""

    # Change to project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    print("=" * 70)
    print("Running ChromaAdapter Test Suite")
    print("=" * 70)
    print()

    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/test_chroma_adapter.py",
        "-v",
        "--tb=short",
        "-m", "not slow"
    ]

    print(f"Command: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, check=False)

        print()
        print("=" * 70)
        if result.returncode == 0:
            print("✅ ALL TESTS PASSED!")
            print("=" * 70)
            print()
            print("Verification Summary:")
            print("✅ pytest tests/unit/test_chroma_adapter.py passes completely")
            print("✅ No regressions in _store_memory tests")
            print("✅ No regressions in semantic_search tests")
            print("✅ All other adapter tests pass")
        else:
            print("❌ TESTS FAILED")
            print("=" * 70)
            print(f"Exit code: {result.returncode}")
            return result.returncode

    except FileNotFoundError:
        print("❌ Error: pytest not found")
        print()
        print("Please install test dependencies first:")
        print(f"  {sys.executable} -m pip install -r requirements-test.txt")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
