#!/usr/bin/env python3
"""
Test script to verify backward compatibility of imports after refactoring.

This script tests that the old import path 'from Tools.litellm_client import ...'
still works correctly after extracting classes into the Tools.litellm package.
"""

import sys


def test_import_all_classes():
    """Test importing all classes from the old path."""
    print("Testing backward compatibility imports from Tools.litellm_client...")
    print("-" * 70)

    # Test importing all main classes
    try:
        from Tools.litellm_client import (
            LiteLLMClient,
            UsageTracker,
            ComplexityAnalyzer,
            ResponseCache,
            ModelResponse,
            get_client,
            init_client,
            LITELLM_AVAILABLE,
            ANTHROPIC_AVAILABLE,
        )
        print("✓ Successfully imported all classes from Tools.litellm_client")
    except ImportError as e:
        print(f"✗ FAILED to import from Tools.litellm_client: {e}")
        return False

    # Test that classes are accessible
    tests_passed = 0
    tests_total = 0

    # Test LiteLLMClient
    tests_total += 1
    if LiteLLMClient.__name__ == "LiteLLMClient":
        print("✓ LiteLLMClient is accessible")
        tests_passed += 1
    else:
        print("✗ LiteLLMClient is not correctly imported")

    # Test UsageTracker
    tests_total += 1
    if UsageTracker.__name__ == "UsageTracker":
        print("✓ UsageTracker is accessible")
        tests_passed += 1
    else:
        print("✗ UsageTracker is not correctly imported")

    # Test ComplexityAnalyzer
    tests_total += 1
    if ComplexityAnalyzer.__name__ == "ComplexityAnalyzer":
        print("✓ ComplexityAnalyzer is accessible")
        tests_passed += 1
    else:
        print("✗ ComplexityAnalyzer is not correctly imported")

    # Test ResponseCache
    tests_total += 1
    if ResponseCache.__name__ == "ResponseCache":
        print("✓ ResponseCache is accessible")
        tests_passed += 1
    else:
        print("✗ ResponseCache is not correctly imported")

    # Test ModelResponse
    tests_total += 1
    if ModelResponse.__name__ == "ModelResponse":
        print("✓ ModelResponse is accessible")
        tests_passed += 1
    else:
        print("✗ ModelResponse is not correctly imported")

    # Test get_client function
    tests_total += 1
    if callable(get_client):
        print("✓ get_client() function is accessible")
        tests_passed += 1
    else:
        print("✗ get_client() is not correctly imported")

    # Test init_client function
    tests_total += 1
    if callable(init_client):
        print("✓ init_client() function is accessible")
        tests_passed += 1
    else:
        print("✗ init_client() is not correctly imported")

    # Test constants
    tests_total += 1
    if isinstance(LITELLM_AVAILABLE, bool):
        print(f"✓ LITELLM_AVAILABLE is accessible (value: {LITELLM_AVAILABLE})")
        tests_passed += 1
    else:
        print("✗ LITELLM_AVAILABLE is not correctly imported")

    tests_total += 1
    if isinstance(ANTHROPIC_AVAILABLE, bool):
        print(f"✓ ANTHROPIC_AVAILABLE is accessible (value: {ANTHROPIC_AVAILABLE})")
        tests_passed += 1
    else:
        print("✗ ANTHROPIC_AVAILABLE is not correctly imported")

    print("-" * 70)
    print(f"Results: {tests_passed}/{tests_total} tests passed")

    return tests_passed == tests_total


def test_new_import_path():
    """Test that the new import path also works."""
    print("\nTesting new import path from Tools.litellm...")
    print("-" * 70)

    try:
        from Tools.litellm import (
            LiteLLMClient,
            UsageTracker,
            ComplexityAnalyzer,
            ResponseCache,
            ModelResponse,
            get_client,
            init_client,
        )
        print("✓ Successfully imported all classes from Tools.litellm")
        return True
    except ImportError as e:
        print(f"✗ FAILED to import from Tools.litellm: {e}")
        return False


def test_class_equivalence():
    """Test that imports from both paths refer to the same classes."""
    print("\nTesting that both import paths refer to the same classes...")
    print("-" * 70)

    from Tools.litellm_client import (
        LiteLLMClient as OldLiteLLMClient,
        UsageTracker as OldUsageTracker,
        ComplexityAnalyzer as OldComplexityAnalyzer,
        ResponseCache as OldResponseCache,
        ModelResponse as OldModelResponse,
    )

    from Tools.litellm import (
        LiteLLMClient as NewLiteLLMClient,
        UsageTracker as NewUsageTracker,
        ComplexityAnalyzer as NewComplexityAnalyzer,
        ResponseCache as NewResponseCache,
        ModelResponse as NewModelResponse,
    )

    tests_passed = 0
    tests_total = 5

    if OldLiteLLMClient is NewLiteLLMClient:
        print("✓ LiteLLMClient is the same class from both paths")
        tests_passed += 1
    else:
        print("✗ LiteLLMClient differs between old and new paths")

    if OldUsageTracker is NewUsageTracker:
        print("✓ UsageTracker is the same class from both paths")
        tests_passed += 1
    else:
        print("✗ UsageTracker differs between old and new paths")

    if OldComplexityAnalyzer is NewComplexityAnalyzer:
        print("✓ ComplexityAnalyzer is the same class from both paths")
        tests_passed += 1
    else:
        print("✗ ComplexityAnalyzer differs between old and new paths")

    if OldResponseCache is NewResponseCache:
        print("✓ ResponseCache is the same class from both paths")
        tests_passed += 1
    else:
        print("✗ ResponseCache differs between old and new paths")

    if OldModelResponse is NewModelResponse:
        print("✓ ModelResponse is the same class from both paths")
        tests_passed += 1
    else:
        print("✗ ModelResponse differs between old and new paths")

    print("-" * 70)
    print(f"Results: {tests_passed}/{tests_total} tests passed")

    return tests_passed == tests_total


def main():
    """Run all backward compatibility tests."""
    print("=" * 70)
    print("BACKWARD COMPATIBILITY TEST SUITE")
    print("=" * 70)

    all_passed = True

    # Test 1: Old import path
    if not test_import_all_classes():
        all_passed = False

    # Test 2: New import path
    if not test_new_import_path():
        all_passed = False

    # Test 3: Class equivalence
    if not test_class_equivalence():
        all_passed = False

    # Final summary
    print("\n" + "=" * 70)
    if all_passed:
        print("SUCCESS: All backward compatibility tests passed! ✓")
        print("=" * 70)
        return 0
    else:
        print("FAILURE: Some backward compatibility tests failed! ✗")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
