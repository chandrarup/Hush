"""
cleaner.py — LLM post-processing with a 3-tier fallback chain.

Priority order (exactly like AlphaScanner):
  1. Docker LLM  — http://localhost:12434/engines/llama.cpp/v1  (your existing setup)
  2. Ollama      — http://localhost:11434  (if installed)
  3. Raw         — return transcript unchanged (graceful degradation)

The Docker LLM uses the same OpenAI-compatible API you used in AlphaScanner:
  POST /engines/llama.cpp/v1/chat/completions
  {"model": "...", "messages": [...], "temperature": 0.1}

Context-aware prompting: pass app_context (e.g. "Slack", "Code", "Mail")
to get output formatted appropriately for the target app.
"""

import requests

from ..prompts.cleanup import (
    APP_CONTEXT_HINTS,
    BASE_SYSTEM_PROMPT,
    LEVEL_PROMPTS,
    PREAMBLE_PATTERNS,
    SHORT_UTTERANCE_WORDS,
)

# ── Optional: ollama SDK as secondary fallback ─────────────────────── #
try:
    import ollama as _ollama_sdk
    _OLLAMA_SDK = True
except ImportError:
    _OLLAMA_SDK = False

# One-time availability cache — set by main.py after the startup probe.
# None = unknown (will probe once), True = available, False = skip entirely.
_docker_llm_available: bool | None = None


def set_docker_llm_available(available: bool) -> None:
    """Called by main.py after the startup Docker LLM check."""
    global _docker_llm_available
    _docker_llm_available = available
    state = "✓ available" if available else "✗ unavailable — will use Ollama"
    print(f"[cleaner] Docker LLM cached as: {state}")

# ──────────────────────────────────────────────────────────────────── #
#  System prompt                                                        #
# ──────────────────────────────────────────────────────────────────── #

def _strip_preamble(text: str) -> str:
    """Strip common LLM preamble phrases that leak into the output."""
    lower = text.lower()
    for pattern in PREAMBLE_PATTERNS:
        if lower.startswith(pattern):
            text = text[len(pattern):].lstrip()
            break
    # Also strip trailing meta-commentary after a double newline
    if "\n\n" in text:
        text = text.split("\n\n")[0]
    return text.strip()


def _build_system_prompt(app_context: str | None, level: str = "light") -> str:
    """Build the system prompt for the given level with an optional app-context addendum."""
    base = LEVEL_PROMPTS.get(level, BASE_SYSTEM_PROMPT)
    if not app_context:
        return base
    hint = APP_CONTEXT_HINTS.get(app_context, "")
    if hint:
        return f"{base}\n\nContext: {hint}"
    return base


# ──────────────────────────────────────────────────────────────────── #
#  Provider implementations                                             #
# ──────────────────────────────────────────────────────────────────── #

def _call_docker_llm(
    raw: str,
    system_prompt: str,
    base_url: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Call your Docker LLM using the same pattern as AlphaScanner:
      POST {base_url}/chat/completions
    base_url should be like: http://localhost:12434/engines/llama.cpp/v1
    """
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Clean this transcription:\n{raw}"},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _call_ollama_sdk(
    raw: str,
    system_prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call local Ollama via its Python SDK."""
    response = _ollama_sdk.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Clean this transcription:\n{raw}"},
        ],
        options={"temperature": temperature, "num_predict": max_tokens},
    )
    return response["message"]["content"].strip()


