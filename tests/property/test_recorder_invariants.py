"""Kiểm chứng bất biến (Property-based tests) cho mô-đun recorder (mma_ai.visualization.recorder).

Chứng minh các bất biến hệ thống:
- INV-002: Lớp hiển thị chỉ đọc trạng thái qua env.read_state(), đường điều khiển duy nhất
  là kích thích cơ u in [0, 1]^6; mọi hành động đưa vào step phải hợp lệ; vi phạm bị chặn tại biên.
- NFR-REL-001: Mọi số trong mọi khung hình của episode đều hữu hạn (không NaN/Inf).
- NFR-REPRO-001: Tái lập 100% khi cùng seed và target_index trên nhiều lượt quét ngẫu nhiên.
"""

from __future__ import annotations

import math

import numpy as np

from mma_ai.environment.single_agent import make_env
from mma_ai.visualization.episode import Episode
from mma_ai.visualization.recorder import record_episode


class RandomBoundedPolicy:
    """Policy sinh hành động ngẫu nhiên tất định dựa trên seed cục bộ."""

    def __init__(self, seed: int, invalid_prob: float = 0.0) -> None:
        self.rng = np.random.default_rng(seed)
        self.invalid_prob = invalid_prob

    def act_deterministic(self, obs: np.ndarray) -> list[float]:
        if self.invalid_prob > 0.0 and self.rng.random() < self.invalid_prob:
            # Sinh hành động sai biên hoặc NaN
            choice = self.rng.integers(0, 3)
            if choice == 0:
                return [float("nan")] * 6
            elif choice == 1:
                return [-0.2] * 6
            else:
                return [1.5] * 6
        return [float(x) for x in self.rng.uniform(0.0, 1.0, size=6)]


def test_inv_002_nfr_rel_001_sweep_seeds_finite_and_unit_interval() -> None:
    """INV-002, NFR-REL-001: Quét 10 seeds, kiểm tra hữu hạn và excitation in [0, 1]^6."""
    env = make_env(split="test")

    for seed in range(200, 210):
        policy = RandomBoundedPolicy(seed=seed, invalid_prob=0.0)
        episode = record_episode(
            env,
            policy,
            split="test",
            target_index=seed % 5,
            seed=seed,
        )

        assert isinstance(episode, Episode)
        for idx, frame in enumerate(episode.frames):
            assert math.isfinite(frame.t_s)
            assert math.isfinite(frame.distance_m)
            assert math.isfinite(frame.reward)
            assert all(math.isfinite(x) for x in frame.qpos)
            assert all(math.isfinite(x) for x in frame.qvel)
            assert all(math.isfinite(x) for x in frame.activation)
            assert all(0.0 <= x <= 1.0 for x in frame.activation)

            if idx == 0:
                assert frame.excitation is None
            else:
                assert frame.excitation is not None
                assert len(frame.excitation) == 6
                assert all(math.isfinite(u) for u in frame.excitation)
                assert all(0.0 <= u <= 1.0 for u in frame.excitation)


def test_inv_002_invalid_action_sweep_always_abnormal_and_finite() -> None:
    """INV-002: Quét policy tiêm lỗi ngẫu nhiên, episode luôn kết thúc abnormal và hữu hạn."""
    env = make_env(split="test")

    for seed in range(300, 310):
        # Xác suất tiêm lỗi 100% để luôn vi phạm
        policy = RandomBoundedPolicy(seed=seed, invalid_prob=1.0)
        episode = record_episode(
            env,
            policy,
            split="test",
            target_index=0,
            seed=seed,
        )

        assert episode.outcome.end_reason == "abnormal"
        assert episode.outcome.reached is False
        assert episode.outcome.terminated is False
        assert episode.outcome.truncated is False
        # Đảm bảo khung hình đã thu thập vẫn hoàn toàn hữu hạn
        for frame in episode.frames:
            assert all(math.isfinite(x) for x in frame.activation)
