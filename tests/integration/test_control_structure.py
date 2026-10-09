"""Kiểm thử cấu trúc điều khiển cơ bắp cho AC-4 và INV-003."""

from __future__ import annotations

import inspect
from typing import Any

import mujoco
import numpy as np


def _make_env() -> Any:
    """Tạo môi trường thật với mô hình cơ bắp sáu actuator."""
    from mma_ai.environment.single_agent import ElbowReachEnv

    return ElbowReachEnv()


def _make_env_via_factory() -> Any:
    """Tạo môi trường qua factory công khai."""
    from mma_ai.environment.single_agent import make_env

    return make_env()


def _state_snapshot(env: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Sao chép các mảng trạng thái không được API công khai ghi trực tiếp."""
    return (
        env.data.qpos.copy(),
        env.data.qvel.copy(),
        env.data.site_xpos.copy(),
        env.data.actuator_force.copy(),
    )


def test_ac_4_all_actuators_are_muscle() -> None:
    """AC-4, INV-003: Sáu actuator đều là muscle, không có motor hay position actuator."""
    env = _make_env()

    assert env.model.nu == 6
    assert all(
        env.model.actuator_gaintype[index] == mujoco.mjtGain.mjGAIN_MUSCLE
        and env.model.actuator_biastype[index] == mujoco.mjtBias.mjBIAS_MUSCLE
        and env.model.actuator_dyntype[index] == mujoco.mjtDyn.mjDYN_MUSCLE
        for index in range(env.model.nu)
    )


def test_inv_003_reset_and_model_record_do_not_mutate_geometry() -> None:
    """INV-003: reset chỉ đưa về trạng thái đầu; model_record không ghi hình học hay lực."""
    env = _make_env()
    env.reset(seed=11)
    baseline = _state_snapshot(env)

    env.model_record()
    after_record = _state_snapshot(env)
    assert all(np.array_equal(before, after) for before, after in zip(baseline, after_record))

    env.step(np.ones(6, dtype=np.float32))
    env.reset(seed=11)
    after_reset = _state_snapshot(env)
    assert np.array_equal(after_reset[0], baseline[0])
    assert np.array_equal(after_reset[1], baseline[1])
    assert np.array_equal(after_reset[2], baseline[2])
    assert np.array_equal(after_reset[3], baseline[3])

    other_env = _make_env_via_factory()
    assert type(other_env) is type(env)
    assert np.array_equal(other_env.data.qpos, baseline[0])
    assert np.array_equal(other_env.data.qvel, baseline[1])


def test_inv_003_step_changes_ctrl_while_physics_computes_force() -> None:
    """INV-003, AC-4: bước môi trường ghi kích thích ctrl; MuJoCo tự tính lực cơ."""
    env = _make_env()
    env.reset(seed=19)
    requested = np.full(6, 0.75, dtype=np.float32)
    force_before = env.data.actuator_force.copy()

    _, _, _, _, info = env.step(requested)

    assert np.allclose(env.data.ctrl, requested)
    assert info["ctrl_requested"] == [0.75] * 6
    assert info["ctrl_effective"] == [0.75] * 6
    assert not np.array_equal(env.data.actuator_force, force_before)


def test_inv_003_no_public_state_writer_api() -> None:
    """INV-003: API công khai không phơi bày setter qpos, lực hay vị trí bàn tay."""
    forbidden_fragments = ("set_qpos", "set_qvel", "set_force", "set_hand", "set_site")
    public_methods = {
        name
        for name, member in inspect.getmembers(type(_make_env()), predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    assert not {
        name
        for name in public_methods
        if any(fragment in name.lower() for fragment in forbidden_fragments)
    }
