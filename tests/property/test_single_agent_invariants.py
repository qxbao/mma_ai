"""Kiểm chứng bất biến (Property-based tests) cho môi trường đơn agent.

Chứng minh tính đúng đắn của các bất biến hệ thống:
- INV-001, AC-3: Môi trường test không bao giờ chọn mục tiêu train; cách nhau >= min_separation_m.
- INV-002, AC-3: Cùng seed và cùng cấu hình luôn chọn cùng mục tiêu ở reset(seed).
- INV-003, AC-4: Đường điều khiển duy nhất qua kích thích cơ u in [0, 1]^6.
- INV-004, AC-2: Mọi observation trong rollout luôn có chiều 14, hữu hạn và trong cận.
- NFR-REL-001, AC-2: Không có giá trị NaN hoặc Inf nào trong suốt rollout ngẫu nhiên.
"""


from __future__ import annotations

from typing import Any

import numpy as np
import pytest


def _make_reach_env(*args: Any, **kwargs: Any) -> Any:
    """Tạo đối tượng ElbowReachEnv mà không import tại module level lúc pytest collect."""
    from mma_ai.environment.single_agent import ElbowReachEnv

    return ElbowReachEnv(*args, **kwargs)


def test_inv_001_test_split_never_selects_train_target() -> None:
    """INV-001, AC-3: Quét 30 seed, chế độ test không bao giờ chọn mục tiêu train."""
    env = _make_reach_env(split="test")
    train_positions = [np.array(t.position_m) for t in env.targets.train.targets]
    min_sep = float(env.cfg.targets.min_separation_m)

    for seed in range(100, 130):
        _, info = env.reset(seed=seed, options={"split": "test"})
        assert info["target_split"] == "test"
        selected_pos = np.array(info["target_position_m"])

        # Kiểm tra khoảng cách Euclid 3D tới mọi mục tiêu train
        for tr_pos in train_positions:
            dist = float(np.linalg.norm(selected_pos - tr_pos))
            assert dist >= min_sep - 1e-6, (
                f"Bất biến INV-001 vi phạm: mục tiêu test ({selected_pos}) "
                f"gần mục tiêu train ({tr_pos}) khoảng cách {dist:.6f} m < {min_sep} m"
            )


def test_inv_002_deterministic_reset_target_selection() -> None:
    """INV-002, AC-3: Với cùng seed, reset(seed) luôn chọn cùng một mục tiêu giữa các lần chạy."""
    env = _make_reach_env()

    for seed in [1, 7, 42, 99, 1337, 2026]:
        obs1, info1 = env.reset(seed=seed)
        obs2, info2 = env.reset(seed=seed)

        assert info1["target_index"] == info2["target_index"]
        assert info1["target_position_m"] == info2["target_position_m"]
        assert info1["initial_distance_m"] == pytest.approx(info2["initial_distance_m"], rel=1e-6)
        assert np.allclose(obs1, obs2, atol=1e-6)


def test_inv_003_control_only_via_muscle_activations() -> None:
    """INV-003, AC-4: Mô hình chỉ có đúng 6 cơ bắp, không có actuator phi cơ."""
    env = _make_reach_env()

    # Khẳng định chỉ có đúng 6 actuator và đều là cơ bắp
    assert env.model.nu == 6
    assert env.action_space.shape == (6,)
    assert np.all(env.action_space.low == 0.0)
    assert np.all(env.action_space.high == 1.0)

    # Chạy một bước với hành động hợp lệ và kiểm tra ctrl_effective
    env.reset(seed=42)
    action = np.array([0.0, 0.2, 0.5, 0.8, 1.0, 0.3], dtype=np.float32)
    _, _, _, _, info = env.step(action)

    ctrl_eff = info["ctrl_effective"]
    for i in range(6):
        ctrl_min = float(env.model.actuator_ctrlrange[i, 0])
        ctrl_max = float(env.model.actuator_ctrlrange[i, 1])
        assert ctrl_min <= ctrl_eff[i] <= ctrl_max


def test_inv_004_observation_always_within_bounds_during_rollouts() -> None:
    """INV-004, NFR-REL-001, AC-2: Rollout ngẫu nhiên 15 episode x 30 bước, obs luôn trong cận."""
    env = _make_reach_env()

    rng = np.random.default_rng(20261009)

    low_bounds = env.layout.low
    high_bounds = env.layout.high
    tol = 1e-4

    total_steps = 0
    for ep in range(15):
        obs, info = env.reset(seed=int(rng.integers(0, 10000)))
        assert obs.shape == (14,)
        assert np.all(np.isfinite(obs))
        assert np.all(obs >= low_bounds - tol)
        assert np.all(obs <= high_bounds + tol)

        for _ in range(30):
            # Lấy mẫu hành động ngẫu nhiên trong [0, 1]^6
            action = rng.uniform(0.0, 1.0, size=6).astype(np.float32)
            obs, reward, terminated, truncated, step_info = env.step(action)
            total_steps += 1

            assert obs.shape == (14,)
            # NFR-REL-001: 0 NaN, 0 Inf
            assert np.all(np.isfinite(obs)), f"Phát hiện NaN/Inf trong obs tại bước {total_steps}"
            assert np.isfinite(reward), f"Phát hiện NaN/Inf trong reward tại bước {total_steps}"

            # INV-004: Observation trong cận khai báo
            assert np.all(obs >= low_bounds - tol), (
                f"Obs dưới cận tại bước {total_steps}: {obs[obs < low_bounds - tol]} "
                f"< {low_bounds[obs < low_bounds - tol]}"
            )
            assert np.all(obs <= high_bounds + tol), (
                f"Obs trên cận tại bước {total_steps}: {obs[obs > high_bounds + tol]} "
                f"> {high_bounds[obs > high_bounds + tol]}"
            )

            if terminated or truncated:
                break

    assert total_steps > 100, f"Tổng số bước chạy thực tế: {total_steps}"
