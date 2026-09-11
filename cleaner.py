
"""
cleaner.py — LLM post-processing with a 3-tier fallback chain.

Latency improvements over v1:
  • rules_clean()   — sub-millisecond regex cleanup for "instant" level.
                      No LLM, no network. Filler removal + capitalisation.
  • prewarm_ollama() — loads the model into memory at startup so the first
                       real call isn't penalised by a 2-3 s cold start.
  • LLM_TIMEOUT     — tightened to 2.5 s (was 6 s). If Ollama misses the
                       window the raw transcript is injected immediately.
  • SHORT_UTTERANCE — raised to 8 words (was 5). Short phrases are injected
                       after rules_clean only.

Cleanup levels:
  "instant"  → rules_clean() only — sub-ms, no LLM
  "none"     → raw transcript unchanged
  "light"    → LLM: grammar + filler only, exact words kept
  "medium"   → LLM: intent-aware — generates the message the user means
  "high"     → LLM: full professional polish
  "commander"→ LLM: composes a complete ready-to-send message from a
                     spoken intent description

Provider order (first to succeed wins):
  1. Docker LLM  — http://localhost:12434/engines/llama.cpp/v1
  2. Ollama      — http://localhost:11434
  3. rules_clean — graceful degradation (never fails)
"""

import re
import time
import threading
import requests

# ── Optional: ollama SDK as secondary fallback ─────────────────────── #
try:
    import ollama as _ollama_sdk
    _OLLAMA_SDK = True
except ImportError:
    _OLLAMA_SDK = False

# Tight timeout — if LLM hasn't responded in 2.5 s, inject raw immediately.
# Ollama warm (after prewarm) typically answers in 0.8–1.5 s.
LLM_TIMEOUT = 2.5   # seconds

# One-time availability cache set by main.py after startup probe.
_docker_llm_available: bool | None = None


def set_docker_llm_available(available: bool) -> None:
    global _docker_llm_available
    _docker_llm_available = available
    state = "✓ available" if available else "✗ unavailable — will use Ollama"
    print(f"[cleaner] Docker LLM cached as: {state}")


# ──────────────────────────────────────────────────────────────────── #
#  Rule-based fast cleanup  (sub-millisecond, no LLM)                   #
# ──────────────────────────────────────────────────────────────────── #

# Unambiguous filler words — safe to remove without LLM context.
# "like", "basically", "literally", "right" are intentionally excluded here
# because they double as ordinary verbs/adjectives in normal sentences.
# Those are handled by the LLM on medium/high/commander levels.
_FILLER_RE = re.compile(
    r"\b(um+|uh+|er+|hmm+|ah+|mhm+)\b"             # vocalisations
    r"|\b(you know|i mean|kind of|sort of)\b",       # unambiguous filler phrases
    re.IGNORECASE,
)

# Self-corrections: "at 4pm no wait 3pm" → keep only "3pm"
_CORRECTION_RE = re.compile(
    r"\b\w[\w\s,]*,?\s+(?:no wait|actually|i mean|sorry|i meant|correction)[,]?\s+",
    re.IGNORECASE,
)


def rules_clean(text: str) -> str:
    """
    Sub-millisecond rule-based cleanup.

    Does:
      • Removes unambiguous filler vocalisations (um, uh, hmm, you know, i mean…)
      • Strips obvious self-corrections ("no wait", "i meant")
      • Collapses extra whitespace
      • Capitalises first letter and standalone "i" → "I"
      • Adds a period if no terminal punctuation

    Does NOT call any LLM — safe to call on every utterance with zero latency.
    Context-dependent fillers ("like", "basically") are intentionally left for LLM.
    """
    if not text or not text.strip():
        return text

    cleaned = _FILLER_RE.sub(" ", text)
    cleaned = _CORRECTION_RE.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split()).strip()   # collapse whitespace

    if not cleaned:
        return text.strip()   # fillers emptied the string — return raw

    # Capitalise first letter
    cleaned = cleaned[0].upper() + cleaned[1:]

    # Capitalise standalone "i" → "I" (first-person pronoun)
    cleaned = re.sub(r'(?<!\w)i(?!\w)', 'I', cleaned)

    # Add terminal punctuation if absent
    if cleaned[-1] not in ".!?":
        cleaned += "."

    return cleaned


# ──────────────────────────────────────────────────────────────────── #
#  Ollama pre-warm                                                      #
# ──────────────────────────────────────────────────────────────────── #

