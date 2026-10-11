"""Cấu hình đầu ra chuẩn theo API-PLT-0007."""

# Trace: API-PLT-0007 / FR-013 / NFR-ENC-001 / AC-4

from __future__ import annotations

import sys
from collections.abc import Iterable


def ensure_utf8_stdio(streams: Iterable[object] | None = None) -> None:
    """Đặt UTF-8 cho các luồng đầu ra nếu luồng cho phép."""
    selected = (sys.stdout, sys.stderr) if streams is None else streams
    try:
        for stream in selected:
            try:
                configure = getattr(stream, "reconfigure", None)
                if callable(configure):
                    configure(encoding="utf-8", errors="replace")
            except Exception:
                continue
    except Exception:
        return
