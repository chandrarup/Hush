"""
audio.py — Push-to-talk audio capture using sounddevice.

Latency fix: the stream is kept open permanently after preheat().
On press we only flip a flag — no PortAudio open/close overhead (~280 ms saved).

Usage:
    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.preheat()     # call once at startup — opens stream, stays warm
    ...
    recorder.start()       # key pressed  — just toggles flag
    recorder.stop()        # key released — harvests chunks, keeps stream warm
    recorder.close()       # app quit     — closes stream cleanly
"""

import threading
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"
BLOCKSIZE = 512  # ~32 ms at 16 kHz (was 1024/~64 ms — tighter for latency)


class AudioRecorder:
    """Thread-safe push-to-talk recorder with persistent warm stream."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS):
        if sd is None:
            raise RuntimeError(
                "sounddevice is not installed. Run: pip install sounddevice"
            )
        self.sample_rate = sample_rate
        self.channels = channels
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: "sd.InputStream | None" = None
        self._recording = False

    # ------------------------------------------------------------------ #
    #  Internal sounddevice callback                                       #
    # ------------------------------------------------------------------ #

    def _callback(self, indata: np.ndarray, frames: int, time, status):
        """Called by sounddevice in a dedicated audio thread for each block."""
        if status:
            print(f"[audio] sounddevice status: {status}")
        if self._recording:
            with self._lock:
                self._chunks.append(indata.copy())

    # ------------------------------------------------------------------ #
    #  Stream management                                                   #
    # ------------------------------------------------------------------ #

    def _open_stream(self, device=None) -> "sd.InputStream":
        return sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=DTYPE,
            blocksize=BLOCKSIZE,
            device=device,
            callback=self._callback,
        )

    def preheat(self):
        """
        Open the audio stream once and keep it warm.

        Call this at startup (from main thread before tray blocks it).
        After preheat, start() has zero stream-open overhead — it just flips
        the recording flag. Eliminates ~280 ms of PortAudio init per press.
        """
        if self._stream is not None and self._stream.active:
            return  # already warm

        try:
            dev_info = sd.query_devices(kind="input")
            dev_name = dev_info.get("name", "default") if isinstance(dev_info, dict) else "default"
        except Exception:
            dev_name = "default"

        try:
            stream = self._open_stream(device=None)
            stream.start()
            self._stream = stream
            print(f"[audio] ✓ Stream preheated  device='{dev_name}'  {self.sample_rate} Hz"
                  " — push-to-talk warmup latency eliminated")
        except Exception as e:
            print(f"[audio] ⚠ Preheat failed ({e}) — will open on first press")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def start(self):
        """
        Begin collecting audio.

        If preheat() was called the stream is already running — we just flip
        the recording flag and clear the chunk buffer.  Latency from press
        to first captured sample: ~0 ms (one BLOCKSIZE buffer, ~32 ms).

        If preheat() was never called (or the stream died), we open a fresh
        stream here. This incurs the normal ~280 ms overhead on this press only.
        """
        # Ensure stream is alive — reopen if it died (device removed, etc.)
        if self._stream is None or not self._stream.active:
            print("[audio] Stream not active — reopening…")
            try:
                stream = self._open_stream(device=None)
                stream.start()
                self._stream = stream
            except Exception as e:
                fallback = self._find_fallback_device()
                if fallback is None:
                    self._recording = False
                    raise RuntimeError("No audio input device available.") from e
                stream = self._open_stream(device=fallback)
                stream.start()
                self._stream = stream

        with self._lock:
            self._chunks = []       # discard any stale frames
            self._recording = True

        print(f"[audio] ● Recording  {self.sample_rate} Hz  (stream persistent)")

    def stop(self) -> np.ndarray:
        """
        Stop collecting audio and return the captured float32 array.

        The stream is intentionally kept open so the next press has zero
        warm-up cost.  Call close() only when the app is shutting down.
        """
        self._recording = False

        # Flush one callback cycle so we don't race the last buffer
        # (BLOCKSIZE / sample_rate ≈ 32 ms — cheap sleep)
        import time
        time.sleep(BLOCKSIZE / self.sample_rate + 0.005)

        with self._lock:
            chunks = list(self._chunks)
            self._chunks = []

        if not chunks:
            print("[audio] No audio chunks captured.")
            return np.array([], dtype=np.float32)

        audio = np.concatenate(chunks, axis=0)
        if audio.ndim > 1:
            audio = audio[:, 0]

        duration = len(audio) / self.sample_rate
        print(f"[audio] Captured {duration:.2f}s of audio ({len(audio)} samples).")
        return audio.astype(np.float32)

    def close(self):
        """Cleanly close the stream on app shutdown."""
        self._recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        print("[audio] Stream closed.")

    @staticmethod
    def _find_fallback_device() -> "int | None":
        """Return the index of the first working input device, or None."""
        try:
            devices = sd.query_devices()
            if isinstance(devices, dict):
                devices = [devices]
            for i, d in enumerate(devices):
                if d.get("max_input_channels", 0) > 0:
                    return i
        except Exception:
            pass
        return None

    @property
    def is_recording(self) -> bool:
        return self._recording