def prewarm_ollama(
    model: str = "llama3.2:3b",
    base_url: str = "http://localhost:11434",
) -> None:
    """
    Load the Ollama model into memory before the first real transcription.

    Ollama's first call after a cold start loads the model from disk, adding
    2–3 s of latency.  Sending a tiny dummy prompt at startup front-loads
    this cost so the first real press gets a warm response.

    Call once at startup inside a daemon thread:
        threading.Thread(target=prewarm_ollama, args=(model, url), daemon=True).start()
    """
    try:
        print(f"[cleaner] Pre-warming Ollama '{model}'…")
        t0 = time.perf_counter()
        url = base_url.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "temperature": 0,
        }
        r = requests.post(url, json=payload, timeout=20)
        elapsed = time.perf_counter() - t0
        if r.ok:
            print(f"[cleaner] ✓ Ollama pre-warm done in {elapsed:.1f} s "
                  f"— first real call will be fast")
        else:
            print(f"[cleaner] ⚠ Ollama pre-warm returned HTTP {r.status_code} "
                  f"({elapsed:.1f} s) — first call may be slow")
    except Exception as e:
        print(f"[cleaner] ⚠ Ollama pre-warm failed ({e}) — first call may be slow")


# ──────────────────────────────────────────────────────────────────── #
#  System prompts                                                        #
# ──────────────────────────────────────────────────────────────────── #

LEVEL_PROMPTS: dict[str, str] = {

    # ── light: keep exact words, fix only grammar/filler ──────────── #
    "light": """\
You are a speech transcription corrector. Fix ONLY grammar and punctuation.

Rules:
1. Keep the speaker's EXACT words. Do NOT rephrase or restructure.
2. Fix: punctuation, capitalisation, verb tense, subject-verb agreement.
3. Remove filler words ONLY: um, uh, like (filler), you know, I mean, kind of, sort of.
4. If the speaker self-corrects ("at 4 pm, no wait, 3 pm"), keep only the final version.
5. Do NOT summarise, shorten, or paraphrase.
6. NEVER change pronouns. If the speaker says "I/me/my/mine/myself", keep them
   exactly as "I/me/my/mine/myself". Do NOT convert first-person to second or
   third person under any circumstance.
7. Output ONLY the corrected text. No preamble, no explanation, no quotes.\
""",

    # ── medium: understand intent, generate the right sentence ─────── #
    "medium": """\
You are a speech-to-text assistant that understands what the speaker MEANS.

Your task: Turn raw, imperfect speech into the exact sentence the speaker \
intends to produce.

Rules:
1. Understand the speaker's INTENT — not just their literal words.
   If they say "ask him if he completed his task", they want a message like
   "Hey, did you complete the task?" — generate THAT, not a cleaned version of
   what they said.
2. If they are narrating or dictating normally, produce a clear, natural sentence.
3. Remove all filler words: um, uh, like, you know, I mean, kind of, sort of.
4. Fix grammar, capitalisation, and punctuation.
5. Keep all specific details, names, numbers, and technical terms exactly as spoken.
6. Match the tone of the app context (casual for Slack, professional for email).
7. PRESERVE PRONOUNS EXACTLY. When the speaker says "I/me/my/mine/myself", the
   speaker is referring to themselves — keep those as "I/me/my/mine/myself".
   Never flip first-person to second person ("you/your") or third person
   ("he/she/they"). Example: "tell him I will be there" → "Hey, I will be
   there" — NOT "Hey, you will be there". The "I" always remains the speaker.
8. Output ONLY the final sentence. No preamble, no labels, no explanation.\
""",

    # ── high: maximum polish, professional brevity ──────────────────── #
    "high": """\
You are a professional editor. Rewrite the spoken text for maximum clarity.

Rules:
1. Understand the speaker's intent and express it as concisely as possible.
2. Remove ALL verbosity, repetition, and filler words.
3. Rewrite for professional readability — polished, complete sentences.
4. Keep every piece of information — just say it more efficiently.
5. Fix all grammar and punctuation.
6. PRESERVE PRONOUNS. When the speaker uses "I/me/my/mine/myself", they are
   referring to themselves — never convert those to second or third person.
   The speaker's perspective is the speaker's perspective.
7. Output ONLY the rewritten text. No preamble, no explanation.\
""",

    # ── commander: compose a ready-to-send message from spoken intent ─ #
    "commander": """\
You are a message composer. The user describes WHAT they want to send, not the message itself.

Your task: Compose the actual ready-to-send message the user intends.

Rules:
1. Read the user's intent and write the message from the user's perspective
   (the user is "I", the recipient is "you").
2. PRESERVE THE USER'S FIRST-PERSON PRONOUNS. If the user says "I/me/my/mine"
   in their dictation, they are referring to themselves (the sender). Keep
   those as "I/me/my/mine" in the composed message. Do NOT flip the user's
   "I" into "you" or any third-person reference.
3. Only the third-person target referred to by the user ("him", "her", "the
   team", "Sarah") becomes "you" in the composed message — never the user's
   own "I".
4. Sound natural and human — not robotic or corporate.
5. Be concise — say what needs to be said, nothing more.
6. Fix grammar and punctuation.
7. Match the tone of the context (casual → Slack, professional → email).
8. Output ONLY the composed message. No labels, no preamble, no explanation.

Examples:
  Input:  "ask him if he completed his task"
  Output: Hey, did you complete the task?

  Input:  "tell sarah the meeting is moved to 3pm"
  Output: Hi Sarah, just letting you know — the meeting has been moved to 3 PM.

  Input:  "let the team know we'll be late shipping this week"
  Output: Team, heads up — we're going to be a bit late shipping this week.

  Input:  "tell him I will be there at 3pm"
  Output: Hey, I'll be there at 3 PM.

  Input:  "ask the agent to send the report I attached"
  Output: Hey, can you send the report I attached?

  Input:  "let sarah know I finished the doc and I need her review"
  Output: Hi Sarah, I finished the doc and I need your review.\
""",
}

