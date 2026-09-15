"""A compact bottom-of-screen recording indicator for the macOS Hush app."""

from __future__ import annotations

import time

try:
    import objc
    from AppKit import (
        NSBackingStoreBuffered,
        NSBezierPath,
        NSColor,
        NSFont,
        NSFontAttributeName,
        NSFontWeightMedium,
        NSFloatingWindowLevel,
        NSForegroundColorAttributeName,
        NSMakePoint,
        NSMakeRect,
        NSOperationQueue,
        NSPanel,
        NSScreen,
        NSView,
        NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSWindowCollectionBehaviorFullScreenAuxiliary,
        NSWindowStyleMaskBorderless,
    )
    from Foundation import NSAttributedString, NSTimer

    _APPKIT_AVAILABLE = True
except ImportError:
    _APPKIT_AVAILABLE = False


if _APPKIT_AVAILABLE:

    class _WaveformView(NSView):
        """Draw a deliberately calm, low-distraction status waveform."""

        def initWithFrame_(self, frame):
            self = objc.super(_WaveformView, self).initWithFrame_(frame)
            if self is None:
                return None
            self._state = "idle"
            self._phase = 0
            self._started_at = None
            self._timer = None
            return self

        def set_state(self, state: str) -> None:
            self._state = state
            if state == "recording":
                self._started_at = time.monotonic()
                self._start_timer()
            elif state == "processing":
                self._started_at = None
                self._start_timer()
            else:
                self._started_at = None
                self._stop_timer()
            self.setNeedsDisplay_(True)

        def _start_timer(self) -> None:
            if self._timer is None:
                self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                    0.12,
                    self,
                    "advanceFrame:",
                    None,
                    True,
                )

        def _stop_timer(self) -> None:
            if self._timer is not None:
                self._timer.invalidate()
                self._timer = None

        def advanceFrame_(self, _timer) -> None:
            self._phase = (self._phase + 1) % 10_000
            self.setNeedsDisplay_(True)

        def drawRect_(self, _dirty_rect) -> None:
            bounds = self.bounds()
            panel_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bounds, 18, 18)
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.045, 0.075, 0.085, 0.94).set()
            panel_path.fill()

            is_recording = self._state == "recording"
            wave_color = (
                NSColor.colorWithCalibratedRed_green_blue_alpha_(0.22, 0.88, 0.72, 1.0)
                if is_recording
                else NSColor.colorWithCalibratedRed_green_blue_alpha_(0.98, 0.69, 0.27, 1.0)
            )
            base_heights = (9, 17, 27, 19, 32, 19, 27, 17, 9)
            center_y = bounds.size.height / 2
            start_x = 23

            for index, base_height in enumerate(base_heights):
                offset = (self._phase + index * 3) % 8
                height = base_height + (offset - 3) * (2 if is_recording else 1)
                path = NSBezierPath.bezierPath()
                path.setLineWidth_(3)
                path.setLineCapStyle_(1)
                x = start_x + index * 7
                path.moveToPoint_(NSMakePoint(x, center_y - height / 2))
                path.lineToPoint_(NSMakePoint(x, center_y + height / 2))
                wave_color.set()
                path.stroke()

            label = "Listening" if is_recording else "Transcribing"
            if is_recording and self._started_at is not None:
                elapsed = int(time.monotonic() - self._started_at)
                label = f"Listening  {elapsed // 60}:{elapsed % 60:02d}"
            attributes = {
                NSFontAttributeName: NSFont.systemFontOfSize_weight_(13, NSFontWeightMedium),
                NSForegroundColorAttributeName: NSColor.colorWithCalibratedWhite_alpha_(0.96, 1.0),
            }
            text = NSAttributedString.alloc().initWithString_attributes_(label, attributes)
            text.drawAtPoint_(NSMakePoint(98, center_y - 8))


class MacOSRecordingHUD:
    """Own an AppKit panel while leaving all other platforms unchanged."""

    _WIDTH = 226
    _HEIGHT = 56
    _BOTTOM_MARGIN = 34

    def __init__(self) -> None:
        self._panel = None
        self._view = None

    def prepare(self) -> None:
        """Create the panel on the AppKit main thread before pystray starts."""
        if not _APPKIT_AVAILABLE or self._panel is not None:
            return

        frame = NSMakeRect(0, 0, self._WIDTH, self._HEIGHT)
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setLevel_(NSFloatingWindowLevel)
        panel.setHidesOnDeactivate_(False)
        panel.setIgnoresMouseEvents_(True)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        view = _WaveformView.alloc().initWithFrame_(frame)
        panel.setContentView_(view)
        self._panel = panel
        self._view = view
        self._position_panel()

    def set_state(self, state: str) -> None:
        if not _APPKIT_AVAILABLE:
            return
        NSOperationQueue.mainQueue().addOperationWithBlock_(lambda: self._set_state_on_main_thread(state))

    def _set_state_on_main_thread(self, state: str) -> None:
        self.prepare()
        if self._panel is None or self._view is None:
            return
        if state == "idle":
            self._panel.orderOut_(None)
            self._view.set_state("idle")
            return
        self._position_panel()
        self._view.set_state(state)
        self._panel.orderFrontRegardless()

    def _position_panel(self) -> None:
        if self._panel is None:
            return
        screen = NSScreen.mainScreen()
        if screen is None:
            return
        visible = screen.visibleFrame()
        x = visible.origin.x + (visible.size.width - self._WIDTH) / 2
        y = visible.origin.y + self._BOTTOM_MARGIN
        self._panel.setFrameOrigin_(NSMakePoint(x, y))
