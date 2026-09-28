import ctypes
import sys

from .runtime import prepare_qt_runtime

prepare_qt_runtime()

from PySide6.QtWidgets import QApplication  # noqa: E402

from .ui import MainWindow


def main() -> int:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "CodexDemo.QuizWindowAssistant.0.1"
    )
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("网页做题悬浮助手")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
