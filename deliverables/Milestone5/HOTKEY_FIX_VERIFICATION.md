# Hotkey and activity indicator fix

Updated October 24, 2026 (America/Chicago).

The installed macOS application was older than the source checkout. Its dashboard
could receive a Recording event while its polled snapshot still said Idle. Those
two update paths could make the sidebar flicker. Modifier matching also treated
the two Control keys as interchangeable, and connection startup could finish
after the user had already released the key.

The updated client publishes the same timestamped state to the dashboard and
native indicator. A configured Left Control key matches only Left Control.
Injected events cannot start or end a recording. The client checks physical key
state before opening the microphone, after connection startup, and before
forwarding each audio block. A watchdog handles missed release events. New
recordings cannot start while the previous result is still finishing. Dashboard
updates older than the latest activity transition are ignored.

## Verification completed

- All 111 automated tests passed, including delayed startup, key release during
  microphone opening, injected events, wrong-side modifiers, audio after release,
  missed release recovery, and out-of-order dashboard updates.
- The installed application's main module matches the fixed source in both
  packaged module locations. Its code signature verifies successfully.
- The updated application reports Microphone, Input Monitoring, and Accessibility
  approved. macOS required fresh grants because the locally updated application
  had a different ad-hoc signing fingerprint.
- The initial 35-second live observation contained 225 Idle samples and no
  activity transition. Cloud history contained the same 26 retained entries.
- The full four-minute observation captured two physical-key test sessions. Each
  followed Idle → Recording → Processing → Idle. Recording lasted about 2.4 and
  2.7 seconds; the final result returned about one second after each release.
  The remaining samples were Idle, with no unexplained additional session.
- Two distinct final transcripts were saved as history entries 450 and 451,
  increasing the history count from 26 to 28. They were different phrases, not
  duplicate renderings of one entry. The user confirmed the popup appeared and
  the transcribed text was visible on the HTTPS cloud dashboard.
- The user confirmed that the final text was inserted correctly into the chosen
  text field and that no speech from before pressing or after releasing Left
  Control was included. This completes the human check of insertion and the
  recording boundary for the observed test.
- Two GKE replicas of the updated cloud release were Ready with zero restarts.

## Cloud release

- Version: `v3.0.2`.
- Cloud Build: `f4d8e137-c7fe-4ba1-ac7a-c51ead026876` (SUCCESS).
- Image digest:
  `sha256:946ba2c9d177aeade0a8980db8559692abc9a0e42ba773054eca00c83c30650d`.
- HTTPS readiness passed after the load balancer registered the new backends.
  An initial readiness request during rollout returned 503; the subsequent
  request returned 200. This is not evidence of an uninterrupted rollout.

The earlier orchestration rehearsal evidence in this folder belongs to v3.0.1.
It is historical evidence, not a new autoscaling or deletion test of v3.0.2.

## Verification scope

The observed physical-key test, popup visibility, cloud persistence, text
insertion, and exclusion of speech outside the held interval passed. Insertion
and the spoken boundary were confirmed by the user; the activity transitions and
saved entries were independently checked. Generated key events are intentionally
rejected by the fix, so automated keystrokes cannot replace the physical-key test.
These results describe the tested installed application and configuration.