# App-specific tone hints appended to any level's system prompt
APP_CONTEXT_HINTS: dict[str, str] = {
    # Browsers / AI chat
    "Google Chrome":   "The user is typing in a browser — likely an AI chat interface (ChatGPT, Claude, etc.). Write it as a clear, well-formed prompt. Preserve ALL technical terms exactly.",
    "Safari":          "The user is typing in a browser. Write it as a clear, well-formed prompt.",
    "Firefox":         "The user is typing in a browser. Write it as a clear, well-formed prompt.",
    "Arc":             "The user is typing in an AI chat. Write it as a clear, well-formed prompt.",
    # Code editors
    "Code":            "The user is in VS Code. Preserve ALL technical terms, variable names, function names, and code syntax exactly as spoken.",
    "Cursor":          "The user is in Cursor (AI code editor). Preserve ALL technical terms exactly. This may be a prompt to an AI coding agent.",
    "Xcode":           "The user is in Xcode. Preserve technical terms and code syntax exactly.",
    # Communication
    "Slack":           "The user is writing a Slack message. Keep it casual, conversational, and direct.",
    "Mail":            "The user is writing an email. Use professional tone with proper sentence structure.",
    "Mimestream":      "The user is writing an email. Use professional tone.",
    "Microsoft Teams": "The user is writing a Teams message. Keep it professional but conversational.",
    # Notes / docs
    "Notion":          "The user is writing in Notion. Use clear structure. If the content sounds like a list, format it as a list.",
    "Obsidian":        "The user is taking notes in Obsidian. Keep it concise and structured.",
    "Notes":           "The user is taking personal notes. Keep it natural and concise.",
    # Terminal
    "Terminal":        "The user is in a terminal. Do NOT modify command-like phrases or technical strings.",
    "iTerm2":          "The user is in a terminal. Do NOT modify commands or technical strings.",
    "Warp":            "The user is in a terminal. Do NOT modify commands or technical strings.",
}

# Skip LLM for utterances this short (words) — apply rules_clean only
SHORT_UTTERANCE_WORDS = 8  # raised from 5

# Preamble patterns that leak into LLM output
_PREAMBLE_PATTERNS = [
    "here is the cleaned transcription:",
    "here's the cleaned transcription:",
    "here is the corrected transcription:",
    "here is the cleaned text:",
    "here's the cleaned text:",
    "here is the corrected text:",
    "here is the composed message:",
    "cleaned transcription:",
    "corrected text:",
    "composed message:",
    "output:",
    "message:",
]


def _strip_preamble(text: str) -> str:
    lower = text.lower()
    for pattern in _PREAMBLE_PATTERNS:
        if lower.startswith(pattern):
            text = text[len(pattern):].lstrip()
            break
    if "\n\n" in text:
        text = text.split("\n\n")[0]
    return text.strip()


def _build_system_prompt(app_context: str | None, level: str) -> str:
    base = LEVEL_PROMPTS.get(level, LEVEL_PROMPTS["light"])
    if not app_context:
        return base
    hint = APP_CONTEXT_HINTS.get(app_context, "")
    return f"{base}\n\nContext: {hint}" if hint else base


# ──────────────────────────────────────────────────────────────────── #
#  Provider implementations                                             #
# ──────────────────────────────────────────────────────────────────── #

def _call_docker_llm(raw, system_prompt, base_url, model, temperature, max_tokens):
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": raw},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = requests.post(url, json=payload, timeout=LLM_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_ollama_sdk(raw, system_prompt, model, temperature, max_tokens):
    response = _ollama_sdk.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": raw},
        ],
        options={"temperature": temperature, "num_predict": max_tokens},
    )
    return response["message"]["content"].strip()


