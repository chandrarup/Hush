# VoiceFlow Agent Guide

## Project purpose

VoiceFlow is a local push-to-talk dictation application. A user holds a global
hotkey, speaks, releases the key, and receives cleaned text in the currently
focused application. The application currently runs locally and supports local
audio capture, Parakeet or Whisper transcription, local Docker/Ollama cleanup,
local history, snippets, a FastAPI dashboard, and platform-specific text
injection.

The long-term goal is a hybrid architecture:

```text
Desktop agent
  microphone, hotkey, permissions, active app, tray, text injection
                              |
                              v
Cloud backend
  authentication, jobs, transcription, cleanup, history, synchronization
```

The desktop agent must remain usable in local-only mode. Cloud migration must
replace adapters, not rewrite the dictation domain workflow.

## Current repository state

The current branch has the local architecture foundation and a backend-only
FastAPI seam. It does not yet contain a production GCP deployment.

Implemented:

- `DictationWorkflow` application service.
- Application ports for preprocessing, transcription, cleanup, snippets,
  history, durable jobs, and events.
- Local SQLite history and durable job repository.
- Idempotent completed-job retries.
- Local daemon-thread dispatch seam.
- Environment-backed runtime settings.
- Backend-only FastAPI factory with health and job endpoints.
- Platform routing for macOS, Windows, Linux, and generic fallback adapters.
- Local dashboard, history, snippets, cleanup levels, and onboarding.

Pending before a real GCP deployment:

- PostgreSQL repository and versioned migrations.
- Server-side authentication and user ownership.
- Cloud Storage temporary audio adapter.
- Pub/Sub or Cloud Tasks dispatcher and separate worker.
- Vertex AI Speech-to-Text and Gemini adapters.
- Secret Manager integration.
- Structured logs, metrics, tracing, rate limits, retries, and cost controls.
- Container and CI/CD deployment configuration.

The authoritative backlog is [docs/user-stories.md](docs/user-stories.md).
The architecture rationale is [docs/architecture.md](docs/architecture.md).

## Codebase map

```text
voiceflow/
├── application/
│   ├── models.py          # Dictation result models and status values
│   ├── jobs.py            # Durable job model and lifecycle values
│   ├── ports.py           # Stable interfaces for replaceable adapters
│   ├── workflow.py        # Platform-neutral dictation workflow
│   ├── adapters.py        # Local adapters for core implementations
│   └── dispatch.py        # Local thread dispatch seam
├── app/
│   └── main.py            # Desktop composition root and process lifecycle
├── config/
│   ├── defaults.py        # User preference defaults
│   ├── loader.py          # TOML and vocabulary loading
│   ├── paths.py           # Repository-owned data paths
│   ├── runtime.py         # Environment-backed deployment settings
│   └── snippets.py        # Local spoken shortcut persistence and expansion
├── core/
│   ├── audio.py           # Microphone capture
│   ├── vad.py             # Silence trimming
│   ├── transcriber.py     # Parakeet and Whisper implementations
│   ├── cleaner.py         # Local LLM cleanup fallback chain
│   ├── history.py         # SQLite transcription history
│   └── jobs.py            # SQLite durable job adapter
├── platform/
│   ├── contracts.py       # Desktop capability interfaces
│   ├── factory.py         # OS detection and adapter routing
│   ├── adapters.py        # Platform service composition
│   └── backends/          # macOS, Windows, Linux, generic implementations
├── web/
│   ├── api_server.py      # Local dashboard API with desktop controls
│   ├── cloud_api.py       # Backend-only FastAPI application factory
│   └── ui/                # Dashboard and onboarding HTML/CSS/JS
└── prompts/
    └── cleanup.py         # Versioned cleanup prompt catalog
```

Supporting folders:

- `tests/` contains behavior tests at application and HTTP seams.
- `docs/` contains setup, architecture, and migration requirements.
- `packaging/` contains macOS application packaging helpers.
- `scripts/` contains cross-platform setup helpers.
- `data/` contains ignored local SQLite runtime data.

## Design rules

### Keep the desktop edge local

Microphone capture, global hotkeys, active application detection, native
permissions, system tray behavior, and text injection must remain in the
desktop agent. Do not move these into Cloud Run.

### Keep application logic portable

Application services must depend on ports, not on SQLite, Ollama, FastAPI,
Quartz, `pyautogui`, `pynput`, GCP SDKs, or filesystem paths. If behavior
varies by operating system, provider, database, or queue, introduce an adapter
at the appropriate seam.

### Prefer deep modules

Use a small interface with meaningful behavior behind it. Callers should not
need to know whether a repository is SQLite or PostgreSQL, or whether a job is
running in a local thread or a cloud worker.

### Keep cloud services stateless

In-memory state may be used for local UI convenience, but correctness must not
depend on `_state`, an in-process subscriber list, or one Python process. Job
status, history, ownership, and retry information must be durable.

### Preserve idempotency

Every dictation job needs a request ID. Retrying a completed request must return
the saved result rather than creating another history entry or injecting text
twice.

### Protect user data

Do not log raw audio, credentials, access tokens, or full sensitive transcripts.
Cloud audio should be temporary by default. Never trust a client-provided
`user_id`; derive ownership from a verified identity token.

## Local development

Use the existing virtual environment when available:

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m compileall -q voiceflow
git diff --check
```

Using uv:

```bash
uv sync
uv run --no-dev python -m voiceflow.app.main
```

The desktop launcher is:

```bash
bash VoiceFlow.command
```

The local dashboard is normally available at:

```text
http://localhost:57327
```

Do not open `voiceflow/web/ui/index.html` directly when testing API-backed
features. Use the running local server.

## Test expectations

Before committing:

1. Run the complete test suite.
2. Run Python compilation checks.
3. Run `git diff --check`.
4. Exercise the changed public seam, not private implementation details.
5. Confirm local-only behavior still works if cloud providers are unavailable.

Tests should not require:

- A microphone.
- Global keyboard permissions.
- Ollama or Docker.
- Downloaded ASR models.
- Cloud credentials.
- Network access, unless explicitly marked as an integration test.

## GCP migration sequence

Follow this order:

1. Finish ports for audio, settings, snippets, text injection, clock, and
   authentication.
2. Add repository contract tests and PostgreSQL adapters.
3. Add user ownership fields and database migrations.
4. Add Identity Platform or Firebase Authentication.
5. Add private temporary Cloud Storage audio handling.
6. Add Pub/Sub or Cloud Tasks dispatch and a Cloud Run worker.
7. Add Vertex AI Speech-to-Text and Gemini adapters.
8. Add a backend container with liveness and readiness checks.
9. Add Secret Manager, structured telemetry, rate limiting, retries, and cost
   limits.
10. Deploy to a private GCP environment and test the desktop agent end to end.
11. Validate privacy, deletion, failure recovery, and duplicate-job behavior.
12. Expose the service publicly only after the private deployment is stable.

## Commit and change policy

Use small, meaningful commits grouped by vertical capability. Good examples:

```text
refactor: extract portable dictation workflow
feat: add durable dictation job lifecycle
feat: add backend-only cloud API boundary
test: verify cloud API job contract
```

Do not push to a remote unless the user explicitly requests it. Preserve
unrelated work, do not use destructive Git commands without explicit approval,
and do not claim a cloud integration is complete until it has been exercised
against the target service.
