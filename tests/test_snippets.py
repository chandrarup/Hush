import pytest

from voiceflow.config import snippets


def test_exact_shortcut_expands_without_rewriting_longer_dictation():
    configured = [{"name": "Greeting", "shortcut": "work intro", "text": "Hello from VoiceFlow."}]

    assert snippets.is_exact_shortcut("Work intro.", configured)
    assert snippets.expand_snippets("Work intro.", configured) == "Hello from VoiceFlow."
    assert not snippets.is_exact_shortcut("Please use work intro", configured)


def test_punctuation_only_shortcuts_are_not_registered_or_expanded(tmp_path, monkeypatch):
    snippets_path = tmp_path / "snippets.toml"
    monkeypatch.setattr(snippets, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(snippets, "SNIPPETS_PATH", snippets_path)

    with pytest.raises(ValueError, match="required"):
        snippets.add_snippet("Punctuation", "...", "Should not expand.")

    configured = [{"name": "Punctuation", "shortcut": "...", "text": "Should not expand."}]
    assert not snippets.is_exact_shortcut("...", configured)
    assert snippets.expand_snippets("...", configured) == "..."


def test_malformed_store_is_preserved_and_blocks_mutation(tmp_path, monkeypatch):
    snippets_path = tmp_path / "snippets.toml"
    malformed = b'snippets = "not a list"'
    snippets_path.write_bytes(malformed)
    monkeypatch.setattr(snippets, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(snippets, "SNIPPETS_PATH", snippets_path)

    with pytest.raises(snippets.SnippetStoreError):
        snippets.load_snippets()
    with pytest.raises(snippets.SnippetStoreError):
        snippets.add_snippet("Greeting", "hello", "Hello there.")

    assert snippets_path.read_bytes() == malformed


def test_snippets_are_saved_atomically_when_serialization_fails(tmp_path, monkeypatch):
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
