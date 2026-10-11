"""Trace: API-PLT-0003 / API-PLT-0010 / INV-004.

Cung cấp phép dò màn hình (display probe) dùng chung cho các hệ điều hành.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from mma_ai.compat.platform_info import PlatformProfile, detect_platform

_FORCE_NO_DISPLAY = "MMA_AI_FORCE_NO_DISPLAY"
_AVAILABLE_REASON = "Màn hình hiển thị khả dụng (display available)."


@dataclass(frozen=True)
class DisplayProbe:
    """Kết quả bất biến của phép dò màn hình."""

    available: bool
    reason: str


def _default_glfw_init() -> bool:
    """Khởi tạo GLFW và xác nhận màn hình chính bằng cách nhập lười."""
    import glfw

    if not glfw.init():
        return False
    try:
        return glfw.get_primary_monitor() is not None
    finally:
        glfw.terminate()


def _linux_failure_reason(
    display: str | None, wayland_display: str | None, detail: str | None
) -> str:
    if not display and not wayland_display:
        reason = (
            "Không phát hiện màn hình hiển thị: cả hai biến môi trường DISPLAY và WAYLAND_DISPLAY "
            "đều chưa được thiết lập. Vui lòng kiểm tra hoặc dùng chế độ không màn hình "
            "(--headless)."
        )
    else:
        env_parts: list[str] = []
        if display is not None:
            env_parts.append(f"DISPLAY='{display}'")
        if wayland_display is not None:
            env_parts.append(f"WAYLAND_DISPLAY='{wayland_display}'")
        env_str = ", ".join(env_parts)
        reason = (
            f"Không thể khởi tạo hoặc kết nối tới màn hình hiển thị ({env_str}). "
            "Màn hình có thể bị hỏng, máy chủ X11/Wayland không phản hồi hoặc thiếu quyền. "
            "Vui lòng kiểm tra lại cấu hình hoặc sử dụng chế độ không màn hình (--headless)."
        )
    if detail:
        reason = f"{reason} [Chi tiết: {detail}]"
    return reason


def _failure_reason(
    profile: PlatformProfile,
    environ: Mapping[str, str],
    detail: str | None = None,
) -> str:
    if profile.kind in ("linux", "wsl2"):
        return _linux_failure_reason(
            environ.get("DISPLAY"), environ.get("WAYLAND_DISPLAY"), detail
        )
    reason = "Không thể khởi tạo màn hình hiển thị hoặc không tìm thấy màn hình chính. "
    reason += "Vui lòng kiểm tra cấu hình hoặc dùng chế độ không màn hình (--headless)."
    if detail:
        reason = f"{reason} [Chi tiết: {detail}]"
    return reason


def probe_display(
    profile: PlatformProfile | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    glfw_init: Callable[[], bool] | None = None,
) -> DisplayProbe:
    """Dò màn hình theo hồ sơ nền tảng và trả lý do bằng tiếng Việt."""
    selected_profile = detect_platform() if profile is None else profile
    selected_environ = os.environ if environ is None else environ
    forced = selected_environ.get(_FORCE_NO_DISPLAY, "")
    if forced not in ("", "0"):
        return DisplayProbe(
            False,
            f"Biến môi trường {_FORCE_NO_DISPLAY} đang ép chế độ không màn hình; "
            "dùng --headless hoặc bỏ biến này để dò lại.",
        )

    display = selected_environ.get("DISPLAY")
    wayland_display = selected_environ.get("WAYLAND_DISPLAY")
    if selected_profile.kind in ("linux", "wsl2") and not display and not wayland_display:
        return DisplayProbe(
            False,
            _linux_failure_reason(display, wayland_display, None),
        )

    initializer = _default_glfw_init if glfw_init is None else glfw_init
    try:
        available = bool(initializer())
    except Exception as exc:
        return DisplayProbe(False, _failure_reason(selected_profile, selected_environ, str(exc)))
    if available:
        return DisplayProbe(True, _AVAILABLE_REASON)
    return DisplayProbe(False, _failure_reason(selected_profile, selected_environ))


def viewer_launch_hint(
    error: str | None = None,
    profile: PlatformProfile | None = None,
    *,
    executable: str | None = None,
) -> str | None:
    """Gợi ý lệnh chạy viewer bằng mjpython khi cần trên macOS."""
    selected_profile = detect_platform() if profile is None else profile
    if selected_profile.kind != "macos":
        return None
    current_executable = sys.executable if executable is None else executable
    is_mjpython = Path(current_executable).name.lower() == "mjpython"
    error_mentions_mjpython = error is not None and "mjpython" in error.lower()
    if is_mjpython and not error_mentions_mjpython:
        return None
    return "Trên macOS, hãy chạy viewer bằng `mjpython -m <mô-đun>`."


__all__ = ["DisplayProbe", "probe_display", "viewer_launch_hint"]
