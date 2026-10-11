"""Mô-đun tính toán phần thưởng (reward) và điều kiện tới đích (mma_ai.environment.reward).

Cung cấp hàm tính phần thưởng và kiểm tra điều kiện tới mục tiêu:
- FR-008: Phần thưởng gồm thành phần tiến tới mục tiêu và phạt nỗ lực kích hoạt cơ (muscle effort).
- FR-009: Xác định trạng thái kết thúc khi khoảng cách đạt dung sai (tolerance_m).
- AC-2: Đảm bảo tính đơn điệu, hữu hạn, không chứa NaN hoặc Inf.
- INV-004: Kiểm soát tính toàn vẹn số học của các đại lượng mô phỏng.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from mma_ai.environment.env_config import ElbowEnvConfig, RewardConfig
from mma_ai.environment.errors import EnvironmentBaseError

_NUM_MUSCLES: int = 6


class RewardError(EnvironmentBaseError, ValueError):
    """Lỗi tính toán phần thưởng khi khoảng cách hoặc hành động không hợp lệ."""


@dataclass(frozen=True)
class RewardTerms:
    """Các thành phần chi tiết của phần thưởng (reward terms)."""

    reward_dist: float
    reward_effort: float
    total: float

    def to_dict(self) -> dict[str, float]:
        """Xuất các thành phần phần thưởng thành từ điển (dictionary)."""
        return {
            "reward_dist": self.reward_dist,
            "reward_effort": self.reward_effort,
            "total": self.total,
        }


def _validate_distance(distance: float, label: str = "Khoảng cách tới mục tiêu") -> float:
    """Xác thực khoảng cách là số thực hữu hạn không âm."""
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise RewardError(f"{label} phải là số thực, nhận được: {type(distance).__name__}.")
    d_val = float(distance)
    if math.isnan(d_val) or math.isinf(d_val):
        raise RewardError(f"{label} phải hữu hạn (không NaN/Inf), nhận được: {distance}.")
    if d_val < 0.0:
        raise RewardError(f"{label} không được âm (< 0), nhận được: {distance}.")
    return d_val


def _validate_action(action: Sequence[float] | np.ndarray[Any, Any] | Any) -> list[float]:
    """Xác thực vector hành động kích thích cơ có đúng 6 phần tử hữu hạn."""
    if isinstance(action, np.ndarray):
        if action.size != _NUM_MUSCLES:
            raise RewardError(
                f"Kích thước vector hành động kích thích cơ phải có đúng {_NUM_MUSCLES} phần tử, "
                f"nhận được kích thước: {action.shape}."
            )
        if not np.issubdtype(action.dtype, np.number):
            raise RewardError("Vector hành động kích thích cơ phải chứa các giá trị số.")
        if bool(np.isnan(action).any()) or bool(np.isinf(action).any()):
            raise RewardError("Vector hành động kích thích cơ phải hữu hạn (không chứa NaN/Inf).")
        return [float(x) for x in action.flat]

    if isinstance(action, Sequence) and not isinstance(action, (str, bytes)):
        if len(action) != _NUM_MUSCLES:
            raise RewardError(
                f"Kích thước vector hành động kích thích cơ phải có đúng {_NUM_MUSCLES} phần tử, "
                f"nhận được: {len(action)}."
            )
        vals: list[float] = []
        for i, val in enumerate(action):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise RewardError(
                    f"Phần tử hành động tại chỉ số {i} phải là số, nhận được: {type(val).__name__}."
                )
            fval = float(val)
            if math.isnan(fval) or math.isinf(fval):
                raise RewardError(
                    f"Phần tử hành động tại chỉ số {i} phải hữu hạn (không NaN/Inf), "
                    f"nhận được: {fval}."
                )
            vals.append(fval)
        return vals

    raise RewardError(
        f"Hành động phải là Sequence hoặc ndarray có đúng {_NUM_MUSCLES} phần tử, "
        f"nhận được: {type(action).__name__}."
    )


def compute_reward(
    distance: float,
    action: Sequence[float] | np.ndarray[Any, Any] | Any,
    cfg: ElbowEnvConfig | RewardConfig | Any,
) -> RewardTerms:
    """Tính toán các thành phần phần thưởng và tổng phần thưởng (FR-008, AC-2)."""
    d_val = _validate_distance(distance)
    u_vals = _validate_action(action)

    if isinstance(cfg, ElbowEnvConfig):
        reward_cfg: RewardConfig = cfg.reward
    elif isinstance(cfg, RewardConfig):
        reward_cfg = cfg
    elif hasattr(cfg, "reward"):
        reward_cfg = getattr(cfg, "reward")
    else:
        reward_cfg = cfg

    try:
        w_dist = float(reward_cfg.w_dist)
        w_effort = float(reward_cfg.w_effort)
        d_ref_m = float(reward_cfg.d_ref_m)
    except AttributeError as err:
        raise RewardError(f"Cấu hình thiếu tham số trọng số phần thưởng bắt buộc: {err}.") from err

    if d_ref_m <= 0.0:
        raise RewardError(
            f"Khoảng cách tham chiếu d_ref_m phải là số thực dương (> 0), nhận được: {d_ref_m}."
        )

    reward_dist = -w_dist * (d_val / d_ref_m)

    if w_effort == 0.0:
        reward_effort = 0.0
    else:
        mean_u_sq = sum(u * u for u in u_vals) / float(_NUM_MUSCLES)
        reward_effort = -w_effort * mean_u_sq
        if reward_effort == 0.0:
            reward_effort = 0.0

    total = reward_dist + reward_effort

    if not (math.isfinite(reward_dist) and math.isfinite(reward_effort) and math.isfinite(total)):
        raise RewardError("Kết quả tính toán phần thưởng chứa giá trị không hữu hạn (NaN/Inf).")

    return RewardTerms(
        reward_dist=reward_dist,
        reward_effort=reward_effort,
        total=total,
    )


def is_reached(distance: float, tolerance: float) -> bool:
    """Kiểm tra khoảng cách đã đạt điều kiện tới mục tiêu hay chưa (FR-009, AC-2)."""
    d_val = _validate_distance(distance, label="Khoảng cách tới mục tiêu")
    tol_val = _validate_distance(tolerance, label="Dung sai tới đích (tolerance)")
    return d_val <= tol_val


__all__: list[str] = [
    "RewardError",
    "RewardTerms",
    "compute_reward",
    "is_reached",
]
