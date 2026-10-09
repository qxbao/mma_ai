"""Mô-đun nạp và thẩm định mô hình cơ bắp (mma_ai.physics.body_model).

Hiện thực các giao diện nạp mô hình MuJoCo cho cánh tay khuỷu MyoElbow:
- FR-001: Nạp mô hình MyoElbow từ myo-sim, xác nhận đúng 6 cơ và không có actuator lạ.
- FR-013: Tính mã băm SHA-256 của tệp XML mô hình.
- AC-1 / AC-4: Ném ModelError khi vi phạm cấu trúc actuator.
- INV-003: Chỉ cho phép cơ bắp điều khiển, không cho phép joint motor hay position controller.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import mujoco
import myo_sim

from mma_ai.environment.errors import ModelError


@dataclass(frozen=True)
class MuscleModelInfo:
    """Thông tin trích xuất của mô hình cơ bắp (FR-001, FR-013)."""

    n_muscles: int
    n_non_muscle_actuators: int
    sha256: str
    muscle_names: list[str]
    joint_ranges_rad: list[list[float]]
    source: str


@dataclass(frozen=True)
class LoadedModel:
    """Mô hình MuJoCo đã nạp kèm thông tin thẩm định cấu trúc."""

    model: mujoco.MjModel
    info: MuscleModelInfo
    xml_path: str


def load_muscle_model(model_name: str = "myoelbow") -> LoadedModel:
    """Nạp tệp XML mô hình từ gói myo-sim và thẩm định 6 cơ bắp (FR-001, FR-013).

    Args:
        model_name: Tên mô hình trong myo-sim (mặc định 'myoelbow').

    Returns:
        LoadedModel chứa MjModel và MuscleModelInfo.

    Raises:
        ModelError: Khi số cơ bắp khác 6 hoặc có actuator không phải cơ bắp.
    """
    xml_path = myo_sim.get_xml_path(model_name)
    xml_path_str = str(xml_path)
    xml_bytes = Path(xml_path_str).read_bytes()
    sha256_hex = hashlib.sha256(xml_bytes).hexdigest()

    model = mujoco.MjModel.from_xml_path(xml_path_str)

    n_muscles = 0
    n_non_muscle_actuators = 0
    muscle_names: list[str] = []

    for i in range(model.nu):
        act_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or f"actuator_{i}"
        gain_type = model.actuator_gaintype[i]
        bias_type = model.actuator_biastype[i]

        # Trong MuJoCo, cơ bắp Hill có gaintype và biastype là mjGAIN_MUSCLE và mjBIAS_MUSCLE
        is_muscle = bool(
            gain_type == mujoco.mjtGain.mjGAIN_MUSCLE
            and bias_type == mujoco.mjtBias.mjBIAS_MUSCLE
        )

        if is_muscle:
            n_muscles += 1
            muscle_names.append(act_name)
        else:
            n_non_muscle_actuators += 1

    if n_muscles != 6 or n_non_muscle_actuators > 0:
        raise ModelError(
            f"Mô hình không hợp lệ: tìm thấy {n_muscles} cơ bắp (kỳ vọng 6) và "
            f"{n_non_muscle_actuators} actuator không phải cơ bắp (kỳ vọng 0)."
        )

    joint_ranges = [
        [float(model.jnt_range[i, 0]), float(model.jnt_range[i, 1])]
        for i in range(model.njnt)
    ]

    source_path = "myo_sim/elbow/myoelbow_1dof6muscles.xml"

    info = MuscleModelInfo(
        n_muscles=n_muscles,
        n_non_muscle_actuators=n_non_muscle_actuators,
        sha256=sha256_hex,
        muscle_names=muscle_names,
        joint_ranges_rad=joint_ranges,
        source=source_path,
    )

    return LoadedModel(
        model=model,
        info=info,
        xml_path=xml_path,
    )


__all__: list[str] = [
    "LoadedModel",
    "ModelError",
    "MuscleModelInfo",
    "load_muscle_model",
]