def _call_ollama_http(raw, system_prompt, base_url, model, temperature, max_tokens):
    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": raw},
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
    level: str            = "light",
    # Docker LLM (primary)
    docker_llm_url: str  = "http://localhost:12434/engines/llama.cpp/v1",
    docker_llm_model: str = "",
    # Ollama (secondary)
    ollama_model: str     = "llama3.2:3b",
    ollama_base_url: str  = "http://localhost:11434",
    # Common
    temperature: float    = 0.1,
    max_tokens: int       = 300,
    app_context: str | None = None,
) -> str:
    """
    Clean a raw ASR transcript through the LLM fallback chain.

    level:
      "instant"   → rules_clean() only, sub-ms, no LLM
      "none"      → raw unchanged
      "light"     → LLM: grammar + filler, exact words kept
      "medium"    → LLM: intent-aware sentence generation
      "high"      → LLM: full professional polish
      "commander" → LLM: compose full message from spoken intent
    """
    if not raw_transcript or not raw_transcript.strip():
        return raw_transcript

    # ── Instant / None: bypass LLM entirely ──────────────────────── #
    if level == "none":
        print("[cleaner] Level=none — returning raw.")
        return raw_transcript.strip()

    if level == "instant":
        result = rules_clean(raw_transcript)
        print(f"[cleaner] Instant rules → {repr(result[:80])}")
        return result

    # ── Short utterance: use rules regardless of level ───────────── #
    # Commander mode always goes through LLM — short or not.
    word_count = len(raw_transcript.split())
    if word_count <= SHORT_UTTERANCE_WORDS and level != "commander":
        result = rules_clean(raw_transcript)
        print(f"[cleaner] Short ({word_count} w) → rules: {repr(result[:80])}")
        return result

    system_prompt = _build_system_prompt(app_context, level)
    if app_context:
        print(f"[cleaner] Context: '{app_context}'  Level: {level}")

    result: dict = {"text": None}

    def _worker():
        global _docker_llm_available

        # ── Tier 1: Docker LLM ────────────────────────────────────── #
        if _docker_llm_available is not False:
            effective_model = docker_llm_model or _detect_docker_model(docker_llm_url)
            if effective_model:
                try:
                    print(f"[cleaner] Tier 1 → Docker LLM (model={effective_model})")
                    cleaned = _call_docker_llm(
                        raw_transcript, system_prompt,
                        docker_llm_url, effective_model,
                        temperature, max_tokens,
                    )
                    result["text"] = _strip_preamble(cleaned)
                    _docker_llm_available = True
                    print(f"[cleaner] ✓ Docker: {repr(result['text'][:80])}")
                    return
                except Exception as e:
                    print(f"[cleaner] ✗ Docker LLM: {e}")
                    _docker_llm_available = False
            else:
                _docker_llm_available = False
        else:
            print("[cleaner] Skipping Docker LLM (known unavailable).")

        # ── Tier 2: Ollama ────────────────────────────────────────── #
        try:
            if _OLLAMA_SDK:
                print(f"[cleaner] Tier 2 → Ollama SDK ({ollama_model})")
                cleaned = _call_ollama_sdk(
                    raw_transcript, system_prompt,
                    ollama_model, temperature, max_tokens,
                )
            else:
                print(f"[cleaner] Tier 2 → Ollama HTTP ({ollama_base_url}, {ollama_model})")
                cleaned = _call_ollama_http(
                    raw_transcript, system_prompt,
                    ollama_base_url, ollama_model,
                    temperature, max_tokens,
                )
            result["text"] = _strip_preamble(cleaned)
            print(f"[cleaner] ✓ Ollama: {repr(result['text'][:80])}")
            return
        except Exception as e:
            print(f"[cleaner] ✗ Ollama: {e}")

        # ── Tier 3: rules fallback (never fails) ──────────────────── #
        print("[cleaner] All LLMs unavailable — using rules_clean.")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=LLM_TIMEOUT + 0.5)  # slightly over so timeout log is meaningful

    if t.is_alive():
        print(f"[cleaner] ⏱ LLM timeout ({LLM_TIMEOUT} s) — falling back to rules.")
        return rules_clean(raw_transcript)

    if result["text"] is not None:
        return result["text"]

    # Tier 3 final fallback
    return rules_clean(raw_transcript)


def _detect_docker_model(base_url: str) -> str:
    try:
        url = base_url.rstrip("/") + "/models"
        resp = requests.get(url, timeout=2)
        resp.raise_for_status()
        models = resp.json().get("data", [])
        if models:
            name = models[0].get("id", "")
            print(f"[cleaner] Auto-detected Docker model: '{name}'")
            return name
    except Exception:
        pass
    return ""
