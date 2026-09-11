"""
transcriber.py — ASR with dual-engine support.

Engine A: NVIDIA Parakeet TDT 0.6B v3  (BEST for English on Apple Silicon)
  - 10× faster than Whisper large-v3-turbo
  - Higher accuracy (WER 6.32% vs 7.44%)
  - Runs on Apple Silicon GPU via MPS backend
  - Requires: pip install torch transformers

Engine B: faster-whisper  (fallback, supports 100+ languages)
  - Good multilingual support
  - Runs on CPU (int8) or CUDA GPU (float16)
  - Requires: pip install faster-whisper

Config controls which engine is used:
  [asr]
  engine = "parakeet"      # or "whisper"
  model = "nvidia/parakeet-tdt-0.6b-v3"   # for parakeet
  model = "large-v3-turbo"                 # for whisper
"""

import numpy as np

# ── Engine A: Parakeet via HuggingFace transformers ───────────────── #
try:
    import torch
    from transformers import pipeline as hf_pipeline
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False
    torch = None

# ── Engine B: faster-whisper ──────────────────────────────────────── #
try:
    from faster_whisper import WhisperModel
    _FASTER_WHISPER_AVAILABLE = True
except ImportError:
    _FASTER_WHISPER_AVAILABLE = False
    WhisperModel = None


# ──────────────────────────────────────────────────────────────────── #
#  Device detection                                                     #
# ──────────────────────────────────────────────────────────────────── #

def _best_torch_device() -> str:
    """Return the best available torch device: mps > cuda > cpu."""
    if torch is None:
        return "cpu"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon GPU
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _best_ctranslate_device() -> tuple[str, str]:
    """Return (device, compute_type) for faster-whisper / ctranslate2."""
    if torch is not None and torch.cuda.is_available():
        return "cuda", "float16"
    return "cpu", "int8"


# ──────────────────────────────────────────────────────────────────── #
#  Engine A — Parakeet                                                  #
# ──────────────────────────────────────────────────────────────────── #

class ParakeetTranscriber:
    """
    NVIDIA Parakeet TDT 0.6B v3 via HuggingFace transformers.
    10× faster than Whisper large-v3-turbo on Apple Silicon.
    English-only (+ 25 European languages as of v3).

    First run downloads ~2.4 GB, cached in ~/.cache/huggingface/.
    """

    def __init__(self, model_name: str = "nvidia/parakeet-tdt-0.6b-v3"):
        if not _TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "transformers/torch not installed.\n"
                "Run: pip install torch transformers"
            )

        device = _best_torch_device()
        print(
            f"[transcriber] Loading Parakeet '{model_name}' on {device}…\n"
            f"  First run downloads ~2.4 GB (cached after that)."
        )

        # HuggingFace ASR pipeline handles everything
        self._pipe = hf_pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=device,
        )
        self.sample_rate = 16000
        print(f"[transcriber] Parakeet ready on {device}.")

    def transcribe(self, audio: np.ndarray, vocab: list[str] | None = None) -> str:
        """
        Transcribe float32 numpy array at 16kHz.
        vocab is accepted for API compatibility but not used by Parakeet.
        """
        if len(audio) == 0:
            return ""
        try:
            # Pipeline expects {"array": ..., "sampling_rate": ...}
            result = self._pipe({"array": audio, "sampling_rate": self.sample_rate})
            text = result.get("text", "").strip()
            print(f"[transcriber] Parakeet raw: {repr(text)}")
            return text
        except Exception as e:
            print(f"[transcriber] Parakeet error: {e}")
            return ""


# ──────────────────────────────────────────────────────────────────── #
#  Engine B — Whisper (faster-whisper)                                  #
# ──────────────────────────────────────────────────────────────────── #

class WhisperTranscriber:
    """
    faster-whisper wrapper. Good fallback and handles 100+ languages.
    """

    def __init__(
        self,
        model_name: str = "large-v3-turbo",
        language: str = "en",
        compute_type_gpu: str = "float16",
        compute_type_cpu: str = "int8",
        beam_size: int = 5,
    ):
        if not _FASTER_WHISPER_AVAILABLE:
            raise RuntimeError(
                "faster-whisper not installed. Run: pip install faster-whisper"
            )

        self.language = language
        self.beam_size = beam_size

        device, compute_type = _best_ctranslate_device()
        # Honour explicit config overrides
        if device == "cuda":
            compute_type = compute_type_gpu
        else:
            compute_type = compute_type_cpu

        print(
            f"[transcriber] Loading Whisper '{model_name}' "
            f"on {device} ({compute_type})…"
        )
        try:
            self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
            print(f"[transcriber] Whisper '{model_name}' ready.")
        except Exception as e:
            print(f"[transcriber] GPU init failed ({e}), retrying on CPU…")
            self.model = WhisperModel(model_name, device="cpu", compute_type="int8")
            print(f"[transcriber] Whisper '{model_name}' ready on CPU.")

    def transcribe(self, audio: np.ndarray, vocab: list[str] | None = None) -> str:
        if len(audio) == 0:
            return ""

        initial_prompt = ", ".join(vocab) if vocab else None

        try:
            segments, _ = self.model.transcribe(
                audio,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=True,
                initial_prompt=initial_prompt,
            )
            texts = [seg.text.strip() for seg in segments]
            raw = " ".join(t for t in texts if t)
            print(f"[transcriber] Whisper raw: {repr(raw)}")
            return raw
        except Exception as e:
            print(f"[transcriber] Whisper error: {e}")
            return ""


# ──────────────────────────────────────────────────────────────────── #
#  Factory                                                              #
# ──────────────────────────────────────────────────────────────────── #

def create_transcriber(
    engine: str = "auto",
    model: str = "",
    language: str = "en",
    compute_type_gpu: str = "float16",
    compute_type_cpu: str = "int8",
):
    """
    Create the best available transcriber based on engine config.

    engine = "auto"     → try Parakeet first (faster), fall back to Whisper
    engine = "parakeet" → use Parakeet (English, fastest)
    engine = "whisper"  → use Whisper (multilingual)

    model = ""          → use sensible default for chosen engine
    """
    # Auto: prefer Parakeet when a supported accelerator is available.
    if engine == "auto":
        engine = "parakeet" if _TRANSFORMERS_AVAILABLE and _best_torch_device() != "cpu" else "whisper"
        print(f"[transcriber] Auto-selected engine: {engine}")

    if engine == "parakeet":
        effective_model = model or "nvidia/parakeet-tdt-0.6b-v3"
        try:
            return ParakeetTranscriber(effective_model)
        except Exception as e:
            print(f"[transcriber] Parakeet unavailable ({e}), falling back to Whisper.")
            engine = "whisper"

    # Whisper
    effective_model = model or "large-v3-turbo"
    return WhisperTranscriber(
        model_name=effective_model,
        language=language,
        compute_type_gpu=compute_type_gpu,
        compute_type_cpu=compute_type_cpu,
    )
