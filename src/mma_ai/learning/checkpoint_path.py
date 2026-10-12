"""Quy tắc thuần để ghi đường dẫn checkpoint vào manifest."""

from __future__ import annotations

from mma_ai.compat.pathrules import to_record_path


def checkpoint_record_path(path: str) -> str:
    """Chuẩn hóa đường dẫn checkpoint thành dạng record tương đối."""
    return to_record_path(path)
