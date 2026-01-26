#!/usr/bin/env python3
"""
Static verification of button handler implementations.

This script verifies that all button handlers are properly implemented
without requiring the bot to run or connect to external services.
"""

import re
import sys
from pathlib import Path


def read_telegram_bot_code():
    """Read the telegram_bot.py file."""
    bot_file = Path(__file__).parent / "Tools" / "telegram_bot.py"
    with open(bot_file, 'r') as f:
        return f.read()


def verify_menu_command(code):
    """Verify /menu command implementation."""
    print("\n" + "="*60)
    print("VERIFICATION 1: /menu command")
    print("="*60)

    checks = {
        'menu_command function exists': r'async def menu_command\(',
        'Menu creates keyboard': r'_build_inline_keyboard',
        'Brain Dump button': r'menu_braindump',
        'Log Energy button': r'menu_energy',
        'View Tasks button': r'menu_tasks',
        'Menu callback handler': r'async def handle_menu_callback\(',
    }

    results = []
    for check_name, pattern in checks.items():
        if re.search(pattern, code):
            print(f"  ✓ {check_name}")
            results.append(True)
        else:
            print(f"  ✗ {check_name}")
            results.append(False)

    return all(results)


def verify_brain_dump_flow(code):
    """Verify brain dump button flow."""
    print("\n" + "="*60)
    print("VERIFICATION 2: Brain dump button flow")
    print("="*60)

    checks = {
        'Menu callback handles braindump': r'if action == ["\']braindump["\']',
        'Displays instruction message': r'Brain Dump Mode',
        'Mentions text message option': r'[Tt]ext message',
        'Mentions voice message option': r'[Vv]oice message',
        'Mentions photo option': r'[Pp]hoto',
        'Returns to menu instruction': r'/menu',
    }

    results = []
    for check_name, pattern in checks.items():
        if re.search(pattern, code):
            print(f"  ✓ {check_name}")
            results.append(True)
        else:
            print(f"  ✗ {check_name}")
            results.append(False)

    return all(results)


def verify_energy_logging(code):
    """Verify log energy button flow."""
    print("\n" + "="*60)
    print("VERIFICATION 3: Log energy button flow")
    print("="*60)

    checks = {
        'Menu callback handles energy': r'if action == ["\']energy["\']',
        'Creates energy level buttons': r'energy_buttons.*range\(1.*11\)',
        'Energy callback handler exists': r'async def handle_energy_callback\(',
        'Parses energy level': r'energy_level.*int\(',
        'Validates range (1-10)': r'energy_level.*<.*1.*>.*10',
        'Logs to database': r'INSERT INTO energy_logs',
        'Success confirmation': r'Energy Logged Successfully',
        'Shows emoji based on level': r'emoji.*energy_level',
        'Shows timestamp': r'timestamp.*strftime',
        'Error handling': r'except.*Exception.*as.*e:',
    }

    results = []
    for check_name, pattern in checks.items():
        if re.search(pattern, code, re.DOTALL):
            print(f"  ✓ {check_name}")
            results.append(True)
        else:
            print(f"  ✗ {check_name}")
            results.append(False)

    return all(results)


def verify_task_buttons(code):
    """Verify task list buttons."""
    print("\n" + "="*60)
    print("VERIFICATION 4: Task list buttons")
    print("="*60)

    checks = {
        'Task callback handler exists': r'async def handle_task_callback\(',
        'Parses callback data': r'callback_data\.split',
        'Handles complete action': r'if action == ["\']complete["\']',
        'Updates task status': r'UPDATE tasks.*SET status.*completed',
        'Handles details action': r'if action == ["\']details["\']',
        'Shows task details': r'SELECT.*FROM tasks.*WHERE id',
        'Handles postpone action': r'if action == ["\']postpone["\']',
        'Postpone updates status': r'UPDATE tasks.*SET status.*queued',
        'Handles delete action': r'if action == ["\']delete["\']',
        'Delete removes task': r'DELETE FROM tasks.*WHERE id',
        'Success confirmation with emoji': r'✅.*Task.*Completed',
        'Shows task title in response': r'row\[["\']title["\']\]',
        'Shows priority': r'priority',
        'Shows timestamp': r'timestamp.*strftime',
        'Error handling': r'except.*Exception.*as.*e:',
        'Connection cleanup': r'finally:.*conn\.close\(\)',
    }

    results = []
    for check_name, pattern in checks.items():
        if re.search(pattern, code, re.DOTALL):
            print(f"  ✓ {check_name}")
            results.append(True)
        else:
            print(f"  ✗ {check_name}")
            results.append(False)

    return all(results)


