# VoiceFlow User Stories and Cloud Migration Requirements

## Purpose

This document records the desired user experience and the technical capabilities required to evolve VoiceFlow from a local desktop application into a modular, portable application that can run locally and later use GCP, AWS, Azure, or another cloud provider.

The first priority is system design. The code must separate product behavior from operating-system integrations, local infrastructure, and cloud infrastructure. Cloud migration should be an adapter change, not a rewrite of the dictation workflow.

This document complements:

- [Architecture](architecture.md), which describes the current implementation.
- [Setup](setup.md), which describes local installation and permissions.

## Product vision

VoiceFlow lets a user speak naturally and receive polished text in whichever application currently has focus. The user should be able to pause, ramble, correct themselves, and continue speaking without manually editing the result. VoiceFlow should work locally for privacy and reliability, while also supporting authenticated cloud processing, synchronization, and cross-device access when the user chooses it.

## Personas

### Primary user: individual writer

Someone who writes messages, documents, notes, code, emails, or prompts and wants to speak faster than they can type.

### Power user: technical user

Someone who uses technical terms, names, code symbols, application-specific language, and reusable snippets.

### Mobile and multi-device user

Someone who uses VoiceFlow on more than one computer or on a phone and expects settings, snippets, and history to remain available after signing in.

### Privacy-sensitive user

Someone who wants local-only processing, clear control over whether audio leaves the device, and explicit retention and deletion controls.

### Operator or administrator

Someone responsible for operating the cloud service, monitoring failures, controlling cost, and protecting user data.

## Priorities

| Priority | Meaning |
| --- | --- |
| P0 | Required before cloud migration work. Protects modularity, portability, and the existing local application. |
| P1 | Required for the first authenticated cloud-backed release. |
| P2 | Important product expansion after the cloud foundation is stable. |
| P3 | Optional future capability. |

# Epic 1: Modular and portable system design

This epic is the first implementation priority. It ensures that application behavior is independent of the operating system, database, model provider, queue, and cloud vendor.

## US-ARCH-001: Separate the dictation workflow from desktop startup

**Priority:** P0

As a maintainer, I want the dictation workflow to be implemented as an application service so that desktop startup code does not contain the business workflow.

### Acceptance criteria

- A `DictationWorkflow` or equivalent application service coordinates transcription, cleanup, persistence, and result creation.
- `voiceflow/app/main.py` is responsible primarily for startup, dependency wiring, and desktop lifecycle management.
- The workflow can be called from a unit test without starting a tray icon, keyboard listener, microphone, or web server.
- The workflow returns an explicit result object containing request ID, raw text, cleaned text, status, and error information.

## US-ARCH-002: Define stable ports for replaceable capabilities

**Priority:** P0

As a maintainer, I want stable interfaces for core capabilities so that local and cloud implementations can be exchanged without changing business logic.

### Required ports

- `AudioSource`
- `Transcriber`
- `TranscriptCleaner`
- `HistoryRepository`
- `SnippetRepository`
- `SettingsRepository`
- `JobRepository`
- `EventPublisher`
- `TextInjector`
- `Clock` or timestamp provider

### Acceptance criteria

- Application services depend on protocols or abstract interfaces rather than SQLite, Ollama, Vertex AI, or OS libraries directly.
- Each port has at least one local implementation.
- Cloud implementations can be added without modifying the domain rules.
- Port contracts define input, output, error behavior, and timeout expectations.

## US-ARCH-003: Keep desktop capabilities at the edge

**Priority:** P0

As a desktop user, I want microphone access, global hotkeys, active application detection, and text injection to continue working even when the processing backend changes.

### Acceptance criteria

- Microphone capture remains in the desktop agent.
- Global hotkey handling remains in the desktop agent.
- macOS, Windows, Linux, and generic behavior remains behind platform adapters.
- Cloud services never assume access to a user's microphone, keyboard, focused window, or tray.
- `voiceflow/core/` and application services do not import platform-specific libraries.

## US-ARCH-004: Support local and cloud AI providers through adapters

**Priority:** P0

As a user, I want to choose local or cloud transcription and cleanup without changing the user workflow.

### Acceptance criteria

- Local Parakeet and Whisper implementations satisfy the same `Transcriber` port.
- A future Google Speech-to-Text implementation can satisfy the same port.
- Local Docker/Ollama cleanup and future Vertex AI cleanup satisfy the same `TranscriptCleaner` port.
- Provider selection is configuration-driven.
- Provider failures return typed errors and do not crash the desktop agent.
- The system can fall back to raw transcription when cleanup is unavailable.

## US-ARCH-005: Support local and cloud data stores through repositories

**Priority:** P0

As a maintainer, I want SQLite to remain available for local mode while PostgreSQL or another cloud database can be used in hosted mode.

