"""Exercise the real deploy shell script with fake cloud and Kubernetes CLIs."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHA = "b" * 40
PREVIOUS_IMAGE = "us-central1-docker.pkg.dev/hush-milestone-2-20260922/hush-containers/hush@sha256:" + "a" * 64
NEW_IMAGE = "us-central1-docker.pkg.dev/hush-milestone-2-20260922/hush-containers/hush@sha256:" + "b" * 64

FAKE_CLI = r'''#!/usr/bin/env python3
import json
import os
import pathlib
import sys

name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
path = pathlib.Path(os.environ["MOCK_STATE"])
state = json.loads(path.read_text())

def save():
    path.write_text(json.dumps(state))

if name == "sleep":
    sys.exit(0)
if name == "gcloud":
    if args[:3] == ["artifacts", "docker", "images"]:
        print(state["new_image"])
    elif args[:3] == ["container", "clusters", "get-credentials"]:
        state["calls"].append("credentials")
    elif args[:3] == ["secrets", "versions", "access"]:
        state["calls"].append("secret-access")
        print("private-demo-token")
    else:
        sys.exit(3)
    save()
    sys.exit(0)
if name == "kubectl":
    if "get" in args:
        if ".image" in args[-1]:
            print(state["image"], end="")
        elif "revision" in args[-1]:
            print(state["revision"], end="")
        elif ".value" in args[-1]:
            print(state["release_sha"], end="")
        else:
            sys.exit(4)
    elif "patch" in args:
        patch = json.loads(args[args.index("-p") + 1])
        container = patch["spec"]["template"]["spec"]["containers"][0]
        state["image"] = container["image"]
        state["release_sha"] = container["env"][0]["value"]
        state["revision"] = "2"
        state["calls"].append("patch")
    elif "undo" in args:
        state["image"] = state["previous_image"]
        state["release_sha"] = "previous-release"
        state["revision"] = "3"
        state["calls"].append("undo")
        if os.environ.get("MOCK_UNDO_FAIL") == "1":
            sys.exit(5)
    elif "status" in args:
        state["calls"].append("rollout-status")
    else:
        sys.exit(6)
    save()
    sys.exit(0)
if name == "curl":
    if args[-1].endswith("/ready"):
        state["calls"].append("ready")
        if os.environ.get("MOCK_NEW_READY_FAIL") == "1" and state["image"] == state["new_image"]:
            save()
            sys.exit(22)
        body = {"status": "ready", "mode": "managed", "checks": {"database": True, "storage": True, "secrets": True, "model": True}, "release_sha": state["release_sha"]}
        pathlib.Path(args[args.index("--output") + 1]).write_text(json.dumps(body))
    elif "/history?limit=1" in args[-1]:
        state["calls"].append("history")
        if "Authorization: Bearer private-demo-token" not in args:
            sys.exit(7)
    else:
        sys.exit(8)
    save()
    sys.exit(0)
sys.exit(9)
'''


def run_pipeline(tmp_path: Path, **overrides: str):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "fake_cli"
    fake.write_text(FAKE_CLI)
    fake.chmod(0o755)
    for name in ("gcloud", "kubectl", "curl", "sleep"):
        (bin_dir / name).symlink_to(fake)
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "image": PREVIOUS_IMAGE,
        "previous_image": PREVIOUS_IMAGE,
        "new_image": NEW_IMAGE,
        "release_sha": "previous-release",
        "revision": "1",
        "calls": [],
    }))
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "MOCK_STATE": str(state_path),
        "HUSH_PROJECT": "hush-milestone-2-20260922",
        "HUSH_BRANCH": "milestone6-deploy",
        "HUSH_EXPECTED_BRANCH": "milestone6-deploy",
        "HUSH_COMMIT_SHA": SHA,
        "HUSH_IMAGE_TAG": f"us-central1-docker.pkg.dev/hush-milestone-2-20260922/hush-containers/hush:{SHA}",
        "HUSH_FORCE_HEALTH_FAILURE": "0",
        **overrides,
    }
    result = subprocess.run(
        ["bash", str(ROOT / "infra/milestone6/deploy_release.sh")],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    return result, json.loads(state_path.read_text())


def test_successful_release_checks_public_sha_and_authenticated_path(tmp_path):
    result, state = run_pipeline(tmp_path)
    assert result.returncode == 0, result.stderr
    assert state["image"] == NEW_IMAGE
    assert "undo" not in state["calls"]
    assert state["calls"].count("ready") >= 4
    assert "history" in state["calls"]
    assert "private-demo-token" not in result.stdout + result.stderr


def test_controlled_health_failure_restores_previous_image(tmp_path):
    result, state = run_pipeline(tmp_path, HUSH_FORCE_HEALTH_FAILURE="1")
    assert result.returncode == 42
    assert state["image"] == PREVIOUS_IMAGE
    assert "undo" in state["calls"]
    assert "Rollback verified" in result.stderr


def test_public_readiness_failure_restores_previous_image(tmp_path):
    result, state = run_pipeline(tmp_path, MOCK_NEW_READY_FAIL="1")
    assert result.returncode != 0
    assert state["image"] == PREVIOUS_IMAGE
    assert "undo" in state["calls"]
    assert "Rollback verified" in result.stderr


def test_wrong_branch_never_mutates_deployment(tmp_path):
    result, state = run_pipeline(tmp_path, HUSH_BRANCH="main")
    assert result.returncode != 0
    assert state["image"] == PREVIOUS_IMAGE
    assert "patch" not in state["calls"]
