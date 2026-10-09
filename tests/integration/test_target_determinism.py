"""Kiểm thử tích hợp tính tất định và tách biệt của tập mục tiêu.

Chứng minh AC-3, FR-010, FR-011, INV-001, INV-002, NFR-REPRO-001 và SC-003
trên mô hình MuJoCo thật, kể cả giữa các tiến trình có hash seed khác nhau.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import numpy as np

from mma_ai.environment.targets import TargetGenerator


def _make_env() -> Any:
    """Tạo môi trường thật sau khi pytest đã thiết lập môi trường thực thi."""
    from mma_ai.environment.single_agent import ElbowReachEnv

    return ElbowReachEnv()


def _target_coordinates(targets: Any) -> np.ndarray:
    """Chuyển vị trí mục tiêu thành ma trận toạ độ 3D để đo độc lập."""
    return np.asarray([target.position_m for target in targets], dtype=np.float64)


def _assert_disjoint_with_minimum_distance(pair: Any) -> None:
    """Đo độc lập giao rỗng và khoảng cách Euclid giữa hai tập mục tiêu."""
    train_positions = _target_coordinates(pair.train.targets)
    test_positions = _target_coordinates(pair.test.targets)
    distances = np.linalg.norm(
        train_positions[:, np.newaxis, :] - test_positions[np.newaxis, :, :], axis=2
    )

    assert not set(map(tuple, train_positions)).intersection(map(tuple, test_positions))
    assert float(np.min(distances)) >= pair.config["min_separation_m"] - 1e-9


def _generate_in_subprocess(hash_seed: str) -> dict[str, object]:
    """Sinh dữ liệu chuẩn hoá trong tiến trình mới với PYTHONHASHSEED chỉ định."""
    project_root = Path(__file__).parents[2]
    script = """
import json
import sys

sys.path.insert(0, sys.argv[1])
from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.environment.targets import TargetGenerator

env = ElbowReachEnv()
pair = TargetGenerator(env.model, env.cfg).generate(seed=137)
print(json.dumps(pair.to_dict(), sort_keys=True))
"""
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = hash_seed
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    completed = subprocess.run(
        [sys.executable, "-c", script, str(project_root / "src")],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    return cast(dict[str, object], json.loads(completed.stdout))


def test_ac_3_same_seed_same_sets_across_process_hash_seeds() -> None:
    """AC-3, INV-002, NFR-REPRO-001: Cùng seed cho dữ liệu giống nhau xuyên tiến trình."""
    env = _make_env()
    local_first = TargetGenerator(env.model, env.cfg).generate(seed=137)
    local_second = TargetGenerator(env.model, env.cfg).generate(seed=137)
    first = _generate_in_subprocess("1")
    second = _generate_in_subprocess("8675309")

    assert local_first.to_dict() == local_second.to_dict()
    assert local_first.fingerprint_sha256 == local_second.fingerprint_sha256
    assert first == second
    assert first == local_first.to_dict()


def test_inv_001_train_test_disjoint_with_independent_euclidean_measurement() -> None:
    """INV-001, AC-3, FR-011: Train/test rời nhau và cách nhau đủ xa theo phép đo độc lập."""
    env = _make_env()

    _assert_disjoint_with_minimum_distance(env.targets)


def test_inv_001_two_seeds_each_disjoint_property() -> None:
    """INV-001, FR-011, SC-003: Thuộc tính tách biệt đúng cho 100 seed được sinh xác định."""
    env = _make_env()
    seeds = np.random.default_rng(20261009).integers(0, 2**31 - 1, size=100)

    for seed in seeds:
        pair = TargetGenerator(env.model, env.cfg).generate(seed=int(seed))
        _assert_disjoint_with_minimum_distance(pair)


def test_inv_002_reset_same_seed_same_target() -> None:
    """INV-002, AC-3: reset cùng seed chọn cùng mục tiêu trong cùng split."""
    first_env = _make_env()
    second_env = _make_env()

    first_obs, first_info = first_env.reset(seed=20261009, options={"split": "test"})
    second_obs, second_info = second_env.reset(seed=20261009, options={"split": "test"})

    assert first_info["target_split"] == second_info["target_split"] == "test"
    assert first_info["target_index"] == second_info["target_index"]
    assert first_info["target_position_m"] == second_info["target_position_m"]
    assert np.array_equal(first_obs, second_obs)
