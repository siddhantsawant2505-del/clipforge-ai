"""
ClipForge AI — Main Twitch Monitor (Entry Point for Phase 1)

Polls Twitch for live streamers in the watchlist, sends Telegram alerts,
and launches per-channel spike detectors on demand.

Usage:
    python watcher/twitch_monitor.py
"""

import os
import sys
import time
import requests
import threading
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    TWITCH_CLIENT_ID,
    TWITCH_USER_TOKEN,
    TWITCH_API_BASE,
    WATCHLIST,
    RAW_CLIPS_DIR,
)
from watcher.spike_detector import SpikeDetector
from watcher.clip_creator import ClipCreator
from watcher.drive_uploader import DriveUploader
from watcher.telegram_bot import TelegramNotifier

import asyncio


# ─── State ───────────────────────────────────────────────────────────────────

active_detectors: dict[str, SpikeDetector] = {}
previously_live:  set[str] = set()

headers = {
    "Client-Id": TWITCH_CLIENT_ID,
    "Authorization": f"Bearer {TWITCH_USER_TOKEN}",
}

clip_creator  = ClipCreator()
drive_uploader = DriveUploader()
notifier      = TelegramNotifier()


# ─── Spike Handler ───────────────────────────────────────────────────────────

def handle_spike(channel: str):
    """Called by SpikeDetector when a chat velocity spike is detected."""
    logger.info(f"[Monitor] Spike handler triggered for #{channel}")

    metadata = clip_creator.create_clip(channel)
    if not metadata:
        logger.error(f"[Monitor] Clip creation failed for #{channel}")
        return

    # Download the MP4 (yt-dlp or requests)
    local_path = _download_clip(metadata["clip_url"], metadata["clip_id"])
    if not local_path:
        return

    # Upload to Google Drive
    drive_url = drive_uploader.upload(local_path, metadata)

    # Notify via Telegram
    asyncio.run(
        notifier.send_clip_ready(
            channel   = channel,
            game      = metadata["game"],
            clip_url  = metadata["clip_url"],
            drive_url = drive_url,
            clip_id   = metadata["clip_id"],
        )
    )


def _download_clip(url: str, clip_id: str) -> str | None:
    """Download a Twitch clip MP4 to the local raw clips directory."""
    if not url:
        logger.warning("[Monitor] No clip URL to download.")
        return None

    out_path = os.path.join(RAW_CLIPS_DIR, f"{clip_id}.mp4")
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.success(f"[Monitor] Downloaded clip → {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"[Monitor] Failed to download clip: {e}")
        return None


# ─── Activation via Telegram ─────────────────────────────────────────────────

def start_monitoring(channel: str):
    """Activate spike detection for a channel (called from Telegram button)."""
    if channel in active_detectors:
        logger.warning(f"[Monitor] Already monitoring #{channel}")
        return

    detector = SpikeDetector(channel=channel, on_spike=handle_spike)
    active_detectors[channel] = detector
    detector.start()
    logger.success(f"[Monitor] ✅ Spike detection active for #{channel}")


# ─── Live Poller ──────────────────────────────────────────────────────────────

def poll_live_streams():
    """Poll Twitch every 60s to check if watchlist streamers are live."""
    if not WATCHLIST:
        logger.warning("[Monitor] WATCHLIST is empty. Add streamers to .env")
        return

    url = f"{TWITCH_API_BASE}/streams"
    params = [("user_login", name) for name in WATCHLIST]

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        live_streams = resp.json().get("data", [])
    except Exception as e:
        logger.error(f"[Monitor] Polling error: {e}")
        return

    live_now = {s["user_login"].lower() for s in live_streams}

    # Newly live channels
    for stream in live_streams:
        channel = stream["user_login"].lower()
        if channel not in previously_live:
            logger.info(f"[Monitor] 🟢 {channel} just went live!")
            notifier.register_monitor_callback(channel, start_monitoring)
            asyncio.run(
                notifier.send_live_alert(
                    channel = channel,
                    game    = stream.get("game_name", "Unknown"),
                    viewers = stream.get("viewer_count", 0),
                )
            )

    # Channels that went offline — stop detectors
    for channel in previously_live - live_now:
        logger.info(f"[Monitor] 🔴 {channel} went offline.")
        if channel in active_detectors:
            active_detectors[channel].stop()
            del active_detectors[channel]

    previously_live.clear()
    previously_live.update(live_now)


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.add(
        os.path.join(os.path.dirname(__file__), "..", "logs", "monitor.log"),
        rotation="10 MB",
        retention="7 days",
        level="INFO",
    )
    logger.info("🚀 ClipForge AI — Watcher starting up...")
    logger.info(f"Watchlist: {WATCHLIST}")

    # Start Telegram bot in a background thread
    bot_thread = threading.Thread(target=notifier.run, daemon=True)
    bot_thread.start()

    # Main polling loop
    while True:
        poll_live_streams()
        logger.debug("[Monitor] Sleeping 60s before next poll...")
        time.sleep(60)
