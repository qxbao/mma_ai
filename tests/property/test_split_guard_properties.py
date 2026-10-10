"""Kiểm thử đặc tính (property-based) cho split_guard (INV-001, FR-008).

Bảo vệ bất biến INV-001 trên không gian hạt giống và cấu hình ngẫu nhiên:
- INV-001: Trùng lặp giữa dải seed episode/random policy với train seeds đều bị từ chối.
- FR-008: Báo cáo trả về luôn đảm bảo min_cross_distance_m >= min_required_m và passed=True.
"""

from __future__ import annotations

import random

import pytest

from mma_ai.environment.targets import (
    ArcInfo,
    Target,
    TargetSet,
    TargetSetPair,
    compute_fingerprint,
)
from mma_ai.evaluation.errors import LeakageError
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.split_guard import check_disjoint


def _make_property_pair(min_sep: float = 0.03) -> TargetSetPair:
    train_targets = tuple(
        Target(index=i, angle_rad=0.1 * i, position_m=(0.1 * i, 0.2, 0.3)) for i in range(3)
    )
    test_targets = tuple(
        Target(index=i, angle_rad=0.2 * i, position_m=(0.5 + 0.1 * i, 0.6, 0.7)) for i in range(3)
    )
    arc = ArcInfo(usable_length_m=0.3, n_blocks=10, train_blocks=(0, 1), test_blocks=(5, 6))
    fp = compute_fingerprint(train_targets, test_targets)
    return TargetSetPair(
        master_seed=42,
        model_sha256="384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
        config={"min_separation_m": min_sep},
        arc=arc,
        train=TargetSet("train", train_targets),
        test=TargetSet("test", test_targets),
        min_cross_distance_m=0.4,
        fingerprint_sha256=fp,
    )


def test_inv_001_seed_overlap_always_detected() -> None:
    """INV-001: Bất kỳ hạt giống nào trùng lặp ngẫu nhiên trong chuỗi đều gây ra LeakageError."""
    pair = _make_property_pair()
    rng = random.Random(20261012)

    for _ in range(50):
        train_seed = rng.randint(0, 100_000)
        n_targets = len(pair.test)
        repeats = rng.randint(1, 5)
        n_episodes = n_targets * repeats

        # Chọn seed vi phạm nằm ngay trong dải [ep_base, ep_base + n_episodes)
        offset = rng.randint(0, n_episodes - 1)
        ep_base = train_seed - offset

        manifest_data = {
            "run_id": f"run_test_{train_seed}",
            "status": "done",
            "seed": train_seed,
            "resumed_from": None,
            "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
        }

        # Cấu hình chứa ep_base mà dải sẽ phủ trúng train_seed
        cfg = EvalConfig.load(
            overrides={"seeds.episode_base": ep_base, "episodes.repeats": repeats}
        )

        with pytest.raises(LeakageError):
            check_disjoint(manifest_data, cfg, pair)


def test_inv_001_disjoint_seeds_always_pass() -> None:
    """INV-001: Khi các hạt giống hoàn toàn phân tách, kiểm tra luôn thành công và passed=True."""
    pair = _make_property_pair()
    rng = random.Random(20261013)

    for _ in range(50):
        train_seed = rng.randint(100, 200)
        # Chọn dải episode xa khỏi train_seed
        ep_base = rng.randint(1000, 5000)
        rand_policy_seed = rng.randint(6000, 9000)

        manifest_data = {
            "run_id": f"run_test_{train_seed}",
            "status": "done",
            "seed": train_seed,
            "resumed_from": None,
            "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
        }

        base_cfg = EvalConfig.load(overrides={"seeds.episode_base": ep_base})
        cfg = EvalConfig(
            schema_version=base_cfg.schema_version,
            seeds=type(base_cfg.seeds)(episode_base=ep_base, random_policy=rand_policy_seed),
            episodes=base_cfg.episodes,
            criterion=base_cfg.criterion,
            stats=base_cfg.stats,
            logs=base_cfg.logs,
            charts=base_cfg.charts,
            paths=base_cfg.paths,
        )

        report = check_disjoint(manifest_data, cfg, pair)
        assert report.passed is True
        assert report.checked is True
        assert report.min_cross_distance_m >= report.min_required_m
        assert report.random_policy_seed == rand_policy_seed
        assert report.train_seeds == (train_seed,)
