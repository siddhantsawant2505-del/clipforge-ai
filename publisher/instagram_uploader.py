"""
ClipForge AI — Instagram Reels Uploader
Uses the Instagram Graph API to upload edited clips as Reels.
"""

import os
import sys
import time
import requests
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID

GRAPH_URL = "https://graph.instagram.com/v20.0"


class InstagramUploader:
    """Uploads short-form videos to Instagram Reels via the Graph API."""

    def upload_reel(
        self,
        video_url: str,       # Must be a publicly accessible URL (e.g., Google Drive CDN link)
        caption: str,
        share_to_feed: bool = True,
    ) -> str:
        """
        Upload a Reel to Instagram.
        Note: Instagram Graph API requires the video to be at a public HTTPS URL.
        Returns the media permalink URL.
        """

        # Step 1: Create a media container
        container_url = f"{GRAPH_URL}/{INSTAGRAM_USER_ID}/media"
        payload = {
            "media_type":    "REELS",
            "video_url":     video_url,
            "caption":       caption,
            "share_to_feed": str(share_to_feed).lower(),
            "access_token":  INSTAGRAM_ACCESS_TOKEN,
        }

        logger.info("[InstagramUploader] Creating Reel media container...")
        resp = requests.post(container_url, data=payload)

        if not resp.ok:
            logger.error(f"[InstagramUploader] Container creation failed: {resp.text}")
            return ""

        container_id = resp.json().get("id", "")
        logger.info(f"[InstagramUploader] Container ID: {container_id}")

        # Step 2: Poll until the container finishes processing
        self._wait_for_processing(container_id)

        # Step 3: Publish the container
        publish_url = f"{GRAPH_URL}/{INSTAGRAM_USER_ID}/media_publish"
        pub_resp = requests.post(publish_url, data={
            "creation_id":  container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        })

        if not pub_resp.ok:
            logger.error(f"[InstagramUploader] Publish failed: {pub_resp.text}")
            return ""

        media_id = pub_resp.json().get("id", "")
        permalink = self._get_permalink(media_id)
        logger.success(f"[InstagramUploader] ✅ Reel published → {permalink}")
        return permalink

    def _wait_for_processing(self, container_id: str, max_wait: int = 300):
        """Poll the container status until it is FINISHED."""
        status_url = f"{GRAPH_URL}/{container_id}"
        params = {
            "fields":        "status_code",
            "access_token":  INSTAGRAM_ACCESS_TOKEN,
        }
        waited = 0
        while waited < max_wait:
            resp = requests.get(status_url, params=params)
            status = resp.json().get("status_code", "")
            logger.debug(f"[InstagramUploader] Container status: {status}")
            if status == "FINISHED":
                return
            elif status == "ERROR":
                logger.error("[InstagramUploader] Container processing error.")
                return
            time.sleep(10)
            waited += 10
        logger.warning("[InstagramUploader] Timed out waiting for container processing.")

    def _get_permalink(self, media_id: str) -> str:
        url = f"{GRAPH_URL}/{media_id}"
        params = {"fields": "permalink", "access_token": INSTAGRAM_ACCESS_TOKEN}
        resp = requests.get(url, params=params)
        return resp.json().get("permalink", f"https://www.instagram.com/p/{media_id}/")
