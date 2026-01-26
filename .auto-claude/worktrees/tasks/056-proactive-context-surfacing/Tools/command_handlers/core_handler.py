"""
Core Command Handler

Provides handlers for user commands that control context verbosity.
Commands: /more-context, /less-context

Pattern: Simple command handlers that update user preferences and return feedback
"""
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.proactive_context import (
    set_context_verbosity,
    get_user_preferences,
    get_verbosity_settings
)


def handle_more_context() -> Dict[str, Any]:
    """
    Handle /more-context command.

    Increases context verbosity level:
    - minimal -> normal
    - normal -> detailed
    - detailed -> detailed (already at max)

    Returns:
        Dict with:
        - success: bool indicating if command succeeded
        - message: str with user-friendly feedback
        - previous_level: str with previous verbosity level
        - new_level: str with new verbosity level
    """
    # Get current preferences
    prefs = get_user_preferences()
    current_verbosity = prefs.get('context_verbosity', 'normal')

    # Determine new verbosity level
    verbosity_ladder = {
        'minimal': 'normal',
        'normal': 'detailed',
        'detailed': 'detailed'  # Already at max
    }

    new_verbosity = verbosity_ladder.get(current_verbosity, 'normal')

    # Check if already at max
    if current_verbosity == 'detailed':
        return {
            'success': True,
            'message': '✨ Context verbosity is already at maximum (detailed). You\'ll receive comprehensive context with up to 10 results per entity and 1500 token budget.',
            'previous_level': current_verbosity,
            'new_level': new_verbosity
        }

    # Update verbosity preference
    success = set_context_verbosity(new_verbosity)

    if not success:
        return {
            'success': False,
            'message': '❌ Failed to update context verbosity. Please check State/jeremy.json file permissions.',
            'previous_level': current_verbosity,
            'new_level': current_verbosity
        }

    # Get new settings
    max_results, max_tokens = get_verbosity_settings(new_verbosity)

    # Build success message
    level_descriptions = {
        'normal': f'balanced context (up to {max_results} results per entity, {max_tokens} token budget)',
        'detailed': f'comprehensive context (up to {max_results} results per entity, {max_tokens} token budget)'
    }

    description = level_descriptions.get(new_verbosity, 'context surfacing')

    message = f'✅ Context verbosity increased from **{current_verbosity}** to **{new_verbosity}**.\n\n'
    message += f'You\'ll now receive {description}.'

    return {
        'success': True,
        'message': message,
        'previous_level': current_verbosity,
        'new_level': new_verbosity
    }


def handle_less_context() -> Dict[str, Any]:
    """
    Handle /less-context command.

    Decreases context verbosity level:
    - detailed -> normal
    - normal -> minimal
    - minimal -> minimal (already at min)

    Returns:
        Dict with:
        - success: bool indicating if command succeeded
        - message: str with user-friendly feedback
        - previous_level: str with previous verbosity level
        - new_level: str with new verbosity level
    """
    # Get current preferences
    prefs = get_user_preferences()
    current_verbosity = prefs.get('context_verbosity', 'normal')

    # Determine new verbosity level
    verbosity_ladder = {
        'detailed': 'normal',
        'normal': 'minimal',
        'minimal': 'minimal'  # Already at min
    }

    new_verbosity = verbosity_ladder.get(current_verbosity, 'normal')

    # Check if already at min
    if current_verbosity == 'minimal':
        return {
            'success': True,
            'message': '✨ Context verbosity is already at minimum (minimal). You\'ll receive only the highest priority context with up to 2 results per entity and 400 token budget.',
            'previous_level': current_verbosity,
            'new_level': new_verbosity
        }

    # Update verbosity preference
    success = set_context_verbosity(new_verbosity)

    if not success:
        return {
            'success': False,
            'message': '❌ Failed to update context verbosity. Please check State/jeremy.json file permissions.',
            'previous_level': current_verbosity,
            'new_level': current_verbosity
        }

    # Get new settings
    max_results, max_tokens = get_verbosity_settings(new_verbosity)

    # Build success message
    level_descriptions = {
        'normal': f'balanced context (up to {max_results} results per entity, {max_tokens} token budget)',
        'minimal': f'only the highest priority context (up to {max_results} results per entity, {max_tokens} token budget)'
    }

    description = level_descriptions.get(new_verbosity, 'context surfacing')

    message = f'✅ Context verbosity decreased from **{current_verbosity}** to **{new_verbosity}**.\n\n'
    message += f'You\'ll now receive {description}.'

    return {
        'success': True,
        'message': message,
        'previous_level': current_verbosity,
        'new_level': new_verbosity
    }


def handle_context_status() -> Dict[str, Any]:
    """
    Handle /context-status command (bonus helper).

    Shows current context verbosity settings.

    Returns:
        Dict with:
        - success: bool (always True for status check)
        - message: str with current settings
        - current_level: str with current verbosity level
    """
    # Get current preferences
    prefs = get_user_preferences()
    current_verbosity = prefs.get('context_verbosity', 'normal')

    # Get current settings
    max_results, max_tokens = get_verbosity_settings(current_verbosity)

    message = f'📊 **Current Context Verbosity: {current_verbosity}**\n\n'
    message += f'- Max results per entity: {max_results}\n'
    message += f'- Token budget: {max_tokens}\n\n'
    message += 'Use `/more-context` or `/less-context` to adjust.'

    return {
        'success': True,
        'message': message,
        'current_level': current_verbosity
    }


# Convenience test functions
if __name__ == '__main__':
    print("=== Testing Context Control Commands ===\n")

    # Test status
    print("1. Check current status:")
    result = handle_context_status()
    print(result['message'])
    print("\n" + "="*50 + "\n")

    # Test more context
    print("2. Request more context:")
    result = handle_more_context()
    print(result['message'])
    print("\n" + "="*50 + "\n")

    # Test less context
    print("3. Request less context:")
    result = handle_less_context()
    print(result['message'])
    print("\n" + "="*50 + "\n")

    # Test final status
    print("4. Check final status:")
    result = handle_context_status()
    print(result['message'])
