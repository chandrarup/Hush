import asyncio
import io
import wave

import httpx
import numpy as np
import pytest

from voiceflow.web import api_server


def make_wav(
    samples: np.ndarray,
    *,
    sample_rate: int = 16_000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    return buffer.getvalue()


def post_audio(payload: bytes, *, include_origin: bool = True):
    async def exercise():
        headers = {"Content-Type": "audio/wav"}
        if include_origin:
            headers["Origin"] = "http://127.0.0.1:57327"
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:57327",
            headers=headers,
        ) as client:
            return await client.post("/transcribe", content=payload)

    return asyncio.run(exercise())


def test_static_file_route_rejects_paths_outside_ui_directory():
    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:57327",
        ) as client:
            escaped = await client.get("/ui/%2E%2E/api_server.py")
            legitimate = await client.get("/ui/index.html")
            return escaped, legitimate

    escaped, legitimate = asyncio.run(exercise())

    assert escaped.status_code == 404
    assert legitimate.status_code == 200
    assert "<title>Hush</title>" in legitimate.text


def test_decode_web_wav_returns_float32_mono_audio():
    samples = np.array([-32768, 0, 16384, 32767], dtype="<i2")

    decoded = api_server._decode_web_wav(make_wav(samples))

    assert decoded.dtype == np.float32
    assert decoded.tolist() == pytest.approx([-1.0, 0.0, 0.5, 32767 / 32768])


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"channels": 2}, "mono 16-bit PCM WAV at 16 kHz"),
        ({"sample_rate": 44_100}, "mono 16-bit PCM WAV at 16 kHz"),
        ({"sample_width": 1}, "mono 16-bit PCM WAV at 16 kHz"),
    ],
)
def test_decode_web_wav_rejects_unsupported_format(kwargs, message):
    samples = np.zeros(32, dtype="<i2")

    with pytest.raises(api_server.WebAudioError, match=message):
        api_server._decode_web_wav(make_wav(samples, **kwargs))


def test_decode_web_wav_rejects_audio_over_duration_limit(monkeypatch):
    monkeypatch.setattr(api_server, "_WEB_AUDIO_MAX_SECONDS", 1)
    samples = np.zeros(16_001, dtype="<i2")

    with pytest.raises(api_server.WebAudioError, match="60 seconds or shorter"):
        api_server._decode_web_wav(make_wav(samples))


def test_transcribe_stops_streaming_upload_at_byte_limit(monkeypatch):
    yielded_chunks = []
    monkeypatch.setattr(api_server, "_WEB_AUDIO_MAX_BYTES", 100)

    async def oversized_body():
        for index in range(3):
            yielded_chunks.append(index)
            yield b"x" * 60

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:57327",
            headers={"Origin": "http://127.0.0.1:57327", "Content-Type": "audio/wav"},
        ) as client:
            return await client.post("/transcribe", content=oversized_body())

    response = asyncio.run(exercise())

    assert response.status_code == 413
    assert response.json()["error"] == "Audio file exceeds the 10 MB limit."
    assert yielded_chunks == [0, 1]


def test_transcribe_saves_history_and_restores_idle_state(monkeypatch):
    saved = []
    events = []
    monkeypatch.setattr(api_server, "_transcribe_web_audio", lambda audio: "Hello from Hush.")
    monkeypatch.setattr(
        api_server._history,
        "save_entry",
        lambda **entry: saved.append(entry) or 17,
    )
    monkeypatch.setattr(
        api_server._history,
        "get_entry",
        lambda entry_id: {"id": entry_id, "clean": "Hello from Hush."},
    )
    monkeypatch.setattr(api_server, "push_event", events.append)
    monkeypatch.setitem(api_server._state, "status", "idle")
    samples = np.zeros(1_600, dtype="<i2")

    response = post_audio(make_wav(samples))

    assert response.status_code == 200
    assert response.json() == {"text": "Hello from Hush.", "history_id": 17}
    assert saved == [
        {
            "raw": "Hello from Hush.",
            "clean": "Hello from Hush.",
            "level": "none",
            "app": "Web upload",
            "client_id": "web-upload",
            "status": "final",
        }
    ]
    assert api_server._state["status"] == "idle"
    assert events[0] == {"type": "status", "value": "processing"}
    assert events[-1] == {"type": "status", "value": "idle"}


def test_transcribe_reports_model_load_failure(monkeypatch):
    def fail(_audio):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(api_server, "_transcribe_web_audio", fail)
    samples = np.zeros(1_600, dtype="<i2")

    response = post_audio(make_wav(samples))

    assert response.status_code == 503
    assert response.json()["error"] == "The transcription model could not be loaded."
    assert api_server._state["status"] == "idle"


def test_transcribe_rejects_malformed_audio_and_cross_origin_request():
    malformed = post_audio(b"not a wav")
    missing_origin = post_audio(make_wav(np.zeros(16, dtype="<i2")), include_origin=False)

    assert malformed.status_code == 400
    assert malformed.json()["error"] == "Audio could not be read as a WAV file."
    assert missing_origin.status_code == 403


def test_api_rejects_dns_rebinding_host():
    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://attacker.example",
            headers={"Origin": "http://attacker.example"},
        ) as client:
            return await client.get("/history"), await client.post("/settings", json={})

    get_response, post_response = asyncio.run(exercise())

    assert get_response.status_code == 403
    assert post_response.status_code == 403
    assert get_response.json()["error"] == "Untrusted host."


def test_overlapping_transcriptions_keep_processing_status(monkeypatch):
    events = []
    monkeypatch.setattr(api_server, "push_event", events.append)
    monkeypatch.setitem(api_server._state, "status", "idle")
    monkeypatch.setattr(api_server, "_web_active_transcriptions", 0)

    api_server._change_web_transcription_count(1)
    api_server._change_web_transcription_count(1)
    api_server._change_web_transcription_count(-1)

    assert api_server._state["status"] == "processing"
    assert events[-1] == {"type": "status", "value": "processing"}

    api_server._change_web_transcription_count(-1)

    assert api_server._state["status"] == "idle"
    assert events[-1] == {"type": "status", "value": "idle"}


def test_browser_pages_use_same_origin_api():
    index_html = (api_server._UI_DIR / "index.html").read_text(encoding="utf-8")
    onboarding_html = (api_server._UI_DIR / "onboarding.html").read_text(encoding="utf-8")

    assert "const API = window.location.origin;" in index_html
    assert "const API = window.location.origin;" in onboarding_html
    assert "id=\"audio-file\"" in index_html
    assert "API + '/transcribe'" in index_html
    assert 'onclick="copyText' not in index_html
    assert 'class="btn primary copy-clean"' in index_html
    assert "http://localhost:57327" not in index_html
    assert "http://localhost:57327" not in onboarding_html
