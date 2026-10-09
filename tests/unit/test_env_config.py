"""Bộ kiểm thử đơn vị cho mô-đun cấu hình môi trường (mma_ai.environment.env_config).

Kiểm chứng các yêu cầu chức năng và bất biến của cấu hình môi trường khuỷu tay:
- FR-014: Cấu hình tập trung duy nhất, không rải hằng số trong mã.
- API-002: ElbowEnvConfig.load(path=None) -> ElbowEnvConfig.
- INV-001: Ràng buộc chéo split_block_m > 1.1 * min_separation_m chống rò rỉ mục tiêu.
- AC-2: Tham số mô phỏng, reward và observation cấu hình được và có giới hạn hợp lệ.
- AC-3: Tham số tập mục tiêu train/test cấu hình được và đảm bảo tính phân tách.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from mma_ai.environment.env_config import (
    ElbowEnvConfig,
    ObsConfig,
    RewardConfig,
    TargetConfig,
)
from mma_ai.environment.errors import EnvConfigError


def _valid_config_dict() -> dict[str, Any]:
    """Tạo bản sao từ điển cấu hình hợp lệ dựa trên cấu hình mặc định."""
    return {
        "schema_version": "1.0.0",
        "physics_timestep_s": 0.0025,
        "substeps_per_action": 16,
        "fingertip_site": "wrist",
        "target_split": "train",
        "reward": {
            "w_dist": 1.0,
            "w_effort": 0.01,
            "d_ref_m": 0.5,
        },
        "tolerance_m": 0.02,
        "max_actions": 100,
        "obs": {
            "qvel_scale_rad_s": 25.0,
        },
        "targets": {
            "n_train": 200,
            "n_test": 50,
            "min_separation_m": 0.02,
            "split_block_m": 0.05,
            "angle_margin_rad": 0.05,
            "default_seed": 42,
        },
    }


def test_defaults_load() -> None:
    """Nạp cấu hình mặc định từ gói đóng sẵn thành công (FR-014, API-002, AC-2, AC-3)."""
    cfg = ElbowEnvConfig.load()

    assert isinstance(cfg, ElbowEnvConfig)
    assert cfg.schema_version == "1.0.0"
    assert cfg.physics_timestep_s == 0.0025
    assert cfg.substeps_per_action == 16
    assert cfg.fingertip_site == "wrist"
    assert cfg.target_split == "train"
    assert cfg.tolerance_m == 0.02
    assert cfg.max_actions == 100

    assert isinstance(cfg.reward, RewardConfig)
    assert cfg.reward.w_dist == 1.0
    assert cfg.reward.w_effort == 0.01
    assert cfg.reward.d_ref_m == 0.5

    assert isinstance(cfg.obs, ObsConfig)
    assert cfg.obs.qvel_scale_rad_s == 25.0

    assert isinstance(cfg.targets, TargetConfig)
    assert cfg.targets.n_train == 200
    assert cfg.targets.n_test == 50
    assert cfg.targets.min_separation_m == 0.02
    assert cfg.targets.split_block_m == 0.05
    assert cfg.targets.angle_margin_rad == 0.05
    assert cfg.targets.default_seed == 42


def test_defaults_equal_example_json() -> None:
    """Giá trị mặc định khớp chính xác với env-config.default.json (FR-014, API-002)."""
    contract_example_path = (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "002-elbow-muscle-env"
        / "contracts"
        / "examples"
        / "env-config.default.json"
    )
    with contract_example_path.open("r", encoding="utf-8") as f:
        expected_data = json.load(f)

    cfg = ElbowEnvConfig.load()
    assert cfg.to_dict() == expected_data


def test_config_is_immutable() -> None:
    """Đối tượng cấu hình và các thành phần con là bất biến (frozen dataclass) (FR-014)."""
    cfg = ElbowEnvConfig.load()

    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.physics_timestep_s = 0.01  # type: ignore[misc]

    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.reward.w_dist = 2.0  # type: ignore[misc]

    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.obs.qvel_scale_rad_s = 50.0  # type: ignore[misc]

    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.targets.n_train = 300  # type: ignore[misc]


def test_override_path_loads(tmp_path: Path) -> None:
    """Nạp cấu hình tuỳ chỉnh từ đường dẫn tệp chỉ định thành công (FR-014, API-002)."""
    custom_dict = _valid_config_dict()
    custom_dict["substeps_per_action"] = 20
    custom_dict["target_split"] = "test"
    custom_dict["targets"]["default_seed"] = 999

    custom_yaml = tmp_path / "custom_elbow_env.yaml"
    custom_yaml.write_text(yaml.safe_dump(custom_dict), encoding="utf-8")

    cfg = ElbowEnvConfig.load(custom_yaml)
    assert cfg.substeps_per_action == 20
    assert cfg.target_split == "test"
    assert cfg.targets.default_seed == 999


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("key_path", "invalid_value"),
    [
        (["physics_timestep_s"], 0.0),
        (["physics_timestep_s"], -0.001),
        (["physics_timestep_s"], "0.0025"),
        (["substeps_per_action"], 0),
        (["substeps_per_action"], -1),
        (["substeps_per_action"], 1.5),
        (["substeps_per_action"], True),
        (["fingertip_site"], ""),
        (["target_split"], "validation"),
        (["target_split"], 123),
        (["tolerance_m"], 0.0),
        (["tolerance_m"], -0.02),
        (["max_actions"], 0),
        (["max_actions"], -10),
        (["schema_version"], "2.0.0"),
        (["reward", "w_dist"], -0.1),
        (["reward", "w_effort"], -0.01),
        (["reward", "d_ref_m"], 0.0),
        (["reward", "d_ref_m"], -0.5),
        (["obs", "qvel_scale_rad_s"], 0.0),
        (["obs", "qvel_scale_rad_s"], -1.0),
        (["targets", "n_train"], 0),
        (["targets", "n_train"], -1),
        (["targets", "n_test"], 0),
        (["targets", "n_test"], -1),
        (["targets", "min_separation_m"], 0.0),
        (["targets", "min_separation_m"], -0.02),
        (["targets", "split_block_m"], 0.0),
        (["targets", "split_block_m"], -0.05),
        (["targets", "angle_margin_rad"], -0.01),
        (["targets", "default_seed"], -1),
    ],
)
def test_invalid_values_raise(
    tmp_path: Path,
    key_path: list[str],
    invalid_value: Any,
) -> None:
    """Ném EnvConfigError khi giá trị cấu hình vi phạm miền hợp lệ (FR-014, AC-2, AC-3)."""
    data = _valid_config_dict()
    curr: dict[str, Any] = data
    for key in key_path[:-1]:
        curr = curr[key]
    curr[key_path[-1]] = invalid_value

    test_yaml = tmp_path / "invalid_cfg.yaml"
    test_yaml.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(EnvConfigError) as exc_info:
        ElbowEnvConfig.load(test_yaml)
    assert key_path[-1] in str(exc_info.value)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("min_separation", "split_block"),
    [
        (0.02, 0.02),
        (0.02, 0.021),
        (0.02, 0.022),
        (0.05, 0.055),
    ],
)
def test_cross_constraint_split_block_vs_min_separation_raises(
    tmp_path: Path,
    min_separation: float,
    split_block: float,
) -> None:
    """Ném EnvConfigError khi vi phạm bất biến INV-001 (split_block_m <= 1.1 * min_separation_m)."""
    data = _valid_config_dict()
    data["targets"]["min_separation_m"] = min_separation
    data["targets"]["split_block_m"] = split_block

    test_yaml = tmp_path / "cross_constraint_invalid.yaml"
    test_yaml.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(EnvConfigError) as exc_info:
        ElbowEnvConfig.load(test_yaml)
    error_msg = str(exc_info.value)
    assert "split_block_m" in error_msg
    assert "min_separation_m" in error_msg


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "missing_key",
    [
        "schema_version",
        "physics_timestep_s",
        "substeps_per_action",
        "fingertip_site",
        "target_split",
        "reward",
        "tolerance_m",
        "max_actions",
        "obs",
        "targets",
    ],
)
def test_missing_root_key_raises(tmp_path: Path, missing_key: str) -> None:
    """Ném EnvConfigError khi thiếu bất kỳ khoá bắt buộc nào ở cấp gốc (FR-014)."""
    data = _valid_config_dict()
    del data[missing_key]

    test_yaml = tmp_path / "missing_root.yaml"
    test_yaml.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(EnvConfigError) as exc_info:
        ElbowEnvConfig.load(test_yaml)
    assert missing_key in str(exc_info.value)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("section", "missing_key"),
    [
        ("reward", "w_dist"),
        ("reward", "w_effort"),
        ("reward", "d_ref_m"),
        ("obs", "qvel_scale_rad_s"),
        ("targets", "n_train"),
        ("targets", "n_test"),
        ("targets", "min_separation_m"),
        ("targets", "split_block_m"),
        ("targets", "angle_margin_rad"),
        ("targets", "default_seed"),
    ],
)
def test_missing_sub_key_raises(
    tmp_path: Path, section: str, missing_key: str
) -> None:
    """Ném EnvConfigError khi thiếu khoá bắt buộc trong phân đoạn con (FR-014)."""
    data = _valid_config_dict()
    del data[section][missing_key]

    test_yaml = tmp_path / "missing_sub.yaml"
    test_yaml.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(EnvConfigError) as exc_info:
        ElbowEnvConfig.load(test_yaml)
    assert missing_key in str(exc_info.value)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("location", "extra_key"),
    [
        ("root", "unknown_root_key"),
        ("reward", "unknown_reward_key"),
        ("obs", "unknown_obs_key"),
        ("targets", "unknown_targets_key"),
    ],
)
def test_extra_key_raises(tmp_path: Path, location: str, extra_key: str) -> None:
    """Ném EnvConfigError khi có khoá lạ không nằm trong hợp đồng schema (FR-014)."""
    data = _valid_config_dict()
    if location == "root":
        data[extra_key] = 123
    else:
        data[location][extra_key] = 123

    test_yaml = tmp_path / "extra_key.yaml"
    test_yaml.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(EnvConfigError) as exc_info:
        ElbowEnvConfig.load(test_yaml)
    assert extra_key in str(exc_info.value)


def test_file_not_found_raises() -> None:
    """Ném EnvConfigError khi đường dẫn tệp cấu hình không tồn tại (FR-014, API-002)."""
    with pytest.raises(EnvConfigError):
        ElbowEnvConfig.load(Path("duong_dan_khong_ton_tai/elbow_env.yaml"))


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    """Ném EnvConfigError khi tệp cấu hình chứa cú pháp YAML hỏng (FR-014, API-002)."""
    corrupt_file = tmp_path / "corrupt.yaml"
    corrupt_file.write_text("physics_timestep_s: [unclosed_list", encoding="utf-8")

    with pytest.raises(EnvConfigError):
        ElbowEnvConfig.load(corrupt_file)


def test_non_dict_content_raises(tmp_path: Path) -> None:
    """Ném EnvConfigError khi nội dung tệp YAML không phải là từ điển mapping (FR-014)."""
    list_file = tmp_path / "list.yaml"
    list_file.write_text("- item1\n- item2\n", encoding="utf-8")

    with pytest.raises(EnvConfigError):
        ElbowEnvConfig.load(list_file)
