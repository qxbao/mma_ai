"""Kiểm thử đo tài nguyên và thời gian huấn luyện."""

from __future__ import annotations

import importlib
import sys
import time
from collections.abc import Iterator
from types import ModuleType

import pytest


@pytest.fixture  # type: ignore[untyped-decorator]
def resource_module() -> Iterator[ModuleType]:
    """Cô lập import learning để không làm bẩn phép thử ranh giới gói."""
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


def test_fr_012_nfr_res_001_resource_fields_present_null_without_gpu(
    monkeypatch: pytest.MonkeyPatch, resource_module: ModuleType
) -> None:
    """FR-012, NFR-RES-001: GPU/VRAM không có vẫn phải hiện tường minh."""
    monkeypatch.setattr(resource_module, "_load_torch", lambda: None)

    measured = resource_module.collect_resources()

    assert set(measured) == {
        "cpu_model",
        "cpu_logical_cores",
        "cpu_utilization_pct",
        "ram_peak_mb",
        "gpu_name",
        "gpu_utilization_pct",
        "vram_peak_mb",
    }
    assert measured["cpu_logical_cores"] >= 1
    assert measured["gpu_name"] is None
    assert measured["gpu_utilization_pct"] is None
    assert measured["vram_peak_mb"] is None


def test_inv_002_inv_007_peak_ram_uses_cross_platform_measurement(
    monkeypatch: pytest.MonkeyPatch, resource_module: ModuleType
) -> None:
    """INV-002, INV-007: số đo RAM tuân theo bộ đo đa nền tảng, kể cả khi không đọc được."""
    monkeypatch.setattr(resource_module, "peak_ram_mb", lambda: 37.5, raising=False)

    assert resource_module._peak_ram_mb() == 37.5

    monkeypatch.setattr(resource_module, "peak_ram_mb", lambda: None, raising=False)
    assert resource_module._peak_ram_mb() is None


def test_fr_013_throughput_and_wallclock_measured(resource_module: ModuleType) -> None:
    """FR-013: đồng hồ thật đo thời gian quanh công việc, không dự đoán."""
    stopwatch = resource_module.Stopwatch()
    stopwatch.start()
    time.sleep(0.01)
    wall_clock_seconds = stopwatch.stop()
    throughput = resource_module.Throughput(env_steps=4, wall_clock_seconds=wall_clock_seconds)

    assert wall_clock_seconds >= 0.01
    assert throughput.env_steps_per_second is not None
    assert throughput.env_steps_per_second > 0.0


def test_fr_013_no_estimate_from_other_numbers(resource_module: ModuleType) -> None:
    """FR-013: thông lượng chỉ lấy số bước và khoảng thời gian thực đã đo."""
    slow = resource_module.Throughput(env_steps=10, wall_clock_seconds=2.0)
    fast = resource_module.Throughput(env_steps=10, wall_clock_seconds=0.5)

    assert slow.env_steps_per_second == 5.0
    assert fast.env_steps_per_second == 20.0
    assert (
        resource_module.Throughput(env_steps=0, wall_clock_seconds=1.0).env_steps_per_second
        == 0.0
    )
    assert (
        resource_module.Throughput(env_steps=10, wall_clock_seconds=0.0).env_steps_per_second
        is None
    )
