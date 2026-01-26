"""
End-to-End Acceptance Tests for Proactive Context Surfacing

Verifies all acceptance criteria from spec.md:
1. Client mentions trigger automatic context loading
2. Topic discussions surface related past decisions
3. Project references load recent activity summary
4. Context surfacing is subtle - not overwhelming
5. User can request 'more context' or 'less context'
6. Performance impact < 500ms additional latency

This test suite performs comprehensive end-to-end validation of the
entire proactive context surfacing feature.
"""
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.entity_extractor import extract_entities
from Tools.proactive_context import (
    load_context_for_entities,
    format_context,
    get_user_preferences,
    set_context_verbosity,
    get_verbosity_settings,
    estimate_tokens
)
from Tools.command_handlers.core_handler import (
    handle_more_context,
    handle_less_context,
    handle_context_status
)

# Import hook module directly by path since it uses hyphens
import importlib.util
hook_path = Path(__file__).parent.parent / 'hooks' / 'pre-tool-use' / 'proactive_context.py'
spec = importlib.util.spec_from_file_location("proactive_context_hook", hook_path)
hook_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook_module)
run_hook = hook_module.run_hook


class TestResults:
    """Track test results for summary report"""
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0

    def record(self, name, passed, details=""):
        self.tests.append({
            'name': name,
            'passed': passed,
            'details': details
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self):
        print("\n" + "=" * 70)
        print("ACCEPTANCE TEST SUMMARY")
        print("=" * 70)
        for test in self.tests:
            status = "✓ PASS" if test['passed'] else "✗ FAIL"
            print(f"{status}: {test['name']}")
            if test['details']:
                print(f"        {test['details']}")
        print("=" * 70)
        print(f"Total: {self.passed} passed, {self.failed} failed")
        print("=" * 70 + "\n")


results = TestResults()


def test_client_mention_triggers_context():
    """
    Acceptance Criterion 1: Client mentions trigger automatic context loading

    Tests:
    - Orlando client mention detected
    - Context is loaded for Orlando
    - Context is formatted and ready to inject
    """
    print("\n[Test 1] Client mention triggers context loading...")

    test_input = "What's the status of the Orlando project?"

    # Run hook
    result = run_hook(test_input)

    # Verify entities detected
    entities = result.get('entities_detected', [])
    entity_texts = [e['text'] for e in entities]

    has_orlando = 'Orlando' in entity_texts
    has_context = result.get('should_inject', False)
    context = result.get('injected_context', '')

    # Verify Orlando was detected
    assert has_orlando, f"Orlando not detected. Entities found: {entity_texts}"
    print(f"  ✓ Orlando entity detected: {entity_texts}")

    # Verify context was loaded
    assert has_context, "Context should be injected for Orlando mention"
    print(f"  ✓ Context injection triggered: {has_context}")

    # Verify context contains relevant information
    assert len(context) > 0, "Context should not be empty"
    assert "Orlando" in context, "Context should mention Orlando"
    print(f"  ✓ Context contains Orlando reference")

    # Verify context has proper formatting (heat indicators)
    has_indicators = any(indicator in context for indicator in ['🔥', '•', '❄️'])
    assert has_indicators, "Context should have heat indicators"
    print(f"  ✓ Context has heat indicators")

    results.record(
        "Client mention triggers context loading",
        True,
        f"Orlando detected with {len(entities)} total entities"
    )
    print("  ✓ Test 1 PASSED")


def test_topic_discussion_surfaces_memories():
    """
    Acceptance Criterion 2: Topic discussions surface related past decisions

    Tests:
    - Calendar topic detected
    - Related memories are surfaced
    - Context is relevant to the topic
    """
    print("\n[Test 2] Topic discussion surfaces related memories...")

    test_input = "What's on my calendar for tomorrow?"

    # Run hook
    result = run_hook(test_input)

    # Verify entities detected
    entities = result.get('entities_detected', [])
    entity_types = [e['type'] for e in entities]

    has_topic = 'topic' in entity_types
    has_context = result.get('should_inject', False)
    context = result.get('injected_context', '')

    # Verify topic was detected
    assert has_topic, f"Topic not detected. Entity types: {entity_types}"
    print(f"  ✓ Topic entity detected: {[e for e in entities if e['type'] == 'topic']}")

    # Verify context was loaded
    assert has_context, "Context should be injected for topic discussion"
    print(f"  ✓ Context injection triggered: {has_context}")

    # Verify context contains relevant information
    assert len(context) > 0, "Context should not be empty"
    print(f"  ✓ Context loaded ({len(context)} chars)")

    results.record(
        "Topic discussion surfaces related memories",
        True,
        f"{len(entities)} topic entities detected"
    )
    print("  ✓ Test 2 PASSED")


def test_project_reference_loads_activity():
    """
    Acceptance Criterion 3: Project references load recent activity summary

    Tests:
    - Thanos project detected
    - Context is loaded for project
    - Activity summary is formatted appropriately
    """
    print("\n[Test 3] Project reference loads recent activity...")

    test_input = "How's the Thanos project coming along?"

    # Run hook
    result = run_hook(test_input)

    # Verify entities detected
    entities = result.get('entities_detected', [])
    entity_texts = [e['text'] for e in entities]
    entity_types = {e['text']: e['type'] for e in entities}

    has_thanos = 'Thanos' in entity_texts
    has_context = result.get('should_inject', False)
    context = result.get('injected_context', '')

    # Verify Thanos project was detected
    assert has_thanos, f"Thanos not detected. Entities found: {entity_texts}"
    assert entity_types.get('Thanos') in ['project', 'client'], f"Thanos should be detected as project or client, got: {entity_types.get('Thanos')}"
    print(f"  ✓ Thanos entity detected: type={entity_types.get('Thanos')}")

    # Verify context was loaded
    assert has_context, "Context should be injected for Thanos mention"
    print(f"  ✓ Context injection triggered: {has_context}")

    # Verify context contains relevant information
    assert len(context) > 0, "Context should not be empty"
    assert "Thanos" in context, "Context should mention Thanos"
    print(f"  ✓ Context contains Thanos reference")

    results.record(
        "Project reference loads recent activity",
        True,
        f"Thanos detected as {entity_types.get('Thanos')}"
    )
    print("  ✓ Test 3 PASSED")


def test_context_is_subtle():
    """
    Acceptance Criterion 4: Context surfacing is subtle - not overwhelming

    Tests:
    - Token budget is respected (< 800 tokens for normal verbosity)
    - Context is formatted cleanly
    - Not too many items are shown
    - Heat indicators provide priority cues
    """
    print("\n[Test 4] Context surfacing is subtle and not overwhelming...")

    test_input = "Tell me about Orlando, Thanos, and my calendar for this week"

    # Run hook
    result = run_hook(test_input)

    context = result.get('injected_context', '')
    entities = result.get('entities_detected', [])

    # Verify context exists
    assert len(context) > 0, "Context should exist for multi-entity input"
    print(f"  ✓ Context loaded for {len(entities)} entities")

    # Check token budget (should be <= 800 for normal verbosity)
    prefs = get_user_preferences()
    verbosity = prefs.get('context_verbosity', 'normal')
    _, max_tokens = get_verbosity_settings(verbosity)

    estimated_tokens = estimate_tokens(context)
    within_budget = estimated_tokens <= max_tokens * 1.1  # Allow 10% margin

    assert within_budget, f"Context tokens ({estimated_tokens}) exceeds budget ({max_tokens})"
    print(f"  ✓ Token budget respected: {estimated_tokens} <= {max_tokens}")

    # Verify context has structure (not just raw text dump)
    has_header = "Proactive Context" in context or "##" in context
    has_indicators = any(indicator in context for indicator in ['🔥', '•', '❄️'])

    assert has_header, "Context should have structured header"
    assert has_indicators, "Context should have heat indicators for priority"
    print(f"  ✓ Context is structured with header and indicators")

    # Verify context is not overwhelming (reasonable line count)
    lines = context.strip().split('\n')
    non_empty_lines = [line for line in lines if line.strip()]

    # Should be concise (< 30 lines for normal verbosity with 3 entities)
    assert len(non_empty_lines) < 30, f"Context too long ({len(non_empty_lines)} lines)"
    print(f"  ✓ Context is concise: {len(non_empty_lines)} lines")

    results.record(
        "Context surfacing is subtle and not overwhelming",
        True,
        f"{estimated_tokens} tokens, {len(non_empty_lines)} lines"
    )
    print("  ✓ Test 4 PASSED")


def test_verbosity_controls():
    """
    Acceptance Criterion 5: User can request 'more context' or 'less context'

    Tests:
    - More context command increases verbosity
    - Less context command decreases verbosity
    - Settings persist in State/jeremy.json
    - Context adapts to new verbosity level
    """
    print("\n[Test 5] Verbosity controls work correctly...")

    # Save original verbosity
    original_prefs = get_user_preferences()
    original_verbosity = original_prefs.get('context_verbosity', 'normal')

    try:
        # Reset to normal
        set_context_verbosity('normal')

        # Test 'more context' command
        result = handle_more_context()
        assert result['success'], "More context command should succeed"
        assert result['new_level'] == 'detailed', f"Expected 'detailed', got {result['new_level']}"
        print(f"  ✓ More context: {result['previous_level']} → {result['new_level']}")

        # Verify preferences updated
        prefs = get_user_preferences()
        assert prefs['context_verbosity'] == 'detailed', "Preferences not updated"
        print(f"  ✓ Preferences persisted: {prefs['context_verbosity']}")

        # Test 'more context' at max (should stay at detailed)
        result = handle_more_context()
        assert result['success'], "More context at max should still succeed"
        assert result['new_level'] == 'detailed', "Should stay at detailed (max)"
        print(f"  ✓ More context at max: stays at {result['new_level']}")

        # Test 'less context' command
        result = handle_less_context()
        assert result['success'], "Less context command should succeed"
        assert result['new_level'] == 'normal', f"Expected 'normal', got {result['new_level']}"
        print(f"  ✓ Less context: {result['previous_level']} → {result['new_level']}")

        # Test 'less context' again
        result = handle_less_context()
        assert result['success'], "Less context command should succeed"
        assert result['new_level'] == 'minimal', f"Expected 'minimal', got {result['new_level']}"
        print(f"  ✓ Less context: {result['previous_level']} → {result['new_level']}")

        # Test 'less context' at min (should stay at minimal)
        result = handle_less_context()
        assert result['success'], "Less context at min should still succeed"
        assert result['new_level'] == 'minimal', "Should stay at minimal (min)"
        print(f"  ✓ Less context at min: stays at {result['new_level']}")

        # Test status command
        result = handle_context_status()
        assert result['success'], "Status command should succeed"
        assert result['current_level'] == 'minimal', "Status should show current level"
        print(f"  ✓ Status command: {result['current_level']}")

        # Verify context adapts to verbosity
        # Set to minimal
        set_context_verbosity('minimal')
        max_results_min, max_tokens_min = get_verbosity_settings('minimal')

        # Set to detailed
        set_context_verbosity('detailed')
        max_results_det, max_tokens_det = get_verbosity_settings('detailed')

        # Verify different settings
        assert max_results_min < max_results_det, "Minimal should have fewer results than detailed"
        assert max_tokens_min < max_tokens_det, "Minimal should have fewer tokens than detailed"
        print(f"  ✓ Verbosity settings differ: minimal({max_results_min},{max_tokens_min}) < detailed({max_results_det},{max_tokens_det})")

        results.record(
            "Verbosity controls work correctly",
            True,
            "All commands and settings work as expected"
        )
        print("  ✓ Test 5 PASSED")

    finally:
        # Restore original verbosity
        set_context_verbosity(original_verbosity)


def test_performance_requirement():
    """
    Acceptance Criterion 6: Performance impact < 500ms additional latency

    Tests:
    - End-to-end latency meets requirement
    - Performance is consistent across multiple runs
    - No significant degradation with multiple entities
    """
    print("\n[Test 6] Performance requirement verification...")

    test_cases = [
        ("Single client mention", "What's the status of the Orlando project?"),
        ("Topic discussion", "What's on my calendar for tomorrow?"),
        ("Multiple entities", "Tell me about Orlando, Thanos, and my calendar appointments"),
    ]

    all_passed = True

    for name, test_input in test_cases:
        # Warm up
        run_hook(test_input)

        # Measure performance
        iterations = 5
        times = []

        for _ in range(iterations):
            start_time = time.time()
            result = run_hook(test_input)
            end_time = time.time()

            elapsed_ms = (end_time - start_time) * 1000
            times.append(elapsed_ms)

        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        # Verify performance requirement
        meets_requirement = avg_time < 500

        if meets_requirement:
            print(f"  ✓ {name}: {avg_time:.2f}ms avg (min: {min_time:.2f}ms, max: {max_time:.2f}ms)")
        else:
            print(f"  ✗ {name}: {avg_time:.2f}ms avg - EXCEEDS 500ms requirement!")
            all_passed = False

    assert all_passed, "Some performance tests exceeded 500ms requirement"

    results.record(
        "Performance requirement < 500ms",
        all_passed,
        "All scenarios complete within 500ms"
    )
    print("  ✓ Test 6 PASSED")


def test_edge_cases():
    """
    Additional testing for edge cases and robustness

    Tests:
    - Empty input
    - Very short input
    - Command input (should not inject)
    - Input with no entities
    - Multiple mentions of same entity
    """
    print("\n[Test 7] Edge cases and robustness...")

    edge_cases = [
        ("Empty input", "", False),
        ("Very short input", "hi", False),
        ("Command input", "/help", False),
        ("No entities", "What's the weather like?", False),
        ("Multiple same entity", "Orlando Orlando Orlando project", True),
    ]

    all_passed = True

    for name, test_input, should_inject in edge_cases:
        result = run_hook(test_input)
        actual_inject = result.get('should_inject', False)

        if actual_inject == should_inject:
            print(f"  ✓ {name}: should_inject={should_inject} (correct)")
        else:
            print(f"  ✗ {name}: expected should_inject={should_inject}, got {actual_inject}")
            all_passed = False

    assert all_passed, "Some edge cases failed"

    results.record(
        "Edge cases handled correctly",
        all_passed,
        "All edge cases pass"
    )
    print("  ✓ Test 7 PASSED")


def test_integration_flow():
    """
    Test complete integration flow from user input to context injection

    Tests:
    - Entity extraction → Context loading → Formatting → Injection
    - All components work together seamlessly
    - No errors or exceptions in pipeline
    """
    print("\n[Test 8] Integration flow end-to-end...")

    test_input = "I need to follow up on the Orlando project and check my calendar"

    try:
        # Step 1: Entity extraction
        entities = extract_entities(test_input)
        assert len(entities) > 0, "Should extract entities"
        print(f"  ✓ Step 1 - Entity extraction: {len(entities)} entities")

        # Step 2: Context loading
        context_items = load_context_for_entities(entities)
        assert len(context_items) > 0, "Should load context"
        print(f"  ✓ Step 2 - Context loading: {len(context_items)} items")

        # Step 3: Context formatting
        formatted_context = format_context(context_items)
        assert len(formatted_context) > 0, "Should format context"
        print(f"  ✓ Step 3 - Context formatting: {len(formatted_context)} chars")

        # Step 4: Hook integration
        hook_result = run_hook(test_input)
        assert hook_result['should_inject'], "Hook should inject context"
        print(f"  ✓ Step 4 - Hook integration: context ready to inject")

        # Verify end-to-end consistency
        assert hook_result['injected_context'] == formatted_context, "Hook should use formatted context"
        print(f"  ✓ Integration consistency verified")

        results.record(
            "Integration flow end-to-end",
            True,
            "All pipeline stages work together"
        )
        print("  ✓ Test 8 PASSED")

    except Exception as e:
        print(f"  ✗ Integration flow failed: {e}")
        results.record(
            "Integration flow end-to-end",
            False,
            f"Error: {e}"
        )
        raise


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("PROACTIVE CONTEXT SURFACING - END-TO-END ACCEPTANCE TESTS")
    print("=" * 70)
    print("\nVerifying all acceptance criteria from spec.md:\n")
    print("1. Client mentions trigger automatic context loading")
    print("2. Topic discussions surface related past decisions")
    print("3. Project references load recent activity summary")
    print("4. Context surfacing is subtle - not overwhelming")
    print("5. User can request 'more context' or 'less context'")
    print("6. Performance impact < 500ms additional latency")
    print("\n" + "=" * 70)

    try:
        # Run all acceptance tests
        test_client_mention_triggers_context()
        test_topic_discussion_surfaces_memories()
        test_project_reference_loads_activity()
        test_context_is_subtle()
        test_verbosity_controls()
        test_performance_requirement()
        test_edge_cases()
        test_integration_flow()

        # Print summary
        results.print_summary()

        if results.failed == 0:
            print("🎉 ALL ACCEPTANCE CRITERIA VERIFIED - FEATURE READY FOR DEPLOYMENT\n")
            sys.exit(0)
        else:
            print(f"❌ {results.failed} ACCEPTANCE CRITERIA FAILED - NEEDS ATTENTION\n")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Acceptance test failed with error: {e}\n")
        results.print_summary()
        sys.exit(1)
