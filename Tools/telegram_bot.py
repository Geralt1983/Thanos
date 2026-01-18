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
    parsed_category: Optional[str] = None  # 'task', 'thought', 'idea', 'worry', 'commitment'
    parsed_context: Optional[str] = None  # 'work', 'personal'
    parsed_priority: Optional[str] = None  # 'low', 'medium', 'high', 'critical'
    parsed_entities: Optional[List[str]] = None  # extracted people, projects, etc.
    parsed_action: Optional[str] = None  # extracted action item
    source: str = 'telegram'
    user_id: Optional[str] = None
    processed: bool = False
    processing_notes: Optional[str] = None


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
    """

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

        # Storage for entries
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
            logger.info("WorkOS sync enabled")

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
        Capture a brain dump entry.

        Args:
            content: Raw content (text or transcription).
            content_type: Type of content ('text', 'voice', 'photo').
            user_id: Telegram user ID.
            parse: Whether to parse content for structure.

        Returns:
            The created BrainDumpEntry.
        """
        entry = BrainDumpEntry(
            id=self._generate_id(),
            timestamp=datetime.now().isoformat(),
            raw_content=content,
            content_type=content_type,
            user_id=str(user_id) if user_id else None
        )

        # Parse content if enabled
        if parse and content:
            parsed = await self.parse_content(content)
            entry.parsed_category = parsed.get('category')
            entry.parsed_context = parsed.get('context', 'personal')  # Default to personal
            entry.parsed_priority = parsed.get('priority')
            entry.parsed_entities = parsed.get('entities')
            entry.parsed_action = parsed.get('action')

        # Add to entries
        self.entries.append(entry)
        self._save_entries()

        # Log to journal
        self.journal.log(
            event_type=EventType.BRAIN_DUMP_RECEIVED,
            title=f"Brain dump captured: {content[:50]}...",
            data={
                'entry_id': entry.id,
                'content_type': content_type,
                'category': entry.parsed_category,
                'priority': entry.parsed_priority
            },
            severity='info',
            source='telegram_bot'
        )

        # Sync to WorkOS if enabled
        if self.workos_enabled:
            workos_id = await self.sync_to_workos(entry)

            # Auto-convert to task ONLY if actionable (task or commitment)
            if entry.parsed_category in ('task', 'commitment') and workos_id:
                task_id = await self.convert_to_task(workos_id, entry)
                if task_id:
                    logger.info(f"Auto-converted to task #{task_id}")

        logger.info(f"Captured brain dump: {entry.id} ({entry.parsed_category})")

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
                "Commands:\n"
                "/status - View pending items\n"
                "/clear - Clear processed items",
                parse_mode='Markdown'
            )

        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                return

            unprocessed = self.get_unprocessed()
            if not unprocessed:
                await update.message.reply_text("✅ No pending brain dumps!")
                return

            # Group by category
            by_category: Dict[str, List[BrainDumpEntry]] = {}
            for entry in unprocessed:
                cat = entry.parsed_category or 'uncategorized'
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(entry)

            message = f"📋 *{len(unprocessed)} Pending Brain Dumps*\n\n"
            for cat, entries in by_category.items():
                emoji = {
                    'task': '✅',
                    'idea': '💡',
                    'worry': '😰',
                    'commitment': '🤝',
                    'thought': '💭',
                    'question': '❓'
                }.get(cat, '📝')
                message += f"{emoji} *{cat.title()}* ({len(entries)})\n"
                for entry in entries[:3]:  # Show max 3 per category
                    preview = entry.raw_content[:50] + '...' if len(entry.raw_content) > 50 else entry.raw_content
                    message += f"  • {preview}\n"
                if len(entries) > 3:
                    message += f"  • _...and {len(entries) - 3} more_\n"
                message += "\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                return

            text = update.message.text
            entry = await self.capture_entry(
                content=text,
                content_type='text',
                user_id=update.effective_user.id
            )

            # Send confirmation
            emoji = {
                'task': '✅',
                'idea': '💡',
                'worry': '😰',
                'commitment': '🤝',
                'thought': '💭',
                'question': '❓'
            }.get(entry.parsed_category, '📝')

            await update.message.reply_text(
                f"{emoji} Captured as *{entry.parsed_category}*\n"
                f"Priority: {entry.parsed_priority}",
                parse_mode='Markdown'
            )

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
                    entry = await self.capture_entry(
                        content=transcription,
                        content_type='voice',
                        user_id=update.effective_user.id
                    )

                    emoji = {
                        'task': '✅',
                        'idea': '💡',
                        'worry': '😰',
                        'commitment': '🤝',
                        'thought': '💭',
                        'question': '❓'
                    }.get(entry.parsed_category, '📝')

                    await processing_msg.edit_text(
                        f"🎤 *Transcription:*\n_{transcription}_\n\n"
                        f"{emoji} Captured as *{entry.parsed_category}*",
                        parse_mode='Markdown'
                    )
                else:
                    await processing_msg.edit_text("❌ Could not transcribe voice message")

            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        # Register handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("status", status_command))
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
