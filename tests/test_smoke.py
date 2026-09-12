def test_hello_world():
    assert 1 + 1 == 2


def test_application_functionality():
    assert True  # Replace with actual checks for your application


def test_platform_factory_routes_by_os():
    from voiceflow.platform.factory import create_platform_services

    assert type(create_platform_services("Darwin")).__name__ == "MacOSPlatformServices"
    assert type(create_platform_services("Linux")).__name__ == "LinuxPlatformServices"
    assert type(create_platform_services("Windows")).__name__ == "WindowsPlatformServices"


def test_history_database_is_repository_local():
    from voiceflow.config.paths import HISTORY_DB_PATH, PROJECT_ROOT

    assert HISTORY_DB_PATH == PROJECT_ROOT / "data" / "history.db"
    assert HISTORY_DB_PATH.is_absolute()
