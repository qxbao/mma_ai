from __future__ import annotations

import random

import pytest

from mma_ai.compat.capabilities import Capability


def test_inv_004_capability_result_always_pairs_availability_and_reason() -> None:
    """INV-004: sinh 1.000 trạng thái để bảo toàn quan hệ giữa kết quả và lý do."""
    generator = random.Random(604)
    reasons = [None, "Không khả dụng.", "   "]

    for _ in range(1_000):
        available = generator.choice((True, False))
        reason = generator.choice(reasons)
        is_consistent = available == (reason is None) and (
            reason is None or bool(reason.strip())
        )
        if is_consistent:
            result = Capability(available, reason)
            assert result.available == (result.reason is None)
        else:
            with pytest.raises(ValueError):
                Capability(available, reason)
