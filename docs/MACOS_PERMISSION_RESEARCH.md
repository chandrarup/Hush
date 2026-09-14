# Hush macOS Permission Research

## Findings

Hush can eliminate the normal need to find a Python executable and paste a
machine-specific path into System Settings. The recommended distribution is a
real **Hush.app**, with an onboarding screen that requests permissions for that
app. Signing and notarization are required for a public signed release, but are
not required for the free local-install flow. Packaging alone does not approve
permissions.

The achievable experience for automatic dictation into other applications is:
open Hush, approve microphone access, open the macOS Accessibility pane from
the native alert, and enable Hush. Apple's current consumer instructions
explicitly require the Accessibility switch in System Settings. A microphone
style Allow/Don't Allow dialog for every capability is therefore not a
supported product promise.[^1]

There is a useful correction to the existing setup guidance. In a May 2026
answer, Apple Developer Technical Support explains that Accessibility grants
both event posting and listening; Input Monitoring grants listening alone.
For Hush's event-tap design, the normal setup flow is **microphone plus
Accessibility**, without requiring a separate Input Monitoring grant. The free
build has been tested with a working global hotkey after Accessibility was
enabled even though Hush was absent from Input Monitoring. The onboarding must
not claim that an unsigned Hush build will appear there.[^2]

A second design can remove keyboard monitoring independently: use registered
global shortcuts. A third, reduced-feature design can avoid Accessibility too:
record inside Hush and let the person paste the transcript manually.

## Present Setup And Paths

The current `./lets-hush` flow remains a source-based Python installation.
It installs software and prints instructions. It does not install a stable
Hush app identity or automatically grant privacy permissions.

The permission path is **not the same on every machine**. Python installation
method, Homebrew prefix, Python version, environment location, and launch
application can all differ. For the present installation, run:

```bash
./lets-hush --permissions
```

That command resolves the local environment and prints a selectable
`Python.app` folder when one exists. On the inspected machine it resolves to:

```text
/opt/homebrew/Cellar/python@3.12/3.12.13_2/Frameworks/Python.framework/Versions/3.12/Resources/Python.app
```

That is a diagnostic result for this machine, not a path to distribute to other
users. Terminal is the initial entry for Terminal-based launches; Python.app
is a troubleshooting fallback. Already-approved entries do not need to be
added repeatedly.

For the proposed consumer app, choose the installation location:

```text
/Applications/Hush.app
```

Then the object users recognize is **Hush**, not a Python version. A per-user
installation under `~/Applications` is another possible location. The
application should discover its own bundle URL to reveal it in Finder if
manual selection becomes necessary.

An installation folder is not itself a permission. Bundle identity,
signing, and the process making the protected call must be correct. Apple's
guidance recommends packaging interpreted code as a standalone program and
using a native executable as the app's main executable; script-based bundle
entry points can cause permission attribution problems.[^3]

## Permission Behavior

| Capability | Current Hush mechanism | Recommended request/check | Expected user action |
| --- | --- | --- | --- |
| Microphone recording | sounddevice/PortAudio | AVFoundation authorization status and request for audio | Native approval dialog on the initial request; Settings recovery after denial |
| Type into another app | Quartz keyboard-event posting | Accessibility trust check and native prompt | Open System Settings and enable Hush |
| Control-only global hotkey | pynput event tap | Test event listening after Accessibility approval | No separate Input Monitoring step if the packaged event path is already authorized |
| Optional listening without Accessibility | Listen-only event tap | CoreGraphics preflight/request APIs | OS-managed Input Monitoring permission flow; retain a Settings fallback |
| Registered global shortcut | Proposed shortcut library | Register the selected shortcut | No keyboard-monitoring permission dialog from that library |
| Manual transcript copy | Proposed in-app record/copy workflow | Microphone only, with user-initiated clipboard write | User presses Command+V in the destination |

The microphone status must come from the authorization API, not the presence
of an audio device. `AVCaptureDevice.authorizationStatus(for: .audio)`
distinguishes not determined, authorized, denied, and restricted.
`requestAccess(for: .audio)` initiates an asynchronous request.
`NSMicrophoneUsageDescription` supplies the explanation. A saved denial
requires a Settings recovery path rather than an endless series of new
requests.[^4]

