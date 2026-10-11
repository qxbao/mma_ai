"""Bộ kiểm thử đơn vị cho mô-đun tính toán phần thưởng (mma_ai.environment.reward).

Kiểm chứng các yêu cầu chức năng và bất biến của hàm phần thưởng và điều kiện tới đích:
- FR-008: Thành phần tiến tới mục tiêu, phạt nỗ lực kích hoạt cơ, hữu hạn ở mọi bước.
- FR-009: Điều kiện kết thúc khi khoảng cách đạt dung sai (d <= tolerance_m).
- AC-2: Trạng thái gần mục tiêu có reward cao hơn; nỗ lực lớn hơn bị phạt nhiều hơn; không NaN/Inf.
- NFR-REL-001: Độ tin cậy số học, 0 giá trị NaN và 0 giá trị Inf trong kết quả phần thưởng.
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from mma_ai.environment.env_config import ElbowEnvConfig, RewardConfig
from mma_ai.environment.reward import (
    RewardError,
    RewardTerms,
    compute_reward,
    is_reached,
)


@pytest.fixture  # type: ignore[untyped-decorator]
def default_reward_config() -> RewardConfig:
    """Fixture cung cấp cấu hình phần thưởng mặc định cho kiểm thử."""
    return RewardConfig(
        w_dist=1.0,
        w_effort=0.01,
        d_ref_m=0.5,
    )


@pytest.fixture  # type: ignore[untyped-decorator]
def sample_valid_action() -> list[float]:
    """Fixture cung cấp vector hành động kích thích 6 cơ hợp lệ."""
    return [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]


def test_closer_is_better(
    default_reward_config: RewardConfig,
    sample_valid_action: list[float],
) -> None:
    """Kiểm chứng khoảng cách gần mục tiêu hơn cho phần thưởng cao hơn (FR-008, AC-2)."""
    d_close = 0.05
    d_far = 0.25

    terms_close = compute_reward(d_close, sample_valid_action, default_reward_config)
    terms_far = compute_reward(d_far, sample_valid_action, default_reward_config)

    # w_dist = 1.0, d_ref_m = 0.5
    # expected reward_dist: -1.0 * (0.05 / 0.5) = -0.1
    # expected reward_dist: -1.0 * (0.25 / 0.5) = -0.5
    assert terms_close.reward_dist == pytest.approx(-0.1)
    assert terms_far.reward_dist == pytest.approx(-0.5)
    assert terms_close.reward_dist > terms_far.reward_dist

    # Cùng hành động nên thành phần phạt nỗ lực bằng nhau
    assert terms_close.reward_effort == pytest.approx(terms_far.reward_effort)

    # Tổng phần thưởng của trạng thái gần phải cao hơn trạng thái xa
    assert terms_close.total > terms_far.total
    assert terms_close.total == pytest.approx(terms_close.reward_dist + terms_close.reward_effort)


def test_effort_penalty_scales_and_zero_weight(
    default_reward_config: RewardConfig,
) -> None:
    """Kiểm chứng phạt nỗ lực theo kích hoạt và triệt tiêu khi w_effort = 0 (FR-008, AC-2)."""
    d = 0.1
    u_small = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    u_large = [0.9, 0.9, 0.9, 0.9, 0.9, 0.9]

    terms_small = compute_reward(d, u_small, default_reward_config)
    terms_large = compute_reward(d, u_large, default_reward_config)

    # mean(u_small^2) = 0.01; mean(u_large^2) = 0.81
    # Với w_effort = 0.01:
    # reward_effort_small = -0.01 * 0.01 = -0.0001
    # reward_effort_large = -0.01 * 0.81 = -0.0081
    assert terms_small.reward_effort == pytest.approx(-0.0001)
    assert terms_large.reward_effort == pytest.approx(-0.0081)
    # Bị phạt ít hơn thì giá trị lớn hơn (ít âm hơn)
    assert terms_small.reward_effort > terms_large.reward_effort

    # Khi w_effort = 0.0, thành phần phạt bằng đúng 0.0
    zero_effort_config = RewardConfig(w_dist=1.0, w_effort=0.0, d_ref_m=0.5)
    terms_zero_small = compute_reward(d, u_small, zero_effort_config)
    terms_zero_large = compute_reward(d, u_large, zero_effort_config)

    assert terms_zero_small.reward_effort == 0.0
    assert terms_zero_large.reward_effort == 0.0
    assert terms_zero_small.total == terms_zero_small.reward_dist
    assert terms_zero_large.total == terms_zero_large.reward_dist


def test_reward_finite(default_reward_config: RewardConfig) -> None:
    """Kiểm chứng tính hữu hạn của phần thưởng ở mọi đầu vào hợp lệ (FR-008, AC-2, NFR-REL-001)."""
    distances = [0.0, 0.001, 0.02, 0.5, 1.0, 10.0]
    actions = [
        [0.0] * 6,
        [1.0] * 6,
        [0.5] * 6,
        np.array([0.001, 0.2, 0.4, 0.6, 0.8, 1.0], dtype=np.float32),
    ]

    for d in distances:
        for u in actions:
            terms = compute_reward(d, u, default_reward_config)
            assert math.isfinite(terms.reward_dist), f"reward_dist: {terms.reward_dist}"
            assert math.isfinite(terms.reward_effort), f"reward_effort: {terms.reward_effort}"
            assert math.isfinite(terms.total), f"total: {terms.total}"
            assert not math.isnan(terms.total)
            assert not math.isinf(terms.total)


def test_is_reached_boundary_inclusive() -> None:
    """Kiểm chứng điều kiện tới đích d <= tolerance_m bao gồm cả giá trị biên (FR-009, AC-2)."""
    tol = 0.02

    # Giá trị đúng tại biên
    assert is_reached(0.02, tol) is True
    assert is_reached(tol, tol) is True

    # Giá trị nhỏ hơn biên (đã chạm đích)
    assert is_reached(0.0, tol) is True
    assert is_reached(0.019999, tol) is True
    assert is_reached(0.01, tol) is True

    # Giá trị lớn hơn biên (chưa chạm đích)
    assert is_reached(0.020001, tol) is False
    assert is_reached(0.021, tol) is False
    assert is_reached(0.05, tol) is False
    assert is_reached(1.0, tol) is False


def test_invalid_inputs_raise(default_reward_config: RewardConfig) -> None:
    """Kiểm chứng ném ngoại lệ rõ ràng khi d âm/NaN hoặc u sai kích thước (FR-008, FR-009)."""
    valid_u = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

    # 1. Khoảng cách âm
    with pytest.raises(RewardError, match="[Kk]hoảng cách.*âm"):
        compute_reward(-0.01, valid_u, default_reward_config)

    # 2. Khoảng cách NaN / Inf
    with pytest.raises(RewardError, match="[Kk]hoảng cách.*[Nn]a[Nn]|[Hh]ữu hạn"):
        compute_reward(float("nan"), valid_u, default_reward_config)

    with pytest.raises(RewardError, match="[Kk]hoảng cách.*[Ii]nf|[Hh]ữu hạn"):
        compute_reward(float("inf"), valid_u, default_reward_config)

    # 3. Khoảng cách không phải kiểu số
    with pytest.raises(RewardError):
        compute_reward("0.5", valid_u, default_reward_config)  # type: ignore[arg-type]

    # 4. Hành động sai kích thước (khác 6)
    with pytest.raises(RewardError, match="[Kk]ích thước|6"):
        compute_reward(0.1, [0.1, 0.2, 0.3, 0.4, 0.5], default_reward_config)

    with pytest.raises(RewardError, match="[Kk]ích thước|6"):
        compute_reward(0.1, [0.1] * 7, default_reward_config)

    with pytest.raises(RewardError, match="[Kk]ích thước|6"):
        compute_reward(0.1, np.array([0.1, 0.2]), default_reward_config)

    # 5. Hành động chứa NaN hoặc Inf
    with pytest.raises(RewardError, match="[Hh]ữu hạn|[Nn]a[Nn]"):
        compute_reward(0.1, [0.1, float("nan"), 0.3, 0.4, 0.5, 0.6], default_reward_config)

    with pytest.raises(RewardError, match="[Hh]ữu hạn|[Ii]nf"):
        compute_reward(0.1, [0.1, float("inf"), 0.3, 0.4, 0.5, 0.6], default_reward_config)

    # 6. is_reached với đầu vào không hợp lệ
    with pytest.raises(RewardError, match="[Kk]hoảng cách.*âm"):
        is_reached(-0.01, 0.02)

    with pytest.raises(RewardError, match="[Kk]hoảng cách.*[Nn]a[Nn]|[Hh]ữu hạn"):
        is_reached(float("nan"), 0.02)

    with pytest.raises(RewardError, match="[Dd]ung sai.*âm"):
        is_reached(0.01, -0.02)

    with pytest.raises(RewardError, match="[Dd]ung sai.*[Nn]a[Nn]|[Hh]ữu hạn"):
        is_reached(0.01, float("nan"))


def test_reward_terms_structure() -> None:
    """Kiểm tra cấu trúc và tính bất biến của RewardTerms (FR-008)."""
    terms = RewardTerms(reward_dist=-0.2, reward_effort=-0.05, total=-0.25)
    assert terms.reward_dist == -0.2
    assert terms.reward_effort == -0.05
    assert terms.total == -0.25

    d = terms.to_dict()
    assert d == {"reward_dist": -0.2, "reward_effort": -0.05, "total": -0.25}

    # Bất biến (frozen dataclass)
    frozen_err = getattr(dataclasses, "FrozenInstanceError", Exception)
    with pytest.raises(frozen_err):
        terms.total = 0.0  # type: ignore[misc]


def test_compute_reward_with_elbow_env_config() -> None:
    """Kiểm chứng compute_reward chấp nhận cả ElbowEnvConfig đầy đủ từ load() (FR-008, FR-014)."""
    cfg = ElbowEnvConfig.load()
    action = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    terms = compute_reward(0.1, action, cfg)

    # cfg.reward.w_dist = 1.0, cfg.reward.d_ref_m = 0.5
    # -1.0 * (0.1 / 0.5) = -0.2
    assert terms.reward_dist == pytest.approx(-0.2)
    assert terms.total == pytest.approx(terms.reward_dist + terms.reward_effort)
