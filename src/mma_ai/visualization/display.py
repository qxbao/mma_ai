"""Mô-đun kiểm tra tính khả dụng của màn hình hiển thị (mma_ai.visualization.display).

Cung cấp cấu trúc dữ liệu và hàm kiểm tra trạng thái màn hình:
- FR-011: Phát hiện môi trường không có màn hình (display) và đưa ra gợi ý --headless.
- NFR-HEADLESS-001: Kiểm tra không làm treo (hang) tiến trình, phản hồi nhanh (<= 5 s).
- API-VIS-0008: Hợp đồng hàm display_available() -> DisplayStatus{available, reason}.
- INV-004: Cung cấp thông tin chuẩn xác để xử lý thoát mã lỗi 7 khi thiếu hiển thị.
"""

from __future__ import annotations

from dataclasses import dataclass

from mma_ai.compat.display import probe_display


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

    Dùng phép dò chung theo hồ sơ nền tảng và giữ nguyên cấu trúc kết quả của giao diện.

    Returns:
        DisplayStatus chứa cờ available (bool) và reason (str) bằng tiếng Việt.
    """
    result = probe_display()
    return DisplayStatus(available=result.available, reason=result.reason)


__all__: list[str] = [
    "DisplayStatus",
    "display_available",
]