For Accessibility, use
`AXIsProcessTrustedWithOptions` and
`kAXTrustedCheckOptionPrompt` when the person chooses to enable typing.
The prompt is asynchronous; a false return does not mean the person has
finished responding. Recheck when Hush regains focus.[^5]

Do not equate Input Monitoring and Accessibility status. The latter can make
event listening work even when there is no separate listening-only approval.
The practical readiness condition should reflect the selected features and
whether their operations work, not require every privacy category to be on.

For a mode that really needs independent listening permission,
`CGPreflightListenEventAccess` and `CGRequestListenEventAccess` are the
relevant CoreGraphics APIs. Apple DTS also points to
`IOHIDRequestAccess` for registering an input-monitoring request. These
are supported request mechanisms, not ways to silently authorize an app.[^6]

Exact prompt wording, list insertion, and restart behavior must be checked
on the supported macOS releases. Avoid promising that every permission
always appears in an identical popup.

## Repository Findings

The following are observations of the current checkout, rather than claims
that the proposed app has already been built.

| File/location | Observation | Consequence |
| --- | --- | --- |
| `lets-hush`, `VoiceFlow.command` | Launch a virtual-environment Python process | The improved command still inherits the source-install identity problem |
| `voiceflow/diagnostics/permission_diagnostic.py` | Resolves Python.app dynamically | Appropriate fallback for developers; not the desired consumer onboarding |
| `voiceflow/platform/backends/common/permissions.py` | Microphone check enumerates input devices | Device availability is presented as permission status |
| `voiceflow/platform/backends/common/permissions.py` | Starts a listener and reads `IS_TRUSTED`; errors can return true | A best-effort diagnostic is treated as authorization |
| `voiceflow/platform/backends/macos/text_injection.py` | Uses `ApplicationServices.AXIsProcessTrusted` and fails closed on errors | Prevents an unavailable trust API from being reported as granted |
| `voiceflow/web/api_server.py` | Permission action opens Settings | It does not implement a native request/state flow |
| `packaging/setup_app.py` | Existing py2app identity is VoiceFlow / `com.voiceflow.app` | A packaging starting point exists, but Hush branding and identity need a deliberate release decision |
| `packaging/setup_app.py` | Apple Events usage text describes Accessibility | Automation and Accessibility are distinct permissions |
| `packaging/build_dmg.sh` | Packages a source folder and install script | A DMG currently does not mean a self-contained app |

Read-only checks in the installed environment established that:

- Quartz exposes the CoreGraphics listen/post preflight and request functions.
- Quartz does **not** expose the tested Accessibility trust symbols.
- ApplicationServices exposes `AXIsProcessTrusted`,
  `AXIsProcessTrustedWithOptions`, and `kAXTrustedCheckOptionPrompt`.
- The AVFoundation Python bridge is not installed.

Therefore, a Python implementation should import the Accessibility functions
from ApplicationServices and add the AVFoundation bridge if it uses that API.
Unknown status should remain unknown and produce a useful diagnostic.

The installed pynput implementation sets `IS_TRUSTED` from an Accessibility
check, then independently attempts to create an event tap. The upstream
v1.8.2 source confirms this behavior. That explains why an
`IS_TRUSTED=False` message is not a definitive Input Monitoring result and
can coexist with observed key events.[^7]

The Apple Events description should be corrected if the AppleScript fallback
is retained: it explains permission to send Apple events to another app, not
a grant to post arbitrary keyboard events. Using that fallback can introduce
an additional Automation consent flow.[^8]

## Recommended Implementation

### First: Keep Python, Fix Identity And Requests

The least disruptive approach is to keep the current recognition and cleanup
pipeline and produce a self-contained Mac application. The existing py2app
configuration is the natural first packaging experiment.

Use a deployable build, not py2app alias mode. Alias builds refer back to the
development machine's files and are explicitly not portable. A normal py2app
deployment build assembles a self-contained application.[^9]

