"""Đo tài nguyên và thời gian thực cho một lượt huấn luyện."""

from __future__ import annotations

import importlib
import os
import platform
import time
from dataclasses import dataclass
from types import ModuleType
from typing import Literal, TypedDict

from mma_ai.compat.memory import peak_ram_mb


class ResourceSnapshot(TypedDict):
    """Các trường tài nguyên khớp khuôn hồ sơ run."""

    cpu_model: str | None
    cpu_logical_cores: int
    cpu_utilization_pct: float | None
    ram_peak_mb: float | None
    gpu_name: str | None
    gpu_utilization_pct: float | None
    vram_peak_mb: float | None


@dataclass(frozen=True)
class Throughput:
    """Thông lượng môi trường được tính từ hai đại lượng đo trực tiếp."""

    env_steps: int
    wall_clock_seconds: float

    @property
    def env_steps_per_second(self) -> float | None:
        """Trả thông lượng hoặc null khi chưa có khoảng thời gian dương để đo."""
        if self.wall_clock_seconds <= 0.0:
            return None
        return self.env_steps / self.wall_clock_seconds


class Stopwatch:
    """Đồng hồ đơn điệu đo wall-clock bằng time.perf_counter."""

    def __init__(self) -> None:
        self._started_at: float | None = None
        self._stopped_at: float | None = None

    def start(self) -> None:
        """Bắt đầu một lần đo mới bằng đồng hồ đơn điệu thực."""
        self._started_at = time.perf_counter()
        self._stopped_at = None

    def stop(self) -> float:
        """Dừng đo và trả wall-clock đã trôi qua."""
        if self._started_at is None:
            raise RuntimeError("Không thể dừng Stopwatch trước khi start")
        self._stopped_at = time.perf_counter()
        return self.wall_clock_seconds

    @property
    def wall_clock_seconds(self) -> float:
        """Trả thời gian thực đã đo, chỉ đọc đồng hồ khi phiên còn chạy."""
        if self._started_at is None:
            return 0.0
        finished_at = self._stopped_at if self._stopped_at is not None else time.perf_counter()
        return max(0.0, finished_at - self._started_at)


def _load_torch() -> ModuleType | None:
    try:
        return importlib.import_module("torch")
    except ImportError:
        return None


def _peak_ram_mb() -> float | None:
    return peak_ram_mb()


def detect_device() -> dict[str, Literal["cpu", "cuda"] | str | None]:
    """Phát hiện loại thiết bị mà không ép phụ thuộc torch lúc import."""
    torch = _load_torch()
    if torch is not None and torch.cuda.is_available():
        return {"kind": "cuda", "name": torch.cuda.get_device_name(0)}
    return {"kind": "cpu", "name": None}


def collect_resources() -> ResourceSnapshot:
    result: ResourceSnapshot = {
        "cpu_model": platform.processor() or None,
        "cpu_logical_cores": os.cpu_count() or 1,
        "cpu_utilization_pct": None,
        "ram_peak_mb": _peak_ram_mb(),
        "gpu_name": None,
        "gpu_utilization_pct": None,
        "vram_peak_mb": None,
    }
    torch = _load_torch()
    if torch is not None and torch.cuda.is_available():
        result["gpu_name"] = torch.cuda.get_device_name(0)
        result["vram_peak_mb"] = torch.cuda.max_memory_allocated(0) / (1024.0 * 1024.0)
    return result
