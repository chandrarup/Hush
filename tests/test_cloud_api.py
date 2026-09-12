import pytest

from voiceflow.core.jobs import SQLiteJobRepository
from voiceflow.web.cloud_api import create_cloud_app


def test_backend_api_factory_does_not_require_desktop_services(tmp_path):
    fastapi = pytest.importorskip("fastapi")
    app = create_cloud_app(SQLiteJobRepository(tmp_path / "jobs.db"))
    routes = {route.path for route in app.routes if hasattr(route, "path")}

    assert "/health/live" in routes
    assert "/health/ready" in routes
    assert "/jobs" in routes
    assert "/jobs/{request_id}" in routes
    assert fastapi is not None
