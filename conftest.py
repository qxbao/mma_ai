"""Cấu hình chung cho kiểm thử (pytest fixtures và thiết lập môi trường)."""

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest

# Thiết lập đường dẫn fixture tích hợp dùng chung cho toàn bộ bộ kiểm thử
_INTEGRATION_DIR = str(Path(__file__).resolve().parent / "tests" / "integration")
if _INTEGRATION_DIR not in sys.path:
    sys.path.insert(0, _INTEGRATION_DIR)


@pytest.fixture(autouse=True)
def _isolate_display_env(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Generator[None, None, None]:
    """Bỏ đặt DISPLAY và WAYLAND_DISPLAY cho mọi test trừ khi test tự bật."""
    if "display" in request.keywords:
        yield
        return

    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    yield
