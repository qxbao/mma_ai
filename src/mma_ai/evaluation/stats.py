"""Các hàm thống kê giải tích và tái lập cho phân hệ đánh giá policy (API-EVL-0007).

Hiện thực:
- FR-005: Khoảng tin cậy Wilson score và Newcombe (phương pháp 10) giải tích,
  bootstrap phân vị có seed.
- FR-006: Quy tắc kết luận 'tốt hơn' khi và chỉ khi cận dưới khoảng tin cậy của hiệu lớn hơn 0.
- NFR-STAT-001: Tính đúng của khoảng tin cậy và kết luận trên dữ liệu tổng hợp.
- INV-006: Tiêu chí so sánh khai trước và bất biến với kết quả.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True)
class Verdict:
    """Kết luận so sánh giữa policy đã học và random policy (INV-006, FR-006)."""

    better: bool
    difference: float
    ci_low: float
    ci_high: float
    method: str = "newcombe_wilson_hybrid"


def _check_level(level: float) -> None:
    """Xác thực mức tin cậy nằm trong khoảng mở (0, 1) (FR-005)."""
    if not math.isfinite(level) or level <= 0.0 or level >= 1.0:
        raise ValueError(f"Mức tin cậy level={level} phải nằm trong khoảng (0, 1).")


def _check_n_k(n: int, k: float | int, name_prefix: str = "") -> None:
    """Xác thực kích thước mẫu n > 0 và số đếm thành công k trong [0, n] (NFR-STAT-001)."""
    pfx_n = f"n{name_prefix}" if name_prefix else "n"
    pfx_k = f"k{name_prefix}" if name_prefix else "k"
    if n <= 0:
        raise ValueError(f"Số lượng mẫu {pfx_n}={n} phải lớn hơn 0.")
    if not math.isfinite(k) or k < 0.0 or k > n:
        raise ValueError(f"Số lượng thành công {pfx_k}={k} phải nằm trong đoạn [0, {pfx_n}={n}].")


def wilson_interval(k: float | int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Tính khoảng tin cậy Wilson score cho tỷ lệ mẫu (FR-005, NFR-STAT-001).

    Tham số:
        k: Số lần thành công (có thể là số thực khi có nhiều lần lặp repeats > 1).
        n: Tổng số lần thử hoặc số mục tiêu đánh giá (n > 0).
        level: Mức tin cậy danh định trong khoảng (0, 1), mặc định 0.95.

    Trả về:
        (low, high): Cận dưới và cận trên của khoảng tin cậy tỷ lệ, nằm trong [0, 1].
    """
    _check_level(level)
    _check_n_k(n, k)

    p = float(k) / float(n)
    z = statistics.NormalDist().inv_cdf((1.0 + level) / 2.0)
    z2 = z * z
    denom = 1.0 + z2 / float(n)
    center = (p + z2 / (2.0 * float(n))) / denom
    margin = (z / denom) * math.sqrt(p * (1.0 - p) / float(n) + z2 / (4.0 * float(n) * float(n)))

    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return float(low), float(high)


def newcombe_difference(
    k1: float | int, n1: int, k2: float | int, n2: int, level: float = 0.95
) -> tuple[float, float, float]:
    """Tính khoảng tin cậy Newcombe phương pháp 10 cho hiệu hai tỷ lệ (FR-005, NFR-STAT-001).

    Sử dụng kết hợp khoảng tin cậy Wilson score độc lập cho hai tỷ lệ (Wilson hỗn hợp):
    d = p1 - p2
    low = d - sqrt((p1 - l1)^2 + (u2 - p2)^2)
    high = d + sqrt((u1 - p1)^2 + (p2 - l2)^2)

    Tham số:
        k1, n1: Số thành công và kích thước mẫu của nhóm 1 (policy đã học).
        k2, n2: Số thành công và kích thước mẫu của nhóm 2 (random policy).
        level: Mức tin cậy danh định trong khoảng (0, 1), mặc định 0.95.

    Trả về:
        (difference, ci_low, ci_high): Hiệu tỷ lệ và hai cận khoảng tin cậy trong [-1, 1].
    """
    _check_level(level)
    _check_n_k(n1, k1, name_prefix="1")
    _check_n_k(n2, k2, name_prefix="2")

    p1 = float(k1) / float(n1)
    p2 = float(k2) / float(n2)
    d = p1 - p2

    l1, u1 = wilson_interval(k1, n1, level)
    l2, u2 = wilson_interval(k2, n2, level)

    low = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    high = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)

    low = max(-1.0, low)
    high = min(1.0, high)
    return float(d), float(low), float(high)


