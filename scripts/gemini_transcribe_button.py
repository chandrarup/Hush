"""Small button-driven Gemini 3.5 Transcribe test app.

Usage:
    gcloud auth application-default login
    uv run --with google-genai python scripts/gemini_transcribe_button.py \
        --project project-25e4d84e-0cf5-4f81-89b --language en-US

Open the printed local URL, click once to start recording from the default
microphone, click again to stop and send the captured WAV to Gemini 3.5
Transcribe.
"""

from __future__ import annotations

import argparse
import os
import queue
import sys
import threading
import wave
from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from voiceflow.core.audio import AudioRecorder, SAMPLE_RATE
from voiceflow.core.vad import audio_duration, trim_silence


DEFAULT_LOCATION = "global"
DEFAULT_MODEL = "gemini-3.5-transcribe-preview"
MIN_AUDIO_SECONDS = 0.3


def float32_audio_to_wav_bytes(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Encode mono float32 audio into 16-bit PCM WAV bytes."""
    if audio.ndim > 1:
        audio = audio[:, 0]
    clipped = np.clip(audio.astype(np.float32), -1.0, 1.0)
    pcm = (clipped * 32767).astype("<i2")

    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())
        return buffer.getvalue()


def response_text(response) -> str:
    """Extract plain transcript text from the Gen AI SDK response shape."""
    text = getattr(response, "text", None)
    if text:
        return str(text).strip()

    parts = getattr(response, "parts", []) or []
    texts: list[str] = []
    for part in parts:
        part_text = getattr(part, "text", None)
        if part_text:
            texts.append(str(part_text))
            continue

        audio_tx = getattr(part, "audio_transcription", None)
        audio_text = getattr(audio_tx, "text", None) if audio_tx else None
        if audio_text:
            texts.append(str(audio_text))

    return " ".join(t.strip() for t in texts if t and t.strip()).strip()


@dataclass
class GeminiTranscribeSettings:
    project: str
    location: str = DEFAULT_LOCATION
    model: str = DEFAULT_MODEL
    language: str | None = None
    diarization: bool = False
    word_timestamps: bool = False
    custom_vocabulary: tuple[str, ...] = ()


class GeminiTranscribeClient:
    def __init__(self, settings: GeminiTranscribeSettings):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "google-genai is not installed. Run:\n"
                "  uv run --with google-genai python scripts/gemini_transcribe_button.py "
                "--project YOUR_PROJECT_ID"
            ) from exc

        self._types = types
        self._settings = settings
        self._client = genai.Client(
            enterprise=True,
            project=settings.project,
            location=settings.location,
        )

    def transcribe(self, wav_bytes: bytes) -> str:
        types = self._types
        tx_config_kwargs = {
            "diarization": self._settings.diarization,
            "word_timestamp": self._settings.word_timestamps,
        }
        if self._settings.language:
            tx_config_kwargs["language_codes"] = [self._settings.language]
        if self._settings.custom_vocabulary:
            tx_config_kwargs["custom_vocabulary"] = list(self._settings.custom_vocabulary)

        response = self._client.models.generate_content(
            model=self._settings.model,
            contents=[
                types.Part.from_bytes(
                    data=wav_bytes,
                    mime_type="audio/wav",
                )
            ],
            config=types.GenerateContentConfig(
                audio_transcription_config=types.AudioTranscriptionConfig(
                    **tx_config_kwargs
                )
            ),
        )
        return response_text(response)


class GeminiTranscribeWebApp:
    def __init__(self, settings: GeminiTranscribeSettings):
        self._events: queue.Queue[tuple[str, str]] = queue.Queue()
        self._settings = settings
        self._recorder = AudioRecorder(sample_rate=SAMPLE_RATE, channels=1)
        self._client: GeminiTranscribeClient | None = None
        self._recording = False
        self._busy = False
        self._lock = threading.Lock()
        self._last_status = "Ready. Click Start, speak, then click Stop."
        self._transcripts: list[str] = []

    def run(self, host: str, port: int, open_browser: bool) -> None:
        try:
            import uvicorn
            from fastapi import FastAPI
            from fastapi.responses import HTMLResponse, JSONResponse
        except ImportError as exc:
            raise RuntimeError(
                "FastAPI/uvicorn are not installed. Run: uv sync --no-dev"
            ) from exc

        app = FastAPI()

        @app.get("/", response_class=HTMLResponse)
        def index():
            return HTMLResponse(self._page_html())

        @app.get("/state")
        def state():
            return JSONResponse(self._state())

        @app.post("/start")
        def start():
            ok, message = self._start_recording()
            status = 200 if ok else 400
            return JSONResponse(self._state(message=message), status_code=status)

        @app.post("/stop")
        def stop():
            ok, message = self._stop_and_transcribe()
            status = 200 if ok else 400
            return JSONResponse(self._state(message=message), status_code=status)

        url = f"http://{host}:{port}"
        print(f"[gemini] Open {url} to test Gemini 3.5 Transcribe.")
        if open_browser:
            try:
                import webbrowser

                threading.Timer(0.5, lambda: webbrowser.open(url)).start()
            except Exception:
                pass

        uvicorn.run(app, host=host, port=port, log_level="warning")

    def _state(self, message: str | None = None) -> dict:
        self._drain_events()
        with self._lock:
            return {
                "status": message or self._last_status,
                "recording": self._recording,
                "busy": self._busy,
                "transcripts": list(self._transcripts),
            }

    def _start_recording(self) -> tuple[bool, str]:
        with self._lock:
            if self._busy:
                return False, "Still transcribing. Wait for the current request to finish."
            if self._recording:
                return True, "Already recording."

        try:
            self._recorder.start()
        except Exception as exc:
            message = f"Could not open microphone: {exc}"
            self._set_status(message)
            return False, message

        with self._lock:
            self._recording = True
        message = "Recording. Speak now, then click Stop."
        self._set_status(message)
        return True, message

    def _stop_and_transcribe(self) -> tuple[bool, str]:
        with self._lock:
            if not self._recording:
                return False, "Not recording yet."
            self._recording = False
            self._busy = True

        message = "Stopping microphone and sending audio to Gemini..."
        self._set_status(message)

        audio = self._recorder.stop()
        threading.Thread(
            target=self._transcribe_audio,
            args=(audio,),
            daemon=True,
            name="gemini-transcribe",
        ).start()
        return True, message

    def _transcribe_audio(self, audio: np.ndarray) -> None:
        try:
            audio = trim_silence(audio)
            duration = audio_duration(audio)
            if duration < MIN_AUDIO_SECONDS:
                self._events.put(("error", "Audio was too short to transcribe."))
                return

            if self._client is None:
                self._client = GeminiTranscribeClient(self._settings)

            wav_bytes = float32_audio_to_wav_bytes(audio)
            transcript = self._client.transcribe(wav_bytes)
            if not transcript:
                transcript = "(Gemini returned an empty transcript.)"
            self._events.put(("transcript", transcript))
        except Exception as exc:
            self._events.put(("error", f"{type(exc).__name__}: {exc}"))

    def _drain_events(self) -> None:
        while True:
            try:
                kind, message = self._events.get_nowait()
            except queue.Empty:
                break

            if kind == "transcript":
                with self._lock:
                    self._transcripts.append(message)
                self._set_status("Ready. Click Start for another recording.")
            else:
                self._set_status(message)

            with self._lock:
                self._busy = False

    def _set_status(self, value: str) -> None:
        with self._lock:
            self._last_status = value

    def _page_html(self) -> str:
        project = escape(self._settings.project)
        model = escape(self._settings.model)
        location = escape(self._settings.location)
        language = escape(self._settings.language or "auto")
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gemini 3.5 Transcribe Test</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f4ed;
      color: #17201b;
    }}
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; }}
    main {{ width: min(760px, calc(100vw - 32px)); }}
    h1 {{ font-size: 1.35rem; margin: 0 0 16px; }}
    .meta {{ color: #55635b; font-size: .92rem; margin-bottom: 16px; }}
    button {{
      width: 100%; height: 56px; border: 0; border-radius: 8px;
      background: #1f7a4d; color: white; font-size: 1rem; font-weight: 650;
      cursor: pointer;
    }}
    button.recording {{ background: #b63b32; }}
    button:disabled {{ background: #758279; cursor: progress; }}
    #status {{ margin: 14px 0; min-height: 24px; color: #2e3a33; }}
    #transcripts {{
      min-height: 220px; background: rgba(255,255,255,.72); border: 1px solid #d8d0c2;
      border-radius: 8px; padding: 14px; white-space: pre-wrap;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{ background: #151815; color: #edf2ec; }}
      .meta {{ color: #aab7af; }}
      #status {{ color: #cbd8cf; }}
      #transcripts {{ background: rgba(255,255,255,.06); border-color: #394238; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Gemini 3.5 Transcribe Test</h1>
    <div class="meta">Project: {project} | Model: {model} | Location: {location} | Language: {language}</div>
    <button id="toggle" type="button">Start recording</button>
    <div id="status">Ready.</div>
    <div id="transcripts"></div>
  </main>
  <script>
    const button = document.getElementById("toggle");
    const statusEl = document.getElementById("status");
    const transcriptsEl = document.getElementById("transcripts");

    async function refresh() {{
      const state = await fetch("/state").then(r => r.json());
      render(state);
    }}

    function render(state) {{
      statusEl.textContent = state.status;
      button.disabled = state.busy;
      button.classList.toggle("recording", state.recording);
      button.textContent = state.busy
        ? "Transcribing..."
        : state.recording
          ? "Stop and transcribe"
          : "Start recording";
      transcriptsEl.textContent = state.transcripts.length
        ? state.transcripts.join("\\n\\n")
        : "Transcripts will appear here.";
    }}

    button.addEventListener("click", async () => {{
      const state = await fetch(button.classList.contains("recording") ? "/stop" : "/start", {{
        method: "POST"
      }}).then(r => r.json());
      render(state);
    }});

    refresh();
    setInterval(refresh, 800);
  </script>
</body>
</html>"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record speech with a button and transcribe it with Gemini 3.5 Transcribe."
    )
    parser.add_argument(
        "--project",
        default=os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_PROJECT_ID"),
        help="Google Cloud project ID. Defaults to GOOGLE_CLOUD_PROJECT or GOOGLE_PROJECT_ID.",
    )
    parser.add_argument("--location", default=DEFAULT_LOCATION)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--language", default="en-US", help="BCP-47 language hint, e.g. en-US.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=57328)
    parser.add_argument("--no-open", action="store_true", help="Print the URL without opening a browser.")
    parser.add_argument("--diarization", action="store_true")
    parser.add_argument("--word-timestamps", action="store_true")
    parser.add_argument(
        "--vocab",
        action="append",
        default=[],
        help="Custom vocabulary hint. Pass multiple times for multiple terms.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.project:
        raise SystemExit(
            "Missing Google Cloud project. Pass --project YOUR_PROJECT_ID or set GOOGLE_CLOUD_PROJECT."
        )

    settings = GeminiTranscribeSettings(
        project=args.project,
        location=args.location,
        model=args.model,
        language=args.language,
        diarization=args.diarization,
        word_timestamps=args.word_timestamps,
        custom_vocabulary=tuple(args.vocab),
    )
    GeminiTranscribeWebApp(settings).run(
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
    )


if __name__ == "__main__":
    main()
