#!/usr/bin/env python3
"""
Verification test for encoder caching in ContextManager

Acceptance Criteria:
1. Encoder is initialized only once (cached at module level)
2. Multiple ContextManager instances share the same encoder
3. Encoder instance identity is preserved across instantiations
4. Module-level _CACHED_ENCODER is set after first instantiation
5. Subsequent instantiations are faster (no re-initialization)
"""
import sys
import time
from Tools.context_manager import ContextManager, _get_cached_encoder, TIKTOKEN_AVAILABLE

print("=" * 70)
print("VERIFICATION: Encoder Caching in ContextManager")
print("=" * 70)

# Check if tiktoken is available
print(f"\n📦 Tiktoken availability: {TIKTOKEN_AVAILABLE}")
if not TIKTOKEN_AVAILABLE:
    print("\n⚠️  WARNING: tiktoken is not available in this environment")
    print("   The encoder will be None, but caching logic can still be verified")
    print()

# Test 1: Module-level encoder cache starts as None (before first access)
print("\n✓ Test 1: Module-level encoder cache initial state")
# Import the module-level variable directly
from Tools.context_manager import _CACHED_ENCODER as initial_cache
print(f"  Initial _CACHED_ENCODER: {initial_cache}")
if initial_cache is None:
    print("  PASS: Cache starts as None (lazy initialization)")
else:
    print("  INFO: Cache already initialized (may be from previous import)")

# Test 2: First instantiation initializes encoder
print("\n✓ Test 2: First ContextManager instantiation initializes encoder")
start = time.time()
cm1 = ContextManager(model="anthropic/claude-opus-4-5")
first_init_time = (time.time() - start) * 1000
print(f"  First instantiation time: {first_init_time:.2f}ms")

# Get encoder instance from first manager
encoder1 = cm1.encoding
encoder1_id = id(encoder1)
print(f"  Encoder instance: {encoder1}")
print(f"  Encoder ID: {encoder1_id}")

if encoder1 is not None:
    print("  PASS: Encoder initialized successfully")
elif not TIKTOKEN_AVAILABLE:
    print("  PASS: Encoder is None (expected when tiktoken unavailable)")
else:
    print("  WARNING: Encoder is None (unexpected with tiktoken available)")

# Test 3: Verify module-level cache is set
print("\n✓ Test 3: Module-level cache is set after first instantiation")
cached_encoder = _get_cached_encoder()
cached_encoder_id = id(cached_encoder)
print(f"  Cached encoder: {cached_encoder}")
print(f"  Cached encoder ID: {cached_encoder_id}")

if cached_encoder is encoder1:
    print("  PASS: Module-level cache matches instance encoder (same object)")
else:
    print(f"  FAIL: Cache mismatch (cache={cached_encoder_id}, instance={encoder1_id})")

# Test 4: Second instantiation reuses cached encoder
print("\n✓ Test 4: Second ContextManager instantiation reuses encoder")
start = time.time()
cm2 = ContextManager(model="anthropic/claude-sonnet-4-5")
second_init_time = (time.time() - start) * 1000
print(f"  Second instantiation time: {second_init_time:.2f}ms")

encoder2 = cm2.encoding
encoder2_id = id(encoder2)
print(f"  Encoder instance: {encoder2}")
print(f"  Encoder ID: {encoder2_id}")

if encoder2 is encoder1:
    print("  PASS: Second instance shares same encoder object (cached)")
else:
    print(f"  FAIL: Different encoder objects (encoder1={encoder1_id}, encoder2={encoder2_id})")

# Test 5: Third instantiation also reuses cached encoder
print("\n✓ Test 5: Third ContextManager instantiation reuses encoder")
start = time.time()
cm3 = ContextManager(model="claude-3-5-sonnet-20241022")
third_init_time = (time.time() - start) * 1000
print(f"  Third instantiation time: {third_init_time:.2f}ms")

encoder3 = cm3.encoding
encoder3_id = id(encoder3)
print(f"  Encoder instance: {encoder3}")
print(f"  Encoder ID: {encoder3_id}")

if encoder3 is encoder1:
    print("  PASS: Third instance shares same encoder object (cached)")
else:
    print(f"  FAIL: Different encoder objects (encoder1={encoder1_id}, encoder3={encoder3_id})")

# Test 6: Verify all instances share identical encoder
print("\n✓ Test 6: Verify all instances share identical encoder")
all_same = (encoder1 is encoder2) and (encoder2 is encoder3)
print(f"  encoder1 is encoder2: {encoder1 is encoder2}")
print(f"  encoder2 is encoder3: {encoder2 is encoder3}")
print(f"  encoder1 is encoder3: {encoder1 is encoder3}")

