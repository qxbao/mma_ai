"""Kiểm thử tích hợp môi trường khuỷu tay cho US1 và AC-1."""

from __future__ import annotations

import hashlib
import re
import warnings
from pathlib import Path
from typing import Any

import gymnasium.spaces as spaces
import mujoco
import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from mma_ai.environment.errors import ModelError
from mma_ai.physics.body_model import LoadedModel, MuscleModelInfo, load_muscle_model


def _make_env() -> Any:
    """Tạo môi trường sau khi pytest đã thiết lập môi trường thực thi."""
    from mma_ai.environment.single_agent import ElbowReachEnv

    return ElbowReachEnv()


def test_ac_1_loads_exactly_six_muscles() -> None:
    """AC-1, FR-001: Mô hình thật có đúng sáu cơ theo thứ tự chỉ định."""
    env = _make_env()

    assert env.model_info.n_muscles == 6
    assert env.model_info.n_non_muscle_actuators == 0
    assert env.muscle_names == ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"]


def test_ac_1_action_space_is_unit_box_6() -> None:
    """AC-1, FR-003: Không gian hành động là Box [0,1]^6 với float32."""
    env = _make_env()

    assert isinstance(env.action_space, spaces.Box)
    assert env.action_space.shape == (6,)
    assert env.action_space.dtype == np.dtype(np.float32)
    assert np.array_equal(env.action_space.low, np.zeros(6, dtype=np.float32))
    assert np.array_equal(env.action_space.high, np.ones(6, dtype=np.float32))


def test_ac_1_model_sha256_in_reset_info_and_model_record() -> None:
    """AC-1, FR-013: Hash XML là SHA-256 ổn định trong info và hồ sơ mô hình."""
    first_env = _make_env()
    _, first_info = first_env.reset(seed=17)
    second_env = _make_env()

    first_hash = first_info["model_sha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", first_hash)
    assert first_env.model_record()["sha256"] == first_hash
    assert second_env.model_record()["sha256"] == first_hash


def test_ac_1_gymnasium_check_env_without_infinite_bounds_warning() -> None:
    """AC-1, FR-002: Gymnasium checker chấp nhận môi trường và cận observation hữu hạn."""
    env = _make_env()

    assert np.all(np.isfinite(env.observation_space.low))
    assert np.all(np.isfinite(env.observation_space.high))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        check_env(env, skip_render_check=True)


def test_ac_1_rejects_model_with_non_muscle_actuator(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-1, FR-001: Loader bị tiêm motor phải bị từ chối, không có fallback thay mô hình."""
    bad_model = mujoco.MjModel.from_xml_string(
        """
        <mujoco model="injected_motor">
          <worldbody>
            <body name="arm">
              <joint name="elbow" type="hinge"/><geom type="sphere" size="0.1"/>
            </body>
          </worldbody>
          <actuator><motor name="forbidden_motor" joint="elbow"/></actuator>
        </mujoco>
        """
    )
    injected = LoadedModel(
        model=bad_model,
        info=MuscleModelInfo(
            n_muscles=0,
            n_non_muscle_actuators=1,
            sha256="0" * 64,
            muscle_names=[],
            joint_ranges_rad=[],
            source="test/injected_motor.xml",
        ),
        xml_path="",
    )
    monkeypatch.setattr("mma_ai.environment.single_agent.load_muscle_model", lambda _: injected)

    with pytest.raises(ModelError, match=r"0 cơ bắp.*1 actuator không phải cơ bắp"):
        _make_env()


def test_ac_1_timestep_set_without_editing_xml() -> None:
    """AC-1, FR-014: Bước vật lý theo cấu hình nhưng bytes XML nguồn không đổi."""
    source = load_muscle_model()
    xml_path = Path(source.xml_path)
    original_hash = hashlib.sha256(xml_path.read_bytes()).hexdigest()

    env = _make_env()

    assert env.model.opt.timestep == pytest.approx(env.cfg.physics_timestep_s)
    assert hashlib.sha256(xml_path.read_bytes()).hexdigest() == original_hash
