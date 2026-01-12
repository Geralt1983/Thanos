#!/usr/bin/env python3
"""
Index existing saved sessions into ChromaAdapter for semantic search.

This script scans the History/Sessions/ directory for JSON session files
(created by SessionManager) and indexes their messages into ChromaAdapter's
'conversations' collection for semantic search capabilities.

Usage:
    python scripts/index_sessions.py [--sessions-dir PATH] [--dry-run]

Arguments:
    --sessions-dir PATH  Path to sessions directory (default: History/Sessions/)
    --dry-run           Show what would be indexed without actually indexing

Requirements:
    - ChromaAdapter must be configured with valid OpenAI API key
    - Session files must be in JSON format (saved by SessionManager)
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Tuple

# Add Tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.adapters.chroma_adapter import ChromaAdapter
from Tools.session_manager import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_session_files(sessions_dir: Path) -> List[Path]:
    """
    Find all JSON session files in the sessions directory.

    Args:
        sessions_dir: Path to sessions directory

    Returns:
        List of paths to JSON session files
    """
    if not sessions_dir.exists():
        logger.warning(f"Sessions directory does not exist: {sessions_dir}")
        return []

    json_files = sorted(sessions_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON session files")
    return json_files


def load_session_from_file(json_path: Path) -> Tuple[str, List[dict]]:
    """
    Load session data from JSON file.

    Args:
        json_path: Path to JSON session file

    Returns:
        Tuple of (session_id, list of message dicts)

    Raises:
        ValueError: If file cannot be parsed or is missing required fields
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract session ID and messages
        session_id = data.get('id', '')
        history = data.get('history', [])
        agent = data.get('agent', 'unknown')

        if not session_id:
            raise ValueError("Session file missing 'id' field")

        if not history:
            logger.debug(f"Session {session_id} has no messages")
            return session_id, []

        # Prepare message data for indexing
        messages = []
        for msg in history:
            messages.append({
                'session_id': session_id,
                'role': msg.get('role', 'unknown'),
                'content': msg.get('content', ''),
                'timestamp': msg.get('timestamp', ''),
                'agent': agent
            })

        return session_id, messages

    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse session file {json_path}: {e}")


async def index_messages_batch(chroma: ChromaAdapter, messages: List[dict]) -> int:
    """
    Index a batch of messages to ChromaAdapter.

    Args:
        chroma: ChromaAdapter instance
        messages: List of message dicts with metadata

    Returns:
        Number of messages successfully indexed
    """
    if not messages:
        return 0

    try:
        # Prepare items for batch storage
        items = []
        for msg in messages:
            # Parse timestamp for date metadata
            from datetime import datetime
            try:
                timestamp = datetime.fromisoformat(msg['timestamp'])
                date_str = timestamp.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                date_str = "unknown"

            items.append({
                'text': msg['content'],
                'metadata': {
                    'session_id': msg['session_id'],
                    'timestamp': msg['timestamp'],
                    'role': msg['role'],
                    'agent': msg['agent'],
                    'date': date_str
                }
            })

        # Store batch to ChromaAdapter
        await chroma.store_batch('conversations', items)
        return len(items)

    except Exception as e:
        logger.error(f"Failed to index message batch: {e}")
        return 0


def main():
    """Main entry point for session indexing script."""
    parser = argparse.ArgumentParser(
        description='Index existing session files into ChromaAdapter for semantic search'
    )
    parser.add_argument(
        '--sessions-dir',
        type=Path,
        default=Path('History/Sessions'),
        help='Path to sessions directory (default: History/Sessions/)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be indexed without actually indexing'
    )

    args = parser.parse_args()

    # Initialize ChromaAdapter
    try:
        chroma = ChromaAdapter()
        logger.info("ChromaAdapter initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ChromaAdapter: {e}")
        logger.error("Make sure OPENAI_API_KEY is set in environment")
        return 1

    # Find session files
    session_files = find_session_files(args.sessions_dir)

    if not session_files:
        logger.info("No JSON session files found to index")
        logger.info("Note: Only JSON files created by SessionManager can be indexed")
        logger.info("Old markdown-only session summaries cannot be indexed (no message history)")
        return 0

    # Process each session file
    total_sessions = 0
    total_messages = 0
    failed_sessions = []

    for json_path in session_files:
        try:
            # Load session data
            session_id, messages = load_session_from_file(json_path)

            if not messages:
                logger.debug(f"Skipping empty session: {session_id}")
                continue

            # Index messages
            if args.dry_run:
                logger.info(f"[DRY RUN] Would index {len(messages)} messages from session {session_id}")
                indexed = len(messages)
            else:
                logger.info(f"Indexing {len(messages)} messages from session {session_id}...")
                indexed = asyncio.run(index_messages_batch(chroma, messages))

            if indexed > 0:
                total_sessions += 1
                total_messages += indexed
                logger.info(f"✓ Indexed {indexed} messages from {json_path.name}")
            else:
                logger.warning(f"✗ Failed to index {json_path.name}")
                failed_sessions.append(json_path.name)

        except ValueError as e:
            logger.error(f"✗ {e}")
            failed_sessions.append(json_path.name)
        except Exception as e:
            logger.error(f"✗ Unexpected error processing {json_path.name}: {e}")
            failed_sessions.append(json_path.name)

    # Print summary
    print("\n" + "="*60)
    print("INDEXING SUMMARY")
    print("="*60)
    print(f"Sessions processed: {total_sessions}/{len(session_files)}")
    print(f"Messages indexed: {total_messages}")
    if failed_sessions:
        print(f"Failed sessions: {len(failed_sessions)}")
        for name in failed_sessions[:5]:  # Show first 5
            print(f"  - {name}")
        if len(failed_sessions) > 5:
            print(f"  ... and {len(failed_sessions) - 5} more")
    print("="*60)

    return 0 if not failed_sessions else 1


if __name__ == '__main__':
    sys.exit(main())
