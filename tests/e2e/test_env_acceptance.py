"""Kiểm thử đầu-cuối cho môi trường khuỷu tay."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

PROJECT_ROOT = Path(__file__).parents[2]


def _run_entrypoint(script: str, *, timeout: int = 180) -> dict[str, Any]:
    """Chạy entrypoint thật trong tiến trình mới và trả payload JSON."""
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return cast(dict[str, Any], json.loads(completed.stdout))


def test_ac_1_six_muscles_unit_box() -> None:
    """AC-1: entrypoint Gymnasium thật phải tạo được môi trường."""
    result = _run_entrypoint(
        """
import json
import gymnasium
from mma_ai.environment import register_envs
register_envs()
env = gymnasium.make("MmaElbowReach-v0")
_, info = env.reset(seed=41)
print(json.dumps({"n_muscles": env.unwrapped.model_info.n_muscles, "sha256": info["model_sha256"]}))
"""
    )
    assert result["n_muscles"] == 6
    assert len(result["sha256"]) == 64


def test_ac_2_random_rollout_clean() -> None:
    """AC-2, NFR-REL-001, NFR-HEADLESS-001: rollout headless không có NaN/Inf."""
    result = _run_entrypoint(
        """
import json
import gymnasium
import numpy as np
from mma_ai.environment import register_envs
register_envs()
env = gymnasium.make("MmaElbowReach-v0")
rng = np.random.default_rng(20261009)
steps = 0
for episode in range(10):
    observation, _ = env.reset(seed=1000 + episode)
    assert observation.shape == (14,) and env.observation_space.contains(observation)
    for _ in range(100):
        action = rng.uniform(0.0, 1.0, size=6).astype(np.float32)
        observation, reward, terminated, truncated, _ = env.step(action)
        steps += 1
        assert observation.shape == (14,) and env.observation_space.contains(observation)
        assert np.isfinite(reward)
        assert all(
            np.all(np.isfinite(getattr(env.unwrapped.data, name)))
            for name in ("qpos", "qvel", "act")
        )
        if terminated or truncated:
            break
print(json.dumps({"episodes": 10, "steps": steps}))
"""
    )
    assert result["episodes"] == 10
    assert result["steps"] > 0


def test_ac_3_same_seed_disjoint_sets() -> None:
    """AC-3, NFR-REPRO-001: hai tiến trình sinh dữ liệu giống nhau và rời nhau."""
    script = """
import json
import gymnasium
from mma_ai.environment import register_envs
register_envs()
pair = gymnasium.make("MmaElbowReach-v0").unwrapped.targets
train = {tuple(target.position_m) for target in pair.train.targets}
test = {tuple(target.position_m) for target in pair.test.targets}
assert train.isdisjoint(test)
print(json.dumps(pair.to_dict(), sort_keys=True))
"""
    first = _run_entrypoint(script)
    second = _run_entrypoint(script)
    assert first == second
    train = {tuple(item["position_m"]) for item in first["train"]}
    test = {tuple(item["position_m"]) for item in first["test"]}
    assert train.isdisjoint(test)


def test_ac_4_no_position_controller() -> None:
    """AC-4: entrypoint thật chỉ có actuator muscle, không motor hay position."""
    result = _run_entrypoint(
        """
import json
import gymnasium
import mujoco
from mma_ai.environment import register_envs
register_envs()
model = gymnasium.make("MmaElbowReach-v0").unwrapped.model
is_muscle = [
    bool(
        model.actuator_gaintype[index] == mujoco.mjtGain.mjGAIN_MUSCLE
        and model.actuator_biastype[index] == mujoco.mjtBias.mjBIAS_MUSCLE
        and model.actuator_dyntype[index] == mujoco.mjtDyn.mjDYN_MUSCLE
    )
    for index in range(model.nu)
]
assert model.nu == 6 and all(is_muscle)
print(json.dumps({"actuators": model.nu, "all_muscle": all(is_muscle)}))
"""
    )
    assert result == {"actuators": 6, "all_muscle": True}


def test_ac_5_clean_install() -> None:
    """AC-5, NFR-INST-001: CLI đồng bộ lockfile trong môi trường ảo sạch."""
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    completed = subprocess.run(
        [sys.executable, "-m", "mma_ai.environment.verify_clean_install"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=900,
    )
    record_path = PROJECT_ROOT / "logs" / "m1" / "verify_clean_install.json"
    assert record_path.is_file(), completed.stdout + completed.stderr
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["passed"] is True
    assert record["exit_codes"] == {"sync": 0, "pytest": 0}
    assert all(version != "unknown" for version in record["installed_versions"].values())
