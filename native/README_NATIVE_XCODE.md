# VoiceFlow Native (Xcode)

This directory contains the native macOS rewrite scaffold for VoiceFlow.

## Goals implemented in this scaffold
- Native macOS app target generated via XcodeGen (`project.yml`)
- Menu bar-first app (`LSUIElement`)
- Native settings storage (`Application Support/VoiceFlow/config.json`)
- Native history storage (`Application Support/VoiceFlow/history.db`)
- One-time importer from legacy `~/.voiceflow/config.toml` and `~/.voiceflow/history.db`
- Native permissions deep-links (Microphone, Accessibility, Input Monitoring)
- CI workflow to build app and package DMG on macOS runners

## Generate project in Xcode

```bash
brew install xcodegen
cd /home/runner/work/Hush/Hush
xcodegen generate --spec /home/runner/work/Hush/Hush/native/VoiceFlowNative/project.yml
open /home/runner/work/Hush/Hush/native/VoiceFlowNative/VoiceFlowNative.xcodeproj
```

## Build locally

```bash
xcodebuild \
  -project /home/runner/work/Hush/Hush/native/VoiceFlowNative/VoiceFlowNative.xcodeproj \
  -scheme VoiceFlowNative \
  -configuration Release \
  -destination 'platform=macOS' \
  -derivedDataPath /tmp/VoiceFlowBuild \
  build
```

## Create DMG locally

```bash
/home/runner/work/Hush/Hush/native/VoiceFlowNative/scripts/create_dmg.sh \
  /tmp/VoiceFlowBuild/Build/Products/Release/VoiceFlow.app \
  /tmp/VoiceFlow.dmg
```

## Current status
- App shell and migration plumbing are implemented.
- Audio capture, VAD, ASR, and LLM cleanup pipeline are scaffolded and intentionally marked TODO in `NativeTranscriptionPipeline`.
