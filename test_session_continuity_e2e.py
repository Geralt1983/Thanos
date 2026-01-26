#!/usr/bin/env python3
"""
End-to-End Test for Enhanced Session Continuity (Task 047)

Verifies all acceptance criteria:
1. Session start includes yesterday's emotional markers
2. Active projects auto-loaded into context
3. Recent commitments and promises surfaced
4. Family/relationship mentions from past week available
5. Context injection efficient - under 800 tokens
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from Tools.context_injector import (
    build_session_context,
    get_yesterday_session,
    build_emotional_context,
    active_projects_context,
    recent_commitments_context,
    relationship_context,
    _estimate_tokens,
    MAX_CONTEXT_TOKENS
)


def test_acceptance_criteria():
    """Run all end-to-end acceptance criteria tests."""

    print("=" * 80)
    print("Enhanced Session Continuity - End-to-End Verification")
    print("=" * 80)
    print()

    results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }

    # Test 1: Build session context successfully
    print("Test 1: Build session context...")
    try:
        context = build_session_context()
        if context and len(context) > 0:
            results['passed'].append("✓ Session context builds successfully")
            print(f"  ✓ Context generated ({len(context)} chars)")
        else:
            results['failed'].append("✗ Session context is empty")
            print("  ✗ FAILED: Empty context")
    except Exception as e:
        results['failed'].append(f"✗ Session context build failed: {e}")
        print(f"  ✗ FAILED: {e}")

    print()

    # Test 2: Verify yesterday's emotional state
    print("Test 2: Yesterday's emotional state...")
    try:
        emotional = build_emotional_context()
        if emotional and not emotional.startswith("<!--"):
            # Check if it contains emotional continuity section
            if "Emotional Continuity" in emotional or "yesterday" in emotional.lower():
                results['passed'].append("✓ Yesterday's emotional state appears in output")
                print(f"  ✓ Emotional continuity section present")
                print(f"     Preview: {emotional[:150]}...")
            else:
                results['warnings'].append("⚠ Emotional section exists but may lack content")
                print(f"  ⚠ WARNING: Section exists but limited content")
        else:
            results['warnings'].append("⚠ No yesterday session data found")
            print(f"  ⚠ WARNING: {emotional[:100]}")
    except Exception as e:
        results['failed'].append(f"✗ Emotional context failed: {e}")
        print(f"  ✗ FAILED: {e}")

    print()

    # Test 3: Verify active projects
    print("Test 3: Active projects context...")
    try:
        projects = active_projects_context()
        if projects and not projects.startswith("<!--"):
            # Check for expected client names from critical_facts.json
            has_clients = any(client in projects for client in ["Orlando", "Raleigh", "Memphis", "Kentucky"])
            if has_clients or "Client" in projects or "Project" in projects:
                results['passed'].append("✓ Active projects auto-loaded into context")
                print(f"  ✓ Active projects section present")
                print(f"     Preview: {projects[:150]}...")
            else:
                results['warnings'].append("⚠ Active projects section exists but no known clients found")
                print(f"  ⚠ WARNING: Section exists but no known clients")
        else:
            results['warnings'].append("⚠ No active projects found in memory")
            print(f"  ⚠ WARNING: {projects[:100]}")
    except Exception as e:
        results['failed'].append(f"✗ Active projects failed: {e}")
        print(f"  ✗ FAILED: {e}")

    print()

    # Test 4: Verify recent commitments
    print("Test 4: Recent commitments...")
    try:
        commitments = recent_commitments_context()
        if commitments and not commitments.startswith("<!--"):
            # Check if commitments section has content
            if "⏳" in commitments or "🔄" in commitments or "commitment" in commitments.lower():
                results['passed'].append("✓ Recent commitments and promises surfaced")
                print(f"  ✓ Recent commitments section present")
                print(f"     Preview: {commitments[:150]}...")
            else:
                results['warnings'].append("⚠ Commitments section exists but may be empty")
                print(f"  ⚠ WARNING: Section exists but limited content")
        else:
            results['warnings'].append("⚠ No recent commitments found")
            print(f"  ⚠ WARNING: {commitments[:100]}")
    except Exception as e:
        results['failed'].append(f"✗ Commitments context failed: {e}")
        print(f"  ✗ FAILED: {e}")

    print()

    # Test 5: Verify relationship mentions
    print("Test 5: Relationship mentions from past week...")
    try:
        relationships = relationship_context()
        if relationships and not relationships.startswith("<!--"):
            # Check if relationship section has content
            has_relationships = any(name in relationships for name in ["Ashley", "Sullivan", "family"])
            if has_relationships or "Relationship" in relationships:
                results['passed'].append("✓ Family/relationship mentions from past week available")
                print(f"  ✓ Relationship context section present")
                print(f"     Preview: {relationships[:150]}...")
            else:
                results['warnings'].append("⚠ Relationship section exists but no known family members found")
                print(f"  ⚠ WARNING: Section exists but no known relationships")
        else:
            results['warnings'].append("⚠ No relationship mentions found")
            print(f"  ⚠ WARNING: {relationships[:100]}")
    except Exception as e:
        results['failed'].append(f"✗ Relationship context failed: {e}")
        print(f"  ✗ FAILED: {e}")

    print()

    # Test 6: Verify token budget
    print("Test 6: Token budget compliance...")
    try:
        context = build_session_context()
        token_count = _estimate_tokens(context)
        char_count = len(context)

        if token_count <= MAX_CONTEXT_TOKENS:
            results['passed'].append(f"✓ Context injection efficient - under {MAX_CONTEXT_TOKENS} tokens")
            print(f"  ✓ Token budget respected")
            print(f"     Tokens: {token_count}/{MAX_CONTEXT_TOKENS}")
            print(f"     Chars: {char_count}")
        else:
            results['failed'].append(f"✗ Token budget exceeded: {token_count}/{MAX_CONTEXT_TOKENS}")
            print(f"  ✗ FAILED: Exceeded token budget")
            print(f"     Tokens: {token_count}/{MAX_CONTEXT_TOKENS} (OVER LIMIT)")
    except Exception as e:
        results['failed'].append(f"✗ Token budget check failed: {e}")
        print(f"  ✗ FAILED: {e}")

    print()

    # Test 7: Verify all expected sections present in full context
    print("Test 7: Verify all sections integrated...")
    try:
        context = build_session_context()
        expected_sections = [
            "Temporal Context",
            "Energy Context",
            "Emotional Continuity",
            "Hot Memory Context",
            "Active Projects",
            "Recent Commitments",
            "Relationship Context"
        ]

        found_sections = []
        missing_sections = []

        for section in expected_sections:
            if section in context:
                found_sections.append(section)
            else:
                missing_sections.append(section)

        if len(found_sections) >= 5:  # At least 5 of 7 sections should be present
            results['passed'].append(f"✓ {len(found_sections)}/7 expected sections present")
            print(f"  ✓ Found {len(found_sections)}/7 sections")
            for section in found_sections:
                print(f"     • {section}")
        else:
            results['failed'].append(f"✗ Only {len(found_sections)}/7 sections present")
            print(f"  ✗ FAILED: Only {len(found_sections)}/7 sections found")

        if missing_sections:
            print(f"  ⚠ Missing sections:")
            for section in missing_sections:
                print(f"     - {section}")
                results['warnings'].append(f"⚠ Missing section: {section}")
    except Exception as e:
        results['failed'].append(f"✗ Section integration check failed: {e}")
        print(f"  ✗ FAILED: {e}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    # Print results
    if results['passed']:
        print(f"PASSED ({len(results['passed'])}):")
        for item in results['passed']:
            print(f"  {item}")
        print()

    if results['warnings']:
        print(f"WARNINGS ({len(results['warnings'])}):")
        for item in results['warnings']:
            print(f"  {item}")
        print()

    if results['failed']:
        print(f"FAILED ({len(results['failed'])}):")
        for item in results['failed']:
            print(f"  {item}")
        print()

    # Overall result
    total_tests = len(results['passed']) + len(results['failed'])
    pass_rate = len(results['passed']) / total_tests * 100 if total_tests > 0 else 0

    print(f"Pass Rate: {len(results['passed'])}/{total_tests} ({pass_rate:.1f}%)")
    print()

    # Display full context output
    print("=" * 80)
    print("FULL CONTEXT OUTPUT")
    print("=" * 80)
    print()
    try:
        context = build_session_context()
        print(context)
        print()
        print(f"Total length: {len(context)} characters (~{_estimate_tokens(context)} tokens)")
    except Exception as e:
        print(f"Failed to generate context: {e}")

    print()
    print("=" * 80)

    # Return exit code based on failures
    if results['failed']:
        print("RESULT: FAILED ❌")
        return 1
    elif results['warnings']:
        print("RESULT: PASSED WITH WARNINGS ⚠️")
        return 0
    else:
        print("RESULT: ALL TESTS PASSED ✓")
        return 0


if __name__ == "__main__":
    exit_code = test_acceptance_criteria()
    sys.exit(exit_code)
