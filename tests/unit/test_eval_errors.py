"""Kiểm thử hợp đồng lỗi và phân hệ đánh giá policy (mma_ai.evaluation).

Chứng minh các yêu cầu và bất biến:
- FR-015: CheckpointUnusable mang mã thoát 4 khi checkpoint hỏng hoặc không dùng được.
- FR-018: EvalConfigError mang mã thoát 2 khi cấu hình đánh giá không hợp lệ.
- INV-004: Mã thoát theo đúng hợp đồng CLI (contracts/cli.md) cho từng lỗi miền.
- API-EVL-0002: Các lớp lỗi hỗ trợ điều phối đánh giá policy và giữ nguyên thông điệp tiếng Việt.
- Ranh giới nhập (import boundary): Gói evaluation không nạp trước các phụ thuộc nặng
  như learning.trainer, learning.ppo, torch, matplotlib.
"""

import sys
from typing import Any

import pytest


def _error_type(name: str) -> Any:
    """Nhập trì hoãn (lazy import) để không làm bẩn ranh giới import khi pytest thu thập."""
    from mma_ai.evaluation import errors

    return getattr(errors, name)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("error_name", "expected_code"),
    [
        ("EvalError", 1),
        ("EvalConfigError", 2),
        ("CheckpointUnusable", 4),
        ("LeakageError", 5),
        ("TrainSetUnknown", 5),
        ("LogMissing", 6),
        ("EvalWriteError", 7),
    ],
)
def test_eval_exit_codes_match_contract(error_name: str, expected_code: int) -> None:
    """FR-015, FR-018, INV-004: Mã thoát (exit_code) phải khớp chính xác bảng mã hợp đồng CLI."""
    cls = _error_type(error_name)
    instance = cls("Thông điệp lỗi mẫu cho kiểm thử ngữ cảnh")

    assert issubclass(cls, Exception), f"{error_name} phải là ngoại lệ (subclass của Exception)"
    if error_name != "EvalError":
        base_cls = _error_type("EvalError")
        assert isinstance(instance, base_cls), f"{error_name} phải kế thừa từ EvalError"

    assert instance.exit_code == expected_code, (
        f"Mã thoát của {error_name} phải là {expected_code}, thực tế: {instance.exit_code}"
    )


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "error_name",
    [
        "EvalError",
        "EvalConfigError",
        "CheckpointUnusable",
        "LeakageError",
        "TrainSetUnknown",
        "LogMissing",
        "EvalWriteError",
    ],
)
def test_eval_errors_preserve_vietnamese_message(error_name: str) -> None:
    """API-EVL-0002: Thông điệp tiếng Việt kèm ngữ cảnh, giá trị vi phạm được giữ nguyên."""
    message = f"Lỗi kiểm thử {error_name}: giá trị vi phạm = 0.95 tại đường dẫn runs/test"
    instance = _error_type(error_name)(message)

    assert str(instance) == message, (
        f"Chuỗi biểu diễn str() của {error_name} phải giữ nguyên vẹn thông điệp đầu vào"
    )
    assert instance.message == message, (
        f"Thuộc tính message của {error_name} phải lưu đúng thông điệp"
    )


def test_evaluation_init_does_not_import_heavy_modules() -> None:
    """Kiểm tra gói evaluation.__init__ chỉ chứa docstring tiếng Việt, không nạp module nặng."""
    forbidden_modules = [
        "torch",
        "matplotlib",
        "matplotlib.pyplot",
        "mma_ai.learning.trainer",
        "mma_ai.learning.ppo",
    ]

    # Đảm bảo dọn các module cấm nếu đã vô tình có sẵn
    for mod in forbidden_modules:
        sys.modules.pop(mod, None)

    import mma_ai.evaluation  # noqa: F401

    assert mma_ai.evaluation.__doc__ is not None, (
        "Gói mma_ai.evaluation phải có docstring tiếng Việt"
    )
    assert len(mma_ai.evaluation.__doc__.strip()) > 0, "Docstring không được để trống"

    for mod in forbidden_modules:
        assert mod not in sys.modules, (
            f"Gói mma_ai.evaluation không được tự động nhập mô-đun nặng '{mod}'"
        )


def teardown_module() -> None:
    """Dọn dẹp các module đã nạp để giữ tính độc lập cho các test tiếp theo."""
    sys.modules.pop("mma_ai.evaluation.errors", None)
    sys.modules.pop("mma_ai.evaluation", None)
