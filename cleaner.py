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

import threading
import requests
import json

# ── Optional: ollama SDK as secondary fallback ─────────────────────── #
try:
    import ollama as _ollama_sdk
    _OLLAMA_SDK = True
except ImportError:
    _OLLAMA_SDK = False

LLM_TIMEOUT = 6   # seconds before we give up and return raw (was 10)

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

# Light (default) — grammar + filler removal, keep exact words
BASE_SYSTEM_PROMPT = """\
You are a speech transcription corrector. You fix ONLY grammar and punctuation — nothing else.

Strict rules:
1. Keep the speaker's EXACT words and vocabulary. Do NOT rephrase, reword, or restructure sentences.
2. Only change: punctuation, capitalisation, verb tense agreement, and subject-verb agreement.
3. Remove filler words ONLY: um, uh, like (filler), you know, I mean, kind of, sort of.
4. If the speaker self-corrects ("at 4pm, no wait, 3pm"), keep only their final intended version.
5. Do NOT summarise, shorten, paraphrase, or omit anything the speaker said.
6. Output ONLY the corrected text. No preamble, no explanation, no quotation marks.
7. If the input needs no changes, return it exactly as-is.\
"""

# Level-specific prompts
LEVEL_PROMPTS = {
    "light": BASE_SYSTEM_PROMPT,

    "medium": """\
You are a speech transcription editor. Improve clarity and readability.

Rules:
1. Remove all filler words: um, uh, like, you know, I mean, kind of, sort of.
2. Fix grammar, punctuation, and capitalisation.
3. Lightly improve sentence structure for clarity — minor rephrasing is OK.
4. Keep all the speaker's key ideas and meaning intact. Do NOT omit information.
5. Output ONLY the improved text. No preamble, no explanation.\
""",

    "high": """\
You are a professional editor. Rewrite for maximum clarity and brevity.

Rules:
1. Remove ALL verbosity, repetition, and filler words.
2. Rewrite for professional readability — concise, polished, complete sentences.
3. Keep every piece of information — just express it more efficiently.
4. Fix all grammar and punctuation.
5. Output ONLY the rewritten text. No preamble, no explanation.\
""",
}

# App-specific tone addenda
APP_CONTEXT_HINTS = {
    # Browsers / AI chat interfaces — the primary use case
    "Google Chrome":   "The user is typing a prompt into an AI assistant (ChatGPT, Claude, Perplexity, etc.). Write it as a clear, well-formed prompt. Preserve all technical terms and specific details exactly.",
    "Safari":          "The user is typing a prompt into an AI assistant in a browser. Write it as a clear, well-formed prompt. Preserve all technical terms and specific details exactly.",
    "Firefox":         "The user is typing a prompt into a browser. Write it as a clear, well-formed prompt.",
    "Arc":             "The user is typing a prompt into an AI assistant. Write it as a clear, well-formed prompt.",
    # Code editors
    "Code":            "The user is in VS Code. Preserve ALL technical terms, variable names, function names, and code syntax exactly as spoken. Do not rephrase technical content.",
    "Cursor":          "The user is in Cursor (AI code editor). Preserve ALL technical terms exactly. This may be a prompt to an AI coding agent — keep it precise.",
    "Xcode":           "The user is in Xcode. Preserve technical terms and code syntax exactly.",
    # Communication
    "Slack":           "The user is writing a Slack message. Keep it casual, conversational, and direct.",
    "Mail":            "The user is writing an email. Use professional tone with proper sentence structure.",
    "Mimestream":      "The user is writing an email. Use professional tone.",
    "Microsoft Teams": "The user is writing a Teams message. Keep it professional but conversational.",
    # Notes / docs
    "Notion":          "The user is writing a Notion note or document. Use clear structure. If the content sounds like a list, format it as a list.",
    "Obsidian":        "The user is taking notes in Obsidian. Keep it concise and structured.",
    "Notes":           "The user is taking personal notes. Keep it natural and concise.",
    # Terminal
    "Terminal":        "The user is in a terminal. Do NOT modify command-like phrases or technical strings. Return minimal cleanup only.",
    "iTerm2":          "The user is in a terminal. Do NOT modify commands or technical strings.",
    "Warp":            "The user is in a terminal. Do NOT modify commands or technical strings.",
}

SHORT_UTTERANCE_WORDS = 5  # skip LLM for <= N words (inject raw instantly)

# Common LLM preamble patterns to strip from responses
_PREAMBLE_PATTERNS = [
    "here is the cleaned transcription:",
    "here's the cleaned transcription:",
    "here is the corrected transcription:",
    "here is the cleaned text:",
    "here's the cleaned text:",
    "here is the corrected text:",
    "cleaned transcription:",
    "corrected text:",
    "output:",
]


def _strip_preamble(text: str) -> str:
    """Strip common LLM preamble phrases that leak into the output."""
    lower = text.lower()
    for pattern in _PREAMBLE_PATTERNS:
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
    resp = requests.post(url, json=payload, timeout=LLM_TIMEOUT)
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
    resp = requests.post(url, json=payload, timeout=LLM_TIMEOUT)
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

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=LLM_TIMEOUT + 1)

    if t.is_alive():
        print("[cleaner] Timeout — returning raw transcript.")
        return raw_transcript

    return result["text"] if result["text"] is not None else raw_transcript


def _detect_docker_model(base_url: str) -> str:
    """
    Auto-detect the model name from your Docker LLM's /models endpoint.
    Returns empty string if unavailable.
    """
    try:
        url = base_url.rstrip("/") + "/models"
        resp = requests.get(url, timeout=3)
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
