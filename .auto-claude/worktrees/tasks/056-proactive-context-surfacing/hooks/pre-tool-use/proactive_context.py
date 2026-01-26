"""
Proactive Context Hook

Pre-tool-use hook that automatically surfaces relevant context when entities
are detected in user input. Anticipates information needs before being asked.

Hook Flow:
1. Receives user input before tools are invoked
2. Extracts entities (clients, projects, topics) from input
3. Loads relevant memories for detected entities
4. Formats and injects context into system prompt

Pattern: Hook module that integrates entity_extractor and proactive_context
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.entity_extractor import extract_entities, get_entity_context
from Tools.proactive_context import (
    load_context_for_entities,
    format_context,
    get_context_summary,
    get_user_preferences
)


def should_inject_context(user_input: str, context: Dict[str, Any]) -> bool:
    """
    Determine if we should inject proactive context based on user input and session state.

    Args:
        user_input: The user's input text
        context: Session context dict with metadata

    Returns:
        True if context should be injected, False otherwise
    """
    # Don't inject for very short inputs (likely not substantive)
    if len(user_input.strip()) < 10:
        return False

    # Don't inject for command-like inputs (starting with /)
    if user_input.strip().startswith('/'):
        return False

    # Check if user has disabled proactive context
    prefs = get_user_preferences()
    if prefs.get('proactive_context_enabled', True) is False:
        return False

    return True


def run_hook(user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main hook function called before tool use.

    This hook is invoked by the system before processing user input with tools.
    It extracts entities and loads relevant context proactively.

    Args:
        user_input: The user's input text
        context: Optional session context dict with metadata

    Returns:
        Dict with hook result:
        {
            'injected_context': str,  # Formatted context to inject
            'entities_detected': list,  # List of detected entities
            'context_summary': str,  # Human-readable summary
            'should_inject': bool  # Whether to inject context
        }
    """
    if context is None:
        context = {}

    # Check if we should inject context
    if not should_inject_context(user_input, context):
        return {
            'injected_context': '',
            'entities_detected': [],
            'context_summary': '',
            'should_inject': False
        }

    # Extract entities from user input
    entities = extract_entities(user_input)

    # If no entities detected, no context to inject
    if not entities:
        return {
            'injected_context': '',
            'entities_detected': [],
            'context_summary': 'No entities detected',
            'should_inject': False
        }

    # Load context for detected entities
    context_items = load_context_for_entities(entities)

    # If no context found, don't inject
    if not context_items:
        return {
            'injected_context': '',
            'entities_detected': entities,
            'context_summary': get_context_summary(entities),
            'should_inject': False
        }

    # Format context for injection
    formatted_context = format_context(context_items)

    # Generate summary
    summary = get_context_summary(entities)

    return {
        'injected_context': formatted_context,
        'entities_detected': entities,
        'context_summary': summary,
        'should_inject': True
    }


def inject_into_system_prompt(base_prompt: str, injected_context: str) -> str:
    """
    Inject proactive context into system prompt.

    Args:
        base_prompt: The base system prompt
        injected_context: The formatted context to inject

    Returns:
        Modified system prompt with injected context
    """
    if not injected_context or not injected_context.strip():
        return base_prompt

    # Inject context at the beginning of system prompt for visibility
    injection = f"{injected_context}\n\n---\n\n"
    return injection + base_prompt


def inject_into_tool_args(tool_args: Dict[str, Any], injected_context: str) -> Dict[str, Any]:
    """
    Inject proactive context into tool arguments.

    Some tools may benefit from having context in their args.
    This is an alternative injection point to system prompt.

    Args:
        tool_args: Tool arguments dict
        injected_context: The formatted context to inject

    Returns:
        Modified tool_args with injected context
    """
    if not injected_context or not injected_context.strip():
        return tool_args

    # Add context as metadata to tool args
    tool_args['_proactive_context'] = injected_context
    return tool_args


# Convenience function for quick testing
def test_hook(user_input: str) -> None:
    """
    Test the hook with a sample user input.

    Args:
        user_input: Sample user input to test
    """
    result = run_hook(user_input)

    print(f"User Input: {user_input}")
    print(f"Entities Detected: {result['context_summary']}")
    print(f"Should Inject: {result['should_inject']}")
    print(f"\nInjected Context:\n{result['injected_context']}")


if __name__ == '__main__':
    # Test with sample inputs
    print("=== Testing Proactive Context Hook ===\n")

    test_hook("What's the status of the Orlando project?")
    print("\n" + "="*50 + "\n")

    test_hook("Check my calendar for tomorrow")
    print("\n" + "="*50 + "\n")

    test_hook("Hi there")  # Should not inject (too short/generic)
