from collections.abc import Callable

from PIL import Image

from .runtime import prepare_qt_runtime

prepare_qt_runtime()

from PySide6.QtCore import QObject, QRunnable, Signal, Slot  # noqa: E402

from .api import ApiSettings, solve_question
from .capture import capture_window
from .imaging import prepare_image_data_url


class WorkerSignals(QObject):
    succeeded = Signal(int, object)
    failed = Signal(int, str)


class CaptureWorker(QRunnable):
    def __init__(
        self,
        token: int,
        hwnd: int,
        capture: Callable[[int], Image.Image] = capture_window,
    ):
        super().__init__()
        self.token = token
        self.hwnd = hwnd
        self.capture = capture
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            image = self.capture(self.hwnd)
        except Exception as exc:
            self.signals.failed.emit(self.token, str(exc))
            return
        self.signals.succeeded.emit(self.token, image)


class SolveWorker(QRunnable):
    def __init__(
        self,
        token: int,
        settings: ApiSettings,
        image: Image.Image,
        instruction: str,
        prepare: Callable[[Image.Image], str] = prepare_image_data_url,
        solve: Callable[[ApiSettings, str, str], str] = solve_question,
    ):
        super().__init__()
        self.token = token
        self.settings = settings
        self.image = image
        self.instruction = instruction
        self.prepare = prepare
        self.solve = solve
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            data_url = self.prepare(self.image)
            answer = self.solve(self.settings, data_url, self.instruction)
        except Exception as exc:
            self.signals.failed.emit(self.token, str(exc))
            return
        self.signals.succeeded.emit(self.token, answer)

