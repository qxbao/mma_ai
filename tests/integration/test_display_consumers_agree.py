from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal

import pytest

from mma_ai.compat import display as compat_display
from mma_ai.compat.platform_info import PlatformProfile
from mma_ai.learning import benchmark
from mma_ai.monitoring import viewer3d
from mma_ai.visualization import display as visualization_display


def _profile(kind: Literal["windows", "linux", "wsl2", "macos"]) -> PlatformProfile:
    return PlatformProfile(
        kind=kind,
        release="test",
        machine="x86_64",
        python_version=(3, 12, 0),
        is_wsl=kind == "wsl2",
        tested=True,
    )


@pytest.mark.parametrize("kind", ["windows", "linux", "wsl2", "macos"])  # type: ignore[untyped-decorator]
def test_fr_006_fr_023_inv_001_ac_3_three_consumers_agree_for_each_profile(
    kind: Literal["windows", "linux", "wsl2", "macos"],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile(kind)
    environ: Mapping[str, str] = {"DISPLAY": ":test", "WAYLAND_DISPLAY": "wayland-test"}
    monkeypatch.setattr(compat_display, "detect_platform", lambda: profile)
    monkeypatch.setattr(compat_display, "_default_glfw_init", lambda: True)
    monkeypatch.setattr(benchmark, "detect_platform", lambda: profile)
    monkeypatch.setattr(os, "environ", dict(environ))

    first = visualization_display.display_available().available
    second = viewer3d.View3D.has_display()
    third = benchmark.evaluate_view3d_status()

    assert first is True
    assert second is True
    assert third == {
        "measured": False,
        "reason": "chế độ hiển thị 3D tắt mặc định trong lượt đo benchmark",
    }


def test_fr_006_inv_001_ac_3_view3d_linux_shortcut_does_not_import_glfw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile("linux")
    monkeypatch.setattr(compat_display, "detect_platform", lambda: profile)
    monkeypatch.setattr(os, "environ", {})

    def unexpected_glfw() -> bool:
        raise AssertionError("Không được nạp GLFW khi thiếu DISPLAY trên Linux.")

    monkeypatch.setattr(compat_display, "_default_glfw_init", unexpected_glfw)

    assert viewer3d.View3D.has_display() is False
