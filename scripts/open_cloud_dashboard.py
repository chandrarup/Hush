"""Open a fresh authenticated cloud dashboard without printing its private token."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tomllib
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import webbrowser


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        # Never forward an authenticated check to another destination.
        return None


def settings() -> tuple[str, str]:
    packaged = Path.home() / "Library/Application Support/Hush/config.toml"
    source = Path(__file__).resolve().parents[1] / "data/config.toml"
    path = packaged if packaged.is_file() else source
    try:
        cloud = tomllib.loads(path.read_text()).get("cloud", {})
    except (OSError, tomllib.TOMLDecodeError):
        raise ValueError("Cannot read your Hush configuration. Complete Hush setup first.") from None
    base = str(cloud.get("base_url", "")).strip().rstrip("/")
    token = str(cloud.get("token", "")).strip()
    try:
        parsed = urlsplit(base)
        valid = (parsed.scheme == "https" and parsed.hostname and not parsed.username
                 and not parsed.password and not parsed.query and not parsed.fragment)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("The saved Hush cloud address must be a valid HTTPS URL.")
    if not token or "\r" in token or "\n" in token:
        raise ValueError("Your Hush team token is missing or invalid. Complete Hush setup first.")
    return base, token


def verify(base: str, token: str) -> None:
    opener = build_opener(NoRedirect())
    try:
        with opener.open(base + "/ready", timeout=15) as response:
            ready = json.load(response)
        if ready.get("status") != "ready":
            raise ValueError("The cloud app is not ready. Resume it first if compute is paused.")
        request = Request(base + "/history?limit=1", headers={"Authorization": "Bearer " + token})
        with opener.open(request, timeout=15) as response:
            entries = json.load(response)
        if not isinstance(entries, list):
            raise ValueError("The cloud history response was unexpected. Do not assume history is empty.")
    except HTTPError as error:
        if error.code in (401, 403):
            raise ValueError("The cloud app rejected the saved Hush login. Check the team token privately.") from None
        if error.code in (502, 503, 504):
            raise ValueError("The cloud app is unavailable or still starting. Resume it first if paused.") from None
        raise ValueError(f"The cloud check returned HTTP {error.code}. No browser login was opened.") from None
    except (URLError, OSError, json.JSONDecodeError):
        raise ValueError("Cannot reach the Hush cloud app securely. Check your connection and resume status.") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Check readiness and login without opening a browser")
    args = parser.parse_args()
    try:
        base, token = settings()
        verify(base, token)
        if args.check_only:
            print("Cloud app is ready and the saved Hush login is accepted.")
            return 0
        parsed = urlsplit(base)
        target = urlunsplit((parsed.scheme, parsed.netloc, parsed.path + "/", "", urlencode({"token": token})))
        try:
            opened = webbrowser.open(target, new=2, autoraise=True)
        except (webbrowser.Error, OSError):
            raise ValueError("Could not open your browser. The saved cloud login was verified.") from None
        if not opened:
            raise ValueError("Could not open your browser. The saved cloud login was verified.")
        print("Opened an authenticated Hush cloud dashboard in a new tab. Select History to view saved speech.")
        print("Keep this tab open. Refreshing it preserves its login; a plain URL in another tab does not.")
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
