"""Kiểm thử đơn vị cho mô-đun sinh mục tiêu (tests/unit/test_targets.py).

Chứng minh các yêu cầu và bất biến kiến trúc:
- FR-010: Mục tiêu với tới được theo động học thuận, tất định theo seed.
- FR-011: Sinh hai tập train và test có giao rỗng và khoảng cách tối thiểu cấu hình được.
- INV-001: Tập train và test không giao nhau, khoảng cách Euclid 3D nhỏ nhất >= min_separation_m.
- INV-002: Với cùng seed và cùng cấu hình, kết quả sinh giống nhau hoàn toàn.
- NFR-REPRO-001: Tính tất định của bộ sinh mục tiêu (fingerprint_sha256 trùng khớp).
- API-002: Hợp đồng giao diện TargetGenerator.generate và TargetSetPair.to_dict/from_dict.
- AC-3: Kịch bản chấp nhận về tập mục tiêu train và test tách bạch, tất định theo seed.
"""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import myo_sim
import numpy as np
import pytest

from mma_ai.environment.env_config import ElbowEnvConfig, TargetConfig
from mma_ai.environment.errors import TargetConfigError
from mma_ai.environment.targets import (
    TargetGenerator,
    TargetSetPair,
)

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


@pytest.fixture  # type: ignore[untyped-decorator]
def real_elbow_model() -> mujoco.MjModel:
    """Nạp mô hình MuJoCo thật của MyoElbow từ gói myo-sim."""
    return myo_sim.load_model("myoelbow")


@pytest.fixture  # type: ignore[untyped-decorator]
def default_target_config() -> TargetConfig:
    """Lấy cấu hình mục tiêu mặc định từ ElbowEnvConfig."""
    return ElbowEnvConfig.load().targets


@pytest.fixture  # type: ignore[untyped-decorator]
def target_set_schema() -> dict[str, object]:
    """Đọc JSON Schema định nghĩa hợp đồng target-set.schema.json."""
    schema_path = (
        Path(__file__).parents[2]
        / "specs"
        / "002-elbow-muscle-env"
        / "contracts"
        / "target-set.schema.json"
    )
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_all_targets_reachable(real_elbow_model: mujoco.MjModel) -> None:
    """FR-010, AC-3: Khẳng định mọi mục tiêu sinh ra đều với tới được và đúng góc khớp."""
    generator = TargetGenerator(real_elbow_model)
    pair = generator.generate(seed=42)

    jnt_id = mujoco.mj_name2id(real_elbow_model, mujoco.mjtObj.mjOBJ_JOINT, "r_elbow_flex")
    jnt_range = real_elbow_model.jnt_range[jnt_id]
    site_id = mujoco.mj_name2id(real_elbow_model, mujoco.mjtObj.mjOBJ_SITE, "wrist")

    margin = pair.config["angle_margin_rad"]
    theta_lo = jnt_range[0] + margin
    theta_hi = jnt_range[1] - margin

    eval_data = mujoco.MjData(real_elbow_model)

    for role, target_set in [("train", pair.train), ("test", pair.test)]:
        for target in target_set:
            assert theta_lo <= target.angle_rad <= theta_hi, (
                f"Mục tiêu {role}[{target.index}] có góc {target.angle_rad} "
                f"nằm ngoài khoảng với tới [{theta_lo}, {theta_hi}]"
            )
            # Đối chiếu toạ độ 3D với động học thuận độc lập
            eval_data.qpos[0] = target.angle_rad
            mujoco.mj_kinematics(real_elbow_model, eval_data)
            expected_pos = eval_data.site_xpos[site_id]
            actual_pos = np.array(target.position_m)
            assert np.allclose(actual_pos, expected_pos, atol=1e-5), (
                f"Vị trí mục tiêu {role}[{target.index}] không khớp động học thuận: "
                f"thực tế {actual_pos}, kỳ vọng {expected_pos}"
            )


