#!/usr/bin/env python3
"""
Test script for pa:export command invocation methods

Tests all different ways to invoke the export command:
1. Direct module: python -m commands.pa.export
2. Thanos run: thanos run pa:export
3. Thanos full: thanos pa:export
4. Thanos shortcut: thanos export
5. Error handling for invalid arguments

Note: Interactive mode (/run pa:export) requires manual testing
"""

import subprocess
import sys
from pathlib import Path
import json
import os

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(msg):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST: {msg}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

def print_pass(msg):
    print(f"{GREEN}✓ PASS:{RESET} {msg}")

def print_fail(msg):
    print(f"{RED}✗ FAIL:{RESET} {msg}")

def print_info(msg):
    print(f"{YELLOW}ℹ INFO:{RESET} {msg}")

def run_command(cmd, shell=False, timeout=30):
    """Run a command and return stdout, stderr, returncode"""
    try:
        if shell:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", -1
    except Exception as e:
        return "", str(e), -1

def test_direct_module():
    """Test: python -m commands.pa.export"""
    print_test("Direct Module Invocation: python -m commands.pa.export --help")

    stdout, stderr, returncode = run_command([
        sys.executable, "-m", "commands.pa.export", "--help"
    ])

    if returncode == 0 and "usage:" in stdout.lower():
        print_pass("Direct module invocation works")
        print_info(f"Help text displayed (first 200 chars):\n{stdout[:200]}")
        return True
    else:
        print_fail(f"Direct module invocation failed (rc={returncode})")
        if stderr:
            print_info(f"Error: {stderr[:200]}")
        return False

def test_direct_module_csv():
    """Test: python -m commands.pa.export --format csv --type tasks"""
    print_test("Direct Module with Args: --format csv --type tasks")

    # Clean up any existing test exports
    test_dir = Path("./test_invocation_exports")

    stdout, stderr, returncode = run_command([
        sys.executable, "-m", "commands.pa.export",
        "--format", "csv",
        "--type", "tasks",
        "--output", str(test_dir)
    ])

    # Check if command executed (may fail due to no database, but should show attempt)
    if "Connecting to WorkOS database" in stdout or "Error connecting" in stdout or "tasks" in stdout.lower():
        print_pass("Direct module with arguments executed")
        print_info(f"Output (first 300 chars):\n{stdout[:300]}")
        return True
    else:
        print_fail(f"Direct module with args failed (rc={returncode})")
        if stderr:
            print_info(f"Error: {stderr[:300]}")
        return False

def test_thanos_run():
    """Test: thanos run pa:export --help"""
    print_test("Thanos Run Command: thanos run pa:export --help")

    # Check if thanos.py is executable
    thanos_path = Path("./thanos.py")
    if not thanos_path.exists():
        print_fail("thanos.py not found")
        return False

    stdout, stderr, returncode = run_command([
        sys.executable, str(thanos_path), "run", "pa:export", "--help"
    ])

    if returncode == 0 or "usage:" in stdout.lower() or "export" in stdout.lower():
        print_pass("Thanos run command works")
        print_info(f"Output (first 200 chars):\n{stdout[:200]}")
        return True
    else:
        print_fail(f"Thanos run command failed (rc={returncode})")
        if stderr:
            print_info(f"Error: {stderr[:200]}")
        return False

def test_thanos_full():
    """Test: thanos pa:export --help"""
    print_test("Thanos Full Command: thanos pa:export --help")

    thanos_path = Path("./thanos.py")
    if not thanos_path.exists():
        print_fail("thanos.py not found")
        return False

    stdout, stderr, returncode = run_command([
        sys.executable, str(thanos_path), "pa:export", "--help"
    ])

    if returncode == 0 or "usage:" in stdout.lower() or "export" in stdout.lower():
        print_pass("Thanos full command works")
        print_info(f"Output (first 200 chars):\n{stdout[:200]}")
        return True
    else:
        print_fail(f"Thanos full command failed (rc={returncode})")
        if stderr:
            print_info(f"Error: {stderr[:200]}")
        return False

