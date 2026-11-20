"""
ClipForge AI — Google Drive Uploader
Uploads raw MP4 clips to a designated Google Drive folder.
"""

import os
import sys
from loguru import logger
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import GOOGLE_CREDENTIALS_JSON, GOOGLE_DRIVE_FOLDER_ID


class DriveUploader:
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self):
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_JSON, scopes=self.SCOPES
        )
        self._service = build("drive", "v3", credentials=creds)

    def upload(self, file_path: str, metadata: dict) -> str:
        """
        Upload a file to Google Drive.
        Returns the shareable Drive file URL.
        """
        filename = os.path.basename(file_path)
        channel  = metadata.get("channel", "unknown")
        game     = metadata.get("game", "unknown")
        clip_id  = metadata.get("clip_id", "")

        drive_name = f"[{channel}] [{game}] {clip_id}.mp4"

        file_metadata = {
            "name": drive_name,
            "parents": [GOOGLE_DRIVE_FOLDER_ID],
            "description": (
                f"ClipForge | Streamer: {channel} | Game: {game} | "
                f"Stream: {metadata.get('stream_title', '')} | "
                f"Viewers: {metadata.get('viewer_count', 0)}"
            ),
        }

        media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)

        logger.info(f"[DriveUploader] Uploading '{drive_name}' to Drive...")

        file = (
            self._service.files()
            .create(body=file_metadata, media_body=media, fields="id,webViewLink")
            .execute()
        )

        file_id  = file.get("id", "")
        view_url = file.get("webViewLink", "")

        # Make the file readable by anyone with the link
        self._service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        logger.success(f"[DriveUploader] ✅ Uploaded: {view_url}")
        return view_url
