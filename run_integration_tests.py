#!/usr/bin/env python3
"""
Integration Test Runner for ChromaDB Batch Embedding

Runs integration tests with appropriate markers and provides clear output.

Usage:
    python3 run_integration_tests.py              # Run all integration tests (mocked OpenAI)
    python3 run_integration_tests.py --real-api   # Run with real OpenAI API
    python3 run_integration_tests.py --all        # Run all tests including slow ones
"""

import sys
import os
import subprocess
import argparse


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []

    try:
        import chromadb
    except ImportError:
        missing.append("chromadb")

    try:
        import pytest
    except ImportError:
        missing.append("pytest")

    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        return False

    return True


def check_openai_key():
    """Check if OpenAI API key is available."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set - tests requiring real API will be skipped")
        print("   Set it with: export OPENAI_API_KEY='sk-...'")
        return False
    return True


def run_tests(args):
    """Run integration tests with appropriate arguments."""
    cmd = ["python3", "-m", "pytest", "tests/integration/", "-v"]

    if args.real_api:
        # Run tests that require OpenAI API
        has_key = check_openai_key()
        if not has_key:
            print("\n❌ Cannot run real API tests without OPENAI_API_KEY")
            print("   Set it with: export OPENAI_API_KEY='sk-...'")
            return 1

        cmd.extend(["-m", "requires_openai"])
    elif not args.all:
        # Run only fast tests by default
        cmd.extend(["-m", "not slow"])

    # Add verbose output
    cmd.append("--tb=short")

    print(f"🚀 Running integration tests...")
    print(f"   Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run ChromaDB batch embedding integration tests"
    )
    parser.add_argument(
        "--real-api",
        action="store_true",
        help="Run tests with real OpenAI API (requires OPENAI_API_KEY)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests including slow ones"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("ChromaDB Batch Embedding Integration Tests")
    print("=" * 70)

    # Check dependencies
    if not check_dependencies():
        return 1

    # Run tests
    return_code = run_tests(args)

    print("\n" + "=" * 70)
    if return_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 70)

    return return_code


if __name__ == "__main__":
    sys.exit(main())
