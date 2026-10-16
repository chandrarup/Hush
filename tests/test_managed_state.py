from pathlib import Path

from voiceflow.cloud import managed_state
from voiceflow.config import snippets
from voiceflow.core import history


def test_committed_migration_contains_real_managed_schema():
    migration = (
        Path(__file__).parents[1] / "migrations" / "001_initial_schema.sql"
    ).read_text(encoding="utf-8")

    for table in ("entries", "uploads", "snippets", "app_settings"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration
    assert "REFERENCES entries(id)" in migration
    assert "uploads_history_id_idx" in migration


def test_migration_discovery_ignores_macos_sidecar_files():
    discovered = sorted(managed_state._MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))

    assert [path.name for path in discovered] == ["001_initial_schema.sql"]


def test_original_filename_is_display_only_and_sanitized():
    assert managed_state._safe_original_filename("../../team/audio?.wav") == "audio_.wav"
    assert managed_state._safe_original_filename("") == "recording.wav"


def test_history_delegates_to_managed_store(monkeypatch):
    calls = []

    class Store:
        def save_entry(self, **values):
            calls.append(values)
            return 42

        def get_entries(self, limit, offset):
            return [{"id": 42, "clean": "Managed."}]

    store = Store()
    monkeypatch.setattr(history, "_managed_store", lambda: store)

    entry_id = history.save_entry(
        raw="managed",
        clean="Managed.",
        app="Web upload",
        client_id="web-upload",
    )

    assert entry_id == 42
    assert calls[0]["status"] == "final"
    assert history.get_entries() == [{"id": 42, "clean": "Managed."}]


def test_snippet_mutations_delegate_to_managed_store(monkeypatch):
    stored = []

    class Store:
        def upsert_snippet(self, name, shortcut, normalized, expanded):
            stored.append((name, shortcut, normalized, expanded))

        def list_snippets(self):
            return [{"name": "Greeting", "shortcut": "Hello!", "text": "Hello there."}]

    store = Store()
    monkeypatch.setattr(snippets, "_managed_store", lambda: store)

    result = snippets.add_snippet("Greeting", "Hello!", "Hello there.")

    assert stored == [("Greeting", "Hello!", "hello", "Hello there.")]
    assert result[0]["text"] == "Hello there."
