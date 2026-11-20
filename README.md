# 🎬 ClipForge AI

> Automated Twitch clip detection, editing, and multi-platform publishing pipeline.

ClipForge AI monitors Twitch streamers for chat activity spikes, automatically creates clips at peak moments, edits them into viral-ready Shorts (9:16, animated captions, SFX), stores them on Google Drive, and lets you review + publish to YouTube Shorts and Instagram Reels with one click.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│          PHASE 1 — Cloud Watcher (24/7)         │
│  Twitch Helix API  →  Chat Spike Detector       │
│  → Clip Created    →  Saved to Google Drive     │
│  → Telegram Bot notifies you with inline buttons│
└─────────────────────────────────────────────────┘
                        ↓ (you approve)
┌─────────────────────────────────────────────────┐
│       PHASE 2 — Local Editing & Publishing      │
│  Google Drive sync  →  Review UI (Streamlit)    │
│  → AI Edit (FFmpeg + Whisper captions + SFX)    │
│  → Preview & Approve  →  Upload to platforms   │
└─────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
clipforge-ai/
├── watcher/                  # Phase 1: 24/7 Cloud Watcher
│   ├── twitch_monitor.py     # Twitch EventSub / IRC chat listener
│   ├── spike_detector.py     # Real-time chat velocity spike detection
│   ├── clip_creator.py       # Twitch Helix API clip creator
│   ├── drive_uploader.py     # Google Drive uploader
│   └── telegram_bot.py       # Telegram notification & control bot
│
├── editor/                   # Phase 2: AI Video Editor
│   ├── video_editor.py       # FFmpeg-based 9:16 reformatter
│   ├── caption_engine.py     # Whisper transcription + animated .ASS captions
│   ├── sfx_engine.py         # Sound effect layering engine
│   └── sfx/                  # Local SFX library (whoosh, vine_boom, etc.)
│
├── publisher/                # Phase 2: Platform Publisher
│   ├── youtube_uploader.py   # YouTube Data API v3 uploader
│   ├── instagram_uploader.py # Instagram Graph API uploader
│   └── scheduler.py          # Drip posting scheduler
│
├── ui/                       # Phase 2: Local Review Dashboard
│   └── dashboard.py          # Streamlit review + approve + publish UI
│
├── config/
│   └── settings.py           # Centralised config (channel list, thresholds)
│
├── .env.example              # Environment variable template
├── requirements.txt          # Python dependencies
├── deploy.sh                 # VPS deployment script (Linux)
└── README.md
```

---

## ⚙️ Setup

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/clipforge-ai.git
cd clipforge-ai
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys (see below)
```

### 3. Required API Keys
| Service | Where to Get |
|---|---|
| `TWITCH_CLIENT_ID` | [dev.twitch.tv](https://dev.twitch.tv) |
| `TWITCH_CLIENT_SECRET` | Twitch Developer Console |
| `TWITCH_USER_TOKEN` | OAuth with `clips:edit` scope |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_ID` | Your personal Telegram user ID |
| `GOOGLE_CREDENTIALS_JSON` | Google Cloud Console → Service Account |
| `YOUTUBE_CLIENT_SECRET_JSON` | Google Cloud Console → OAuth 2.0 |

---

## 🚀 Running the Pipeline

### Start the Watcher (Phase 1)
```bash
python watcher/twitch_monitor.py
```

### Start the Editing Dashboard (Phase 2)
```bash
streamlit run ui/dashboard.py
```

---

## 🔄 Workflow

1. **Watcher** polls Twitch for live streamers in your watchlist.
2. When a streamer goes live → **Telegram alert** with `[Monitor]` / `[Ignore]` buttons.
3. If you tap **Monitor** → Chat spike detector activates for that channel.
4. Chat spike detected → Twitch clip created → Raw MP4 saved to **Google Drive**.
5. **Telegram notification** with clip preview link.
6. Open the **local dashboard** → clip appears in Inbox.
7. Click **AI Edit** → 9:16 vertical, animated captions, hook SFX applied.
8. **Preview** the clip, approve it.
9. Click **Publish** → posts to YouTube Shorts + Instagram Reels on a drip schedule.

---

## 📋 Requirements
- Python 3.10+
- FFmpeg (must be in PATH)
- A Twitch Developer App
- A Telegram Bot (via BotFather)
- Google Cloud Project (Drive API + YouTube Data API v3)
