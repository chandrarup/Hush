"""Focused tests for the packaged macOS Hush application path."""

import asyncio
import builtins
import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx

from voiceflow import runtime
from voiceflow.app import main as app_main
from voiceflow.platform.backends.common import permissions as common_permissions
from voiceflow.platform.backends.common.tray import TrayIcon
from voiceflow.platform.backends.macos import permissions as macos_permissions
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
    monkeypatch.setattr(common_permissions, "is_packaged_macos_app", lambda: True)
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


def test_model_stack_is_imported_after_runtime_configuration():
    main_source = (REPO / "voiceflow/app/main.py").read_text()

    assert main_source.index("configure_runtime_environment()") < main_source.index(
        "from ..core.transcriber import create_transcriber"
    )


def test_recording_hud_loads_when_pyobjc_is_unavailable(monkeypatch):
    module_path = REPO / "voiceflow/platform/backends/macos/recording_hud.py"
    original_import = builtins.__import__

    def import_without_pyobjc(name, *args, **kwargs):
        if name == "objc":
            raise ImportError("PyObjC is not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_pyobjc)
    spec = importlib.util.spec_from_file_location("recording_hud_without_pyobjc", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module._APPKIT_AVAILABLE is False
    assert module.MacOSRecordingHUD().prepare() is None


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


def test_denied_microphone_opens_settings_only_after_a_user_click(monkeypatch):
    permissions = macos_permissions.MacOSPermissions()
    opened = []
    requests = []
    monkeypatch.setattr(macos_permissions, "microphone_authorization_status", lambda: "denied")
    monkeypatch.setattr(permissions, "open_system_settings", lambda kind: opened.append(kind) or True)
    monkeypatch.setattr(macos_permissions, "request_microphone", lambda: requests.append(True) or False)

    assert permissions.request_permission("microphone") is False
    assert permissions.last_permission_request_opened_settings is True
    assert opened == ["microphone"]
    assert requests == []


def test_first_microphone_request_keeps_the_native_prompt(monkeypatch):
    permissions = macos_permissions.MacOSPermissions()
    opened = []
    requests = []
    monkeypatch.setattr(macos_permissions, "microphone_authorization_status", lambda: "not_determined")
    monkeypatch.setattr(permissions, "open_system_settings", lambda kind: opened.append(kind) or True)
    monkeypatch.setattr(macos_permissions, "request_microphone", lambda: requests.append(True) or False)

    assert permissions.request_permission("microphone") is False
    assert permissions.last_permission_request_opened_settings is False
    assert opened == []
    assert requests == [True]


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


def test_activity_hud_receives_state_when_the_tray_is_unavailable():
    received = []
    tray = TrayIcon(activity_hud=SimpleNamespace(set_state=received.append))
    tray._enabled = False

    tray.set_state("recording")

    assert received == ["recording"]


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
            return await client.post(
                "/permissions/request/microphone",
                headers={"Origin": "http://test"},
            )

    response = asyncio.run(exercise())

    assert response.status_code == 200
    assert response.json() == {"ok": False}
    assert requested == ["microphone"]


def test_permission_request_endpoint_reports_settings_recovery(monkeypatch):
    permissions = SimpleNamespace(
        request_permission=lambda _permission_type: False,
        last_permission_request_opened_settings=True,
    )
    monkeypatch.setattr(
        api_server,
        "get_platform_services",
        lambda: SimpleNamespace(permissions=permissions),
    )

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/permissions/request/microphone",
                headers={"Origin": "http://test"},
            )

    response = asyncio.run(exercise())

    assert response.status_code == 200
    assert response.json() == {"ok": False, "opened_settings": True}


def test_dashboard_does_not_allow_cross_origin_access():
    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/status", headers={"Origin": "https://evil.example"})

    response = asyncio.run(exercise())

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None


def test_dashboard_rejects_cross_origin_mutations(monkeypatch):
    started = []
    permissions = SimpleNamespace(begin_onboarding=lambda: started.append(True))
    monkeypatch.setattr(
        api_server,
        "get_platform_services",
        lambda: SimpleNamespace(permissions=permissions),
    )

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            rejected = await client.post(
                "/onboarding/start",
                headers={"Origin": "https://evil.example"},
            )
            allowed = await client.post(
                "/onboarding/start",
                headers={"Origin": "http://test"},
            )
            missing_origin = await client.post("/onboarding/start")
            return rejected, allowed, missing_origin

    rejected, allowed, missing_origin = asyncio.run(exercise())

    assert rejected.status_code == 403
    assert allowed.status_code == 200
    assert missing_origin.status_code == 403
    assert started == [True]


def test_onboarding_reconnect_signal_requires_the_existing_page(monkeypatch):
    api_server.begin_onboarding_reconnect_window()

    async def exercise():
        transport = httpx.ASGITransport(app=api_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/onboarding/reconnect",
                headers={"Origin": "http://test"},
            )

    response = asyncio.run(exercise())

    assert response.status_code == 200
    assert api_server.wait_for_onboarding_reconnect(0) is True


def test_resumed_onboarding_only_opens_a_browser_when_the_page_does_not_reconnect(monkeypatch):
    opened = []
    monkeypatch.setattr(app_main._api, "wait_for_onboarding_reconnect", lambda _timeout: True)
    monkeypatch.setattr(
        app_main,
        "_open_browser_after_server_start",
        lambda port, first_launch: opened.append((port, first_launch)),
    )

    thread = app_main._recover_resumed_onboarding(57327, timeout_seconds=0)
    thread.join(timeout=1)
    assert opened == []

    monkeypatch.setattr(app_main._api, "wait_for_onboarding_reconnect", lambda _timeout: False)
    thread = app_main._recover_resumed_onboarding(57327, timeout_seconds=0)
    thread.join(timeout=1)
    assert opened == [(57327, True)]


def test_dashboard_does_not_show_the_source_run_config_path():
    dashboard_source = (REPO / "voiceflow/web/ui/index.html").read_text()

    assert "Currently configured in ~/.voiceflow/config.toml" not in dashboard_source
    assert "Saved automatically for this installation" in dashboard_source


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
    assert 'vars.MACOS_SKIP_SIGNING' in workflow
    assert "id: signing_mode" in workflow
    assert "steps.signing_mode.outputs.signing_enabled == 'true'" in workflow
    assert "steps.signing_mode.outputs.signing_enabled != 'true'" in workflow
    assert 'permissions:\n  contents: read' in workflow
    assert 'persist-credentials: false' in workflow
    assert 'actions/checkout@11d5960a326750d5838078e36cf38b85af677262' in workflow
    assert 'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065' in workflow
    assert 'astral-sh/setup-uv@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86' in workflow
    assert 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02' in workflow
    assert 'actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093' in workflow
    assert 'publish-release:' in workflow
    assert 'contents: write' in workflow
    assert 'notarytool store-credentials' in workflow
    assert 'bash packaging/sign_and_notarize.sh dist/Hush.app' in workflow
    assert 'bash packaging/build_dmg.sh dist/Hush.app' in workflow
    assert 'name: hush-release-dmg' in workflow
    assert 'gh release create' in workflow
    assert 'Developer ID Application:' not in workflow
    assert 'BEGIN PRIVATE KEY' not in workflow
