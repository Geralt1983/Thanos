#!/usr/bin/env python3
"""
Manual color testing script for CLI error message visibility
Tests that errors display in red, warnings in yellow, and success in green
"""

import sys
sys.path.insert(0, '.')

from Tools.command_router import Colors

def test_color_display():
    """Display test messages in different colors"""

    print("\n=== Manual Color Testing ===\n")

    # Test RED (errors)
    print(f"{Colors.RED}❌ Error: Unknown command '/invalid'{Colors.RESET}")
    print(f"{Colors.RED}❌ Error: Agent 'nonexistent' not found{Colors.RESET}")
    print(f"{Colors.RED}❌ Error: Session 'missing' not found{Colors.RESET}")
    print(f"{Colors.RED}❌ Error: Failed to store memory{Colors.RESET}")
    print(f"{Colors.RED}❌ Error: No commitments file found{Colors.RESET}")

    print("\n")

    # Test YELLOW (warnings)
    print(f"{Colors.YELLOW}⚠ Warning: Neo4j connection issue - using ChromaDB only{Colors.RESET}")
    print(f"{Colors.YELLOW}⚠ Warning: MemOS available but not initialized{Colors.RESET}")
    print(f"{Colors.YELLOW}💡 Tip: Use /remember <text> to store a memory{Colors.RESET}")
    print(f"{Colors.YELLOW}💡 Tip: Use /agent <name> to switch agents{Colors.RESET}")

    print("\n")

    # Test GREEN (success)
    print(f"{Colors.GREEN}✓ Switched to agent: ops{Colors.RESET}")
    print(f"{Colors.GREEN}✓ Conversation cleared{Colors.RESET}")
    print(f"{Colors.GREEN}✓ Session saved to: test_session{Colors.RESET}")
    print(f"{Colors.GREEN}✓ Session restored from: test_session{Colors.RESET}")
    print(f"{Colors.GREEN}✓ Memory stored: Test memory entry{Colors.RESET}")
    print(f"{Colors.GREEN}✓ Model switched to: sonnet{Colors.RESET}")

    print("\n")

    # Test color codes are correct
    print("=== Verifying Color Codes ===\n")
    print(f"RED code: {repr(Colors.RED)} (should be '\\033[31m')")
    print(f"YELLOW code: {repr(Colors.YELLOW)} (should be '\\033[33m')")
    print(f"GREEN code: {repr(Colors.GREEN)} (should be '\\033[32m')")
    print(f"RESET code: {repr(Colors.RESET)} (should be '\\033[0m')")

    print("\n=== Visual Verification ===")
    print("Please visually verify:")
    print("  - Errors appear in RED")
    print("  - Warnings appear in YELLOW")
    print("  - Success messages appear in GREEN")
    print("\n")

if __name__ == "__main__":
    test_color_display()
