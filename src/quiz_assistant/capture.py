from __future__ import annotations

from threading import Event
from typing import Any, Protocol

from PIL import Image
import win32gui
from windows_capture import Frame, InternalCaptureControl, WindowsCapture


class CaptureError(RuntimeError):
    """A user-facing failure to capture a selected window."""


class CaptureBackend(Protocol):
    def is_window(self, hwnd: int) -> bool: ...

    def is_minimized(self, hwnd: int) -> bool: ...

    def capture_graphics_window(self, hwnd: int) -> Image.Image | None: ...


def frame_to_image(frame: Any) -> Image.Image:
    """Copy a Windows Capture BGR frame into an independent RGB image."""
    bgr = frame.convert_to_bgr().frame_buffer
    rgb = bgr[:, :, ::-1].copy()
    return Image.fromarray(rgb)


class WindowsGraphicsCaptureBackend:
    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = timeout_seconds

    def is_window(self, hwnd: int) -> bool:
        return bool(win32gui.IsWindow(hwnd))

    def is_minimized(self, hwnd: int) -> bool:
        return bool(win32gui.IsIconic(hwnd))

    def capture_graphics_window(self, hwnd: int) -> Image.Image | None:
        done = Event()
        outcome: dict[str, object] = {}
        capture = WindowsCapture(
            cursor_capture=False,
            draw_border=False,
            window_hwnd=hwnd,
        )

        @capture.event
        def on_frame_arrived(
            frame: Frame, capture_control: InternalCaptureControl
        ) -> None:
            try:
                outcome["image"] = frame_to_image(frame)
            except Exception as exc:
                outcome["error"] = exc
            finally:
                capture_control.stop()
                done.set()

        @capture.event
        def on_closed() -> None:
            if "image" not in outcome and "error" not in outcome:
                outcome["error"] = RuntimeError("capture item closed")
            done.set()

        control = capture.start_free_threaded()
        if not done.wait(self.timeout_seconds):
            control.stop()
            control.wait()
            raise TimeoutError("graphics capture timed out")
        control.wait()

        error = outcome.get("error")
        if isinstance(error, BaseException):
            raise error
        image = outcome.get("image")
        return image if isinstance(image, Image.Image) else None


def capture_window(
    hwnd: int, backend: CaptureBackend | None = None
) -> Image.Image:
    capture_backend = backend or WindowsGraphicsCaptureBackend()
    if not capture_backend.is_window(hwnd):
        raise CaptureError("目标窗口已关闭，请重新选择")
    if capture_backend.is_minimized(hwnd):
        raise CaptureError("目标窗口已最小化，请先恢复窗口")

    try:
        image = capture_backend.capture_graphics_window(hwnd)
    except Exception as exc:
        raise CaptureError(
            "Windows 图形捕获失败，请恢复目标窗口后重试"
        ) from exc
    if image is None:
        raise CaptureError("Windows 图形捕获没有返回画面")
    return image
