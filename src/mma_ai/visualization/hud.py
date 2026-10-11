"""Mô-đun hiển thị thông số HUD (heads-up display) cho phân hệ trực quan hoá 3D.

Định danh mô-đun: mma_ai.visualization.hud.

Hiện thực:
- FR-005: Hiển thị 6 giá trị kích hoạt cơ (muscle activation) kèm tên cơ và thanh trực quan.
- FR-012: Hiển thị cảnh báo lệch mô hình (model mismatch warning) "MÔ HÌNH LỆCH" khi phát hiện.
- INV-006: Làm tròn số chỉ phục vụ hiển thị trên giao diện, bảo toàn dữ liệu gốc không bị thay đổi.
- API-VIS-0012: Hàm hud_lines(activation, muscle_names, cfg, warning=None) -> list[str].
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

    ActivationInput = Sequence[float] | NDArray[np.floating[Any]]
else:
    ActivationInput = Any


def _extract_hud_params(cfg: Any) -> tuple[int, int]:
    """Trích xuất tham số decimals và bar_width từ đối tượng cấu hình hoặc từ điển."""
    hud_obj = getattr(cfg, "hud", cfg)
    decimals_raw: Any = getattr(hud_obj, "decimals", None)
    bar_width_raw: Any = getattr(hud_obj, "bar_width", None)

    if decimals_raw is None or bar_width_raw is None:
        if isinstance(cfg, dict):
            sub_dict = cfg.get("hud", cfg)
            if isinstance(sub_dict, dict):
                decimals_raw = sub_dict.get("decimals", 3)
                bar_width_raw = sub_dict.get("bar_width", 10)
            else:
                decimals_raw = getattr(sub_dict, "decimals", 3)
                bar_width_raw = getattr(sub_dict, "bar_width", 10)
        else:
            decimals_raw = 3
            bar_width_raw = 10

    decimals_val: int = 3
    bar_width_val: int = 10
    if decimals_raw is not None:
        try:
            decimals_val = int(decimals_raw)
        except (TypeError, ValueError):
            pass
    if bar_width_raw is not None:
        try:
            bar_width_val = int(bar_width_raw)
        except (TypeError, ValueError):
            pass

    return max(0, decimals_val), max(0, bar_width_val)


def hud_lines(
    activation: ActivationInput,
    muscle_names: Sequence[str],
    cfg: Any,
    warning: str | bool | None = None,
) -> list[str]:
    """Sinh danh sách các dòng chuỗi hiển thị HUD (API-VIS-0012).

    Bảo toàn bất biến INV-006: việc làm tròn chỉ thực hiện trên chuỗi ký tự hiển thị,
    không chỉnh sửa mảng kích hoạt cơ gốc.

    Args:
        activation: Chuỗi các giá trị kích hoạt cơ trong đoạn [0, 1].
        muscle_names: Chuỗi tên định danh của các cơ tương ứng.
        cfg: Cấu hình phát lại hoặc cấu hình HUD (ReplayConfig, HudConfig, hoặc dict).
        warning: Thông điệp cảnh báo tuỳ chọn (ví dụ: cờ cảnh báo lệch mô hình).

    Returns:
        Danh sách các dòng chuỗi văn bản hiển thị trên HUD.

    Raises:
        ValueError: Khi độ dài chuỗi activation và muscle_names không bằng nhau.
    """
    if len(activation) != len(muscle_names):
        raise ValueError(
            f"Số lượng activation ({len(activation)}) "
            f"không khớp với số tên cơ ({len(muscle_names)})."
        )

    decimals, bar_width = _extract_hud_params(cfg)
    lines: list[str] = []

    for name, act in zip(muscle_names, activation):
        val_str = f"{float(act):.{decimals}f}"
        if bar_width > 0:
            clamped_act = max(0.0, min(1.0, float(act)))
            filled_len = int(round(clamped_act * bar_width))
            filled_len = max(0, min(bar_width, filled_len))
            empty_len = bar_width - filled_len
            bar = "█" * filled_len + " " * empty_len
            lines.append(f"{name}: {val_str} [{bar}]")
        else:
            lines.append(f"{name}: {val_str}")

    if warning is not None and warning is not False:
        if isinstance(warning, str):
            if warning.strip():
                lines.append(warning)
        elif isinstance(warning, (list, tuple, set)):
            for item in warning:
                if item:
                    lines.append(str(item))
        elif warning is True:
            lines.append("MÔ HÌNH LỆCH")
        else:
            lines.append(str(warning))

    return lines
