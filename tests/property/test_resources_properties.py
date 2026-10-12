"""Kiểm thử thuộc tính cho số đo tài nguyên huấn luyện."""

from __future__ import annotations

import importlib
import random
import sys
from collections.abc import Iterator
from types import ModuleType

import pytest


@pytest.fixture  # type: ignore[untyped-decorator]
def resource_module() -> Iterator[ModuleType]:
    learning_before = sys.modules.get("mma_ai.learning")
    resources_before = sys.modules.get("mma_ai.learning.resources")
    module = importlib.import_module("mma_ai.learning.resources")
    yield module
    if resources_before is None:
        sys.modules.pop("mma_ai.learning.resources", None)
    else:
        sys.modules["mma_ai.learning.resources"] = resources_before
    if learning_before is None:
        sys.modules.pop("mma_ai.learning", None)
    else:
        sys.modules["mma_ai.learning"] = learning_before


def test_inv_002_inv_007_measured_ram_is_never_reinterpreted_property(
    monkeypatch: pytest.MonkeyPatch, resource_module: ModuleType
) -> None:
    """INV-002, INV-007: 100 số đo hợp lệ được chuyển nguyên vẹn qua lớp thu thập."""
    generator = random.Random(613)
    measurements = [generator.uniform(0.0, 1_000_000.0) for _ in range(100)]

    for measurement in measurements:
        monkeypatch.setattr(
            resource_module,
            "peak_ram_mb",
            lambda measurement=measurement: measurement,
            raising=False,
        )
        assert resource_module._peak_ram_mb() == measurement

