from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_runs_as_non_root_cloud_service():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.12.12-slim-bookworm AS builder" in dockerfile
    assert "USER hush" in dockerfile
    assert '"--host", "0.0.0.0"' in dockerfile
    assert '"--port", "57327"' in dockerfile
    assert "http://127.0.0.1:57327/ready" in dockerfile
    assert "HUSH_TEAM_TOKEN" not in dockerfile


def test_compose_keeps_only_disposable_model_caches_on_the_vm():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "ollama/ollama:0.35.0" in compose
    assert 'profiles: ["ollama"]' in compose
    assert "linux/amd64" in compose
    assert "hush-data:/app/data" not in compose
    assert "/app/data:size=16m" in compose
    assert "whisper-cache:/var/cache/hush" in compose
    assert "ollama-models:/root/.ollama" in compose
    assert "http://127.0.0.1:57327/ready" in compose
    assert "HUSH_CLOUD_SQL_INSTANCE" in compose
    assert "HUSH_UPLOAD_BUCKET" in compose
    assert "HUSH_TEAM_TOKEN:" not in compose
    assert "192.168.240.0/24" in compose
    assert '"127.0.0.1:57327:57327"' in compose
    assert "104.198.149.120" not in compose
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

    assert "HUSH_TEAM_TOKEN=" not in example
    assert "HUSH_DB_PASSWORD=" not in example
    assert "HUSH_TEAM_TOKEN_SECRET=hush-team-token" in example
    assert "HUSH_DB_PASSWORD_SECRET=hush-db-password" in example
    assert "hush:v2.0.2" in example


def test_provisioning_converges_private_managed_service_controls():
    provision = (ROOT / "infra/milestone4/provision.sh").read_text(encoding="utf-8")

    assert provision.count("--no-assign-ip") == 2
    assert "settings.ipConfiguration.ipv4Enabled" in provision
    assert provision.count("--uniform-bucket-level-access") == 2
    assert provision.count("--public-access-prevention") == 2
    assert "for secret in hush-db-password hush-team-token" in provision
