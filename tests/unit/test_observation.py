"""Kiểm thử đơn vị cho mô-đun bố cục và chuẩn hoá quan sát (tests/unit/test_observation.py).

Chứng minh các yêu cầu và bất biến kiến trúc:
- FR-005: Vector quan sát 14 chiều với cận hữu hạn, chuẩn hoá góc khớp, vận tốc, cơ và vị trí.
- FR-006: Kiểm tra tính hợp lệ của observation (chiều, hữu hạn, trong cận), báo ObservationError.
- INV-004: Observation trả ra đúng chiều, hữu hạn và trong cận hoặc chặn bằng lỗi rõ ràng.
- AC-2: Quan sát đúng chiều 14, không NaN/Inf, nằm trong khoảng khai báo cả khi chuyển động mạnh.
"""

from __future__ import annotations

import math

import mujoco
import myo_sim
import numpy as np
import pytest

from mma_ai.environment.errors import ObservationError
from mma_ai.environment.observation import (
    ObservationLayout,
    build_observation,
    validate_observation,
)


@pytest.fixture  # type: ignore[untyped-decorator]
def real_elbow_model() -> mujoco.MjModel:
    """Nạp mô hình MuJoCo thật của MyoElbow từ gói myo-sim (FR-001, AC-1)."""
    return myo_sim.load_model("myoelbow")


@pytest.fixture  # type: ignore[untyped-decorator]
def default_layout(real_elbow_model: mujoco.MjModel) -> ObservationLayout:
    """Khởi tạo bố cục quan sát từ mô hình thật MyoElbow (FR-005, INV-004)."""
    return ObservationLayout(real_elbow_model, fingertip_site="wrist", qvel_scale_rad_s=25.0)


def test_layout_is_14_with_finite_bounds(default_layout: ObservationLayout) -> None:
    """Kiểm tra không gian quan sát có đúng 14 chiều và mọi cận đều hữu hạn (FR-005, INV-004)."""
    layout = default_layout
    space = layout.observation_space

    assert space.shape == (14,)
    assert len(layout.low) == 14
    assert len(layout.high) == 14
    assert np.all(np.isfinite(layout.low)), "Mọi cận dưới (low) phải là số hữu hạn"
    assert np.all(np.isfinite(layout.high)), "Mọi cận trên (high) phải là số hữu hạn"
    assert np.all(layout.low < layout.high), "Mọi cận dưới phải nhỏ hơn cận trên"

    # Kiểm tra đối chiếu chi tiết theo research.md Q4 và data-model.md
    # Chỉ số 0: góc khớp [-1.5, 1.5]
    assert math.isclose(float(layout.low[0]), -1.5, abs_tol=1e-5)
    assert math.isclose(float(layout.high[0]), 1.5, abs_tol=1e-5)

    # Chỉ số 1: vận tốc khớp [-1.0, 1.0]
    assert math.isclose(float(layout.low[1]), -1.0, abs_tol=1e-5)
    assert math.isclose(float(layout.high[1]), 1.0, abs_tol=1e-5)

    # Chỉ số 2..7: kích hoạt 6 cơ [0.0, 1.0]
    for idx in range(2, 8):
        assert math.isclose(float(layout.low[idx]), 0.0, abs_tol=1e-5)
        assert math.isclose(float(layout.high[idx]), 1.0, abs_tol=1e-5)

    # Chỉ số 8..10: vị trí đầu mút tay [-1.5, 1.5]
    for idx in range(8, 11):
        assert math.isclose(float(layout.low[idx]), -1.5, abs_tol=1e-5)
        assert math.isclose(float(layout.high[idx]), 1.5, abs_tol=1e-5)

    # Chỉ số 11..13: vị trí mục tiêu [-1.5, 1.5]
    for idx in range(11, 14):
        assert math.isclose(float(layout.low[idx]), -1.5, abs_tol=1e-5)
        assert math.isclose(float(layout.high[idx]), 1.5, abs_tol=1e-5)


