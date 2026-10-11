"""Kiểm thử API-PLT-0007, FR-013, NFR-ENC-001 và AC-4."""

# Trace: API-PLT-0007 / FR-013 / NFR-ENC-001 / AC-4

from __future__ import annotations

import sys

from pytest import MonkeyPatch

from mma_ai.compat.stdio import ensure_utf8_stdio


class ConfigurableStream:
    def __init__(self) -> None:
        self.encoding = "ascii"
        self.errors = "strict"

    def reconfigure(self, *, encoding: str, errors: str) -> None:
        self.encoding = encoding
        self.errors = errors


class FailingStream:
    def reconfigure(self, *, encoding: str, errors: str) -> None:
        raise OSError("luồng đã đóng")


def test_reconfigure_sets_utf8_replace(monkeypatch: MonkeyPatch) -> None:
    """AC-4: Hai luồng mặc định nhận bảng mã và cách xử lý lỗi đã chốt."""
    stdout = ConfigurableStream()
    stderr = ConfigurableStream()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", stdout)
        patch.setattr(sys, "stderr", stderr)
        ensure_utf8_stdio()

    assert (stdout.encoding, stdout.errors) == ("utf-8", "replace")
    assert (stderr.encoding, stderr.errors) == ("utf-8", "replace")


def test_stream_without_reconfigure_is_ignored() -> None:
    """API-PLT-0007: Luồng thiếu hỗ trợ hoặc từ chối cấu hình không cản luồng còn lại."""
    supported = ConfigurableStream()

    ensure_utf8_stdio((object(), FailingStream(), supported))
    assert (supported.encoding, supported.errors) == ("utf-8", "replace")


def test_idempotent() -> None:
    """FR-013: Gọi lặp vẫn để luồng ở cùng cấu hình."""
    stream = ConfigurableStream()

    ensure_utf8_stdio((stream,))
    first = (stream.encoding, stream.errors)
    ensure_utf8_stdio((stream,))

    assert first == ("utf-8", "replace")
    assert (stream.encoding, stream.errors) == first
