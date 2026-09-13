"""Exercise setup helpers without installing software or changing permissions."""

from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from voiceflow.diagnostics.permission_diagnostic import find_python_app
from voiceflow.platform.backends.macos.text_injection import check_accessibility_permission


REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("prefix", ["opt/homebrew/Cellar/python@3.12/3.12.99",
                                     "usr/local/Cellar/python@3.12/3.12.99",
                                     "Library"])
def test_permission_app_from_venv_symlink(tmp_path, prefix):
    framework = tmp_path / prefix / "Frameworks/Python.framework/Versions/3.12"
    executable = framework / "bin/python3.12"
    executable.parent.mkdir(parents=True)
    executable.touch()
    app = framework / "Resources/Python.app"
    app.mkdir(parents=True)
    venv = tmp_path / "Hush with spaces/.venv/bin/python"
    venv.parent.mkdir(parents=True)
    venv.symlink_to(executable)
    assert find_python_app(venv, tmp_path / "unused") == app


def test_no_invented_permission_path(tmp_path):
    assert find_python_app(tmp_path / "bin/python", tmp_path) is None


def test_lets_hush_help_is_available_before_setup():
    result = subprocess.run(
        ["/bin/bash", str(REPO / "lets-hush"), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Let's Hush." in result.stdout
    assert "--permissions" in result.stdout


def test_setup_check_targets_the_package_layout():
    contents = (REPO / "setup_check.py").read_text()
    assert "voiceflow.config" in contents
    assert "voiceflow.core.transcriber" in contents
    assert "from config import" not in contents
    assert "from transcriber import" not in contents


def test_accessibility_check_uses_application_services_and_fails_closed(monkeypatch):
    monkeypatch.setitem(sys.modules, "ApplicationServices", SimpleNamespace(AXIsProcessTrusted=lambda: True))
    assert check_accessibility_permission() is True

    monkeypatch.setitem(
        sys.modules,
        "ApplicationServices",
        SimpleNamespace(AXIsProcessTrusted=lambda: (_ for _ in ()).throw(RuntimeError("unavailable"))),
    )
    assert check_accessibility_permission() is False
