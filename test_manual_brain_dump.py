#!/usr/bin/env python3
"""
Manual test script for brain dump processing command.

This script:
1. Creates test brain dump entries in the database
2. Runs pa:process with --dry-run to preview
3. Runs pa:process for real to process entries
4. Verifies the results
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from Tools.adapters.workos import WorkOSAdapter
from commands.pa import process


# Test brain dump entries with various types
TEST_ENTRIES = [
    {
        "content": "Need to schedule dentist appointment for next month",
        "expected": "task",
        "reason": "Clear actionable task"
    },
    {
        "content": "Just noticed the sunset looks beautiful today. The colors are amazing - deep orange fading into purple. Makes me think about how we rarely stop to appreciate moments like these.",
        "expected": "thought",
        "reason": "Observation/reflection, not actionable"
    },
    {
        "content": "What if we built a mobile app that helps people track their carbon footprint? Could integrate with smart home devices and transportation apps. Maybe add gamification with challenges.",
        "expected": "idea",
        "reason": "Creative concept for potential project"
    },
    {
        "content": "Really stressed about the presentation tomorrow. Not sure if I've prepared enough. What if they ask questions I can't answer?",
        "expected": "worry",
        "reason": "Anxiety/concern about future event"
    },
    {
        "content": "Write unit tests for the new authentication module",
        "expected": "task",
        "reason": "Specific, actionable work task"
    },
    {
        "content": "Maybe learn Spanish or Italian this year",
        "expected": "idea",
        "reason": "Vague aspiration, not concrete action"
    },
    {
        "content": "Update project README with new installation instructions and troubleshooting section",
        "expected": "task",
        "reason": "Clear documentation task"
    },
    {
        "content": "Coffee tastes better in the morning",
        "expected": "thought",
        "reason": "Random observation, no action needed"
    },
]


async def insert_test_entries():
    """Insert test brain dump entries into the database."""
    print("📝 Creating test brain dump entries...\n")

    adapter = WorkOSAdapter()
    try:
        pool = await adapter._get_pool()
        async with pool.acquire() as conn:
            # Insert each test entry
            for i, entry in enumerate(TEST_ENTRIES, 1):
                await conn.execute(
                    """
                    INSERT INTO brain_dump (content, processed)
                    VALUES ($1, 0)
                    """,
                    entry["content"]
                )
                print(f"  {i}. [{entry['expected'].upper()}] {entry['content'][:60]}...")
                print(f"     Reason: {entry['reason']}")

        print(f"\n✅ Created {len(TEST_ENTRIES)} test entries\n")
        print("=" * 70)

    finally:
        await adapter.close()


async def verify_results():
    """Verify the processing results in the database."""
    print("\n" + "=" * 70)
    print("🔍 Verifying Results in Database\n")

    adapter = WorkOSAdapter()
    try:
        pool = await adapter._get_pool()
        async with pool.acquire() as conn:
            # Get all processed entries from our test batch
            rows = await conn.fetch(
                """
                SELECT
                    bd.id,
                    bd.content,
                    bd.category,
                    bd.processed,
                    bd.processed_at,
                    bd.converted_to_task_id,
                    t.title as task_title,
                    t.category as task_category
                FROM brain_dump bd
                LEFT JOIN tasks t ON bd.converted_to_task_id = t.id
                WHERE bd.processed = 1
                ORDER BY bd.processed_at DESC
                LIMIT $1
                """,
                len(TEST_ENTRIES)
            )

            print(f"Found {len(rows)} processed entries:\n")

            tasks_created = 0
            archived = 0

            for row in rows:
                content_preview = row['content'][:60] + ('...' if len(row['content']) > 60 else '')
                category = row['category'] or 'unknown'

                print(f"  ID {row['id']}: [{category.upper()}]")
                print(f"    Content: {content_preview}")

                if row['converted_to_task_id']:
                    tasks_created += 1
                    print(f"    ✅ Converted to Task: {row['task_title']} (ID: {row['converted_to_task_id']})")
                    print(f"    Task Category: {row['task_category']}")
                else:
                    archived += 1
                    print(f"    📦 Archived (no task created)")

                print()

            print(f"📊 Summary:")
            print(f"   Total processed: {len(rows)}")
            print(f"   Tasks created: {tasks_created}")
            print(f"   Archived: {archived}")

            # Verify conservative task creation (should be ~3-4 tasks out of 8 entries)
            task_rate = tasks_created / len(rows) if rows else 0
            print(f"   Task creation rate: {task_rate:.1%}")

            if task_rate > 0.6:
                print(f"   ⚠️  Warning: Task creation rate seems high (expected ~40-50%)")
            elif task_rate < 0.2:
                print(f"   ⚠️  Warning: Task creation rate seems low (expected ~40-50%)")
            else:
                print(f"   ✅ Task creation rate looks reasonable (conservative approach)")

    finally:
        await adapter.close()


async def cleanup_test_entries():
    """Clean up test entries (optional)."""
    print("\n" + "=" * 70)
    response = input("\n🗑️  Clean up test entries? (y/N): ")

    if response.lower() != 'y':
        print("Keeping test entries for manual inspection.")
        return

    adapter = WorkOSAdapter()
    try:
        pool = await adapter._get_pool()
        async with pool.acquire() as conn:
            # Delete tasks created from test entries
            deleted_tasks = await conn.fetchval(
                """
                DELETE FROM tasks
                WHERE id IN (
                    SELECT converted_to_task_id
                    FROM brain_dump
                    WHERE converted_to_task_id IS NOT NULL
                    AND processed = 1
                    AND processed_at > NOW() - INTERVAL '1 hour'
                )
                RETURNING 1
                """
            )

            # Delete processed brain dump entries
            deleted_entries = await conn.fetchval(
                """
                DELETE FROM brain_dump
                WHERE processed = 1
                AND processed_at > NOW() - INTERVAL '1 hour'
                RETURNING 1
                """
            )

            print(f"✅ Cleaned up test data")
            if deleted_tasks:
                print(f"   - Deleted tasks")
            if deleted_entries:
                print(f"   - Deleted brain dump entries")

    finally:
        await adapter.close()


def main():
    """Run the manual test."""
    print("\n" + "=" * 70)
    print("🧪 Manual Test: Brain Dump Processing Command")
    print("=" * 70 + "\n")

    # Step 1: Insert test entries
    asyncio.run(insert_test_entries())

    # Step 2: Run with --dry-run first
    print("\n" + "=" * 70)
    print("STEP 1: Dry Run (Preview Mode)")
    print("=" * 70 + "\n")
    input("Press Enter to run with --dry-run...")
    print()

    result = process.execute("--dry-run --limit 10")

    # Step 3: Run for real
    print("\n" + "=" * 70)
    print("STEP 2: Real Processing")
    print("=" * 70 + "\n")
    response = input("Proceed with real processing? (y/N): ")

    if response.lower() != 'y':
        print("Skipping real processing. Test entries remain in database.")
        return

    print()
    result = process.execute("--limit 10")

    # Step 4: Verify results
    asyncio.run(verify_results())

    # Step 5: Optional cleanup
    asyncio.run(cleanup_test_entries())

    print("\n" + "=" * 70)
    print("✅ Manual test complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
