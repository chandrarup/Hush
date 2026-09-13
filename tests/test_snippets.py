import pytest

from voiceflow.config import snippets


def test_snippet_save_is_atomic_when_serialization_fails(tmp_path, monkeypatch):
    snippets_path = tmp_path / "snippets.toml"
    monkeypatch.setattr(snippets, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(snippets, "SNIPPETS_PATH", snippets_path)

    snippets.add_snippet("Greeting", "hello", "Hello there.")
    original = snippets_path.read_bytes()

    def fail_dump(*args, **kwargs):
        raise OSError("serialization failed")

    monkeypatch.setattr(snippets.toml, "dump", fail_dump)

    with pytest.raises(OSError, match="serialization failed"):
        snippets.add_snippet("Updated", "hello", "Updated greeting.")

    assert snippets_path.read_bytes() == original
    assert list(tmp_path.glob(".snippets.toml.*.tmp")) == []