def test_normalisation_matches_bounds(
    real_elbow_model: mujoco.MjModel, default_layout: ObservationLayout
) -> None:
    """Kiểm tra rollout cực đoan vẫn nằm trong cận (FR-005, FR-006, INV-004, AC-2)."""
    model = real_elbow_model
    model.opt.timestep = 0.0025
    layout = default_layout

    # Chọn một mục tiêu kiểm thử cố định nằm trong tầm với
    target_pos = np.array([-0.21, -0.05, 1.0], dtype=np.float64)

    # Bốn kịch bản điều khiển cực đoan
    scenarios: dict[str, np.ndarray] = {
        "all_zeros": np.zeros(6, dtype=np.float64),
        "all_ones": np.ones(6, dtype=np.float64),
        "flexor_group": np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0], dtype=np.float64),
        "extensor_group": np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0], dtype=np.float64),
    }

    site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "wrist")
    assert site_id >= 0

    for name, action in scenarios.items():
        data = mujoco.MjData(model)
        mujoco.mj_resetData(model, data)
        mujoco.mj_forward(model, data)

        # Chạy 30 bước hành động, mỗi bước gồm 16 bước con vật lý (substeps)
        for step_idx in range(30):
            data.ctrl[:6] = action
            for _ in range(16):
                mujoco.mj_step(model, data)

            wrist_pos = data.site_xpos[site_id].copy()
            obs, qvel_clipped = build_observation(
                layout,
                qpos=float(data.qpos[0]),
                qvel=float(data.qvel[0]),
                act=np.array(data.act[:6], dtype=np.float64),
                fingertip_pos=wrist_pos,
                target_pos=target_pos,
            )

            # Xác nhận observation không ném lỗi và nằm trong cận khai báo
            validated_obs = validate_observation(obs, layout)
            assert validated_obs.shape == (14,)
            assert np.all(validated_obs >= layout.low), (
                f"Kịch bản {name} tại bước {step_idx} có giá trị dưới cận: {validated_obs}"
            )
            assert np.all(validated_obs <= layout.high), (
                f"Kịch bản {name} tại bước {step_idx} có giá trị trên cận: {validated_obs}"
            )


def test_rejects_out_of_bounds(default_layout: ObservationLayout) -> None:
    """Kiểm tra từ chối các thành phần observation vượt cận và ném ObservationError (FR-006)."""
    layout = default_layout

    # Tạo vector mẫu hợp lệ (nằm chính giữa cận)
    base_obs = np.array(
        [
            0.0,  # qpos [-1.5, 1.5]
            0.0,  # qvel [-1.0, 1.0]
            0.5, 0.5, 0.5, 0.5, 0.5, 0.5,  # act [0.0, 1.0]
            0.0, 0.0, 0.0,  # wrist [-1.5, 1.5]
            0.0, 0.0, 0.0,  # target [-1.5, 1.5]
        ],
        dtype=np.float32,
    )
    # Khẳng định vector mẫu hợp lệ
    assert validate_observation(base_obs, layout) is not None

    # 1. Góc khớp vượt cận trên (chỉ số 0)
    bad_obs = base_obs.copy()
    bad_obs[0] = 1.6
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(bad_obs, layout)
    err_msg = str(exc_info.value)
    assert "0" in err_msg
    assert "1.6" in err_msg

    # 2. Vận tốc khớp vượt cận khi đưa vào validate (chỉ số 1)
    bad_obs = base_obs.copy()
    bad_obs[1] = 1.05
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(bad_obs, layout)
    err_msg = str(exc_info.value)
    assert "1" in err_msg
    assert "1.05" in err_msg

    # 3. Kích hoạt cơ dưới cận dưới 0.0 (chỉ số 3)
    bad_obs = base_obs.copy()
    bad_obs[3] = -0.05
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(bad_obs, layout)
    err_msg = str(exc_info.value)
    assert "3" in err_msg
    assert "-0.05" in err_msg

    # 4. Kích hoạt cơ vượt cận trên 1.0 (chỉ số 6)
    bad_obs = base_obs.copy()
    bad_obs[6] = 1.02
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(bad_obs, layout)
    err_msg = str(exc_info.value)
    assert "6" in err_msg
    assert "1.02" in err_msg

    # 5. Vị trí đầu mút tay vượt cận (chỉ số 9)
    bad_obs = base_obs.copy()
    bad_obs[9] = 1.55
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(bad_obs, layout)
    err_msg = str(exc_info.value)
    assert "9" in err_msg
    assert "1.55" in err_msg

    # 6. Vị trí mục tiêu dưới cận dưới (chỉ số 12)
    bad_obs = base_obs.copy()
    bad_obs[12] = -1.55
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(bad_obs, layout)
    err_msg = str(exc_info.value)
    assert "12" in err_msg
    assert "-1.55" in err_msg


