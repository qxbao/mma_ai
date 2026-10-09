"""Kiểm thử hợp đồng lỗi của pipeline huấn luyện."""

import pytest

from mma_ai.learning.errors import (
    CheckpointError,
    CheckpointIOError,
    NonFiniteError,
    RunDirError,
    StageNotImplemented,
    TrainConfigError,
    TrainError,
)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("error_type", "expected_code"),
    [
        (TrainConfigError, 2),
        (StageNotImplemented, 3),
        (CheckpointError, 4),
        (NonFiniteError, 1),
        (CheckpointIOError, 1),
        (RunDirError, 1),
    ],
)
def test_exit_codes_match_contract(error_type: type[TrainError], expected_code: int) -> None:
    """FR-015, FR-017, INV-005: mã thoát phải đúng hợp đồng CLI."""
    error = error_type("Giá trị stage balance không được hỗ trợ")

    assert isinstance(error, TrainError)
    assert error.exit_code == expected_code


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "error_type",
    [
        TrainConfigError,
        StageNotImplemented,
        CheckpointError,
        NonFiniteError,
        CheckpointIOError,
        RunDirError,
    ],
)
def test_errors_carry_vietnamese_context(error_type: type[TrainError]) -> None:
    """INV-005: lỗi giữ nguyên ngữ cảnh tiếng Việt do caller cung cấp."""
    error = error_type("Lượt 7 có đại lượng loss thiếu thành phần optimizer")

    assert "Lượt 7" in str(error)
    assert "loss" in str(error)
    assert "optimizer" in str(error)
