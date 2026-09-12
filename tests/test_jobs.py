from voiceflow.application.jobs import JobStatus
from voiceflow.core.jobs import SQLiteJobRepository


def test_sqlite_job_repository_is_idempotent_and_persists_lifecycle(tmp_path):
    repository = SQLiteJobRepository(tmp_path / "jobs.db")

    first = repository.create("request-1", user_id="user-1")
    duplicate = repository.create("request-1", user_id="other-user")

    assert first.status is JobStatus.ACCEPTED
    assert duplicate.user_id == "user-1"

    completed = repository.update(
        "request-1",
        JobStatus.COMPLETED,
        raw_text="hello",
        clean_text="Hello.",
        entry_id=7,
    )
    loaded = repository.get("request-1")

    assert completed.status is JobStatus.COMPLETED
    assert loaded.clean_text == "Hello."
    assert loaded.entry_id == 7
    assert loaded.created_at is not None
    assert loaded.updated_at is not None