def test_min_separation(real_elbow_model: mujoco.MjModel) -> None:
    """FR-011, INV-001, AC-3: Quét >= 20 seed, khoảng cách Euclid 3D train-test >= min_sep."""
    generator = TargetGenerator(real_elbow_model)
    seeds = range(42, 65)  # 23 seeds >= 20

    for seed in seeds:
        pair = generator.generate(seed=seed)
        min_sep = pair.config["min_separation_m"]

        train_positions = np.array([t.position_m for t in pair.train])
        test_positions = np.array([t.position_m for t in pair.test])

        # Tính khoảng cách Euclidean 3D giữa mọi cặp (train, test)
        diffs = train_positions[:, np.newaxis, :] - test_positions[np.newaxis, :, :]
        distances = np.linalg.norm(diffs, axis=2)
        min_measured_d = float(np.min(distances))

        assert min_measured_d >= min_sep - 1e-6, (
            f"Seed {seed}: Khoảng cách nhỏ nhất đo được {min_measured_d:.6f} m "
            f"nhỏ hơn min_separation_m ({min_sep} m)"
        )
        assert pair.min_cross_distance_m >= min_sep - 1e-6, (
            f"Seed {seed}: min_cross_distance_m ({pair.min_cross_distance_m}) vi phạm INV-001"
        )
        assert np.isclose(pair.min_cross_distance_m, min_measured_d, atol=1e-5), (
            f"Seed {seed}: min_cross_distance_m trong kết quả ({pair.min_cross_distance_m}) "
            f"không khớp giá trị thực tế đo được ({min_measured_d})"
        )


def test_infeasible_config_raises(real_elbow_model: mujoco.MjModel) -> None:
    """FR-011, INV-001: Cấu hình bất khả thi phải ném TargetConfigError nêu rõ giới hạn vi phạm."""
    # 1. Kích thước tập bằng 0
    with pytest.raises(TargetConfigError, match="Kích thước"):
        TargetGenerator(
            real_elbow_model,
            TargetConfig(
                n_train=0,
                n_test=50,
                min_separation_m=0.02,
                split_block_m=0.05,
                angle_margin_rad=0.05,
                default_seed=42,
            ),
        ).generate(seed=42)

    with pytest.raises(TargetConfigError, match="Kích thước"):
        TargetGenerator(
            real_elbow_model,
            TargetConfig(
                n_train=200,
                n_test=0,
                min_separation_m=0.02,
                split_block_m=0.05,
                angle_margin_rad=0.05,
                default_seed=42,
            ),
        ).generate(seed=42)

    # 2. split_block_m <= 1.1 * min_separation_m
    with pytest.raises(TargetConfigError, match="phải lớn hơn 1,1 lần"):
        TargetGenerator(
            real_elbow_model,
            TargetConfig(
                n_train=200,
                n_test=50,
                min_separation_m=0.05,
                split_block_m=0.05,
                angle_margin_rad=0.05,
                default_seed=42,
            ),
        ).generate(seed=42)

    with pytest.raises(TargetConfigError, match="phải lớn hơn 1,1 lần"):
        TargetGenerator(
            real_elbow_model,
            TargetConfig(
                n_train=200,
                n_test=50,
                min_separation_m=0.02,
                split_block_m=0.022,
                angle_margin_rad=0.05,
                default_seed=42,
            ),
        ).generate(seed=42)

    # 3. Số khối < 2 (ví dụ split_block_m quá lớn so với cung)
    with pytest.raises(TargetConfigError, match="nhỏ hơn 2"):
        TargetGenerator(
            real_elbow_model,
            TargetConfig(
                n_train=200,
                n_test=50,
                min_separation_m=0.02,
                split_block_m=1.0,
                angle_margin_rad=0.05,
                default_seed=42,
            ),
        ).generate(seed=42)


def test_same_seed_same_fingerprint(real_elbow_model: mujoco.MjModel) -> None:
    """INV-002, NFR-REPRO-001, AC-3: Cùng seed và config sinh ra kết quả giống nhau hoàn toàn."""
    generator = TargetGenerator(real_elbow_model)

    pair_1 = generator.generate(seed=123)
    pair_2 = generator.generate(seed=123)

    assert pair_1.fingerprint_sha256 == pair_2.fingerprint_sha256, (
        f"Lệch fingerprint: {pair_1.fingerprint_sha256} != {pair_2.fingerprint_sha256}"
    )
    assert pair_1.train.to_dict() == pair_2.train.to_dict()
    assert pair_1.test.to_dict() == pair_2.test.to_dict()
    assert pair_1.to_dict() == pair_2.to_dict()


