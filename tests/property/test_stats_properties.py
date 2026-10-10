"""Kiểm thử đặc tính (property-based) cho phân hệ thống kê (NFR-STAT-001, INV-006).

Xác minh các bất biến trên không gian tham số ngẫu nhiên lớn:
- NFR-STAT-001: Khoảng tin cậy Wilson và Newcombe luôn hữu hạn và nằm trong miền giá trị hợp lệ.
- INV-006: Quy tắc kết luận better luôn tương đương chính xác với ci_low > 0.
"""

from __future__ import annotations

import math
import random

from mma_ai.evaluation.stats import decide, newcombe_difference, wilson_interval


def test_nfr_stat_001_wilson_always_in_unit_interval_and_finite() -> None:
    """NFR-STAT-001: Khoảng Wilson cho 300 mẫu ngẫu nhiên luôn hữu hạn và thuộc [0, 1]."""
    rng = random.Random(20261010)
    for _ in range(300):
        n = rng.randint(1, 500)
        # Hỗ trợ k nguyên hoặc thực (repeats > 1)
        k = rng.uniform(0.0, float(n)) if rng.random() < 0.5 else float(rng.randint(0, n))
        level = rng.uniform(0.01, 0.99)

        low, high = wilson_interval(k, n, level=level)

        assert math.isfinite(low) and math.isfinite(high)
        assert 0.0 <= low <= high <= 1.0
        # Tỷ lệ mẫu p = k / n phải nằm trong hoặc bằng cận
        p = k / n
        assert low <= p + 1e-12
        assert high >= p - 1e-12


def test_nfr_stat_001_newcombe_always_bounded_and_finite() -> None:
    """NFR-STAT-001: Khoảng Newcombe cho 300 mẫu ngẫu nhiên luôn hữu hạn và thuộc [-1, 1]."""
    rng = random.Random(20261011)
    for _ in range(300):
        n1 = rng.randint(1, 200)
        n2 = rng.randint(1, 200)
        k1 = float(rng.randint(0, n1))
        k2 = float(rng.randint(0, n2))
        level = rng.uniform(0.05, 0.99)

        diff, low, high = newcombe_difference(k1, n1, k2, n2, level=level)

        assert math.isfinite(diff) and math.isfinite(low) and math.isfinite(high)
        assert -1.0 <= low <= high <= 1.0
        assert low <= diff + 1e-12
        assert high >= diff - 1e-12


def test_inv_006_verdict_better_iff_ci_low_gt_zero() -> None:
    """INV-006: Bất biến better <=> ci_low > 0 luôn đúng trên 300 trường hợp ngẫu nhiên."""
    rng = random.Random(20261012)
    for _ in range(300):
        n1 = rng.randint(1, 100)
        n2 = rng.randint(1, 100)
        k1 = rng.randint(0, n1)
        k2 = rng.randint(0, n2)
        level = rng.uniform(0.5, 0.99)

        v = decide((k1, n1), (k2, n2), level=level)
        assert v.better == (v.ci_low > 0.0)
        assert v.difference == (k1 / n1 - k2 / n2)
        assert v.method == "newcombe_wilson_hybrid"
