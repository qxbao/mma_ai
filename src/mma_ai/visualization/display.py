"""Mô-đun kiểm tra tính khả dụng của màn hình hiển thị (mma_ai.visualization.display).

Cung cấp cấu trúc dữ liệu và hàm kiểm tra trạng thái màn hình:
- FR-011: Phát hiện môi trường không có màn hình (display) và đưa ra gợi ý --headless.
- NFR-HEADLESS-001: Kiểm tra không làm treo (hang) tiến trình, phản hồi nhanh (<= 5 s).
- API-VIS-0008: Hợp đồng hàm display_available() -> DisplayStatus{available, reason}.
- INV-004: Cung cấp thông tin chuẩn xác để xử lý thoát mã lỗi 7 khi thiếu hiển thị.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayStatus:
    """Trạng thái khả dụng của màn hình hiển thị (display availability status).

    Thuộc tính:
        available: Màn hình có khả dụng để mở giao diện đồ họa hay không.
        reason: Thông điệp tiếng Việt giải thích lý do hoặc ghi chú trạng thái.
    """

    available: bool
    reason: str

    def __bool__(self) -> bool:
        """Cho phép đánh giá logic trực tiếp: bool(status) == status.available."""
        return self.available


def display_available() -> DisplayStatus:
    """Kiểm tra xem hệ thống có màn hình hiển thị khả dụng (display available) hay không.

    Hàm sử dụng kỹ thuật nhập lười (lazy import) GLFW để tránh nạp đồ họa ở chế độ không màn hình.
    Thực hiện gọi glfw.init() trong tiến trình và chặn các cảnh báo rò rỉ ra stderr.
    Nếu khởi tạo thành công, lập tức gọi glfw.terminate() để dọn dẹp và trả về trạng thái sẵn sàng.

    Returns:
        DisplayStatus chứa cờ available (bool) và reason (str) bằng tiếng Việt.
    """
    try:
        import glfw  # Nhập lười (lazy import) để không nạp GLFW ở cấp độ mô-đun
    except ImportError as err:
        return DisplayStatus(
            available=False,
            reason=(
                f"Thư viện đồ họa GLFW chưa được cài đặt trong môi trường ({err}). "
                "Vui lòng chạy với cờ chế độ không màn hình (--headless)."
            ),
        )

    # Chặn cảnh báo từ thư viện GLFW để không làm ô nhiễm stderr của tiến trình
    captured_msg = ""
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        try:
            init_res = glfw.init()
            init_ok = bool(init_res)
        except Exception as exc:
            init_ok = False
            captured_msg = str(exc)
        else:
            if captured_warnings:
                captured_msg = str(captured_warnings[0].message)

    if init_ok:
        try:
            glfw.terminate()
        except Exception:
            pass
        return DisplayStatus(
            available=True,
            reason="Màn hình hiển thị khả dụng (display available).",
        )

    # Xây dựng thông điệp giải thích lý do bằng tiếng Việt kèm ngữ cảnh biến môi trường
    display_env = os.environ.get("DISPLAY")
    wayland_env = os.environ.get("WAYLAND_DISPLAY")

    if not display_env and not wayland_env:
        reason = (
            "Không phát hiện màn hình hiển thị: cả hai biến môi trường DISPLAY và WAYLAND_DISPLAY "
            "đều chưa được thiết lập. Vui lòng kiểm tra hoặc dùng chế độ không màn hình "
            "(--headless)."
        )
    else:
        env_parts: list[str] = []
        if display_env is not None:
            env_parts.append(f"DISPLAY='{display_env}'")
        if wayland_env is not None:
            env_parts.append(f"WAYLAND_DISPLAY='{wayland_env}'")
        env_str = ", ".join(env_parts)
        reason = (
            f"Không thể khởi tạo hoặc kết nối tới màn hình hiển thị ({env_str}). "
            "Màn hình có thể bị hỏng, máy chủ X11/Wayland không phản hồi hoặc thiếu quyền. "
            "Vui lòng kiểm tra lại cấu hình hoặc sử dụng chế độ không màn hình (--headless)."
        )

    if captured_msg:
        reason = f"{reason} [Chi tiết: {captured_msg}]"

    return DisplayStatus(available=False, reason=reason)


__all__: list[str] = [
    "DisplayStatus",
    "display_available",
]
