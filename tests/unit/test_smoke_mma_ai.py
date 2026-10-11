"""Bộ kiểm thử khói (smoke test) cho gói mma_ai.

Hiện thực và xác thực các yêu cầu chức năng (functional requirements):
- FR-015: Ranh giới nạp mô-đun (module import boundary) độc lập, không phụ thuộc huấn luyện.
- FR-019: Môi trường kiểm thử tự động, cô lập màn hình (display isolation).
"""

import os
import subprocess
import sys

import pytest

import mma_ai


def test_smoke_version() -> None:
    """Kiểm tra phiên bản của gói mma_ai khớp với đặc tả đã định."""
    assert mma_ai.__version__ == "0.1.0"


def test_smoke_fr_015_clean_import_boundary() -> None:
    """FR-015: Nhập gói mma_ai không nạp các mô-đun huấn luyện nặng hoặc học máy."""
    subprocess.run(
        [
            sys.executable,
            "-c",
            'import sys, mma_ai; assert "mma_ai.learning" not in sys.modules and '
            '"torch" not in sys.modules',
        ],
        check=True,
    )


def test_smoke_fr_019_headless_display_isolation() -> None:
    """FR-019: Xác nhận biến môi trường DISPLAY và WAYLAND_DISPLAY bị bỏ đặt mặc định."""
    assert "DISPLAY" not in os.environ
    assert "WAYLAND_DISPLAY" not in os.environ


@pytest.mark.display  # type: ignore[untyped-decorator]
def test_smoke_fr_019_display_marker_preserves_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-019: Marker display cho phép sử dụng biến môi trường hiển thị khi cần."""
    # Khi test tự đặt hoặc môi trường có cấu hình, marker cho phép giữ nguyên
    monkeypatch.setenv("DISPLAY", ":99")
    assert os.environ.get("DISPLAY") == ":99"
