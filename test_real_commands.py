#!/usr/bin/env python3
"""
Real command scenario testing for color verification
Simulates actual command outputs to verify colors
"""

import sys
sys.path.insert(0, '.')

from Tools.command_router import Colors

def test_real_scenarios():
    """Test real command scenarios with proper colors"""

    print("\n" + "=" * 70)
    print("MANUAL COLOR VERIFICATION TEST")
    print("=" * 70 + "\n")

    print("Testing error messages (should be RED):")
    print("-" * 70)
    print(f"{Colors.RED}Unknown command: /invalid. Type /help for available commands.{Colors.RESET}")
    print(f"{Colors.RED}Unknown agent: nonexistent{Colors.RESET}")
    print(f"{Colors.RED}Session not found: missing_session{Colors.RESET}")
    print(f"{Colors.RED}Branch not found: feature/nonexistent{Colors.RESET}")
    print(f"{Colors.RED}MemOS not available. Check Neo4j/ChromaDB configuration.{Colors.RESET}")
    print(f"{Colors.RED}Failed to store memory: Connection timeout{Colors.RESET}")
    print(f"{Colors.RED}No commitments file found.{Colors.RESET}")
    print(f"{Colors.RED}Error reading commitments: File not readable{Colors.RESET}")
    print(f"{Colors.RED}Unknown model: invalid-model{Colors.RESET}")
    print(f"{Colors.RED}Calendar integration not available.{Colors.RESET}")

    print("\n")
    print("Testing warning messages (should be YELLOW):")
    print("-" * 70)
    print(f"    {Colors.YELLOW}⚠ Neo4j connection issue{Colors.RESET}")
    print(f"    {Colors.YELLOW}⚠ MemOS available but not initialized{Colors.RESET}")
    print(f"    {Colors.YELLOW}💡 MemOS will initialize on first /remember or /recall{Colors.RESET}")
    print(f"    {Colors.YELLOW}💡 Install neo4j and chromadb packages{Colors.RESET}")
    print(f"{Colors.YELLOW}Tip: Use \"\"\" for multi-line input{Colors.RESET}")
    print(f"{Colors.YELLOW}Tip: For intelligent scheduling, ask the agent in natural language:{Colors.RESET}")

    print("\n")
    print("Testing success messages (should be GREEN):")
    print("-" * 70)
    print(f"{Colors.GREEN}Switched to ops (Operations Manager){Colors.RESET}")
    print(f"{Colors.GREEN}Conversation cleared.{Colors.RESET}")
    print(f"{Colors.GREEN}Session saved: ~/.thanos/sessions/my_session.json{Colors.RESET}")
    print(f"{Colors.GREEN}Session restored:{Colors.RESET}")
    print(f"{Colors.GREEN}Memory stored:{Colors.RESET}")
    print(f"{Colors.GREEN}Branch created:{Colors.RESET}")
    print(f"{Colors.GREEN}Continue conversation on this branch. Use /branches to switch back to main.{Colors.RESET}")
    print(f"{Colors.GREEN}Switched to branch:{Colors.RESET}")
    print(f"{Colors.GREEN}Model switched:{Colors.RESET} opus → sonnet")
    print(f"{Colors.GREEN}Using: anthropic/claude-sonnet-4-5{Colors.RESET}")

    print("\n" + "=" * 70)
    print("VERIFICATION CHECKLIST")
    print("=" * 70)
    print("\nPlease verify the following:")
    print("  ✓ All error messages are displayed in RED")
    print("  ✓ All warning messages (⚠, 💡, Tip:) are displayed in YELLOW")
    print("  ✓ All success messages (confirmations) are displayed in GREEN")
    print("  ✓ Text returns to normal color after each message (RESET)")
    print("\nColor codes used:")
    print(f"  RED:    {repr(Colors.RED)}")
    print(f"  YELLOW: {repr(Colors.YELLOW)}")
    print(f"  GREEN:  {repr(Colors.GREEN)}")
    print(f"  RESET:  {repr(Colors.RESET)}")
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    test_real_scenarios()
