"""Bounded real transcription load. Credentials stay in process memory."""
from __future__ import annotations

import concurrent.futures
import json
import os
import threading
import time

import requests
from google.cloud import secretmanager, storage


def main() -> None:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    secret = os.getenv("HUSH_TEAM_TOKEN_SECRET", "hush-team-token")
    token = secretmanager.SecretManagerServiceClient().access_secret_version(
        request={"name": f"projects/{project}/secrets/{secret}/versions/latest"}
    ).payload.data.decode().strip()
    sample = storage.Client(project=project).bucket(os.environ["HUSH_UPLOAD_BUCKET"]).blob(
        os.getenv("HUSH_LOAD_SAMPLE", "milestone5-demo/load-sample.wav")
    ).download_as_bytes(timeout=20)
    target = os.environ["HUSH_LOAD_TARGET"].rstrip("/")
    host = os.environ["HUSH_PUBLIC_HOST"]
    duration = min(max(int(os.getenv("HUSH_LOAD_SECONDS", "180")), 1), 180)
    concurrency = min(max(int(os.getenv("HUSH_LOAD_CONCURRENCY", "4")), 1), 8)
    deadline = time.monotonic() + duration
    counts: dict[str, int] = {}
    lock = threading.Lock()

    def worker() -> None:
        with requests.Session() as session:
            session.headers.update({"Authorization": f"Bearer {token}", "Host": host,
                                    "Origin": f"https://{host}", "Content-Type": "audio/wav",
                                    "X-Hush-Filename": "milestone5-load.wav", "Connection": "close"})
            while time.monotonic() < deadline:
                try:
                    response = session.post(f"{target}/transcribe", data=sample, timeout=(5, 45))
                    result = str(response.status_code)
                except requests.RequestException:
                    result = "transport_error"
                with lock:
                    counts[result] = counts.get(result, 0) + 1
                if result != "200":
                    time.sleep(1)

    print(json.dumps({"event": "load_started", "seconds": duration, "concurrency": concurrency}), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        list(executor.map(lambda _: worker(), range(concurrency)))
    print(json.dumps({"event": "load_finished", "responses": counts}), flush=True)
    if not counts.get("200"):
        raise SystemExit("No successful transcription requests")


if __name__ == "__main__":
    main()
