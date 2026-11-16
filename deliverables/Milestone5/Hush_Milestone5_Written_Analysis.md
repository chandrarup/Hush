# Why a disruption budget matters

Without a PodDisruptionBudget, overlapping voluntary maintenance can evict both
replicas while their replacements are still starting. The load balancer then
has no ready application endpoint and requests can fail intermittently until
replacement pods pass readiness checks. A 503 can indicate unavailable backends;
a connection interrupted during termination can also produce a 502. The exact
response depends on the failure path. Having two replicas alone does not prevent
both from becoming unavailable together during maintenance.

Hush uses an HPA minimum of two during demonstrations and a PDB allowing at most
one unavailable replica. In our live eviction test, Kubernetes admitted the first
eviction but rejected an immediate attempt to evict the other healthy replica
because it would violate the disruption budget. Its replacement subsequently
became ready. This tested the maintenance safeguard directly. A separate direct
pod-deletion test demonstrated automatic replacement. Readiness checks Cloud SQL,
storage and model availability; liveness checks only the running API. Rolling
updates allow no unavailable replicas, and termination marks the pod unready
before a drain delay. Our public health monitor recorded no HTTP 5xx, although
three transport errors occurred; this does not establish zero downtime.

The PDB protects eviction-based voluntary disruption. Direct pod deletion bypasses
it, while Deployment rollouts and HPA scale-down have separate controls. It cannot
prevent abrupt node failures, database outages or every interrupted streaming
connection.
Intentional standby scales the application to zero between demonstrations and is
an acknowledged outage. We therefore attribute the observed eviction protection
to the tested configuration without claiming that a PDB guarantees availability.

Evidence: `evidence/pdb-eviction-test.json`, `pod-replacement-watch.txt` and
`public-health-monitor.jsonl`. Export the prose above to the requested half-page
PDF during final submission assembly; the evidence note is not part of its prose.
