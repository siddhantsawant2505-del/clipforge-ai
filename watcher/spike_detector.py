"""
ClipForge AI — Twitch Chat Spike Detector
Connects to Twitch IRC and measures chat velocity in a sliding window.
Fires a callback when a spike is detected.
"""

import socket
import time
import threading
from collections import deque
from loguru import logger
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import (
    TWITCH_CLIENT_ID,
    TWITCH_USER_TOKEN,
    TWITCH_IRC_HOST,
    TWITCH_IRC_PORT,
    SPIKE_THRESHOLD,
    SPIKE_WINDOW_SECONDS,
    CLIP_COOLDOWN_SECONDS,
)


class SpikeDetector:
    """
    Monitors Twitch IRC chat for a single channel.
    Calls `on_spike(channel)` when a chat velocity spike is detected.
    """

    def __init__(self, channel: str, on_spike):
        self.channel = channel.lower().lstrip("#")
        self.on_spike = on_spike
        self._sock: socket.socket | None = None
        self._running = False

        # Sliding window of message timestamps
        self._timestamps: deque[float] = deque()

        # Rolling baseline: average messages per window
        self._baseline_samples: deque[float] = deque(maxlen=20)
        self._last_clip_time: float = 0

    # ─── IRC Connection ───────────────────────────────────────────────────────

    def _connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((TWITCH_IRC_HOST, TWITCH_IRC_PORT))
        self._send(f"PASS oauth:{TWITCH_USER_TOKEN}")
        self._send(f"NICK clipforge_bot")
        self._send(f"JOIN #{self.channel}")
        logger.info(f"[SpikeDetector] Connected to #{self.channel}")

    def _send(self, msg: str):
        self._sock.send(f"{msg}\r\n".encode("utf-8"))

    # ─── Main Loop ────────────────────────────────────────────────────────────

    def start(self):
        self._running = True
        self._connect()
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()
        logger.info(f"[SpikeDetector] Monitoring #{self.channel} started.")

    def stop(self):
        self._running = False
        if self._sock:
            self._sock.close()
        logger.info(f"[SpikeDetector] Monitoring #{self.channel} stopped.")

    def _listen_loop(self):
        buffer = ""
        while self._running:
            try:
                data = self._sock.recv(2048).decode("utf-8", errors="ignore")
                if not data:
                    break
                buffer += data
                lines = buffer.split("\r\n")
                buffer = lines[-1]
                for line in lines[:-1]:
                    self._handle_line(line)
            except Exception as e:
                logger.error(f"[SpikeDetector] Error in listen loop: {e}")
                break

    # ─── Message Handling & Spike Detection ──────────────────────────────────

    def _handle_line(self, line: str):
        # Keep-alive
        if line.startswith("PING"):
            self._send("PONG :tmi.twitch.tv")
            return

        # Count PRIVMSG (chat messages)
        if "PRIVMSG" in line:
            now = time.time()
            self._timestamps.append(now)

            # Remove messages outside the sliding window
            cutoff = now - SPIKE_WINDOW_SECONDS
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            current_rate = len(self._timestamps)

            # Update baseline every window
            self._baseline_samples.append(current_rate)

            if len(self._baseline_samples) >= 5:
                baseline = sum(self._baseline_samples) / len(self._baseline_samples)
                if baseline > 0 and current_rate >= baseline * SPIKE_THRESHOLD:
                    self._trigger_spike()

    def _trigger_spike(self):
        now = time.time()
        cooldown_elapsed = now - self._last_clip_time

        if cooldown_elapsed < CLIP_COOLDOWN_SECONDS:
            remaining = int(CLIP_COOLDOWN_SECONDS - cooldown_elapsed)
            logger.debug(
                f"[SpikeDetector] Spike detected on #{self.channel} "
                f"but cooling down ({remaining}s remaining)."
            )
            return

        self._last_clip_time = now
        rate = len(self._timestamps)
        logger.success(
            f"[SpikeDetector] 🔥 SPIKE on #{self.channel}! "
            f"{rate} messages in {SPIKE_WINDOW_SECONDS}s"
        )
        # Fire the callback in a separate thread so IRC loop is never blocked
        threading.Thread(
            target=self.on_spike, args=(self.channel,), daemon=True
        ).start()
