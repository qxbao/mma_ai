"""Quy tắc đường dẫn độc lập với hệ điều hành."""

from __future__ import annotations

import ntpath
import posixpath
from pathlib import Path, PurePosixPath, PureWindowsPath

from .platform_info import PlatformProfile, detect_platform


def is_absolute_any_os(value: str) -> bool:
    """Nhận diện đường dẫn tuyệt đối của POSIX hoặc Windows."""
    return PurePosixPath(value).is_absolute() or bool(
        PureWindowsPath(value).drive or PureWindowsPath(value).root
    )


def to_record_path(path: str | Path, base: str | Path | None = None) -> str:
    """Chuyển đường dẫn thành dạng tương đối, dùng dấu gạch chéo xuôi."""
    raw = str(path)
    windows_path = PureWindowsPath(raw)
    if windows_path.drive or (windows_path.root and not raw.startswith("/")):
        if not is_absolute_any_os(raw):
            return posixpath.normpath(raw.replace("\\", "/"))
        if base is None:
            parts = windows_path.parts[1:] if windows_path.drive else windows_path.parts
            return "/".join(part for part in parts if part not in ("\\", "/"))
        windows_base = PureWindowsPath(str(base))
        if windows_base.drive or windows_base.root:
            relative_path = str(ntpath.relpath(str(windows_path), str(windows_base)))
            return relative_path.replace("\\", "/")
        parts = windows_path.parts[1:] if windows_path.drive else windows_path.parts
        return "/".join(part for part in parts if part not in ("\\", "/"))

    posix_path = PurePosixPath(raw)
    if posix_path.is_absolute():
        if base is not None:
            windows_base = PureWindowsPath(str(base))
            if windows_base.drive or (windows_base.root and not str(base).startswith("/")):
                return "/".join(posix_path.parts[1:])
        base_path = Path.cwd() if base is None else Path(base)
        relative = posixpath.relpath(posix_path.as_posix(), str(base_path))
        return relative.replace("\\", "/")
    return posixpath.normpath(raw.replace("\\", "/"))


def venv_python(venv_dir: str | Path, profile: PlatformProfile | None = None) -> Path:
    """Trả về đường dẫn trình thông dịch Python trong môi trường ảo."""
    selected = profile if profile is not None else detect_platform()
    root = Path(venv_dir)
    if selected.kind == "windows":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"
