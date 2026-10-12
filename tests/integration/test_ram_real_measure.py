"""Kiểm tra số đo RAM bằng mức cấp phát thật trên tiến trình."""

from __future__ import annotations

from mma_ai.compat.memory import peak_ram_mb


def test_regress_t613_ac_2_inv_002_inv_007_real_peak_covers_allocation() -> None:
    """AC-2, INV-002, INV-007: đỉnh RAM (RAM peak) bao phủ mức cấp phát thật 256 MiB."""
    before = peak_ram_mb()
    assert before is not None

    allocation = bytearray(256 * 1024 * 1024)
    for offset in range(0, len(allocation), 4096):
        allocation[offset] = 1

    after = peak_ram_mb()
    assert after is not None
    assert after >= before
    assert after >= 230.4
    del allocation
