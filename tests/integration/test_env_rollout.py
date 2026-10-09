"""Kiểm thử tích hợp (integration test) triển khai cuộn (rollout) và kiểm tra hợp lệ (validation).

Áp dụng cho môi trường mô phỏng (simulation) MyoElbow (US2).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from mma_ai.environment.errors import ActivationError, PhysicsInstabilityError


def _make_env() -> Any:
    """Tạo môi trường sau khi pytest đã thiết lập môi trường thực thi."""
    from mma_ai.environment.single_agent import ElbowReachEnv

    return ElbowReachEnv()


def _assert_finite_env_state(env: Any) -> None:
    """Khẳng định các trạng thái số học công khai của mô phỏng đều hữu hạn."""
    for name in ("qpos", "qvel", "act"):
        assert np.all(np.isfinite(getattr(env.data, name))), name


def test_ac_2_random_rollout_no_nan_inf() -> None:
    """AC-2, INV-004, NFR-REL-001: 10 rollout ngẫu nhiên luôn trả quan sát (observation) hợp lệ."""
    env = _make_env()
    rng = np.random.default_rng(20261009)

    for episode in range(10):
        obs, _ = env.reset(seed=1000 + episode)
        assert obs.shape == (14,)
        assert env.observation_space.contains(obs)
        _assert_finite_env_state(env)

        for _ in range(100):
            action = rng.uniform(0.0, 1.0, size=6).astype(np.float32)
            obs, reward, terminated, truncated, _ = env.step(action)

            assert obs.shape == (14,)
            assert env.observation_space.contains(obs)
            assert np.isfinite(reward)
            _assert_finite_env_state(env)
            if terminated or truncated:
                break


def test_inv_004_extreme_actions_stay_in_bounds() -> None:
    """INV-004, AC-2: Các hành động cực trị vẫn tạo observation trong cận."""
    env = _make_env()
    extreme_actions = (
        np.zeros(6, dtype=np.float32),
        np.ones(6, dtype=np.float32),
        np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0], dtype=np.float32),
    )

    for action in extreme_actions:
        env.reset(seed=42)
        for _ in range(20):
            obs, reward, terminated, truncated, _ = env.step(action)
            assert env.observation_space.contains(obs)
            assert np.isfinite(reward)
            _assert_finite_env_state(env)
            if terminated or truncated:
                break


def test_fr_003_rejects_invalid_actions() -> None:
    """FR-003, AC-2: Kích thích sai bị từ chối cùng giá trị hoặc kích thước vi phạm."""
    invalid_actions = (
        (np.zeros(5, dtype=np.float32), "5 phần tử"),
        (np.array([np.nan, 0, 0, 0, 0, 0], dtype=np.float32), "NaN"),
        (np.array([np.inf, 0, 0, 0, 0, 0], dtype=np.float32), "Inf"),
        (np.array([-0.1, 0, 0, 0, 0, 0], dtype=np.float32), "-0.1"),
        (np.array([1.1, 0, 0, 0, 0, 0], dtype=np.float32), "1.1"),
    )

    for action, expected in invalid_actions:
        env = _make_env()
        env.reset(seed=42)
        with pytest.raises(ActivationError, match=expected):
            env.step(action)


def test_fr_006_physics_instability_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-006, AC-2: Kết quả quét NaN tiêm vào phải nêu bước và đại lượng lỗi."""
    env = _make_env()
    env.reset(seed=42)

    def injected_scan(_: dict[str, np.ndarray]) -> tuple[int, int, str | None]:
        return 1, 0, "qvel"

    monkeypatch.setattr("mma_ai.physics.numeric_health.scan_nonfinite", injected_scan)

    with pytest.raises(PhysicsInstabilityError, match=r"substep 1.*qvel"):
        env.step(np.zeros(6, dtype=np.float32))


def test_fr_003_ctrl_effective_recorded_next_to_requested() -> None:
    """FR-003, AC-2: Kích thích 0 ghi cả giá trị yêu cầu và giá trị kẹp tối thiểu."""
    env = _make_env()
    env.reset(seed=42)

    _, _, _, _, info = env.step(np.zeros(6, dtype=np.float32))

    assert info["ctrl_requested"] == [0.0] * 6
    assert info["ctrl_effective"] == pytest.approx([0.001] * 6)


def test_nfr_rel_001_same_seed_same_rollout() -> None:
    """NFR-REL-001, AC-2: Cùng hạt ngẫu nhiên (seed) và chuỗi hành động cho rollout giống hệt."""
    first_env = _make_env()
    second_env = _make_env()
    actions = np.random.default_rng(91).uniform(0.0, 1.0, size=(30, 6)).astype(np.float32)

    first_obs, _ = first_env.reset(seed=701)
    second_obs, _ = second_env.reset(seed=701)
    assert np.array_equal(first_obs, second_obs)

    for action in actions:
        first = first_env.step(action)
        second = second_env.step(action)
        first_obs, first_reward, first_terminated, first_truncated, _ = first
        second_obs, second_reward, second_terminated, second_truncated, _ = second

        assert np.array_equal(first_obs, second_obs)
        assert first_reward == second_reward
        assert first_terminated == second_terminated
        assert first_truncated == second_truncated
        if first_terminated or first_truncated:
            break
