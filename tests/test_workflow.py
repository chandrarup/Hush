from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from time import monotonic, sleep

import pytest

from voiceflow.application.models import DictationStatus
from voiceflow.application.jobs import DictationJob, JobClaim, JobStatus
from voiceflow.application.workflow import DictationWorkflow
from voiceflow.core.jobs import SQLiteJobRepository


class FakePreprocessor:
    def __init__(self, prepared=True, error=None):
        self.prepared = prepared
        self.error = error

    def prepare(self, audio):
        if self.error:
            raise self.error
        return audio if self.prepared else None


class FakeTranscriber:
    def __init__(self, transcript):
        self.transcript = transcript
        self.vocab = None

    def transcribe(self, audio, vocab=None):
        self.vocab = vocab
        return self.transcript


class FakeCleaner:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def clean(self, transcript, *, level, app_context=None):
        if self.error:
            raise self.error
        self.calls.append((transcript, level, app_context))
        return f"cleaned: {transcript}"


class FakeHistory:
    def __init__(self):
        self.entries = []
        self.request_ids = {}

    def save_entry(self, raw, clean, level="light", app=None, request_id=None):
        if request_id in self.request_ids:
            return self.request_ids[request_id]
        self.entries.append((raw, clean, level, app))
        entry_id = len(self.entries)
        self.request_ids[request_id] = entry_id
        return entry_id


class FakeSnippets:
    def __init__(self, expanded=None, exact=False):
        self.expanded = expanded
        self.exact = exact

    def expand(self, transcript):
        return self.expanded or transcript, self.exact


class FakeEvents:
    def __init__(self, error=None):
        self.events = []
        self.error = error

    def publish(self, event):
        if self.error:
            raise self.error
        self.events.append(event)


class FakeJobs:
    def __init__(self):
        self.statuses = []
        self.existing = None

    def create(self, request_id, user_id=None):
        if self.existing is not None:
            return self.existing
        self.statuses.append((request_id, JobStatus.ACCEPTED))
        return DictationJob(request_id=request_id, status=JobStatus.ACCEPTED)

    def claim_processing(self, request_id, claim_token):
        job = DictationJob(
            request_id=request_id,
            status=JobStatus.PROCESSING,
            claim_token=claim_token,
        )
        self.statuses.append((request_id, JobStatus.PROCESSING, {"claim_token": claim_token}))
        return JobClaim(job=job, acquired=True)

    def renew_processing(self, request_id, claim_token):
        self.statuses.append((request_id, JobStatus.PROCESSING, {"renewed": claim_token}))
        return True

    def update(self, request_id, status, **kwargs):
        self.statuses.append((request_id, status, kwargs))

    def get_for_owner(self, request_id, user_id):
        return self.existing


class LeaseLostJobs(FakeJobs):
    def __init__(self):
        super().__init__()
        self.renew_attempts = 0

    def renew_processing(self, request_id, claim_token):
        self.renew_attempts += 1
        return False


class FailedUpdateRejectedJobs(FakeJobs):
    def update(self, request_id, status, **kwargs):
        if status is JobStatus.FAILED:
            raise KeyError(f"Claim lost for {request_id}")
        super().update(request_id, status, **kwargs)


class BlockingTranscriber(FakeTranscriber):
    def __init__(self, started, release):
        super().__init__("hello")
        self.started = started
        self.release = release

    def transcribe(self, audio, vocab=None):
        self.started.set()
        self.release.wait(timeout=2)
        return super().transcribe(audio, vocab=vocab)


def make_workflow(
    transcript="hello",
    *,
    snippets=None,
    cleaner=None,
    prepared=True,
    preprocessor_error=None,
    event_error=None,
    jobs=None,
    transcriber=None,
    cleaner_error=None,
    lease_renewal_interval_seconds=30.0,
):
    history = FakeHistory()
    events = FakeEvents(error=event_error)
    cleaner = cleaner or FakeCleaner(error=cleaner_error)
    workflow = DictationWorkflow(
        preprocessor=FakePreprocessor(prepared, error=preprocessor_error),
        transcriber=transcriber or FakeTranscriber(transcript),
        cleaner=cleaner,
        history=history,
        snippets=snippets or FakeSnippets(),
        events=events,
        jobs=jobs,
        lease_renewal_interval_seconds=lease_renewal_interval_seconds,
    )
    return workflow, cleaner, history, events


def test_workflow_processes_and_persists_a_completed_dictation():
    workflow, cleaner, history, events = make_workflow("hello there")

    result = workflow.process(
        object(),
        vocab=["VoiceFlow"],
        cleanup_level="medium",
        app_context="Mail",
        request_id="request-1",
    )

    assert result.status is DictationStatus.COMPLETED
    assert result.request_id == "request-1"
    assert result.raw_text == "hello there"
    assert result.clean_text == "cleaned: hello there"
    assert result.entry_id == 1
    assert history.entries == [("hello there", "cleaned: hello there", "medium", "Mail")]
    assert cleaner.calls == [("hello there", "medium", "Mail")]
    assert events.events[0]["request_id"] == "request-1"


def test_exact_snippet_skips_cleanup_and_persists_expansion():
    workflow, cleaner, history, _ = make_workflow(
        "my signature",
        snippets=FakeSnippets("Best regards, Vishnu", exact=True),
    )

    result = workflow.process(object())

    assert result.status is DictationStatus.COMPLETED
    assert result.clean_text == "Best regards, Vishnu"
    assert cleaner.calls == []
    assert history.entries[0][1] == "Best regards, Vishnu"


