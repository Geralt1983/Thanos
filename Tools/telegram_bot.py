#!/usr/bin/env python3
"""
Thanos Telegram Brain Dump Bot.

Mobile-first capture interface for quick thoughts, tasks, and ideas.
Supports voice messages with Whisper transcription.
"""

import os
import re
import json
import asyncio
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.journal import Journal, EventType, Severity

# Import new unified pipeline
from Tools.brain_dump.pipeline import process_brain_dump_sync
from Tools.state_store import get_db

# Import Memory V2 service for vector storage (unified pgvector backend)
# NOTE: ChromaDB has been deprecated in favor of Memory V2 (Neon pgvector)
try:
    from Tools.memory_v2.service import MemoryService
    MEMORY_V2_AVAILABLE = True
except ImportError:
    MemoryService = None
    MEMORY_V2_AVAILABLE = False

# Database URL for WorkOS sync
WORKOS_DATABASE_URL = os.getenv('WORKOS_DATABASE_URL')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('telegram_bot')


@dataclass
class BrainDumpEntry:
    """A captured brain dump entry."""
    id: str
    timestamp: str
    raw_content: str
    content_type: str  # 'text', 'voice', 'photo'
    # New classification system fields
    classification: Optional[str] = None  # thinking, observation, idea, personal_task, work_task, worry
    confidence: float = 0.0
    acknowledgment: Optional[str] = None  # User-friendly response
    # Legacy fields for backwards compatibility
    parsed_category: Optional[str] = None  # mapped from classification
    parsed_context: Optional[str] = None  # 'work', 'personal' - derived from classification
    parsed_priority: Optional[str] = None  # 'low', 'medium', 'high', 'critical'
    parsed_entities: Optional[List[str]] = None  # extracted people, projects, etc.
    parsed_action: Optional[str] = None  # extracted action item
    source: str = 'telegram'
    user_id: Optional[str] = None
    processed: bool = False
    processing_notes: Optional[str] = None
    # Review status (from pipeline)
    needs_review: bool = False
    review_reason: Optional[str] = None
    # Routing results
    routing_result: Optional[Dict[str, Any]] = None


