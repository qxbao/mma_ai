"""Các lớp ngoại lệ cho phân hệ hiển thị và phát lại 3D (mma_ai.visualization).

Định nghĩa các lớp lỗi và mã thoát dòng lệnh (exit code) tương ứng theo hợp đồng CLI:
- FR-013: Báo lỗi khi episode hoặc checkpoint không hợp lệ hoặc thiếu thành phần.
- FR-018: Hỗ trợ thông điệp tiếng Việt (Vietnamese) kèm giá trị và ngữ cảnh (context).
- INV-004: Thoát mã lỗi khác 0 khi phát sinh sự cố, không để lại trạng thái dở dang.
"""
from __future__ import annotations

from typing import Any


class ReplayError(Exception):
    """Lớp ngoại lệ cơ sở (base exception) cho phân hệ phát lại và hiển thị mô phỏng 3D.

    Thuộc tính exit_code xác định mã thoát trả về khi chạy dòng lệnh.
    """

    exit_code: int = 1

    def __init__(self, message: str = "") -> None:
        """Khởi tạo ngoại lệ với thông điệp lỗi tiếng Việt kèm ngữ cảnh."""
        super().__init__(message)
        self.message: str = message


class ReplayConfigError(ReplayError):
    """Lỗi cấu hình hoặc tham số dòng lệnh (command-line argument) không hợp lệ (mã thoát 2)."""

    exit_code: int = 2


class CheckpointUnusable(ReplayError):
    """Lỗi checkpoint không dùng được, không tồn tại hoặc sai cấu trúc mạng (mã thoát 4)."""

    exit_code: int = 4


class EpisodeNotFound(ReplayError):
    """Lỗi không tìm thấy tệp episode đã lưu tại đường dẫn chỉ định (mã thoát 5)."""

    exit_code: int = 5


class EpisodeInvalid(ReplayError):
    """Lỗi nội dung episode hỏng, sai khuôn lược đồ hoặc giá trị không hợp lệ (mã thoát 5)."""

    exit_code: int = 5


class ModelMismatch(ReplayError):
    """Lỗi lệch mô hình mô phỏng giữa episode và môi trường hiện tại (mã thoát 6)."""

    exit_code: int = 6


class DisplayUnavailable(ReplayError):
    """Lỗi không tìm thấy màn hình hiển thị hoặc không thể khởi tạo viewer đồ họa (mã thoát 7)."""

    exit_code: int = 7


class EpisodeWriteError(ReplayError):
    """Lỗi không thể ghi tệp episode ra ổ đĩa do trùng lặp hoặc lỗi phân quyền (mã thoát 8)."""

    exit_code: int = 8


class DemoUnstable(ReplayError):
    """Lỗi mô phỏng demo mất ổn định số học hoặc vật lý trong quá trình chạy (mã thoát 1)."""

    exit_code: int = 1

    def __init__(self, message: str = "", episode: Any = None) -> None:
        """Khởi tạo ngoại lệ kèm bản ghi episode dở dang (nếu có)."""
        super().__init__(message)
        self.episode = episode


__all__: list[str] = [
    "CheckpointUnusable",
    "DemoUnstable",
    "DisplayUnavailable",
    "EpisodeInvalid",
    "EpisodeNotFound",
    "EpisodeWriteError",
    "ModelMismatch",
    "ReplayConfigError",
    "ReplayError",
]
