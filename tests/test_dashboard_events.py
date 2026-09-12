from voiceflow.app import main as app_main


def test_only_completed_dictation_events_become_dashboard_entries(monkeypatch):
    pushed = []
    monkeypatch.setattr(app_main._api, "push_event", pushed.append)

    failed_event = {
        "type": "dictation_completed",
        "status": "failed",
        "request_id": "request-failed",
    }
    app_main._publish_dashboard_event(failed_event)

    assert pushed == [failed_event]


def test_completed_dictation_event_keeps_dashboard_translation(monkeypatch):
    pushed = []
    monkeypatch.setattr(app_main._api, "push_event", pushed.append)

    app_main._publish_dashboard_event(
        {
            "type": "dictation_completed",
            "status": "completed",
            "entry_id": 4,
            "raw": "hello",
            "clean": "Hello.",
        }
    )

    assert pushed[0]["type"] == "new_entry"
    assert pushed[0]["entry"]["id"] == 4
