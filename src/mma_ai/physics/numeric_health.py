"""Mô-đun kiểm tra sức khoẻ số học mô phỏng vật lý (mma_ai.physics.numeric_health).

Cung cấp hàm quét NaN/Inf và đọc cảnh báo MuJoCo:
- FR-006: Phát hiện mất ổn định số học và cảnh báo vật lý.
- INV-004: Ngăn chặn lan truyền giá trị không hữu hạn.
"""

from __future__ import annotations

from typing import Mapping

import mujoco
import numpy as np


def scan_nonfinite(arrays: Mapping[str, np.ndarray]) -> tuple[int, int, str | None]:
    """Quét số lượng giá trị NaN, Inf và xác định đại lượng đầu tiên vi phạm.

    Args:
        arrays: Ánh xạ từ tên đại lượng tới mảng NumPy cần kiểm tra.

    Returns:
        Bộ ba (số NaN, số Inf, tên đại lượng đầu tiên vi phạm hoặc None).
    """
    total_nan = 0
    total_inf = 0
    first_violating_name: str | None = None

    for name, arr in arrays.items():
        nan_count = int(np.isnan(arr).sum())
        inf_count = int(np.isinf(arr).sum())

        if nan_count > 0 or inf_count > 0:
            if first_violating_name is None:
                first_violating_name = name
            total_nan += nan_count
            total_inf += inf_count

    return total_nan, total_inf, first_violating_name


def read_physics_warnings(data: mujoco.MjData) -> int:
    """Đọc tổng số cảnh báo vật lý được ghi nhận trong MjData.warning."""
    total_warnings = 0
    for w in data.warning:
        total_warnings += int(w.number)
    return total_warnings


__all__: list[str] = [
    "read_physics_warnings",
    "scan_nonfinite",
]
