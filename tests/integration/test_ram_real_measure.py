"""Kiểm tra số đo RAM bằng mức cấp phát thật trên tiến trình."""

from __future__ import annotations

from mma_ai.compat.memory import peak_ram_mb


def test_ac_2_inv_002_inv_007_real_peak_grows_by_allocation_within_band() -> None:
    """AC-2, INV-002, INV-007: cấp phát 256 MiB làm RAM đỉnh tăng trong biên đo."""
    before = peak_ram_mb()
    assert before is not None

    allocation = bytearray(256 * 1024 * 1024)
    for offset in range(0, len(allocation), 4096):
        allocation[offset] = 1

    after = peak_ram_mb()
    assert after is not None
    increase = after - before
    assert 230.4 <= increase <= 332.8
    del allocation
