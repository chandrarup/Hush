"""
audio.py - Push-to-talk audio capture using sounddevice.

Usage:
    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.start()          # call when hotkey pressed
    ...                       # while key held
    audio_array = recorder.stop()  # call when hotkey released; returns float32 numpy array
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
BLOCKSIZE = 1024  # frames per callback (~64 ms at 16kHz)


class AudioRecorder:
    """Thread-safe push-to-talk recorder."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS):
        if sd is None:
            raise RuntimeError(
                "sounddevice is not installed. Run: uv sync --no-dev"
            )
        self.sample_rate = sample_rate
        self.channels = channels
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._recording = False

    # ------------------------------------------------------------------ #
    #  Internal sounddevice callback                                       #
    # ------------------------------------------------------------------ #

    def _callback(self, indata: np.ndarray, frames: int, time, status):
        """Called by sounddevice in a dedicated audio thread for each block."""
        if status:
            print(f"[audio] sounddevice status: {status}")
        if self._recording:
            # indata shape: (frames, channels) - copy to avoid reuse issues
            with self._lock:
                self._chunks.append(indata.copy())

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def _open_stream(self, device=None) -> "sd.InputStream":
        """Open a sounddevice InputStream. Pass device=None for system default."""
        return sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=DTYPE,
            blocksize=BLOCKSIZE,
            device=device,
            callback=self._callback,
        )

    def start(self):
        """Open the input stream and begin collecting audio.

        Opens a fresh stream each time so the operating system can hand us the
        active input device (handles headphone plug/unplug gracefully).
        """
        if self._stream is not None:
            return  # already running

        with self._lock:
            self._chunks = []
            self._recording = True

        # Resolve the current default input device name for logging
        try:
            device_info = sd.query_devices(kind="input")
            dev_name = device_info.get("name", "default") if isinstance(device_info, dict) else "default"
        except Exception:
            dev_name = "default"

        # Try to open with default device; if it fails (e.g. device is gone),
        # retry with explicit device=None which lets PortAudio pick any available input.
        try:
            stream = self._open_stream(device=None)
            stream.start()
        except Exception as e:
            print(f"[audio] ⚠ Default device failed ({e}), trying any available input…")
            # Query for any working input device
            fallback = self._find_fallback_device()
            if fallback is None:
                self._recording = False
                raise RuntimeError("No audio input device available.") from e
            print(f"[audio] Falling back to device index {fallback}")
            stream = self._open_stream(device=fallback)
            stream.start()
            try:
                dev_name = sd.query_devices(fallback)["name"]
            except Exception:
                dev_name = f"device[{fallback}]"

        self._stream = stream
        print(f"[audio] ● Recording  device='{dev_name}'  {self.sample_rate}Hz")

    @staticmethod
    def _find_fallback_device() -> int | None:
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

    def stop(self) -> np.ndarray:
        """
        Stop recording and return the captured audio as a 1-D float32 numpy array.
        Returns an empty array if no audio was captured.
        """
        self._recording = False

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            chunks = list(self._chunks)
            self._chunks = []

        if not chunks:
            print("[audio] No audio chunks captured.")
            return np.array([], dtype=np.float32)

        # Concatenate all chunks; shape becomes (total_frames, channels)
        audio = np.concatenate(chunks, axis=0)

        # Flatten to mono
        if audio.ndim > 1:
            audio = audio[:, 0]

        duration = len(audio) / self.sample_rate
        print(f"[audio] Captured {duration:.2f}s of audio ({len(audio)} samples).")
        return audio.astype(np.float32)

    @property
    def is_recording(self) -> bool:
        return self._recording