def test_rejects_wrong_shape_and_nan_inf(default_layout: ObservationLayout) -> None:
    """Kiểm tra từ chối sai kích thước, kiểu dữ liệu sai hoặc NaN/Inf (FR-006, INV-004, AC-2)."""
    layout = default_layout

    # 1. Sai kích thước (13 phần tử)
    short_obs = np.zeros(13, dtype=np.float32)
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(short_obs, layout)
    assert "13" in str(exc_info.value) or "14" in str(exc_info.value)

    # 2. Sai kích thước (15 phần tử)
    long_obs = np.zeros(15, dtype=np.float32)
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(long_obs, layout)
    assert "15" in str(exc_info.value) or "14" in str(exc_info.value)

    # 3. Sai số chiều ma trận 2D
    matrix_obs = np.zeros((2, 7), dtype=np.float32)
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(matrix_obs, layout)
    assert "kích thước" in str(exc_info.value).lower() or "shape" in str(exc_info.value).lower()

    # 4. Chứa NaN tại chỉ số 4
    base_obs = np.zeros(14, dtype=np.float32)
    nan_obs = base_obs.copy()
    nan_obs[4] = float("nan")
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(nan_obs, layout)
    err_msg = str(exc_info.value)
    assert "4" in err_msg
    assert "nan" in err_msg.lower() or "hữu hạn" in err_msg.lower()

    # 5. Chứa dương vô cực (Inf) tại chỉ số 1
    inf_obs = base_obs.copy()
    inf_obs[1] = float("inf")
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(inf_obs, layout)
    err_msg = str(exc_info.value)
    assert "1" in err_msg
    assert "inf" in err_msg.lower() or "hữu hạn" in err_msg.lower()

    # 6. Chứa âm vô cực (-Inf) tại chỉ số 10
    neg_inf_obs = base_obs.copy()
    neg_inf_obs[10] = float("-inf")
    with pytest.raises(ObservationError) as exc_info:
        validate_observation(neg_inf_obs, layout)
    err_msg = str(exc_info.value)
    assert "10" in err_msg


