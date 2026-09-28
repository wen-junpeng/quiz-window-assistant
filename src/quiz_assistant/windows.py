from dataclasses import dataclass

import win32gui


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str


def filter_window_records(
    records: list[tuple[int, str, bool]], own_hwnd: int | None = None
) -> list[WindowInfo]:
    items = [
        WindowInfo(hwnd=hwnd, title=title.strip())
        for hwnd, title, visible in records
        if visible and title.strip() and hwnd != own_hwnd
    ]
    return sorted(items, key=lambda item: item.title.casefold())


def list_selectable_windows(own_hwnd: int | None = None) -> list[WindowInfo]:
    records: list[tuple[int, str, bool]] = []

    def collect(hwnd: int, _: object) -> bool:
        records.append(
            (
                hwnd,
                win32gui.GetWindowText(hwnd),
                bool(win32gui.IsWindowVisible(hwnd)),
            )
        )
        return True

    win32gui.EnumWindows(collect, None)
    return filter_window_records(records, own_hwnd)


def window_is_capturable(hwnd: int) -> tuple[bool, str]:
    if not win32gui.IsWindow(hwnd):
        return False, "目标窗口已关闭，请重新选择"
    if win32gui.IsIconic(hwnd):
        return False, "目标窗口已最小化，请先恢复窗口"
    return True, ""

