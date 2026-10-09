"""Mô-đun quản lý bố cục và chuẩn hoá không gian quan sát (mma_ai.environment.observation).

Cung cấp bố cục 14 chiều float32 cho môi trường khuỷu tay MyoElbow:
- FR-005: Vector quan sát 14 chiều với cận hữu hạn, chuẩn hoá góc khớp, vận tốc, cơ và vị trí.
- FR-006: Kiểm tra tính hợp lệ của observation (chiều, hữu hạn, trong cận) và báo lỗi rõ ràng.
- INV-004: Observation trả về đúng chiều, hữu hạn và trong cận hoặc chặn lại bằng lỗi rõ ràng.
- AC-2: Quan sát đúng chiều 14, không NaN/Inf, nằm trong khoảng khai báo cả khi chuyển động mạnh.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar, Sequence

import gymnasium.spaces as spaces
import mujoco
import numpy as np

from mma_ai.environment.errors import ObservationError

# Số chiều không gian quan sát chuẩn theo hợp đồng (research.md Q4)
OBSERVATION_DIMENSION: int = 14
_NUM_MUSCLES: int = 6

# Cận chuẩn hoá mặc định đã khai báo cho từng thành phần
DEFAULT_BOUNDS_LOW: np.ndarray = np.array(
    [
        -1.5,  # 0: góc khớp (q - q_mid) / q_half
        -1.0,  # 1: vận tốc khớp qvel / qvel_scale_rad_s (đã kẹp)
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,  # 2..7: kích hoạt 6 cơ [0, 1]
        -1.5, -1.5, -1.5,  # 8..10: vị trí đầu mút tay đẳng hướng (p - c) / h
        -1.5, -1.5, -1.5,  # 11..13: vị trí mục tiêu đẳng hướng (p_target - c) / h
    ],
    dtype=np.float32,
)

DEFAULT_BOUNDS_HIGH: np.ndarray = np.array(
    [
        1.5,  # 0: góc khớp
        1.0,  # 1: vận tốc khớp
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  # 2..7: kích hoạt 6 cơ
        1.5, 1.5, 1.5,  # 8..10: vị trí đầu mút tay
        1.5, 1.5, 1.5,  # 11..13: vị trí mục tiêu
    ],
    dtype=np.float32,
)


class ObservationLayout:
    """Bố cục không gian quan sát (observation space) 14 chiều với cận hữu hạn (FR-005, INV-004).

    Công khai các lát cắt (slices) chỉ số của từng thành phần dữ liệu quan sát:
    - joint_angle: chỉ số 0
    - joint_velocity: chỉ số 1
    - activation: chỉ số 2-7 (6 cơ)
    - fingertip_position: chỉ số 8-10 (3D)
    - target_position: chỉ số 11-13 (3D)
    """

    JOINT_ANGLE_SLICE: ClassVar[slice] = slice(0, 1)
    JOINT_VELOCITY_SLICE: ClassVar[slice] = slice(1, 2)
    ACTIVATION_SLICE: ClassVar[slice] = slice(2, 8)
    FINGERTIP_POSITION_SLICE: ClassVar[slice] = slice(8, 11)
    TARGET_POSITION_SLICE: ClassVar[slice] = slice(11, 14)

    def __init__(
        self,
        model: mujoco.MjModel | None = None,
        *,
        fingertip_site: str = "wrist",
        qvel_scale_rad_s: float = 25.0,
        q_mid: float | None = None,
        q_half: float | None = None,
        c: Sequence[float] | np.ndarray | None = None,
        h: float | None = None,
    ) -> None:
        """Khởi tạo bố cục quan sát, tính toán các hằng số hình học từ mô hình nếu có."""
        self.fingertip_site: str = fingertip_site
        self.qvel_scale_rad_s: float = float(qvel_scale_rad_s)
        self.dim: int = OBSERVATION_DIMENSION
        self.shape: tuple[int, ...] = (OBSERVATION_DIMENSION,)

        if model is not None:
            # Suy ra các hằng số chuẩn hoá từ mô hình bằng cách quét cung chuyển động
            calc_q_mid, calc_q_half, calc_c, calc_h = self.compute_arc_parameters(
                model=model,
                fingertip_site=fingertip_site,
            )
            self.q_mid: float = calc_q_mid if q_mid is None else float(q_mid)
            self.q_half: float = calc_q_half if q_half is None else float(q_half)
            self.c: np.ndarray = (
                calc_c if c is None else np.asarray(c, dtype=np.float64)
            )
            self.h: float = calc_h if h is None else float(h)
        else:
            if q_mid is None or q_half is None or c is None or h is None:
                # Nạp mô hình MyoElbow mặc định từ gói myo-sim khi không truyền đủ tham số
                try:
                    import myo_sim

                    default_model = myo_sim.load_model("myoelbow")
                    calc_q_mid, calc_q_half, calc_c, calc_h = (
                        self.compute_arc_parameters(
                            model=default_model,
                            fingertip_site=fingertip_site,
                        )
                    )
                    self.q_mid = (
                        calc_q_mid if q_mid is None else float(q_mid)
                    )
                    self.q_half = (
                        calc_q_half if q_half is None else float(q_half)
                    )
                    self.c = (
                        calc_c if c is None else np.asarray(c, dtype=np.float64)
                    )
                    self.h = calc_h if h is None else float(h)
                except Exception:
                    # Giá trị dự phòng nếu không nạp được gói myo-sim
                    self.q_mid = 1.134465 if q_mid is None else float(q_mid)
                    self.q_half = 1.134465 if q_half is None else float(q_half)
                    self.c = (
                        np.array([-0.21, -0.045, 1.059], dtype=np.float64)
                        if c is None
                        else np.asarray(c, dtype=np.float64)
                    )
                    self.h = 0.2175 if h is None else float(h)
            else:
                self.q_mid = float(q_mid)
                self.q_half = float(q_half)
                self.c = np.asarray(c, dtype=np.float64)
                self.h = float(h)

        self.low: np.ndarray = DEFAULT_BOUNDS_LOW.copy()
        self.high: np.ndarray = DEFAULT_BOUNDS_HIGH.copy()

        self.observation_space: spaces.Box = spaces.Box(
            low=self.low,
            high=self.high,
            shape=self.shape,
            dtype=np.float32,
        )
        self.space: spaces.Box = self.observation_space

    @classmethod
    def compute_arc_parameters(
        cls,
        model: mujoco.MjModel,
        fingertip_site: str = "wrist",
    ) -> tuple[float, float, np.ndarray, float]:
        """Tính toán các hằng số chuẩn hoá q_mid, q_half, c, h từ mô hình MuJoCo (FR-014).

        - q_mid, q_half: tâm và nửa dải góc khớp khuỷu r_elbow_flex.
        - c: tâm hộp bao (bounding box center) của cung quỹ đạo đầu mút tay 3D.
        - h: nửa cạnh dài nhất của hộp bao quỹ đạo đầu mút tay (đẳng hướng).
        """
        # 1. Xác định giới hạn hành trình góc khớp
        jnt_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "r_elbow_flex")
        if jnt_id < 0:
            jnt_id = 0
        jnt_range = model.jnt_range[jnt_id]
        jnt_lo = float(jnt_range[0])
        jnt_hi = float(jnt_range[1])

        q_mid = (jnt_lo + jnt_hi) / 2.0
        q_half = (jnt_hi - jnt_lo) / 2.0
        if q_half <= 0.0:
            q_half = 1.0

        # 2. Xác định site đầu mút tay
        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, fingertip_site)
        if site_id < 0:
            raise ObservationError(
                f"Không tìm thấy fingertip_site '{fingertip_site}' trong mô hình MuJoCo."
            )

        # 3. Quét cung chuyển động bằng MjData riêng biệt (không chạm episode)
        calc_data = mujoco.MjData(model)
        n_samples = 500
        thetas = np.linspace(jnt_lo, jnt_hi, n_samples)
        positions: list[np.ndarray] = []
        for th in thetas:
            calc_data.qpos[jnt_id] = th
            mujoco.mj_kinematics(model, calc_data)
            positions.append(calc_data.site_xpos[site_id].copy())

        pos_arr = np.array(positions)
        min_coords = np.min(pos_arr, axis=0)
        max_coords = np.max(pos_arr, axis=0)

        # Tâm hộp bao 3D
        c = (min_coords + max_coords) / 2.0
        # Nửa cạnh dài nhất (đẳng hướng)
        extents = max_coords - min_coords
        h = float(np.max(extents) / 2.0)
        if h <= 0.0:
            h = 1.0

        return q_mid, q_half, c, h

    @property
    def joint_angle_slice(self) -> slice:
        """Lát cắt chỉ số góc khớp (joint angle) tại chỉ số 0."""
        return self.JOINT_ANGLE_SLICE

    @property
    def joint_velocity_slice(self) -> slice:
        """Lát cắt chỉ số vận tốc khớp (joint velocity) tại chỉ số 1."""
        return self.JOINT_VELOCITY_SLICE

    @property
    def activation_slice(self) -> slice:
        """Lát cắt chỉ số kích hoạt cơ (muscle activations) tại chỉ số 2-7."""
        return self.ACTIVATION_SLICE

    @property
    def muscle_activation_slice(self) -> slice:
        """Bí danh cho lát cắt kích hoạt 6 cơ tại chỉ số 2-7."""
        return self.ACTIVATION_SLICE

    @property
    def fingertip_position_slice(self) -> slice:
        """Lát cắt chỉ số vị trí đầu mút tay (fingertip position) tại chỉ số 8-10."""
        return self.FINGERTIP_POSITION_SLICE

    @property
    def target_position_slice(self) -> slice:
        """Lát cắt chỉ số vị trí mục tiêu (target position) tại chỉ số 11-13."""
        return self.TARGET_POSITION_SLICE

    def build_observation(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[np.ndarray, bool]:
        """Xây dựng vector quan sát từ trạng thái mô phỏng thông qua đối tượng layout."""
        return build_observation(self, *args, **kwargs)


def validate_observation(
    obs: Any,
    layout: ObservationLayout | None = None,
) -> np.ndarray:
    """Kiểm tra tính hợp lệ của vector quan sát (FR-006, INV-004).

    Kiểm tra chiều (14), tính hữu hạn (không NaN/Inf) và nằm trong cận khai báo.
    Chỉ vận tốc khớp được kẹp trong bước sinh; mọi thành phần khác vượt cận
    đều ném ngoại lệ ObservationError nêu rõ chỉ số và giá trị vi phạm.
    """
    # 1. Trích xuất mảng numpy từ đối tượng đầu vào
    if isinstance(obs, tuple) and len(obs) == 2 and isinstance(obs[0], np.ndarray):
        arr = obs[0]
    elif isinstance(obs, np.ndarray):
        arr = obs
    elif isinstance(obs, Sequence) and not isinstance(obs, (str, bytes)):
        try:
            arr = np.array(obs, dtype=np.float32)
        except Exception as e:
            raise ObservationError(
                f"Không thể chuyển đổi dữ liệu quan sát sang mảng số: {e}"
            ) from e
    else:
        type_name = type(obs).__name__
        raise ObservationError(
            f"Dữ liệu quan sát phải là ndarray hoặc Sequence, nhận được: {type_name}."
        )

    # 2. Kiểm tra kiểu số và số chiều
    if not np.issubdtype(arr.dtype, np.number):
        raise ObservationError("Vector quan sát phải chứa các phần tử số thực.")

    if arr.ndim != 1 or arr.shape != (OBSERVATION_DIMENSION,):
        raise ObservationError(
            f"Kích thước vector quan sát không hợp lệ: shape={arr.shape}, "
            f"mong đợi ({OBSERVATION_DIMENSION},)."
        )

    # 3. Kiểm tra tính hữu hạn (finite check: không NaN/Inf)
    for idx in range(OBSERVATION_DIMENSION):
        val = float(arr[idx])
        if math.isnan(val):
            raise ObservationError(
                f"Observation chứa giá trị NaN không hữu hạn tại chỉ số {idx}: giá trị={val}."
            )
        if math.isinf(val):
            raise ObservationError(
                f"Observation chứa giá trị vô cực Inf tại chỉ số {idx}: giá trị={val}."
            )

    # 4. Kiểm tra nằm trong cận đã khai báo (bounds check)
    low_bounds = layout.low if layout is not None else DEFAULT_BOUNDS_LOW
    high_bounds = layout.high if layout is not None else DEFAULT_BOUNDS_HIGH
    tolerance = 1e-5

    for idx in range(OBSERVATION_DIMENSION):
        val = float(arr[idx])
        lo = float(low_bounds[idx])
        hi = float(high_bounds[idx])
        if val < lo - tolerance or val > hi + tolerance:
            val_str = f"{round(val, 6):g}"
            raise ObservationError(
                f"Observation tại chỉ số {idx} vượt cận khai báo [{lo}, {hi}]: giá trị={val_str}."
            )

    return arr.astype(np.float32)


def build_observation(
    layout: ObservationLayout,
    qpos: float | Sequence[float] | np.ndarray | mujoco.MjData | None = None,
    qvel: float | Sequence[float] | np.ndarray | None = None,
    act: Sequence[float] | np.ndarray | None = None,
    fingertip_pos: Sequence[float] | np.ndarray | None = None,
    target_pos: Sequence[float] | np.ndarray | None = None,
    *,
    data: mujoco.MjData | None = None,
    target_position: Sequence[float] | np.ndarray | None = None,
    validate: bool = True,
) -> tuple[np.ndarray, bool]:
    """Xây dựng vector quan sát 14 chiều và cờ kẹp vận tốc (FR-005, FR-006, INV-004).

    Vector quan sát 14 chiều gồm thứ tự cố định:
    - 0: góc khớp chuẩn hoá (q - q_mid) / q_half
    - 1: vận tốc khớp chuẩn hoá qvel / qvel_scale_rad_s, kẹp về [-1, 1]
    - 2..7: kích hoạt 6 cơ trong [0, 1]
    - 8..10: vị trí đầu mút tay đẳng hướng (p - c) / h
    - 11..13: vị trí mục tiêu đẳng hướng (p_target - c) / h
    """
    # 1. Hỗ trợ truyền thẳng đối tượng MjData
    active_data = data
    if isinstance(qpos, mujoco.MjData):
        active_data = qpos
        if (
            isinstance(qvel, (Sequence, np.ndarray))
            and target_pos is None
            and target_position is None
        ):
            target_pos = qvel

    if active_data is not None:
        qpos_val = float(active_data.qpos[0])
        qvel_val = float(active_data.qvel[0])
        act_val = [float(x) for x in active_data.act[:_NUM_MUSCLES]]

        if hasattr(active_data, "site_xpos"):
            # Lấy vị trí site đầu mút tay
            fingertip_arr = np.asarray(fingertip_pos) if fingertip_pos is not None else None
            if fingertip_arr is None or fingertip_arr.size != 3:
                # Nếu không truyền vị trí site riêng, đọc từ site_xpos của active_data
                fingertip_val = [float(x) for x in active_data.site_xpos[0]]
            else:
                fingertip_val = [float(x) for x in fingertip_arr.flat]
        else:
            fingertip_val = [float(x) for x in (fingertip_pos or (0.0, 0.0, 0.0))]
    else:
        # Trích xuất từ các tham số rời rạc
        if qpos is None:
            raise ObservationError("Thiếu tham số góc khớp (qpos) để xây dựng observation.")
        qpos_arr = np.asarray(qpos, dtype=np.float64)
        qpos_val = float(qpos_arr.flat[0])

        if qvel is None:
            raise ObservationError("Thiếu tham số vận tốc khớp (qvel) để xây dựng observation.")
        qvel_arr = np.asarray(qvel, dtype=np.float64)
        qvel_val = float(qvel_arr.flat[0])

        if act is None:
            raise ObservationError("Thiếu tham số kích hoạt cơ (act) để xây dựng observation.")
        act_arr = np.asarray(act, dtype=np.float64)
        if act_arr.size != _NUM_MUSCLES:
            raise ObservationError(
                f"Kích hoạt cơ phải có đúng {_NUM_MUSCLES} phần tử, nhận được: {act_arr.size}."
            )
        act_val = [float(x) for x in act_arr.flat]

        if fingertip_pos is None:
            raise ObservationError("Thiếu tham số vị trí đầu mút tay (fingertip_pos).")
        fingertip_arr = np.asarray(fingertip_pos, dtype=np.float64)
        if fingertip_arr.size != 3:
            raise ObservationError(
                f"Vị trí đầu mút tay phải là 3D, nhận được: {fingertip_arr.size} phần tử."
            )
        fingertip_val = [float(x) for x in fingertip_arr.flat]

    # Xác định toạ độ mục tiêu
    raw_target = target_pos if target_pos is not None else target_position
    if raw_target is None:
        raise ObservationError("Thiếu tham số vị trí mục tiêu (target_pos).")
    target_arr = np.asarray(raw_target, dtype=np.float64)
    if target_arr.size != 3:
        raise ObservationError(
            f"Vị trí mục tiêu phải là toạ độ 3D (3 phần tử), nhận được: {target_arr.size}."
        )
    target_val = [float(x) for x in target_arr.flat]

    # 2. Thực hiện các phép chuẩn hoá theo research.md Q4
    # (a) Góc khớp chuẩn hoá: (q - q_mid) / q_half
    norm_qpos = (qpos_val - layout.q_mid) / layout.q_half

    # (b) Vận tốc khớp chuẩn hoá: qvel / qvel_scale_rad_s kẹp về [-1, 1]
    raw_norm_qvel = qvel_val / layout.qvel_scale_rad_s
    qvel_clipped = bool(raw_norm_qvel < -1.0 or raw_norm_qvel > 1.0)
    norm_qvel = float(np.clip(raw_norm_qvel, -1.0, 1.0))

    # (c) Kích hoạt 6 cơ: giữ nguyên trong [0, 1]
    norm_act = act_val

    # (d) Vị trí đầu mút tay chuẩn hoá đẳng hướng: (p - c) / h
    c = layout.c
    h = layout.h
    norm_fingertip = [
        (fingertip_val[i] - float(c[i])) / h for i in range(3)
    ]

    # (e) Vị trí mục tiêu chuẩn hoá đẳng hướng: (p_target - c) / h
    norm_target = [
        (target_val[i] - float(c[i])) / h for i in range(3)
    ]

    # 3. Đóng gói vector 14 chiều float32
    obs_elements = [norm_qpos, norm_qvel] + norm_act + norm_fingertip + norm_target
    obs = np.array(obs_elements, dtype=np.float32)

    # 4. Xác thực vector trước khi trả ra nếu validate=True (INV-004)
    if validate:
        validate_observation(obs, layout)

    return obs, qvel_clipped


__all__: list[str] = [
    "DEFAULT_BOUNDS_HIGH",
    "DEFAULT_BOUNDS_LOW",
    "OBSERVATION_DIMENSION",
    "ObservationLayout",
    "build_observation",
    "validate_observation",
]
