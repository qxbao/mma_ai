"""Kiểm thử hợp đồng lỗi của pipeline huấn luyện."""

from typing import Any

import pytest


def _error_type(name: str) -> Any:
    """Nhập trì hoãn để không làm bẩn ranh giới import khi pytest collection."""
    from mma_ai.learning import errors

    return getattr(errors, name)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("error_name", "expected_code"),
    [
        ("TrainConfigError", 2),
        ("StageNotImplemented", 3),
        ("CheckpointError", 4),
        ("NonFiniteError", 1),
        ("CheckpointIOError", 1),
        ("RunDirError", 1),
    ],
)
def test_exit_codes_match_contract(error_name: str, expected_code: int) -> None:
    """FR-015, FR-017, INV-005: mã thoát phải đúng hợp đồng CLI."""
    error_type = _error_type(error_name)
    error = error_type("Giá trị stage balance không được hỗ trợ")

    assert isinstance(error, _error_type("TrainError"))
    assert error.exit_code == expected_code


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "error_name",
    [
        "TrainConfigError",
        "StageNotImplemented",
        "CheckpointError",
        "NonFiniteError",
        "CheckpointIOError",
        "RunDirError",
    ],
)
def test_errors_carry_vietnamese_context(error_name: str) -> None:
    """INV-005: lỗi giữ nguyên ngữ cảnh tiếng Việt do caller cung cấp."""
    error = _error_type(error_name)("Lượt 7 có đại lượng loss thiếu thành phần optimizer")

    assert "Lượt 7" in str(error)
    assert "loss" in str(error)
    assert "optimizer" in str(error)


def teardown_module() -> None:
    """Dọn module được nhập trì hoãn để giữ độc lập cho boundary test kế tiếp."""
    import sys

    for mod in list(sys.modules):
        if mod == "mma_ai.learning" or mod.startswith("mma_ai.learning."):
            sys.modules.pop(mod, None)
