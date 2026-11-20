"""
ClipForge AI — Twitch Clip Creator
Uses the Twitch Helix API to create a clip immediately after a spike.
"""

import requests
import time
import os
import sys
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    TWITCH_CLIENT_ID,
    TWITCH_USER_TOKEN,
    TWITCH_API_BASE,
    CLIP_DURATION,
)


class ClipCreator:
    """Handles Twitch API authentication and clip creation."""

    def __init__(self):
        self._headers = {
            "Client-Id": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {TWITCH_USER_TOKEN}",
        }

    def get_broadcaster_id(self, username: str) -> str | None:
        """Resolve a Twitch username to its broadcaster user ID."""
        url = f"{TWITCH_API_BASE}/users"
        resp = requests.get(url, headers=self._headers, params={"login": username})
        if resp.ok and resp.json().get("data"):
            return resp.json()["data"][0]["id"]
        logger.error(f"[ClipCreator] Could not resolve user ID for '{username}'")
        return None

    def get_stream_info(self, username: str) -> dict | None:
        """Fetch current stream info (title, game, viewer count)."""
        url = f"{TWITCH_API_BASE}/streams"
        resp = requests.get(url, headers=self._headers, params={"user_login": username})
        if resp.ok and resp.json().get("data"):
            return resp.json()["data"][0]
        return None

    def create_clip(self, channel: str) -> dict | None:
        """
        Create a Twitch clip for `channel`.
        Returns clip metadata dict (id, url, edit_url) or None on failure.
        """
        broadcaster_id = self.get_broadcaster_id(channel)
        if not broadcaster_id:
            return None

        url = f"{TWITCH_API_BASE}/clips"
        params = {
            "broadcaster_id": broadcaster_id,
            "has_delay": "false",
        }

        resp = requests.post(url, headers=self._headers, params=params)

        if not resp.ok:
            logger.error(
                f"[ClipCreator] Failed to create clip for '{channel}': "
                f"{resp.status_code} — {resp.text}"
            )
            return None

        clip_data = resp.json().get("data", [{}])[0]
        clip_id = clip_data.get("id", "")
        edit_url = clip_data.get("edit_url", "")

        logger.success(
            f"[ClipCreator] ✅ Clip created for #{channel}: "
            f"ID={clip_id}  edit_url={edit_url}"
        )

        # Twitch needs ~20s to process the clip before the MP4 is ready
        logger.info("[ClipCreator] Waiting 25s for Twitch to process clip...")
        time.sleep(25)

        # Fetch the final clip URL
        clip_url = self._fetch_clip_url(clip_id)
        stream_info = self.get_stream_info(channel)

        return {
            "clip_id": clip_id,
            "edit_url": edit_url,
            "clip_url": clip_url,
            "channel": channel,
            "game": stream_info.get("game_name", "Unknown") if stream_info else "Unknown",
            "stream_title": stream_info.get("title", "") if stream_info else "",
            "viewer_count": stream_info.get("viewer_count", 0) if stream_info else 0,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def _fetch_clip_url(self, clip_id: str) -> str:
        """Fetch the direct thumbnail/clip URL after processing."""
        url = f"{TWITCH_API_BASE}/clips"
        resp = requests.get(url, headers=self._headers, params={"id": clip_id})
        if resp.ok and resp.json().get("data"):
            # Convert thumbnail URL to MP4 URL
            thumb = resp.json()["data"][0].get("thumbnail_url", "")
            # Twitch MP4: replace -preview-480x272.jpg with .mp4
            mp4_url = thumb.rsplit("-preview", 1)[0] + ".mp4"
            return mp4_url
        return ""