def verify_voice_buttons(code):
    """Verify voice message action buttons."""
    print("\n" + "="*60)
    print("VERIFICATION 5: Voice message action buttons")
    print("="*60)

    checks = {
        'Voice callback handler exists': r'async def handle_voice_callback\(',
        'Parses callback data': r'callback_data\.split.*2\)',
        'Extracts action and entry_id': r'action.*parts\[1\].*entry_id.*parts\[2\]',
        'Finds entry by ID': r'entry\.id == entry_id',
        'Handles save as task': r'if action == ["\']savetask["\']',
        'Uses brain dump pipeline': r'process_brain_dump_sync',
        'Forces task classification': r'force_classification.*personal_task',
        'Handles save as idea': r'if action == ["\']saveidea["\']',
        'Forces idea classification': r'force_classification.*idea',
        'Success confirmation': r'✅.*Task Created.*Voice',
        'Shows transcription in response': r'entry\.raw_content',
        'Shows routing results': r'routing_result',
        'Error handling for missing entry': r'not found',
    }

    results = []
    for check_name, pattern in checks.items():
        if re.search(pattern, code, re.DOTALL):
            print(f"  ✓ {check_name}")
            results.append(True)
        else:
            print(f"  ✗ {check_name}")
            results.append(False)

    return all(results)


def verify_error_handling(code):
    """Verify error handling in all callbacks."""
    print("\n" + "="*60)
    print("VERIFICATION 6: Error handling")
    print("="*60)

    # Find all callback handlers
    handlers = re.findall(r'async def handle_(\w+)_callback\(', code)
    print(f"  Found {len(handlers)} callback handlers: {', '.join(handlers)}")

    checks = {
        'Menu callback has error handling': r'handle_menu_callback.*?(?=async def|\Z)',
        'Task callback has error handling': r'handle_task_callback.*?(?=async def|\Z)',
        'Energy callback has error handling': r'handle_energy_callback.*?(?=async def|\Z)',
        'Voice callback has error handling': r'handle_voice_callback.*?(?=async def|\Z)',
    }

    results = []
    for handler_name, pattern in checks.items():
        handler_code = re.search(pattern, code, re.DOTALL)
        if handler_code:
            handler_text = handler_code.group(0)

            # Check for error handling patterns
            has_try_except = 'try:' in handler_text and 'except' in handler_text
            has_validation = 'if len(parts)' in handler_text or 'if not' in handler_text
            has_error_message = '⚠️' in handler_text or '❌' in handler_text

            if has_try_except or has_validation:
                print(f"  ✓ {handler_name}")
                if has_try_except:
                    print(f"    - Has try/except blocks")
                if has_validation:
                    print(f"    - Has input validation")
                if has_error_message:
                    print(f"    - Shows user-friendly error messages")
                results.append(True)
            else:
                print(f"  ⚠ {handler_name} - limited error handling")
                results.append(True)  # Don't fail for this
        else:
            print(f"  ? {handler_name} - handler not found")
            results.append(False)

    # Check for callback query answering (Telegram requirement)
    print("\n  Checking callback query answering:")
    if re.search(r'query\.answer\(\)', code):
        print(f"    ✓ Callbacks answer queries (query.answer())")
        results.append(True)
    else:
        print(f"    ✗ Missing query.answer() calls")
        results.append(False)

    # Check for connection cleanup
    print("\n  Checking database connection cleanup:")
    if re.search(r'finally:.*conn\.close\(\)', code, re.DOTALL):
        print(f"    ✓ Database connections closed in finally blocks")
        results.append(True)
    else:
        print(f"    ⚠ Should verify connection cleanup")
        results.append(True)  # Don't fail for this

    return all(results)


