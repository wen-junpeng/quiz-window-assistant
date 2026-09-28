from collections.abc import Callable
from pathlib import Path

from PIL import Image

from .runtime import prepare_qt_runtime

prepare_qt_runtime()

from PySide6.QtCore import QSettings, QThreadPool, QTimer, Qt  # noqa: E402
from PySide6.QtGui import QCloseEvent, QImage, QPixmap, QResizeEvent  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .api import ApiError, ApiSettings
from .windows import WindowInfo, list_selectable_windows
from .workers import CaptureWorker, SolveWorker


WindowProvider = Callable[[int | None], list[WindowInfo]]


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: QSettings | None = None,
        auto_start_preview: bool = True,
        window_provider: WindowProvider = list_selectable_windows,
        thread_pool: QThreadPool | None = None,
    ):
        super().__init__()
        if settings is None:
            settings_path = (
                Path(__file__).resolve().parents[2] / "config" / "settings.ini"
            )
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings = QSettings(str(settings_path), QSettings.IniFormat)

        self.settings = settings
        self.window_provider = window_provider
        self.pool = thread_pool or QThreadPool.globalInstance()
        self.selected_hwnd: int | None = None
        self.latest_frame: Image.Image | None = None
        self.capture_busy = False
        self.capture_token = 0
        self.active_solve_token: int | None = None
        self.solve_token = 0
        self._preview_pixmap: QPixmap | None = None

        self.build_ui()
        self.restore_non_secret_settings()

        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(500)
        self.preview_timer.timeout.connect(self.request_preview_capture)
        if auto_start_preview:
            self.preview_timer.start()
        self.refresh_windows()

    def build_ui(self) -> None:
        self.setWindowTitle("网页做题悬浮助手 Demo")
        self.resize(560, 800)
        self.setMinimumSize(400, 560)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.setCentralWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        target_row = QHBoxLayout()
        self.target_combo = QComboBox()
        self.target_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.target_combo.currentIndexChanged.connect(self.select_target)
        self.refresh_button = QPushButton("刷新窗口")
        self.refresh_button.clicked.connect(self.refresh_windows)
        self.topmost_checkbox = QCheckBox("置顶显示")
        self.topmost_checkbox.toggled.connect(self.set_topmost)
        target_row.addWidget(self.target_combo, 1)
        target_row.addWidget(self.refresh_button)
        target_row.addWidget(self.topmost_checkbox)
        layout.addLayout(target_row)

        self.preview_label = QLabel("请选择一个窗口")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(250)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setFrameShape(QFrame.StyledPanel)
        self.preview_label.setStyleSheet(
            "QLabel { background: #161a22; color: #c8d0df; "
            "border: 1px solid #3b4353; border-radius: 8px; }"
        )
        layout.addWidget(self.preview_label, 3)

        self.api_group = QGroupBox("API 设置")
        self.api_group.setCheckable(True)
        self.api_group.setChecked(True)
        api_group_layout = QVBoxLayout(self.api_group)
        self.api_content = QWidget()
        api_form = QFormLayout(self.api_content)
        api_form.setContentsMargins(0, 0, 0, 0)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://api.example.com/v1")
        api_form.addRow("API 地址", self.base_url_edit)

        key_row = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("仅保存在本次运行内存中")
        self.show_key_checkbox = QCheckBox("显示")
        self.show_key_checkbox.toggled.connect(self.toggle_key_visibility)
        key_row.addWidget(self.api_key_edit, 1)
        key_row.addWidget(self.show_key_checkbox)
        api_form.addRow("API Key", key_row)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("支持图片输入的模型名")
        api_form.addRow("模型", self.model_edit)
        api_group_layout.addWidget(self.api_content)
        self.api_group.toggled.connect(self.api_content.setVisible)
        layout.addWidget(self.api_group)

        layout.addWidget(QLabel("补充说明"))
        self.instruction_edit = QTextEdit()
        self.instruction_edit.setPlaceholderText(
            "例如：只给答案；详细讲解；重点看第 3 题"
        )
        self.instruction_edit.setMaximumHeight(86)
        layout.addWidget(self.instruction_edit)

        action_row = QHBoxLayout()
        self.solve_button = QPushButton("识别并解答")
        self.solve_button.setEnabled(False)
        self.solve_button.clicked.connect(self.start_solve)
        self.stop_button = QPushButton("停止请求")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.cancel_solve)
        self.clear_button = QPushButton("清空结果")
        self.clear_button.clicked.connect(self.clear_result)
        action_row.addWidget(self.solve_button, 1)
        action_row.addWidget(self.stop_button)
        action_row.addWidget(self.clear_button)
        layout.addLayout(action_row)

        layout.addWidget(QLabel("解题结果"))
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setMinimumHeight(150)
        self.output_edit.setPlaceholderText("识别结果会显示在这里")
        layout.addWidget(self.output_edit, 2)

        self.status_label = QLabel("只有点击“识别并解答”才会发送截图")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #57657a;")
        layout.addWidget(self.status_label)

        self.setStyleSheet(
            "QPushButton { padding: 6px 10px; }"
            "QLineEdit, QTextEdit, QComboBox { padding: 5px; }"
            "QGroupBox { font-weight: 600; margin-top: 8px; }"
        )

    def toggle_key_visibility(self, visible: bool) -> None:
        self.api_key_edit.setEchoMode(
            QLineEdit.Normal if visible else QLineEdit.Password
        )

    def set_topmost(self, enabled: bool) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, enabled)
        self.show()

    def save_non_secret_settings(self) -> None:
        self.settings.setValue("base_url", self.base_url_edit.text())
        self.settings.setValue("model", self.model_edit.text())
        self.settings.setValue("topmost", self.topmost_checkbox.isChecked())
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.sync()

    def restore_non_secret_settings(self) -> None:
        self.base_url_edit.setText(str(self.settings.value("base_url", "")))
        self.model_edit.setText(str(self.settings.value("model", "")))
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        topmost = self.settings.value("topmost", False, type=bool)
        self.topmost_checkbox.setChecked(topmost)

    def refresh_windows(self) -> None:
        current_hwnd = self.selected_hwnd
        try:
            windows = self.window_provider(int(self.winId()))
        except Exception:
            self.status_label.setText("读取窗口列表失败，请重试")
            return

        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem("请选择目标窗口", None)
        selected_index = 0
        for info in windows:
            self.target_combo.addItem(info.title, info.hwnd)
            if info.hwnd == current_hwnd:
                selected_index = self.target_combo.count() - 1
        self.target_combo.setCurrentIndex(selected_index)
        self.target_combo.blockSignals(False)
        if selected_index == 0:
            self.select_target(0)

    def select_target(self, index: int) -> None:
        self.capture_token += 1
        self.capture_busy = False
        self.selected_hwnd = self.target_combo.itemData(index)
        self.latest_frame = None
        self._preview_pixmap = None
        self.preview_label.clear()
        self.solve_button.setEnabled(False)
        if self.selected_hwnd is None:
            self.preview_label.setText("请选择一个窗口")
            self.status_label.setText("只有点击“识别并解答”才会发送截图")
            return
        self.preview_label.setText("正在读取目标窗口…")
        self.status_label.setText("正在建立本地预览…")
        self.request_preview_capture()

    def request_preview_capture(self) -> None:
        if self.capture_busy or self.selected_hwnd is None:
            return
        self.capture_busy = True
        self.capture_token += 1
        worker = CaptureWorker(self.capture_token, self.selected_hwnd)
        worker.signals.succeeded.connect(self.handle_capture_success)
        worker.signals.failed.connect(self.handle_capture_failure)
        self.pool.start(worker)

    def handle_capture_success(self, token: int, image: object) -> None:
        if token != self.capture_token or not isinstance(image, Image.Image):
            return
        self.capture_busy = False
        self.latest_frame = image
        self._preview_pixmap = self.image_to_pixmap(image)
        self.rescale_preview()
        self.solve_button.setEnabled(self.active_solve_token is None)
        self.status_label.setText("预览正常；只有点击解题才会发送截图")

    def handle_capture_failure(self, token: int, message: str) -> None:
        if token != self.capture_token:
            return
        self.capture_busy = False
        self.latest_frame = None
        self._preview_pixmap = None
        self.preview_label.clear()
        self.preview_label.setText(message)
        self.solve_button.setEnabled(False)
        self.status_label.setText(message)

    @staticmethod
    def image_to_pixmap(image: Image.Image) -> QPixmap:
        rgb = image.convert("RGB")
        data = rgb.tobytes("raw", "RGB")
        qimage = QImage(
            data,
            rgb.width,
            rgb.height,
            rgb.width * 3,
            QImage.Format_RGB888,
        ).copy()
        return QPixmap.fromImage(qimage)

    def rescale_preview(self) -> None:
        if self._preview_pixmap is None:
            return
        scaled = self._preview_pixmap.scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)

    def start_solve(self) -> None:
        if self.latest_frame is None:
            self.output_edit.setPlainText(
                "没有可用截图，请先选择并恢复目标窗口"
            )
            return
        settings = ApiSettings(
            self.base_url_edit.text(),
            self.api_key_edit.text(),
            self.model_edit.text(),
        )
        try:
            settings.validate()
        except ApiError as exc:
            self.output_edit.setPlainText(str(exc))
            return

        self.save_non_secret_settings()
        self.solve_token += 1
        self.active_solve_token = self.solve_token
        worker = SolveWorker(
            self.solve_token,
            settings,
            self.latest_frame.copy(),
            self.instruction_edit.toPlainText(),
        )
        worker.signals.succeeded.connect(self.handle_solve_success)
        worker.signals.failed.connect(self.handle_solve_failure)
        self.solve_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.output_edit.setPlainText("正在识别并解答…")
        self.status_label.setText("正在请求模型；可点击“停止请求”忽略结果")
        self.pool.start(worker)

    def cancel_solve(self) -> None:
        self.active_solve_token = None
        self.solve_button.setEnabled(self.latest_frame is not None)
        self.stop_button.setEnabled(False)
        self.status_label.setText("已停止等待；迟到结果将被忽略")

    def handle_solve_success(self, token: int, answer: object) -> None:
        if token != self.active_solve_token:
            return
        self.active_solve_token = None
        self.output_edit.setPlainText(str(answer))
        self.solve_button.setEnabled(self.latest_frame is not None)
        self.stop_button.setEnabled(False)
        self.status_label.setText("解题完成；预览继续在本机更新")

    def handle_solve_failure(self, token: int, message: str) -> None:
        if token != self.active_solve_token:
            return
        self.active_solve_token = None
        self.output_edit.setPlainText(message)
        self.solve_button.setEnabled(self.latest_frame is not None)
        self.stop_button.setEnabled(False)
        self.status_label.setText("请求失败；截图未保存到磁盘")

    def clear_result(self) -> None:
        self.output_edit.clear()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.rescale_preview()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.preview_timer.stop()
        self.capture_token += 1
        self.active_solve_token = None
        self.save_non_secret_settings()
        super().closeEvent(event)

