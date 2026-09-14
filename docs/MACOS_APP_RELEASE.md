# Hush macOS App Release

This document is for release builders. End users install the resulting
`Hush.app`; they do not create a Python virtual environment or run `uv`.

## Release Architecture

`py2app` packages the current Python application, its Python interpreter, and
its required dependencies as `Hush.app`. The first distributable build uses
the faster-whisper engine; the optional Parakeet/Torch stack remains available
to source developers but is not bundled into this initial app release. The
local FastAPI dashboard remains a local UI at `http://127.0.0.1`; it is
launched by Hush and is not a hosted web service.

When frozen as a macOS app, Hush stores configuration, history, and downloaded
models in:

```text
~/Library/Application Support/Hush/
```

Nothing downloaded after installation is written into the signed app bundle.

## Build Prerequisites

- macOS on the architecture being released.
- Python and `uv` for the release builder only.
- An Apple Developer Developer ID Application certificate for public releases.
- Apple notarization credentials for public releases.

The first build can be unsigned for free local packaging checks. A signed and
notarized build is the public-release path; see
[macOS release credentials](MACOS_RELEASE_CREDENTIALS.md).

## Supported Architecture

The current GitHub release workflow builds an **Apple Silicon (arm64)** app on
the `macos-14` runner. It is not an Intel Mac release. Build and validate a
separate x86_64 artifact before advertising Intel support; do not label this
first artifact as universal.

## Build The App

From the repository root, run:

```bash
HUSH_VERSION="1.0.0" bash packaging/build_app.sh
```

The build command deliberately invokes `setup_app.py` from `packaging/` after
syncing the locked environment. This keeps py2app's legacy build metadata
separate from the application's modern `pyproject.toml` runtime dependencies.

The expected output is `dist/Hush.app`. Before signing, verify that its UI
files are present under `Hush.app/Contents/Resources/ui` and that opening the
application does not depend on a project `.venv`.

## Sign And Notarize

Follow [macOS release credentials](MACOS_RELEASE_CREDENTIALS.md) once on the
release Mac or CI runner. Then use `packaging/sign_and_notarize.sh`; it signs
the app with Hardened Runtime, verifies the nested code, creates the DMG,
notarizes it, staples Apple's ticket, and runs Gatekeeper assessment.

Keep signing and notarization secrets in the Keychain or CI secret store,
never in this repository or a release script.

## End-User Installation

1. Download `Hush-<version>.dmg` from the GitHub Release.
2. Open the DMG and drag **Hush** to **Applications**.
3. Eject the DMG, then open **Hush** from Applications.
4. Select **Allow** when Hush requests microphone access.
5. Select **Enable** for typing. In the macOS alert, choose **Open System
   Settings** and turn on **Hush** under Accessibility.
6. Return to the existing browser setup page. It refreshes and enables
   **Continue** when both permissions are available. If macOS asks to quit and
   reopen Hush, leave that page open; it reconnects when Hush starts again.
7. Wait for the initial speech-model download, then run the dictation test.

Input Monitoring is not a required setup step for the free Hush build. macOS
does not reliably list an unsigned app in that pane, and Accessibility covers
Hush's event-listening and text-insertion path. If the hotkey works after
Accessibility is enabled, setup is complete. Do not use the `+` button to add
Terminal, Python, a virtual environment, or a Python framework path.

## Required Clean-Mac Checks

- No Homebrew, Python, or developer tools are installed.
- Hush launches directly from Applications after the DMG is ejected.
- The microphone dialog identifies Hush.
- Accessibility identifies Hush and the setup page refreshes after it is enabled.
- Input Monitoring is not required to complete setup or to use the hotkey.
- A denied permission produces a recovery state, never a false success.
- Hold-to-talk, recording, transcription, and text insertion work in TextEdit.
- Updating Hush preserves the same bundle identifier and signing identity.
