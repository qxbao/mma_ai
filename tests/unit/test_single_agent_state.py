"""Kiểm thử trạng thái vòng đời và giao diện môi trường đơn agent (mma_ai.environment.single_agent).

Các kiểm thử chứng minh các yêu cầu và bất biến theo hợp đồng:
- FR-001, AC-1, AC-4: Nạp mô hình MyoElbow, kiểm tra 6 muscle actuators và từ chối actuator lạ.
- FR-002, AC-1, API-002: Cung cấp giao diện Gymnasium chuẩn (ElbowReachEnv, make_env).
- FR-003, AC-1, INV-003: Action space [0, 1]^6 và từ chối hành động sai bằng ActivationError.
- FR-004, AC-4, INV-003: Chỉ điều khiển qua kích thích cơ, không ghi trực tiếp lực/toạ độ.
- FR-006, INV-004: Kiểm tra observation trả về đúng chiều, hữu hạn và trong cận.
- FR-009, AC-2: Phân định terminated (tới mục tiêu) và truncated (hết số bước).
- FR-012, AC-3: Chọn nguồn mục tiêu train/test tách bạch, báo qua reset info.
- FR-013, AC-1: Báo mã băm SHA-256 của tệp XML mô hình trong info và model_record().
- NFR-HEADLESS-001: Môi trường khởi tạo, reset và step hoàn toàn không cần giao diện đồ hoạ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gymnasium as gym

try:
    import jsonschema
except ImportError:
    jsonschema = None
import numpy as np
import pytest

from mma_ai.environment import register_envs
from mma_ai.environment.errors import EnvStateError
from mma_ai.physics.simulator import ActivationError


@pytest.fixture  # type: ignore[untyped-decorator]
def repo_root() -> Path:
    """Trả về thư mục gốc của repo dự án."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture  # type: ignore[untyped-decorator]