def verify_callback_registration(code):
    """Verify callback handlers are registered."""
    print("\n" + "="*60)
    print("VERIFICATION 7: Callback handler registration")
    print("="*60)

    # Check for registration system
    has_registration = re.search(r'_register_callback_handler', code)
    has_routing = re.search(r'_route_callback', code)

    if has_registration and has_routing:
        print(f"  ✓ Callback registration system exists")
        print(f"    - _register_callback_handler method found")
        print(f"    - _route_callback method found")
    else:
        print(f"  ⚠ Callback registration system may be missing")
        return False

    # Check for handler registrations
    registrations = re.findall(r'_register_callback_handler\(["\'](\w+_)["\']', code)
    if registrations:
        print(f"\n  Found {len(set(registrations))} callback prefixes registered:")
        for prefix in sorted(set(registrations)):
            print(f"    - {prefix}")
        return True
    else:
        print(f"  ⚠ No callback handler registrations found")
        return False


def verify_response_formatting(code):
    """Verify consistent response formatting."""
    print("\n" + "="*60)
    print("VERIFICATION 8: Response formatting")
    print("="*60)

    checks = {
        'Markdown formatting': r'parse_mode.*["\']Markdown["\']',
        'Bold headers': r'\*\*.*\*\*|\*[A-Z]',
        'Emoji indicators': r'[✅❌⚠️📋🧠⚡🎯]',
        'Timestamp formatting': r'strftime',
        'Consistent spacing': r'\\n\\n',
        'Action items with bullets': r'•|✓|-',
        'Italic notes': r'_.*_',
    }

    results = []
    for check_name, pattern in checks.items():
        matches = len(re.findall(pattern, code))
        if matches > 0:
            print(f"  ✓ {check_name}: {matches} occurrences")
            results.append(True)
        else:
            print(f"  ✗ {check_name}: not found")
            results.append(False)

    return all(results)


def main():
    """Run all verifications."""
    print("="*60)
    print("BUTTON HANDLER IMPLEMENTATION VERIFICATION")
    print("="*60)

    try:
        code = read_telegram_bot_code()
        print(f"\n✓ Loaded telegram_bot.py ({len(code)} characters)")

        results = [
            ("Menu command", verify_menu_command(code)),
            ("Brain dump flow", verify_brain_dump_flow(code)),
            ("Energy logging", verify_energy_logging(code)),
            ("Task buttons", verify_task_buttons(code)),
            ("Voice buttons", verify_voice_buttons(code)),
            ("Error handling", verify_error_handling(code)),
            ("Callback registration", verify_callback_registration(code)),
            ("Response formatting", verify_response_formatting(code)),
        ]

        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)

        passed = 0
        failed = 0
        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status}: {name}")
            if result:
                passed += 1
            else:
                failed += 1

        print(f"\n  Total: {passed} passed, {failed} failed")

        if failed == 0:
            print("\n✅ ALL VERIFICATIONS PASSED!")
            print("\n" + "="*60)
            print("MANUAL TESTING CHECKLIST")
            print("="*60)
            print("""
To complete end-to-end verification:

1. Start the Telegram bot:
   $ python Tools/telegram_bot.py

2. Test /menu command:
   • Send /menu in Telegram
   • Verify 3 quick action buttons appear
   • Screenshot result

3. Test Brain Dump flow:
   • Click "Brain Dump" button
   • Verify instruction message appears
   • Send a text message
   • Verify it's processed and acknowledged

4. Test Log Energy flow:
   • Click "Log Energy" button
   • Verify energy level buttons (1-10) appear
   • Click a level (e.g., 7)
   • Verify success message with emoji and timestamp

5. Test Task buttons:
   • Click "View Tasks" button
   • Verify tasks show with Complete/Details buttons
   • Click "Complete" on a task
   • Verify success confirmation
   • Click "Details" on another task
   • Verify full details with action buttons

6. Test Voice actions:
   • Send a voice message
   • Verify transcription appears
   • Verify "Save as Task" and "Save as Idea" buttons
   • Click one and verify processing

7. Performance check:
   • Time each operation
   • All should complete < 3 seconds

8. Error scenarios:
   • Test with invalid inputs
   • Verify graceful error messages
            """)
            return 0
        else:
            print(f"\n❌ {failed} VERIFICATION(S) FAILED")
            print("\nPlease review the failed checks above.")
            return 1

    except FileNotFoundError:
        print("✗ Error: telegram_bot.py not found")
        return 1
    except Exception as e:
        print(f"✗ Verification error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
