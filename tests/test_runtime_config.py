from voiceflow.app import main


def test_runtime_settings_update_pipeline_configuration(monkeypatch):
    config = {
        "asr": {"engine": "auto"},
        "llm": {"cleanup_level": "light", "ollama_model": "llama3.2:3b"},
    }
    monkeypatch.setattr(main, "_config", config)

    main._apply_runtime_settings(
        {"cleanup_level": "high", "ollama_model": "phi3:mini"}
    )

    assert config["llm"]["cleanup_level"] == "high"
    assert config["llm"]["ollama_model"] == "phi3:mini"
