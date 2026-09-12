import toml

from voiceflow.config import loader


def test_config_updates_replace_file_atomically_without_leaving_temp_files(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(loader, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(loader, "CONFIG_PATH", config_path)

    loader.update_config_value("llm", "cleanup_level", "medium")

    assert toml.load(config_path)["llm"]["cleanup_level"] == "medium"
    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob(".*.tmp")) == []
