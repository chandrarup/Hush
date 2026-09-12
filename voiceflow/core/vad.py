"""
vad.py - Voice Activity Detection using webrtcvad.

Trims leading and trailing silence from a float32 audio buffer.
webrtcvad requires:
  - Sample rate: 8000, 16000, or 32000 Hz
  - Frame duration: 10, 20, or 30 ms
  - PCM int16 little-endian bytes

The function returns the trimmed float32 array (same format as input).
"""

import numpy as np

try:
    import webrtcvad
    _VAD_AVAILABLE = True
except ImportError:
    _VAD_AVAILABLE = False
    print("[vad] WARNING: webrtcvad not installed. VAD trimming disabled.")

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30          # 30 ms frames - best supported by webrtcvad
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # 480 samples
VAD_MODE = 2                    # aggressiveness: 0 (least) - 3 (most)

# How many consecutive voiced/silent frames needed to flip state
VOICED_TRIGGER = 2
SILENCE_TRIGGER = 8             # ~240 ms of silence to end speech


def _float32_to_int16_bytes(audio: np.ndarray) -> bytes:
    """Convert float32 [-1, 1] to int16 PCM bytes."""
    audio_clipped = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio_clipped * 32767).astype(np.int16)
    return audio_int16.tobytes()


def trim_silence(
    audio: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    mode: int = VAD_MODE,
    padding_ms: int = 150,
) -> np.ndarray:
    """
    Trim leading and trailing silence from audio using webrtcvad.

    Args:
        audio:       1-D float32 numpy array at `sample_rate` Hz.
        sample_rate: Must be 8000, 16000, or 32000.
        mode:        VAD aggressiveness 0-3.
        padding_ms:  Milliseconds of padding to keep around voiced regions.

    Returns:
        Trimmed float32 array, or the original array if VAD is unavailable
        or no voiced frames are found.
    """
    if not _VAD_AVAILABLE:
        return audio

    if len(audio) == 0:
        return audio

    vad = webrtcvad.Vad(mode)
    frame_size = int(sample_rate * FRAME_DURATION_MS / 1000)
    padding_frames = int(padding_ms / FRAME_DURATION_MS)

    # Pad audio so it divides evenly into frames
    remainder = len(audio) % frame_size
    if remainder:
        audio = np.concatenate([audio, np.zeros(frame_size - remainder, dtype=np.float32)])

    # Split into frames and classify each as voiced / not-voiced
    frames = [audio[i : i + frame_size] for i in range(0, len(audio), frame_size)]
    voiced_flags: list[bool] = []

    for frame in frames:
        frame_bytes = _float32_to_int16_bytes(frame)
        try:
            is_speech = vad.is_speech(frame_bytes, sample_rate)
        except Exception:
            is_speech = False
        voiced_flags.append(is_speech)

    # Find first and last voiced frame indices
    voiced_indices = [i for i, v in enumerate(voiced_flags) if v]
    if not voiced_indices:
        # No voiced speech detected - return original (let transcriber handle it)
        print("[vad] No voiced frames detected; returning original audio.")
        return audio

    start_idx = max(0, voiced_indices[0] - padding_frames)
    end_idx = min(len(frames), voiced_indices[-1] + 1 + padding_frames)

    trimmed = np.concatenate(frames[start_idx:end_idx])

    original_dur = len(audio) / sample_rate
    trimmed_dur = len(trimmed) / sample_rate
    print(
        f"[vad] Trimmed {original_dur:.2f}s → {trimmed_dur:.2f}s "
        f"({voiced_indices[0]}-{voiced_indices[-1]+1} of {len(frames)} frames voiced)"
    )
    return trimmed.astype(np.float32)


def audio_duration(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> float:
    """Return duration of audio array in seconds."""
    return len(audio) / sample_rate