The proposed release requirements are:

1. Use one chosen Hush display name and a stable bundle identifier.
2. Embed the interpreter and required libraries; avoid depending on a user's
   Homebrew Python installation at runtime.
3. Verify the main executable is native and the protected operations are
   attributed to Hush.
4. Request microphone access with a clear purpose string.
5. Request Accessibility when enabling automatic insertion.
6. Keep Input Monitoring out of the normal onboarding sequence if event
   listening works after Accessibility approval.
7. Preserve a clear recovery action that opens Settings or reveals Hush.app.
8. Offer a test sentence and require successful recording and insertion before
   declaring setup complete.

Move permission onboarding before expensive model loading and before starting
global keyboard listeners. The user should not wait through a model download
just to learn that recording cannot begin.

Package all the lazy imports, model-support libraries, UI assets, and dynamic
audio libraries that the app actually needs. Keep downloaded model data outside
the signed application bundle. Measure the finished package rather than
treating the existing size estimate in `setup_app.py` as a verified build size.

For public distribution, sign the distributed executables with Developer ID,
enable the appropriate Hardened Runtime settings, notarize the artifact, and
staple its ticket. Notarization is Apple's distribution verification process;
it does not replace privacy consent.[^10]

A hardened app that records audio needs the actual audio-input entitlement
`com.apple.security.device.audio-input`. It does not authorize keyboard
monitoring. Do not introduce invented entitlement names to solve TCC
problems.[^11]

Test the specific packaged PyTorch/PortAudio runtime before choosing additional
entitlements. Do not turn off runtime protections wholesale as a packaging
default.

PyInstaller is an alternative if py2app cannot reliably collect this dependency
graph. Its documentation covers signing identities, entitlements, architectures,
and the different process models of one-directory versus one-file apps.
A one-directory app is a reasonable first experiment for simpler process
attribution and debugging; that is an engineering recommendation, not a
guarantee about TCC behavior.[^12]

### Second: Consider A Native Front End

A Swift/AppKit front end can own onboarding, microphone capture, keyboard
shortcuts, and final text insertion. Python can remain a worker that receives
audio and returns text. This gives the native application a clear responsibility
for every permission-sensitive operation.

That design is preferable to a shell script disguised as an app which launches
an unrelated Python installation. It is also more work than packaging the
current pipeline. Begin with it only if the packaging experiment reveals
persistent identity problems, or if a native onboarding experience is a
product priority.

If keeping the Python worker, define explicit start/stop recording and
transcription messages. Do not have both the native app and Python independently
listen for the hotkey or request the same microphone.

### Third: Reduce Keyboard Monitoring

The maintained KeyboardShortcuts Swift package documents global shortcuts
without permission dialogs and exposes key-down and key-up callbacks. It also
provides a shortcut recorder and conflict warnings. This is a concrete option
for a native front end.[^13]

The UX would change from a bare Control key to a selected combination, such
as a Command+Shift+letter shortcut that passes conflict validation. Do not
silently replace an existing user shortcut.

Modifier-only hotkeys, including the present Control behavior, need separate
treatment. Registered shortcuts are not a drop-in replacement for arbitrary
modifier monitoring. Test release ordering, autorepeat, sleep/wake, menu-bar
focus, and shortcut conflicts before claiming hold-to-talk reliability.

This redesign independently avoids global key-stream monitoring, but it
does not remove Accessibility for automatic insertion into other apps.
Since Accessibility may already cover the current event tap, a shortcut
redesign is optional for the first simplified release.

## Proposed First-Run Experience

This is the recommended product flow, not behavior implemented by the current
setup command.

1. Download the Hush application and move it to Applications.
2. Open Hush from Finder or Launchpad.
3. See the greeting **Let's Hush.**
4. Choose **Enable Microphone** and respond to the native macOS dialog.
5. Choose **Enable Typing**; use the native alert to open Accessibility.
6. Enable **Hush** in the list and return to the app.
7. Hush rechecks authorization and verifies its keyboard listener.
8. Prepare the speech model, then dictate a test sentence into TextEdit.

