# Milestone 5 deployment evidence

These are actual October 23, 2026 UTC rehearsal outputs for release `v3.0.1`.
They support the working artifacts; the submission video must still show the
deletion/replacement live.
Console logs have normalized line endings and trailing whitespace for Git.

| Files | What they establish |
| --- | --- |
| `certificate-active.png`, `certificate-active.yaml` | Matching nip.io managed certificate is Active; PNG is the real Google Cloud console. |
| `pods-before.txt`, `deletion-command.txt`, `pod-replacement-watch.txt`, `pods-after.txt` | Actual existing pod deletion and automatic replacement. The after snapshot was collected later, so Pod ages advance. |
| `hpa-before.txt`, `hpa-watch.txt`, `hpa-returned-to-two.json` | Final-release automatic scale-up from two to four, then scale-down to two. Watch includes both final-release load rehearsals. |
| `load-job-short-demo.txt`, `short-load-four-replicas.txt`, `hpa-after-short-load.yaml`, `pods-after-short-load.txt`, `hpa-events.txt` | Final eight-second audio rehearsal: 374 successes, 82 busy responses, no transport errors or 5xx; scale-up to four healthy replicas. |
| `heavy-stress-v3.0.1/` | Separate saturation test with 48-second clips: 5 successful requests, 109 busy responses, 11 transport errors/timeouts. Preserve this limitation. |
| `pdb-eviction-test.json`, `pods-after-pdb-test.txt` | First eviction admitted; immediate second eviction rejected by PDB; replacement subsequently became Ready. |
| `release-image.txt` | Actual Deployment and running containers use the recorded release digest. |
| `public-end-to-end.txt`, `public-after-heavy-stress.txt` | Trusted HTTPS, authenticated WAV upload, native WSS, persisted history, unauthorized history rejection and HTTP 301. |
| `pause-resume.txt`, `public-after-resume.txt` | Verified zero-Pod standby followed by two healthy replicas, active HPA, public HTTPS upload/WSS/history and HTTP redirect. |
| `final-standby.txt`, `final-standby-status.txt` | Final intentionally paused application state and stopped old VM, collected after the lifecycle checks. |
| `public-health-monitor.jsonl` | 842 HTTP 200 responses and 3 transport errors, no HTTP 5xx; bounded diagnostic sample, not an uptime guarantee. |
| `local-tests.txt` | 101 tests passed; includes probe fault and overload behavior. |

`rehearsal-v3.0.0/` is a local historical archive and is excluded from the intended
Milestone 5 commit. It must not be used as evidence for the final deployed image.
Only the names and public identifiers of managed resources are included; private
team tokens and database credentials are never printed by the verification tools.

The required Codex Security source review completed and sealed scan
`83eb97ff-0713-407d-bf33-aaa9d7546d34` with no reportable findings. It reviewed
31 changed files in an isolated copy plus supplemental publication documents.
It does not replace the live cloud checks recorded here.
