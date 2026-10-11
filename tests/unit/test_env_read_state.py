"""Kiểm thử đơn vị cho accessor đọc-chỉ ElbowReachEnv.read_state() (T505).

Xác minh hợp đồng đọc trạng thái:
- FR-002, FR-003, INV-002: Đường đọc chỉ-đọc (read-only), không ghi đè vào MjData hay mô phỏng.
- Bản sao độc lập (independent copies): thay đổi mảng trả về không làm thay đổi trạng thái mô phỏng.
- Tính bất biến quỹ đạo (trajectory invariance): gọi read_state() không làm đổi trajectory mô phỏng.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from mma_ai.environment.errors import EnvStateError
from mma_ai.environment.single_agent import ElbowReachEnv, StateSnapshot, make_env


def test_read_state_before_reset_raises_error() -> None:
    """Gọi read_state() trước khi reset() phải ném lỗi EnvStateError."""
    env = make_env()
    assert isinstance(env, ElbowReachEnv)
    with pytest.raises(EnvStateError, match="reset"):
        env.read_state()


def test_read_state_returns_expected_fields_and_types() -> None:
    """read_state() trả về StateSnapshot với đầy đủ các trường và kiểu dữ liệu hợp lệ."""
    env = make_env()
    obs, info = env.reset(seed=42)

    snapshot = env.read_state()

    assert isinstance(snapshot, StateSnapshot)
    # Kiểm tra các trường cơ bản
    assert isinstance(snapshot.qpos, np.ndarray)
    assert snapshot.qpos.shape == (env.model.nq,)
    assert snapshot.qpos.dtype == np.float64

    assert isinstance(snapshot.qvel, np.ndarray)
    assert snapshot.qvel.shape == (env.model.nv,)
    assert snapshot.qvel.dtype == np.float64

    assert isinstance(snapshot.act, np.ndarray)
    assert snapshot.act.shape == (env.model.na,)
    assert snapshot.act.dtype == np.float64

    assert isinstance(snapshot.fingertip_position_m, np.ndarray)
    assert snapshot.fingertip_position_m.shape == (3,)
    assert snapshot.fingertip_position_m.dtype == np.float64

    assert isinstance(snapshot.target_position_m, np.ndarray)
    assert snapshot.target_position_m.shape == (3,)
    assert snapshot.target_position_m.dtype == np.float64

    assert isinstance(snapshot.time_s, float)
    assert snapshot.time_s == 0.0

    # Hỗ trợ truy cập cả dạng thuộc tính (attribute) lẫn dạng chỉ mục từ điển (subscript)
    assert np.array_equal(snapshot["qpos"], snapshot.qpos)
    assert np.array_equal(snapshot["qvel"], snapshot.qvel)
    assert np.array_equal(snapshot["act"], snapshot.act)
    assert np.array_equal(snapshot["fingertip_position_m"], snapshot.fingertip_position_m)
    assert np.array_equal(snapshot["target_position_m"], snapshot.target_position_m)
    assert snapshot["time_s"] == snapshot.time_s

    with pytest.raises(KeyError):
        _ = snapshot["non_existent_key"]


def test_read_state_returns_independent_copies() -> None:
    """Sửa đổi các mảng trong kết quả trả về không được làm thay đổi MjData
    hoặc mô phỏng (INV-002).
    """
    env = make_env()
    env.reset(seed=123)

    snapshot1 = env.read_state()

    # Lưu lại giá trị ban đầu trong MjData
    orig_qpos = float(env.data.qpos[0])
    orig_qvel = float(env.data.qvel[0])
    orig_act = env.data.act.copy()
    orig_fingertip = env.data.site_xpos[env.fingertip_site_id].copy()

    # Sửa đổi dữ liệu trong snapshot1
    snapshot1.qpos[0] = 999.0
    snapshot1.qvel[0] = 888.0
    snapshot1.act[:] = 1.0
    snapshot1.fingertip_position_m[:] = 777.0
    snapshot1.target_position_m[:] = 666.0

    # Kiểm tra MjData không bị biến đổi
    assert env.data.qpos[0] == orig_qpos
    assert env.data.qvel[0] == orig_qvel
    np.testing.assert_array_equal(env.data.act, orig_act)
    np.testing.assert_array_equal(env.data.site_xpos[env.fingertip_site_id], orig_fingertip)

    # Đọc lại snapshot mới và kiểm tra tính nguyên vẹn
    snapshot2 = env.read_state()
    assert snapshot2.qpos[0] == orig_qpos
    assert snapshot2.qvel[0] == orig_qvel
    np.testing.assert_array_equal(snapshot2.act, orig_act)
    np.testing.assert_array_equal(snapshot2.fingertip_position_m, orig_fingertip)


def test_read_state_does_not_mutate_trajectory() -> None:
    """Gọi read_state() giữa các bước step() không được làm thay đổi quỹ đạo mô phỏng (INV-002)."""
    seed = 2026
    n_steps = 10
    action = np.array([0.1, 0.5, 0.2, 0.0, 0.8, 0.4], dtype=np.float32)

    # Lần chạy 1: không gọi read_state()
    env1 = make_env()
    obs1_list = []
    reward1_list = []
    obs1, _ = env1.reset(seed=seed)
    obs1_list.append(obs1)
    for _ in range(n_steps):
        o, r, term, trunc, _ = env1.step(action)
        obs1_list.append(o)
        reward1_list.append(r)
        if term or trunc:
            break

    # Lần chạy 2: gọi read_state() liên tục trước và sau mỗi bước
    env2 = make_env()
    obs2_list = []
    reward2_list = []
    obs2, _ = env2.reset(seed=seed)
    _ = env2.read_state()
    obs2_list.append(obs2)
    for _ in range(n_steps):
        _ = env2.read_state()
        o, r, term, trunc, _ = env2.step(action)
        _ = env2.read_state()
        obs2_list.append(o)
        reward2_list.append(r)
        if term or trunc:
            break

    assert len(obs1_list) == len(obs2_list)
    for o1, o2 in zip(obs1_list, obs2_list):
        np.testing.assert_array_equal(o1, o2)

    for r1, r2 in zip(reward1_list, reward2_list):
        assert r1 == r2


def test_read_state_updates_after_step() -> None:
    """read_state() cập nhật giá trị thời gian và trạng thái chính xác sau bước mô phỏng step()."""
    env = make_env()
    env.reset(seed=100)

    snap_start = env.read_state()
    assert snap_start.time_s == 0.0

    action = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    env.step(action)

    snap_step = env.read_state()
    # Thời gian mô phỏng phải tăng theo bước thời gian
    assert snap_step.time_s > 0.0
    expected_time = float(env.data.time)
    assert abs(snap_step.time_s - expected_time) < 1e-9
    np.testing.assert_allclose(snap_step.qpos, env.data.qpos)
    np.testing.assert_allclose(snap_step.qvel, env.data.qvel)
    np.testing.assert_allclose(snap_step.act, env.data.act)


def test_read_state_snapshot_is_frozen() -> None:
    """Đối tượng StateSnapshot là bất biến (frozen), không cho phép gán đè thuộc tính."""
    env = make_env()
    env.reset(seed=42)
    snapshot = env.read_state()

    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.time_s = 1.23  # type: ignore[misc]


def test_read_state_with_target_index_option() -> None:
    """read_state() phản ánh đúng mục tiêu khi reset với tuỳ chọn
    options={'split': 'test', 'target_index': i}.
    """
    env = make_env()
    target_idx = 3
    _, info = env.reset(seed=999, options={"split": "test", "target_index": target_idx})

    snapshot = env.read_state()
    assert info["target_index"] == target_idx
    assert info["target_split"] == "test"

    expected_target = env.targets.test.targets[target_idx]
    np.testing.assert_allclose(snapshot.target_position_m, expected_target.position_m)