def test_short_or_silent_audio_is_discarded_without_side_effects():
    workflow, cleaner, history, events = make_workflow(prepared=False)

    result = workflow.process(object())

    assert result.status is DictationStatus.DISCARDED
    assert cleaner.calls == []
    assert history.entries == []
    assert events.events == []


def test_workflow_updates_durable_job_lifecycle():
    jobs = FakeJobs()
    workflow, _, _, _ = make_workflow(jobs=jobs)

    result = workflow.process(object(), request_id="request-2")

    assert result.status is DictationStatus.COMPLETED
    assert jobs.statuses[0] == ("request-2", JobStatus.ACCEPTED)
    assert jobs.statuses[1][1] is JobStatus.PROCESSING
    assert jobs.statuses[2][1] is JobStatus.PROCESSING
    assert jobs.statuses[3][1] is JobStatus.COMPLETED


def test_workflow_retries_an_abandoned_processing_claim_without_duplicate_history(tmp_path):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def clock():
        return now

    jobs = SQLiteJobRepository(
        tmp_path / "jobs.db",
        processing_lease_seconds=30,
        clock=clock,
    )
    jobs.create("request-abandoned")
    abandoned = jobs.claim_processing("request-abandoned", "stopped-worker")
    assert abandoned.acquired is True

    now += timedelta(seconds=31)
    workflow, _, history, events = make_workflow(jobs=jobs)
    retried = workflow.process(object(), request_id="request-abandoned")

    assert retried.status is DictationStatus.COMPLETED
    assert len(history.entries) == 1
    assert len(events.events) == 1
    assert jobs.get("request-abandoned").status is JobStatus.COMPLETED
    with pytest.raises(KeyError):
        jobs.update(
            "request-abandoned",
            JobStatus.COMPLETED,
            entry_id=999,
            claim_token="stopped-worker",
        )
    assert jobs.get("request-abandoned").entry_id == retried.entry_id


def test_stale_worker_losing_lease_cannot_persist_or_publish_result():
    jobs = LeaseLostJobs()
    workflow, _, history, events = make_workflow(jobs=jobs)

    result = workflow.process(object(), request_id="request-reclaimed")

    assert result.status is DictationStatus.FAILED
    assert result.error == "dictation job processing lease was lost"
    assert history.entries == []
    assert events.events == []


def test_lost_claim_during_failure_does_not_publish_failed_result():
    jobs = FailedUpdateRejectedJobs()
    workflow, _, history, events = make_workflow(
        jobs=jobs,
        cleaner_error=RuntimeError("cleanup failed"),
    )

    result = workflow.process(object(), request_id="request-failed-claim")

    assert result.status is DictationStatus.FAILED
    assert result.error == "dictation job processing lease was lost"
    assert history.entries == []
    assert events.events == []


def test_processing_lease_is_renewed_while_transcriber_is_active(tmp_path):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def clock():
        return now

    jobs = SQLiteJobRepository(
        tmp_path / "jobs.db",
        processing_lease_seconds=0.05,
        clock=clock,
    )
    jobs.create("request-long-running")
    started = Event()
    release = Event()
    transcriber = BlockingTranscriber(started, release)
    workflow, _, _, _ = make_workflow(
        jobs=jobs,
        transcriber=transcriber,
        lease_renewal_interval_seconds=0.01,
    )
    result_holder = {}

    worker = Thread(
        target=lambda: result_holder.setdefault(
            "result",
            workflow.process(object(), request_id="request-long-running"),
        )
    )
    worker.start()
    assert started.wait(timeout=1)

    now += timedelta(seconds=1)
    deadline = monotonic() + 1
    while jobs.get("request-long-running").updated_at < now and monotonic() < deadline:
        sleep(0.005)

    competing_claim = jobs.claim_processing("request-long-running", "worker-2")
    assert competing_claim.acquired is False

    release.set()
    worker.join(timeout=1)
    assert not worker.is_alive()
    assert result_holder["result"].status is DictationStatus.COMPLETED


def test_retrying_completed_job_returns_saved_result_without_duplicate_history():
    jobs = FakeJobs()
    workflow, cleaner, history, _ = make_workflow(jobs=jobs)
    first = workflow.process(object(), request_id="request-3")

    jobs.existing = type(
        "CompletedJob",
        (),
        {
            "status": JobStatus.COMPLETED,
            "raw_text": first.raw_text,
            "clean_text": first.clean_text,
            "entry_id": first.entry_id,
        },
    )()
    second = workflow.process(object(), request_id="request-3")

    assert second.clean_text == first.clean_text
    assert len(history.entries) == 1
    assert len(cleaner.calls) == 1


def test_preprocessor_failure_marks_job_failed():
    jobs = FakeJobs()
    workflow, _, history, _ = make_workflow(
        jobs=jobs,
        preprocessor_error=RuntimeError("audio preprocessing failed"),
    )

    result = workflow.process(object(), request_id="request-preprocess")

    assert result.status is DictationStatus.FAILED
    assert "preprocessing failed" in result.error
    assert history.entries == []
    assert jobs.statuses[-1][1] is JobStatus.FAILED


def test_event_publisher_failure_does_not_change_completed_result_or_job():
    jobs = FakeJobs()
    workflow, _, history, _ = make_workflow(
        jobs=jobs,
        event_error=RuntimeError("subscriber disconnected"),
    )

    result = workflow.process(object(), request_id="request-event")

    assert result.status is DictationStatus.COMPLETED
    assert len(history.entries) == 1
    assert jobs.statuses[-1][1] is JobStatus.COMPLETED
