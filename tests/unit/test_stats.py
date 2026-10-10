"""Kiểm thử đơn vị cho mô-đun thống kê mma_ai.evaluation.stats (API-EVL-0007).

Truy vết yêu cầu:
- FR-005: Khoảng tin cậy Wilson score và Newcombe (phương pháp 10) giải tích, bootstrap phân vị.
- FR-006: Quy tắc kết luận 'tốt hơn' khi và chỉ khi cận dưới khoảng tin cậy của hiệu lớn hơn 0.
- NFR-STAT-001: Tính đúng của khoảng tin cậy và kết luận trên dữ liệu tổng hợp.
- INV-006: Tiêu chí so sánh khai trước và bất biến với kết quả.
- AC-2: So sánh tỷ lệ thành công của hai policy kèm khoảng tin cậy 95%.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pytest

from mma_ai.evaluation.stats import (
    Verdict,
    bootstrap_mean_ci,
    decide,
    newcombe_difference,
    wilson_interval,
)


def test_wilson_matches_hand_values() -> None:
    """Kiểm tra khoảng tin cậy Wilson khớp với giá trị tính tay giải tích (FR-005, NFR-STAT-001)."""
    # Tại mức tin cậy 95%, z = 1.95996398454...
    # Với n = 50, k = 0: low = 0.0, high = z^2 / (n + z^2) ≈ 3.84146 / 53.84146 ≈ 0.071348
    low_0, high_0 = wilson_interval(0, 50, level=0.95)
    assert math.isclose(low_0, 0.0, abs_tol=1e-5)
    assert math.isclose(high_0, 0.07135, abs_tol=1e-3)

    # Với n = 50, k = 50: low = n / (n + z^2) ≈ 50 / 53.84146 ≈ 0.92865, high = 1.0
    low_50, high_50 = wilson_interval(50, 50, level=0.95)
    assert math.isclose(low_50, 0.92865, abs_tol=1e-3)
    assert math.isclose(high_50, 1.0, abs_tol=1e-5)

    # Với n = 50, k = 25 (tỷ lệ 0.5): đối xứng quanh 0.5
    low_25, high_25 = wilson_interval(25, 50, level=0.95)
    assert 0.0 < low_25 < 0.5 < high_25 < 1.0
    assert math.isclose(0.5 - low_25, high_25 - 0.5, abs_tol=1e-5)


def test_newcombe_matches_hand_values() -> None:
    """Kiểm tra khoảng tin cậy Newcombe khớp đáp án Research Q1 (FR-005, AC-2)."""
    cases: list[tuple[int, int, int, int, float, float, float]] = [
        # k1, n1, k2, n2, expected_diff, expected_low, expected_high
        (50, 50, 0, 50, 1.000, 0.899, 1.000),
        (30, 50, 10, 50, 0.400, 0.210, 0.552),
        (20, 50, 10, 50, 0.200, 0.020, 0.364),
        (15, 50, 8, 50, 0.140, -0.026, 0.297),
        (10, 50, 10, 50, 0.000, -0.157, 0.157),
        (0, 50, 0, 50, 0.000, -0.071, 0.071),
        (50, 50, 50, 50, 0.000, -0.071, 0.071),
    ]

    for k1, n1, k2, n2, exp_diff, exp_low, exp_high in cases:
        diff, ci_low, ci_high = newcombe_difference(k1, n1, k2, n2, level=0.95)
        assert math.isclose(diff, exp_diff, abs_tol=1e-3)
        assert math.isclose(ci_low, exp_low, abs_tol=1e-3)
        assert math.isclose(ci_high, exp_high, abs_tol=1e-3)
        assert -1.0 <= ci_low <= diff <= ci_high <= 1.0


def test_edge_counts_0_and_n_finite() -> None:
    """Kiểm tra ca biên k=0, k=n, n=1 luôn hữu hạn và không chia cho 0 (NFR-STAT-001)."""
    # Biên n = 1
    l_0_1, u_0_1 = wilson_interval(0, 1, level=0.95)
    assert 0.0 <= l_0_1 <= u_0_1 <= 1.0
    assert math.isfinite(l_0_1) and math.isfinite(u_0_1)

    l_1_1, u_1_1 = wilson_interval(1, 1, level=0.95)
    assert 0.0 <= l_1_1 <= u_1_1 <= 1.0
    assert math.isfinite(l_1_1) and math.isfinite(u_1_1)

    # Hiệu Newcombe với n = 1
    d, low, high = newcombe_difference(1, 1, 0, 1, level=0.95)
    assert math.isfinite(d) and math.isfinite(low) and math.isfinite(high)
    assert -1.0 <= low <= d <= high <= 1.0

    # Hiệu Newcombe với 0 vs 0 và 50 vs 50
    d_00, low_00, high_00 = newcombe_difference(0, 50, 0, 50, level=0.95)
    assert math.isclose(d_00, 0.0, abs_tol=1e-9)
    assert math.isclose(low_00, -high_00, abs_tol=1e-9)


def test_bootstrap_seeded_reproducible() -> None:
    """Kiểm tra tính tái lập bit-bit của bootstrap phân vị theo seed (FR-005, NFR-STAT-001)."""
    data = [0.12, 0.45, 0.78, 0.23, 0.56, 0.89, 0.34, 0.67]

    # Cùng seed cho kết quả giống hệt
    ci1 = bootstrap_mean_ci(data, level=0.95, resamples=1000, seed=42)
    ci2 = bootstrap_mean_ci(data, level=0.95, resamples=1000, seed=42)
    assert ci1 == ci2

    # Giá trị trung bình mẫu nằm trong khoảng tin cậy
    mean_val = float(np.mean(data))
    assert ci1[0] <= mean_val <= ci1[1]

    # Khác seed cho kết quả khác biệt nhẹ
    ci3 = bootstrap_mean_ci(data, level=0.95, resamples=1000, seed=999)
    assert math.isfinite(ci3[0]) and math.isfinite(ci3[1])


def test_verdict_rule_ci_lower_gt_zero() -> None:
    """Kiểm tra quy tắc kết luận better iff ci_low > 0 (INV-006, FR-006, AC-2)."""
    # 50 vs 0: ci_low ≈ 0.899 > 0 -> better = True
    v1 = decide((50, 50), (0, 50), level=0.95)
    assert isinstance(v1, Verdict)
    assert v1.better is True
    assert v1.ci_low > 0.0
    assert v1.method == "newcombe_wilson_hybrid"

    # 20 vs 10: ci_low ≈ 0.020 > 0 -> better = True
    v2 = decide((20, 50), (10, 50), level=0.95)
    assert v2.better is True
    assert v2.ci_low > 0.0

    # 15 vs 8: ci_low ≈ -0.026 <= 0 -> better = False
    v3 = decide((15, 50), (8, 50), level=0.95)
    assert v3.better is False
    assert v3.ci_low <= 0.0

    # 10 vs 10: ci_low ≈ -0.157 <= 0 -> better = False
    v4 = decide((10, 50), (10, 50), level=0.95)
    assert v4.better is False
    assert v4.ci_low <= 0.0

    # 0 vs 0: better = False
    v5 = decide((0, 50), (0, 50), level=0.95)
    assert v5.better is False
    assert v5.ci_low <= 0.0


def test_invalid_parameters_raise_value_error() -> None:
    """Kiểm tra tham số n <= 0, level ngoài (0, 1) hoặc k sai ném ValueError (NFR-STAT-001)."""
    # n <= 0
    with pytest.raises(ValueError, match="n="):
        wilson_interval(0, 0, level=0.95)

    with pytest.raises(ValueError, match="n="):
        wilson_interval(5, -1, level=0.95)

    # level ngoài (0, 1)
    with pytest.raises(ValueError, match="level="):
        wilson_interval(10, 50, level=0.0)

    with pytest.raises(ValueError, match="level="):
        wilson_interval(10, 50, level=1.0)

    with pytest.raises(ValueError, match="level="):
        wilson_interval(10, 50, level=1.5)

    # k < 0 hoặc k > n
    with pytest.raises(ValueError, match="k="):
        wilson_interval(-1, 50, level=0.95)

    with pytest.raises(ValueError, match="k="):
        wilson_interval(51, 50, level=0.95)

    # Newcombe n1, n2 <= 0 hoặc level ngoài (0, 1)
    with pytest.raises(ValueError, match="n1="):
        newcombe_difference(10, 0, 5, 50, level=0.95)

    with pytest.raises(ValueError, match="level="):
        newcombe_difference(10, 50, 5, 50, level=-0.5)

    # Bootstrap mảng rỗng hoặc level sai
    with pytest.raises(ValueError):
        bootstrap_mean_ci([], level=0.95)

    with pytest.raises(ValueError):
        bootstrap_mean_ci([1.0, 2.0], level=1.0)

    with pytest.raises(ValueError):
        bootstrap_mean_ci([1.0, 2.0], resamples=0)


def test_non_integer_k_supported_for_repeated_evals() -> None:
    """Kiểm tra k có thể là số thực khi có nhiều lần lặp repeats > 1 (FR-005, research Q1)."""
    # k = 25.5 khi n = 50
    low, high = wilson_interval(25.5, 50, level=0.95)
    assert 0.0 < low < high < 1.0

    diff, c_low, c_high = newcombe_difference(30.2, 50, 10.4, 50, level=0.95)
    assert math.isclose(diff, (30.2 - 10.4) / 50, abs_tol=1e-9)
    assert c_low < diff < c_high


def test_decide_accepts_various_input_structures() -> None:
    """Kiểm tra decide hỗ trợ linh hoạt tuple, sequence, và PolicyResult (API-EVL-0007)."""
    # Dạng sequence booleans
    learned_seq = [True] * 40 + [False] * 10
    random_seq = [True] * 10 + [False] * 40
    v_seq = decide(learned_seq, random_seq, level=0.95)
    assert v_seq.better is True
    assert math.isclose(v_seq.difference, 0.6, abs_tol=1e-9)

    # Dạng đối tượng có thuộc tính success_rate
    @dataclass
    class DummyStat:
        value: float
        n: int

    @dataclass
    class DummyPolicyResult:
        success_rate: DummyStat
        n_episodes: int

    pol_learned = DummyPolicyResult(success_rate=DummyStat(value=0.8, n=50), n_episodes=50)
    pol_random = DummyPolicyResult(success_rate=DummyStat(value=0.2, n=50), n_episodes=50)
    v_obj = decide(pol_learned, pol_random, level=0.95)
    assert v_obj.better is True
    assert math.isclose(v_obj.difference, 0.6, abs_tol=1e-9)