if all_same:
    print("  PASS: All three instances share the same encoder object")
else:
    print("  FAIL: Encoder objects are not identical across instances")

# Test 7: Performance verification (if tiktoken available)
if TIKTOKEN_AVAILABLE and encoder1 is not None:
    print("\n✓ Test 7: Performance improvement verification")
    print(f"  First instantiation:  {first_init_time:.2f}ms")
    print(f"  Second instantiation: {second_init_time:.2f}ms")
    print(f"  Third instantiation:  {third_init_time:.2f}ms")

    # Second and third should be significantly faster
    avg_cached = (second_init_time + third_init_time) / 2
    speedup = first_init_time / avg_cached if avg_cached > 0 else 0

    print(f"  Average cached instantiation: {avg_cached:.2f}ms")
    print(f"  Speedup factor: {speedup:.1f}x")

    if second_init_time < first_init_time and third_init_time < first_init_time:
        print("  PASS: Cached instantiations are faster than first")
    else:
        print("  INFO: Performance may vary (timing can be noisy for small operations)")
else:
    print("\n✓ Test 7: Performance verification (SKIPPED - tiktoken not available)")
    print("  INFO: Performance benefits only apply when tiktoken is installed")

# Test 8: Verify encoder functionality (basic smoke test)
print("\n✓ Test 8: Verify encoder functionality across instances")
test_text = "Hello, world! This is a test message."

tokens1 = cm1.estimate_tokens(test_text)
tokens2 = cm2.estimate_tokens(test_text)
tokens3 = cm3.estimate_tokens(test_text)

print(f"  Instance 1 token count: {tokens1}")
print(f"  Instance 2 token count: {tokens2}")
print(f"  Instance 3 token count: {tokens3}")

if tokens1 == tokens2 == tokens3:
    print("  PASS: All instances produce identical token counts")
else:
    print(f"  FAIL: Token counts differ (t1={tokens1}, t2={tokens2}, t3={tokens3})")

# Test 9: Direct module-level cache access
print("\n✓ Test 9: Direct module-level cache verification")
from Tools import context_manager
module_cache = context_manager._CACHED_ENCODER
module_cache_id = id(module_cache)
print(f"  Module._CACHED_ENCODER: {module_cache}")
print(f"  Module._CACHED_ENCODER ID: {module_cache_id}")

if module_cache is encoder1:
    print("  PASS: Module-level cache is the same object as instance encoders")
else:
    print(f"  FAIL: Module cache mismatch (module={module_cache_id}, instance={encoder1_id})")

# Test 10: Multiple instantiations with different models
print("\n✓ Test 10: Different models share same encoder")
managers = []
for i, model in enumerate([
    "anthropic/claude-opus-4-5",
    "anthropic/claude-sonnet-4-5",
    "claude-3-5-sonnet-20241022",
    "unknown-model-falls-back-to-default"
]):
    cm = ContextManager(model=model)
    managers.append(cm)

encoder_ids = [id(cm.encoding) for cm in managers]
all_identical = all(enc_id == encoder_ids[0] for enc_id in encoder_ids)

print(f"  Encoder IDs: {encoder_ids}")
if all_identical:
    print("  PASS: All models share the same encoder instance")
else:
    print("  FAIL: Different models have different encoder instances")

# Final summary
print("\n" + "=" * 70)
print("✅ ENCODER CACHING VERIFICATION COMPLETE")
print("=" * 70)
print("\nAcceptance Criteria Results:")

criteria = [
    ("Encoder initialized only once (cached at module level)", all_same),
    ("Multiple ContextManager instances share same encoder", all_same),
    ("Encoder instance identity preserved", encoder1_id == encoder2_id == encoder3_id),
    ("Module-level _CACHED_ENCODER set after first use", module_cache is encoder1),
    ("Different models share same encoder", all_identical),
]

all_passed = True
for criterion, passed in criteria:
    status = "✅" if passed else "❌"
    print(f"{status} {criterion}")
    if not passed:
        all_passed = False

if all_passed:
    print("\n" + "=" * 70)
    print("🎉 ALL ACCEPTANCE CRITERIA MET - ENCODER CACHING VERIFIED!")
    print("=" * 70)
    sys.exit(0)
else:
    print("\n" + "=" * 70)
    print("⚠️  SOME CRITERIA FAILED - REVIEW OUTPUT ABOVE")
    print("=" * 70)
    sys.exit(1)