### Acceptance criteria

- History access goes through `HistoryRepository`.
- SQLite remains the default local implementation.
- PostgreSQL is the first planned cloud implementation because it preserves the relational model and remains portable across cloud vendors.
- Snippets and settings have repository boundaries rather than being read directly by API handlers.
- SQL queries and schema migrations are isolated from application services.

## US-ARCH-006: Make configuration environment-independent

**Priority:** P0

As an operator, I want the same application code to run locally, in a container, and in a cloud service using configuration rather than hardcoded paths or localhost URLs.

### Acceptance criteria

- Runtime configuration is loaded through one configuration object.
- Local defaults remain convenient for development.
- Cloud deployments can provide database URLs, provider names, queue names, storage buckets, and service URLs through environment variables.
- Secrets are not stored in TOML files, source code, or Git.
- Cloud secrets can be supplied through a secret manager.
- File paths are resolved through an injectable storage abstraction.

## US-ARCH-007: Make the application testable without external services

**Priority:** P0

As a maintainer, I want to test the workflow with fakes so that tests do not require a microphone, model download, Ollama, Docker, or cloud credentials.

### Acceptance criteria

- A fake transcriber, cleaner, repository, clock, and injector can be supplied to the workflow.
- Tests verify successful processing, provider failure, timeout, duplicate job, and cancellation behavior.
- Unit tests do not require network access.
- Integration tests are explicitly marked and run separately.

## US-ARCH-008: Make the API stateless

**Priority:** P0

As an operator, I want any API request to be handled by any service instance so that the backend can scale horizontally.

### Acceptance criteria

- Request and job state are stored in a durable repository.
- In-memory subscriber lists are not required for correctness.
- A client can reconnect and retrieve the current job status.
- API instances can be restarted without losing completed or pending jobs.
- Live events are treated as an optimization, not the only delivery mechanism.

## US-ARCH-009: Add an explicit job model

**Priority:** P0

As a user, I want a dictation request to have a trackable status so that a slow or interrupted transcription can recover safely.

### Suggested statuses

```text
accepted → processing → transcribed → cleaned → completed
                         └──────────────→ failed
accepted or processing ────────────────→ cancelled
```

### Acceptance criteria

- Every dictation has a unique request ID.
- Job status is persisted outside process memory.
- A job records timestamps, provider information, retry count, and failure reason.
- A retry cannot create duplicate history entries or duplicate text injection.
- The desktop agent injects text only after it receives a completed result.

## US-ARCH-010: Package the backend independently from the desktop agent

**Priority:** P0

As an operator, I want to run the API and worker as containers without installing desktop permissions or tray dependencies.

### Acceptance criteria

- Desktop and backend entry points are separate.
- The backend does not import `pynput`, `pystray`, Quartz, `pyautogui`, or microphone libraries.
- A container can start the API with a health endpoint.
- A worker can start independently from the API.
- Local development can still run the complete application with one documented command.

# Epic 2: Core dictation experience

## US-CORE-001: Speak naturally

**Priority:** P0

As a user, I want to ramble, pause, restart, or change my mind so that I can express a complete thought without manually editing every false start.

### Acceptance criteria

- The user can hold the configured hotkey, speak, and release it.
- The recording is transcribed after release.
- The cleanup stage removes configured filler words without changing the intended meaning.
- Spoken corrections such as `meet at five, actually six` produce the intended final meaning when the selected cleanup level supports it.
- Raw and cleaned text remain distinguishable in history.

## US-CORE-002: Edit after dictation completes

**Priority:** P0

As a user, I want punctuation, formatting, and filler removal applied before text is inserted into the focused application.

### Acceptance criteria

- The final text is not injected before transcription and cleanup complete.
- The user receives a visible processing state.
- If cleanup times out, the raw transcript can still be injected according to configuration.
- The UI does not claim that text is edited live while the user is speaking unless streaming transcription is implemented.

## US-CORE-003: Use VoiceFlow anywhere text can be entered

**Priority:** P0

As a user, I want the final text inserted into the currently focused text field without a plugin for each application.

### Acceptance criteria

- Text injection uses the appropriate platform adapter.
- macOS Accessibility and Input Monitoring requirements are clearly documented.
- Windows and Linux alternatives are isolated in their own adapters.
- The user receives a useful error if permissions prevent injection.

## US-CORE-004: Choose cleanup style

**Priority:** P1

As a user, I want light, medium, high, or no cleanup so that VoiceFlow matches the context of my writing.

### Acceptance criteria

- Cleanup levels have versioned prompts.
- `none` bypasses the language model.
- Light cleanup focuses on punctuation and filler removal.
- Medium cleanup allows limited restructuring.
- High cleanup produces stronger rewriting but preserves intent.
- The selected level is recorded with the history entry.

