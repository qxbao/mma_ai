"""Kiểm thử tích hợp (integration test) kết thúc episode và phần thưởng môi trường thật.

Các ca kiểm thử này giữ FR-008, FR-009, FR-014 và AC-2 trên đường chạy
ElbowReachEnv thay vì chỉ kiểm tra hàm phần thưởng độc lập.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

try:
    import jsonschema
except ImportError:
    jsonschema = None

from mma_ai.environment.env_config import ElbowEnvConfig
from mma_ai.environment.targets import Target


def _make_env(cfg: ElbowEnvConfig) -> Any:
    """Tạo môi trường thật sau khi pytest đã cô lập display."""
    from mma_ai.environment.single_agent import ElbowReachEnv

    return ElbowReachEnv(cfg=cfg)


def _config(**changes: Any) -> ElbowEnvConfig:
    """Tạo cấu hình bất biến dẫn xuất từ mặc định cho từng ca kết thúc."""
    return replace(ElbowEnvConfig.load(), **changes)


def _step_info_schema() -> dict[str, Any]:
    """Nạp schema hợp đồng của info do step trả về."""
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "002-elbow-muscle-env"
        / "contracts"
        / "step-info.schema.json"
    )
    return cast(dict[str, Any], json.loads(schema_path.read_text(encoding="utf-8")))


def _position_tuple(position: np.ndarray[Any, Any]) -> tuple[float, float, float]:
    """Đổi vị trí MuJoCo thành bộ ba float có độ dài tĩnh cho Target."""
    return (float(position[0]), float(position[1]), float(position[2]))


def test_ac_2_terminated_on_reach() -> None:
    """AC-2, FR-009, FR-014: Dung sai lớn kết thúc vì reached chứ không truncated."""
    env = _make_env(_config(tolerance_m=10.0, max_actions=1))
    env.reset(seed=401)

    _, _, terminated, truncated, info = env.step(np.zeros(6, dtype=np.float32))

    assert terminated is True
    assert truncated is False
    assert info["end_reason"] == "reached"
    assert info["reached"] is True


def test_ac_2_truncated_at_max_actions() -> None:
    """AC-2, FR-009, FR-014: Đích chưa tới ở hành động cuối báo max_actions."""
    env = _make_env(_config(tolerance_m=1e-12, max_actions=1))
    env.reset(seed=402)

    _, _, terminated, truncated, info = env.step(np.zeros(6, dtype=np.float32))

    assert terminated is False
    assert truncated is True
    assert info["end_reason"] == "max_actions"
    assert info["n_actions"] == 1


def test_ac_2_terminated_wins_on_tie() -> None:
    """AC-2, FR-009: reached thắng max_actions khi cùng xảy ra một bước."""
    env = _make_env(_config(tolerance_m=10.0, max_actions=1))
    env.reset(seed=403)

    _, _, terminated, truncated, info = env.step(np.ones(6, dtype=np.float32))

    assert terminated is True
    assert truncated is False
    assert info["end_reason"] == "reached"


def test_ac_2_reward_components_in_info_and_weights_configurable() -> None:
    """AC-2, FR-008, FR-014: info có thành phần reward và effort tôn trọng cấu hình."""
    zero_effort_cfg = _config(reward=replace(ElbowEnvConfig.load().reward, w_effort=0.0))
    zero_env = _make_env(zero_effort_cfg)
    zero_env.reset(seed=404)
    _, zero_reward, _, _, zero_info = zero_env.step(np.ones(6, dtype=np.float32))

    weighted_env = _make_env(ElbowEnvConfig.load())
    weighted_env.reset(seed=404)
    _, weighted_reward, _, _, weighted_info = weighted_env.step(np.ones(6, dtype=np.float32))

    assert zero_info["reward_effort"] == 0.0
    assert weighted_info["reward_effort"] < 0.0
    assert zero_reward > weighted_reward
    assert {"reward_dist", "reward_effort"} <= zero_info.keys()


def test_ac_2_closer_state_higher_reward_finite() -> None:
    """AC-2, FR-008: Cùng trạng thái gần mục tiêu hơn cho reward lớn hơn và hữu hạn."""
    near_env = _make_env(ElbowEnvConfig.load())
    far_env = _make_env(ElbowEnvConfig.load())
    near_env.reset(seed=405)
    far_env.reset(seed=405)
    action = np.zeros(6, dtype=np.float32)

    position = np.array(near_env.data.site_xpos[near_env.fingertip_site_id], dtype=np.float64)
    base_target = near_env._current_target
    assert base_target is not None
    near_env._current_target = Target(
        index=base_target.index,
        angle_rad=base_target.angle_rad,
        position_m=_position_tuple(position),
    )
    far_env._current_target = Target(
        index=base_target.index,
        angle_rad=base_target.angle_rad,
        position_m=_position_tuple(position + np.array([0.1, 0.0, 0.0])),
    )

    _, near_reward, _, _, near_info = near_env.step(action)
    _, far_reward, _, _, far_info = far_env.step(action)

    assert np.isfinite(near_reward)
    assert np.isfinite(far_reward)
    assert near_info["distance_m"] < far_info["distance_m"]
    assert near_reward > far_reward


def test_ac_2_step_info_matches_schema() -> None:
    """AC-2, FR-008, FR-009: info trả về khớp đầy đủ step-info.schema.json."""
    env = _make_env(_config(tolerance_m=1e-12, max_actions=2))
    env.reset(seed=406)

    _, _, _, _, info = env.step(np.full(6, 0.25, dtype=np.float32))

    if jsonschema is None:
        pytest.skip("jsonschema không có trong môi trường kiểm thử")
    jsonschema.validate(instance=info, schema=_step_info_schema())
