import pytest


@pytest.fixture(autouse=True)
def allow_test_client_hostname(monkeypatch):
    """Permit httpx's synthetic host only inside the test process."""
    monkeypatch.setenv("HUSH_ALLOWED_HOSTS", "test")
