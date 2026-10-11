"""Trace: API-PLT-0004 / INV-004 / AC-4 / AC-6."""

from __future__ import annotations

import codecs
import importlib
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from mma_ai.compat.memory import peak_ram_mb
from mma_ai.compat.platform_info import PlatformProfile, detect_platform

_LONG_PATHS_KEY = r"SYSTEM\CurrentControlSet\Control\FileSystem"
_LONG_PATHS_VALUE = "LongPathsEnabled"


@dataclass(frozen=True)
class Capability:
    """Kết quả phép dò năng lực, với lý do bắt buộc khi không khả dụng."""

    available: bool
    reason: str | None

    def __post_init__(self) -> None:
        if self.available != (self.reason is None):
            raise ValueError("Trạng thái năng lực và lý do không nhất quán")
        if self.reason is not None and not self.reason.strip():
            raise ValueError("Lý do năng lực không khả dụng không được để trống")


def _unavailable(reason: str) -> Capability:
    return Capability(False, reason)


def symlink_supported(probe_dir: Path | str | None = None) -> Capability:
    """Tạo và dọn symlink thật để xác định hệ thống tệp có hỗ trợ hay không."""
    try:
        with tempfile.TemporaryDirectory(dir=probe_dir) as temporary:
            root = Path(temporary)
            target = root / "target"
            link = root / "link"
            target.write_text("probe", encoding="utf-8")
            link.symlink_to(target)
            if not link.is_symlink() or link.read_text(encoding="utf-8") != "probe":
                return _unavailable("Không xác nhận được hỗ trợ symlink trên hệ thống này.")
        return Capability(True, None)
    except OSError as error:
        return _unavailable(f"Không hỗ trợ symlink: {error}")
    except Exception as error:
        return _unavailable(f"Không xác định được hỗ trợ symlink: {error}")


def _read_long_paths_registry() -> int | None:
    winreg: Any = importlib.import_module("winreg")

    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _LONG_PATHS_KEY) as key:
        value, _ = winreg.QueryValueEx(key, _LONG_PATHS_VALUE)
        return int(value)


def long_paths_enabled(
    profile: PlatformProfile | None = None,
    *,
    registry_reader: Callable[[str, str], int | None] | None = None,
) -> Capability:
    """Đọc cờ đường dẫn dài trên Windows; hệ điều hành khác không cần cờ này."""
    selected = profile if profile is not None else detect_platform()
    if selected.kind != "windows":
        return Capability(True, None)
    try:
        value = (
            registry_reader(_LONG_PATHS_KEY, _LONG_PATHS_VALUE)
            if registry_reader is not None
            else _read_long_paths_registry()
        )
        if value == 1:
            return Capability(True, None)
        if value == 0:
            return _unavailable("Windows chưa bật hỗ trợ đường dẫn dài.")
        return _unavailable("Không xác định được trạng thái đường dẫn dài của Windows.")
    except Exception as error:
        return _unavailable(f"Không đọc được cài đặt đường dẫn dài của Windows: {error}")


def ram_probe(
    profile: PlatformProfile | None = None,
    *,
    peak_ram_source: Callable[[], float | None] | None = None,
) -> Capability:
    """Báo khả dụng khi phép đo RAM đỉnh trả về giá trị hữu hạn."""
    selected = profile if profile is not None else detect_platform()
    try:
        value = peak_ram_source() if peak_ram_source is not None else peak_ram_mb(selected)
        if value is None:
            return _unavailable("Không đo được RAM đỉnh trên hệ thống này.")
        if value < 0 or value != value or value in (float("inf"), float("-inf")):
            return _unavailable("Giá trị đo RAM đỉnh không hợp lệ.")
        return Capability(True, None)
    except Exception as error:
        return _unavailable(f"Không đo được RAM đỉnh: {error}")


def utf8_stdio_ok() -> Capability:
    """Kiểm tra đầu ra chuẩn và lỗi có thể mã hóa văn bản UTF-8."""
    try:
        encodings = (sys.stdout.encoding, sys.stderr.encoding)
        if all(encoding and codecs.lookup(encoding).name == "utf-8" for encoding in encodings):
            return Capability(True, None)
        return _unavailable("Đầu ra chuẩn hoặc lỗi chưa dùng mã hóa UTF-8.")
    except Exception as error:
        return _unavailable(f"Không xác định được mã hóa đầu ra UTF-8: {error}")


__all__ = [
    "Capability",
    "long_paths_enabled",
    "ram_probe",
    "symlink_supported",
    "utf8_stdio_ok",
]
