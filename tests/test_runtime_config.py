from voiceflow.config.runtime import RuntimeSettings


def test_runtime_settings_default_to_local(monkeypatch):
    for name in (
        "VOICEFLOW_RUNTIME_MODE",
        "VOICEFLOW_TRANSCRIPTION_PROVIDER",
        "VOICEFLOW_CLEANUP_PROVIDER",
        "VOICEFLOW_DATABASE_URL",
        "VOICEFLOW_QUEUE_BACKEND",
        "VOICEFLOW_AUDIO_BUCKET",
        "VOICEFLOW_AUTH_REQUIRED",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = RuntimeSettings.from_environment()

    assert settings.mode == "local"
    assert settings.transcription_provider == "local"
    assert settings.cleanup_provider == "local"
    assert settings.queue_backend == "in_process"
    assert settings.audio_bucket is None
    assert settings.auth_required is False


def test_runtime_settings_can_be_switched_for_a_hosted_environment(monkeypatch):
    monkeypatch.setenv("VOICEFLOW_RUNTIME_MODE", "gcp")
    monkeypatch.setenv("VOICEFLOW_TRANSCRIPTION_PROVIDER", "vertex")
    monkeypatch.setenv("VOICEFLOW_CLEANUP_PROVIDER", "vertex")
    monkeypatch.setenv("VOICEFLOW_DATABASE_URL", "postgresql://voiceflow")
    monkeypatch.setenv("VOICEFLOW_QUEUE_BACKEND", "pubsub")
    monkeypatch.setenv("VOICEFLOW_AUDIO_BUCKET", "voiceflow-audio")
    monkeypatch.setenv("VOICEFLOW_AUTH_REQUIRED", "true")

    settings = RuntimeSettings.from_environment()

    assert settings.mode == "gcp"
    assert settings.transcription_provider == "vertex"
    assert settings.cleanup_provider == "vertex"
    assert settings.database_url == "postgresql://voiceflow"
    assert settings.queue_backend == "pubsub"
    assert settings.audio_bucket == "voiceflow-audio"
    assert settings.auth_required is True
