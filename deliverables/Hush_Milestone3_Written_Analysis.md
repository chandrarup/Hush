# Hush Milestone 3 Written Analysis

The final Hush `v1` image is **845 MB unpacked** on the local machine. A local
compressed export is **203,024,065 bytes (about 194 MiB)**; the Artifact
Registry page will provide the registry-reported compressed size after the
push. We reduced the runtime image by
using a multi-stage build and a pinned Python slim base. Compilers and Linux
headers exist only in the builder stage. The runtime stage contains the locked
production environment, Hush source, and only the operating-system libraries
needed by the server. It runs as the unprivileged `hush` user. The Whisper model
downloads into a named cache volume instead of becoming an image layer, so
rebuilding the application does not duplicate model data. The VM runs the
Hush-only Compose profile on its existing 20 GB disk. Ollama remains an optional
experiment profile; without it, Hush safely returns the raw Whisper transcript.

`.dockerignore` removes Git history, virtual environments, Python caches, tests,
coverage output, local databases, logs, and editor settings because none are
required to run the cloud service. It also removes deliverables, screenshots,
PowerPoints, PDFs, macOS packages, app assets, and Codex/Playwright scratch
folders, which keeps the build context small and prevents unrelated work from
entering the image. Most importantly, it excludes `.env` files, tokens, keys,
certificates, and secret files. The committed `.env.example` contains
placeholders only.

No secret is baked into the Hush image. Compose supplies `HUSH_TEAM_TOKEN` only
when the container starts. We verified the image configuration, full build
history, and files under `/app`; none contained the team token, `.env`, private
keys, or secret files. The local image runs as a non-root user and reports
`linux/amd64`. Artifact Registry and the VM both resolved `v1` to
`sha256:c00fb84a421cb16e36d12bfd2897df0a942e75da0b5b7f10b0d9b2b3d7038d0b`,
proving that both machines ran the same artifact. Cost controls remain active
through the $50 monthly budget with 20%,
50%, and 100% actual-spend alerts, restricted `/32` firewall rules, and stopping
the VM after the demo.
