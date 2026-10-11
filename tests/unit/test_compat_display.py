"""Kiểm thử đơn vị cho phép dò màn hình tương thích đa nền tảng."""

from __future__ import annotations

from mma_ai.compat.display import DisplayProbe, probe_display, viewer_launch_hint
from mma_ai.compat.platform_info import PlatformProfile


def _profile(kind: str) -> PlatformProfile:
    return PlatformProfile(
        kind=kind,  # type: ignore[arg-type]
        release="test",
        machine="x86_64",
        python_version=(3, 12, 0),
        is_wsl=kind == "wsl2",
        tested=True,
    )


def test_api_plt_0003_linux_unset_env_unavailable_exact_message() -> None:
    result = probe_display(_profile("linux"), environ={})

    assert result == DisplayProbe(
        available=False,
        reason=(
            "Không phát hiện màn hình hiển thị: cả hai biến môi trường DISPLAY và WAYLAND_DISPLAY "
            "đều chưa được thiết lập. Vui lòng kiểm tra hoặc dùng chế độ không màn hình "
            "(--headless)."
        ),
    )


def test_api_plt_0003_linux_bogus_display_unavailable() -> None:
    called = False

    def init() -> bool:
        nonlocal called
        called = True
        return False

    result = probe_display(_profile("linux"), environ={"DISPLAY": ":99"}, glfw_init=init)

    assert result.available is False
    assert "DISPLAY=':99'" in result.reason
    assert "--headless" in result.reason
    assert called


def test_api_plt_0003_windows_ignores_display_env_vars() -> None:
    result = probe_display(
        _profile("windows"),
        environ={"DISPLAY": ":99", "WAYLAND_DISPLAY": "broken"},
        glfw_init=lambda: True,
    )

    assert result == DisplayProbe(True, "Màn hình hiển thị khả dụng (display available).")


def test_api_plt_0003_macos_ignores_display_env_vars() -> None:
    result = probe_display(
        _profile("macos"),
        environ={"DISPLAY": ":99", "WAYLAND_DISPLAY": "broken"},
        glfw_init=lambda: True,
    )

    assert result == DisplayProbe(True, "Màn hình hiển thị khả dụng (display available).")


def test_api_plt_0003_windows_no_primary_monitor_unavailable() -> None:
    result = probe_display(_profile("windows"), environ={}, glfw_init=lambda: False)

    assert not result.available
    assert "--headless" in result.reason


def test_api_plt_0003_glfw_exception_is_unavailable_with_detail() -> None:
    def init() -> bool:
        raise RuntimeError("GLFW backend failed")

    result = probe_display(_profile("macos"), environ={}, glfw_init=init)

    assert not result.available
    assert "GLFW backend failed" in result.reason
    assert "--headless" in result.reason


def test_api_plt_0003_force_no_display_env() -> None:
    result = probe_display(
        _profile("windows"),
        environ={"MMA_AI_FORCE_NO_DISPLAY": "1"},
        glfw_init=lambda: True,
    )

    assert not result.available
    assert "MMA_AI_FORCE_NO_DISPLAY" in result.reason
    assert "--headless" in result.reason


def test_api_plt_0010_viewer_launch_hint_macos_only() -> None:
    hint = viewer_launch_hint(profile=_profile("macos"), executable="python")

    assert hint is not None
    assert "mjpython -m <mô-đun>" in hint
    assert viewer_launch_hint(profile=_profile("macos"), executable="mjpython") is None
    assert viewer_launch_hint(profile=_profile("linux"), executable="python") is None


def test_api_plt_0010_viewer_launch_hint_when_error_mentions_mjpython() -> None:
    hint = viewer_launch_hint(
        error="Use mjpython to launch the viewer",
        profile=_profile("macos"),
        executable="mjpython",
    )

    assert hint is not None
    assert "mjpython -m <mô-đun>" in hint


def test_nfr_display_001_probe_returns_within_5s_real() -> None:
    import time

    started = time.monotonic()
    result = probe_display(_profile("linux"), environ={})

    assert time.monotonic() - started <= 5.0
    assert not result.available
