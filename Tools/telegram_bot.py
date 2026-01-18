#!/usr/bin/env python3
"""
Thanos Telegram Brain Dump Bot.

Mobile-first capture interface for quick thoughts, tasks, and ideas.
Supports voice messages with Whisper transcription.
"""

import os
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

# Import new classification system
from Tools.brain_dump import (
    BrainDumpClassifier,
    ClassifiedBrainDump,
    BrainDumpRouter,
    RoutingResult,
    Classification,
)
from Tools.state_store import get_db

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
    classification: Optional[str] = None  # thinking, venting, observation, note, idea, personal_task, work_task, commitment, mixed
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

        # Initialize new classification system
        self.classifier = BrainDumpClassifier(api_key=self.claude_api_key)
        self.state_store = get_db()
        self.router = BrainDumpRouter(
            state=self.state_store,
            journal=self.journal,
            workos_adapter=None  # Will be set up if WorkOS enabled
        )

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
            else:
                return "I didn't understand that command. Try asking about tasks, habits, or status."
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
        """Load existing brain dump entries from file."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path) as f:
                    data = json.load(f)
                    self.entries = [BrainDumpEntry(**e) for e in data]
                logger.info(f"Loaded {len(self.entries)} brain dump entries")
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
        Capture a brain dump entry using the new classification system.

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

        # Use new classification system
        if parse and content:
            try:
                # Classify using the new classifier
                classified = await self.classifier.classify(
                    content=content,
                    source='telegram',
                    user_id=str(user_id) if user_id else None
                )

                # Update entry with classification results
                entry.classification = classified.classification
                entry.confidence = classified.confidence
                entry.acknowledgment = classified.acknowledgment
                entry.parsed_priority = classified.priority
                entry.parsed_entities = classified.entities

                # Map classification to legacy category for backwards compatibility
                classification_to_category = {
                    'thinking': 'thought',
                    'venting': 'thought',
                    'observation': 'thought',
                    'note': 'thought',
                    'idea': 'idea',
                    'personal_task': 'task',
                    'work_task': 'task',
                    'commitment': 'commitment',
                    'mixed': 'thought',
                }
                entry.parsed_category = classification_to_category.get(
                    classified.classification, 'thought'
                )

                # Derive context from classification
                if classified.classification == 'work_task':
                    entry.parsed_context = 'work'
                else:
                    entry.parsed_context = 'personal'

                # Route the classified brain dump
                routing_result = await self.router.route(classified)
                entry.routing_result = {
                    'tasks_created': routing_result.tasks_created,
                    'commitment_created': routing_result.commitment_created,
                    'idea_created': routing_result.idea_created,
                    'note_created': routing_result.note_created,
                    'workos_task_id': routing_result.workos_task_id,
                    'acknowledgment': routing_result.acknowledgment,
                }

                logger.info(
                    f"Classified as {classified.classification} "
                    f"(confidence: {classified.confidence:.0%})"
                )

            except Exception as e:
                logger.error(f"Classification failed, falling back to basic parse: {e}")
                # Fallback to basic parsing
                parsed = await self.parse_content(content)
                entry.parsed_category = parsed.get('category')
                entry.parsed_context = parsed.get('context', 'personal')
                entry.parsed_priority = parsed.get('priority')
                entry.parsed_entities = parsed.get('entities')
                entry.parsed_action = parsed.get('action')
                entry.classification = entry.parsed_category

        # Add to entries list (legacy storage)
        self.entries.append(entry)
        self._save_entries()

        # Also store in unified state store
        try:
            self.state_store.create_brain_dump(
                content=content,
                source='telegram',
                category=entry.classification,
                domain=entry.parsed_context,
                metadata={
                    'entry_id': entry_id,
                    'content_type': content_type,
                    'user_id': str(user_id) if user_id else None,
                    'confidence': entry.confidence,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to store in state store: {e}")

        logger.info(f"Captured brain dump: {entry.id} ({entry.classification})")

        return entry

    def get_unprocessed(self) -> List[BrainDumpEntry]:
        """Get all unprocessed brain dump entries."""
        return [e for e in self.entries if not e.processed]

    def mark_processed(self, entry_id: str, notes: Optional[str] = None):
        """Mark an entry as processed."""
        for entry in self.entries:
            if entry.id == entry_id:
                entry.processed = True
                entry.processing_notes = notes
                self._save_entries()
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
            if not self.allowed_users:
                return True  # No restrictions if no users specified
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

            # Use acknowledgment from classification if available
            if entry.acknowledgment:
                await update.message.reply_text(entry.acknowledgment)
                return

            # Fallback: Send confirmation with emoji based on new classification
            emoji = {
                'thinking': '💭',
                'venting': '😤',
                'observation': '👁️',
                'note': '📝',
                'idea': '💡',
                'personal_task': '✅',
                'work_task': '💼',
                'commitment': '🤝',
                'mixed': '🔀',
                # Legacy fallbacks
                'task': '✅',
                'thought': '💭',
                'worry': '😰',
                'question': '❓'
            }.get(entry.classification or entry.parsed_category, '📝')

            classification_display = entry.classification or entry.parsed_category or 'captured'

            # Build response based on classification
            response_parts = [f"{emoji} {classification_display.replace('_', ' ').title()}"]

            # Add context info for tasks
            if entry.classification in ('personal_task', 'work_task'):
                domain = 'personal' if entry.classification == 'personal_task' else 'work'
                response_parts.append(f"Domain: {domain}")
                if entry.parsed_priority:
                    response_parts.append(f"Priority: {entry.parsed_priority}")

            # Add routing result info
            if entry.routing_result:
                if entry.routing_result.get('tasks_created'):
                    response_parts.append("Task created ✓")
                if entry.routing_result.get('workos_task_id'):
                    response_parts.append("Synced to WorkOS ✓")
                if entry.routing_result.get('idea_created'):
                    response_parts.append("Idea captured ✓")
                if entry.routing_result.get('commitment_created'):
                    response_parts.append("Commitment tracked ✓")

            await update.message.reply_text("\n".join(response_parts))

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

                    # Use acknowledgment or build response
                    if entry.acknowledgment:
                        response = f"🎤 *Transcription:*\n_{transcription}_\n\n{entry.acknowledgment}"
                    else:
                        emoji = {
                            'thinking': '💭',
                            'venting': '😤',
                            'observation': '👁️',
                            'note': '📝',
                            'idea': '💡',
                            'personal_task': '✅',
                            'work_task': '💼',
                            'commitment': '🤝',
                            'mixed': '🔀',
                            'task': '✅',
                            'thought': '💭',
                        }.get(entry.classification or entry.parsed_category, '📝')

                        classification_display = (
                            entry.classification or entry.parsed_category or 'captured'
                        ).replace('_', ' ').title()

                        response = (
                            f"🎤 *Transcription:*\n_{transcription}_\n\n"
                            f"{emoji} {classification_display}"
                        )

                    await processing_msg.edit_text(response, parse_mode='Markdown')
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

        # Register handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("status", status_command))
        self.application.add_handler(CommandHandler("tasks", tasks_command))
        self.application.add_handler(CommandHandler("habits", habits_command))
        self.application.add_handler(CommandHandler("dumps", dumps_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        self.application.add_handler(MessageHandler(filters.VOICE, handle_voice))

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
