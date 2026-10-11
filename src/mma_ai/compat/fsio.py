"""Trace: API-PLT-0005 / INV-003 / INV-005 / NFR-IO-001 / NFR-ENC-001 / AC-4."""

from __future__ import annotations

import math
import os
import tempfile
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from mma_ai.compat.capabilities import long_paths_enabled
from mma_ai.compat.platform_info import PlatformProfile, detect_platform

_DEFAULT_WAITS = (0.05, 0.10, 0.20, 0.20)
_LONG_PATH_LIMIT = 260


def _retry_delays(kind: str, attempts: int, waits: Sequence[float]) -> tuple[float, ...]:
    if attempts < 1:
        raise ValueError("Số lần thử phải lớn hơn hoặc bằng 1.")
    if any(not math.isfinite(delay) or delay < 0 for delay in waits):
        raise ValueError("Thời gian chờ phải là số hữu hạn không âm.")
    if kind != "windows":
        return ()
    return tuple(waits[: attempts - 1])


def _error_message(destination: Path, cause: Exception, long_path_hint: bool) -> str:
    message = f"Không ghi nguyên tử được tệp đích {destination}: {cause}"
    if long_path_hint:
        message += (
            f" (đường dẫn dài {len(str(destination))} ký tự; hãy bật hỗ trợ đường dẫn dài "
            "trên Windows hoặc rút ngắn thư mục gốc)."
        )
    return message


class AtomicWriteError(OSError):
    """Lỗi ghi nguyên tử có đường dẫn đích và nguyên nhân gốc."""

    def __init__(
        self,
        destination: Path,
        cause: Exception,
        message: str,
    ) -> None:
        self.destination = destination
        self.cause = cause
        super().__init__(message)


def _atomic_error(
    destination: Path,
    cause: Exception,
    profile: PlatformProfile,
) -> AtomicWriteError:
    long_path_hint = (
        profile.kind == "windows"
        and len(str(destination)) >= _LONG_PATH_LIMIT
        and not long_paths_enabled(profile).available
    )
    return AtomicWriteError(
        destination,
        cause,
        _error_message(destination, cause, long_path_hint),
    )


def _remove_temporary(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def replace_atomic(
    src: str | os.PathLike[str],
    dst: str | os.PathLike[str],
    *,
    attempts: int = 5,
    waits: Sequence[float] = _DEFAULT_WAITS,
    sleep: Callable[[float], None] = time.sleep,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None] = os.replace,
    profile: PlatformProfile | None = None,
) -> None:
    """Thay tệp đích bằng nguồn; chỉ Windows thử lại khi đích đang bị khóa."""
    source = Path(src)
    destination = Path(dst)
    selected = profile if profile is not None else detect_platform()
    delays = _retry_delays(selected.kind, attempts, waits)
    for attempt in range(len(delays) + 1):
        try:
            replace(source, destination)
            return
        except PermissionError as error:
            if selected.kind == "windows" and attempt < len(delays):
                try:
                    sleep(delays[attempt])
                except Exception as sleep_error:
                    _remove_temporary(source)
                    raise _atomic_error(destination, sleep_error, selected) from sleep_error
                continue
            _remove_temporary(source)
            raise _atomic_error(destination, error, selected) from error
        except Exception as error:
            _remove_temporary(source)
            raise _atomic_error(destination, error, selected) from error


def _write_temporary(
    destination: Path,
    mode: str,
    writer: Callable[[Any], None],
    profile: PlatformProfile,
) -> None:
    temporary: Path | None = None
    descriptor: int | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(temporary_name)
        if mode == "wb":
            stream = os.fdopen(descriptor, mode)
        else:
            stream = os.fdopen(descriptor, mode, encoding="utf-8", newline="\n")
        descriptor = None
        with stream:
            writer(stream)
            stream.flush()
            os.fsync(stream.fileno())
        replace_atomic(temporary, destination, profile=profile)
    except AtomicWriteError:
        raise
    except Exception as error:
        raise _atomic_error(destination, error, profile) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            _remove_temporary(temporary)


def write_text_atomic(
    dst: str | os.PathLike[str],
    text: str,
    *,
    profile: PlatformProfile | None = None,
) -> None:
    """Ghi văn bản UTF-8 không BOM với xuống dòng LF rồi thay tệp nguyên tử."""
    destination = Path(dst)
    selected = profile if profile is not None else detect_platform()
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    def write(stream: Any) -> None:
        stream.write(normalized)

    _write_temporary(destination, "w", write, selected)


def write_bytes_atomic(
    dst: str | os.PathLike[str],
    data: bytes,
    *,
    profile: PlatformProfile | None = None,
) -> None:
    """Ghi byte rồi thay tệp đích nguyên tử."""
    destination = Path(dst)
    selected = profile if profile is not None else detect_platform()

    def write(stream: Any) -> None:
        stream.write(data)

    _write_temporary(destination, "wb", write, selected)


__all__ = [
    "AtomicWriteError",
    "replace_atomic",
    "write_bytes_atomic",
    "write_text_atomic",
]
