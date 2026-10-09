"""Kiểm thử đơn vị (unit test) cho tính khả dụng màn hình (mma_ai.visualization.display).

Các kiểm thử chứng minh yêu cầu, hợp đồng và bất biến:
- FR-011: Báo lỗi tiếng Việt nêu nguyên nhân và gợi ý --headless khi không có màn hình.
- NFR-HEADLESS-001: Đường kiểm tra không màn hình không treo, không crash, phản hồi nhanh (<= 5 s).
- API-VIS-0008: Hợp đồng hàm display_available() -> DisplayStatus{available, reason}.
- AC-3: Môi trường không có màn hình hoặc màn hình hỏng phản hồi rõ lý do và gợi ý --headless.
- INV-004: Cung cấp đầy đủ thông tin lỗi để thoát mã 7 mà không để lại trạng thái dở dang.
"""

from __future__ import annotations

import sys
import time
from dataclasses import FrozenInstanceError
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from mma_ai.visualization.display import DisplayStatus, display_available


@pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
def _clean_glfw_module() -> Generator[None, None, None]:
    """Dọn dẹp glfw khỏi sys.modules sau mỗi test để bảo đảm tính cô lập (test isolation)."""
    yield
    sys.modules.pop("glfw", None)
    for mod in list(sys.modules.keys()):
        if mod.startswith("glfw."):
            sys.modules.pop(mod, None)


def test_display_status_dataclass_contract() -> None:
    """API-VIS-0008: Kiểm tra cấu trúc dữ liệu DisplayStatus và tính bất biến (immutable)."""
    status_ok = DisplayStatus(available=True, reason="Khả dụng")
    assert status_ok.available is True
    assert status_ok.reason == "Khả dụng"
    assert bool(status_ok) is True

    status_fail = DisplayStatus(available=False, reason="Không khả dụng")
    assert status_fail.available is False
    assert status_fail.reason == "Không khả dụng"
    assert bool(status_fail) is False

    # Kiểm tra tính bất biến (frozen dataclass)
    with pytest.raises(FrozenInstanceError):
        status_ok.available = False  # type: ignore[misc]


def test_unavailable_reports_reason_without_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-011, NFR-HEADLESS-001, API-VIS-0008, AC-3: Biến hiển thị bỏ đặt và DISPLAY hỏng.

    Xác nhận không treo (hang), không sập tiến trình (crash), và lý do (reason) bằng tiếng Việt
    chứa gợi ý chế độ không màn hình (--headless).
    """
    # Ca 1: Cả DISPLAY và WAYLAND_DISPLAY đều bị bỏ đặt (unset)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    status_unset = display_available()
    assert status_unset.available is False
    assert bool(status_unset) is False
    assert isinstance(status_unset.reason, str)
    assert len(status_unset.reason) > 0
    assert "--headless" in status_unset.reason
    assert "màn hình" in status_unset.reason.lower()

    # Ca 2: DISPLAY giả lập hỏng hoặc trỏ tới cổng không tồn tại (:99)
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    status_bogus = display_available()
    assert status_bogus.available is False
    assert bool(status_bogus) is False
    assert isinstance(status_bogus.reason, str)
    assert "--headless" in status_bogus.reason
    assert ":99" in status_bogus.reason


def test_nfr_headless_001_fast_response_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """NFR-HEADLESS-001, AC-3: Thời gian thực thi kiểm tra màn hình hoàn thành trong <= 5 giây."""
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    start_time = time.perf_counter()
    status = display_available()
    elapsed = time.perf_counter() - start_time

    assert status.available is False
    # Ngưỡng phi chức năng NFR-HEADLESS-001 là <= 5.0 s (thực tế chạy thường < 0.1 s)
    assert elapsed <= 5.0, (
        f"Thời gian thực thi {elapsed:.4f} s vượt quá ngưỡng 5.0 s của NFR-HEADLESS-001"
    )


def test_glfw_import_error_handled_gracefully() -> None:
    """FR-011, INV-004: Xử lý nhẹ nhàng khi thư viện đồ họa GLFW không được cài đặt."""
    with patch.dict(sys.modules, {"glfw": None}):
        status = display_available()
        assert status.available is False
        assert bool(status) is False
        assert "--headless" in status.reason
        assert "GLFW" in status.reason or "glfw" in status.reason


def test_display_available_when_glfw_succeeds() -> None:
    """API-VIS-0008, FR-011: Khởi tạo thành công trả về available=True và gọi glfw.terminate()."""
    mock_glfw = MagicMock()
    mock_glfw.init.return_value = 1

    with patch.dict(sys.modules, {"glfw": mock_glfw}):
        status = display_available()
        assert status.available is True
        assert bool(status) is True
        assert "khả dụng" in status.reason.lower() or "available" in status.reason.lower()
        mock_glfw.terminate.assert_called_once()


def test_lazy_import_boundary() -> None:
    """FR-015: Nhập mô-đun display không được nạp thư viện glfw ở cấp độ mô-đun (top-level)."""
    saved_glfw = sys.modules.pop("glfw", None)
    try:
        if "mma_ai.visualization.display" in sys.modules:
            del sys.modules["mma_ai.visualization.display"]

        # Nhập mô-đun display
        import mma_ai.visualization.display  # noqa: F401

        # Xác nhận glfw chưa bị nạp tự động vào sys.modules
        assert "glfw" not in sys.modules, "display.py không được nhập glfw ở cấp độ mô-đun"
    finally:
        if saved_glfw is not None:
            sys.modules["glfw"] = saved_glfw
