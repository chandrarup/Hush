# Hush Milestone 5: deployment and demo package

Updated October 25, 2026. Start with [the current demo run sheet](DEMO_RUN_SHEET.md)
for the exact tabs, files, commands, and 9:45 sequence. Six submission artifacts,
including the two-slide PowerPoint and half-page PDF, have been created in the
sibling `Milestone 5` folder. The current application release is v3.0.2. The
video still needs recording, and its fresh pod captures must be copied back into
the final package. Follow [the four-proof recording checklist](SUBMISSION_CHECKLIST.md)
before submitting; a static package alone does not complete the milestone.

Read [the deployment report](LIVE_DEPLOYMENT.md) for historical v3.0.1 rehearsal
results and [the hotkey verification](HOTKEY_FIX_VERIFICATION.md) for the later
fix. Compute was paused after testing; resume and verify before a demo.

Resume and pause in **Mac Terminal**, outside the timed video. Run the live
demo commands in **Cloud Shell in Chrome**, with no Git clone. Use
[the exact command sheet](DEMO_TERMINAL_COMMANDS.md), or
[its Chrome page](http://127.0.0.1:57330/commands.html), for numbered copyable
blocks and automatic pod selection. All other presentation content is displayed
in Chrome: [slides](http://127.0.0.1:57330/slides.html),
[analysis](http://127.0.0.1:57330/analysis.html), and
[artifacts](http://127.0.0.1:57330/artifacts.html).

## Decisions already made

- Use GKE so the pod deletion, HPA, and PodDisruptionBudget requirements can be
  demonstrated directly.
- Use a free hostname. Do not buy a domain or create a paid Cloud DNS zone.
- Target $100 total for the 45-day demo period, with $150 as the proposed
  contingency ceiling, including existing managed services. The user permits
  compute to be stopped between demonstrations; continuous application uptime
  is no longer required.
- Keep the cluster configuration, hostname/certificate and managed data, but
  pause application replicas between rehearsals/demos. Restore two healthy
  replicas and autoscaling before each demo or agreed grading window.
- Use three presenters: Presenter 1 covers both slides, Presenter 3 handles the
  complete live demo, and Presenter 2 explains the written analysis and closes.
  Speaking order is 1 → 3 → 2; names remain open. Read
  [the three-presenter notes](THREE_PRESENTER_NOTES.md) for exact handoffs.
- Retain the earlier milestones' detailed show/run/say/expected-result format,
  one visible terminal, camera-on presentation, consistent image identity, and
  separate final submission folder.

## Read in this order

0. [Current demo run sheet](DEMO_RUN_SHEET.md): prepared screens, current release
   checks, time allocations, commands, and which file fields to explain.
1. [Implementation plan](Hush_Milestone5_Implementation_Plan.md): architecture,
   budget, application changes, build/deploy sequence, tests, and acceptance.
2. [10-minute recording guide](Hush_Milestone5_10_Minute_Demo_Guide.md): setup,
   exact timing, draft narration, commands, expected results, and recovery rules.
3. [PowerPoint and analysis guide](Hush_Milestone5_PPT_and_Analysis_Guide.md):
   exactly two slides, their speaker notes, the half-page analysis, and evidence.
4. [Written analysis](Hush_Milestone5_Written_Analysis.md): evidence-based prose
   ready for the half-page PDF layout during final submission assembly.

The Kubernetes resources exist in cluster `hush-m5`. The local release manifest
now selects `v3.0.2` and the hostname is `hush.34.36.104.111.nip.io`. Resume and verify the
application before using the recording commands. The old VM is a retained
rollback path, not the Milestone 5 runtime.

## What we carry forward from the final earlier package

Milestone 3 made deployment repeatable using a versioned container. Milestone 4
moved history, settings, snippets, and upload metadata to Cloud SQL; recordings
to Cloud Storage; and credentials to Secret Manager. Its final demo used the
cloud VM through an encrypted SSH tunnel. Recovery still needed a person.

Milestone 5 replaces that compute layer with replicas managed by GKE and makes
the application reachable through public HTTPS. The recording should spend its
time proving this change. It does not need to repeat the earlier migration
row-count, Docker pull, IAM, and Secret Manager tours.

Lessons to preserve: use the latest substantive files; avoid competing “final”
versions; prepare fuller narration rather than a thin checklist; rehearse actual
waiting times; show fresh live results; and package only the required artifacts.
The previous guide targeted 9:45 to stay under a 10-minute ceiling. Preserve that
target unless the course explicitly requires a different duration.

## Earlier package planning layout

The earlier proposed nested layout below is retained as planning context. The
user requested the actual required artifacts as six flat files in the sibling
`Milestone 5` folder instead. Keep presenter notes in this repository, and add
the final video according to the course's submission instructions.

| Folder | Contents |
| --- | --- |
| `01_PowerPoint` | One editable PPTX containing exactly two slides |
| `02_Written_Analysis` | Half-page PDF; editable Markdown kept in the team docs |
| `03_Working_Artifacts` | Committed manifests, repository/commit link, certificate Active screenshot, before/after pod output, HPA evidence |
| `04_Video_and_Canvas` | Recorded video archive, OneDrive link, recording guide |

Add a submission checklist and a documentation-only teammate ZIP. Teammates get
application source from GitHub. Exclude secrets, `.env`, credential files, local
databases, `.git`, environments, and caches. Do not label a placeholder video,
certificate, or scaling result as finished evidence.

The earlier course workflow used a OneDrive share link in Canvas and cameras
visible during each presenter's section. Recheck the current Milestone 5 upload
instructions and recipient list before submission; do not treat an old guide
as proof that those administrative details are unchanged.
