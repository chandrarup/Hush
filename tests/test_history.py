from voiceflow.core import history


def test_history_save_is_idempotent_for_request_id(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "history.db")
    history.init_db()

    first = history.save_entry("hello", "Hello.", request_id="request-1")
    retried = history.save_entry("hello", "Hello.", request_id="request-1")

    assert retried == first
    assert len(history.get_entries()) == 1
