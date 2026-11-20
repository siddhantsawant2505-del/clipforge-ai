"""
ClipForge AI — Centralised Settings & Configuration
All environment variables are loaded here. Import this module across the project.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Twitch ─────────────────────────────────────────────────────────────────
TWITCH_CLIENT_ID     = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "")
TWITCH_USER_TOKEN    = os.getenv("TWITCH_USER_TOKEN", "")
TWITCH_IRC_HOST      = "irc.chat.twitch.tv"
TWITCH_IRC_PORT      = 6667
TWITCH_API_BASE      = "https://api.twitch.tv/helix"

# ─── Telegram ────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

# ─── Google Drive ────────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_JSON  = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
GOOGLE_DRIVE_FOLDER_ID   = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# ─── YouTube ─────────────────────────────────────────────────────────────────
YOUTUBE_CLIENT_SECRET_JSON = os.getenv("YOUTUBE_CLIENT_SECRET_JSON", "youtube_secret.json")
YOUTUBE_SCOPES             = ["https://www.googleapis.com/auth/youtube.upload"]

# ─── Instagram ───────────────────────────────────────────────────────────────
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.getenv("INSTAGRAM_USER_ID", "")

# ─── Clip / Spike Settings ───────────────────────────────────────────────────
# How long (seconds) a clip should be when created via Twitch API
CLIP_DURATION = int(os.getenv("CLIP_DURATION", 30))

# A spike is detected when messages-per-window exceed SPIKE_THRESHOLD × rolling average
SPIKE_THRESHOLD = float(os.getenv("SPIKE_THRESHOLD", 3.0))

# Sliding window (seconds) used to measure chat velocity
SPIKE_WINDOW_SECONDS = int(os.getenv("SPIKE_WINDOW_SECONDS", 10))

# Minimum seconds between successive clip triggers (cooldown)
CLIP_COOLDOWN_SECONDS = 90

# Comma-separated list of Twitch usernames to watch
WATCHLIST: list[str] = [
    s.strip().lower()
    for s in os.getenv("WATCHLIST", "").split(",")
    if s.strip()
]

# ─── Posting Schedule (IST) ──────────────────────────────────────────────────
# Clips will be queued and drip-posted at these times (IST, 24h format)
POSTING_TIMES_IST: list[str] = [
    t.strip()
    for t in os.getenv("POSTING_TIMES_IST", "14:00,18:00,21:00").split(",")
    if t.strip()
]

# ─── Paths ───────────────────────────────────────────────────────────────────
RAW_CLIPS_DIR    = os.path.join(os.path.dirname(__file__), "..", "clips", "raw")
EDITED_CLIPS_DIR = os.path.join(os.path.dirname(__file__), "..", "clips", "edited")
SFX_DIR          = os.path.join(os.path.dirname(__file__), "..", "editor", "sfx")
LOGS_DIR         = os.path.join(os.path.dirname(__file__), "..", "logs")

# Create directories if they don't exist
for _dir in [RAW_CLIPS_DIR, EDITED_CLIPS_DIR, SFX_DIR, LOGS_DIR]:
    os.makedirs(_dir, exist_ok=True)
