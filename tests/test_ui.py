from PIL import Image
from PySide6.QtCore import QSettings, Qt

from quiz_assistant.ui import MainWindow
from quiz_assistant.windows import WindowInfo


class FakePool:
    def __init__(self):
        self.started = []

    def start(self, worker):
        self.started.append(worker)


def make_window(qtbot, tmp_path, *, window_provider=None, pool=None):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    window = MainWindow(
        settings=settings,
        auto_start_preview=False,
        window_provider=window_provider or (lambda own_hwnd: []),
        thread_pool=pool or FakePool(),
    )
    qtbot.addWidget(window)
    window.show()
    return window, settings


def test_topmost_checkbox_updates_window_flag(qtbot, tmp_path):
    window, _ = make_window(qtbot, tmp_path)

    window.topmost_checkbox.setChecked(True)

    assert window.windowFlags() & Qt.WindowStaysOnTopHint


def test_api_key_is_not_written_to_settings(qtbot, tmp_path):
    window, settings = make_window(qtbot, tmp_path)
    window.api_key_edit.setText("do-not-save")
    window.base_url_edit.setText("https://example.test/v1")
    window.model_edit.setText("vision")

    window.save_non_secret_settings()

    saved = [(key, settings.value(key)) for key in settings.allKeys()]
    assert settings.value("api_key") is None
    assert "do-not-save" not in repr(saved)


def test_refresh_windows_populates_handles_and_selection(qtbot, tmp_path):
    own_handles = []

    def provider(own_hwnd):
        own_handles.append(own_hwnd)
        return [
            WindowInfo(101, "Browser - Questions"),
            WindowInfo(202, "Notepad"),
        ]

    window, _ = make_window(qtbot, tmp_path, window_provider=provider)

    assert own_handles == [int(window.winId())]
    assert window.target_combo.count() == 3
    window.target_combo.setCurrentIndex(1)
    assert window.selected_hwnd == 101
    assert window.preview_label.text() == "正在读取目标窗口…"


def test_preview_timer_does_not_start_second_capture_while_busy(qtbot, tmp_path):
    pool = FakePool()
    window, _ = make_window(qtbot, tmp_path, pool=pool)
    window.selected_hwnd = 5
    window.capture_busy = True
    before = window.capture_token

    window.request_preview_capture()

    assert window.capture_token == before
    assert pool.started == []


def test_capture_success_enables_solving_and_keeps_latest_frame(qtbot, tmp_path):
    window, _ = make_window(qtbot, tmp_path)
    image = Image.new("RGB", (40, 20), "white")
    window.capture_token = 3

    window.handle_capture_success(3, image)

    assert window.latest_frame is image
    assert window.solve_button.isEnabled()
    assert "只有点击解题" in window.status_label.text()


def test_cancelled_request_cannot_overwrite_output(qtbot, tmp_path):
    window, _ = make_window(qtbot, tmp_path)
    window.latest_frame = Image.new("RGB", (4, 4), "white")
    window.active_solve_token = 21

    window.cancel_solve()
    window.handle_solve_success(21, "迟到答案")

    assert "迟到答案" not in window.output_edit.toPlainText()
    assert "迟到结果将被忽略" in window.status_label.text()
