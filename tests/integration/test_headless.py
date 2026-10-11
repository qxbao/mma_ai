"""Kiểm thử môi trường (environment) chạy không giao diện (headless)."""

from __future__ import annotations

import os
import subprocess
import sys

_HEADLESS_SCRIPT = """
import sys

import gymnasium as gym

from mma_ai.environment import register_envs

register_envs()
env = gym.make("MmaElbowReach-v0")
observation, _ = env.reset(seed=20261009)
for _ in range(30):
    observation, _, terminated, truncated, _ = env.step(env.action_space.sample())
    if terminated or truncated:
        observation, _ = env.reset(seed=20261009)
assert "mujoco.viewer" not in sys.modules
print(observation.shape)
env.close()
"""


def _run_headless_process() -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    return subprocess.run(
        [sys.executable, "-c", _HEADLESS_SCRIPT],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def test_ac_2_runs_without_display() -> None:
    """AC-2, NFR-HEADLESS-001: tiến trình mới tạo và bước môi trường không hiển thị."""
    result = _run_headless_process()

    assert result.returncode == 0, result.stderr


def test_nfr_headless_no_viewer_or_pixel_import() -> None:
    """NFR-HEADLESS-001: rollout không nạp viewer/glfw và không tạo observation ảnh."""
    result = _run_headless_process()

    assert result.returncode == 0, result.stderr
    assert "display" not in result.stderr.lower()
    assert "pixel" not in result.stdout.lower()
    assert "(14,)" in result.stdout

