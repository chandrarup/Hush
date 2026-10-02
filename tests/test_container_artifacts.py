from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_runs_as_non_root_cloud_service():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.12.12-slim-bookworm AS builder" in dockerfile
    assert "USER hush" in dockerfile
    assert '"--host", "0.0.0.0"' in dockerfile
    assert '"--port", "57327"' in dockerfile
    assert "HUSH_TEAM_TOKEN" not in dockerfile


def test_compose_declares_private_services_and_persistent_volumes():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "ollama/ollama:0.35.0" in compose
    assert 'profiles: ["ollama"]' in compose
    assert "linux/amd64" in compose
    assert "hush-data:/app/data" in compose
    assert "whisper-cache:/var/cache/hush" in compose
    assert "ollama-models:/root/.ollama" in compose
    assert "replace-with-a-long-random-team-token" not in compose


def test_default_compose_profile_does_not_require_ollama():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    hush_service = compose.split("  hush:\n", maxsplit=1)[1].split("\nvolumes:", maxsplit=1)[0]

    assert "depends_on:" not in hush_service


def test_dockerignore_excludes_runtime_data_and_secrets():
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    for required in (".git", ".venv", "data", ".env", "*.key", "deliverables", "tests"):
        assert required in ignored


def test_example_environment_contains_placeholders_only():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "replace-with-a-long-random-team-token" in example
    assert "hush:v1" in example
