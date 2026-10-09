"""Kiểm thử tích hợp lựa chọn tập mục tiêu khi reset (FR-012)."""

from __future__ import annotations

import re
from typing import Any

import pytest

from mma_ai.environment.errors import EnvConfigError


def _make_env(*, split: str = "train") -> Any:
    """Tạo môi trường thật với vai trò tập mục tiêu được chỉ định."""
    from mma_ai.environment.single_agent import ElbowReachEnv

    return ElbowReachEnv(split=split)


def _positions(targets: Any) -> set[tuple[float, float, float]]:
    """Chuẩn hoá vị trí mục tiêu để đối chiếu độc lập với metadata reset."""
    return {
        (
            float(target.position_m[0]),
            float(target.position_m[1]),
            float(target.position_m[2]),
        )
        for target in targets
    }


def _assert_samples_only_split(env: Any, split: str) -> None:
    """Kiểm tra 200 seed chỉ chọn vị trí thuộc đúng tập mục tiêu."""
    selected_positions = _positions(getattr(env.targets, split).targets)
    opposite_split = "test" if split == "train" else "train"
    excluded_positions = _positions(getattr(env.targets, opposite_split).targets)

    for seed in range(200):
        _, info = env.reset(seed=seed, options={"split": split})
        position = tuple(info["target_position_m"])

        assert info["target_split"] == split
        assert position in selected_positions
        assert position not in excluded_positions


def test_ac_3_test_split_never_samples_train_from_config_or_options() -> None:
    """AC-3, INV-001: test không bao giờ lấy mục tiêu train qua config hay options."""
    _assert_samples_only_split(_make_env(split="test"), "test")
    _assert_samples_only_split(_make_env(), "test")


def test_inv_001_train_split_never_samples_test() -> None:
    """INV-001, AC-3: train không bao giờ lấy mục tiêu test."""
    _assert_samples_only_split(_make_env(split="train"), "train")


def test_fr_012_reset_info_fields_follow_schema() -> None:
    """FR-012, AC-3: metadata reset khớp đúng hợp đồng reset-info.schema.json."""
    _, info = _make_env(split="test").reset(seed=20261009)
    assert set(info) == {
        "seed",
        "target_split",
        "target_index",
        "target_position_m",
        "initial_distance_m",
        "model_sha256",
    }
    assert info["target_split"] == "test"
    assert info["seed"] == 20261009
    assert isinstance(info["target_index"], int)
    assert info["target_index"] >= 0
    assert len(info["target_position_m"]) == 3
    assert all(isinstance(coordinate, (int, float)) for coordinate in info["target_position_m"])
    assert isinstance(info["initial_distance_m"], float)
    assert info["initial_distance_m"] >= 0
    assert re.fullmatch(r"[0-9a-f]{64}", info["model_sha256"])


def test_inv_002_reset_seed_none_records_reusable_seed() -> None:
    """INV-002, AC-3: seed được rút lại tái tạo cùng mục tiêu khi dùng lại."""
    env = _make_env(split="test")
    _, generated_info = env.reset(seed=None)
    _, replayed_info = env.reset(seed=generated_info["seed"])

    assert generated_info["seed"] >= 0
    assert replayed_info["target_split"] == generated_info["target_split"] == "test"
    assert replayed_info["target_index"] == generated_info["target_index"]
    assert replayed_info["target_position_m"] == generated_info["target_position_m"]


def test_fr_012_split_option_overrides_config() -> None:
    """FR-012, AC-3: options split có ưu tiên hơn cấu hình môi trường."""
    _, info = _make_env(split="train").reset(seed=17, options={"split": "test"})

    assert info["target_split"] == "test"


def test_fr_012_unknown_split_rejected() -> None:
    """FR-012: split ngoài train/test bị từ chối thay vì rơi sang test."""
    with pytest.raises(EnvConfigError):
        _make_env().reset(seed=17, options={"split": "holdout"})
