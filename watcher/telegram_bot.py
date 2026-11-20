"""
ClipForge AI — Telegram Bot
Sends live alerts and receives inline button commands from you.
"""

import os
import sys
import asyncio
from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    CommandHandler,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramNotifier:
    """Sends messages and inline buttons to your Telegram chat."""

    def __init__(self):
        self._app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self._monitor_callbacks: dict[str, callable] = {}

    # ─── Sending Notifications ────────────────────────────────────────────────

    async def send_live_alert(self, channel: str, game: str, viewers: int):
        """Alert: streamer just went live. Ask if we should monitor."""
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🎬 Monitor for Clips",
                    callback_data=f"monitor:{channel}"
                ),
                InlineKeyboardButton(
                    "❌ Ignore",
                    callback_data=f"ignore:{channel}"
                ),
            ]
        ])
        text = (
            f"🔴 *{channel}* is LIVE!\n"
            f"🎮 Playing: *{game}*\n"
            f"👥 Viewers: {viewers:,}\n\n"
            f"Should I monitor for clip-worthy moments?"
        )
        await self._app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        logger.info(f"[Telegram] Live alert sent for {channel}")

    async def send_clip_ready(
        self,
        channel: str,
        game: str,
        clip_url: str,
        drive_url: str,
        clip_id: str,
    ):
        """Notify that a clip was captured and uploaded to Drive."""
        text = (
            f"✂️ *Clip captured!*\n\n"
            f"📺 Streamer: *{channel}*\n"
            f"🎮 Game: *{game}*\n"
            f"🆔 Clip ID: `{clip_id}`\n\n"
            f"🔗 [Watch on Twitch]({clip_url})\n"
            f"💾 [Open in Drive]({drive_url})\n\n"
            f"_Open the ClipForge dashboard to edit and publish._"
        )
        await self._app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown",
        )
        logger.info(f"[Telegram] Clip-ready notification sent for {channel}")

    async def send_message(self, text: str):
        """Send a plain text message."""
        await self._app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="Markdown"
        )

    # ─── Receiving Button Callbacks ───────────────────────────────────────────

    def register_monitor_callback(self, channel: str, callback: callable):
        """Register a function to call when user taps 'Monitor' for `channel`."""
        self._monitor_callbacks[channel.lower()] = callback

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        action, channel = query.data.split(":", 1)
        channel = channel.lower()

        if action == "monitor":
            await query.edit_message_text(
                f"✅ Monitoring *{channel}* for chat spikes...",
                parse_mode="Markdown",
            )
            cb = self._monitor_callbacks.get(channel)
            if cb:
                asyncio.create_task(asyncio.to_thread(cb, channel))
        elif action == "ignore":
            await query.edit_message_text(f"⏭️ Ignoring stream from *{channel}*.", parse_mode="Markdown")

    # ─── Bot Lifecycle ────────────────────────────────────────────────────────

    def run(self):
        """Start the bot's polling loop (blocking)."""
        self._app.add_handler(CallbackQueryHandler(self._handle_callback))
        logger.info("[Telegram] Bot polling started...")
        self._app.run_polling()
