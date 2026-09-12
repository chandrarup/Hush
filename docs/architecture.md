# VoiceFlow Architecture

VoiceFlow keeps application behavior independent of the operating system. The
runtime routing module `voiceflow.platform.factory` is the only module that
uses host-OS detection to select one concrete platform bundle at startup.

```text
voiceflow.app.main
        |
        v
PlatformServices  <-- stable capability contracts
        |
        +--> macOS bundle    --> Quartz / osascript / System Settings
        +--> Linux bundle    --> xdotool / notify-send / desktop fallback
        +--> Windows bundle  --> clipboard / pyautogui / Windows Settings
        +--> Generic bundle  --> portable clipboard and console fallbacks
```

## Module responsibilities

- `voiceflow/core/` contains recording, VAD, transcription, cleanup, and
  history logic. It must not import platform backends.
- `voiceflow/config/snippets.py` owns the small, deep interface for loading,
  saving, and expanding spoken shortcuts. The application calls it once at the
  final pipeline seam, immediately before text injection.
- `voiceflow/app/` coordinates the workflow through `PlatformServices`; it
  does not contain OS-specific branches.
- `voiceflow/platform/contracts.py` is the seam: it defines the small
  interfaces used by the application.
- `voiceflow/platform/factory.py` owns host detection and backend selection.
- `voiceflow/platform/adapters.py` composes each platform bundle.
- `voiceflow/platform/backends/<platform>/` contains concrete adapters grouped
  by capability: text injection, notifications, context, and permissions.
- `voiceflow/platform/backends/common/` contains implementations reusable by
  more than one platform, such as the tray and clipboard helpers.
- `voiceflow/application/` owns the platform-neutral dictation workflow,
  durable job model, and ports that local and hosted adapters must satisfy.
- `voiceflow/core/jobs.py` is the local SQLite job adapter. A hosted
  PostgreSQL or cloud-job adapter can replace it without changing the workflow.
- `voiceflow/application/dispatch.py` is the execution seam. Local mode uses a
  daemon thread dispatcher; a hosted adapter can publish the same work to a
  durable queue.

## Application dependency management

VoiceFlow is distributed and operated as a desktop application, not as a
library or SDK. `pyproject.toml` is therefore an application manifest rather
than a package-publishing configuration, and `tool.uv.package = false` prevents
uv from installing the repository itself as a Python package.

- Runtime dependencies live in the main project dependency list.
- Parakeet dependencies are an optional `parakeet` extra for Apple Silicon or
  users who explicitly want that ASR engine.
- Test-only dependencies are in the `dev` dependency group.
- py2app packaging dependencies are in the `build` dependency group.
- `uv.lock` is committed so setup and CI resolve the same versions.

Use `uv sync` to create or update `.venv` and `uv run` to execute application,
diagnostic, and test commands. The installers and documentation intentionally
do not maintain a second `requirements.txt` or invoke pip directly.

## Application data paths

`voiceflow.config.paths` centralizes paths owned by the application. User
preferences remain in `~/.voiceflow`, while transcription history is stored at
`data/history.db` relative to the repository root. The history module consumes
that shared path instead of depending on the current working directory or
embedding an absolute home-directory path.

Spoken snippets are user preferences stored at `~/.voiceflow/snippets.toml`.
The dashboard writes them through the local API. The pipeline reloads them for
each recording, so a new shortcut works without restarting VoiceFlow.

## Dictation sequence

The application keeps the user experience small and predictable:

1. The global hotkey starts a platform-neutral recorder.
2. Voice Activity Detection trims leading and trailing silence.
3. The selected ASR adapter transcribes the complete recording.
4. The cleanup module removes filler, resolves spoken self-corrections, and
   applies punctuation according to the selected style.
5. The snippet module expands an exact spoken shortcut.
6. The platform text adapter injects the final text into the focused field.

The current implementation edits after the hotkey is released. It does not
stream partial text into the target field while the microphone is still open.

## Job lifecycle

Every workflow execution can have a durable request ID and status:

```text
accepted -> processing -> completed
                     \-> discarded
                     \-> failed
```

The local implementation stores job status in SQLite. A cloud deployment can
use the same application port with a PostgreSQL repository and a Pub/Sub or
Cloud Tasks worker. The API exposes `POST /jobs` and `GET /jobs/{request_id}`
so clients can reconnect and retrieve a result after a process or network
restart.

## Deployment configuration

Deployment settings are separate from user preferences. `RuntimeSettings`
reads environment variables such as `VOICEFLOW_DATABASE_URL`,
`VOICEFLOW_TRANSCRIPTION_PROVIDER`, `VOICEFLOW_CLEANUP_PROVIDER`, and
`VOICEFLOW_QUEUE_BACKEND`. Local defaults remain unchanged; hosted values can
be supplied by a container platform and secrets manager.

## Design patterns

### Strategy

### Strategy

Text injection and notifications are strategies. Each platform chooses an
ordered list of methods appropriate to its capabilities and falls back when a
dependency or permission is unavailable.

### Factory and registry

`factory.py` maps `platform.system()` names to bundle constructors. Adding a new
operating system changes this registry and adds a backend package; application
orchestration does not change.

### Adapter

Each concrete backend adapts native facilities such as Quartz, `xdotool`, or
Windows settings into the same `PlatformServices` contract.

### Dependency inversion

The application depends on protocols, not subprocesses, GUI libraries, or
native APIs. This keeps tests fast and makes platform behavior replaceable.

## Adding another operating system

1. Add `voiceflow/platform/backends/<platform>/`.
2. Implement the four capability adapters: text injection, notifications,
   context, and permissions.
3. Compose them into a `PlatformServices` subclass in `adapters.py`.
4. Register the host name in `factory.py`.
5. Add a routing test to `tests/test_smoke.py`.

Do not add `sys.platform` checks to `core/` or `app/`. If behavior varies by
host, add it behind a platform capability interface instead.

## Naming conventions

- Python modules and functions use `snake_case`.
- Classes use `PascalCase` and describe the capability plus role, such as
  `MacOSTextInjector` or `WindowsPermissions`.
- Platform names use the canonical spelling: `macos`, `linux`, `windows`, and
  `generic` for backend folders.
- Diagnostic modules use descriptive names ending in `_diagnostic.py`.