No Python path should be part of the normal flow. If the app does not appear
in the relevant settings list, show **Reveal Hush in Finder** with a short
instruction to select that app. Preserve this fallback until clean-system tests
show how reliable list registration is on every supported release.

An existing user who denies a permission should see a specific recovery action,
not a generic failure, repeated prompt loop, or a green completed state.

## A True Popup-Only Option

A reduced-permission mode can meet the popup-only objective more closely:
record through a button inside Hush, show the resulting transcript, and offer
**Copy**. The person returns to the target app and presses Command+V.

This mode does not need to synthesize keystrokes or monitor global keys.
Its relevant initial privacy request is microphone access. A registered global
shortcut could later trigger recording without the broader keyboard listener.

This is a product tradeoff: it preserves local speech recognition but gives up
automatic insertion. Programmatically pressing Command+V after copying would
reintroduce the event-posting permission requirement.[^14]

For full automatic dictation, the supported goal is therefore **no path hunting
and a short, guided Settings step**, rather than a promise of only Allow/Don't
Allow dialogs.

## Unsupported Shortcuts And Managed Macs

Changing file permissions, using an administrator shell, adding a usage string,
or signing a binary does not constitute the person's privacy approval.
`tccutil` is a reset tool for testing, not a public grant API.
Do not distribute a setup flow based on editing the TCC database or clicking
its consent controls on the user's behalf.[^15]

Organizational device management is a separate deployment model, not a
consumer-install shortcut. Apple's WWDC26 deployment documentation describes
a consolidated consent prompt with managed defaults on supervised macOS 27
devices. The page explicitly labels these features prerelease.
It also describes changes to management of Accessibility permissions.
Those mechanisms require the appropriate managed environment and should not
be presented as something a GitHub installer can enable on ordinary Macs.[^16]

## Verification And Release Criteria

Research and read-only API checks establish the implementation direction.
They do not establish that a Hush.app build has passed first-launch privacy
tests. In particular, a new Python virtual environment on an already-used Mac
does not create a fresh macOS permission database.

Use a separate Mac or a VM with a clean snapshot. Apple's developer support
specifically recommends fresh-system tests because cached privacy state can
mislead development testing.[^17]

| Scenario | Required evidence |
| --- | --- |
| Fresh Mac, no developer tools or Homebrew | Hush launches from its bundle without a Python-path instruction |
| First microphone request | Dialog identifies Hush and recording works after approval |
| Microphone denied | App shows denied/recovery state and does not report a successful recording |
| First Accessibility request | Native alert, identifiable Hush entry, successful recheck after enabling |
| Accessibility granted; Input Monitoring not separately granted | Control hotkey press/release and insertion work, or failure is explicitly documented |
| Accessibility denied | No false success; copy-only mode remains usable if offered |
| Signed app upgrade | Prior consent remains usable or a clear reauthorization flow is shown |
| Relaunch, sleep/wake, logout/login | Listener and recording recover without stuck recording |
| Different supported macOS releases | Exact dialogs and any restart requirement are recorded |
| Apple Silicon and any promised Intel build | Dependencies, audio, recognition, and packaging tested separately |
| Settings entry missing | User can reveal/select Hush.app without finding Python |
| AppleScript fallback | Additional Automation prompts are understood or the fallback is removed |

The next concrete development milestone should be a signed app prototype with
correct permission checks, native requests, and a recorded clean-Mac result.
After that evidence, simplify the main setup guide to the validated two-permission
flow and retain source-install instructions in its developer section.

## Sources

All web sources were consulted on September 11, 2026. Apple forum answers below
are attributed to Apple Developer Technical Support; statements by the original
question authors are not treated as platform guarantees. Local observations
refer to the current Hush checkout and its installed Python environment.

