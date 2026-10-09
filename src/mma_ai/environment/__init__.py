"""Gói môi trường mô phỏng cánh tay khuỷu (mma_ai.environment).

Cung cấp môi trường học tăng cường (RL) tương thích chuẩn Gymnasium cho mô hình MyoElbow:
- FR-002: Cung cấp giao diện Gymnasium chuẩn và hàm đăng ký môi trường register_envs().
- FR-003: Quản lý không gian hành động và phát hiện lỗi trạng thái hoặc giá trị vi phạm.
- FR-006: Kiểm soát tính ổn định vật lý và tính toàn vẹn của observation.
"""

import gymnasium as gym

from mma_ai.environment.errors import (
    EnvConfigError,
    EnvironmentBaseError,
    EnvStateError,
    ObservationError,
    PhysicsInstabilityError,
    TargetConfigError,
)

ENV_ID: str = "MmaElbowReach-v0"
ENTRY_POINT: str = "mma_ai.environment.single_agent:ElbowReachEnv"


def register_envs() -> None:
    """Đăng ký môi trường khuỷu tay MmaElbowReach-v0 với Gymnasium (idempotent).

    Hàm thực hiện kiểm tra tránh đăng ký đè gây cảnh báo, đảm bảo an toàn khi gọi nhiều lần.
    Không nạp trực tiếp mô-đun single_agent hay mujoco.viewer khi đăng ký.
    """
    if ENV_ID not in gym.registry:
        gym.register(
            id=ENV_ID,
            entry_point=ENTRY_POINT,
        )


__all__: list[str] = [
    "ENTRY_POINT",
    "ENV_ID",
    "EnvConfigError",
    "EnvironmentBaseError",
    "EnvStateError",
    "ObservationError",
    "PhysicsInstabilityError",
    "TargetConfigError",
    "register_envs",
]
