"""Môi trường học tăng cường cánh tay khuỷu MyoElbow đơn agent (mma_ai.environment.single_agent).

Cung cấp giao diện Gymnasium chuẩn bọc mô phỏng cơ bắp MyoElbow 6 cơ:
- FR-001, AC-1: Nạp mô hình MyoElbow từ myo-sim, kiểm tra đúng 6 cơ và không có actuator khác.
- FR-002, API-002: Lớp ElbowReachEnv(gymnasium.Env) và hàm khởi tạo chuẩn make_env().
- FR-003, AC-1: Action space là Box(0, 1, (6,), float32), kiểm tra kích hoạt u qua hàm.
- FR-004, INV-003: Chỉ điều khiển qua kích thích cơ u; không ghi trực tiếp góc, lực, toạ độ.
- FR-006, INV-004: Observation 14 chiều chuẩn hoá với cận hữu hạn, kiểm soát mất ổn định số học.
- FR-009, AC-2: Kết thúc terminated (tới đích) thắng truncated (hết số bước) khi cùng bước.
- FR-012, AC-3: Quản lý chọn mục tiêu train/test tách bạch, báo qua reset info.
- FR-013, AC-1: Báo mã băm SHA-256 XML và hồ sơ mô hình qua model_record().
- NFR-HEADLESS-001: Hoạt động headless hoàn toàn, không phụ thuộc màn hình hiển thị.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import gymnasium as gym
import gymnasium.spaces as spaces
import mujoco
import numpy as np

from mma_ai.environment.env_config import ElbowEnvConfig
from mma_ai.environment.errors import (
    EnvConfigError,
    EnvStateError,
    ModelError,
)
from mma_ai.environment.observation import ObservationLayout, build_observation
from mma_ai.environment.reward import compute_reward, is_reached
from mma_ai.environment.targets import Target, TargetGenerator, TargetSetPair
from mma_ai.physics.body_model import LoadedModel, MuscleModelInfo, load_muscle_model
from mma_ai.physics.simulator import (
    ActivationError,
    HeadlessSimulator,
    StepReadout,
    validate_activation,
)


class ElbowReachEnv(gym.Env[np.ndarray, np.ndarray]):
    """Môi trường học tăng cường tiếp cận mục tiêu cánh tay khuỷu MyoElbow (FR-002)."""

    metadata: dict[str, Any] = {"render_modes": []}

    def __init__(
        self,
        cfg: ElbowEnvConfig | str | Path | None = None,
        targets: TargetSetPair | None = None,
        split: str | None = None,
        model: mujoco.MjModel | None = None,
    ) -> None:
        """Khởi tạo môi trường khuỷu tay MyoElbow 6 cơ bắp (FR-001, FR-002).

        Args:
            cfg: Cấu hình ElbowEnvConfig hoặc đường dẫn tệp YAML (mặc định nạp gói).
            targets: Bộ mục tiêu TargetSetPair (mặc định sinh mới theo cấu hình).
            split: Vai trò tập mục tiêu ban đầu ('train' hoặc 'test').
            model: Mô hình MjModel tuỳ biến phục vụ kiểm thử cấu trúc.

        Raises:
            ModelError: Khi mô hình không có đúng 6 cơ bắp hoặc chứa actuator không phải cơ.
            EnvConfigError: Khi cấu hình hoặc tên site đầu mút tay không hợp lệ.
        """
        super().__init__()

        # 1. Nạp và xác thực cấu hình môi trường (FR-014)
        if cfg is None:
            self.cfg: ElbowEnvConfig = ElbowEnvConfig.load()
        elif isinstance(cfg, (str, Path)):
            self.cfg = ElbowEnvConfig.load(cfg)
        elif isinstance(cfg, ElbowEnvConfig):
            self.cfg = cfg
        else:
            raise EnvConfigError(f"Cấu hình truyền vào không hợp lệ: {type(cfg).__name__}.")

        # 2. Xác định vai trò phân chia tập mục tiêu (FR-012)
        initial_split = split if split is not None else self.cfg.target_split
        if initial_split not in ("train", "test"):
            raise EnvConfigError(
                f"Phân tách mục tiêu (split) không hợp lệ: '{initial_split}', "
                f"kỳ vọng 'train' hoặc 'test'."
            )
        self.split: str = initial_split

        # 3. Nạp và thẩm định mô hình MyoElbow MỘT lần (FR-001, FR-013)
        if model is not None:
            self._validate_model_structure(model)
            self.model: mujoco.MjModel = model
            sha256_hex = self._compute_model_sha256(model)
            muscle_names = [
                mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or f"actuator_{i}"
                for i in range(model.nu)
            ]
            joint_ranges = [
                [float(model.jnt_range[i, 0]), float(model.jnt_range[i, 1])]
                for i in range(model.njnt)
            ]
            self.loaded_model = LoadedModel(
                model=model,
                info=MuscleModelInfo(
                    n_muscles=model.nu,
                    n_non_muscle_actuators=0,
                    sha256=sha256_hex,
                    muscle_names=muscle_names,
                    joint_ranges_rad=joint_ranges,
                    source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
                ),
                xml_path="",
            )
        else:
            self.loaded_model = load_muscle_model("myoelbow")
            self.model = self.loaded_model.model

        self.model_info: MuscleModelInfo = self.loaded_model.info
        self.model_sha256: str = self.model_info.sha256
        self.muscle_names: list[str] = list(self.model_info.muscle_names)

        # 4. Gán bước thời gian vật lý từ cấu hình (KHÔNG sửa XML) (FR-014)
        self.model.opt.timestep = float(self.cfg.physics_timestep_s)

        # 5. Khởi tạo bộ mô phỏng không giao diện (INV-003, FR-004)
        self.sim: HeadlessSimulator = HeadlessSimulator(
            self.loaded_model,
            timestep_s=self.cfg.physics_timestep_s,
        )
        self.data: mujoco.MjData = self.sim.data

        # 6. Kiểm tra vị trí site đầu mút tay (fingertip_site)
        self.fingertip_site_name: str = self.cfg.fingertip_site
        site_id = mujoco.mj_name2id(
            self.model,
            mujoco.mjtObj.mjOBJ_SITE,
            self.fingertip_site_name,
        )
        if site_id < 0:
            raise EnvConfigError(
                f"Không tìm thấy site đầu mút tay '{self.fingertip_site_name}' "
                f"trong mô hình MuJoCo."
            )

        self.fingertip_site_id: int = site_id

        # 7. Thiết lập không gian quan sát (observation) và hành động (action) (FR-003, FR-005)
        self.layout: ObservationLayout = ObservationLayout(
            self.model,
            fingertip_site=self.fingertip_site_name,
            qvel_scale_rad_s=self.cfg.obs.qvel_scale_rad_s,
        )
        self.observation_space: spaces.Box = self.layout.observation_space
        self.action_space: spaces.Box = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(6,),
            dtype=np.float32,
        )

        # 8. Khởi tạo bộ mục tiêu train/test (FR-010, FR-011, INV-001)
        if targets is not None:
            self.targets: TargetSetPair = targets
        else:
            generator = TargetGenerator(self.model, self.cfg)
            self.targets = generator.generate(seed=self.cfg.targets.default_seed)

        # 9. Trạng thái vòng đời của episode (máy trạng thái: created -> ready -> done)
        self._is_ready: bool = False
        self._is_done: bool = False
        self._n_actions: int = 0
        self._current_split: str = self.split
        self._current_target: Target | None = None

    @staticmethod
    def _validate_model_structure(model: mujoco.MjModel) -> None:
        """Kiểm tra cấu trúc actuator của mô hình (FR-001, AC-1)."""
        n_muscles = 0
        n_non_muscle_actuators = 0

        for i in range(model.nu):
            gain_type = model.actuator_gaintype[i]
            bias_type = model.actuator_biastype[i]

            is_muscle = bool(
                gain_type == mujoco.mjtGain.mjGAIN_MUSCLE
                and bias_type == mujoco.mjtBias.mjBIAS_MUSCLE
            )

            if is_muscle:
                n_muscles += 1
            else:
                n_non_muscle_actuators += 1

        if n_muscles != 6 or n_non_muscle_actuators > 0:
            raise ModelError(
                f"Mô hình không hợp lệ: tìm thấy {n_muscles} cơ bắp (kỳ vọng 6) và "
                f"{n_non_muscle_actuators} actuator không phải cơ bắp (kỳ vọng 0)."
            )

    @staticmethod
    def _compute_model_sha256(model: mujoco.MjModel) -> str:
        """Tính mã băm tượng trưng cho mô hình nạp tuỳ biến."""
        summary = f"nu={model.nu}_nq={model.nq}_nv={model.nv}"
        return hashlib.sha256(summary.encode("utf-8")).hexdigest()

    def reset(
        self,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Đặt lại trạng thái môi trường về ban đầu cố định và chọn mục tiêu mới (FR-012, INV-002).

        Args:
            seed: Seed ngẫu nhiên (nếu None, rút một seed nguyên ngẫu nhiên).
            options: Tuỳ chọn đặt lại, bao gồm 'split' ('train' hoặc 'test').

        Returns:
            Bộ đôi (observation 14 chiều float32, info theo reset-info.schema.json).
        """
        # Quản lý seed ngẫu nhiên theo chuẩn Gymnasium
        if seed is not None:
            active_seed = int(seed)
            super().reset(seed=active_seed)
        else:
            if self._np_random is None:
                super().reset()
            active_seed = int(self.np_random.integers(0, 2**31 - 1))

        # Xác định vai trò split cho episode này
        current_split = self.split
        if options is not None and "split" in options:
            opt_split = str(options["split"])
            if opt_split not in ("train", "test"):
                raise EnvConfigError(
                    f"Phân tách mục tiêu trong options không hợp lệ: '{opt_split}', "
                    f"kỳ vọng 'train' hoặc 'test'."
                )
            current_split = opt_split
        self._current_split = current_split

        # Đặt lại mô phỏng bằng mj_resetData (trạng thái đầu cố định qpos=0, act=0)
        self.sim.reset()

        # Chọn mục tiêu ngẫu nhiên từ tập tương ứng bằng self.np_random.integers (INV-001)
        target_set = self.targets.train if current_split == "train" else self.targets.test
        n_targets = len(target_set.targets)
        target_idx = int(self.np_random.integers(0, n_targets))
        selected_target = target_set.targets[target_idx]
        self._current_target = selected_target

        # Đo khoảng cách khởi đầu Euclid 3D từ site wrist tới mục tiêu
        fingertip_pos = np.array(
            self.data.site_xpos[self.fingertip_site_id],
            dtype=np.float64,
        )
        target_pos_arr = np.array(selected_target.position_m, dtype=np.float64)
        initial_distance_m = float(np.linalg.norm(fingertip_pos - target_pos_arr))

        # Tạo vector quan sát khởi đầu 14 chiều float32 (FR-005, INV-004)
        obs, _ = build_observation(
            self.layout,
            data=self.data,
            fingertip_pos=fingertip_pos,
            target_pos=selected_target.position_m,
            validate=True,
        )

        # Cập nhật máy trạng thái môi trường
        self._is_ready = True
        self._is_done = False
        self._n_actions = 0

        # Đóng gói thông tin trả về theo reset-info.schema.json
        info: dict[str, Any] = {
            "seed": active_seed,
            "target_split": current_split,
            "target_index": target_idx,
            "target_position_m": [float(coord) for coord in selected_target.position_m],
            "initial_distance_m": float(initial_distance_m),
            "model_sha256": self.model_sha256,
        }

        return obs, info

    def step(
        self,
        action: Any,
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Tiến một bước hành động mô phỏng và tính phần thưởng (FR-003, FR-004, FR-008, FR-009).

        Args:
            action: Vector kích thích 6 cơ bắp u in [0, 1]^6.

        Returns:
            Bộ 5 phần tử chuẩn Gymnasium: (obs, reward, terminated, truncated, info).

        Raises:
            EnvStateError: Khi gọi step() trước reset() hoặc sau khi episode đã kết thúc.
            ActivationError: Khi hành động sai kích thước, chứa NaN/Inf hoặc ngoài [0, 1].
            PhysicsInstabilityError: Khi mô phỏng MuJoCo mất ổn định số học hoặc cảnh báo vật lý.
        """
        # 1. Kiểm tra trạng thái vòng đời (máy trạng thái)
        if not self._is_ready:
            raise EnvStateError(
                "Lỗi trạng thái môi trường: gọi step() khi episode chưa được reset()."
            )
        if self._is_done:
            raise EnvStateError(
                "Lỗi trạng thái môi trường: gọi step() sau khi episode đã kết thúc "
                "(cần gọi reset() trước khi tiếp tục)."
            )
        if self._current_target is None:
            raise EnvStateError("Môi trường chưa có mục tiêu hợp lệ, cần gọi reset().")

        # 2. Xác thực kích hoạt cơ bắp qua validate_activation (FR-003, AC-1)
        u_valid = validate_activation(action, n_muscles=6)

        # 3. Tiến bước mô phỏng chỉ qua đường ghi ctrl duy nhất (INV-003, FR-004)
        step_readout: StepReadout = self.sim.step(
            u_valid,
            n_steps=self.cfg.substeps_per_action,
        )
        self._n_actions += 1

        # 4. Đo khoảng cách hiện tại giữa đầu mút tay và mục tiêu
        fingertip_pos = np.array(
            self.data.site_xpos[self.fingertip_site_id],
            dtype=np.float64,
        )
        target_pos_arr = np.array(self._current_target.position_m, dtype=np.float64)
        distance_m = float(np.linalg.norm(fingertip_pos - target_pos_arr))

        # 5. Tính toán các thành phần phần thưởng (FR-008)
        reward_terms = compute_reward(distance_m, u_valid, self.cfg)
        reward_val = float(reward_terms.total)

        # 6. Xác định điều kiện kết thúc episode (FR-009, AC-2)
        # Terminated khi khoảng cách <= dung sai tolerance_m
        reached = is_reached(distance_m, self.cfg.tolerance_m)
        terminated = bool(reached)

        # Truncated khi đạt số hành động tối đa mà chưa tới đích
        max_actions_reached = bool(self._n_actions >= self.cfg.max_actions)
        # Terminated thắng Truncated khi xảy ra cùng bước (FR-009)
        truncated = bool(max_actions_reached and not reached)

        end_reason: str | None = None
        if terminated:
            end_reason = "reached"
            self._is_done = True
        elif truncated:
            end_reason = "max_actions"
            self._is_done = True

        # 7. Xây dựng và kiểm tra observation 14 chiều (FR-005, FR-006, INV-004)
        obs, qvel_clipped = build_observation(
            self.layout,
            data=self.data,
            fingertip_pos=fingertip_pos,
            target_pos=self._current_target.position_m,
            validate=True,
        )

        # 8. Đóng gói thông tin step info theo step-info.schema.json
        info: dict[str, Any] = {
            "distance_m": float(distance_m),
            "reached": bool(reached),
            "reward_dist": float(reward_terms.reward_dist),
            "reward_effort": float(reward_terms.reward_effort),
            "ctrl_requested": [float(x) for x in step_readout.ctrl_requested],
            "ctrl_effective": [float(x) for x in step_readout.ctrl_effective],
            "qvel_clipped": bool(qvel_clipped),
            "n_actions": int(self._n_actions),
            "terminated": bool(terminated),
            "truncated": bool(truncated),
            "end_reason": end_reason,
        }

        return obs, reward_val, terminated, truncated, info

    def model_record(self) -> dict[str, Any]:
        """Xuất hồ sơ mô hình theo model-record.schema.json (FR-001, FR-013, INV-003)."""
        ctrl_ranges: list[list[float]] = [
            [float(self.model.actuator_ctrlrange[i, 0]), float(self.model.actuator_ctrlrange[i, 1])]
            for i in range(self.model.nu)
        ]

        joint_ranges: list[list[float]] = [
            [float(self.model.jnt_range[i, 0]), float(self.model.jnt_range[i, 1])]
            for i in range(self.model.njnt)
        ]

        return {
            "schema_version": "1.0.0",
            "source": self.model_info.source,
            "sha256": self.model_sha256,
            "n_muscles": int(self.model_info.n_muscles),
            "n_non_muscle_actuators": int(self.model_info.n_non_muscle_actuators),
            "muscle_names": list(self.muscle_names),
            "joint_ranges_rad": joint_ranges,
            "ctrl_range": ctrl_ranges,
            "physics_timestep_s": float(self.model.opt.timestep),
            "fingertip_site": self.fingertip_site_name,
        }


def make_env(
    config_path: str | Path | None = None,
    split: str = "train",
) -> ElbowReachEnv:
    """Tạo môi trường khuỷu tay chuẩn cho huấn luyện và đánh giá (FR-002, API-002).

    Args:
        config_path: Đường dẫn tệp cấu hình YAML (mặc định nạp tệp đóng gói).
        split: Vai trò tập mục tiêu ban đầu ('train' hoặc 'test').

    Returns:
        Đối tượng ElbowReachEnv đã sẵn sàng hoạt động.
    """
    cfg = ElbowEnvConfig.load(config_path)
    return ElbowReachEnv(cfg=cfg, split=split)


__all__: list[str] = [
    "ActivationError",
    "ElbowReachEnv",
    "ModelError",
    "make_env",
]
