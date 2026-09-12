from voiceflow.application.models import DictationStatus
from voiceflow.application.workflow import DictationWorkflow


class FakePreprocessor:
    def __init__(self, prepared=True):
        self.prepared = prepared

    def prepare(self, audio):
        return audio if self.prepared else None


class FakeTranscriber:
    def __init__(self, transcript):
        self.transcript = transcript
        self.vocab = None

    def transcribe(self, audio, vocab=None):
        self.vocab = vocab
        return self.transcript


class FakeCleaner:
    def __init__(self):
        self.calls = []

    def clean(self, transcript, *, level, app_context=None):
        self.calls.append((transcript, level, app_context))
        return f"cleaned: {transcript}"


class FakeHistory:
    def __init__(self):
        self.entries = []

    def save_entry(self, raw, clean, level="light", app=None):
        self.entries.append((raw, clean, level, app))
        return len(self.entries)


class FakeSnippets:
    def __init__(self, expanded=None, exact=False):
        self.expanded = expanded
        self.exact = exact

    def expand(self, transcript):
        return self.expanded or transcript, self.exact


class FakeEvents:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def make_workflow(transcript="hello", *, snippets=None, cleaner=None, prepared=True):
    history = FakeHistory()
    events = FakeEvents()
    cleaner = cleaner or FakeCleaner()
    workflow = DictationWorkflow(
        preprocessor=FakePreprocessor(prepared),
        transcriber=FakeTranscriber(transcript),
        cleaner=cleaner,
        history=history,
        snippets=snippets or FakeSnippets(),
        events=events,
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
