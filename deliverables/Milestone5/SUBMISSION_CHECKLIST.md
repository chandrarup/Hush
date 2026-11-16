# Milestone 5 recording and submission checks

Target recording length: **9:45**, maximum **10:00**. Presenter order is
1 (slides), 3 (live demo), 2 (written analysis and closing).

| Required live proof | When in the notes | Screen and command | Finish condition |
| --- | --- | --- | --- |
| Valid HTTPS and HTTP redirect | 1:40–2:35 | Chrome Hush tab: security details and matching trusted certificate. Cloud certificate tab: Active. Cloud Shell block 2: HTTP response headers. | The browser trusts the Hush hostname; HTTP returns 301 with the same HTTPS hostname in Location. Also show explicit HTTP navigation ending at HTTPS. |
| At least two healthy replicas | 2:35, before deletion | Cloud Shell block 3: Deployment and application pods; save `pods-before.txt`. | Two application pods are Running and Ready. Do not count the load generator. |
| Delete a pod live and show replacement | 2:35–4:15 | Cloud Shell block 4 selects and prints a healthy pod, deletes it, and watches pods live. Block 5 saves `pods-after.txt`. | The deletion command is visible and a different pod becomes Ready automatically. An old Terminating pod is not HPA evidence. No screenshot or old log replaces this live sequence. |
| Autoscaler actually changes count | Load starts 4:15; proof 6:10–7:55 | Cloud Shell blocks 6 and 8–9: baseline HPA, real bounded load, CPU, HPA rescale events, final count and pods. | Show two changing to three or four through HPA, with added application replicas Ready. Configuration alone, a manual scale, or only Pending pods is insufficient. |

The health-check slide and live `/health`/`/ready` responses cover the separate
probe requirement. Briefly show the five committed manifest types in GitHub:
Deployment, Service, Ingress, HPA, and PDB. Presenter 2 explains missing-PDB 5xx
failures and the scope of the tested safeguard. No other infrastructure tour is
needed.

## Terminal and browser split

- Mac Terminal resumes before recording and pauses afterward.
- All commands inside the timed demo run in the same Cloud Shell session in
  Chrome. No Git clone or manually copied pod name is required.
- Slides, website, certificate details, GitHub, and written analysis are shown
  in Chrome. Presenter notes stay outside the shared content when possible.
- Readiness, warm-up, sign-in, and rehearse-and-reset happen before the timer.

## Static submission files

The sibling `Milestone 5` folder contains the required two-slide PPTX, half-page
analysis PDF, Active certificate screenshot, before/after pod outputs, and the
user-requested Word document linking the committed source and evidence.

The saved pod outputs and original autoscaling/eviction logs are real earlier
v3.0.1 rehearsal evidence. They must retain their date/release context. The final
video demonstrates the current v3.0.2 runtime; replace the two pod text files
with its fresh captures after recording. Cloud Shell block 11 downloads the
capture archive. No video placeholder is included in the submission folder.

## Human recording gate

These boxes stay unchecked until the actual video is reviewed:

- [ ] Two application replicas visibly Running and Ready.
- [ ] Pod deletion and automatic Ready replacement shown live.
- [ ] HPA count actually changes, with the added replicas healthy.
- [ ] Trusted browser certificate and HTTP-to-HTTPS redirect both visible.
- [ ] Total recording is at most ten minutes.
- [ ] Fresh before/after pod outputs copied into the submission folder.
- [ ] Video file or accessible submission link supplied with the six static files.

Written notes, rehearsals, screenshots, and source review cannot satisfy the
human recording gate by themselves.
