"""Kiểm thử đơn vị cho gói lỗi môi trường và đăng ký Gymnasium (mma_ai.environment).

Các kiểm thử chứng minh các yêu cầu và bất biến:
- FR-002: Đăng ký môi trường MmaElbowReach-v0 theo Gymnasium và kiểm soát ranh giới nhập gói.
- FR-003: Phân định các lớp ngoại lệ khi cấu hình, trạng thái hoặc giá trị vi phạm.
- FR-006: Báo lỗi mất ổn định vật lý và kiểm tra tính toàn vẹn của quan sát.
- AC-1 / AC-2: Thông điệp tiếng Việt kèm ngữ cảnh, giá trị vi phạm và số thực thể.
- INV-004: Không sử dụng lại tên OSError/EnvironmentError có sẵn của hệ điều hành.
"""

import sys
import warnings
from typing import Type

import gymnasium as gym

from mma_ai.environment import register_envs
from mma_ai.environment.errors import (
    EnvConfigError,
    EnvironmentBaseError,
    EnvStateError,
    ObservationError,
    PhysicsInstabilityError,
    TargetConfigError,
)

ALL_ENV_ERROR_CLASSES: list[Type[EnvironmentBaseError]] = [
    EnvConfigError,
    TargetConfigError,
    ObservationError,
    PhysicsInstabilityError,
    EnvStateError,
]


def test_errors_subclass_hierarchy_and_naming() -> None:
    """FR-003, INV-004: Kế thừa EnvironmentBaseError, không dùng OSError/EnvironmentError."""
    assert issubclass(EnvironmentBaseError, Exception)
    # Không kế thừa OSError / EnvironmentError có sẵn của Python
    assert not issubclass(EnvironmentBaseError, OSError)

    for err_cls in ALL_ENV_ERROR_CLASSES:
        assert issubclass(err_cls, EnvironmentBaseError), (
            f"{err_cls.__name__} phải kế thừa từ EnvironmentBaseError"
        )
        assert issubclass(err_cls, Exception)
        assert not issubclass(err_cls, OSError)


def test_messages_in_vietnamese_with_values() -> None:
    """AC-1, AC-2, FR-003, FR-006: Ngoại lệ lưu thông điệp tiếng Việt kèm giá trị ngữ cảnh."""
    test_cases: list[tuple[Type[EnvironmentBaseError], str]] = [
        (
            EnvConfigError,
            "Cấu hình bước vật lý (physics_timestep_s) không hợp lệ: -0.001 s (yêu cầu > 0)",
        ),
        (
            TargetConfigError,
            "Cấu hình mục tiêu bất khả thi: khoảng cách min 0.5 m vượt độ dài cung 0.477 m",
        ),
        (
            ObservationError,
            "Quan sát (observation) không hợp lệ: chiều nhận được là 12, kỳ vọng 14",
        ),
        (
            PhysicsInstabilityError,
            "Mất ổn định vật lý tại bước 45: phát hiện NaN trong vận tốc khớp (qvel)",
        ),
        (
            EnvStateError,
            "Lỗi trạng thái môi trường: gọi step() khi episode chưa được reset()",
        ),
    ]

    for err_cls, message in test_cases:
        err = err_cls(message)
        assert str(err) == message, f"{err_cls.__name__} phải giữ nguyên nội dung str"
        assert getattr(err, "message", None) == message, (
            f"{err_cls.__name__} phải có thuộc tính message lưu trữ chuỗi tiếng Việt"
        )


def test_register_envs_idempotent() -> None:
    """FR-002: Đăng ký id MmaElbowReach-v0 chuẩn, gọi nhiều lần không lỗi và không warning."""
    env_id = "MmaElbowReach-v0"
    expected_entry_point = "mma_ai.environment.single_agent:ElbowReachEnv"

    # Gọi lần 1
    register_envs()

    assert env_id in gym.registry, f"Môi trường {env_id} phải có trong gym.registry sau khi đăng ký"
    spec = gym.spec(env_id)
    assert spec.id == env_id
    assert spec.entry_point == expected_entry_point

    # Gọi lần 2: phải idempotent, không raise lỗi và không phát UserWarning ghi đè
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        register_envs()

    # Kiểm tra không có UserWarning nào về ghi đè môi trường
    override_warnings = [
        w for w in recorded_warnings if "Overriding environment" in str(w.message)
    ]
    assert len(override_warnings) == 0, (
        f"Gọi register_envs() lần thứ 2 không được phát sinh cảnh báo ghi đè: {override_warnings}"
    )


def test_import_package_has_no_viewer() -> None:
    """FR-002: Nhập gói mma_ai.environment không nạp mujoco.viewer hoặc single_agent."""
    sys.modules.pop("mma_ai.environment.single_agent", None)
    sys.modules.pop("mujoco.viewer", None)
    sys.modules.pop("glfw", None)
    import mma_ai.environment

    assert mma_ai.environment.__doc__ is not None
    assert len(mma_ai.environment.__doc__.strip()) > 0

    # Tuyệt đối không nạp các mô-đun nặng hoặc viewer đồ hoạ
    assert "mujoco.viewer" not in sys.modules, "Không được nhập mujoco.viewer khi nạp gói"
    assert "glfw" not in sys.modules, "Không được nhập glfw khi nạp gói môi trường"
    assert "mma_ai.environment.single_agent" not in sys.modules, (
        "Không được nhập trực tiếp single_agent khi nạp gói mma_ai.environment"
    )
