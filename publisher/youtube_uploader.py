"""
ClipForge AI — YouTube Shorts Uploader
Uses YouTube Data API v3 to upload edited clips as Shorts.
"""

import os
import sys
import pickle
from loguru import logger
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import YOUTUBE_CLIENT_SECRET_JSON, YOUTUBE_SCOPES


TOKEN_PICKLE = os.path.join(os.path.dirname(__file__), "youtube_token.pkl")


class YouTubeUploader:
    """Handles OAuth and uploads to YouTube as Shorts."""

    def __init__(self):
        self._service = None

    def is_configured(self) -> bool:
        """Check if token or client secret exists."""
        return os.path.exists(TOKEN_PICKLE) or os.path.exists(YOUTUBE_CLIENT_SECRET_JSON)

    def get_service(self):
        """Lazy authentication so importing or starting the app doesn't block."""
        if self._service is None:
            if not self.is_configured():
                logger.warning(f"[YouTubeUploader] Secret file '{YOUTUBE_CLIENT_SECRET_JSON}' not found. Uploads disabled until configured.")
                return None
            try:
                self._service = self._authenticate()
            except Exception as e:
                logger.error(f"[YouTubeUploader] Auth failed: {e}")
                return None
        return self._service

    def _authenticate(self):
        creds = None
        if os.path.exists(TOKEN_PICKLE):
            with open(TOKEN_PICKLE, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    YOUTUBE_CLIENT_SECRET_JSON, YOUTUBE_SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PICKLE, "wb") as f:
                pickle.dump(creds, f)

        return build("youtube", "v3", credentials=creds)

    def upload(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        privacy: str = "public",   # "public" | "unlisted" | "private"
    ) -> str:
        """Upload an MP4 to YouTube. Returns the video URL."""
        service = self.get_service()
        if not service:
            logger.warning("[YouTubeUploader] YouTube is not authenticated. Please check your credentials.")
            return ""

        # Ensure #Shorts is in the description for Shorts detection
        if "#Shorts" not in description:
            description += "\n\n#Shorts"

        body = {
            "snippet": {
                "title":       title[:100],
                "description": description,
                "tags":        (tags or []) + ["Shorts", "TwitchClips", "Gaming"],
                "categoryId":  "20",   # Gaming
            },
            "status": {
                "privacyStatus":          privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            file_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,
        )

        logger.info(f"[YouTubeUploader] Uploading '{title}'...")
        request = self._service.videos().insert(
            part="snippet,status", body=body, media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.debug(f"[YouTubeUploader] Upload {int(status.progress() * 100)}%")

        video_id  = response.get("id", "")
        video_url = f"https://www.youtube.com/shorts/{video_id}"
        logger.success(f"[YouTubeUploader] ✅ Published → {video_url}")
        return video_url