def bootstrap_mean_ci(
    x: Sequence[float] | np.ndarray,
    level: float = 0.95,
    resamples: int = 10000,
    seed: int = 12345,
) -> tuple[float, float]:
    """Tính khoảng tin cậy bootstrap phân vị cho trung bình mẫu có seed (FR-005, NFR-STAT-001).

    Tham số:
        x: Dãy hoặc mảng một chiều các giá trị thực hữu hạn.
        level: Mức tin cậy danh định trong khoảng (0, 1), mặc định 0.95.
        resamples: Số lần lấy mẫu lại có hoàn lại, mặc định 10000.
        seed: Hạt giống ngẫu nhiên đảm bảo tính tái lập tuyệt đối.

    Trả về:
        (low, high): Cận dưới và cận trên phân vị của phân phối trung bình bootstrap.
    """
    _check_level(level)
    if resamples <= 0:
        raise ValueError(f"Số lần lấy mẫu resamples={resamples} phải lớn hơn 0.")

    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError("Tập dữ liệu x phải là mảng một chiều không rỗng.")
    if not np.all(np.isfinite(arr)):
        raise ValueError("Tập dữ liệu x chứa giá trị không hữu hạn (NaN hoặc Inf).")

    n = len(arr)
    if n == 1:
        val = float(arr[0])
        return val, val

    rng = np.random.default_rng(seed)
    boot_indices = rng.integers(0, n, size=(resamples, n))
    boot_means = np.mean(arr[boot_indices], axis=1)

    alpha = 1.0 - level
    low_pct = 100.0 * (alpha / 2.0)
    high_pct = 100.0 * (1.0 - alpha / 2.0)
    low, high = np.percentile(boot_means, [low_pct, high_pct])

    return float(low), float(high)


def _extract_k_n(obj: Any) -> tuple[float, int]:
    """Trích xuất cặp (k, n) từ nhiều cấu trúc dữ liệu chính sách khác nhau (API-EVL-0007)."""
    if isinstance(obj, tuple) and len(obj) == 2:
        k_val, n_val = obj
        return float(k_val), int(n_val)

    if hasattr(obj, "k") and hasattr(obj, "n"):
        return float(obj.k), int(obj.n)

    if hasattr(obj, "success_rate"):
        sr = obj.success_rate
        n_val = getattr(obj, "n_episodes", None) or getattr(sr, "n", None)
        if n_val is None:
            raise ValueError("Không tìm thấy kích thước mẫu n trong đối tượng chính sách.")
        if hasattr(sr, "k"):
            return float(sr.k), int(n_val)
        val = getattr(sr, "value", None)
        if val is None:
            raise ValueError("Chỉ số success_rate không có giá trị hợp lệ.")
        return float(val * n_val), int(n_val)

    if isinstance(obj, dict):
        if "k" in obj and "n" in obj:
            return float(obj["k"]), int(obj["n"])
        if "success_rate" in obj and isinstance(obj["success_rate"], dict):
            sr_dict = obj["success_rate"]
            n_dict = obj.get("n_episodes", sr_dict.get("n"))
            if n_dict is None:
                raise ValueError("Không tìm thấy kích thước mẫu n trong cấu trúc dict.")
            if "k" in sr_dict:
                return float(sr_dict["k"]), int(n_dict)
            val_dict = sr_dict.get("value")
            if val_dict is None:
                raise ValueError("Chỉ số success_rate trong dict không có giá trị.")
            return float(val_dict * n_dict), int(n_dict)

    if isinstance(obj, (list, np.ndarray)) or (isinstance(obj, tuple) and len(obj) != 2):
        arr = np.asarray(obj, dtype=np.float64)
        if arr.size == 0:
            raise ValueError("Dãy kết quả chính sách không được rỗng.")
        return float(np.sum(arr)), int(len(arr))

    raise ValueError(f"Không thể trích xuất (k, n) từ đối tượng kiểu {type(obj)}.")


def decide(learned: Any, random: Any, level: float = 0.95) -> Verdict:
    """Đưa ra kết luận policy học được có tốt hơn random policy hay không (FR-006, INV-006).

    Quy tắc kết luận cốt lõi:
    better <=> ci_low > 0
    (cận dưới khoảng tin cậy Newcombe của hiệu tỷ lệ thành công lớn hơn 0).
    """
    k1, n1 = _extract_k_n(learned)
    k2, n2 = _extract_k_n(random)

    diff, ci_low, ci_high = newcombe_difference(k1, n1, k2, n2, level=level)
    better = bool(ci_low > 0.0)

    return Verdict(
        better=better,
        difference=diff,
        ci_low=ci_low,
        ci_high=ci_high,
        method="newcombe_wilson_hybrid",
    )


__all__: list[str] = [
    "Verdict",
    "bootstrap_mean_ci",
    "decide",
    "newcombe_difference",
    "wilson_interval",
]
