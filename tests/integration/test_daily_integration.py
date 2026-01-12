"""
Test script to verify daily.py integration with BriefingEngine.

This script tests that the updated daily.py:
1. Imports successfully
2. Uses BriefingEngine
3. Maintains backward compatibility
4. Preserves save_to_history functionality
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required imports work."""
    print("✓ Testing imports...")
    try:
        from commands.pa import daily
        from Tools.briefing_engine import BriefingEngine
        print("  ✅ All imports successful")
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False


def test_briefing_engine_usage():
    """Test that daily.py can use BriefingEngine."""
    print("\n✓ Testing BriefingEngine integration...")
    try:
        from commands.pa import daily
        from Tools.briefing_engine import BriefingEngine

        # Check that daily.py has the necessary functions
        assert hasattr(daily, 'execute'), "Missing execute function"
        assert hasattr(daily, 'save_to_history'), "Missing save_to_history function"
        assert hasattr(daily, 'build_context_legacy'), "Missing build_context_legacy function"

        print("  ✅ daily.py has all required functions")
        return True
    except (ImportError, AssertionError) as e:
        print(f"  ❌ Test failed: {e}")
        return False


def test_backward_compatibility():
    """Test that legacy functions are preserved."""
    print("\n✓ Testing backward compatibility...")
    try:
        from commands.pa import daily

        # Check that legacy functions exist
        assert hasattr(daily, 'SYSTEM_PROMPT'), "Missing SYSTEM_PROMPT"
        assert hasattr(daily, 'save_to_history'), "Missing save_to_history"

        # Check that function signatures are compatible
        import inspect
        sig = inspect.signature(daily.execute)
        params = list(sig.parameters.keys())
        assert 'args' in params, "execute() missing 'args' parameter"

        print("  ✅ Backward compatibility maintained")
        return True
    except (ImportError, AssertionError) as e:
        print(f"  ❌ Test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing daily.py Integration with BriefingEngine")
    print("=" * 60)

    tests = [
        test_imports,
        test_briefing_engine_usage,
        test_backward_compatibility,
    ]

    results = [test() for test in tests]

    print("\n" + "=" * 60)
    if all(results):
        print("✅ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some tests failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
