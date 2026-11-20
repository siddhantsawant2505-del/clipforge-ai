"""
ClipForge AI — Video Editor (Core)
Converts a 16:9 raw clip into a 9:16 vertical Short using FFmpeg,
then chains: caption generation (Whisper) → SFX layering → final render.
"""

import os
import sys
import subprocess
import time
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import RAW_CLIPS_DIR, EDITED_CLIPS_DIR
from editor.caption_engine import CaptionEngine
from editor.sfx_engine import SFXEngine


class VideoEditor:
    """Full editing pipeline for a single clip."""

    def __init__(self):
        self._captions = CaptionEngine(model_size="base")
        self._sfx      = SFXEngine()

    # ─── 9:16 Vertical Conversion ─────────────────────────────────────────────

    def convert_to_vertical(
        self,
        input_path: str,
        output_path: str,
        mode: str = "blur",        # "blur" | "split" | "crop"
    ) -> str:
        """
        Convert a 16:9 video to 9:16 (1080×1920) vertical format.

        Modes:
          blur  — Original centred; zoomed blurred version fills the BG (most common).
          split — Top half = facecam crop, bottom half = gameplay crop.
          crop  — Centre-crop to 9:16 (content fills the full frame).
        """
        if mode == "blur":
            vf = (
                # Layer 1: blurred, zoomed background filling 1080x1920
                "[0:v]scale=1920:1080,boxblur=20:5,"
                "scale=1080:1920,setsar=1[bg];"
                # Layer 2: original video scaled to fit width=1080
                "[0:v]scale=1080:-1,setsar=1[fg];"
                # Overlay fg centred over bg
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"
            )
        elif mode == "crop":
            # Centre crop to 9:16
            vf = (
                "[0:v]scale=1920:1080,"
                "crop=607:1080,scale=1080:1920,setsar=1[out]"
            )
        else:
            # Fallback to blur mode
            return self.convert_to_vertical(input_path, output_path, mode="blur")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-filter_complex", vf,
            "-map", "[out]",
            "-map", "0:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            output_path,
        ]

        logger.info(f"[VideoEditor] Converting to 9:16 ({mode} mode)...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"[VideoEditor] FFmpeg error:\n{result.stderr}")
            return input_path

        logger.success(f"[VideoEditor] 9:16 video → {output_path}")
        return output_path

    # ─── Full Edit Pipeline ───────────────────────────────────────────────────

    def edit_clip(
        self,
        raw_clip_path: str,
        clip_id: str,
        channel: str,
        game: str,
        vertical_mode: str = "blur",
        add_captions:  bool = True,
        add_hook_sfx:  bool = True,
        custom_sfx:    list[dict] | None = None,
    ) -> str:
        """
        Full editing pipeline:
          1. Convert to 9:16 vertical
          2. Add animated word-by-word captions (Whisper)
          3. Add hook SFX and any custom SFX events
          4. Return path to final edited video

        Returns the path to the finished edited clip.
        """
        timestamp = int(time.time())
        base_name = f"{channel}_{clip_id}_{timestamp}"

        vertical_path  = os.path.join(EDITED_CLIPS_DIR, f"{base_name}_vertical.mp4")
        captioned_path = os.path.join(EDITED_CLIPS_DIR, f"{base_name}_captioned.mp4")
        sfx_path       = os.path.join(EDITED_CLIPS_DIR, f"{base_name}_sfx.mp4")
        final_path     = os.path.join(EDITED_CLIPS_DIR, f"{base_name}_FINAL.mp4")

        # Step 1: 9:16 conversion
        step1 = self.convert_to_vertical(raw_clip_path, vertical_path, mode=vertical_mode)

        # Step 2: Captions (Whisper → .ASS → burn in)
        if add_captions:
            words    = self._captions.transcribe(step1)
            ass_path = os.path.join(EDITED_CLIPS_DIR, f"{base_name}.ass")
            if words:
                self._captions.generate_ass_file(words, ass_path)
                step2 = self._captions.add_captions_to_video(step1, captioned_path, ass_path)
            else:
                logger.warning("[VideoEditor] No words transcribed — skipping captions.")
                step2 = step1
        else:
            step2 = step1

        # Step 3: SFX
        sfx_events = custom_sfx or []
        if add_hook_sfx:
            step3 = self._sfx.add_hook_sfx(step2, sfx_path)
        elif sfx_events:
            step3 = self._sfx.add_sfx(step2, sfx_path, sfx_events)
        else:
            step3 = step2

        # Step 4: Final copy / rename
        if step3 != final_path:
            import shutil
            shutil.copy2(step3, final_path)

        logger.success(f"[VideoEditor] ✅ Final clip ready → {final_path}")
        return final_path

    # ─── Utility ─────────────────────────────────────────────────────────────

    def get_duration(self, video_path: str) -> float:
        """Return video duration in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
        return 0.0
