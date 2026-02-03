#!/usr/bin/env python3
"""
Telegram Channel Implementation - Wraps existing telegram_bot.py.

Provides the Channel interface for Telegram integration.
"""

import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, AsyncIterator, Dict, Any

from .base import Channel, ChannelConfig, ChannelType, Message, MessageType

logger = logging.getLogger(__name__)

# Check for telegram library
try:
    from telegram import Update, Bot
    from telegram.ext import Application, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed. Telegram channel unavailable.")


class TelegramChannel(Channel):
    """
    Telegram channel implementation.

    Wraps python-telegram-bot library with the unified Channel interface.
    """

    def __init__(self, config: ChannelConfig):
        """
        Initialize Telegram channel.

        Args:
            config: Channel configuration (needs token and default_recipient)
        """
        super().__init__(config)

        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot not installed")

        self.token = config.token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("Telegram bot token not configured")

        self.bot: Optional[Bot] = None
        self.app: Optional[Application] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._polling_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """
        Connect to Telegram.

        Returns:
            True if connected successfully
        """
        try:
            self.bot = Bot(token=self.token)
            # Verify connection
            me = await self.bot.get_me()
            logger.info(f"Connected to Telegram as @{me.username}")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        if self._polling_task:
            self._polling_task.cancel()
            self._polling_task = None

        if self.app:
            await self.app.stop()
            await self.app.shutdown()

        self._connected = False
        logger.info("Disconnected from Telegram")

    async def send(
        self,
        content: str,
        recipient: Optional[str] = None,
        reply_to: Optional[str] = None,
        parse_mode: str = "Markdown",
        **kwargs
    ) -> Optional[Message]:
        """
        Send a text message via Telegram.

        Args:
            content: Message text
            recipient: Chat ID (uses default if None)
            reply_to: Message ID to reply to
            parse_mode: "Markdown", "HTML", or None
            **kwargs: Additional telegram options

        Returns:
            Sent Message object
        """
        if not self.bot:
            logger.error("Not connected to Telegram")
            return None

        chat_id = recipient or self.config.default_recipient
        if not chat_id:
            logger.error("No recipient specified and no default configured")
            return None

        try:
            # Send message
            result = await self.bot.send_message(
                chat_id=chat_id,
                text=content,
                parse_mode=parse_mode,
                reply_to_message_id=int(reply_to) if reply_to else None,
                **kwargs
            )

            return Message(
                id=str(result.message_id),
                channel_type=ChannelType.TELEGRAM,
                channel_id=str(chat_id),
                content=content,
                timestamp=datetime.now(),
                is_from_bot=True,
                raw_data={"telegram_message": result.to_dict()}
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return None

    async def send_media(
        self,
        media_path: str,
        caption: Optional[str] = None,
        recipient: Optional[str] = None,
        media_type: str = "auto",
        **kwargs
    ) -> Optional[Message]:
        """
        Send media via Telegram.

        Args:
            media_path: Path to media file
            caption: Optional caption
            recipient: Chat ID
            media_type: "auto", "photo", "document", "audio", "video"
            **kwargs: Additional options

        Returns:
            Sent Message object
        """
        if not self.bot:
            return None

        chat_id = recipient or self.config.default_recipient
        if not chat_id:
            return None

        try:
            # Detect media type if auto
            if media_type == "auto":
                ext = media_path.lower().split(".")[-1]
                if ext in ("jpg", "jpeg", "png", "gif", "webp"):
                    media_type = "photo"
                elif ext in ("mp4", "avi", "mov", "webm"):
                    media_type = "video"
                elif ext in ("mp3", "ogg", "wav", "m4a"):
                    media_type = "audio"
                else:
                    media_type = "document"

            with open(media_path, "rb") as f:
                if media_type == "photo":
                    result = await self.bot.send_photo(
                        chat_id=chat_id, photo=f, caption=caption, **kwargs
                    )
                elif media_type == "video":
                    result = await self.bot.send_video(
                        chat_id=chat_id, video=f, caption=caption, **kwargs
                    )
                elif media_type == "audio":
                    result = await self.bot.send_audio(
                        chat_id=chat_id, audio=f, caption=caption, **kwargs
                    )
                else:
                    result = await self.bot.send_document(
                        chat_id=chat_id, document=f, caption=caption, **kwargs
                    )

            return Message(
                id=str(result.message_id),
                channel_type=ChannelType.TELEGRAM,
                channel_id=str(chat_id),
                content=caption or "",
                message_type=MessageType.IMAGE if media_type == "photo" else MessageType.DOCUMENT,
                timestamp=datetime.now(),
                is_from_bot=True,
                media_url=media_path,
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram media: {e}")
            return None

    async def send_typing(self, recipient: Optional[str] = None) -> None:
        """Send typing indicator."""
        if not self.bot:
            return

        chat_id = recipient or self.config.default_recipient
        if chat_id:
            try:
                await self.bot.send_chat_action(chat_id=chat_id, action="typing")
            except Exception:
                pass

    async def receive(self) -> AsyncIterator[Message]:
        """
        Receive messages using polling.

        Yields:
            Incoming Message objects
        """
        if not self.bot:
            return

        # Build application for updates
        self.app = Application.builder().token(self.token).build()

        # Handler to queue messages
        async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.message:
                msg = self._convert_update(update)
                if msg and self.is_sender_allowed(msg.sender_id or ""):
                    await self._message_queue.put(msg)

        self.app.add_handler(MessageHandler(
            filters.TEXT | filters.VOICE | filters.PHOTO | filters.Document.ALL,
            message_handler
        ))

        # Start polling in background
        await self.app.initialize()
        await self.app.start()
        self._polling_task = asyncio.create_task(self.app.updater.start_polling())

        # Yield messages from queue
        while self._connected:
            try:
                msg = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                yield msg
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    def _convert_update(self, update: Update) -> Optional[Message]:
        """
        Convert Telegram Update to unified Message.

        Args:
            update: Telegram Update object

        Returns:
            Unified Message object
        """
        if not update.message:
            return None

        tg_msg = update.message

        # Determine message type
        if tg_msg.voice:
            msg_type = MessageType.VOICE
            content = "[Voice message]"
        elif tg_msg.photo:
            msg_type = MessageType.IMAGE
            content = tg_msg.caption or "[Photo]"
        elif tg_msg.document:
            msg_type = MessageType.DOCUMENT
            content = tg_msg.caption or f"[Document: {tg_msg.document.file_name}]"
        else:
            msg_type = MessageType.TEXT
            content = tg_msg.text or ""

        return Message(
            id=str(tg_msg.message_id),
            channel_type=ChannelType.TELEGRAM,
            channel_id=str(tg_msg.chat_id),
            content=content,
            message_type=msg_type,
            timestamp=tg_msg.date,
            sender_id=str(tg_msg.from_user.id) if tg_msg.from_user else None,
            sender_name=tg_msg.from_user.username if tg_msg.from_user else None,
            reply_to_id=str(tg_msg.reply_to_message.message_id) if tg_msg.reply_to_message else None,
            raw_data={"telegram_update": update.to_dict()}
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check Telegram connection health."""
        base = await super().health_check()

        if self.bot:
            try:
                me = await self.bot.get_me()
                base["bot_username"] = me.username
                base["bot_id"] = me.id
            except Exception as e:
                base["error"] = str(e)

        return base


# =========================================================================
# Convenience functions for quick sending
# =========================================================================

async def send_telegram(
    message: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "Markdown"
) -> bool:
    """
    Quick function to send a Telegram message.

    Uses environment variables for configuration.

    Args:
        message: Text to send
        chat_id: Target chat (uses TELEGRAM_DEFAULT_CHAT_ID if None)
        parse_mode: Markdown or HTML

    Returns:
        True if sent successfully
    """
    def _load_env_fallback() -> None:
        env_path = Path(__file__).parent.parent.parent / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key not in os.environ:
                os.environ[key] = value

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_DEFAULT_CHAT_ID")
    if not token or not chat_id:
        _load_env_fallback()
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = chat_id or os.getenv("TELEGRAM_DEFAULT_CHAT_ID")
    if not chat_id:
        allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        if allowed:
            chat_id = allowed.split(",")[0].strip()

    if not token or not chat_id:
        logger.error("Telegram not configured (missing token or chat_id)")
        return False

    config = ChannelConfig(
        channel_type=ChannelType.TELEGRAM,
        token=token,
        default_recipient=chat_id
    )

    channel = TelegramChannel(config)
    if await channel.connect():
        result = await channel.send(message, parse_mode=parse_mode)
        return result is not None

    return False


def send_telegram_sync(message: str, chat_id: Optional[str] = None) -> bool:
    """
    Synchronous wrapper for send_telegram.

    Args:
        message: Text to send
        chat_id: Target chat

    Returns:
        True if sent successfully
    """
    return asyncio.run(send_telegram(message, chat_id))
