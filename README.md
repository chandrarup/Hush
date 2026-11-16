# Hush

Hush turns your voice into text. Hold a hotkey, speak, and release to insert the transcript into the active text field. A desktop client records audio; the cloud service transcribes it with Whisper.

## Features

- Push-to-talk dictation with a configurable global hotkey.
- Live partial transcripts and automatic text insertion.
- Optional text cleanup, snippet expansion, and custom vocabulary.
- Browser dashboard with recording uploads, transcription history, and settings.
- macOS menu bar and notifications, with platform-specific desktop adapters.
- Private cloud storage for recordings and PostgreSQL for durable application data.
- HTTPS deployment, health checks, monitoring, alerts, and deployment rollback.

Cleanup depends on the configured provider; when unavailable, Hush returns the raw transcript.

## Install and connect

**macOS app:** download the DMG from the project's GitHub Releases, drag Hush into Applications, and open it. Allow Microphone, Input Monitoring, and Accessibility for **Hush**. See the [app installation guide](docs/MACOS_APP_RELEASE.md).

**From source:** install Python 3.10+, uv, and PortAudio, then run:

```bash
./lets-hush
# After setup:
./lets-hush --start
```

Linux users can run `bash scripts/setup_cross_platform.sh`. Follow the [source setup guide](docs/setup.md) for dependencies and operating-system permissions.

### Which URL?

- **Cloud dashboard and desktop cloud connection:** `https://hush.34.36.104.111.nip.io`
- **Local desktop dashboard:** `http://localhost:57327` (while Hush is running).
- **Older VM tunnel:** retained only in the [legacy deployment guide](docs/LEGACY_SETUP.md).

The cloud address is the configured deployment address, not a guarantee of current uptime. Replicas may be paused between demonstrations; the operator must [resume and verify the service](infra/milestone5/README.md).

Set the desktop connection in `data/config.toml`:

```toml
[cloud]
base_url = "https://hush.34.36.104.111.nip.io"
token = ""
```

### Authentication today

Cloud access currently requires a shared team token. Obtain it privately from the deployment owner; downloading Hush does not grant access. Never commit it or include it in screenshots.

For a source launch, set `HUSH_TEAM_TOKEN` in the same terminal before starting Hush. The installed app also needs the token configured for its cloud connection; a terminal environment variable does not automatically reach an app opened from Finder. The current configuration supports `cloud.token`, but this stores the token in plaintext, so use it only on a trusted demo machine.

The cloud browser dashboard accepts `https://hush.34.36.104.111.nip.io/#token=YOUR_TOKEN`. The page reads the fragment into tab-scoped session storage and removes it from the address bar. Enter this privately in your own browser; do not distribute token-bearing links. A new tab/session may require authentication again. A 401 means the token is missing or invalid; an unavailable service requires an operator readiness check.

A guided login and secure desktop credential storage are planned; the current release is a controlled team demo, not open public signup. See the [final-product completion plan](docs/FINAL_PRODUCT_PLAN.md).

## Milestone progress

These summarize repository artifacts and saved evidence, not a fresh live cloud audit.

| Milestone | Work performed and completed | Remaining |
|---|---|---|
| 1 | Project proposal, voice-to-text workflow, and architecture design. | Final product polish. |
| 2 | GCP project, budget setup, networking, VM, and initial deployment workflow. | Bring retained resources under Terraform. |
| 3 | Containerized application, versioned images, and deployment/demo documentation. | Release installation verification. |
| 4 | Private Cloud SQL, recording storage, Secret Manager, keyless runtime, and data migration. | Reconcile unmanaged dependencies. |
| 5 | GKE Autopilot, HTTPS ingress, durable-state integration, and scaling/demo evidence. | Repeat end-to-end demo validation. |
| 6 | Monitoring, alerts, Terraform for 18 resources, branch-triggered builds, health gates, and demonstrated rollback. | Full Terraform coverage, including budget, trigger, IAM, APIs, private service access, and SQL user. |

## Further instructions

- [Source installation and permissions](docs/setup.md)
- [macOS packaging and troubleshooting](docs/MACOS_APP_RELEASE.md)
- [Architecture](docs/architecture.md)
- [GKE operator guide](infra/milestone5/README.md)
- [Terraform scope and operation](infra/milestone6/terraform/README.md)
- [Existing detailed configuration, hotkeys, vocabulary, optional Gemini diagnostic, and legacy VM instructions](docs/LEGACY_SETUP.md)

Use `uv sync` and `uv run`; do not install this application with `pip install -e .`. Cloud transcription requires a running server and valid credentials.

## License

MIT.