class TelegramBrainDumpBot:
    """
    Telegram bot for brain dump capture.

    Features:
    - Text message capture
    - Voice message transcription via Whisper
    - Photo/image capture with optional OCR
    - AI parsing to extract tasks, commitments, ideas
    - Direct integration with WorkOS brain dump
    - Journal logging for all captures
    - Content quality filtering (noise, incomplete transcriptions)
    - Natural language command support (task queries, habit checks)
    """

    # Content filtering thresholds
    MIN_WORD_COUNT = 3  # Minimum words for valid content
    MIN_CHAR_COUNT = 10  # Minimum characters
    MAX_NON_ASCII_RATIO = 0.5  # Max ratio of non-ASCII chars (filters TV audio in other languages)

    # Command patterns for natural language queries
    COMMAND_PATTERNS = {
        'tasks_today': [
            r'\b(what|show|list|get)\b.*(task|todo|to-do|to do)',
            r'\bwhat.*(do i have|on my plate|should i do)',
            r'\btask.*today',
            r'\btoday.*task',
            r'\bmy task',
        ],
        'tasks_all': [
            r'\ball.*task',
            r'\bbacklog',
            r'\bqueued',
        ],
        'habits': [
            r'\b(habit|routine)',
            r'\bwhat.*(habit|routine)',
        ],
        'brain_dumps': [
            r'\bbrain.?dump',
            r'\bunprocessed',
            r'\bpending.*(thought|idea|dump)',
        ],
        'status': [
            r'\bstatus\b',
            r'\bhow.*doing',
            r'\bmy progress',
        ],
        'health': [
            r'\b(health|oura|readiness|sleep score|energy level)',
            r'\bhow.*(sleep|rested|energy)',
            r'\bmy (readiness|hrv|heart rate)',
            r'\bcheck.*oura',
        ],
    }

    def __init__(
        self,
        token: Optional[str] = None,
        allowed_users: Optional[List[int]] = None,
        whisper_api_key: Optional[str] = None,
        claude_api_key: Optional[str] = None
    ):
        """
        Initialize the brain dump bot.

        Args:
            token: Telegram bot token. Defaults to TELEGRAM_BOT_TOKEN env var.
            allowed_users: List of allowed Telegram user IDs. Defaults to TELEGRAM_ALLOWED_USERS.
            whisper_api_key: OpenAI API key for Whisper. Defaults to OPENAI_API_KEY.
            claude_api_key: Anthropic API key for parsing. Defaults to ANTHROPIC_API_KEY.
        """
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.whisper_api_key = whisper_api_key or os.getenv('OPENAI_API_KEY')
        self.claude_api_key = claude_api_key or os.getenv('ANTHROPIC_API_KEY')

        # Parse allowed users
        allowed_users_str = os.getenv('TELEGRAM_ALLOWED_USERS', '')
        self.allowed_users = allowed_users or [
            int(uid.strip()) for uid in allowed_users_str.split(',') if uid.strip()
        ]

        # Initialize journal
        self.journal = Journal()

        # Initialize state store for pipeline
        self.state_store = get_db()

        # Initialize Memory V2 service for vector storage (Neon pgvector)
        # This is the primary vector storage for brain dumps, ideas, and memories
        self.memory_service = None
        if MEMORY_V2_AVAILABLE:
            try:
                self.memory_service = MemoryService()
                logger.info("Memory V2 service initialized for brain dump storage")
            except Exception as e:
                logger.warning(f"Memory V2 not available: {e}")

        # Storage for entries (legacy - now also stored in state_store)
        self.entries: List[BrainDumpEntry] = []
        self.storage_path = Path(__file__).parent.parent / "State" / "brain_dumps.json"

        # Load existing entries
        self._load_entries()

        # Track bot state
        self.is_running = False
        self.application = None

        # WorkOS sync enabled if database URL is configured
        self.workos_enabled = bool(WORKOS_DATABASE_URL)
        if self.workos_enabled:
            logger.info("WorkOS sync enabled for work tasks only")

    def should_filter_content(self, content: str) -> tuple[bool, str]:
        """
        Check if content should be filtered out (noise, incomplete, gibberish).

        Returns:
            Tuple of (should_filter, reason)
        """
        import re

        if not content or not content.strip():
            return True, "empty"

        content = content.strip()

        # Check minimum length
        words = content.split()
        if len(words) < self.MIN_WORD_COUNT:
            return True, f"too_short ({len(words)} words)"

        if len(content) < self.MIN_CHAR_COUNT:
            return True, f"too_short ({len(content)} chars)"

        # Check for high non-ASCII ratio (TV/radio in other languages)
        non_ascii = sum(1 for c in content if ord(c) > 127)
        if len(content) > 0 and non_ascii / len(content) > self.MAX_NON_ASCII_RATIO:
            return True, f"likely_noise (non-ASCII ratio: {non_ascii/len(content):.0%})"

        # Check for common filler patterns (incomplete thoughts)
        filler_patterns = [
            r'^(um+|uh+|hmm+|so+|you know|like|well|okay|alright)[.,\s]*$',
            r'^(um+|uh+|so+|you know)[,\s]+(it\'?s?|that|the)[,\s]*$',
        ]
        for pattern in filler_patterns:
            if re.match(pattern, content, re.IGNORECASE):
                return True, "filler_only"

        # Check for very fragmented content (likely cut-off transcription)
        # Words that suggest an incomplete thought
        incomplete_endings = (
            'a', 'an', 'the', 'to', 'and', 'or', 'but', 'it', 'is', "it's",
            'that', 'this', 'very', 'really', 'quite', 'so', 'just', 'about',
            'for', 'with', 'at', 'in', 'on', 'of', 'my', 'your', 'their',
            'some', 'any', 'no', 'not', 'be', 'been', 'being', 'was', 'were'
        )
        last_word = words[-1].lower().rstrip('.,!?')
        if last_word in incomplete_endings:
            if len(words) < 6:
                return True, "incomplete_sentence"

        # Check for sentences that look cut off (no terminal punctuation, short)
        if not content.rstrip().endswith(('.', '!', '?', ')', '"', "'")):
            # Short sentence without punctuation - might be cut off
            if len(words) <= 5 and len(words) >= self.MIN_WORD_COUNT:
                # Check if it looks like a trailing adjective (incomplete predicate)
                common_trailing_adjectives = (
                    'tough', 'hard', 'good', 'bad', 'great', 'nice', 'big', 'small',
                    'new', 'old', 'long', 'short', 'high', 'low', 'fast', 'slow',
                    'important', 'interesting', 'different', 'similar', 'better', 'worse'
                )
                if last_word in common_trailing_adjectives:
                    return True, "incomplete_sentence"

        return False, ""

    def detect_command(self, content: str) -> tuple[Optional[str], Optional[dict]]:
        """
        Detect if content is a command/query rather than a brain dump.

        Returns:
            Tuple of (command_type, params) or (None, None) if not a command
        """
        import re

        content_lower = content.lower().strip()

        # Check each command pattern
        for command_type, patterns in self.COMMAND_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    # Extract any params (e.g., "today", "this week")
                    params = {}
                    if 'today' in content_lower:
                        params['timeframe'] = 'today'
                    elif 'week' in content_lower:
                        params['timeframe'] = 'week'
                    elif 'all' in content_lower:
                        params['timeframe'] = 'all'

                    logger.info(f"Detected command: {command_type} with params {params}")
                    return command_type, params

        return None, None

    async def handle_command(self, command_type: str, params: dict) -> str:
        """
        Handle a detected command by querying WorkOS.

        Returns:
            Response message to send to user
        """
        try:
            if command_type == 'tasks_today':
                return await self._get_tasks_response('active')
            elif command_type == 'tasks_all':
                return await self._get_tasks_response('backlog')
            elif command_type == 'habits':
                return await self._get_habits_response()
            elif command_type == 'brain_dumps':
                return self._get_brain_dumps_response()
            elif command_type == 'status':
                return await self._get_status_response()
            elif command_type == 'health':
                return await self._get_health_response()
            else:
                return "I didn't understand that command. Try asking about tasks, habits, health, or status."
        except Exception as e:
            logger.error(f"Command handling failed: {e}")
            return f"Sorry, I couldn't fetch that information: {e}"

    async def _get_tasks_response(self, status: str = 'active') -> str:
        """Fetch tasks from WorkOS and format response."""
        if not self.workos_enabled:
            return "WorkOS not configured - can't fetch tasks."

        try:
            import asyncpg
            import ssl

            db_url = WORKOS_DATABASE_URL.split('?')[0]
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            conn = await asyncpg.connect(db_url, ssl=ssl_context)
            try:
                if status == 'active':
                    # Get both work and personal active/queued tasks
                    rows = await conn.fetch(
                        """
                        SELECT id, title, status, category, value_tier
                        FROM tasks
                        WHERE status IN ('active', 'queued')
                        ORDER BY category, status, created_at DESC
                        LIMIT 15
                        """
                    )
                    header = "📋 *Today's Tasks*"
                else:
                    rows = await conn.fetch(
                        """
                        SELECT id, title, status, category, value_tier
                        FROM tasks
                        WHERE status = 'backlog'
                        ORDER BY category, created_at DESC
                        LIMIT 15
                        """
                    )
                    header = "📋 *Backlog*"

                if not rows:
                    return f"{header}\n\nNo tasks found! 🎉"

                # Group by category for cleaner display
                work_tasks = [r for r in rows if r['category'] == 'work']
                personal_tasks = [r for r in rows if r['category'] != 'work']

                lines = [header, ""]

                if work_tasks:
                    lines.append("💼 *Work*")
                    for row in work_tasks[:7]:
                        status_emoji = {'active': '🔥', 'queued': '⏳'}.get(row['status'], '📝')
                        lines.append(f"  {status_emoji} {row['title'][:45]}")
                    lines.append("")

                if personal_tasks:
                    lines.append("🏠 *Personal*")
                    for row in personal_tasks[:7]:
                        status_emoji = {'active': '🔥', 'queued': '⏳'}.get(row['status'], '📝')
                        lines.append(f"  {status_emoji} {row['title'][:45]}")

                if not work_tasks and not personal_tasks:
                    lines.append("No tasks found! 🎉")

                return "\n".join(lines)
            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"Failed to fetch tasks: {e}")
            return f"Couldn't fetch tasks: {e}"

    async def _get_habits_response(self) -> str:
        """Fetch habits from WorkOS and format response."""
        if not self.workos_enabled:
            return "WorkOS not configured - can't fetch habits."

        try:
            import asyncpg
            import ssl

            db_url = WORKOS_DATABASE_URL.split('?')[0]
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            conn = await asyncpg.connect(db_url, ssl=ssl_context)
            try:
                rows = await conn.fetch(
                    """
                    SELECT id, name, emoji, current_streak, frequency, time_of_day
                    FROM habits
                    WHERE active = true
                    ORDER BY time_of_day, name
                    LIMIT 15
                    """
                )

                if not rows:
                    return "🎯 *Habits*\n\nNo active habits found."

                lines = ["🎯 *Your Habits*", ""]
                for row in rows:
                    emoji = row['emoji'] or '✨'
                    streak = f"🔥{row['current_streak']}" if row['current_streak'] > 0 else ""
                    time_badge = {'morning': '🌅', 'evening': '🌙', 'anytime': '⏰'}.get(row['time_of_day'], '')
                    lines.append(f"{emoji} {row['name']} {streak} {time_badge}")

                return "\n".join(lines)
            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"Failed to fetch habits: {e}")
            return f"Couldn't fetch habits: {e}"

    def _get_brain_dumps_response(self) -> str:
        """Get pending brain dumps from local storage."""
        unprocessed = self.get_unprocessed()
        if not unprocessed:
            return "🧠 *Brain Dumps*\n\nAll caught up! No pending items."

        lines = [f"🧠 *{len(unprocessed)} Pending Brain Dumps*", ""]
        for entry in unprocessed[:10]:
            emoji = {
                'task': '✅', 'idea': '💡', 'thought': '💭',
                'commitment': '🤝', 'personal_task': '🏠', 'work_task': '💼'
            }.get(entry.classification or entry.parsed_category, '📝')
            preview = entry.raw_content[:40] + '...' if len(entry.raw_content) > 40 else entry.raw_content
            lines.append(f"{emoji} {preview}")

        if len(unprocessed) > 10:
            lines.append(f"\n_...and {len(unprocessed) - 10} more_")

        return "\n".join(lines)

    async def _get_status_response(self) -> str:
        """Get overall status summary."""
        lines = ["📊 *Quick Status*", ""]

        # Local brain dumps
        unprocessed = self.get_unprocessed()
        lines.append(f"🧠 Brain dumps: {len(unprocessed)} pending")

        # WorkOS data if available
        if self.workos_enabled:
            try:
                import asyncpg
                import ssl

                db_url = WORKOS_DATABASE_URL.split('?')[0]
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                conn = await asyncpg.connect(db_url, ssl=ssl_context)
                try:
                    # Count active tasks
                    active_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM tasks WHERE status = 'active'"
                    )
                    lines.append(f"✅ Active tasks: {active_count}")

                    # Today's points
                    today_points = await conn.fetchval(
                        """
                        SELECT COALESCE(SUM(points_earned), 0)
                        FROM task_completions
                        WHERE DATE(completed_at) = CURRENT_DATE
                        """
                    )
                    lines.append(f"⭐ Today's points: {today_points or 0}")

                finally:
                    await conn.close()
            except Exception as e:
                logger.warning(f"Couldn't fetch WorkOS stats: {e}")

        return "\n".join(lines)

    async def _get_health_response(self) -> str:
        """Get health status from Oura Ring cache."""
        import sqlite3

        oura_cache_dir = os.getenv('OURA_CACHE_DIR', os.path.join(os.path.expanduser('~'), '.oura-cache'))
        oura_db_path = os.path.join(oura_cache_dir, 'oura-health.db')

        if not os.path.exists(oura_db_path):
            return "💪 *Health Status*\n\nOura data not available. Make sure oura-mcp has synced."

        try:
            conn = sqlite3.connect(oura_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            today = datetime.now().strftime('%Y-%m-%d')

            # Fetch readiness
            cursor.execute('SELECT data FROM readiness_data WHERE day = ?', (today,))
            readiness_row = cursor.fetchone()

            # Fetch sleep
            cursor.execute('SELECT data FROM sleep_data WHERE day = ?', (today,))
            sleep_row = cursor.fetchone()

            conn.close()

            if not readiness_row and not sleep_row:
                return "💪 *Health Status*\n\nNo data for today yet. Check back later."

            lines = ["💪 *Health Status*", ""]

            # Parse readiness
            if readiness_row:
                import json
                readiness = json.loads(readiness_row['data'])
                score = readiness.get('score')
                contributors = readiness.get('contributors', {})

                # Determine energy level
                if score is not None:
                    if score >= 85:
                        energy = "🟢 HIGH"
                        rec = "Great day for deep work!"
                    elif score >= 70:
                        energy = "🟡 MEDIUM"
                        rec = "Good for standard tasks"
                    else:
                        energy = "🔴 LOW"
                        rec = "Take it easy, more breaks"
                    lines.append(f"*Energy:* {energy}")
                    lines.append(f"*Readiness:* {score}/100")

                    # Add contributors
                    hrv = contributors.get('hrv_balance')
                    rhr = contributors.get('resting_heart_rate')
                    temp = contributors.get('body_temperature')

                    if hrv is not None:
                        lines.append(f"💓 HRV Balance: {hrv}")
                    if rhr is not None:
                        lines.append(f"❤️ RHR Score: {rhr}")
                    if temp is not None:
                        lines.append(f"🌡️ Body Temp: {temp}")

                    lines.append("")
                    lines.append(f"📝 _{rec}_")

            # Parse sleep
            if sleep_row:
                import json
                sleep = json.loads(sleep_row['data'])
                sleep_score = sleep.get('score')
                if sleep_score is not None:
                    lines.insert(3, f"😴 *Sleep:* {sleep_score}/100")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to fetch Oura data: {e}")
            return f"💪 *Health Status*\n\nError fetching data: {e}"

    async def sync_to_workos(self, entry: 'BrainDumpEntry') -> Optional[int]:
        """
        Sync a brain dump entry to WorkOS database.

        Args:
            entry: The BrainDumpEntry to sync.

        Returns:
            The WorkOS brain dump ID if successful, None otherwise.
        """
        if not self.workos_enabled:
            return None

        try:
            import asyncpg
            import ssl

            # Parse database URL and configure SSL for Neon
            db_url = WORKOS_DATABASE_URL.split('?')[0]  # Remove query params
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            conn = await asyncpg.connect(db_url, ssl=ssl_context)
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO brain_dump (content, category, context, processed, created_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    RETURNING id
                    """,
                    entry.raw_content,
                    entry.parsed_category,
                    entry.parsed_context or 'personal',
                    0  # Not processed
                )
                workos_id = row['id']
                logger.info(f"Synced brain dump to WorkOS #{workos_id}: {entry.id} (context: {entry.parsed_context})")
                return workos_id
            finally:
                await conn.close()

        except ImportError:
            logger.warning("asyncpg not installed - WorkOS sync disabled. Install with: pip install asyncpg")
            self.workos_enabled = False
            return None
        except Exception as e:
            logger.error(f"WorkOS sync failed: {e}")
            return None

    async def convert_to_task(self, brain_dump_id: int, entry: 'BrainDumpEntry') -> Optional[int]:
        """
        Convert a brain dump to a task in WorkOS.

        Args:
            brain_dump_id: The WorkOS brain dump ID.
            entry: The BrainDumpEntry to convert.

        Returns:
            The task ID if successful, None otherwise.
        """
        try:
            import asyncpg
            import ssl

            db_url = WORKOS_DATABASE_URL.split('?')[0]
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            conn = await asyncpg.connect(db_url, ssl=ssl_context)
            try:
                # Create the task
                task_title = entry.parsed_action or entry.raw_content[:100]
                task_row = await conn.fetchrow(
                    """
                    INSERT INTO tasks (title, description, status, category, created_at, updated_at)
                    VALUES ($1, $2, 'backlog', $3, NOW(), NOW())
                    RETURNING id
                    """,
                    task_title,
                    entry.raw_content,
                    entry.parsed_context or 'personal'
                )
                task_id = task_row['id']

                # Mark brain dump as processed
                await conn.execute(
                    """
                    UPDATE brain_dump
                    SET processed = 1, processed_at = NOW(), converted_to_task_id = $1
                    WHERE id = $2
                    """,
                    task_id,
                    brain_dump_id
                )

                return task_id
            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"Failed to convert to task: {e}")
            return None

    def _load_entries(self):
        """Load existing brain dump entries from file.

        Only loads unprocessed entries - processed ones should have been
        deleted, but we clean up any legacy entries that slipped through.
        """
        try:
            if self.storage_path.exists():
                with open(self.storage_path) as f:
                    data = json.load(f)
                    all_entries = [BrainDumpEntry(**e) for e in data]

                # Only keep unprocessed entries (inbox only)
                self.entries = [e for e in all_entries if not e.processed]

                cleaned = len(all_entries) - len(self.entries)
                if cleaned > 0:
                    logger.info(f"Cleaned {cleaned} legacy processed entries")
                    self._save_entries()  # Persist the cleanup

                logger.info(f"Loaded {len(self.entries)} inbox entries")
        except Exception as e:
            logger.warning(f"Could not load brain dump entries: {e}")
            self.entries = []

    def _save_entries(self):
        """Save brain dump entries to file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump([asdict(e) for e in self.entries], f, indent=2)
        except Exception as e:
            logger.error(f"Could not save brain dump entries: {e}")

    def _generate_id(self) -> str:
        """Generate unique ID for entry."""
        import uuid
        return f"bd_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    async def transcribe_voice(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe voice message using OpenAI Whisper API.

        Args:
            audio_file_path: Path to the audio file.

        Returns:
            Transcribed text or None on failure.
        """
        if not self.whisper_api_key:
            logger.error("No Whisper API key configured")
            return None

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                with open(audio_file_path, 'rb') as audio_file:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.whisper_api_key}"},
                        files={"file": ("audio.ogg", audio_file, "audio/ogg")},
                        data={"model": "whisper-1"},
                        timeout=30.0
                    )

                if response.status_code == 200:
                    result = response.json()
                    return result.get('text')
                else:
                    logger.error(f"Whisper API error: {response.status_code} - {response.text}")
                    return None

        except ImportError:
            logger.error("httpx not installed. Install with: pip install httpx")
            return None
        except Exception as e:
            logger.error(f"Voice transcription failed: {e}")
            return None

    async def extract_memories_from_transcription(self, transcription: str, user_id: int) -> List[Dict[str, Any]]:
        """
        Extract and store memories from voice transcription.

        Uses lightweight pattern matching to identify memorable content:
        - Decisions ("decided to...", "going with...")
        - Facts about clients/projects
        - Personal preferences
        - Important dates/deadlines

        Args:
            transcription: The transcribed voice text
            user_id: Telegram user ID for metadata

        Returns:
            List of stored memory results
        """
        if not self.memory_service:
            logger.debug("Memory V2 service not available, skipping memory extraction")
            return []

        # Pattern definitions for memory classification
        patterns = {
            'decision': [
                r'\b(?:decided|going with|choosing|will use|picked|selected|chose)\b',
                r'\b(?:the plan is|we\'re going to|I\'m going to)\b',
            ],
            'deadline': [
                r'\b(?:by|due|deadline|before)\s+(?:end of|next|this|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
                r'\b(?:need to|have to|must)\s+.*\b(?:by|before|until)\b',
                r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}',
            ],
            'preference': [
                r'\b(?:prefer|like to|want to|need to|rather)\b',
                r'\b(?:always|usually|typically|normally)\s+(?:do|use|work|start)',
            ],
            'client_fact': [
                r'\b(?:client|customer|account)\s+(?:wants|needs|said|mentioned|asked)',
                r'\b(?:orlando|raleigh|memphis|kentucky|versacare)\b',  # Known clients
            ],
            'project_fact': [
                r'\b(?:project|feature|sprint|release|milestone)\s+(?:is|was|will be|needs)',
                r'\b(?:thanos|workos|telegram)\s+(?:integration|bot|feature)',  # Known projects
            ],
            'commitment': [
                r'\b(?:promised|committed|agreed|told them|said I would)\b',
                r'\b(?:will get|will send|will deliver|will have)\b.*\b(?:by|before|tomorrow|monday|tuesday|wednesday|thursday|friday)',
            ],
        }

        stored_memories = []

        for memory_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, transcription, re.IGNORECASE):
                    # Found a match - store this as a memory
                    try:
                        metadata = {
                            'source': 'telegram',
                            'content_type': 'voice',
                            'type': memory_type,
                            'user_id': str(user_id),
                            'timestamp': datetime.now().isoformat(),
                            'pattern_matched': pattern,
                        }

                        result = self.memory_service.add(
                            content=transcription,
                            metadata=metadata
                        )

                        if result:
                            stored_memories.append({
                                'memory_type': memory_type,
                                'result': result
                            })
                            logger.info(f"Stored {memory_type} memory from voice transcription")

                        # Only store once per transcription (avoid duplicates)
                        break

                    except Exception as e:
                        logger.warning(f"Failed to store {memory_type} memory: {e}")

                    break  # Move to next memory type after first match

        return stored_memories

    async def parse_content(self, content: str) -> Dict[str, Any]:
        """
        Parse brain dump content using Claude to extract structure.

        Args:
            content: Raw text content to parse.

        Returns:
            Dictionary with parsed fields.
        """
        if not self.claude_api_key:
            # Fallback to basic parsing
            return self._basic_parse(content)

        try:
            import httpx

            prompt = f"""Analyze this brain dump entry and extract structured information.

Content: "{content}"

Respond with JSON only:
{{
    "category": "task|thought|idea|worry|commitment|question",
    "context": "work|personal",
    "priority": "low|medium|high|critical",
    "entities": ["list", "of", "people", "projects", "mentioned"],
    "action": "extracted action item if any, or null",
    "summary": "one-line summary"
}}

For "context": Use "personal" for family, health, errands, hobbies, relationships, home tasks. Use "work" for professional tasks, clients, projects, meetings, deadlines."""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.claude_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    text = result.get('content', [{}])[0].get('text', '{}')
                    # Extract JSON from response
                    try:
                        # Handle potential markdown code blocks
                        if '```json' in text:
                            text = text.split('```json')[1].split('```')[0]
                        elif '```' in text:
                            text = text.split('```')[1].split('```')[0]
                        return json.loads(text.strip())
                    except json.JSONDecodeError:
                        return self._basic_parse(content)
                else:
                    logger.error(f"Claude API error: {response.status_code}")
                    return self._basic_parse(content)

        except ImportError:
            return self._basic_parse(content)
        except Exception as e:
            logger.error(f"Content parsing failed: {e}")
            return self._basic_parse(content)

    def _basic_parse(self, content: str) -> Dict[str, Any]:
        """Basic keyword-based parsing fallback."""
        content_lower = content.lower()

        # Detect category
        if any(word in content_lower for word in ['todo', 'task', 'need to', 'must', 'should']):
            category = 'task'
        elif any(word in content_lower for word in ['idea', 'what if', 'maybe we could']):
            category = 'idea'
        elif any(word in content_lower for word in ['worried', 'concern', 'anxiety', 'stress']):
            category = 'worry'
        elif any(word in content_lower for word in ['commit', 'promise', 'will do', 'agreed']):
            category = 'commitment'
        elif '?' in content:
            category = 'question'
        else:
            category = 'thought'

        # Detect work vs personal context
        personal_keywords = ['family', 'mom', 'dad', 'wife', 'husband', 'kid', 'doctor', 'gym',
                            'grocery', 'home', 'personal', 'errand', 'birthday', 'vacation',
                            'hobby', 'friend', 'dinner', 'weekend', 'health', 'appointment']
        work_keywords = ['client', 'meeting', 'project', 'deadline', 'boss', 'team', 'work',
                        'report', 'presentation', 'email', 'call with', 'sprint', 'deploy',
                        'review', 'standup', 'stakeholder', 'deliverable']

        if any(word in content_lower for word in personal_keywords):
            context = 'personal'
        elif any(word in content_lower for word in work_keywords):
            context = 'work'
        else:
            context = 'personal'  # Default to personal

        # Detect priority
        if any(word in content_lower for word in ['urgent', 'asap', 'critical', 'emergency']):
            priority = 'critical'
        elif any(word in content_lower for word in ['important', 'priority', 'soon']):
            priority = 'high'
        elif any(word in content_lower for word in ['maybe', 'sometime', 'eventually']):
            priority = 'low'
        else:
            priority = 'medium'

        return {
            'category': category,
            'context': context,
            'priority': priority,
            'entities': [],
            'action': None,
            'summary': content[:100]
        }

    async def capture_entry(
        self,
        content: str,
        content_type: str = 'text',
        user_id: Optional[int] = None,
        parse: bool = True
    ) -> BrainDumpEntry:
        """
        Capture a brain dump entry using the new unified pipeline.

        Args:
            content: Raw content (text or transcription).
            content_type: Type of content ('text', 'voice', 'photo').
            user_id: Telegram user ID.
            parse: Whether to parse content for structure.

        Returns:
            The created BrainDumpEntry.
        """
        entry_id = self._generate_id()
        entry = BrainDumpEntry(
            id=entry_id,
            timestamp=datetime.now().isoformat(),
            raw_content=content,
            content_type=content_type,
            user_id=str(user_id) if user_id else None
        )

        # Use new unified pipeline for classification and routing
        if parse and content:
            try:
                # Process through the unified pipeline
                # This handles classification AND routing automatically
                # IMPORTANT: Voice content uses 'voice' source to trigger AI classification
                # This ensures voice notes about work concerns aren't misclassified as tasks
                pipeline_source = 'voice' if content_type == 'voice' else 'telegram'

                result = process_brain_dump_sync(
                    content=content,
                    source=pipeline_source,
                    state_store=self.state_store,
                    journal=self.journal,
                    memory_service=self.memory_service,
                )

                # Update entry with pipeline results
                entry.classification = result.classification
                entry.confidence = result.classification_confidence
                entry.acknowledgment = result.acknowledgment
                entry.needs_review = result.needs_review
                entry.review_reason = result.review_reason

                # Map classification to legacy fields for backwards compatibility
                classification_to_category = {
                    'thinking': 'thought',
                    'venting': 'thought',  # Venting is reflective, not a task
                    'observation': 'thought',
                    'note': 'thought',
                    'idea': 'idea',
                    'personal_task': 'task',
                    'work_task': 'task',
                    'worry': 'worry',
                    'commitment': 'commitment',
                }
                entry.parsed_category = classification_to_category.get(
                    result.classification, 'thought'
                )

                # Derive context from domain
                entry.parsed_context = result.domain or 'personal'

                # Store routing result
                entry.routing_result = {
                    'tasks_created': bool(result.created_task_id),
                    'commitment_created': bool(result.created_commitment_id),
                    'idea_created': result.classification == 'idea' and bool(result.chroma_memory_id),
                    'note_created': result.classification in ('thinking', 'observation') and bool(result.chroma_memory_id),
                    'workos_task_id': result.workos_task_id,
                    'acknowledgment': result.acknowledgment,
                }

                logger.info(
                    f"Classified as {result.classification} "
                    f"(confidence: {result.classification_confidence:.0%}), "
                    f"routed to {result.destinations}"
                )

            except Exception as e:
                logger.error(f"Pipeline processing failed, falling back to basic parse: {e}")
                # Fallback to basic parsing
                parsed = await self.parse_content(content)
                entry.parsed_category = parsed.get('category')
                entry.parsed_context = parsed.get('context', 'personal')
                entry.parsed_priority = parsed.get('priority')
                entry.parsed_entities = parsed.get('entities')
                entry.parsed_action = parsed.get('action')
                entry.classification = entry.parsed_category
                entry.acknowledgment = f"{entry.parsed_category} captured"

        # Add to entries list (legacy storage)
        self.entries.append(entry)
        self._save_entries()

        logger.info(f"Captured brain dump: {entry.id} ({entry.classification})")

        return entry

    def get_unprocessed(self) -> List[BrainDumpEntry]:
        """Get all unprocessed brain dump entries."""
        return [e for e in self.entries if not e.processed]

    def mark_processed(self, entry_id: str, notes: Optional[str] = None):
        """Mark an entry as processed by REMOVING it from the inbox.

        The entry has already been routed to the appropriate database
        (SQLite, Memory V2, WorkOS), so we delete it from the JSON inbox.
        """
        for i, entry in enumerate(self.entries):
            if entry.id == entry_id:
                # Remove from inbox - it's now in the database
                self.entries.pop(i)
                self._save_entries()
                logger.info(f"Removed processed entry {entry_id} from inbox")
                return
        raise ValueError(f"Entry not found: {entry_id}")

    async def setup_handlers(self):
        """Set up Telegram bot handlers."""
        try:
            from telegram import Update
            from telegram.ext import (
                Application,
                CommandHandler,
                MessageHandler,
                filters,
                ContextTypes
            )
        except ImportError:
            logger.error("python-telegram-bot not installed. Install with: pip install python-telegram-bot")
            return False

        if not self.token:
            logger.error("No Telegram bot token configured")
            return False

        # Create application
        self.application = Application.builder().token(self.token).build()

        # Security: check if user is allowed
        def is_allowed(user_id: int) -> bool:
            # SECURITY: Fail-secure - deny access if no users configured
            if not self.allowed_users:
                logger.warning(f"Telegram access denied: No allowed users configured (user_id={user_id})")
                return False
            return user_id in self.allowed_users

        # Command handlers
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                await update.message.reply_text("⛔ You are not authorized to use this bot.")
                return

            await update.message.reply_text(
                "🧠 *Thanos Brain Dump Bot*\n\n"
                "Just send me anything:\n"
                "• 📝 Text messages\n"
                "• 🎤 Voice messages\n"
                "• 📸 Photos (with text)\n\n"
                "I'll capture it, parse it, and add it to your brain dump queue.\n\n"
                "*Commands:*\n"
                "/status - Quick status overview\n"
                "/health - Oura Ring health metrics\n"
                "/tasks - View active tasks\n"
                "/habits - View habits\n"
                "/dumps - View pending brain dumps\n\n"
                "*Natural Language:*\n"
                "Ask \"what tasks do I have?\" or \"show my habits\"",
                parse_mode='Markdown'
            )

        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                return
            response = await self._get_status_response()
            await update.message.reply_text(response, parse_mode='Markdown')

        async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                return

            text = update.message.text

            # Check if this is a command/query first
            command_type, params = self.detect_command(text)
            if command_type:
                response = await self.handle_command(command_type, params or {})
                await update.message.reply_text(response, parse_mode='Markdown')
                return

            # Check if content should be filtered
            should_filter, filter_reason = self.should_filter_content(text)
            if should_filter:
                logger.info(f"Filtered content ({filter_reason}): {text[:50]}")
                await update.message.reply_text(
                    f"🔇 Message filtered ({filter_reason})\n\n"
                    "Send a complete thought or use /status to check pending items."
                )
                return

            entry = await self.capture_entry(
                content=text,
                content_type='text',
                user_id=update.effective_user.id
            )

            # Build response message
            response_parts = []

            # Use acknowledgment from pipeline if available
            if entry.acknowledgment:
                response_parts.append(entry.acknowledgment)

            # Add classification info
            emoji = {
                'thinking': '💭',
                'venting': '😤',
                'observation': '👁️',
                'note': '📝',
                'idea': '💡',
                'personal_task': '✅',
                'work_task': '💼',
                'worry': '😰',
                'commitment': '🤝',
                # Legacy fallbacks
                'task': '✅',
                'thought': '💭',
            }.get(entry.classification or entry.parsed_category, '📝')

            classification_display = entry.classification or entry.parsed_category or 'captured'
            response_parts.append(f"{emoji} {classification_display.replace('_', ' ').title()}")

            # Add routing result info
            if entry.routing_result:
                destinations = []
                if entry.routing_result.get('tasks_created'):
                    destinations.append("task created")
                if entry.routing_result.get('workos_task_id'):
                    destinations.append("synced to WorkOS")
                if entry.routing_result.get('idea_created'):
                    destinations.append("idea saved")
                if entry.routing_result.get('commitment_created'):
                    destinations.append("commitment tracked")
                if entry.routing_result.get('note_created'):
                    destinations.append("note saved")

                if destinations:
                    response_parts.append(f"✓ {', '.join(destinations)}")

            # Add review notice if needed (check if entry has this attribute)
            if hasattr(entry, 'needs_review') and entry.needs_review:
                response_parts.append("\n⚠️ Needs review - please check later")

            await update.message.reply_text("\n".join(response_parts))

        async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle document/file uploads (text files, etc.)"""
            if not is_allowed(update.effective_user.id):
                return

            document = update.message.document
            file_name = document.file_name or "unknown"
            mime_type = document.mime_type or ""

            # Only process text files
            supported_extensions = ('.txt', '.md', '.text', '.log')
            supported_mimes = ('text/plain', 'text/markdown', 'text/x-markdown')

            is_text_file = (
                file_name.lower().endswith(supported_extensions) or
                mime_type in supported_mimes
            )

            if not is_text_file:
                await update.message.reply_text(
                    f"📄 Received: {file_name}\n\n"
                    "Currently only text files (.txt, .md) are supported.\n"
                    "For other files, please copy and paste the content."
                )
                return

            # Download the file
            file = await context.bot.get_file(document.file_id)

            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='wb') as tmp:
                await file.download_to_drive(tmp.name)
                tmp_path = tmp.name

            try:
                # Read file content
                processing_msg = await update.message.reply_text(f"📄 Processing: {file_name}...")

                with open(tmp_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()

                if not content.strip():
                    await processing_msg.edit_text(f"📄 {file_name} is empty.")
                    return

                # Check content length - handle large files
                if len(content) > 10000:
                    await processing_msg.edit_text(
                        f"📄 {file_name}\n\n"
                        f"File is large ({len(content):,} chars). Processing first 10,000 characters.\n"
                        "Consider breaking into smaller files for better classification."
                    )
                    content = content[:10000]

                # Check if content should be filtered
                should_filter, filter_reason = self.should_filter_content(content)
                if should_filter:
                    logger.info(f"Filtered document ({filter_reason}): {file_name}")
                    await processing_msg.edit_text(
                        f"📄 {file_name}\n\n"
                        f"🔇 Content filtered ({filter_reason})"
                    )
                    return

                # Process through brain dump pipeline
                entry = await self.capture_entry(
                    content=content,
                    content_type='document',
                    user_id=update.effective_user.id
                )

                # Build response
                response_parts = [f"📄 *{file_name}*\n"]

                # Preview of content
                preview = content[:200].replace('*', '').replace('_', '')
                if len(content) > 200:
                    preview += "..."
                response_parts.append(f"```\n{preview}\n```\n")

                # Acknowledgment
                if entry.acknowledgment:
                    response_parts.append(entry.acknowledgment)

                # Classification
                emoji = {
                    'thinking': '💭', 'venting': '😤', 'observation': '👁️',
                    'note': '📝', 'idea': '💡', 'personal_task': '✅',
                    'work_task': '💼', 'worry': '😰', 'commitment': '🤝',
                    'task': '✅', 'thought': '💭',
                }.get(entry.classification or entry.parsed_category, '📝')

                classification_display = (entry.classification or entry.parsed_category or 'captured').replace('_', ' ').title()
                response_parts.append(f"{emoji} {classification_display}")

                # Routing info
                if entry.routing_result:
                    destinations = []
                    if entry.routing_result.get('tasks_created'):
                        destinations.append("task created")
                    if entry.routing_result.get('workos_task_id'):
                        destinations.append("synced to WorkOS")
                    if entry.routing_result.get('idea_created'):
                        destinations.append("idea saved")
                    if entry.routing_result.get('commitment_created'):
                        destinations.append("commitment tracked")
                    if entry.routing_result.get('note_created'):
                        destinations.append("note saved")
                    if destinations:
                        response_parts.append(f"✓ {', '.join(destinations)}")

                if entry.needs_review:
                    response_parts.append("\n⚠️ Needs review")

                await processing_msg.edit_text("\n".join(response_parts), parse_mode='Markdown')

            except Exception as e:
                logger.error(f"Document processing failed: {e}")
                await update.message.reply_text(f"❌ Error processing {file_name}: {e}")
            finally:
                os.unlink(tmp_path)

        async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                return

            # Download voice file
            voice = update.message.voice
            file = await context.bot.get_file(voice.file_id)

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
                await file.download_to_drive(tmp.name)
                tmp_path = tmp.name

            try:
                # Send "processing" message
                processing_msg = await update.message.reply_text("🎤 Transcribing...")

                # Transcribe
                transcription = await self.transcribe_voice(tmp_path)

                if transcription:
                    # Check if this is a voice command/query
                    command_type, params = self.detect_command(transcription)
                    if command_type:
                        response = await self.handle_command(command_type, params or {})
                        await processing_msg.edit_text(
                            f"🎤 _{transcription}_\n\n{response}",
                            parse_mode='Markdown'
                        )
                        return

                    # Check if content should be filtered (noise, incomplete)
                    should_filter, filter_reason = self.should_filter_content(transcription)
                    if should_filter:
                        logger.info(f"Filtered voice ({filter_reason}): {transcription[:50]}")
                        await processing_msg.edit_text(
                            f"🎤 _{transcription}_\n\n"
                            f"🔇 Filtered ({filter_reason})\n"
                            "Try speaking a complete thought or task."
                        )
                        return

                    entry = await self.capture_entry(
                        content=transcription,
                        content_type='voice',
                        user_id=update.effective_user.id
                    )

                    # Extract and store memories from transcription
                    memories_stored = await self.extract_memories_from_transcription(
                        transcription,
                        update.effective_user.id
                    )

                    # Build response message
                    response_parts = [f"🎤 *Transcription:*\n_{transcription}_\n"]

                    # Use acknowledgment from pipeline if available
                    if entry.acknowledgment:
                        response_parts.append(entry.acknowledgment)

                    # Add classification info
                    emoji = {
                        'thinking': '💭',
                        'venting': '😤',
                        'observation': '👁️',
                        'note': '📝',
                        'idea': '💡',
                        'personal_task': '✅',
                        'work_task': '💼',
                        'worry': '😰',
                        'commitment': '🤝',
                        # Legacy fallbacks
                        'task': '✅',
                        'thought': '💭',
                    }.get(entry.classification or entry.parsed_category, '📝')

                    classification_display = (
                        entry.classification or entry.parsed_category or 'captured'
                    ).replace('_', ' ').title()
                    response_parts.append(f"{emoji} {classification_display}")

                    # Add routing result info
                    if entry.routing_result:
                        destinations = []
                        if entry.routing_result.get('tasks_created'):
                            destinations.append("task created")
                        if entry.routing_result.get('workos_task_id'):
                            destinations.append("synced to WorkOS")
                        if entry.routing_result.get('idea_created'):
                            destinations.append("idea saved")
                        if entry.routing_result.get('commitment_created'):
                            destinations.append("commitment tracked")
                        if entry.routing_result.get('note_created'):
                            destinations.append("note saved")

                        if destinations:
                            response_parts.append(f"✓ {', '.join(destinations)}")

                    # Add memory extraction info
                    if memories_stored:
                        memory_types = [m['memory_type'].replace('_', ' ') for m in memories_stored]
                        response_parts.append(f"🧠 Memory stored: {', '.join(memory_types)}")

                    # Add review notice if needed
                    if entry.needs_review:
                        response_parts.append("\n⚠️ Needs review - please check later")

                    await processing_msg.edit_text("\n".join(response_parts), parse_mode='Markdown')
                else:
                    await processing_msg.edit_text("❌ Could not transcribe voice message")

            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        # Explicit command handlers
        async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                return
            response = await self._get_tasks_response('active')
            await update.message.reply_text(response, parse_mode='Markdown')

        async def habits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                return
            response = await self._get_habits_response()
            await update.message.reply_text(response, parse_mode='Markdown')

        async def dumps_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                return
            response = self._get_brain_dumps_response()
            await update.message.reply_text(response, parse_mode='Markdown')

        async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                return
            response = await self._get_health_response()
            await update.message.reply_text(response, parse_mode='Markdown')

        # Register handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("status", status_command))
        self.application.add_handler(CommandHandler("tasks", tasks_command))
        self.application.add_handler(CommandHandler("habits", habits_command))
        self.application.add_handler(CommandHandler("dumps", dumps_command))
        self.application.add_handler(CommandHandler("health", health_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        self.application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        self.application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

        return True

    async def run(self):
        """Run the Telegram bot."""
        if not await self.setup_handlers():
            logger.error("Failed to set up bot handlers")
            return

        logger.info("Starting Telegram brain dump bot...")
        self.is_running = True

        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            # Keep running until stopped
            while self.is_running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    def stop(self):
        """Stop the bot."""
        self.is_running = False


async def main():
    """Run the Telegram bot."""
    import argparse

    parser = argparse.ArgumentParser(description='Thanos Telegram Brain Dump Bot')
    parser.add_argument('--test-capture', type=str, help='Test capture without Telegram')
    parser.add_argument('--status', action='store_true', help='Show pending entries')
    args = parser.parse_args()

    bot = TelegramBrainDumpBot()

    if args.status:
        unprocessed = bot.get_unprocessed()
        print(f"\n=== {len(unprocessed)} Pending Brain Dumps ===\n")
        for entry in unprocessed:
            print(f"[{entry.parsed_category}] {entry.raw_content[:80]}")
            print(f"  Priority: {entry.parsed_priority} | ID: {entry.id}")
            print()
        return

    if args.test_capture:
        entry = await bot.capture_entry(args.test_capture, 'text')
        print(f"\nCaptured entry:")
        print(f"  ID: {entry.id}")
        print(f"  Category: {entry.parsed_category}")
        print(f"  Priority: {entry.parsed_priority}")
        print(f"  Action: {entry.parsed_action}")
        return

    # Run the bot
    await bot.run()


if __name__ == '__main__':
    asyncio.run(main())