def reset_info_schema(repo_root: Path) -> dict[str, Any]:
    """Tải JSON schema kiểm tra tính hợp lệ của reset info (FR-012)."""
    schema_path = (
        repo_root
        / "specs"
        / "002-elbow-muscle-env"
        / "contracts"
        / "reset-info.schema.json"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture  # type: ignore[untyped-decorator]
def step_info_schema(repo_root: Path) -> dict[str, Any]:
    """Tải JSON schema kiểm tra tính hợp lệ của step info (FR-004, FR-009)."""
    schema_path = (
        repo_root
        / "specs"
        / "002-elbow-muscle-env"
        / "contracts"
        / "step-info.schema.json"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


@pytest.fixture  # type: ignore[untyped-decorator]
def model_record_schema(repo_root: Path) -> dict[str, Any]:
    """Tải JSON schema kiểm tra tính hợp lệ của model record (FR-013)."""
    schema_path = (
        repo_root
        / "specs"
        / "002-elbow-muscle-env"
        / "contracts"
        / "model-record.schema.json"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _make_reach_env(*args: Any, **kwargs: Any) -> Any:
    """Tạo đối tượng ElbowReachEnv mà không import tại module level lúc pytest collect."""
    from mma_ai.environment.single_agent import ElbowReachEnv
    return ElbowReachEnv(*args, **kwargs)


def _make_env(*args: Any, **kwargs: Any) -> Any:
    """Gọi make_env mà không import tại module level lúc pytest collect."""
    from mma_ai.environment.single_agent import make_env
    return make_env(*args, **kwargs)


def test_step_before_reset_raises() -> None:
    """FR-002, AC-2: Gọi step() trước reset() phải ném EnvStateError."""
    env = _make_reach_env()
    dummy_action = np.zeros(6, dtype=np.float32)

    with pytest.raises(EnvStateError) as exc_info:
        env.step(dummy_action)

    assert "chưa được reset" in str(exc_info.value).lower() or "reset" in str(exc_info.value)


def test_step_after_done_raises() -> None:
    """FR-002, AC-2: Gọi step() sau khi episode kết thúc (done) phải ném EnvStateError."""
    env = _make_reach_env()
    env.reset(seed=42)

    dummy_action = np.zeros(6, dtype=np.float32)

    # Chạy tới khi truncated hoặc terminated
    done = False
    for _ in range(env.cfg.max_actions + 5):
        _, _, terminated, truncated, _ = env.step(dummy_action)
        if terminated or truncated:
            done = True
            break

    assert done, "Episode phải kết thúc sau max_actions bước"

    # Gọi step() tiếp theo khi đã done phải ném EnvStateError
    with pytest.raises(EnvStateError) as exc_info:
        env.step(dummy_action)

    assert "kết thúc" in str(exc_info.value).lower() or "reset" in str(exc_info.value)


def test_reset_after_done_ok() -> None:
    """FR-002, AC-2: Sau khi episode kết thúc, gọi reset() đưa môi trường về trạng thái sẵn sàng."""
    env = _make_reach_env()
    env.reset(seed=42)

    dummy_action = np.zeros(6, dtype=np.float32)
    for _ in range(env.cfg.max_actions):
        _, _, terminated, truncated, _ = env.step(dummy_action)
        if terminated or truncated:
            break

    # Gọi reset() lại
    obs, info = env.reset(seed=123)
    assert obs.shape == (14,)
    assert isinstance(info, dict)

    # Bước tiếp theo phải hoạt động bình thường, không ném lỗi
    next_obs, reward, terminated, truncated, step_info = env.step(dummy_action)
    assert next_obs.shape == (14,)
    assert isinstance(reward, float)
    assert step_info["n_actions"] == 1


def test_reset_returns_obs_shape_14(reset_info_schema: dict[str, Any]) -> None:
    """FR-005, FR-012, INV-004, AC-2: reset() trả về observation 14 chiều và info chuẩn schema."""
    env = _make_reach_env()
    obs, info = env.reset(seed=42)

    assert obs.shape == (14,)
    assert obs.dtype == np.float32
    assert np.all(np.isfinite(obs))

    # Khẳng định info khớp với JSON schema reset-info.schema.json
    if jsonschema is not None:
        jsonschema.validate(instance=info, schema=reset_info_schema)
    assert info["seed"] == 42
    assert info["target_split"] == "train"
    assert info["target_index"] >= 0
    assert len(info["target_position_m"]) == 3
    assert info["initial_distance_m"] >= 0.0
    assert len(info["model_sha256"]) == 64


def test_reset_with_seed_none_assigns_valid_seed(reset_info_schema: dict[str, Any]) -> None:
    """FR-012, AC-3: reset(seed=None) vẫn điền seed thực dùng nguyên dương (không null)."""
    env = _make_reach_env()
    obs, info = env.reset(seed=None)

    assert obs.shape == (14,)
    if jsonschema is not None:
        jsonschema.validate(instance=info, schema=reset_info_schema)
    assert isinstance(info["seed"], int)
    assert info["seed"] >= 0


def test_reset_with_split_options() -> None:
    """FR-012, INV-001, AC-3: reset(options={'split': 'test'}) chọn mục tiêu từ tập test."""
    env = _make_reach_env(split="train")
    _, info_train = env.reset(seed=42, options={"split": "train"})
    assert info_train["target_split"] == "train"

    _, info_test = env.reset(seed=42, options={"split": "test"})
    assert info_test["target_split"] == "test"

    # Mục tiêu test không được trùng với bất kỳ mục tiêu train nào
    test_pos = info_test["target_position_m"]
    train_targets_pos = [t.position_m for t in env.targets.train.targets]
    for tr_pos in train_targets_pos:
        dist = np.linalg.norm(np.array(test_pos) - np.array(tr_pos))
        assert dist >= env.cfg.targets.min_separation_m - 1e-6


def test_make_env_default_and_split_arg() -> None:
    """FR-002, API-002: make_env() tạo môi trường chuẩn với split train/test tuỳ biến."""
    from mma_ai.environment.single_agent import ElbowReachEnv

    env_train = _make_env(split="train")
    assert isinstance(env_train, ElbowReachEnv)
    assert env_train.split == "train"
    _, info_tr = env_train.reset(seed=10)
    assert info_tr["target_split"] == "train"

    env_test = _make_env(split="test")
    assert isinstance(env_test, ElbowReachEnv)
    assert env_test.split == "test"
    _, info_te = env_test.reset(seed=10)
    assert info_te["target_split"] == "test"


def test_registered_id_makes_env() -> None:
    """FR-002, API-002: Gymnasium make('MmaElbowReach-v0') khởi tạo thành công môi trường."""
    from mma_ai.environment.single_agent import ElbowReachEnv

    register_envs()
    env = gym.make("MmaElbowReach-v0")
    assert isinstance(env.unwrapped, ElbowReachEnv)
    obs, info = env.reset(seed=42)
    assert obs.shape == (14,)
    assert "target_split" in info


def test_step_returns_step_info_schema(step_info_schema: dict[str, Any]) -> None:
    """FR-004, FR-008, FR-009, INV-003, AC-2: step() trả về info tuân thủ step-info.schema.json."""
    env = _make_reach_env()
    env.reset(seed=42)

    action = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)

    assert obs.shape == (14,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)

    if jsonschema is not None:
        jsonschema.validate(instance=info, schema=step_info_schema)
    assert len(info["ctrl_requested"]) == 6
    assert len(info["ctrl_effective"]) == 6
    assert info["n_actions"] == 1
    assert info["end_reason"] is None


def test_step_action_validation_raises_activation_error() -> None:
    """FR-003, INV-003, AC-1: Từ chối hành động sai kích thước, NaN/Inf hoặc ngoài [0, 1]."""
    env = _make_reach_env()
    env.reset(seed=42)

    # Sai số phần tử (5 phần tử thay vì 6)
    with pytest.raises(ActivationError):
        env.step(np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32))

    # Chứa giá trị ngoài [0, 1]
    with pytest.raises(ActivationError):
        env.step(np.array([-0.1, 0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float32))

    with pytest.raises(ActivationError):
        env.step(np.array([1.2, 0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float32))

    # Chứa NaN
    with pytest.raises(ActivationError):
        env.step(np.array([np.nan, 0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float32))


def test_model_record_conforms_to_schema(model_record_schema: dict[str, Any]) -> None:
    """FR-001, FR-013, INV-003, AC-1: model_record() trả về thông tin chuẩn schema."""
    env = _make_reach_env()
    record = env.model_record()

    if jsonschema is not None:
        jsonschema.validate(instance=record, schema=model_record_schema)
    assert record["schema_version"] == "1.0.0"
    assert record["n_muscles"] == 6
    assert record["n_non_muscle_actuators"] == 0
    assert len(record["muscle_names"]) == 6
    assert len(record["sha256"]) == 64
    assert record["physics_timestep_s"] == env.cfg.physics_timestep_s
    assert record["fingertip_site"] == "wrist"


def test_terminated_priority_over_truncated() -> None:
    """FR-009, AC-2: Khi tới mục tiêu đồng thời đạt max_actions, terminated thắng truncated."""
    env = _make_reach_env()
    env.reset(seed=42)

    # Đặt số bước đã chạy bằng max_actions - 1
    env._n_actions = env.cfg.max_actions - 1

    # Giả lập vị trí mục tiêu sát vị trí đầu mút tay hiện tại
    wrist_pos = env.data.site_xpos[env.fingertip_site_id].copy()
    from mma_ai.environment.targets import Target

    env._current_target = Target(index=0, angle_rad=0.0, position_m=tuple(wrist_pos))

    action = np.zeros(6, dtype=np.float32)
    _, _, terminated, truncated, info = env.step(action)

    assert terminated is True
    assert truncated is False
    assert info["end_reason"] == "reached"

