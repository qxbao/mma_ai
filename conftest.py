"""Cấu hình chung cho kiểm thử (pytest fixtures và thiết lập môi trường)."""

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest

pytest_plugins = ["capability_gate"]

# Thiết lập đường dẫn fixture tích hợp dùng chung cho toàn bộ bộ kiểm thử
_INTEGRATION_DIR = str(Path(__file__).resolve().parent / "tests" / "integration")
if _INTEGRATION_DIR not in sys.path:
    sys.path.insert(0, _INTEGRATION_DIR)
_UNIT_DIR = str(Path(__file__).resolve().parent / "tests" / "unit")
if _UNIT_DIR not in sys.path:
    sys.path.insert(0, _UNIT_DIR)


@pytest.fixture(autouse=True)
def _isolate_display_env(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Generator[None, None, None]:
    """Cô lập biến hiển thị và ép phép dò thất bại nếu test không yêu cầu màn hình."""
    if "display" in request.keywords:
        yield
        return

    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("MMA_AI_FORCE_NO_DISPLAY", "1")
    yield
