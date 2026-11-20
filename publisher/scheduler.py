"""
ClipForge AI — Drip Post Scheduler
Queues edited clips and posts them at optimal IST times.
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
import pytz
import schedule
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import POSTING_TIMES_IST, EDITED_CLIPS_DIR

QUEUE_FILE = os.path.join(os.path.dirname(__file__), "posting_queue.json")
IST         = pytz.timezone("Asia/Kolkata")


class PostScheduler:
    """
    Maintains a JSON queue of approved clips and
    drip-posts them at the configured IST times.
    """

    def __init__(self, youtube_uploader=None, instagram_uploader=None):
        self._yt  = youtube_uploader
        self._ig  = instagram_uploader
        self._queue = self._load_queue()

    # ─── Queue Management ─────────────────────────────────────────────────────

    def _load_queue(self) -> list[dict]:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE) as f:
                return json.load(f)
        return []

    def _save_queue(self):
        with open(QUEUE_FILE, "w") as f:
            json.dump(self._queue, f, indent=2)

    def add_to_queue(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str],
        platforms: list[str],  # ["youtube", "instagram"]
        video_url: str = "",   # Public URL for Instagram
    ):
        """Add an approved clip to the posting queue."""
        self._queue.append({
            "file_path":   file_path,
            "title":       title,
            "description": description,
            "tags":        tags,
            "platforms":   platforms,
            "video_url":   video_url,
            "added_at":    datetime.now(IST).isoformat(),
            "posted":      False,
        })
        self._save_queue()
        logger.info(f"[Scheduler] Added to queue: {os.path.basename(file_path)}")

    def _post_next(self):
        """Post the next unposted clip in the queue."""
        pending = [c for c in self._queue if not c["posted"]]
        if not pending:
            logger.debug("[Scheduler] Queue is empty — nothing to post.")
            return

        clip = pending[0]
        logger.info(f"[Scheduler] Posting: {clip['title']}")

        for platform in clip.get("platforms", []):
            if platform == "youtube" and self._yt:
                self._yt.upload(
                    file_path   = clip["file_path"],
                    title       = clip["title"],
                    description = clip["description"],
                    tags        = clip["tags"],
                )
            elif platform == "instagram" and self._ig:
                self._ig.upload_reel(
                    video_url = clip["video_url"],
                    caption   = clip["description"],
                )

        clip["posted"] = True
        self._save_queue()

    # ─── Scheduler Setup ──────────────────────────────────────────────────────

    def start(self):
        """Schedule _post_next at all configured IST posting times."""
        for t in POSTING_TIMES_IST:
            schedule.every().day.at(t).do(self._post_next)
            logger.info(f"[Scheduler] Scheduled post at {t} IST")

        def _run():
            while True:
                schedule.run_pending()
                time.sleep(30)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        logger.success("[Scheduler] Drip scheduler running.")
