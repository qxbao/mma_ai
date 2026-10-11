"""Trace: API-PLT-0002 / INV-002 / INV-007.

Đo và chuẩn hoá RAM đỉnh theo đơn vị MiB.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any, cast

from mma_ai.compat.platform_info import PlatformProfile, detect_platform

_BYTES_PER_MIB = 1024 * 1024


def ram_mib_from_raw(raw: float, kind: str) -> float:
    """Quy đổi số đo RAM gốc của hệ điều hành sang MiB."""
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"Giá trị RAM không hợp lệ: {raw!r}") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"Giá trị RAM không hợp lệ: {raw!r}")
    if kind in {"linux", "wsl2"}:
        return value / 1024.0
    if kind in {"macos", "windows"}:
        return value / _BYTES_PER_MIB
    raise ValueError(f"Hệ điều hành không hợp lệ để quy đổi RAM: {kind!r}")


def _resource_peak_raw() -> float:
    import resource

    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _windows_peak_raw() -> float:
    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    windows_ctypes = cast(Any, ctypes)
    kernel32 = windows_ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = windows_ctypes.WinDLL("psapi", use_last_error=True)
    get_process = kernel32.GetCurrentProcess
    get_process.restype = wintypes.HANDLE
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    get_memory = psapi.GetProcessMemoryInfo
    get_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
    get_memory.restype = wintypes.BOOL
    if not get_memory(get_process(), ctypes.byref(counters), counters.cb):
        raise OSError(windows_ctypes.get_last_error(), "Không đọc được bộ nhớ tiến trình")
    return float(counters.PeakWorkingSetSize)


def peak_ram_mb(
    profile: PlatformProfile | None = None,
    *,
    linux_source: Callable[[], float] | None = None,
    macos_source: Callable[[], float] | None = None,
    windows_source: Callable[[], float] | None = None,
) -> float | None:
    """Đọc RAM đỉnh; trả về None khi hệ điều hành không đo được."""
    selected = profile if profile is not None else detect_platform()
    source = {
        "linux": linux_source or _resource_peak_raw,
        "wsl2": linux_source or _resource_peak_raw,
        "macos": macos_source or _resource_peak_raw,
        "windows": windows_source or _windows_peak_raw,
    }.get(selected.kind)
    if source is None:
        return None
    try:
        return ram_mib_from_raw(source(), selected.kind)
    except Exception:
        return None
