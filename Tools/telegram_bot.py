#!/usr/bin/env python3
"""
Thanos Telegram Brain Dump Bot.

Mobile-first capture interface for quick thoughts, tasks, and ideas.
Supports voice messages with Whisper transcription and photo capture with classification.
"""

import os
import re
import json
import asyncio
import tempfile
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
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
    - Photo/image capture with auto-classification (receipt, document, screenshot, etc.)
    - PDF document intake with text extraction and memory ingestion
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
        'rag_ingest': [
            r'\bingest\b.*\bdrive\b',
            r'\bsync\b.*\bdrive\b',
            r'\bdrive\b.*\bingest\b',
            r'\bdrive\b.*\bsync\b',
            r'\brefresh\b.*\brag\b',
            r'\bupdate\b.*\brag\b',
            r'\bopenai\b.*\brag\b',
            r'\bopenai\b.*\bresponses\b',
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

        # Chat mode - when enabled, messages route through ThanosOrchestrator for AI responses
        # Toggle with /chat command, or use /ask for one-shot queries
        self.chat_mode: Dict[int, bool] = {}  # user_id -> chat_mode_enabled
        self._orchestrator = None  # Lazy-loaded ThanosOrchestrator

        # Callback routing system - maps callback prefixes to handler functions
        # Example: {"cal_": handle_calendar, "task_": handle_task_action}
        self.callback_handlers: Dict[str, callable] = {}

    @property
    def orchestrator(self):
        """Lazy-load ThanosOrchestrator for chat mode."""
        if self._orchestrator is None:
            try:
                from Tools.thanos_orchestrator import ThanosOrchestrator
                self._orchestrator = ThanosOrchestrator()
                logger.info("ThanosOrchestrator initialized for chat mode")
            except Exception as e:
                logger.error(f"Failed to initialize ThanosOrchestrator: {e}")
                raise
        return self._orchestrator

    def is_chat_mode_enabled(self, user_id: int) -> bool:
        """Check if chat mode is enabled for a user."""
        return self.chat_mode.get(user_id, False)

    def toggle_chat_mode(self, user_id: int) -> bool:
        """Toggle chat mode for a user. Returns new state."""
        current = self.chat_mode.get(user_id, False)
        self.chat_mode[user_id] = not current
        return not current

    def _create_button(self, text: str, callback_data: str):
        """
        Create a single inline keyboard button.

        Args:
            text: Button text to display
            callback_data: Callback data to send when button is pressed

        Returns:
            InlineKeyboardButton instance
        """
        from telegram import InlineKeyboardButton
        return InlineKeyboardButton(text=text, callback_data=callback_data)

    def _create_button_row(self, buttons: List[tuple]) -> List:
        """
        Create a row of inline keyboard buttons.

        Args:
            buttons: List of (text, callback_data) tuples

        Returns:
            List of InlineKeyboardButton instances (single row)
        """
        return [self._create_button(text, callback_data) for text, callback_data in buttons]

    def _build_inline_keyboard(self, button_rows: List[List[tuple]]):
        """
        Build an inline keyboard markup from button definitions.

        Args:
            button_rows: List of button rows, where each row is a list of (text, callback_data) tuples
                        Example: [
                            [("Button 1", "callback_1"), ("Button 2", "callback_2")],
                            [("Button 3", "callback_3")]
                        ]

        Returns:
            InlineKeyboardMarkup instance
        """
        from telegram import InlineKeyboardMarkup
        keyboard = [self._create_button_row(row) for row in button_rows]
        return InlineKeyboardMarkup(keyboard)

    def _create_button_grid(self, buttons: List[tuple], columns: int = 2):
        """
        Create a grid layout of inline keyboard buttons.

        Args:
            buttons: List of (text, callback_data) tuples
            columns: Number of buttons per row (default: 2)

        Returns:
            InlineKeyboardMarkup instance
        """
        button_rows = []
        for i in range(0, len(buttons), columns):
            row = buttons[i:i + columns]
            button_rows.append(row)
        return self._build_inline_keyboard(button_rows)

    def _register_callback_handler(self, prefix: str, handler: callable):
        """
        Register a callback handler for a specific callback data prefix.

        This enables unified routing of button callbacks through a single entry point.
        Handlers are matched by prefix, allowing namespaced callback organization.

        Args:
            prefix: Callback data prefix (e.g., "task_", "menu_", "energy_")
            handler: Async function that handles the callback
                    Signature: async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE)

        Example:
            self._register_callback_handler("task_", handle_task_actions)
            # Now all callbacks starting with "task_" will route to handle_task_actions
        """
        self.callback_handlers[prefix] = handler
        logger.info(f"Registered callback handler for prefix: {prefix}")

    async def _route_callback(self, update, context):
        """
        Unified callback routing system for inline keyboard button actions.

        Routes callback queries to the appropriate handler based on callback_data prefix.
        This provides a central dispatch point for all button interactions.

        Args:
            update: Telegram Update object containing callback_query
            context: Telegram context object

        Flow:
            1. Extract callback_data from query
            2. Find matching handler by prefix
            3. Dispatch to handler or show error
            4. Log routing for debugging

        The callback_data format should be: "prefix_action_params"
        Example: "task_complete_123" routes to handler registered for "task_"
        """
        query = update.callback_query

        try:
            # Always acknowledge the callback to remove loading state
            await query.answer()

            callback_data = query.data
            logger.info(f"Routing callback: {callback_data}")

            # Find matching handler by prefix
            handler = None
            matched_prefix = None

            for prefix, registered_handler in self.callback_handlers.items():
                if callback_data.startswith(prefix):
                    handler = registered_handler
                    matched_prefix = prefix
                    break

            if handler:
                logger.info(f"Dispatching to handler for prefix: {matched_prefix}")
                await handler(update, context)
            else:
                # No handler found for this callback
                logger.warning(f"No handler registered for callback: {callback_data}")
                await query.edit_message_text(
                    "⚠️ This action is not yet implemented.\n"
                    "Please try again later or use text commands."
                )

        except Exception as e:
            logger.error(f"Error routing callback {query.data}: {e}", exc_info=True)
            try:
                await query.edit_message_text(
                    f"❌ Error processing action: {str(e)[:100]}\n"
                    "Please try again or contact support."
                )
            except Exception:
                # If we can't edit the message, at least log it
                logger.error("Failed to send error message to user")

    async def get_ai_response(self, message: str, user_id: int) -> str:
        """
        Get AI response via ThanosOrchestrator.

        Routes message through the orchestrator which handles:
        - Agent selection based on content
        - State/context injection
        - Memory integration
        - Tool execution

        Args:
            message: User's message
            user_id: Telegram user ID

        Returns:
            AI response text
        """
        try:
            # Route through orchestrator
            response = self.orchestrator.route(message, stream=False)

            # Handle different response types
            if isinstance(response, dict):
                # Response with metadata
                return response.get('response', response.get('content', str(response)))
            elif isinstance(response, str):
                return response
            else:
                return str(response)
        except Exception as e:
            logger.error(f"AI response error: {e}")
            return f"⚠️ Error getting response: {str(e)[:100]}"

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

                    if command_type == "rag_ingest":
                        match = re.search(r"(?:into|to)\s+(.+)$", content_lower)
                        if match:
                            target = match.group(1).strip()
                            target = re.sub(r"[^\w\s-]+$", "", target).strip()
                            if target:
                                params["target"] = target

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
            elif command_type == 'rag_ingest':
                return await self._handle_rag_ingest(params)
            else:
                return "I didn't understand that command. Try asking about tasks, habits, health, or status."
        except Exception as e:
            logger.error(f"Command handling failed: {e}")
            return f"Sorry, I couldn't fetch that information: {e}"

    async def _handle_rag_ingest(self, params: dict) -> str:
        """Sync Google Drive PDFs into OpenAI RAG vector store."""
        import sys
        import subprocess
        from pathlib import Path

        target = (params or {}).get("target")
        project_root = Path(__file__).resolve().parents[1]
        script_path = project_root / "Tools" / "openai_file_search.py"

        cmd = [sys.executable, str(script_path), "sync-drive", "--ensure-folders"]
        if target:
            cmd += ["--key", target]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            output = (result.stderr or result.stdout or "RAG ingest failed").strip()
            return f"❌ Drive ingest failed.\n{output}"

        output = (result.stdout or "Drive sync complete.").strip()
        return f"✅ {output}"

    def _classify_photo(self, caption: str) -> str:
        """
        Classify photo type based on caption keywords.

        Returns:
            Photo type: receipt, document, screenshot, whiteboard, note, reference, personal, unknown
        """
        caption_lower = caption.lower() if caption else ""

        # Receipt keywords
        if any(kw in caption_lower for kw in ['receipt', 'invoice', 'bill', 'purchase', 'expense', 'payment', 'bought', 'paid']):
            return 'receipt'

        # Document keywords
        if any(kw in caption_lower for kw in ['document', 'contract', 'form', 'paper', 'letter', 'certificate', 'license', 'id', 'passport']):
            return 'document'

        # Screenshot keywords
        if any(kw in caption_lower for kw in ['screenshot', 'screen', 'app', 'error', 'bug', 'ui', 'interface']):
            return 'screenshot'

        # Whiteboard keywords
        if any(kw in caption_lower for kw in ['whiteboard', 'board', 'diagram', 'flowchart', 'meeting', 'brainstorm']):
            return 'whiteboard'

        # Reference keywords
        if any(kw in caption_lower for kw in ['reference', 'save', 'remember', 'later', 'bookmark', 'look up', 'calendar', 'schedule']):
            return 'reference'

        # Note keywords
        if any(kw in caption_lower for kw in ['note', 'notes', 'handwritten', 'written', 'list', 'todo']):
            return 'note'

        # Personal photo keywords
        if any(kw in caption_lower for kw in ['photo', 'picture', 'selfie', 'family', 'kids', 'fun', 'vacation']):
            return 'personal'

        # No caption or unknown
        return 'unknown' if not caption else 'reference'

    async def extract_pdf_text(self, pdf_path: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Tuple of (extracted_text, error_message) - one will be None.
        """
        # Try PyPDF2 first (most common)
        try:
            import PyPDF2

            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text_parts = []

                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                        continue

                if text_parts:
                    return "\n\n".join(text_parts), None
                else:
                    return None, "PDF contains no extractable text (may be scanned/image-based)"

        except ImportError:
            pass  # Try pdfplumber

        # Try pdfplumber as fallback (better for complex layouts)
        try:
            import pdfplumber

            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                        continue

            if text_parts:
                return "\n\n".join(text_parts), None
            else:
                return None, "PDF contains no extractable text (may be scanned/image-based)"

        except ImportError:
            return None, "No PDF library available. Install with: pip install PyPDF2 or pip install pdfplumber"

        except Exception as e:
            return None, f"PDF extraction failed: {e}"

    def _extract_pdf_metadata(self, filename: str, content: str) -> Dict[str, Any]:
        """
        Automatically extract metadata from PDF filename and content.

        Analyzes:
        - Filename for client names, document types
        - First page content for titles, headers, key terms
        """
        metadata = {}

        # Known clients to detect
        known_clients = {
            'orlando': 'Orlando',
            'raleigh': 'Raleigh',
            'memphis': 'Memphis',
            'kentucky': 'Kentucky',
            'versacare': 'VersaCare',
            'unc': 'UNC',
            'duke': 'Duke',
        }

        # Work document type patterns
        work_doc_types = {
            'proposal': 'proposal',
            'contract': 'contract',
            'invoice': 'invoice',
            'report': 'report',
            'spec': 'specification',
            'requirements': 'requirements',
            'sow': 'statement_of_work',
            'msa': 'master_agreement',
            'nda': 'nda',
            'workflow': 'workflow',
            'flowsheet': 'flowsheet',
            'policy': 'policy',
            'procedure': 'procedure',
            'training': 'training',
            'manual': 'manual',
            'guide': 'guide',
        }

        # Personal document type patterns
        personal_doc_types = {
            # Financial
            'receipt': 'receipt',
            'statement': 'statement',
            'tax': 'tax',
            '1099': 'tax',
            'w2': 'tax',
            'w-2': 'tax',
            '1040': 'tax',
            'return': 'tax_return',
            # Insurance
            'insurance': 'insurance',
            'policy': 'insurance_policy',
            'claim': 'insurance_claim',
            'eob': 'explanation_of_benefits',
            'coverage': 'insurance',
            # Medical/Health
            'prescription': 'medical',
            'lab': 'medical',
            'results': 'medical',
            'immunization': 'medical',
            'vaccination': 'medical',
            # Travel
            'passport': 'travel',
            'visa': 'travel',
            'itinerary': 'travel',
            'boarding': 'travel',
            'ticket': 'travel',
            'reservation': 'travel',
            'confirmation': 'confirmation',
            # Legal
            'will': 'legal',
            'trust': 'legal',
            'deed': 'legal',
            'title': 'legal',
            'certificate': 'certificate',
            'license': 'license',
            # Home
            'mortgage': 'home',
            'lease': 'home',
            'rental': 'home',
            'utility': 'home',
            'hoa': 'home',
            # Vehicle
            'registration': 'vehicle',
            'inspection': 'vehicle',
            'maintenance': 'vehicle',
            # Education
            'transcript': 'education',
            'diploma': 'education',
            'enrollment': 'education',
            # Kids/Family
            'sullivan': 'family',
            'school': 'family',
            'pediatric': 'family',
        }

        filename_lower = filename.lower().replace('.pdf', '').replace('_', ' ').replace('-', ' ')

        # Check filename for client
        for key, client_name in known_clients.items():
            if key in filename_lower:
                metadata['client'] = client_name
                metadata['domain'] = 'work'
                break

        # Check filename for work document type
        for key, doc_type in work_doc_types.items():
            if key in filename_lower:
                metadata['document_type'] = doc_type
                metadata['domain'] = 'work'
                break

        # Check filename for personal document type (if not already matched)
        if 'document_type' not in metadata:
            for key, doc_type in personal_doc_types.items():
                if key in filename_lower:
                    metadata['document_type'] = doc_type
                    metadata['domain'] = 'personal'
                    metadata['category'] = doc_type  # personal docs get a category
                    break

        # Analyze first page content for additional context
        first_page = content.split("--- Page 2 ---")[0] if "--- Page 2 ---" in content else content[:3000]
        first_page_lower = first_page.lower()

        # Check content for client mentions if not found in filename
        if 'client' not in metadata:
            for key, client_name in known_clients.items():
                if key in first_page_lower:
                    metadata['client'] = client_name
                    metadata['domain'] = 'work'
                    break

        # Check for Epic/healthcare context (common in Jeremy's work)
        healthcare_terms = ['epic', 'flowsheet', 'clindoc', 'emr', 'ehr', 'patient', 'clinical', 'nursing', 'physician', 'ambulatory', 'inpatient']
        if any(term in first_page_lower for term in healthcare_terms):
            metadata['domain'] = 'work'
            metadata['industry'] = 'healthcare'
            if 'epic' in first_page_lower:
                metadata['system'] = 'Epic'

        # Check for personal document indicators in content (if not already work)
        if metadata.get('domain') != 'work' and 'document_type' not in metadata:
            # Financial personal docs
            if any(term in first_page_lower for term in ['account statement', 'credit card', 'bank of america', 'chase', 'wells fargo', 'fidelity', 'vanguard', 'schwab', 'ira', '401k', 'brokerage']):
                metadata['domain'] = 'personal'
                metadata['category'] = 'financial'
            # Insurance docs
            elif any(term in first_page_lower for term in ['blue cross', 'aetna', 'cigna', 'united health', 'humana', 'explanation of benefits', 'deductible', 'copay', 'premium']):
                metadata['domain'] = 'personal'
                metadata['category'] = 'insurance'
            # Tax docs
            elif any(term in first_page_lower for term in ['internal revenue', 'irs', 'form 1040', 'form w-2', 'form 1099', 'tax return', 'turbotax', 'h&r block']):
                metadata['domain'] = 'personal'
                metadata['category'] = 'tax'
            # Medical docs
            elif any(term in first_page_lower for term in ['diagnosis', 'prescription', 'lab results', 'immunization record', 'medical record', 'hospital', 'pharmacy']):
                metadata['domain'] = 'personal'
                metadata['category'] = 'medical'
            # Travel docs
            elif any(term in first_page_lower for term in ['boarding pass', 'flight confirmation', 'hotel reservation', 'passport', 'united states of america', 'department of state']):
                metadata['domain'] = 'personal'
                metadata['category'] = 'travel'
            # Vehicle docs
            elif any(term in first_page_lower for term in ['vehicle registration', 'dmv', 'department of motor', 'vin', 'odometer', 'carfax']):
                metadata['domain'] = 'personal'
                metadata['category'] = 'vehicle'
            # Home docs
            elif any(term in first_page_lower for term in ['mortgage', 'deed of trust', 'property tax', 'homeowner', 'hoa', 'lease agreement', 'landlord', 'tenant']):
                metadata['domain'] = 'personal'
                metadata['category'] = 'home'

        # Extract potential title from first lines
        lines = first_page.replace("--- Page 1 ---\n", "").strip().split('\n')
        for line in lines[:5]:
            line = line.strip()
            # Title candidates: short, no punctuation at end, capitalized
            if 5 < len(line) < 100 and not line.endswith(('.', ',', ':')):
                if line[0].isupper():
                    metadata['title'] = line
                    break

        # Default domain to work if document looks professional
        if 'domain' not in metadata:
            work_indicators = ['confidential', 'proprietary', 'copyright', 'prepared by', 'submitted to', 'client', 'project']
            if any(ind in first_page_lower for ind in work_indicators):
                metadata['domain'] = 'work'
            else:
                metadata['domain'] = 'personal'

        return metadata

    async def ingest_pdf_to_memory(
        self,
        content: str,
        filename: str,
        user_id: Optional[int] = None,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest PDF content to Memory V2.

        Args:
            content: Extracted text content from PDF.
            filename: Original PDF filename.
            user_id: Telegram user ID.
            caption: Optional caption/context from user.

        Returns:
            Result dict with memory_id and status.
        """
        if not self.memory_service:
            logger.warning("Memory V2 not available, PDF content not persisted")
            return {"status": "skipped", "reason": "Memory V2 not available"}

        try:
            # Auto-extract metadata from filename and content
            auto_metadata = self._extract_pdf_metadata(filename, content)

            # Build metadata
            metadata = {
                "source": "telegram",
                "content_type": "pdf",
                "filename": filename,
                "user_id": str(user_id) if user_id else None,
                "timestamp": datetime.now().isoformat(),
                "type": "document",
                **auto_metadata,  # Merge auto-extracted metadata
            }

            if caption:
                metadata["caption"] = caption
                # If caption contains context clues, add them
                caption_lower = caption.lower()
                if any(kw in caption_lower for kw in ['client', 'work', 'project', 'meeting']):
                    metadata["domain"] = "work"
                elif any(kw in caption_lower for kw in ['personal', 'family', 'home']):
                    metadata["domain"] = "personal"

            # For large documents, chunk and store
            # Memory V2 handles embedding, so we just store the content
            MAX_CONTENT_LENGTH = 50000  # Reasonable limit for embedding

            if len(content) > MAX_CONTENT_LENGTH:
                # Store summary and reference
                summary_content = f"[PDF: {filename}]\n\n{content[:MAX_CONTENT_LENGTH]}\n\n[... {len(content) - MAX_CONTENT_LENGTH:,} more characters truncated]"
                metadata["truncated"] = True
                metadata["original_length"] = len(content)
                content_to_store = summary_content
            else:
                content_to_store = f"[PDF: {filename}]\n\n{content}"

            # Use add_document() for direct storage (bypasses mem0 fact extraction)
            result = self.memory_service.add_document(
                content=content_to_store,
                metadata=metadata
            )

            if result:
                logger.info(f"Ingested PDF to Memory V2: {filename} (metadata: {auto_metadata})")
                return {"status": "success", "result": result, "metadata": auto_metadata}
            else:
                return {"status": "failed", "reason": "Memory service returned no result"}

        except Exception as e:
            logger.error(f"PDF memory ingestion failed: {e}")
            return {"status": "error", "reason": str(e)}

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
                        "model": "anthropic/claude-3-5-haiku-20241022",
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
                    use_ai_classifier=False,  # Use Claude Code for interpretation, not API
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

                # Sync ALL brain dumps to WorkOS brain_dump table for visibility via life_get_brain_dump()
                # This includes personal_task, thoughts, ideas, worries - everything captured
                if self.workos_enabled:
                    workos_id = await self.sync_to_workos(entry)
                    if workos_id:
                        entry.routing_result['workos_brain_dump_id'] = workos_id
                        logger.info(f"Synced brain dump to WorkOS brain_dump #{workos_id}")

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

                # Sync to WorkOS even in fallback case
                if self.workos_enabled:
                    workos_id = await self.sync_to_workos(entry)
                    if workos_id:
                        if not entry.routing_result:
                            entry.routing_result = {}
                        entry.routing_result['workos_brain_dump_id'] = workos_id
                        logger.info(f"Synced brain dump to WorkOS brain_dump #{workos_id} (fallback)")

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
            from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
            from telegram.ext import (
                Application,
                CommandHandler,
                MessageHandler,
                CallbackQueryHandler,
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
                "• 📸 Photos (with text)\n"
                "• 📕 PDF documents\n\n"
                "I'll capture it, parse it, and add it to your brain dump queue.\n\n"
                "*Commands:*\n"
                "/help - Quick help + Drive ingest\n"
                "/menu - Quick action buttons\n"
                "/status - Quick status overview\n"
                "/health - Oura Ring health metrics\n"
                "/tasks - View active tasks\n"
                "/habits - View habits\n"
                "/dumps - View pending brain dumps\n"
                "/chat - Toggle chat mode (AI conversation)\n"
                "/ask <question> - One-shot AI query\n\n"
                "*Natural Language:*\n"
                "Ask \"what tasks do I have?\" or \"show my habits\"\n\n"
                "*Drive RAG Ingest:*\n"
                "Say \"ingest drive\" (default inbox)\n"
                "Or \"ingest drive into <name>\" to create/use a new folder/store",
                parse_mode='Markdown'
            )

        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed(update.effective_user.id):
                await update.message.reply_text("⛔ You are not authorized to use this bot.")
                return

            await update.message.reply_text(
                "🧭 *Thanos Help*\n\n"
                "*Drive RAG Ingest*\n"
                "• \"ingest drive\" → syncs default inbox\n"
                "• \"ingest drive into <name>\" → creates/uses a folder + store\n\n"
                "*Examples*\n"
                "ingest drive\n"
                "ingest drive into NCDHHS radiology\n\n"
                "*Other commands*\n"
                "/menu /status /health /tasks /habits /dumps /chat /ask",
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
            user_id = update.effective_user.id

            # Check if this is a command/query first
            command_type, params = self.detect_command(text)
            if command_type:
                response = await self.handle_command(command_type, params or {})
                await update.message.reply_text(response, parse_mode='Markdown')
                return

            # Chat mode - route through AI for full conversational response
            if self.is_chat_mode_enabled(user_id):
                # Show typing indicator while processing
                await update.message.chat.send_action('typing')

                # Get AI response via orchestrator
                response = await self.get_ai_response(text, user_id)

                # Send response (handle long messages)
                if len(response) > 4000:
                    # Split long messages
                    for i in range(0, len(response), 4000):
                        await update.message.reply_text(response[i:i+4000])
                else:
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
            """Handle document/file uploads (text files, PDFs, etc.)"""
            if not is_allowed(update.effective_user.id):
                return

            document = update.message.document
            file_name = document.file_name or "unknown"
            mime_type = document.mime_type or ""
            caption = update.message.caption or ""

            # Determine file type
            is_pdf = (
                file_name.lower().endswith('.pdf') or
                mime_type == 'application/pdf'
            )

            supported_text_extensions = ('.txt', '.md', '.text', '.log')
            supported_text_mimes = ('text/plain', 'text/markdown', 'text/x-markdown')

            is_text_file = (
                file_name.lower().endswith(supported_text_extensions) or
                mime_type in supported_text_mimes
            )

            if not is_text_file and not is_pdf:
                await update.message.reply_text(
                    f"📄 Received: {file_name}\n\n"
                    "Supported formats:\n"
                    "• Text files (.txt, .md)\n"
                    "• PDF documents (.pdf)\n\n"
                    "For other files, please copy and paste the content."
                )
                return

            # Download the file
            file = await context.bot.get_file(document.file_id)
            suffix = '.pdf' if is_pdf else '.txt'

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode='wb') as tmp:
                await file.download_to_drive(tmp.name)
                tmp_path = tmp.name

            try:
                # Send processing message
                processing_msg = await update.message.reply_text(
                    f"{'📕' if is_pdf else '📄'} Processing: {file_name}..."
                )

                # Extract content based on file type
                if is_pdf:
                    content, error = await self.extract_pdf_text(tmp_path)
                    if error:
                        await processing_msg.edit_text(
                            f"📕 *{file_name}*\n\n"
                            f"❌ {error}",
                            parse_mode='Markdown'
                        )
                        return
                else:
                    # Text file
                    with open(tmp_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()

                if not content or not content.strip():
                    await processing_msg.edit_text(f"{'📕' if is_pdf else '📄'} {file_name} is empty.")
                    return

                # For PDFs, ingest to Memory V2 and show different response
                if is_pdf:
                    # Ingest to memory
                    memory_result = await self.ingest_pdf_to_memory(
                        content=content,
                        filename=file_name,
                        user_id=update.effective_user.id,
                        caption=caption
                    )

                    # Count pages and words
                    page_count = content.count("--- Page ")
                    word_count = len(content.split())

                    # Build response
                    response_parts = [f"📕 *{file_name}*\n"]

                    # Stats
                    response_parts.append(f"📊 {page_count} pages | {word_count:,} words\n")

                    # Preview of content
                    preview_text = content.replace("--- Page 1 ---\n", "").strip()[:300]
                    preview_text = preview_text.replace('*', '').replace('_', '').replace('`', '')
                    if len(content) > 300:
                        preview_text += "..."
                    response_parts.append(f"```\n{preview_text}\n```\n")

                    # Memory status
                    if memory_result["status"] == "success":
                        response_parts.append("✅ Ingested to memory")

                        # Show detected metadata
                        detected = memory_result.get("metadata", {})
                        meta_parts = []
                        if detected.get("client"):
                            meta_parts.append(f"Client: {detected['client']}")
                        if detected.get("title"):
                            meta_parts.append(f"Title: {detected['title'][:40]}")
                        if detected.get("document_type"):
                            meta_parts.append(f"Type: {detected['document_type']}")
                        if detected.get("category"):
                            meta_parts.append(f"Category: {detected['category']}")
                        if detected.get("system"):
                            meta_parts.append(f"System: {detected['system']}")
                        if detected.get("domain"):
                            meta_parts.append(f"Domain: {detected['domain']}")

                        if meta_parts:
                            response_parts.append(f"🏷️ _{' | '.join(meta_parts)}_")

                        if caption:
                            response_parts.append(f"📝 Context: _{caption}_")
                    elif memory_result["status"] == "skipped":
                        response_parts.append("⚠️ Memory not available - content displayed only")
                    else:
                        response_parts.append(f"❌ Memory error: {memory_result.get('reason', 'unknown')}")

                    await processing_msg.edit_text("\n".join(response_parts), parse_mode='Markdown')
                    return

                # For text files, continue with existing brain dump pipeline
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

        async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle photo/image uploads with classification and storage."""
            if not is_allowed(update.effective_user.id):
                return

            # Get the largest photo size (Telegram sends multiple resolutions)
            photo = update.message.photo[-1]  # Last is highest resolution
            caption = update.message.caption or ""

            # Generate unique filename
            timestamp = datetime.now()
            date_str = timestamp.strftime("%Y%m%d_%H%M%S")
            photo_id = photo.file_unique_id[:8]
            filename = f"{date_str}_{photo_id}.jpg"

            # Setup photo storage
            photos_dir = Path(__file__).parent.parent / "State" / "photos"
            photos_dir.mkdir(parents=True, exist_ok=True)
            photo_path = photos_dir / filename
            metadata_path = photos_dir / f"{date_str}_{photo_id}.json"

            try:
                processing_msg = await update.message.reply_text("📷 Processing photo...")

                # Download photo
                file = await context.bot.get_file(photo.file_id)
                await file.download_to_drive(str(photo_path))

                # Classify photo based on caption keywords
                photo_type = self._classify_photo(caption)

                # Build metadata
                metadata = {
                    "id": photo.file_unique_id,
                    "filename": filename,
                    "timestamp": timestamp.isoformat(),
                    "user_id": str(update.effective_user.id),
                    "caption": caption,
                    "photo_type": photo_type,
                    "width": photo.width,
                    "height": photo.height,
                    "file_size": photo.file_size,
                    "processed": False,
                    "source": "telegram"
                }

                # Save metadata
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                logger.info(f"Photo saved: {filename} (type: {photo_type})")

                # Check if this is a calendar photo - flag for Claude Code processing
                caption_lower = caption.lower()
                is_calendar = any(kw in caption_lower for kw in ['calendar', 'schedule', 'event', 'appointment'])

                if is_calendar:
                    # Mark as needing calendar processing (Claude Code will handle via vision)
                    metadata['needs_calendar_processing'] = True
                    metadata['photo_type'] = 'calendar'

                    # Update metadata file
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)

                    await processing_msg.edit_text(
                        f"📅 *Calendar photo saved*\n\n"
                        f"📷 `{filename}`\n\n"
                        f"_Events will be extracted when you chat with Claude._",
                        parse_mode='Markdown'
                    )
                    return

                # Normal photo handling (non-calendar or extraction failed)
                entry = None
                if caption.strip():
                    entry = await self.capture_entry(
                        content=f"[PHOTO: {photo_type}] {caption}",
                        content_type='photo',
                        user_id=update.effective_user.id
                    )

                # Build response
                type_emoji = {
                    'receipt': '🧾',
                    'document': '📄',
                    'screenshot': '📱',
                    'whiteboard': '📋',
                    'note': '📝',
                    'personal': '📸',
                    'reference': '🔖',
                    'unknown': '🖼️'
                }.get(photo_type, '🖼️')

                response_parts = [f"{type_emoji} *Photo captured*"]
                response_parts.append(f"Type: {photo_type.title()}")
                response_parts.append(f"Size: {photo.width}x{photo.height}")

                if caption:
                    response_parts.append(f"\n📝 _{caption}_")

                if entry and entry.acknowledgment:
                    response_parts.append(f"\n{entry.acknowledgment}")

                if entry and entry.routing_result:
                    destinations = []
                    if entry.routing_result.get('tasks_created'):
                        destinations.append("task created")
                    if entry.routing_result.get('workos_task_id'):
                        destinations.append("synced to WorkOS")
                    if entry.routing_result.get('idea_created'):
                        destinations.append("idea saved")
                    if destinations:
                        response_parts.append(f"✓ {', '.join(destinations)}")

                response_parts.append(f"\n💾 Saved: `{filename}`")

                await processing_msg.edit_text("\n".join(response_parts), parse_mode='Markdown')

            except Exception as e:
                logger.error(f"Photo processing failed: {e}")
                await update.message.reply_text(f"❌ Error processing photo: {e}")

        async def handle_calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle calendar selection callbacks."""
            query = update.callback_query
            await query.answer()

            data = query.data
            if not data.startswith("cal_"):
                return

            parts = data.split("_", 2)
            if len(parts) < 3:
                return

            action = parts[1]  # work, personal, or skip
            events_key = f"cal_{parts[2]}"

            # Get stored events
            stored = context.bot_data.get(events_key)
            if not stored:
                await query.edit_message_text("⚠️ Session expired. Please send the photo again.")
                return

            if action == "skip":
                del context.bot_data[events_key]
                await query.edit_message_text("📷 Photo saved without adding to calendar.")
                return

            # Determine calendar ID
            calendar_id = "primary" if action == "personal" else os.getenv("GOOGLE_WORK_CALENDAR_ID", "primary")
            calendar_name = "Personal" if action == "personal" else "Work"

            try:
                # Create events in Google Calendar
                from Tools.adapters.google_calendar.legacy import GoogleCalendarAdapter
                adapter = GoogleCalendarAdapter()

                created_count = 0
                duplicate_skipped = 0
                duplicate_check_failed = 0
                duplicate_cache: Dict[tuple[str, str, str], Optional[List[Dict[str, Any]]]] = {}
                events = stored['events']

                def _normalize_summary(text: str) -> str:
                    cleaned = re.sub(r'[^a-z0-9\\s]+', ' ', (text or "").lower())
                    return re.sub(r'\\s+', ' ', cleaned).strip()

                def _parse_dt(value: Optional[str]) -> Optional[datetime]:
                    if not value or "T" not in value:
                        return None
                    try:
                        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        return None
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=ZoneInfo("America/New_York"))
                    return dt.astimezone(ZoneInfo("America/New_York"))

                def _parse_date(value: Optional[str]):
                    if not value or "T" in value:
                        return None
                    try:
                        return datetime.fromisoformat(value).date()
                    except ValueError:
                        return None

                async def _get_existing_events(start_date: str, end_date: str) -> Optional[List[Dict[str, Any]]]:
                    cache_key = (calendar_id, start_date, end_date)
                    if cache_key in duplicate_cache:
                        return duplicate_cache[cache_key]
                    result = await adapter._tool_get_events({
                        "start_date": start_date,
                        "end_date": end_date,
                        "calendar_id": calendar_id,
                        "include_cancelled": False,
                        "max_results": 50,
                        "single_events": True
                    })
                    if not result.success:
                        logger.warning(f"Duplicate check failed: {result.error}")
                        duplicate_cache[cache_key] = None
                        return None
                    events_list = result.data.get("events", []) if result.data else []
                    duplicate_cache[cache_key] = events_list
                    return events_list

                def _is_duplicate(existing_events: List[Dict[str, Any]], new_summary: str, new_start: str, new_all_day: bool) -> bool:
                    norm_new = _normalize_summary(new_summary)
                    if not norm_new:
                        return False
                    if new_all_day:
                        new_date = _parse_date(new_start)
                        if not new_date:
                            return False
                        for existing in existing_events:
                            if not existing.get("is_all_day"):
                                continue
                            if _normalize_summary(existing.get("summary", "")) != norm_new:
                                continue
                            existing_date = _parse_date(existing.get("start"))
                            if existing_date and existing_date == new_date:
                                return True
                        return False

                    new_dt = _parse_dt(new_start)
                    if not new_dt:
                        return False
                    for existing in existing_events:
                        if existing.get("is_all_day"):
                            continue
                        if _normalize_summary(existing.get("summary", "")) != norm_new:
                            continue
                        existing_dt = _parse_dt(existing.get("start"))
                        if existing_dt and abs((existing_dt - new_dt).total_seconds()) <= 300:
                            return True
                    return False

                for event_data in events:
                    try:
                        # Build event for Google Calendar
                        from Tools.photo_processors import ExtractedEvent
                        event = ExtractedEvent(**event_data)
                        gcal_event = event.to_gcal_format()

                        # Create the event
                        start_value = gcal_event["start"].get("dateTime", gcal_event["start"].get("date"))
                        end_value = gcal_event["end"].get("dateTime", gcal_event["end"].get("date"))
                        if action == "work" and start_value and end_value:
                            existing = await _get_existing_events(start_value, end_value)
                            if existing is None:
                                duplicate_check_failed += 1
                                continue
                            is_all_day = "date" in gcal_event.get("start", {}) and "dateTime" not in gcal_event.get("start", {})
                            if _is_duplicate(existing, gcal_event.get("summary", ""), start_value, is_all_day):
                                duplicate_skipped += 1
                                continue

                        result = await adapter._tool_create_event({
                            "summary": gcal_event["summary"],
                            "start_time": start_value,
                            "end_time": end_value,
                            "calendar_id": calendar_id,
                            "description": gcal_event.get("description", ""),
                            "location": gcal_event.get("location", "")
                        })

                        if result.success:
                            created_count += 1
                        else:
                            logger.warning(f"Failed to create event: {result.error}")

                    except Exception as e:
                        logger.error(f"Error creating event: {e}")

                # Cleanup
                del context.bot_data[events_key]

                if created_count > 0:
                    extra = []
                    if duplicate_skipped > 0:
                        extra.append(f"⏭️ Skipped {duplicate_skipped} duplicate(s)")
                    if duplicate_check_failed > 0:
                        extra.append(f"⚠️ Skipped {duplicate_check_failed} event(s) (duplicate check failed)")
                    suffix = "\n" + "\n".join(extra) if extra else ""
                    await query.edit_message_text(
                        f"✅ Added {created_count} event(s) to {calendar_name} calendar!{suffix}"
                    )
                else:
                    if duplicate_skipped > 0 or duplicate_check_failed > 0:
                        parts = []
                        if duplicate_skipped > 0:
                            parts.append(f"⏭️ Skipped {duplicate_skipped} duplicate(s)")
                        if duplicate_check_failed > 0:
                            parts.append(f"⚠️ Skipped {duplicate_check_failed} event(s) (duplicate check failed)")
                        await query.edit_message_text("\n".join(parts))
                    else:
                        await query.edit_message_text(
                            f"⚠️ Could not add events to calendar. Please add them manually."
                        )

            except ImportError:
                await query.edit_message_text("❌ Google Calendar adapter not available.")
            except Exception as e:
                logger.error(f"Calendar creation failed: {e}")
                await query.edit_message_text(f"❌ Error: {e}")

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

        async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Toggle chat mode - when enabled, all messages get AI responses."""
            if not is_allowed(update.effective_user.id):
                return

            user_id = update.effective_user.id
            new_state = self.toggle_chat_mode(user_id)

            if new_state:
                await update.message.reply_text(
                    "💬 *Chat mode enabled*\n\n"
                    "All your messages will now get AI responses.\n"
                    "Use /chat again to return to brain dump mode.\n\n"
                    "_Tip: Use /ask <question> for one-off questions without enabling chat mode._",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "📝 *Brain dump mode restored*\n\n"
                    "Messages will be captured as thoughts/tasks.\n"
                    "Use /chat to enable conversational mode.",
                    parse_mode='Markdown'
                )

        async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """One-shot AI query without enabling chat mode."""
            if not is_allowed(update.effective_user.id):
                return

            user_id = update.effective_user.id

            # Get the question (everything after /ask)
            question = ' '.join(context.args) if context.args else None

            if not question:
                await update.message.reply_text(
                    "❓ *Usage:* `/ask <your question>`\n\n"
                    "Example: `/ask What should I prioritize today?`",
                    parse_mode='Markdown'
                )
                return

            # Show typing indicator
            await update.message.chat.send_action('typing')

            # Get AI response
            response = await self.get_ai_response(question, user_id)

            # Send response
            if len(response) > 4000:
                for i in range(0, len(response), 4000):
                    await update.message.reply_text(response[i:i+4000])
            else:
                await update.message.reply_text(response, parse_mode='Markdown')

        async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Display main quick action menu with inline buttons."""
            if not is_allowed(update.effective_user.id):
                await update.message.reply_text("⛔ You are not authorized to use this bot.")
                return

            # Create quick action buttons
            keyboard = self._build_inline_keyboard([
                [("🧠 Brain Dump", "menu_braindump")],
                [("⚡ Log Energy", "menu_energy")],
                [("📋 View Tasks", "menu_tasks")]
            ])

            await update.message.reply_text(
                "🎯 *Quick Actions*\n\n"
                "Choose an action below:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle menu quick action button callbacks."""
            query = update.callback_query
            await query.answer()

            action = query.data.split("_", 1)[1] if "_" in query.data else ""

            if action == "braindump":
                # Prompt user to send a brain dump
                await query.edit_message_text(
                    "🧠 *Brain Dump Mode*\n\n"
                    "Just send me your thoughts as:\n"
                    "• 📝 Text message\n"
                    "• 🎤 Voice message\n"
                    "• 📸 Photo with caption\n\n"
                    "I'll capture and process it for you.\n\n"
                    "_Send /menu to return to quick actions._",
                    parse_mode='Markdown'
                )

            elif action == "energy":
                # Show energy level selection (placeholder for now)
                await query.edit_message_text(
                    "⚡ *Log Energy*\n\n"
                    "Energy logging will be available soon.\n"
                    "This will let you quickly log your current energy level.\n\n"
                    "_Send /menu to return to quick actions._",
                    parse_mode='Markdown'
                )

            elif action == "tasks":
                # Show tasks
                await query.edit_message_text(
                    "📋 *Loading tasks...*",
                    parse_mode='Markdown'
                )
                response = await self._get_tasks_response('active')
                await query.edit_message_text(
                    response,
                    parse_mode='Markdown'
                )

        # Register callback handlers with unified routing system
        self._register_callback_handler("cal_", handle_calendar_callback)
        self._register_callback_handler("menu_", handle_menu_callback)

        # Register handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("status", status_command))
        self.application.add_handler(CommandHandler("menu", menu_command))
        self.application.add_handler(CommandHandler("tasks", tasks_command))
        self.application.add_handler(CommandHandler("habits", habits_command))
        self.application.add_handler(CommandHandler("dumps", dumps_command))
        self.application.add_handler(CommandHandler("health", health_command))
        self.application.add_handler(CommandHandler("chat", chat_command))
        self.application.add_handler(CommandHandler("ask", ask_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        self.application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        self.application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        self.application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

        # Unified callback router - handles all button callbacks
        self.application.add_handler(CallbackQueryHandler(self._route_callback))

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
