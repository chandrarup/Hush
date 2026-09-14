# Hush macOS Release Credentials

The signed public Hush app needs an Apple Developer account. This is an
optional release-builder path, not an end-user setup requirement. Do not follow
this guide to test the free local Hush DMG.

## One-Time Builder Setup

1. Enrol the publishing account in the Apple Developer Program.
2. Create a **Developer ID Application** certificate for the Hush publisher
   and install it in the login Keychain on the release Mac or CI runner.
3. Confirm that macOS can see it:

   ```bash
   security find-identity -v -p codesigning
   ```

   Use the complete `Developer ID Application: ... (TEAMID)` value from this
   output as `HUSH_SIGNING_IDENTITY`.
4. Create an App Store Connect API key that is permitted to notarize software.
   Download its `.p8` key file once and store it outside this repository.
5. Store a named notary profile in the login Keychain:

   ```bash
   xcrun notarytool store-credentials "Hush Notary" \
     --key /secure/location/AuthKey_KEYID.p8 \
     --key-id KEYID \
     --issuer ISSUER_ID
   ```

   `notarytool` keeps the authentication material in the Keychain. Do not put
   API keys, passwords, issuer IDs, or certificates in Git, shell scripts, or
   release notes.

## Create A Public Release

Build the app, then run the release command with the Keychain-backed profile:

```bash
HUSH_VERSION="1.0.0" bash packaging/build_app.sh
HUSH_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAMID)" \
HUSH_NOTARY_PROFILE="Hush Notary" \
HUSH_VERSION="1.0.0" \
bash packaging/sign_and_notarize.sh dist/Hush.app
```

The script signs the embedded executable code, verifies the app, creates the
DMG, submits it to Apple, staples Apple's ticket, validates that ticket, and
runs Gatekeeper assessment. Publish only the final `dist/Hush-<version>.dmg`.

## GitHub Release Automation

The repository includes [the macOS release workflow](../.github/workflows/macos-release.yml).
It runs on a clean Apple Silicon `macos-14` GitHub-hosted runner when a tag
named `vX.Y.Z` is pushed. It builds the arm64 app, signs it, notarizes the DMG,
validates Gatekeeper, and creates the matching GitHub Release.

Create these **Actions secrets** in the repository before pushing a release
tag. Their values are supplied only to the short-lived release runner:

| Secret | Value |
| --- | --- |
| `MACOS_CERTIFICATE_BASE64` | Base64-encoded Developer ID Application `.p12` export |
| `MACOS_CERTIFICATE_PASSWORD` | Password used when exporting that `.p12` file |
| `MACOS_SIGNING_IDENTITY` | Full `Developer ID Application: Publisher (TEAMID)` identity |
| `MACOS_KEYCHAIN_PASSWORD` | A new, high-entropy password for the temporary CI keychain |
| `APPLE_NOTARY_KEY_BASE64` | Base64-encoded App Store Connect API `.p8` key |
| `APPLE_NOTARY_KEY_ID` | The API key ID |
| `APPLE_NOTARY_ISSUER_ID` | The App Store Connect issuer ID |

On macOS, create each encoded value without adding a trailing newline:

```bash
base64 -i DeveloperIDApplication.p12 | pbcopy
base64 -i AuthKey_KEYID.p8 | pbcopy
```

Paste each clipboard value into its matching GitHub Actions secret. Do not add
the certificate, `.p12`, `.p8`, passwords, or encoded values to the repository.

After the secrets are present, create and push a release tag from the reviewed
commit:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions then produces the public `Hush-1.0.0.dmg` release asset, with
the same version embedded in the app bundle. A tag push is a publication
action: use it only after the code review and release checks are complete.

## What Cannot Be Automated

Apple requires a real Developer ID identity and notarization account. The
release script deliberately stops before signing when either is missing. It
does not create an Apple account, bypass Gatekeeper, edit the TCC database, or
approve microphone, Accessibility, or Input Monitoring permission on a user's
machine.
