"""INV-006: bất biến toán học của tỷ lệ test bị loại theo năng lực."""

from __future__ import annotations

import random

from capability_gate import _deselection_ratio


def test_inv_006_deselection_ratio_is_bounded_and_matches_counts() -> None:
    """INV-006: với ít nhất 100 bộ đếm, tỷ lệ luôn đúng và nằm trong [0, 1]."""
    generator = random.Random(606)
    counts = [(0, 0)]
    counts.extend(
        (total := generator.randint(1, 100_000), generator.randint(0, total))
        for _ in range(512)
    )

    for collected, deselected in counts:
        ratio = _deselection_ratio(deselected, collected)

        assert 0.0 <= ratio <= 1.0
        assert ratio == (deselected / collected if collected else 0.0)

