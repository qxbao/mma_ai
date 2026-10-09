"""Cấu hình chung cho kiểm thử (pytest fixtures và thiết lập môi trường)."""

from typing import Generator

import pytest


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
