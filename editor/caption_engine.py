"""
ClipForge AI — Caption Engine
Uses OpenAI Whisper to transcribe clip audio, then renders
word-by-word animated captions (.ASS format) burned in by FFmpeg.
"""

import os
import sys
import json
import subprocess
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import EDITED_CLIPS_DIR

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("[CaptionEngine] openai-whisper not installed. Captions disabled.")


# ─── ASS Styling ─────────────────────────────────────────────────────────────

ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat Black,90,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,200,1
Style: Highlight,Montserrat Black,90,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _seconds_to_ass_time(seconds: float) -> str:
    """Convert float seconds to ASS timestamp format H:MM:SS.cc"""
    hours   = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs    = int(seconds % 60)
    centis  = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


# ─── Caption Engine ───────────────────────────────────────────────────────────

class CaptionEngine:
    """Transcribes a video clip with Whisper and generates animated captions."""

    def __init__(self, model_size: str = "base"):
        self._model = None
        self._model_size = model_size

    def _load_model(self):
        if self._model is None and WHISPER_AVAILABLE:
            logger.info(f"[CaptionEngine] Loading Whisper model '{self._model_size}'...")
            self._model = whisper.load_model(self._model_size)

    def transcribe(self, video_path: str) -> list[dict]:
        """
        Transcribe a video file and return word-level timestamps.
        Returns list of: {"word": str, "start": float, "end": float}
        """
        if not WHISPER_AVAILABLE:
            return []

        self._load_model()
        logger.info(f"[CaptionEngine] Transcribing: {os.path.basename(video_path)}")
        result = self._model.transcribe(
            video_path,
            word_timestamps=True,
            language="en",
        )

        words = []
        for segment in result.get("segments", []):
            for word_info in segment.get("words", []):
                words.append({
                    "word":  word_info["word"].strip(),
                    "start": word_info["start"],
                    "end":   word_info["end"],
                })

        logger.success(f"[CaptionEngine] Transcribed {len(words)} words.")
        return words

    def generate_ass_file(self, words: list[dict], output_path: str, group_size: int = 4):
        """
        Generate a .ASS subtitle file with word-by-word highlight captions.
        Words are grouped into lines of `group_size`.
        The current word highlights in yellow; others are white.
        """
        lines = []
        # Group words into subtitle blocks
        groups = [words[i:i+group_size] for i in range(0, len(words), group_size)]

        for group in groups:
            if not group:
                continue

            group_start = group[0]["start"]
            group_end   = group[-1]["end"]

            for highlight_idx, hw in enumerate(group):
                # Build the line with the current word highlighted
                parts = []
                for idx, w in enumerate(group):
                    if idx == highlight_idx:
                        parts.append(f"{{\\rHighlight}}{w['word']}{{\\rDefault}}")
                    else:
                        parts.append(w["word"])
                text = " ".join(parts)

                word_start = hw["start"]
                word_end   = hw["end"]

                ass_start = _seconds_to_ass_time(word_start)
                ass_end   = _seconds_to_ass_time(word_end)
                lines.append(
                    f"Dialogue: 0,{ass_start},{ass_end},Default,,0,0,0,,{text}"
                )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ASS_HEADER)
            f.write("\n".join(lines))

        logger.success(f"[CaptionEngine] ASS file saved → {output_path}")
        return output_path

    def add_captions_to_video(
        self, input_video: str, output_video: str, ass_path: str
    ) -> str:
        """Burn the .ASS captions into the video using FFmpeg."""
        ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-vf", f"ass=filename='{ass_escaped}'",
            "-c:a", "copy",
            output_video,
        ]
        logger.info(f"[CaptionEngine] Burning captions with FFmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[CaptionEngine] FFmpeg error:\n{result.stderr}")
            return input_video   # Fallback: return uncaptioned video

        logger.success(f"[CaptionEngine] Captions burned → {output_video}")
        return output_video