## US-CORE-005: Preserve privacy choices

**Priority:** P0

As a privacy-sensitive user, I want to know whether audio or text leaves my device.

### Acceptance criteria

- The application exposes local-only and cloud-enabled processing modes.
- The active provider is visible in settings.
- Audio retention is disabled by default.
- Cloud audio is deleted after processing unless the user explicitly enables retention.
- Data deletion removes cloud history, snippets, settings, and temporary audio according to the selected scope.

# Epic 3: Personalization and reusable text

## US-PERSONAL-001: Manage vocabulary

**Priority:** P1

As a user, I want to add names, technical terms, and organization-specific words so that transcription recognizes them more accurately.

### Acceptance criteria

- Vocabulary entries are associated with a user.
- Vocabulary can be used by local ASR and cloud ASR where supported.
- The user can add, edit, remove, import, and export entries.
- The system does not silently treat a vocabulary term as a replacement rule.

## US-PERSONAL-002: Create and use spoken snippets

**Priority:** P1

As a user, I want to speak a short trigger and insert a longer saved block of text.

### Acceptance criteria

- A snippet has a name, spoken trigger, expanded text, owner, and timestamps.
- Trigger matching is case-insensitive.
- Exact-trigger and in-sentence expansion behavior are clearly defined.
- Snippet expansion happens before final text injection.
- Duplicate triggers are handled predictably.
- Snippet text is never sent to a cloud provider unnecessarily.

## US-PERSONAL-003: Sync preferences across devices

**Priority:** P1

As a signed-in user, I want my vocabulary, snippets, cleanup preferences, and selected languages available on each authorized device.

### Acceptance criteria

- Preferences are associated with a user account.
- Local changes synchronize using a defined conflict policy.
- The user can force a refresh.
- Device-specific settings such as hotkeys and microphone selection do not overwrite incompatible device settings.
- Offline local changes are queued and synchronized when connectivity returns.

# Epic 4: Cloud processing

## US-CLOUD-001: Submit a dictation job

**Priority:** P1

As a desktop agent, I want to submit a completed recording or transcript to the cloud and receive a request ID.

### Acceptance criteria

- The API authenticates the user and device.
- The request receives a unique idempotency key.
- The API returns a request ID and accepted status quickly.
- The API does not wait indefinitely for transcription or cleanup.
- The desktop agent can continue operating while the cloud job is processing.

## US-CLOUD-002: Process jobs asynchronously

**Priority:** P1

As an operator, I want transcription and cleanup to run through durable cloud workers so that temporary failures can be retried.

### Acceptance criteria

- Jobs are placed on a durable queue such as Pub/Sub or Cloud Tasks.
- Workers acknowledge a job only after its result is persisted.
- Failed jobs have a bounded retry policy.
- Poison messages are moved to a dead-letter path.
- Duplicate delivery does not duplicate history or injection.

## US-CLOUD-003: Store temporary audio safely

**Priority:** P1

As a user, I want cloud processing to avoid retaining my microphone recordings longer than necessary.

### Acceptance criteria

- Temporary audio is stored in private object storage.
- Access uses short-lived signed URLs or service identity.
- Audio has an explicit retention deadline.
- Successful processing deletes audio when retention is disabled.
- Logs never contain raw audio or full sensitive transcripts.

## US-CLOUD-004: Return results to the desktop agent

**Priority:** P1

As a desktop user, I want the completed result returned to the device that started the dictation.

### Acceptance criteria

- The agent can poll job status after reconnecting.
- A temporary network outage does not lose a completed result.
- Results include the request ID so the agent can match them to the correct recording.
- The agent injects each successful result at most once.
- A result cannot be injected into an unintended focused application without an explicit local policy.

## US-CLOUD-005: Support multiple providers

**Priority:** P1

As an operator, I want to change transcription and cleanup providers through configuration so that the application is not locked to one vendor.

### Acceptance criteria

- Provider selection is made outside domain logic.
- GCP providers can be added without removing local providers.
- Provider timeouts and error categories are normalized.
- The system records provider and model metadata for diagnostics.
- Provider-specific credentials are stored outside source code.

# Epic 5: Accounts, security, and data ownership

## US-SEC-001: Sign in securely

**Priority:** P1

As a cloud user, I want to sign in so that my history, snippets, and preferences are private to me.

### Acceptance criteria

- The API validates an identity token on every protected request.
- Every user-owned record contains an owner ID.
- Access checks occur at the service boundary and data access boundary.
- Sign-out and token expiry are handled safely.
- Local-only mode works without requiring an account.

## US-SEC-002: Control data retention

**Priority:** P1

As a user, I want to control how long history and audio are retained.

### Acceptance criteria

