# Hush Milestone 5: deployment and demo package

Prepared October 22, 2026. Deployment verification continues October 23 UTC.
Read [the live deployment report](LIVE_DEPLOYMENT.md) for actual results and
pause/resume instructions. The two-slide PowerPoint and recorded video still
need to be assembled; the detailed guides below are their preparation material.

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
- Leave presenter names and assignments open. The recording guide is divided
  into timed sections that can be assigned later.
- Retain the earlier milestones' detailed show/run/say/expected-result format,
  one visible terminal, camera-on presentation, consistent image identity, and
  separate final submission folder.

## Read in this order

1. [Implementation plan](Hush_Milestone5_Implementation_Plan.md): architecture,
   budget, application changes, build/deploy sequence, tests, and acceptance.
2. [10-minute recording guide](Hush_Milestone5_10_Minute_Demo_Guide.md): setup,
   exact timing, draft narration, commands, expected results, and recovery rules.
3. [PowerPoint and analysis guide](Hush_Milestone5_PPT_and_Analysis_Guide.md):
   exactly two slides, their speaker notes, the half-page analysis, and evidence.
4. [Written analysis](Hush_Milestone5_Written_Analysis.md): evidence-based prose
   ready for the half-page PDF layout during final submission assembly.

The Kubernetes resources now exist in cluster `hush-m5`. Use the final
`v3.0.1` digest and `hush.34.36.104.111.nip.io` hostname. Resume and verify the
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

## Final package to assemble after successful verification

Create `SUBMISSION_READY/` only after the evidence is real. Its planned contents:

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