def test_qvel_clipped_flag(default_layout: ObservationLayout) -> None:
    """Kiểm tra vận tốc khớp được kẹp về [-1, 1] và cờ qvel_clipped (FR-005, FR-006, INV-004)."""
    layout = default_layout
    qpos = 1.0
    act = np.zeros(6, dtype=np.float64)
    fingertip_pos = np.array([-0.2, 0.0, 1.0], dtype=np.float64)
    target_pos = np.array([-0.2, 0.0, 1.0], dtype=np.float64)

    # Vận tốc vượt ngưỡng dương (qvel = 50.0 > 25.0 rad/s)
    obs_hi, clipped_hi = build_observation(
        layout,
        qpos=qpos,
        qvel=50.0,
        act=act,
        fingertip_pos=fingertip_pos,
        target_pos=target_pos,
    )
    assert clipped_hi is True
    assert math.isclose(float(obs_hi[1]), 1.0, abs_tol=1e-5)
    validate_observation(obs_hi, layout)

    # Vận tốc vượt ngưỡng âm (qvel = -50.0 < -25.0 rad/s)
    obs_lo, clipped_lo = build_observation(
        layout,
        qpos=qpos,
        qvel=-50.0,
        act=act,
        fingertip_pos=fingertip_pos,
        target_pos=target_pos,
    )
    assert clipped_lo is True
    assert math.isclose(float(obs_lo[1]), -1.0, abs_tol=1e-5)
    validate_observation(obs_lo, layout)

    # Vận tốc nằm trong ngưỡng an toàn (qvel = 12.5 rad/s -> 12.5 / 25.0 = 0.5)
    obs_mid, clipped_mid = build_observation(
        layout,
        qpos=qpos,
        qvel=12.5,
        act=act,
        fingertip_pos=fingertip_pos,
        target_pos=target_pos,
    )
    assert clipped_mid is False
    assert math.isclose(float(obs_mid[1]), 0.5, abs_tol=1e-5)
    validate_observation(obs_mid, layout)

    # Vận tốc bằng 0.0
    obs_zero, clipped_zero = build_observation(
        layout,
        qpos=qpos,
        qvel=0.0,
        act=act,
        fingertip_pos=fingertip_pos,
        target_pos=target_pos,
    )
    assert clipped_zero is False
    assert math.isclose(float(obs_zero[1]), 0.0, abs_tol=1e-5)
    validate_observation(obs_zero, layout)


def test_activation_slice_indices_2_to_7(default_layout: ObservationLayout) -> None:
    """Kiểm tra lát cắt kích hoạt 6 cơ tại chỉ số 2-7 và các lát cắt khác (FR-005)."""
    layout = default_layout

    # 1. Kiểm tra lát cắt kích hoạt cơ trên lớp và trên đối tượng
    assert ObservationLayout.ACTIVATION_SLICE == slice(2, 8)
    assert layout.activation_slice == slice(2, 8)
    assert layout.muscle_activation_slice == slice(2, 8)

    # Kiểm tra các chỉ số cụ thể
    sample_vector = np.arange(14, dtype=np.float32)
    activation_part = sample_vector[layout.activation_slice]
    assert len(activation_part) == 6
    np.testing.assert_array_equal(
        activation_part, np.array([2, 3, 4, 5, 6, 7], dtype=np.float32)
    )

    # 2. Kiểm tra lát cắt góc khớp và vận tốc khớp
    assert ObservationLayout.JOINT_ANGLE_SLICE == slice(0, 1)
    assert layout.joint_angle_slice == slice(0, 1)
    np.testing.assert_array_equal(
        sample_vector[layout.joint_angle_slice], np.array([0], dtype=np.float32)
    )

    assert ObservationLayout.JOINT_VELOCITY_SLICE == slice(1, 2)
    assert layout.joint_velocity_slice == slice(1, 2)
    np.testing.assert_array_equal(
        sample_vector[layout.joint_velocity_slice], np.array([1], dtype=np.float32)
    )

    # 3. Kiểm tra lát cắt vị trí đầu mút tay và mục tiêu
    assert ObservationLayout.FINGERTIP_POSITION_SLICE == slice(8, 11)
    assert layout.fingertip_position_slice == slice(8, 11)
    np.testing.assert_array_equal(
        sample_vector[layout.fingertip_position_slice], np.array([8, 9, 10], dtype=np.float32)
    )

    assert ObservationLayout.TARGET_POSITION_SLICE == slice(11, 14)
    assert layout.target_position_slice == slice(11, 14)
    np.testing.assert_array_equal(
        sample_vector[layout.target_position_slice], np.array([11, 12, 13], dtype=np.float32)
    )
