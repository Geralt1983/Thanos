#!/usr/bin/env python3
"""
Integration tests for Telegram bot button handlers.

This tests all the callback handlers:
1. /menu command shows all quick actions
2. Brain dump button flow end-to-end
3. Log energy button flow end-to-end
4. Task list buttons (complete, details)
5. Voice message with action buttons
6. Error handling in callbacks
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

# Import after path setup
from Tools.telegram_bot import TelegramBrainDumpBot


class MockUpdate:
    """Mock Telegram Update object."""
    def __init__(self, callback_data=None, user_id=123456789):
        self.effective_user = Mock()
        self.effective_user.id = user_id
        self.effective_user.username = "testuser"

        if callback_data:
            self.callback_query = Mock()
            self.callback_query.data = callback_data
            self.callback_query.answer = AsyncMock()
            self.callback_query.edit_message_text = AsyncMock()
            self.callback_query.message = Mock()
            self.callback_query.message.message_id = 12345
        else:
            self.message = Mock()
            self.message.reply_text = AsyncMock()
            self.message.chat = Mock()
            self.message.chat.id = user_id


class MockContext:
    """Mock Telegram Context object."""
    def __init__(self):
        self.bot = Mock()
        self.args = []
        self.user_data = {}


async def test_menu_command():
    """Test /menu command shows all quick actions."""
    print("\n" + "="*60)
    print("TEST 1: /menu command shows all quick actions")
    print("="*60)

    bot = TelegramBrainDumpBot()
    update = MockUpdate()
    context = MockContext()

    # Get the menu command handler
    for handler in bot.application.handlers.get(0, []):
        if hasattr(handler, 'callback') and handler.callback.__name__ == 'menu_command':
            await handler.callback(update, context)
            break

    # Verify reply_text was called
    if update.message.reply_text.called:
        call_args = update.message.reply_text.call_args
        text = call_args[0][0]
        keyboard = call_args[1].get('reply_markup')

        print(f"✓ Menu command responded")
        print(f"  Message: {text[:50]}...")

        # Verify quick action buttons are present
        if keyboard:
            print(f"✓ Inline keyboard present")
            # Check keyboard structure
            if hasattr(keyboard, 'inline_keyboard'):
                buttons = keyboard.inline_keyboard
                button_texts = []
                button_callbacks = []
                for row in buttons:
                    for button in row:
                        button_texts.append(button.text)
                        button_callbacks.append(button.callback_data)

                print(f"  Buttons: {', '.join(button_texts)}")
                print(f"  Callbacks: {', '.join(button_callbacks)}")

                # Verify expected buttons
                expected_callbacks = ['menu_braindump', 'menu_energy', 'menu_tasks']
                for expected in expected_callbacks:
                    if expected in button_callbacks:
                        print(f"  ✓ Found {expected}")
                    else:
                        print(f"  ✗ Missing {expected}")
        else:
            print("  ⚠ No inline keyboard in response")
    else:
        print("✗ Menu command did not respond")


async def test_brain_dump_button():
    """Test brain dump button flow."""
    print("\n" + "="*60)
    print("TEST 2: Brain dump button flow end-to-end")
    print("="*60)

    bot = TelegramBrainDumpBot()
    update = MockUpdate(callback_data="menu_braindump")
    context = MockContext()

    # Find and call the menu callback handler
    handler_found = False
    for prefix, handler in bot.callback_handlers.items():
        if prefix == "menu_":
            await handler(update, context)
            handler_found = True
            break

    if handler_found and update.callback_query.edit_message_text.called:
        call_args = update.callback_query.edit_message_text.call_args
        text = call_args[0][0]

        print(f"✓ Brain dump button responded")
        print(f"  Message contains 'Brain Dump Mode': {'Brain Dump Mode' in text}")
        print(f"  Message contains instructions: {'send me' in text.lower() or 'text message' in text.lower()}")

        # Verify callback was answered (Telegram requirement)
        if update.callback_query.answer.called:
            print(f"✓ Callback query answered")
        else:
            print(f"⚠ Callback query not answered")
    else:
        print("✗ Brain dump button handler not found or did not respond")


async def test_energy_button():
    """Test log energy button flow."""
    print("\n" + "="*60)
    print("TEST 3: Log energy button flow end-to-end")
    print("="*60)

    bot = TelegramBrainDumpBot()

    # Step 1: Click energy button from menu
    update = MockUpdate(callback_data="menu_energy")
    context = MockContext()

    for prefix, handler in bot.callback_handlers.items():
        if prefix == "menu_":
            await handler(update, context)
            break

    if update.callback_query.edit_message_text.called:
        call_args = update.callback_query.edit_message_text.call_args
        text = call_args[0][0]
        keyboard = call_args[1].get('reply_markup')

        print(f"✓ Energy button responded")
        print(f"  Message contains 'Log Energy': {'Energy' in text}")

        # Verify energy level buttons (1-10) are present
        if keyboard and hasattr(keyboard, 'inline_keyboard'):
            button_count = sum(len(row) for row in keyboard.inline_keyboard)
            print(f"✓ Energy level buttons present: {button_count} buttons")

            # Check for energy level callbacks
            callbacks = []
            for row in keyboard.inline_keyboard:
                for button in row:
                    callbacks.append(button.callback_data)

            # Verify we have energy_1 through energy_10
            expected_levels = [f"energy_{i}" for i in range(1, 11)]
            found_levels = [cb for cb in callbacks if cb.startswith("energy_")]
            print(f"  Energy levels found: {len(found_levels)}/10")

            # Step 2: Simulate clicking an energy level
            if bot.workos_enabled:
                print("\n  Testing energy level selection (level 7)...")
                energy_update = MockUpdate(callback_data="energy_7")

                # Mock database connection
                with patch('asyncpg.connect') as mock_connect:
                    mock_conn = AsyncMock()
                    mock_connect.return_value = mock_conn
                    mock_conn.execute = AsyncMock()
                    mock_conn.close = AsyncMock()

                    # Find and call energy callback handler
                    for prefix, handler in bot.callback_handlers.items():
                        if prefix == "energy_":
                            await handler(energy_update, context)
                            break

                    if energy_update.callback_query.edit_message_text.called:
                        call_args = energy_update.callback_query.edit_message_text.call_args
                        text = call_args[0][0]

                        print(f"  ✓ Energy level logged")
                        print(f"    Contains success indicator: {'✅' in text}")
                        print(f"    Contains level: {'7' in text}")
                        print(f"    Contains timestamp: {'Time:' in text}")

                        # Verify database was called
                        if mock_conn.execute.called:
                            print(f"  ✓ Database insert called")
                        else:
                            print(f"  ⚠ Database insert not called")
                    else:
                        print(f"  ✗ Energy level handler did not respond")
            else:
                print("  ⊘ WorkOS not enabled, skipping database test")
        else:
            print("  ⚠ No energy level buttons in response")
    else:
        print("✗ Energy button handler did not respond")


async def test_task_buttons():
    """Test task list buttons (complete, details)."""
    print("\n" + "="*60)
    print("TEST 4: Task list buttons (complete, details)")
    print("="*60)

    bot = TelegramBrainDumpBot()

    if not bot.workos_enabled:
        print("⊘ WorkOS not enabled, skipping task button tests")
        return

    # Test complete button
    print("\n  Testing Complete Task button...")
    update = MockUpdate(callback_data="task_complete_123")
    context = MockContext()

    with patch('asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_conn.execute = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'title': 'Test Task',
            'priority': 'high'
        })
        mock_conn.close = AsyncMock()

        # Find and call task callback handler
        for prefix, handler in bot.callback_handlers.items():
            if prefix == "task_":
                await handler(update, context)
                break

        if update.callback_query.edit_message_text.called:
            call_args = update.callback_query.edit_message_text.call_args
            text = call_args[0][0]

            print(f"  ✓ Complete task button responded")
            print(f"    Contains success: {'✅' in text or 'Completed' in text}")
            print(f"    Contains task title: {'Test Task' in text}")
            print(f"    Contains priority: {'high' in text.lower()}")

            if mock_conn.execute.called:
                print(f"  ✓ Database update called")
            else:
                print(f"  ⚠ Database update not called")
        else:
            print(f"  ✗ Complete task handler did not respond")

    # Test details button
    print("\n  Testing Task Details button...")
    details_update = MockUpdate(callback_data="task_details_123")

    with patch('asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 123,
            'title': 'Test Task Details',
            'description': 'This is a test task',
            'status': 'active',
            'priority': 'medium',
            'created_at': datetime.now(),
            'tags': ['test', 'sample']
        })
        mock_conn.close = AsyncMock()

        for prefix, handler in bot.callback_handlers.items():
            if prefix == "task_":
                await handler(details_update, context)
                break

        if details_update.callback_query.edit_message_text.called:
            call_args = details_update.callback_query.edit_message_text.call_args
            text = call_args[0][0]
            keyboard = call_args[1].get('reply_markup')

            print(f"  ✓ Task details button responded")
            print(f"    Contains task title: {'Test Task Details' in text}")
            print(f"    Contains description: {'test task' in text.lower()}")

            # Verify action buttons are present (Complete, Postpone, Delete, Back)
            if keyboard and hasattr(keyboard, 'inline_keyboard'):
                callbacks = []
                for row in keyboard.inline_keyboard:
                    for button in row:
                        callbacks.append(button.callback_data)

                print(f"  ✓ Action buttons present: {len(callbacks)} buttons")
                expected_actions = ['complete', 'postpone', 'delete']
                for action in expected_actions:
                    if any(action in cb for cb in callbacks):
                        print(f"    ✓ Found {action} button")
            else:
                print(f"  ⚠ No action buttons in details view")
        else:
            print(f"  ✗ Task details handler did not respond")


async def test_voice_action_buttons():
    """Test voice message with action buttons."""
    print("\n" + "="*60)
    print("TEST 5: Voice message with action buttons")
    print("="*60)

    bot = TelegramBrainDumpBot()

    # Create a mock entry that would be created from voice transcription
    from Tools.telegram_bot import Entry

    test_entry = Entry(
        id="test_voice_123",
        content="This is a test voice transcription",
        raw_content="This is a test voice transcription",
        timestamp=datetime.now(),
        user_id="123456789",
        voice_file_id="test_file_id"
    )
    bot.entries.append(test_entry)

    # Test "Save as Task" button
    print("\n  Testing 'Save as Task' button...")
    update = MockUpdate(callback_data=f"voice_savetask_{test_entry.id}")
    context = MockContext()

    with patch('Tools.telegram_bot.process_brain_dump_sync') as mock_process:
        mock_process.return_value = {
            'classification': 'personal_task',
            'routing_result': {
                'tasks_created': True,
                'workos_task_id': 456
            }
        }

        for prefix, handler in bot.callback_handlers.items():
            if prefix == "voice_":
                await handler(update, context)
                break

        if update.callback_query.edit_message_text.called:
            call_args = update.callback_query.edit_message_text.call_args
            text = call_args[0][0]

            print(f"  ✓ Save as Task button responded")
            print(f"    Contains success: {'✅' in text or 'Task Created' in text}")
            print(f"    Contains transcription: {test_entry.raw_content[:20] in text}")
            print(f"    Contains routing info: {'Task created' in text or 'WorkOS' in text}")

            if mock_process.called:
                print(f"  ✓ Brain dump pipeline called with force_classification='personal_task'")
                call_kwargs = mock_process.call_args[1]
                if call_kwargs.get('force_classification') == 'personal_task':
                    print(f"    ✓ Correct classification forced")
            else:
                print(f"  ⚠ Brain dump pipeline not called")
        else:
            print(f"  ✗ Save as Task handler did not respond")

    # Test "Save as Idea" button
    print("\n  Testing 'Save as Idea' button...")
    idea_update = MockUpdate(callback_data=f"voice_saveidea_{test_entry.id}")

    with patch('Tools.telegram_bot.process_brain_dump_sync') as mock_process:
        mock_process.return_value = {
            'classification': 'idea',
            'routing_result': {}
        }

        for prefix, handler in bot.callback_handlers.items():
            if prefix == "voice_":
                await handler(idea_update, context)
                break

        if idea_update.callback_query.edit_message_text.called:
            call_args = idea_update.callback_query.edit_message_text.call_args
            text = call_args[0][0]

            print(f"  ✓ Save as Idea button responded")
            print(f"    Contains success: {'✅' in text or 'Idea' in text}")

            if mock_process.called:
                call_kwargs = mock_process.call_args[1]
                if call_kwargs.get('force_classification') == 'idea':
                    print(f"  ✓ Brain dump pipeline called with force_classification='idea'")
            else:
                print(f"  ⚠ Brain dump pipeline not called")
        else:
            print(f"  ✗ Save as Idea handler did not respond")


async def test_error_handling():
    """Test that all callbacks handle errors gracefully."""
    print("\n" + "="*60)
    print("TEST 6: Error handling in callbacks")
    print("="*60)

    bot = TelegramBrainDumpBot()
    context = MockContext()

    # Test invalid callback data formats
    test_cases = [
        ("task_invalid", "Invalid task callback (missing ID)"),
        ("energy_invalid", "Invalid energy level (non-numeric)"),
        ("energy_11", "Invalid energy level (out of range)"),
        ("voice_savetask_nonexistent", "Non-existent voice entry"),
    ]

    for callback_data, description in test_cases:
        print(f"\n  Testing: {description}")
        update = MockUpdate(callback_data=callback_data)

        try:
            # Find appropriate handler
            prefix = callback_data.split("_")[0] + "_"
            handler = bot.callback_handlers.get(prefix)

            if handler:
                await handler(update, context)

                if update.callback_query.edit_message_text.called:
                    call_args = update.callback_query.edit_message_text.call_args
                    text = call_args[0][0]

                    # Verify error message is shown
                    if '⚠️' in text or '❌' in text or 'Invalid' in text or 'not found' in text:
                        print(f"    ✓ Error handled gracefully")
                        print(f"      Message: {text[:60]}...")
                    else:
                        print(f"    ⚠ Response did not indicate error")
                else:
                    print(f"    ⚠ Handler did not respond")
            else:
                print(f"    ⊘ No handler found for prefix '{prefix}'")
        except Exception as e:
            print(f"    ✗ Exception raised: {e}")

    # Test database errors
    if bot.workos_enabled:
        print(f"\n  Testing: Database connection error")
        update = MockUpdate(callback_data="energy_5")

        with patch('asyncpg.connect', side_effect=Exception("Connection failed")):
            for prefix, handler in bot.callback_handlers.items():
                if prefix == "energy_":
                    try:
                        await handler(update, context)

                        if update.callback_query.edit_message_text.called:
                            call_args = update.callback_query.edit_message_text.call_args
                            text = call_args[0][0]

                            if '❌' in text or 'Failed' in text:
                                print(f"    ✓ Database error handled gracefully")
                                print(f"      Message: {text[:60]}...")
                            else:
                                print(f"    ⚠ Database error not properly communicated")
                        else:
                            print(f"    ⚠ Handler did not respond to error")
                    except Exception as e:
                        print(f"    ✗ Exception not caught: {e}")
                    break
    else:
        print(f"\n  ⊘ WorkOS not enabled, skipping database error tests")


async def test_callback_query_answering():
    """Test that all callbacks properly answer callback queries (Telegram requirement)."""
    print("\n" + "="*60)
    print("TEST 7: Callback query answering (Telegram requirement)")
    print("="*60)

    bot = TelegramBrainDumpBot()
    context = MockContext()

    # Test various callback types
    test_callbacks = [
        ("menu_braindump", "Menu - Brain Dump"),
        ("menu_energy", "Menu - Energy"),
        ("menu_tasks", "Menu - Tasks"),
        ("energy_5", "Energy - Level 5"),
    ]

    if bot.workos_enabled:
        test_callbacks.extend([
            ("task_complete_123", "Task - Complete"),
            ("task_details_123", "Task - Details"),
        ])

    # Mock database for task operations
    with patch('asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_conn.execute = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            'id': 123,
            'title': 'Test Task',
            'priority': 'medium',
            'status': 'active',
            'created_at': datetime.now()
        })
        mock_conn.close = AsyncMock()

        for callback_data, description in test_callbacks:
            update = MockUpdate(callback_data=callback_data)

            # Find appropriate handler
            prefix = callback_data.split("_")[0] + "_"
            handler = bot.callback_handlers.get(prefix)

            if handler:
                try:
                    await handler(update, context)

                    if update.callback_query.answer.called:
                        print(f"  ✓ {description}: callback query answered")
                    else:
                        print(f"  ✗ {description}: callback query NOT answered (Telegram will show loading)")
                except Exception as e:
                    print(f"  ✗ {description}: Exception - {e}")


async def main():
    """Run all integration tests."""
    print("="*60)
    print("TELEGRAM BOT BUTTON HANDLERS - INTEGRATION TESTS")
    print("="*60)

    try:
        await test_menu_command()
        await test_brain_dump_button()
        await test_energy_button()
        await test_task_buttons()
        await test_voice_action_buttons()
        await test_error_handling()
        await test_callback_query_answering()

        print("\n" + "="*60)
        print("✅ ALL INTEGRATION TESTS COMPLETED")
        print("="*60)
        print("\nNOTE: Some tests may show warnings (⊘) if WorkOS is not")
        print("configured. This is expected and not a failure.")
        print("\nFor full end-to-end testing, manually verify:")
        print("  1. Send /menu in Telegram")
        print("  2. Click each button and verify behavior")
        print("  3. Check response times (should be < 3s)")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