def test_different_size_same_seed_still_disjoint(real_elbow_model: mujoco.MjModel) -> None:
    """INV-001, AC-3: Khác kích thước tập cùng seed vẫn đảm bảo giao rỗng và đạt khoảng cách."""
    cfg_large = TargetConfig(
        n_train=100,
        n_test=30,
        min_separation_m=0.02,
        split_block_m=0.05,
        angle_margin_rad=0.05,
        default_seed=42,
    )
    cfg_small = TargetConfig(
        n_train=10,
        n_test=5,
        min_separation_m=0.02,
        split_block_m=0.05,
        angle_margin_rad=0.05,
        default_seed=42,
    )

    pair_large = TargetGenerator(real_elbow_model, cfg_large).generate(seed=999)
    pair_small = TargetGenerator(real_elbow_model, cfg_small).generate(seed=999)

    for pair in [pair_large, pair_small]:
        assert pair.min_cross_distance_m >= 0.02 - 1e-6
        train_angles = [t.angle_rad for t in pair.train]
        test_angles = [t.angle_rad for t in pair.test]
        # Không có góc nào giao nhau
        assert len(set(train_angles).intersection(set(test_angles))) == 0


def test_no_duplicate_points(real_elbow_model: mujoco.MjModel) -> None:
    """FR-010: Khẳng định không có điểm nào bị trùng lặp trong cùng một tập."""
    generator = TargetGenerator(real_elbow_model)
    pair = generator.generate(seed=777)

    for role, t_set in [("train", pair.train), ("test", pair.test)]:
        angles = [t.angle_rad for t in t_set]
        assert len(angles) == len(set(angles)), f"Tập {role} chứa các điểm có góc trùng nhau"

        positions = [tuple(t.position_m) for t in t_set]
        assert len(positions) == len(set(positions)), (
            f"Tập {role} chứa các điểm có vị trí trùng nhau"
        )


def test_roundtrip_to_from_dict(
    real_elbow_model: mujoco.MjModel, target_set_schema: dict[str, object]
) -> None:
    """API-002, FR-011: Kiểm tra to_dict() và roundtrip from_dict() bảo toàn dữ liệu."""
    generator = TargetGenerator(real_elbow_model)
    pair = generator.generate(seed=42)

    data = pair.to_dict()

    # Kiểm tra cấu trúc bắt buộc theo hợp đồng target-set.schema.json
    for key in [
        "schema_version",
        "master_seed",
        "model_sha256",
        "config",
        "arc",
        "train",
        "test",
        "min_cross_distance_m",
        "fingerprint_sha256",
    ]:
        assert key in data, f"to_dict() thiếu trường bắt buộc: {key}"

    # Xác thực với JSON Schema nếu thư viện jsonschema có sẵn
    if jsonschema is not None:
        jsonschema.validate(instance=data, schema=target_set_schema)

    # Roundtrip khôi phục đối tượng
    restored_pair = TargetSetPair.from_dict(data)

    assert restored_pair.master_seed == pair.master_seed
    assert restored_pair.model_sha256 == pair.model_sha256
    assert restored_pair.min_cross_distance_m == pair.min_cross_distance_m
    assert restored_pair.fingerprint_sha256 == pair.fingerprint_sha256
    assert restored_pair.arc == pair.arc
    assert len(restored_pair.train) == len(pair.train)
    assert len(restored_pair.test) == len(pair.test)
    assert restored_pair.to_dict() == data


def test_generation_does_not_touch_sim_data(real_elbow_model: mujoco.MjModel) -> None:
    """INV-003, AC-4, FR-010: Sinh mục tiêu không được thay đổi trạng thái MjData của episode."""
    sim_data = mujoco.MjData(real_elbow_model)

    # Đặt trạng thái tuỳ chỉnh mô phỏng
    sim_data.qpos[0] = 1.2345
    sim_data.qvel[0] = 6.7890
    sim_data.ctrl[:] = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    mujoco.mj_step(real_elbow_model, sim_data)

    saved_qpos = sim_data.qpos.copy()
    saved_qvel = sim_data.qvel.copy()
    saved_act = sim_data.act.copy()
    saved_ctrl = sim_data.ctrl.copy()
    saved_time = sim_data.time

    generator = TargetGenerator(real_elbow_model)
    _ = generator.generate(seed=42)

    # Khẳng định sim_data không bị chạm tới
    assert np.array_equal(sim_data.qpos, saved_qpos), (
        "sim_data.qpos bị thay đổi trong quá trình sinh mục tiêu"
    )
    assert np.array_equal(sim_data.qvel, saved_qvel), (
        "sim_data.qvel bị thay đổi trong quá trình sinh mục tiêu"
    )
    assert np.array_equal(sim_data.act, saved_act), (
        "sim_data.act bị thay đổi trong quá trình sinh mục tiêu"
    )
    assert np.array_equal(sim_data.ctrl, saved_ctrl), (
        "sim_data.ctrl bị thay đổi trong quá trình sinh mục tiêu"
    )
    assert sim_data.time == saved_time, (
        "sim_data.time bị thay đổi trong quá trình sinh mục tiêu"
    )
