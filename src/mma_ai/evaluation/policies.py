"""Mô-đun chính sách điều khiển cho phân hệ đánh giá (mma_ai.evaluation.policies).

Cung cấp các lớp chính sách (policy) phục vụ đánh giá so sánh:
- 004 FR-003, 004 INV-003: Mọi hành động là kích thích cơ u in [0, 1]^6.
- 004 INV-007, NFR-REPRO-001: RandomPolicy bảo đảm tính tất định theo hạt giống ngẫu nhiên (seed).
- 004 API-EVL-0004: Giao diện chung act(obs_raw) -> np.ndarray[6].
- 004 AC-5: LearnedPolicy ném CheckpointUnusable khi điểm kiểm tra (checkpoint) lỗi.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any

import numpy as np

from mma_ai.evaluation.errors import CheckpointUnusable


class BasePolicy(abc.ABC):
    """Giao diện cơ sở cho các chính sách trong phân hệ đánh giá (004 API-EVL-0004)."""

    @abc.abstractmethod
    def act(self, obs_raw: Any = None) -> np.ndarray:
        """Tính toán hoặc lấy mẫu hành động kích thích cơ u in [0, 1]^6.

        Args:
            obs_raw: Quan sát thô từ môi trường.

        Returns:
            np.ndarray: Mảng kích thích cơ u thuộc [0, 1]^6.
        """


Policy = BasePolicy


class RandomPolicy(BasePolicy):
    """Chính sách ngẫu nhiên lấy mẫu đều u in [0, 1]^act_dim (004 FR-003, 004 INV-003, 004 INV-007).

    Sử dụng duy nhất một bộ sinh ngẫu nhiên numpy.random.default_rng(seed) xuyên suốt
    lượt đánh giá, không nhìn quan sát observation, không điều khiển lực hay toạ độ.
    """

    def __init__(self, seed: int | None = None, act_dim: int = 6) -> None:
        """Khởi tạo RandomPolicy với hạt giống ngẫu nhiên (seed) và số chiều hành động.

        Args:
            seed: Hạt giống ngẫu nhiên để tái lập chuỗi hành động (deterministic).
            act_dim: Số chiều hành động cơ bắp (mặc định 6).

        Raises:
            ValueError: Khi act_dim <= 0.
        """
        if act_dim <= 0:
            raise ValueError(f"act_dim phải là số nguyên dương lớn hơn 0, nhận: {act_dim}")
        self.seed: int | None = seed
        self.act_dim: int = int(act_dim)
        self._rng: np.random.Generator = np.random.default_rng(seed)

    def act(self, obs_raw: Any = None) -> np.ndarray:
        """Lấy mẫu hành động u in [0, 1]^act_dim độc lập với quan sát đầu vào.

        Args:
            obs_raw: Quan sát đầu vào từ môi trường (hoàn toàn bị bỏ qua).

        Returns:
            np.ndarray: Mảng 1D gồm act_dim giá trị kích thích cơ u in [0, 1]^act_dim.
        """
        sample = self._rng.uniform(0.0, 1.0, size=self.act_dim)
        return np.asarray(sample, dtype=np.float32)


class LearnedPolicy(BasePolicy):
    """Chính sách đã học nạp từ checkpoint chỉ-đọc (004 FR-003, 004 INV-003, 004 AC-5).

    Bọc load_policy(...).act_deterministic(obs_raw) từ phân hệ learning.checkpoint.
    Chỉ nhập learning.checkpoint, nghiêm cấm nhập learning.trainer hoặc learning.ppo.
    """

    def __init__(self, checkpoint: str | Path | Any, cfg: Any = None) -> None:
        """Khởi tạo LearnedPolicy từ đường dẫn checkpoint hoặc đối tượng policy.

        Args:
            checkpoint: Đường dẫn tệp .pt, latest.json, hoặc đối tượng có act_deterministic.
            cfg: Cấu hình tuỳ chọn truyền vào khi nạp policy.

        Raises:
            CheckpointUnusable: Khi checkpoint không tồn tại, hỏng, thiếu thành phần,
                hoặc khác cấu trúc mạng.
        """
        if hasattr(checkpoint, "act_deterministic") and callable(
            getattr(checkpoint, "act_deterministic")
        ):
            self._policy: Any = checkpoint
            return

        try:
            from mma_ai.learning.checkpoint import load_policy

            self._policy = load_policy(checkpoint, cfg=cfg)
        except CheckpointUnusable:
            raise
        except Exception as err:
            raise CheckpointUnusable(
                f"Không thể nạp điểm kiểm tra (checkpoint) từ '{checkpoint}': {err}"
            ) from err

    def act(self, obs_raw: Any = None) -> np.ndarray:
        """Tính toán hành động tất định từ quan sát obs_raw (004 FR-003, 004 INV-003).

        Args:
            obs_raw: Quan sát thô từ môi trường (thường là mảng 14 chiều).

        Returns:
            np.ndarray: Mảng 1D gồm 6 giá trị kích thích cơ u in [0, 1]^6.

        Raises:
            ValueError: Khi quan sát đầu vào obs_raw là None.
        """
        if obs_raw is None:
            raise ValueError(
                "Quan sát đầu vào (obs_raw) không được để trống khi tính toán chính sách học được."
            )
        action = self._policy.act_deterministic(obs_raw)
        action_np = np.asarray(action, dtype=np.float32).reshape(-1)
        return action_np


__all__: list[str] = [
    "BasePolicy",
    "LearnedPolicy",
    "Policy",
    "RandomPolicy",
]
