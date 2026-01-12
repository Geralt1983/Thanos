#!/usr/bin/env python3
"""
Test script for pa:export command
Bypasses module import issues by directly executing the command
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the export command
from commands.pa.export import execute

if __name__ == "__main__":
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    result = execute(args)
    print("\n" + "="*60)
    print("TEST RESULT")
    print("="*60)
    print(result)
