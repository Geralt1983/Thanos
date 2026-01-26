"""
Performance Tests for Proactive Context Surfacing

Verifies that entity detection, memory search, and context formatting
meet the < 500ms latency requirement specified in acceptance criteria.

Performance Requirements:
- Entity detection < 50ms
- Memory search < 200ms
- Context formatting < 50ms
- Total end-to-end latency < 500ms
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
    search_memory_for_entity
)
# Import hook module directly by path since it uses hyphens
import importlib.util
hook_path = Path(__file__).parent.parent / 'hooks' / 'pre-tool-use' / 'proactive_context.py'
spec = importlib.util.spec_from_file_location("proactive_context_hook", hook_path)
hook_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook_module)
run_hook = hook_module.run_hook


def test_entity_detection_performance():
    """Test that entity detection completes in < 50ms"""
    # Sample input with multiple entities
    test_input = "What's the status of the Orlando project? I need to check my calendar for tomorrow and schedule a health appointment."

    # Warm up (first run may be slower due to file loading)
    extract_entities(test_input)

    # Measure performance
    iterations = 10
    total_time = 0

    for _ in range(iterations):
        start_time = time.time()
        entities = extract_entities(test_input)
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000
        total_time += elapsed_ms

    avg_time_ms = total_time / iterations

    # Verify entities were found
    assert len(entities) > 0, "No entities detected in test input"

    # Verify performance requirement
    assert avg_time_ms < 50, f"Entity detection took {avg_time_ms:.2f}ms, expected < 50ms"

    print(f"✓ Entity detection: {avg_time_ms:.2f}ms (< 50ms required)")


def test_memory_search_performance():
    """Test that memory search completes in < 200ms per entity"""
    # Create test entity
    test_entity = {
        'text': 'Orlando',
        'type': 'client',
        'confidence': 1.0
    }

    # Warm up
    search_memory_for_entity(test_entity, limit=5)

    # Measure performance
    iterations = 10
    total_time = 0

    for _ in range(iterations):
        start_time = time.time()
        memories = search_memory_for_entity(test_entity, limit=5)
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000
        total_time += elapsed_ms

    avg_time_ms = total_time / iterations

    # Verify memories were returned (mock or real)
    assert len(memories) > 0, "No memories returned from search"

    # Verify performance requirement
    assert avg_time_ms < 200, f"Memory search took {avg_time_ms:.2f}ms, expected < 200ms"

    print(f"✓ Memory search: {avg_time_ms:.2f}ms (< 200ms required)")


def test_context_formatting_performance():
    """Test that context formatting completes in < 50ms"""
    # Create test context items
    test_context = [
        {
            'entity': 'Orlando',
            'entity_type': 'client',
            'memory': 'Recent discussion about Orlando project timeline and deliverables',
            'heat': 0.85,
            'priority_score': 0.9,
            'timestamp': '2026-01-25T10:00:00Z'
        },
        {
            'entity': 'calendar',
            'entity_type': 'topic',
            'memory': 'User has upcoming appointments scheduled for next week',
            'heat': 0.6,
            'priority_score': 0.65,
            'timestamp': '2026-01-24T15:30:00Z'
        },
        {
            'entity': 'health',
            'entity_type': 'topic',
            'memory': 'User mentioned needing to schedule annual checkup',
            'heat': 0.7,
            'priority_score': 0.72,
            'timestamp': '2026-01-23T09:15:00Z'
        }
    ]

    # Warm up
    format_context(test_context, max_tokens=800)

    # Measure performance
    iterations = 10
    total_time = 0

    for _ in range(iterations):
        start_time = time.time()
        formatted = format_context(test_context, max_tokens=800)
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000
        total_time += elapsed_ms

    avg_time_ms = total_time / iterations

    # Verify formatting produced output
    assert len(formatted) > 0, "No formatted output produced"
    assert "Proactive Context" in formatted, "Formatted output missing header"

    # Verify performance requirement
    assert avg_time_ms < 50, f"Context formatting took {avg_time_ms:.2f}ms, expected < 50ms"

    print(f"✓ Context formatting: {avg_time_ms:.2f}ms (< 50ms required)")


def test_end_to_end_latency():
    """Test that complete end-to-end flow completes in < 500ms"""
    # Sample user input with entities
    test_input = "What's the status of the Orlando project? I need to check my calendar for tomorrow."

    # Warm up
    run_hook(test_input)

    # Measure performance
    iterations = 10
    total_time = 0

    for _ in range(iterations):
        start_time = time.time()
        result = run_hook(test_input)
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000
        total_time += elapsed_ms

    avg_time_ms = total_time / iterations

    # Verify hook produced results
    assert 'entities_detected' in result, "Hook result missing entities_detected"
    assert 'should_inject' in result, "Hook result missing should_inject"

    # Verify performance requirement
    assert avg_time_ms < 500, f"End-to-end latency was {avg_time_ms:.2f}ms, expected < 500ms"

    print(f"✓ End-to-end latency: {avg_time_ms:.2f}ms (< 500ms required)")


def test_context_loading_performance():
    """Test that context loading for multiple entities completes in < 300ms"""
    # Create test entities
    test_entities = [
        {'text': 'Orlando', 'type': 'client', 'confidence': 1.0},
        {'text': 'calendar', 'type': 'topic', 'confidence': 1.0},
        {'text': 'health', 'type': 'topic', 'confidence': 1.0}
    ]

    # Warm up
    load_context_for_entities(test_entities, max_results_per_entity=5)

    # Measure performance
    iterations = 10
    total_time = 0

    for _ in range(iterations):
        start_time = time.time()
        context = load_context_for_entities(test_entities, max_results_per_entity=5)
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000
        total_time += elapsed_ms

    avg_time_ms = total_time / iterations

    # Verify context was loaded
    assert len(context) > 0, "No context loaded for entities"

    # Verify performance (should be much faster than 500ms)
    assert avg_time_ms < 300, f"Context loading took {avg_time_ms:.2f}ms, expected < 300ms"

    print(f"✓ Context loading: {avg_time_ms:.2f}ms (< 300ms required)")


def test_performance_under_load():
    """Test performance with larger input and multiple entities"""
    # Create a longer input with multiple entities
    test_input = """
    I need to follow up on the Orlando project status and check if there are any
    calendar conflicts for next week. Also, I should schedule a health checkup
    appointment and review my commitments for the month. Let me know about any
    deadlines coming up and whether the team needs anything from me.
    """

    # Warm up
    run_hook(test_input)

    # Measure performance
    iterations = 5  # Fewer iterations for larger input
    total_time = 0

    for _ in range(iterations):
        start_time = time.time()
        result = run_hook(test_input)
        end_time = time.time()

        elapsed_ms = (end_time - start_time) * 1000
        total_time += elapsed_ms

    avg_time_ms = total_time / iterations

    # Verify multiple entities were detected
    num_entities = len(result.get('entities_detected', []))
    assert num_entities > 0, "No entities detected in complex input"

    # Verify performance requirement even with longer input
    assert avg_time_ms < 500, f"Performance under load was {avg_time_ms:.2f}ms, expected < 500ms"

    print(f"✓ Performance under load ({num_entities} entities): {avg_time_ms:.2f}ms (< 500ms required)")


if __name__ == '__main__':
    # Run all tests
    print("\n=== Proactive Context Performance Tests ===\n")

    try:
        test_entity_detection_performance()
        test_memory_search_performance()
        test_context_formatting_performance()
        test_context_loading_performance()
        test_end_to_end_latency()
        test_performance_under_load()

        print("\n✓ All performance tests passed!\n")

    except AssertionError as e:
        print(f"\n✗ Performance test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        sys.exit(1)
