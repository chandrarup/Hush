"""Focused tests for the packaged macOS Hush application path."""

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx

from voiceflow import runtime
from voiceflow.app import main as app_main
from voiceflow.platform.backends.common import permissions as common_permissions
from voiceflow.platform.backends.macos import tcc
from voiceflow.platform.backends.common.tray import _make_menu_image
from voiceflow.web import api_server


REPO = Path(__file__).resolve().parents[1]


def test_packaged_macos_uses_application_support(monkeypatch):
    monkeypatch.setattr(runtime.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)

    assert runtime.is_packaged_macos_app() is True
    assert runtime.user_data_dir() == Path.home() / "Library" / "Application Support" / "Hush"


def test_source_run_keeps_existing_voiceflow_data_dir(monkeypatch):
    monkeypatch.setattr(runtime.platform, "system", lambda: "Darwin")
    monkeypatch.delattr(runtime.sys, "frozen", raising=False)

    assert runtime.is_packaged_macos_app() is False
    assert runtime.user_data_dir() == Path.home() / ".voiceflow"


def test_hush_opens_setup_once_then_dashboard_on_every_later_launch():
    assert app_main._initial_browser_url(57327, first_launch=True) == (
        "http://localhost:57327/onboarding"
    )
    assert app_main._initial_browser_url(57327, first_launch=False) == "http://localhost:57327/"


def test_packaged_reinstall_reopens_onboarding_without_erasing_user_data(monkeypatch, tmp_path):
    monkeypatch.setattr(common_permissions, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(common_permissions, "_packaged_app_install_marker", lambda: "first-copy")
    permissions = common_permissions.DesktopPermissions()

    assert permissions.is_first_launch() is True
    permissions.begin_onboarding()
    assert permissions.is_onboarding_in_progress() is True
    permissions.mark_onboarded()
    assert permissions.is_first_launch() is False
    assert permissions.is_onboarding_in_progress() is False

    monkeypatch.setattr(common_permissions, "_packaged_app_install_marker", lambda: "reinstalled-copy")
    assert permissions.is_first_launch() is True


def test_mac_app_onboarding_requires_only_microphone_and_accessibility():
    permissions_source = (REPO / "voiceflow/platform/backends/macos/permissions.py").read_text()
    onboarding_source = (REPO / "voiceflow/web/ui/onboarding.html").read_text()
    release_guide = (REPO / "docs/MACOS_APP_RELEASE.md").read_text()

    assert '"input_monitoring"' not in permissions_source
    assert "Input Monitoring" not in onboarding_source
    assert "p.microphone && p.accessibility" in onboarding_source
    assert "Input Monitoring is not a required setup step" in release_guide


def test_packaged_runtime_sets_model_cache_outside_the_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "is_packaged_macos_app", lambda: True)
    monkeypatch.setattr(runtime, "user_data_dir", lambda: tmp_path / "Hush")
    monkeypatch.delenv("HF_HOME", raising=False)

    runtime.configure_runtime_environment()

    assert os.environ["HF_HOME"] == str(tmp_path / "Hush" / "Models")
    assert (tmp_path / "Hush" / "Models").is_dir()


def test_accessibility_request_uses_native_prompt(monkeypatch):
    requests = []
    monkeypatch.setitem(
        sys.modules,
        "ApplicationServices",
        SimpleNamespace(
            AXIsProcessTrustedWithOptions=lambda options: requests.append(options) or False,
            kAXTrustedCheckOptionPrompt="prompt",
        ),
    )

    assert tcc.request_accessibility() is False
    assert requests == [{"prompt": True}]


def test_microphone_request_starts_native_authorization(monkeypatch):
    requests = []

    class Device:
        @staticmethod
        def authorizationStatusForMediaType_(_media_type):
            return 0

        @staticmethod
        def requestAccessForMediaType_completionHandler_(media_type, callback):
            requests.append(media_type)
            callback(True)

    monkeypatch.setitem(
        sys.modules,
        "AVFoundation",
        SimpleNamespace(
            AVCaptureDevice=Device,
            AVAuthorizationStatusAuthorized=3,
            AVAuthorizationStatusNotDetermined=0,
            AVMediaTypeAudio="audio",
        ),
    )

    assert tcc.request_microphone() is False
    assert requests == ["audio"]


def test_input_monitoring_uses_the_hid_registration_api(monkeypatch):
    requests = []

    def check_access(request_type):
        requests.append(("check", request_type))
        return 0

    def request_access(request_type):
        requests.append(("request", request_type))
        return False

    monkeypatch.setattr(
        tcc.ctypes,
        "CDLL",
        lambda _path: SimpleNamespace(
            IOHIDCheckAccess=check_access,
            IOHIDRequestAccess=request_access,
        ),
    )
    assert tcc.is_input_monitoring_trusted() is True
    assert tcc.request_input_monitoring() is False
    assert requests == [("check", 1), ("request", 1)]


def test_menu_bar_mark_is_a_static_waveform_not_a_status_dot():
    icon = _make_menu_image()

    assert icon.size == (64, 64)
    assert icon.getbbox() is not None


def test_permission_request_endpoint_delegates_to_platform(monkeypatch):
    requested = []
    permissions = SimpleNamespace(
        request_permission=lambda permission_type: requested.append(permission_type) or False,
    )
    monkeypatch.setattr(
        api_server,
        "get_platform_services",
        lambda: SimpleNamespace(permissions=permissions),
    )

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/permissions/request/microphone")

    response = asyncio.run(exercise())

    assert response.status_code == 200
    assert response.json() == {"ok": False}
    assert requested == ["microphone"]


def test_dashboard_does_not_allow_cross_origin_access():
    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/history", headers={"Origin": "https://evil.example"})

    response = asyncio.run(exercise())

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None


def test_release_scripts_package_hush_app_not_source_tree():
    build_script = (REPO / "packaging/build_app.sh").read_text()
    dmg_script = (REPO / "packaging/build_dmg.sh").read_text()
    release_script = (REPO / "packaging/sign_and_notarize.sh").read_text()
    setup_script = (REPO / "packaging/setup_app.py").read_text()

    assert "py2app" in build_script
    assert 'APP_NAME="Hush"' in dmg_script
    assert "Hush.app was not found" in dmg_script
    assert "install.sh" not in dmg_script
    assert "HUSH_SIGNING_IDENTITY" in release_script
    assert "HUSH_NOTARY_PROFILE" in release_script
    assert "--keychain-profile" in release_script
    assert "notarytool submit" in release_script
    assert "stapler validate" in release_script
    assert 'os.environ.get("HUSH_VERSION", "1.0.0").removeprefix("v")' in setup_script
    assert "HushIcon.icns" in setup_script
    assert (REPO / "assets/HushIcon.icns").is_file()


def test_tagged_release_workflow_uses_ephemeral_secrets_and_publishes_dmg():
    workflow = (REPO / ".github/workflows/macos-release.yml").read_text()

    assert 'runs-on: macos-14' in workflow
    assert 'test "$(uname -m)" = "arm64"' in workflow
    assert 'tags:' in workflow
    assert '- "v*"' in workflow
    assert 'MACOS_CERTIFICATE_BASE64' in workflow
    assert 'APPLE_NOTARY_KEY_BASE64' in workflow
    assert 'notarytool store-credentials' in workflow
    assert 'bash packaging/sign_and_notarize.sh dist/Hush.app' in workflow
    assert 'gh release create' in workflow
    assert 'Developer ID Application:' not in workflow
    assert 'BEGIN PRIVATE KEY' not in workflow
