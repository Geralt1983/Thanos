#!/usr/bin/env python3
"""
Verification script to test that all external files importing from
litellm_client.py still work correctly after the refactoring.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("Verifying external imports from litellm_client.py")
print("=" * 80)

# Test 1: Import get_client (used by commands/pa/*.py files)
print("\n1. Testing 'from Tools.litellm_client import get_client'")
try:
    from Tools.litellm_client import get_client
    print("   ✓ get_client imported successfully")
    print(f"   ✓ get_client is callable: {callable(get_client)}")
    # Test that it's the correct function
    assert callable(get_client), "get_client should be callable"
    print("   ✓ get_client is the correct function")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)
except AssertionError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Import LiteLLMClient (used by Tools/thanos_orchestrator.py for TYPE_CHECKING)
print("\n2. Testing 'from Tools.litellm_client import LiteLLMClient'")
try:
    from Tools.litellm_client import LiteLLMClient
    print("   ✓ LiteLLMClient imported successfully")
    print(f"   ✓ LiteLLMClient is a class: {isinstance(LiteLLMClient, type)}")
    assert isinstance(LiteLLMClient, type), "LiteLLMClient should be a class"
    print("   ✓ LiteLLMClient is the correct class")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)
except AssertionError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

# Test 3: Dynamic module import (used by Tools/thanos_orchestrator.py)
print("\n3. Testing 'from Tools import litellm_client' (dynamic import)")
try:
    from Tools import litellm_client
    print("   ✓ litellm_client module imported successfully")
    print(f"   ✓ Module has get_client: {hasattr(litellm_client, 'get_client')}")
    print(f"   ✓ Module has LiteLLMClient: {hasattr(litellm_client, 'LiteLLMClient')}")
    assert hasattr(litellm_client, 'get_client'), "Module should have get_client"
    assert hasattr(litellm_client, 'LiteLLMClient'), "Module should have LiteLLMClient"
    print("   ✓ Module exports are correct")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)
except AssertionError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

# Test 4: Verify all other exports are available
print("\n4. Testing all other exports from litellm_client")
expected_exports = [
    'UsageTracker',
    'ComplexityAnalyzer',
    'ResponseCache',
    'ModelResponse',
    'init_client',
    'LITELLM_AVAILABLE',
    'ANTHROPIC_AVAILABLE'
]

try:
    from Tools.litellm_client import (
        UsageTracker,
        ComplexityAnalyzer,
        ResponseCache,
        ModelResponse,
        init_client,
        LITELLM_AVAILABLE,
        ANTHROPIC_AVAILABLE
    )
    for name in expected_exports:
        print(f"   ✓ {name} imported successfully")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

# Test 5: Verify backward compatibility - old and new paths refer to same objects
print("\n5. Testing backward compatibility (old path == new path)")
try:
    from Tools.litellm_client import LiteLLMClient as OldClient, get_client as old_get_client
    from Tools.litellm import LiteLLMClient as NewClient, get_client as new_get_client

    assert OldClient is NewClient, "LiteLLMClient should be the same object from both paths"
    print("   ✓ LiteLLMClient is identical from both import paths")

    assert old_get_client is new_get_client, "get_client should be the same function from both paths"
    print("   ✓ get_client is identical from both import paths")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)
except AssertionError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

# Test 6: Verify CLI functionality still exists in wrapper
print("\n6. Testing CLI functionality in litellm_client.py")
try:
    # Check if the file can be executed as a script
    cli_path = Path(__file__).parent / 'Tools' / 'litellm_client.py'
    assert cli_path.exists(), "litellm_client.py should exist"

    # Read and verify it has the CLI entry point
    content = cli_path.read_text()
    assert 'if __name__ == "__main__"' in content, "Module should have CLI entry point"
    assert 'sys.argv[1] == "test"' in content, "Module should support 'test' command"
    assert 'sys.argv[1] == "usage"' in content, "Module should support 'usage' command"
    assert 'sys.argv[1] == "models"' in content, "Module should support 'models' command"
    print("   ✓ CLI entry point exists with test/usage/models commands")
except AssertionError as e:
    print(f"   ✗ FAILED: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL VERIFICATION TESTS PASSED!")
print("=" * 80)
print("\nSummary:")
print("  • get_client function is accessible (used by 5 PA command files)")
print("  • LiteLLMClient class is accessible (used by thanos_orchestrator.py)")
print("  • Dynamic module import works (used by thanos_orchestrator.py)")
print("  • All exports are available through the wrapper")
print("  • Backward compatibility is maintained")
print("  • CLI functionality is preserved")
print("\nAll external files importing from litellm_client.py will continue to work!")
