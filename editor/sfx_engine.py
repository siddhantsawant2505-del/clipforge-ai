"""
ClipForge AI — SFX Engine
Layers sound effects onto a video at specific timestamps using FFmpeg.
"""

import os
import sys
import subprocess
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import SFX_DIR


# ─── SFX Catalogue ───────────────────────────────────────────────────────────
# Maps friendly names → filenames (place .mp3/.wav files in editor/sfx/)

SFX_CATALOGUE = {
    "vine_boom":      "vine_boom.mp3",
    "whoosh":         "whoosh.mp3",
    "pop":            "pop.mp3",
    "record_scratch": "record_scratch.mp3",
    "bass_drop":      "bass_drop.mp3",
    "ding":           "ding.mp3",
    "bleep":          "bleep.mp3",
    "dramatic":       "dramatic.mp3",
}


class SFXEngine:
    """Layers SFX clips onto a video at given timestamps."""

    def _sfx_path(self, sfx_name: str) -> str | None:
        filename = SFX_CATALOGUE.get(sfx_name)
        if not filename:
            logger.warning(f"[SFXEngine] Unknown SFX: '{sfx_name}'")
            return None
        full_path = os.path.join(SFX_DIR, filename)
        if not os.path.exists(full_path):
            logger.warning(
                f"[SFXEngine] SFX file not found: {full_path} — skipping."
            )
            return None
        return full_path

    def add_sfx(
        self,
        input_video: str,
        output_video: str,
        sfx_events: list[dict],
    ) -> str:
        """
        Add multiple SFX events to a video.

        sfx_events: list of {"sfx": "vine_boom", "at": 12.5, "volume": 1.0}
        """
        if not sfx_events:
            return input_video

        # Build a complex FFmpeg filtergraph that mixes the original audio
        # with one or more SFX tracks delayed to their timestamps.

        inputs   = ["-i", input_video]
        delays   = []
        mix_ins  = ["[0:a]"]    # Original audio stream
        sfx_idx  = 1

        for event in sfx_events:
            sfx_path = self._sfx_path(event.get("sfx", ""))
            if not sfx_path:
                continue
            at     = float(event.get("at", 0.0))
            volume = float(event.get("volume", 1.0))
            delay_ms = int(at * 1000)

            inputs += ["-i", sfx_path]
            filter_label = f"[sfx{sfx_idx}]"
            delays.append(
                f"[{sfx_idx}:a]"
                f"adelay={delay_ms}|{delay_ms},"
                f"volume={volume}"
                f"{filter_label}"
            )
            mix_ins.append(filter_label)
            sfx_idx += 1

        if sfx_idx == 1:
            # No valid SFX found — return unchanged
            return input_video

        num_streams = len(mix_ins)
        mix_filter  = "".join(mix_ins) + f"amix=inputs={num_streams}:duration=first[aout]"

        filter_complex = "; ".join(delays) + "; " + mix_filter

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-shortest",
            output_video,
        ]

        logger.info(f"[SFXEngine] Mixing {sfx_idx - 1} SFX track(s)...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"[SFXEngine] FFmpeg error:\n{result.stderr}")
            return input_video

        logger.success(f"[SFXEngine] SFX mixed → {output_video}")
        return output_video

    def add_hook_sfx(self, input_video: str, output_video: str) -> str:
        """
        Convenience: add a 'whoosh' hook sound at t=0 and a 'pop' at t=0.5s.
        These are the standard retention-hooking sounds used for Shorts intros.
        """
        return self.add_sfx(
            input_video,
            output_video,
            sfx_events=[
                {"sfx": "whoosh", "at": 0.0,  "volume": 0.7},
                {"sfx": "pop",    "at": 0.5,  "volume": 0.5},
            ],
        )
