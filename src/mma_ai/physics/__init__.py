"""Phân hệ mô phỏng vật lý và mô hình cơ bắp (mma_ai.physics).

Cung cấp giao diện nạp mô hình, bộ mô phỏng headless và kiểm soát ổn định số học:
- FR-001: Nạp mô hình MyoElbow và kiểm tra số lượng cơ bắp.
- FR-003: Xác thực vector kích hoạt cơ bắp.
- FR-004: Điều khiển mô phỏng chỉ thông qua kích thích cơ.
"""

from __future__ import annotations

from mma_ai.physics.body_model import (
    LoadedModel,
    ModelError,
    MuscleModelInfo,
    load_muscle_model,
)
from mma_ai.physics.numeric_health import read_physics_warnings, scan_nonfinite
from mma_ai.physics.simulator import (
    ActivationError,
    HeadlessSimulator,
    StepReadout,
    validate_activation,
)

__all__: list[str] = [
    "ActivationError",
    "HeadlessSimulator",
    "LoadedModel",
    "ModelError",
    "MuscleModelInfo",
    "StepReadout",
    "load_muscle_model",
    "read_physics_warnings",
    "scan_nonfinite",
    "validate_activation",
]
