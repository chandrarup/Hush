import time

from voiceflow.core import cleaner


def test_cleaner_waits_for_final_ollama_result(monkeypatch):
    raw = "Hey, so um like I was thinking maybe we should meet at four pm."

    monkeypatch.setattr(cleaner, "_docker_llm_available", False)
    monkeypatch.setattr(cleaner, "_OLLAMA_SDK", True)

    def slow_ollama(*args, **kwargs):
        time.sleep(0.02)
        return "Let's meet at 4 pm."

    monkeypatch.setattr(cleaner, "_call_ollama_sdk", slow_ollama)

    assert cleaner.clean_transcript(raw, level="high") == "Let's meet at 4 pm."
