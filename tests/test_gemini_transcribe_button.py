import importlib.util
import sys
import wave
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import numpy as np


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/gemini_transcribe_button.py"


spec = importlib.util.spec_from_file_location("gemini_transcribe_button", SCRIPT)
gemini_transcribe_button = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gemini_transcribe_button
spec.loader.exec_module(gemini_transcribe_button)


def test_float32_audio_to_wav_bytes_writes_mono_16khz_pcm():
    audio = np.array([0.0, 0.5, -0.5], dtype=np.float32)

    wav_bytes = gemini_transcribe_button.float32_audio_to_wav_bytes(audio)

    with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 16000
        assert wav_file.getsampwidth() == 2
        assert wav_file.getnframes() == 3


def test_response_text_prefers_top_level_text():
    response = SimpleNamespace(text=" hello from gemini ")

    assert gemini_transcribe_button.response_text(response) == "hello from gemini"


def test_response_text_reads_audio_transcription_parts():
    audio_tx = SimpleNamespace(text="part transcript")
    response = SimpleNamespace(text="", parts=[SimpleNamespace(audio_transcription=audio_tx)])

    assert gemini_transcribe_button.response_text(response) == "part transcript"
