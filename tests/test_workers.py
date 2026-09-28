from PIL import Image

from quiz_assistant.api import ApiSettings
from quiz_assistant.workers import CaptureWorker, SolveWorker


def test_capture_worker_emits_image_with_token(qtbot):
    image = Image.new("RGB", (4, 4), "white")
    worker = CaptureWorker(12, 99, capture=lambda hwnd: image)

    with qtbot.waitSignal(worker.signals.succeeded, timeout=1000) as signal:
        worker.run()

    assert signal.args == [12, image]


def test_capture_worker_emits_user_facing_error(qtbot):
    def fail(hwnd):
        raise RuntimeError("capture failed")

    worker = CaptureWorker(13, 99, capture=fail)

    with qtbot.waitSignal(worker.signals.failed, timeout=1000) as signal:
        worker.run()

    assert signal.args == [13, "capture failed"]


def test_solve_worker_prepares_image_and_emits_answer(qtbot):
    image = Image.new("RGB", (4, 4), "white")
    settings = ApiSettings("https://example.test/v1", "secret", "vision")
    received = []

    def solve(config, data_url, instruction):
        received.append((config, data_url, instruction))
        return "答案：A"

    worker = SolveWorker(
        8,
        settings,
        image,
        "只给答案",
        prepare=lambda value: "data:image/jpeg;base64,abc",
        solve=solve,
    )

    with qtbot.waitSignal(worker.signals.succeeded, timeout=1000) as signal:
        worker.run()

    assert signal.args == [8, "答案：A"]
    assert received == [
        (settings, "data:image/jpeg;base64,abc", "只给答案")
    ]