def _call_ollama_http(
    raw: str,
    system_prompt: str,
    base_url: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call Ollama via HTTP (OpenAI-compatible endpoint) — no SDK needed."""
    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Clean this transcription:\n{raw}"},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ──────────────────────────────────────────────────────────────────── #
#  Public API                                                           #
# ──────────────────────────────────────────────────────────────────── #

def clean_transcript(
    raw_transcript: str,
    # Cleanup level
    level: str            = "light",   # none | light | medium | high
    # Docker LLM (primary — your existing setup)
    docker_llm_url: str  = "http://localhost:12434/engines/llama.cpp/v1",
    docker_llm_model: str = "",
    # Ollama (secondary fallback)
    ollama_model: str     = "llama3.2:3b",
    ollama_base_url: str  = "http://localhost:11434",
    # Common
    temperature: float    = 0.1,
    max_tokens: int       = 500,
    app_context: str | None = None,
) -> str:
    """
    Clean raw Whisper/Parakeet transcript through the LLM fallback chain.

    level: "none"   → return raw transcript unchanged
           "light"  → grammar + filler removal only (default)
           "medium" → clarity + mild restructuring
           "high"   → full polish, brevity
    """
    if not raw_transcript or not raw_transcript.strip():
        return raw_transcript

    # None: skip LLM entirely
    if level == "none":
        print("[cleaner] Level=none — returning raw transcript.")
        return raw_transcript.strip()

    # Short utterance bypass
    word_count = len(raw_transcript.split())
    if word_count <= SHORT_UTTERANCE_WORDS:
        print(f"[cleaner] Short utterance ({word_count} words) — skipping LLM.")
        return raw_transcript.strip()

    system_prompt = _build_system_prompt(app_context, level)
    if app_context:
        print(f"[cleaner] Context: '{app_context}'  Level: {level}")

    result: dict = {"text": None, "error": None}

    def _worker():
        global _docker_llm_available

        # ── Tier 1: Docker LLM — skip if known unavailable ─────────── #
        if _docker_llm_available is not False:
            effective_model = docker_llm_model
            if not effective_model:
                effective_model = _detect_docker_model(docker_llm_url)

            if effective_model:
                try:
                    print(f"[cleaner] Tier 1 → Docker LLM (model={effective_model})")
                    cleaned = _call_docker_llm(
                        raw_transcript, system_prompt,
                        docker_llm_url, effective_model,
                        temperature, max_tokens,
                    )
                    cleaned = _strip_preamble(cleaned)
                    result["text"] = cleaned
                    _docker_llm_available = True   # confirmed working
                    print(f"[cleaner] ✓ Docker LLM: {repr(cleaned[:80])}")
                    return
                except Exception as e:
                    print(f"[cleaner] ✗ Docker LLM failed: {e}")
                    _docker_llm_available = False  # don't retry next time
            else:
                # No model detected — mark as unavailable
                _docker_llm_available = False
        else:
            print("[cleaner] Skipping Docker LLM (known unavailable).")

        # ── Tier 2: Ollama (SDK or HTTP) ──────────────────────────── #
        try:
            if _OLLAMA_SDK:
                print(f"[cleaner] Tier 2 → Ollama SDK (model={ollama_model})")
                cleaned = _call_ollama_sdk(
                    raw_transcript, system_prompt,
                    ollama_model, temperature, max_tokens,
                )
            else:
                print(f"[cleaner] Tier 2 → Ollama HTTP ({ollama_base_url}, model={ollama_model})")
                cleaned = _call_ollama_http(
                    raw_transcript, system_prompt,
                    ollama_base_url, ollama_model,
                    temperature, max_tokens,
                )
            cleaned = _strip_preamble(cleaned)
            result["text"] = cleaned
            print(f"[cleaner] ✓ Ollama: {repr(cleaned[:80])}")
            return
        except Exception as e:
            print(f"[cleaner] ✗ Ollama failed: {e}")

        # ── Tier 3: Raw passthrough ────────────────────────────────── #
        print("[cleaner] All LLMs unavailable — using raw transcript.")
        result["error"] = "all_failed"

    # Cleanup is part of the committed pipeline result. Wait for the provider
    # to finish before the caller injects text or persists history.
    _worker()
    return result["text"] if result["text"] is not None else raw_transcript


def _detect_docker_model(base_url: str) -> str:
    """
    Auto-detect the model name from your Docker LLM's /models endpoint.
    Returns empty string if unavailable.
    """
    try:
        url = base_url.rstrip("/") + "/models"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", [])
        if models:
            name = models[0].get("id", "")
            print(f"[cleaner] Auto-detected Docker LLM model: '{name}'")
            return name
    except Exception:
        pass
    return ""