[^1]: Apple Support. [Allow accessibility apps to access your Mac](https://support.apple.com/en-lamr/guide/mac-help/mh43185/mac). Current Mac User Guide; no publication date shown. Documents the alert and explicit System Settings approval.

[^2]: Kevin Elliott, Apple Developer Technical Support. [How to make app appear in Input Monitoring permissions list](https://developer.apple.com/forums/thread/828052?page=1). May 2026. Explains Accessibility's event-posting/listening relationship and request mechanisms.

[^3]: Quinn, Apple Developer Technical Support. [On File System Permissions](https://developer.apple.com/forums/thread/678819). First published April 2021; visible revision November 4, 2025. Sections on responsible code, scripting, native main executables, and signing identity.

[^4]: Apple Developer Documentation. [AVCaptureDevice requestAccess(for:completionHandler:)](https://developer.apple.com/documentation/avfoundation/avcapturedevice/requestaccess%28for%3Acompletionhandler%3A%29?changes=_8) and [authorizationStatus(for:)](https://developer.apple.com/documentation/AVFoundation/AVCaptureDevice/authorizationStatus%28for%3A%29). Undated living API references.

[^5]: Apple Developer Documentation. [AXIsProcessTrustedWithOptions](https://developer.apple.com/documentation/applicationservices/1459186-axisprocesstrustedwithoptions?changes=__9&language=objc). Undated API reference. Describes the prompt option and asynchronous behavior.

[^6]: Apple Developer Documentation. [CGRequestListenEventAccess](https://developer.apple.com/documentation/CoreGraphics/CGRequestListenEventAccess%28%29). Undated API reference. See also the Apple DTS answer in source 2 for IOHIDRequestAccess.

[^7]: Moses Palmer and pynput contributors. [Darwin listener implementation, v1.8.2](https://raw.githubusercontent.com/moses-palmer/pynput/v1.8.2/lib/pynput/_util/darwin.py). Versioned project source; ListenerMixin trust check and event-tap creation.

[^8]: Apple Developer Documentation. [NSAppleEventsUsageDescription](https://developer.apple.com/documentation/bundleresources/information-property-list/nsappleeventsusagedescription). Undated API reference. Defines the purpose string for Apple events.

[^9]: py2app maintainers. [Tutorial](https://py2app.readthedocs.io/en/latest/tutorial.html). Documentation version 0.28.10 displayed. Distinguishes alias development builds from self-contained deployment builds.

[^10]: Apple Developer Documentation. [Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution?changes=_9). Undated living documentation. Covers Developer ID, Hardened Runtime, signatures, notarization, and tickets.

[^11]: Apple Developer Documentation. [Audio Input Entitlement](https://developer.apple.com/documentation/BundleResources/Entitlements/com.apple.security.device.audio-input). Undated API reference.

[^12]: PyInstaller maintainers. [Notes about specific features](https://pyinstaller.org/en/stable/feature-notes.html). Documentation version 6.22.2 displayed. macOS architecture, code-signing, and process-model sections.

[^13]: Sindre Sorhus and contributors. [KeyboardShortcuts](https://github.com/sindresorhus/KeyboardShortcuts). Living project documentation, version 3.0.1 displayed. Global shortcuts, key-down/up support, permission FAQ, and modifier-key limitations.

[^14]: Apple. [Advances in macOS Security, WWDC19 session 701](https://developer.apple.com/videos/play/wwdc2019/701/). June 2019. Transcript discussion of synthetic input events, Accessibility, and Automation; used with current support guidance.

[^15]: Apple Developer Documentation. [Resetting access to protected resources in macOS](https://developer.apple.com/documentation/xcode/resetting-access-to-protected-resources-in-macos?changes=_8%2C_8). Undated living documentation. Defines tccutil reset workflows.

[^16]: Apple Platform Deployment. [WWDC26 app management updates](https://support.apple.com/en-au/guide/deployment/depd567c9ffa/web). 2026; explicitly marked prerelease. Supervised-device privacy consent and Accessibility management updates.

[^17]: Quinn, Apple Developer Technical Support. [Why does NSEvent.addGlobalMonitorForEventsMatchingMask...](https://developer.apple.com/forums/thread/811443). Living forum thread. Recommends fresh-system privacy tests and describes supported input-monitoring APIs.
