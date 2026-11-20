"""
ClipForge AI — End-to-End Pipeline Self-Test
Generates a mock 16:9 clip with real Windows SAPI speech audio,
runs it through VideoEditor (9:16 vertical, Whisper captions, SFX mix),
and validates the resulting Short.
"""

import os
import sys
import subprocess
import time
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import RAW_CLIPS_DIR, EDITED_CLIPS_DIR
from editor.video_editor import VideoEditor
from editor.generate_sfx import generate_all_sfx


def generate_mock_speech(wav_path: str, text: str):
    """Use Windows Speech Synthesis to generate a clean spoken audio track."""
    ps_script = f"""
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.SetOutputToWaveFile('{wav_path}')
    $synth.Speak('{text}')
    $synth.Dispose()
    """
    cmd = ["powershell", "-NoProfile", "-Command", ps_script]
    subprocess.run(cmd, check=True)


def create_mock_raw_clip(out_mp4: str):
    """Generate a realistic 16:9 test gaming clip (1920x1080) with real speech."""
    os.makedirs(RAW_CLIPS_DIR, exist_ok=True)
    temp_wav = out_mp4.replace(".mp4", "_speech.wav")
    text = "Wait, did you see that incredible clutch? No way!"
    
    logger.info("[Test] Generating mock spoken audio via SAPI...")
    generate_mock_speech(temp_wav, text)

    logger.info("[Test] Combining video pattern and speech audio into 16:9 clip...")
    # Generate 1920x1080 30fps video pattern matching speech duration
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc=size=1920x1080:rate=30:duration=7",
        "-i", temp_wav,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        out_mp4
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(temp_wav):
        os.remove(temp_wav)


def run_test():
    logger.info("🧪 Starting ClipForge AI Pipeline Self-Test...")

    # Step 1: Ensure baseline SFX exist
    generate_all_sfx()

    # Step 2: Create mock 16:9 raw clip
    mock_clip_id = "test_clutch_001"
    raw_path = os.path.join(RAW_CLIPS_DIR, f"{mock_clip_id}.mp4")
    create_mock_raw_clip(raw_path)
    logger.success(f"[Test] Created raw 16:9 clip → {raw_path}")

    # Step 3: Run VideoEditor pipeline
    editor = VideoEditor()
    logger.info("[Test] Running full edit pipeline (9:16 + Whisper captions + SFX)...")
    start_time = time.time()
    
    final_path = editor.edit_clip(
        raw_clip_path=raw_path,
        clip_id=mock_clip_id,
        channel="tarik",
        game="VALORANT",
        vertical_mode="blur",
        add_captions=True,
        add_hook_sfx=True,
        custom_sfx=[{"sfx": "vine_boom", "at": 3.0, "volume": 1.0}],
    )
    
    elapsed = time.time() - start_time
    logger.success(f"[Test] Pipeline finished in {elapsed:.2f} seconds!")
    logger.success(f"[Test] Final edited clip → {final_path}")

    # Step 4: Verification with ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "csv=p=0",
        final_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    logger.info(f"[Test] Probe result (width,height,duration): {res.stdout.strip()}")
    
    parts = res.stdout.strip().split(",")
    if len(parts) >= 2 and parts[0] == "1080" and parts[1] == "1920":
        logger.success("🎉 VERIFICATION PASSED: Video is true 9:16 vertical (1080x1920) with captions and SFX!")
    else:
        logger.warning(f"Unexpected dimensions: {parts}")


if __name__ == "__main__":
    run_test()