- The user can delete one history entry or all history.
- The user can delete snippets and vocabulary.
- Deletion behavior is documented for primary storage, backups, caches, and temporary files.
- The service reports completion or failure of a deletion request.

## US-SEC-003: Protect sensitive data

**Priority:** P1

As an operator, I want user audio and text protected in transit and at rest.

### Acceptance criteria

- Public APIs require HTTPS.
- Databases and object storage are private.
- Secrets are stored in a managed secret store.
- Logs redact tokens, audio contents, and sensitive transcript content.
- Service accounts have least-privilege access.

# Epic 6: Reliability and operations

## US-OPS-001: Observe the system

**Priority:** P1

As an operator, I want to identify slow, failed, and expensive dictations without reading sensitive content.

### Acceptance criteria

- Requests have correlation IDs.
- Logs include request ID, user-safe status, provider, latency, and error category.
- Metrics include job count, success rate, processing latency, retry count, and provider failures.
- Alerts exist for elevated failure rate, queue backlog, and database errors.

## US-OPS-002: Deploy consistently

**Priority:** P1

As a maintainer, I want local, test, and cloud environments to use repeatable builds.

### Acceptance criteria

- Backend services have reproducible container builds.
- Dependency lock files are used in CI.
- Automated tests run before deployment.
- Database migrations are versioned and reversible where practical.
- Deployment configuration is separate from application code.

## US-OPS-003: Control cloud cost

**Priority:** P1

As an operator, I want cost controls so that a transcription service cannot grow unexpectedly.

### Acceptance criteria

- Maximum recording duration is configurable.
- Maximum request size is enforced.
- Per-user rate limits exist.
- Model and provider selection can be restricted by environment.
- Cloud Storage lifecycle rules delete temporary audio.
- Usage metrics can be attributed to a user or account.

# Epic 7: Future product capabilities

## US-FUTURE-001: Hands-free dictation

**Priority:** P2

As a user, I want to start and stop dictation without holding a key continuously.

### Acceptance criteria

- Hands-free mode has clear start, pause, resume, and cancel actions.
- The desktop agent remains responsive while the recording is active.
- Accidental activation can be cancelled without sending audio.

## US-FUTURE-002: Live transcription

**Priority:** P2

As a user, I want partial words or sentences to appear while I speak.

### Acceptance criteria

- The product clearly distinguishes partial text from final text.
- Final cleanup can revise partial output.
- Streaming does not insert duplicated text.
- The system handles network loss and reconnects.

## US-FUTURE-003: Cross-device history and snippets

**Priority:** P2

As a multi-device user, I want history, snippets, and preferences synchronized across authorized devices.

### Acceptance criteria

- Device registration and revocation are supported.
- Synchronization conflicts have a documented policy.
- A user can see which device created an entry.
- Local-only history remains available when cloud sync is disabled.

## US-FUTURE-004: Command mode

**Priority:** P3

As a power user, I want to speak an instruction that performs a safe action instead of inserting text.

### Acceptance criteria

- Command mode has a separate activation path from normal dictation.
- Commands are allowlisted and confirmed for destructive actions.
- The system does not execute arbitrary spoken shell commands.
- The user can disable command mode completely.

# Recommended implementation order

1. Extract `DictationWorkflow` from the desktop entry point.
2. Define ports for transcription, cleanup, persistence, jobs, events, and injection.
3. Add fake adapters and unit tests for the workflow.
4. Add SQLite repositories behind those ports.
5. Make the local API stateless and job-oriented.
6. Separate desktop and backend entry points.
7. Add container and health-check support for the backend.
8. Add PostgreSQL support while retaining SQLite for local mode.
9. Add cloud transcription and cleanup adapters.
10. Add Pub/Sub or Cloud Tasks workers.
11. Add authentication, ownership, retention, and observability.
12. Add synchronization, mobile clients, and other P2 capabilities.

# Definition of done for cloud readiness

The application is ready for a first cloud deployment when:

- The core workflow can run without desktop libraries.
- Local and cloud implementations satisfy the same ports.
- The API is stateless and job status is durable.
- SQLite and PostgreSQL implementations are tested against the same repository contract.
- AI providers can be changed through configuration.
- The backend runs independently in a container.
- Authentication and user ownership are enforced.
- Audio retention and deletion behavior are documented and tested.
- Retries are idempotent.
- Logs, metrics, and health checks are available.
- The local desktop experience still works in offline mode.

# Explicit non-goals

- Do not move microphone, keyboard, tray, permission, or focused-application behavior into Cloud Run.
- Do not require cloud connectivity for local-only mode.
- Do not store raw microphone audio permanently by default.
- Do not expose a public API without authentication and rate limits.
- Do not couple the domain workflow directly to GCP SDKs.
- Do not replace SQLite before repository boundaries and contract tests exist.