def test_thanos_shortcut():
    """Test: thanos export --help"""
    print_test("Thanos Shortcut: thanos export --help")

    thanos_path = Path("./thanos.py")
    if not thanos_path.exists():
        print_fail("thanos.py not found")
        return False

    stdout, stderr, returncode = run_command([
        sys.executable, str(thanos_path), "export", "--help"
    ])

    if returncode == 0 or "usage:" in stdout.lower() or "export" in stdout.lower():
        print_pass("Thanos shortcut works")
        print_info(f"Output (first 200 chars):\n{stdout[:200]}")
        return True
    else:
        print_fail(f"Thanos shortcut failed (rc={returncode})")
        if stderr:
            print_info(f"Error: {stderr[:200]}")
        return False

def test_invalid_format():
    """Test: Invalid --format argument"""
    print_test("Error Handling: Invalid --format argument")

    stdout, stderr, returncode = run_command([
        sys.executable, "-m", "commands.pa.export",
        "--format", "xml"
    ])

    combined_output = stdout + stderr
    if returncode != 0 and ("invalid" in combined_output.lower() or "error" in combined_output.lower()):
        print_pass("Invalid format argument produces clear error")
        print_info(f"Error message: {combined_output[:200]}")
        return True
    else:
        print_fail("Invalid format should produce error")
        return False

def test_invalid_type():
    """Test: Invalid --type argument"""
    print_test("Error Handling: Invalid --type argument")

    stdout, stderr, returncode = run_command([
        sys.executable, "-m", "commands.pa.export",
        "--type", "projects"
    ])

    combined_output = stdout + stderr
    if returncode != 0 and ("invalid" in combined_output.lower() or "error" in combined_output.lower()):
        print_pass("Invalid type argument produces clear error")
        print_info(f"Error message: {combined_output[:200]}")
        return True
    else:
        print_fail("Invalid type should produce error")
        return False

def test_help_flag():
    """Test: --help flag"""
    print_test("Help Flag: --help")

    stdout, stderr, returncode = run_command([
        sys.executable, "-m", "commands.pa.export", "--help"
    ])

    if returncode == 0 and "usage:" in stdout.lower():
        print_pass("--help flag works")
        # Verify key sections are present
        if "--format" in stdout and "--type" in stdout and "--output" in stdout:
            print_pass("Help text includes all parameter documentation")
        return True
    else:
        print_fail("--help flag failed")
        return False

def main():
    """Run all invocation tests"""
    print(f"\n{BLUE}{'='*70}")
    print("PA:EXPORT COMMAND INVOCATION TEST SUITE")
    print(f"{'='*70}{RESET}\n")

    print_info("Testing all different ways to invoke the pa:export command")
    print_info("Note: Some tests may fail due to missing database credentials")
    print_info("The goal is to verify command invocation, not data export\n")

    results = {}

    # Test 1: Direct module invocation
    results['direct_help'] = test_direct_module()

    # Test 2: Direct module with arguments
    results['direct_args'] = test_direct_module_csv()

    # Test 3: Thanos run command
    results['thanos_run'] = test_thanos_run()

    # Test 4: Thanos full command
    results['thanos_full'] = test_thanos_full()

    # Test 5: Thanos shortcut
    results['thanos_shortcut'] = test_thanos_shortcut()

    # Test 6: Invalid format argument
    results['invalid_format'] = test_invalid_format()

    # Test 7: Invalid type argument
    results['invalid_type'] = test_invalid_type()

    # Test 8: Help flag
    results['help_flag'] = test_help_flag()

    # Summary
    print(f"\n{BLUE}{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}{RESET}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{GREEN}✓ PASS{RESET}" if result else f"{RED}✗ FAIL{RESET}"
        print(f"{status} - {test_name}")

    print(f"\n{BLUE}Results: {passed}/{total} tests passed{RESET}")

    if passed == total:
        print(f"\n{GREEN}{'='*70}")
        print("ALL TESTS PASSED ✓")
        print(f"{'='*70}{RESET}\n")
    else:
        print(f"\n{YELLOW}{'='*70}")
        print(f"SOME TESTS FAILED ({total - passed} failures)")
        print(f"{'='*70}{RESET}\n")

    # Note about interactive mode
    print(f"\n{YELLOW}{'='*70}")
    print("MANUAL TESTING REQUIRED")
    print(f"{'='*70}{RESET}")
    print("\nInteractive mode must be tested manually:")
    print(f"  1. Run: {BLUE}python thanos.py interactive{RESET}")
    print(f"  2. Type: {BLUE}/run pa:export --help{RESET}")
    print(f"  3. Verify: Command executes and shows help text\n")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
