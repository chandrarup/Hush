"""Read the live Hush 5xx counter without printing Google Cloud credentials."""

import datetime as dt
import json
import subprocess
import urllib.parse
import urllib.request


PROJECT = "hush-milestone-2-20260922"
METRIC = "logging.googleapis.com/user/hush_http_5xx_count"


def main() -> None:
    token = subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True
    ).strip()
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(minutes=30)
    metric_filter = (
        f'metric.type="{METRIC}" AND resource.type="k8s_container" '
        'AND resource.labels.cluster_name="hush-m5" '
        'AND resource.labels.namespace_name="hush" '
        'AND resource.labels.container_name="hush"'
    )
    params = urllib.parse.urlencode(
        {
            "filter": metric_filter,
            "interval.startTime": start.isoformat(),
            "interval.endTime": now.isoformat(),
            "view": "FULL",
        }
    )
    url = f"https://monitoring.googleapis.com/v3/projects/{PROJECT}/timeSeries?{params}"
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    points = [
        {
            "pod": series.get("resource", {}).get("labels", {}).get("pod_name"),
            "end": point["interval"]["endTime"],
            "value": point["value"].get("int64Value"),
        }
        for series in data.get("timeSeries", [])
        for point in series.get("points", [])
    ]
    print(json.dumps(sorted(points, key=lambda point: point["end"])))


if __name__ == "__main__":
    main()
