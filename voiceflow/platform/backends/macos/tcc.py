"""macOS TCC permission checks and user-initiated permission requests."""

from __future__ import annotations

import ctypes
import threading


_IOKIT_PATH = "/System/Library/Frameworks/IOKit.framework/IOKit"
_HID_REQUEST_LISTEN_EVENT = 1
_HID_ACCESS_GRANTED = 0


def _hid_access_function(name: str, result_type):
    """Load an Input Monitoring TCC function from macOS's IOKit framework."""
    library = ctypes.CDLL(_IOKIT_PATH)
    function = getattr(library, name)
    function.argtypes = [ctypes.c_uint32]
    function.restype = result_type
    return function


def _run_on_main_thread(operation):
    """Run TCC UI work on AppKit's main queue when Hush is already running."""
    try:
        from Foundation import NSOperationQueue, NSThread

        if NSThread.isMainThread():
            return operation()

        completed = threading.Event()
        result = {"value": False}

        def run() -> None:
            try:
                result["value"] = operation()
            finally:
                completed.set()

        NSOperationQueue.mainQueue().addOperationWithBlock_(run)
        if completed.wait(timeout=5):
            return result["value"]
    except Exception:
        pass
    return operation()


def is_accessibility_trusted() -> bool:
    try:
        from ApplicationServices import AXIsProcessTrusted

        return bool(AXIsProcessTrusted())
    except Exception:
        return False


def request_accessibility() -> bool:
    """Ask macOS to show its Accessibility approval prompt when needed."""
    try:
        from ApplicationServices import (
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )

        return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
    except Exception:
        return False


def is_microphone_authorized() -> bool:
    try:
        from AVFoundation import AVCaptureDevice, AVAuthorizationStatusAuthorized, AVMediaTypeAudio

        return AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio) == AVAuthorizationStatusAuthorized
    except Exception:
        return False


def microphone_authorization_status() -> str:
    """Return the microphone state needed to choose a user-initiated recovery."""
    try:
        from AVFoundation import (
            AVCaptureDevice,
            AVAuthorizationStatusAuthorized,
            AVAuthorizationStatusDenied,
            AVAuthorizationStatusNotDetermined,
            AVAuthorizationStatusRestricted,
            AVMediaTypeAudio,
        )

        status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
        states = {
            AVAuthorizationStatusAuthorized: "authorized",
            AVAuthorizationStatusNotDetermined: "not_determined",
            AVAuthorizationStatusDenied: "denied",
            AVAuthorizationStatusRestricted: "restricted",
        }
        return states.get(status, "unknown")
    except Exception:
        return "unknown"


def request_microphone() -> bool:
    """Start the native microphone authorization request without blocking the UI."""
    try:
        from AVFoundation import (
            AVCaptureDevice,
            AVAuthorizationStatusAuthorized,
            AVAuthorizationStatusNotDetermined,
            AVMediaTypeAudio,
        )

        status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
        if status == AVAuthorizationStatusAuthorized:
            return True
        if status == AVAuthorizationStatusNotDetermined:
            AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                AVMediaTypeAudio,
                lambda _granted: None,
            )
    except Exception:
        pass
    return False


def is_input_monitoring_trusted() -> bool:
    """Return a best-effort legacy Input Monitoring decision without prompting.

    Hush does not use this for normal onboarding: Accessibility grants both
    event listening and event posting for its global hotkey and text injection.
    """
    try:
        check_access = _hid_access_function("IOHIDCheckAccess", ctypes.c_uint32)

        return check_access(_HID_REQUEST_LISTEN_EVENT) == _HID_ACCESS_GRANTED
    except Exception:
        try:
            from Quartz import CGPreflightListenEventAccess

            return bool(CGPreflightListenEventAccess())
        except Exception:
            return False


def request_input_monitoring() -> bool:
    """Register Hush for Input Monitoring from a user-initiated setup action."""
    def request() -> bool:
        try:
            request_access = _hid_access_function("IOHIDRequestAccess", ctypes.c_bool)
            return bool(request_access(_HID_REQUEST_LISTEN_EVENT))
        except Exception:
            return False

    return bool(_run_on_main_thread(request))
