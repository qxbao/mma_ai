"""Kiểm thử thuộc tính cho lõi dựng bản ghi chỉ số."""

from __future__ import annotations

import math
import random


def test_inv_004_finite_generated_metrics_always_form_complete_record() -> None:
    """INV-004: 100 bộ số hữu hạn tạo bản ghi đầy đủ."""
    from mma_ai.learning.metrics_log import build_metrics_record

    generator = random.Random(20261009)
    muscle_names = ("m1", "m2", "m3", "m4", "m5", "m6")
    values = tuple(generator.uniform(-1_000.0, 1_000.0) for _ in range(100))
    records = tuple(
        build_metrics_record(
            update=index,
            env_steps=index * 2048,
            policy_loss=value,
            value_loss=value,
            entropy=value,
            mean_return=value,
            activations=(value,) * 6,
            env_steps_per_second=abs(value) + 0.001,
            muscle_names=muscle_names,
        )
        for index, value in enumerate(values, 1)
    )
    assert len(records) == 100
    assert all(math.isfinite(item) for entry in records for item in entry.values())


def teardown_module() -> None:
    """Dọn import trì hoãn để các test ranh giới độc lập với thứ tự collection."""
    import sys

    for mod in list(sys.modules):
        if mod == "mma_ai.learning" or mod.startswith("mma_ai.learning."):
            sys.modules.pop(mod, None)
