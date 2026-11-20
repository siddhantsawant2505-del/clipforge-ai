"""
ClipForge AI — Default SFX Generator
Generates clean baseline audio effects using NumPy and FFmpeg so the SFX engine
works immediately without needing external audio downloads.
Users can replace any of these files with their own MP3 memes at any time.
"""

import os
import sys
import numpy as np
import subprocess
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import SFX_DIR


SAMPLE_RATE = 44100


def save_wav_as_mp3(wav_path: str, mp3_path: str):
    """Convert WAV to MP3 using FFmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", wav_path,
        "-codec:a", "libmp3lame",
        "-b:a", "192k",
        mp3_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(wav_path):
        os.remove(wav_path)


def generate_whoosh(out_mp3: str):
    """Generate a clean whoosh / swoosh sweep."""
    duration = 0.5
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Filtered white noise with envelope
    noise = np.random.uniform(-1, 1, len(t))
    # Frequency sweep modulation
    freq = np.linspace(300, 1800, len(t))
    sweep = np.sin(2 * np.pi * freq * t) * noise
    # Smooth bell envelope
    envelope = np.sin(np.pi * (t / duration)) ** 2
    audio = sweep * envelope * 0.7
    audio_int16 = (audio * 32767).astype(np.int16)

    wav_path = out_mp3.replace(".mp3", ".wav")
    with wave.open(wav_path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio_int16.tobytes())
    save_wav_as_mp3(wav_path, out_mp3)


def generate_pop(out_mp3: str):
    """Generate a short bright pop / click sound."""
    duration = 0.15
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq = np.linspace(900, 300, len(t))
    audio = np.sin(2 * np.pi * freq * t) * np.exp(-t * 40)
    audio_int16 = (audio * 32767).astype(np.int16)

    wav_path = out_mp3.replace(".mp3", ".wav")
    with wave.open(wav_path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio_int16.tobytes())
    save_wav_as_mp3(wav_path, out_mp3)


def generate_vine_boom(out_mp3: str):
    """Generate a heavy bass impact (Vine boom style)."""
    duration = 1.2
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Bass sweep from 150 Hz down to 40 Hz
    freq = np.linspace(150, 40, len(t))
    sub_bass = np.sin(2 * np.pi * freq * t) * 0.8
    # Click/punch transient at the very start
    transient = np.random.uniform(-0.5, 0.5, len(t)) * np.exp(-t * 80)
    audio = (sub_bass + transient) * np.exp(-t * 2.5)
    # Soft saturation distortion
    audio = np.tanh(audio * 1.8) * 0.85
    audio_int16 = (audio * 32767).astype(np.int16)

    wav_path = out_mp3.replace(".mp3", ".wav")
    with wave.open(wav_path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio_int16.tobytes())
    save_wav_as_mp3(wav_path, out_mp3)


def generate_ding(out_mp3: str):
    """Generate a bright bell / ding sound."""
    duration = 1.0
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    fundamental = np.sin(2 * np.pi * 1200 * t) * 0.6
    harmonic = np.sin(2 * np.pi * 2400 * t) * 0.3
    audio = (fundamental + harmonic) * np.exp(-t * 4)
    audio_int16 = (audio * 32767).astype(np.int16)

    wav_path = out_mp3.replace(".mp3", ".wav")
    with wave.open(wav_path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio_int16.tobytes())
    save_wav_as_mp3(wav_path, out_mp3)


def generate_bleep(out_mp3: str):
    """Generate standard 1000 Hz censor bleep."""
    duration = 0.5
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    audio = np.sin(2 * np.pi * 1000 * t) * 0.5
    audio_int16 = (audio * 32767).astype(np.int16)

    wav_path = out_mp3.replace(".mp3", ".wav")
    with wave.open(wav_path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio_int16.tobytes())
    save_wav_as_mp3(wav_path, out_mp3)


def generate_all_sfx():
    """Build all default SFX files if missing."""
    os.makedirs(SFX_DIR, exist_ok=True)
    generators = {
        "whoosh.mp3": generate_whoosh,
        "pop.mp3": generate_pop,
        "vine_boom.mp3": generate_vine_boom,
        "ding.mp3": generate_ding,
        "bleep.mp3": generate_bleep,
        "bass_drop.mp3": generate_vine_boom,
        "record_scratch.mp3": generate_whoosh,
        "dramatic.mp3": generate_ding,
    }

    for filename, fn in generators.items():
        target = os.path.join(SFX_DIR, filename)
        if not os.path.exists(target):
            fn(target)
            print(f"[SFX Generator] Created: {filename}")
        else:
            print(f"[SFX Generator] Exists: {filename}")


if __name__ == "__main__":
    generate_all_sfx()
