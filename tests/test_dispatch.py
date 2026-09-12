from voiceflow.application.dispatch import LocalThreadDispatcher


def test_local_dispatcher_runs_work_without_exposing_thread_details():
    completed = []

    LocalThreadDispatcher(name="test-job").dispatch(
        lambda value: completed.append(value),
        "done",
    )

    # The dispatcher is intentionally asynchronous. Wait briefly without
    # making the test depend on a fixed worker implementation.
    import time

    deadline = time.monotonic() + 1
    while not completed and time.monotonic() < deadline:
        time.sleep(0.01)

    assert completed == ["done"]
