"""Kiểm thử đơn vị (unit test) cho gói lỗi phát lại và hiển thị (mma_ai.visualization.errors).

Các kiểm thử chứng minh các yêu cầu và bất biến:
- FR-013: Định nghĩa các lớp lỗi khi episode hoặc checkpoint không hợp lệ hoặc không đọc được.
- FR-015: Ranh giới nhập mô-đun (import boundary) không phụ thuộc mã huấn luyện hay đồ hoạ nặng.
- FR-018: Thông điệp lỗi hỗ trợ tiếng Việt (Vietnamese) kèm ngữ cảnh cụ thể.
- INV-004: Mọi lỗi thuộc phân hệ phát lại đều mang mã thoát khác 0 (non-zero exit code).
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Type

import pytest

from mma_ai.visualization.errors import (
    CheckpointUnusable,
    DemoUnstable,
    DisplayUnavailable,
    EpisodeInvalid,
    EpisodeNotFound,
    EpisodeWriteError,
    ModelMismatch,
    ReplayConfigError,
    ReplayError,
)

ALL_ERROR_CLASSES: list[Type[ReplayError]] = [
    ReplayConfigError,
    EpisodeNotFound,
    EpisodeInvalid,
    EpisodeWriteError,
    CheckpointUnusable,
    ModelMismatch,
    DisplayUnavailable,
    DemoUnstable,
]


def test_errors_subclass_hierarchy() -> None:
    """FR-013: Xác nhận tất cả các lớp lỗi cụ thể đều kế thừa từ ReplayError và Exception."""
    assert issubclass(ReplayError, Exception)
    for err_cls in ALL_ERROR_CLASSES:
        assert issubclass(err_cls, ReplayError), f"{err_cls.__name__} phải kế thừa từ ReplayError"
        assert issubclass(err_cls, Exception), f"{err_cls.__name__} phải kế thừa từ Exception"


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("err_cls", "expected_exit_code"),
    [
        (ReplayConfigError, 2),
        (EpisodeNotFound, 5),
        (EpisodeInvalid, 5),
        (EpisodeWriteError, 8),
        (CheckpointUnusable, 4),
        (ModelMismatch, 6),
        (DisplayUnavailable, 7),
        (DemoUnstable, 1),
        (ReplayError, 1),
    ],
)
def test_inv_004_exit_codes(err_cls: Type[ReplayError], expected_exit_code: int) -> None:
    """INV-004: Kiểm tra thuộc tính exit_code khớp chuẩn bảng mã thoát hợp đồng cli.md."""
    assert err_cls.exit_code == expected_exit_code
    instance = err_cls("Thông điệp thử nghiệm")
    assert instance.exit_code == expected_exit_code


def test_inv_004_all_exit_codes_nonzero() -> None:
    """INV-004: Bất biến mã thoát khác 0 cho toàn bộ ngoại lệ phát lại (replay exceptions)."""
    valid_cli_codes = {1, 2, 4, 5, 6, 7, 8}
    for err_cls in ALL_ERROR_CLASSES:
        assert err_cls.exit_code in valid_cli_codes
        assert err_cls.exit_code != 0


def test_fr_018_vietnamese_message_and_context() -> None:
    """FR-018: Ngoại lệ lưu trữ và hiển thị thông điệp tiếng Việt kèm ngữ cảnh (context)."""
    context_msg = "Không tìm thấy tệp episode tại đường dẫn tương đối: runs/001/eval.episode.json"
    err = EpisodeNotFound(context_msg)
    assert str(err) == context_msg
    assert err.message == context_msg


def test_fr_015_clean_import_boundary() -> None:
    """FR-015: Nhập mma_ai.visualization không kéo theo thư viện học máy hoặc viewer nặng."""
    env = os.environ.copy()
    src_dir = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONPATH"] = f"{src_dir}:{env.get('PYTHONPATH', '')}".rstrip(":")
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, mma_ai.visualization\n"
            "assert mma_ai.visualization.__doc__ is not None\n"
            "assert len(mma_ai.visualization.__doc__.strip()) > 0\n"
            "assert 'mujoco.viewer' not in sys.modules\n"
            "assert 'glfw' not in sys.modules\n"
            "assert 'torch' not in sys.modules\n"
            "assert 'mma_ai.learning' not in sys.modules\n",
        ],
        env=env,
        check=True,
    )
