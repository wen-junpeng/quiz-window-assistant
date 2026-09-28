import numpy as np
from PIL import Image
import pytest

from quiz_assistant.capture import CaptureError, capture_window, frame_to_image


class FakeBackend:
    def __init__(self, *, valid=True, minimized=False, graphics=None, error=None):
        self.valid = valid
        self.minimized = minimized
        self.graphics = graphics
        self.error = error
        self.capture_calls = 0

    def is_window(self, hwnd):
        return self.valid

    def is_minimized(self, hwnd):
        return self.minimized

    def capture_graphics_window(self, hwnd):
        self.capture_calls += 1
        if self.error is not None:
            raise self.error
        return self.graphics


def test_capture_returns_windows_graphics_capture_frame():
    expected = Image.new("RGB", (10, 10), "white")
    backend = FakeBackend(graphics=expected)

    result = capture_window(7, backend)

    assert result is expected
    assert backend.capture_calls == 1


@pytest.mark.parametrize(
    ("backend", "message"),
    [
        (FakeBackend(valid=False), "已关闭"),
        (FakeBackend(minimized=True), "最小化"),
        (FakeBackend(graphics=None), "没有返回画面"),
    ],
)
def test_capture_reports_actionable_errors(backend, message):
    with pytest.raises(CaptureError, match=message):
        capture_window(7, backend)


def test_capture_hides_low_level_graphics_errors_from_user():
    backend = FakeBackend(error=OSError("native details"))

    with pytest.raises(CaptureError, match="Windows 图形捕获失败") as error:
        capture_window(7, backend)

    assert "native details" not in str(error.value)


def test_frame_to_image_converts_bgr_channels_to_rgb():
    class FakeFrame:
        frame_buffer = np.array([[[0, 0, 255], [255, 0, 0]]], dtype=np.uint8)

        def convert_to_bgr(self):
            return self

    result = frame_to_image(FakeFrame())

    assert result.mode == "RGB"
    assert result.size == (2, 1)
    assert result.getpixel((0, 0)) == (255, 0, 0)
    assert result.getpixel((1, 0)) == (0, 0, 255)
