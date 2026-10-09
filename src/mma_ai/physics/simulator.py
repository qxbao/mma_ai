"""Mô phỏng không giao diện (headless simulator) và kiểm tra kích hoạt (mma_ai.physics.simulator).

Hiện thực bộ mô phỏng tuân thủ nghiêm ngặt các bất biến và hợp đồng:
- FR-003, AC-1: Xác thực vector kích hoạt cơ bắp u in [0, 1]^6 qua validate_activation.
- FR-004, AC-4, INV-003: Chỉ ghi data.ctrl, không ghi trực tiếp lực hay toạ độ.
- FR-006, AC-2: Quét NaN/Inf và cảnh báo vật lý, ném PhysicsInstabilityError khi mất ổn định.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

import mujoco
import numpy as np

from mma_ai.environment.errors import (
    ActivationError,
    PhysicsInstabilityError,
)


@dataclass(frozen=True)
class StepReadout:
    """Kết quả đọc dữ liệu sau bước mô phỏng vật lý."""

    ctrl_requested: list[float]
    ctrl_effective: list[float]
    qpos: np.ndarray
    qvel: np.ndarray
    act: np.ndarray


def validate_activation(vec: Any, n_muscles: int = 6) -> np.ndarray:
    """Xác thực vector kích hoạt cơ bắp u in [0, 1]^n_muscles (FR-003, AC-1).

    Args:
        vec: Vector hoặc mảng hành động kích thích cơ cần kiểm tra.
        n_muscles: Số lượng cơ bắp kỳ vọng (mặc định 6).

    Returns:
        Mảng NumPy kiểu float64 chứa các giá trị kích hoạt hợp lệ.

    Raises:
        ActivationError: Khi sai kích thước, chứa NaN/Inf hoặc nằm ngoài [0, 1].
    """
    if isinstance(vec, np.ndarray):
        if vec.size != n_muscles:
            raise ActivationError(
                f"Kích thước vector hành động kích thích cơ không hợp lệ: "
                f"nhận được {vec.size} phần tử (kỳ vọng {n_muscles})."
            )
        if not np.issubdtype(vec.dtype, np.number):
            raise ActivationError("Vector hành động kích thích cơ phải chứa các giá trị số.")
        if bool(np.isnan(vec).any()) or bool(np.isinf(vec).any()):
            raise ActivationError(
                "Hành động kích thích cơ chứa giá trị không hữu hạn (NaN hoặc Inf)."
            )
        flat_vals = [float(x) for x in vec.flat]
    elif isinstance(vec, Sequence) and not isinstance(vec, (str, bytes)):
        if len(vec) != n_muscles:
            raise ActivationError(
                f"Kích thước vector hành động kích thích cơ không hợp lệ: "
                f"nhận được {len(vec)} phần tử (kỳ vọng {n_muscles})."
            )
        flat_vals = []
        for i, val in enumerate(vec):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ActivationError(
                    f"Phần tử hành động tại chỉ số {i} phải là số, nhận được: {type(val).__name__}."
                )
            fval = float(val)
            if math.isnan(fval) or math.isinf(fval):
                raise ActivationError(
                    f"Phần tử hành động tại chỉ số {i} không hữu hạn (NaN hoặc Inf): {fval}."
                )
            flat_vals.append(fval)
    else:
        raise ActivationError(
            f"Vector hành động phải là Sequence hoặc ndarray có đúng {n_muscles} phần tử, "
            f"nhận được: {type(vec).__name__}."
        )

    for i, val in enumerate(flat_vals):
        if val < 0.0 or val > 1.0:
            raise ActivationError(
                f"Hành động kích thích cơ tại chỉ số {i} nằm ngoài khoảng [0, 1]: {val}."
            )

    return np.array(flat_vals, dtype=np.float64)


class HeadlessSimulator:
    """Bộ mô phỏng không giao diện chỉ điều khiển qua kích thích cơ (INV-003, FR-004)."""

    def __init__(
        self,
        model_or_loaded: Any,
        data: mujoco.MjData | None = None,
        timestep_s: float | None = None,
    ) -> None:
        """Khởi tạo bộ mô phỏng headless với mô hình MuJoCo."""
        if hasattr(model_or_loaded, "model"):
            self.model: mujoco.MjModel = model_or_loaded.model
        else:
            self.model = model_or_loaded

        self.data: mujoco.MjData = data if data is not None else mujoco.MjData(self.model)

        if timestep_s is not None:
            self.model.opt.timestep = float(timestep_s)

    def reset(self) -> None:
        """Đặt lại trạng thái mô phỏng ban đầu cố định (INV-002)."""
        mujoco.mj_resetData(self.model, self.data)
        mujoco.mj_forward(self.model, self.data)

    def step(
        self,
        activation: np.ndarray | Sequence[float],
        n_steps: int = 1,
    ) -> StepReadout:
        """Tiến bước mô phỏng chỉ qua đường ghi ctrl duy nhất (INV-003, FR-004).

        Args:
            activation: Vector kích hoạt cơ bắp đã qua kiểm tra.
            n_steps: Số bước vật lý nhỏ (substeps) cần thực hiện.

        Returns:
            StepReadout chứa giá trị yêu cầu, hiệu dụng và trạng thái mô phỏng.

        Raises:
            PhysicsInstabilityError: Khi phát hiện NaN/Inf hoặc cảnh báo MuJoCo.
        """
        u = validate_activation(activation, n_muscles=self.model.nu)
        ctrl_requested = [float(x) for x in u]

        # Đường ghi ctrl duy nhất; tuyệt đối không ghi qpos/qvel/site_xpos
        self.data.ctrl[:] = u

        for step_idx in range(n_steps):
            mujoco.mj_step(self.model, self.data)

            # Kiểm tra mất ổn định số học giữa các bước
            for name, arr in [
                ("qpos", self.data.qpos),
                ("qvel", self.data.qvel),
                ("act", self.data.act),
                ("actuator_force", self.data.actuator_force),
            ]:
                if bool(np.isnan(arr).any()) or bool(np.isinf(arr).any()):
                    raise PhysicsInstabilityError(
                        f"Mất ổn định vật lý tại substep {step_idx + 1}: "
                        f"phát hiện NaN/Inf trong đại lượng {name}."
                    )

            # Kiểm tra cảnh báo từ MuJoCo
            total_warnings = sum(int(w.number) for w in self.data.warning)
            if total_warnings > 0:
                raise PhysicsInstabilityError(
                    f"Mất ổn định vật lý tại substep {step_idx + 1}: "
                    f"phát hiện {total_warnings} cảnh báo vật lý từ MuJoCo."
                )

        # Tính giá trị điều khiển hiệu dụng sau khi MuJoCo kẹp theo ctrlrange
        ctrl_effective: list[float] = []
        for i in range(self.model.nu):
            low = float(self.model.actuator_ctrlrange[i, 0])
            high = float(self.model.actuator_ctrlrange[i, 1])
            eff = float(np.clip(u[i], low, high))
            ctrl_effective.append(eff)

        return StepReadout(
            ctrl_requested=ctrl_requested,
            ctrl_effective=ctrl_effective,
            qpos=self.data.qpos.copy(),
            qvel=self.data.qvel.copy(),
            act=self.data.act.copy(),
        )


__all__: list[str] = [
    "ActivationError",
    "HeadlessSimulator",
    "StepReadout",
    "validate_activation",
]
