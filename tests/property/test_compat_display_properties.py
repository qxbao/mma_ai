"""Kiểm thử thuộc tính cho bất biến INV-004 của phép dò màn hình."""

from __future__ import annotations

import random

from mma_ai.compat.display import probe_display
from mma_ai.compat.platform_info import PlatformProfile


def _profile(kind: str) -> PlatformProfile:
    return PlatformProfile(
        kind=kind,  # type: ignore[arg-type]
        release="property-test",
        machine="x86_64",
        python_version=(3, 12, 0),
        is_wsl=kind == "wsl2",
        tested=True,
    )


def test_inv_004_probe_always_returns_a_reason_for_random_platform_inputs() -> None:
    rng = random.Random(20261012)
    kinds = ("linux", "wsl2", "windows", "macos")

    for _ in range(300):
        kind = rng.choice(kinds)
        environ = {
            key: rng.choice(("", ":99", "socket", "0", "value"))
            for key in ("DISPLAY", "WAYLAND_DISPLAY", "MMA_AI_FORCE_NO_DISPLAY")
            if rng.choice((True, False))
        }
        result = probe_display(_profile(kind), environ=environ, glfw_init=lambda: False)

        assert result.reason.strip()
        if environ.get("MMA_AI_FORCE_NO_DISPLAY", "") not in ("", "0"):
            assert not result.available
            assert "MMA_AI_FORCE_NO_DISPLAY" in result.reason


def test_inv_004_absent_linux_display_never_tries_glfw() -> None:
    rng = random.Random(20261013)
    for _ in range(100):
        kind = rng.choice(("linux", "wsl2"))
        result = probe_display(_profile(kind), environ={}, glfw_init=lambda: True)

        assert not result.available
        assert "DISPLAY" in result.reason
        assert "WAYLAND_DISPLAY" in result.reason
        assert "--headless" in result.reason
