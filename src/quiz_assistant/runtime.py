import ctypes
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


_ICU_HANDLE: Any = None


def prepare_qt_runtime(
    *,
    platform_name: str | None = None,
    system_root: str | Path | None = None,
    loader: Callable[[str], Any] | None = None,
) -> None:
    """Prefer Windows' ICU before Qt can load an incompatible Conda copy."""
    if (platform_name or sys.platform) != "win32":
        return

    root = Path(system_root or os.environ.get("SystemRoot", r"C:\Windows"))
    icu_path = root / "System32" / "icuuc.dll"
    if not icu_path.is_file():
        return

    global _ICU_HANDLE
    _ICU_HANDLE = (loader or ctypes.WinDLL)(str(icu_path))

