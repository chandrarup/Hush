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

## Design patterns

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
