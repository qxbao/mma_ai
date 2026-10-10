"""Kiểm thử đơn vị cho mô-đun split_guard (mma_ai.evaluation.split_guard).

Bao phủ các yêu cầu và bất biến cốt lõi:
- FR-008: Kiểm tra tập đánh giá không giao tập huấn luyện (giao rỗng mục tiêu và khoảng cách).
- FR-009: Từ chối đánh giá khi không thiết lập được tập huấn luyện (TrainSetUnknown).
- INV-001: Tập đánh giá không giao tập train, khoảng cách >= min_required_m, seed không trùng.
- API-EVL-0003: Giao diện check_disjoint(run, cfg, pair) -> DisjointnessReport.
- AC-4: Kiểm tra rò rỉ (leakage) trước khi chạy bất kỳ episode đánh giá nào.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mma_ai.environment.targets import (
    ArcInfo,
    Target,
    TargetSet,
    TargetSetPair,
    compute_fingerprint,
)
from mma_ai.evaluation.errors import LeakageError, TrainSetUnknown
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.split_guard import DisjointnessReport, check_disjoint


def _create_sample_target_pair(
    *,
    min_separation_m: float = 0.03,
    train_positions: list[tuple[float, float, float]] | None = None,
    test_positions: list[tuple[float, float, float]] | None = None,
) -> TargetSetPair:
    """Tạo cặp tập mục tiêu mẫu phục vụ kiểm thử (FR-008, INV-001)."""
    t_pos = train_positions or [(0.1, 0.2, 0.3), (0.15, 0.25, 0.35)]
    e_pos = test_positions or [(0.3, 0.4, 0.5), (0.35, 0.45, 0.55)]

    train_targets = tuple(
        Target(index=i, angle_rad=0.1 * i, position_m=pos) for i, pos in enumerate(t_pos)
    )
    test_targets = tuple(
        Target(index=i, angle_rad=0.2 * i, position_m=pos) for i, pos in enumerate(e_pos)
    )

    arc = ArcInfo(
        usable_length_m=0.3,
        n_blocks=10,
        train_blocks=(0, 1, 2),
        test_blocks=(5, 6, 7),
    )
    fp = compute_fingerprint(train_targets, test_targets)
    return TargetSetPair(
        master_seed=42,
        model_sha256="384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
        config={"min_separation_m": min_separation_m},
        arc=arc,
        train=TargetSet("train", train_targets),
        test=TargetSet("test", test_targets),
        min_cross_distance_m=0.15,
        fingerprint_sha256=fp,
    )


def test_disjoint_targets_and_min_distance_ok(tmp_path: Path) -> None:
    """FR-008, INV-001, AC-4, API-EVL-0003: Mục tiêu không giao nhau và hạt giống phân tách."""
    cfg = EvalConfig.load()
    pair = _create_sample_target_pair(min_separation_m=0.03)

    manifest_data = {
        "run_id": "20261010T080000Z_elbow_s42",
        "status": "done",
        "seed": 42,
        "resumed_from": None,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
        "model": {"sha256": pair.model_sha256},
    }

    report = check_disjoint(manifest_data, cfg, pair)

    assert isinstance(report, DisjointnessReport)
    assert report.checked is True
    assert report.passed is True
    assert report.min_cross_distance_m >= report.min_required_m
    assert report.n_train_targets == 2
    assert report.n_eval_targets == 2
    assert report.n_checked > 0
    assert report.random_policy_seed == cfg.seeds.random_policy
    assert report.train_seeds == (42,)
    assert report.eval_seed_range == (
        cfg.seeds.episode_base,
        cfg.seeds.episode_base + len(pair.test) * cfg.episodes.repeats,
    )
    assert report.provenance in ("rebuilt_from_config", "manifest_fingerprint")

    # Kiểm tra tính hợp lệ của từ điển xuất ra
    report_dict = report.to_dict()
    assert report_dict["passed"] is True
    assert report_dict["checked"] is True
    assert report_dict["min_cross_distance_m"] >= report_dict["min_required_m"]


def test_seed_equal_train_seed_rejected() -> None:
    """FR-008, INV-001, AC-4: Từ chối khi hạt giống random policy trùng hạt giống huấn luyện."""
    pair = _create_sample_target_pair()
    train_seed = 42

    manifest_data = {
        "run_id": "20261010T080000Z_elbow_s42",
        "status": "done",
        "seed": train_seed,
        "resumed_from": None,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
    }

    # Đặt seed của random policy trùng đúng seed của run huấn luyện
    cfg = EvalConfig.load(overrides={"seeds.episode_base": 1000})
    bad_cfg = EvalConfig(
        schema_version=cfg.schema_version,
        seeds=type(cfg.seeds)(episode_base=1000, random_policy=train_seed),
        episodes=cfg.episodes,
        criterion=cfg.criterion,
        stats=cfg.stats,
        logs=cfg.logs,
        charts=cfg.charts,
        paths=cfg.paths,
    )

    with pytest.raises(LeakageError, match="trùng với seed"):
        check_disjoint(manifest_data, bad_cfg, pair)


def test_seed_range_overlap_rejected() -> None:
    """FR-008, INV-001, AC-4: Từ chối khi dải hạt giống episode giao cắt hạt giống huấn luyện."""
    pair = _create_sample_target_pair()
    train_seed = 102

    manifest_data = {
        "run_id": "20261010T080000Z_elbow_s102",
        "status": "done",
        "seed": train_seed,
        "resumed_from": None,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
    }

    # episode_base = 100, n_targets = 2, repeats = 2 => dải seed [100, 104) chứa train_seed 102
    base_cfg = EvalConfig.load(overrides={"episodes.repeats": 2, "seeds.episode_base": 100})

    with pytest.raises(LeakageError, match="giao với seed huấn luyện"):
        check_disjoint(manifest_data, base_cfg, pair)


def test_target_within_min_distance_rejected() -> None:
    """FR-008, INV-001, AC-4: Từ chối khi mục tiêu nằm trong khoảng cách tối thiểu của tập train."""
    cfg = EvalConfig.load()

    # Mục tiêu đánh giá và tập train cách nhau chỉ 0.005m trong khi min_separation_m = 0.03m
    pair_with_close_target = _create_sample_target_pair(
        min_separation_m=0.03,
        train_positions=[(0.0, 0.0, 0.0)],
        test_positions=[(0.005, 0.0, 0.0)],
    )

    manifest_data = {
        "run_id": "20261010T080000Z_elbow_s42",
        "status": "done",
        "seed": 42,
        "resumed_from": None,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
    }

    with pytest.raises(LeakageError, match="khoảng cách tối thiểu"):
        check_disjoint(manifest_data, cfg, pair_with_close_target)


def test_unknown_train_set_refused(tmp_path: Path) -> None:
    """FR-009, INV-001, AC-4: Từ chối (TrainSetUnknown) khi thiếu seed hoặc cấu hình môi trường."""
    cfg = EvalConfig.load()

    # Ca 1: Thiếu hoàn toàn seed
    bad_manifest_no_seed = {
        "run_id": "20261010T080000Z_elbow",
        "status": "done",
        "resumed_from": None,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
    }
    with pytest.raises(TrainSetUnknown, match="thiếu seed"):
        check_disjoint(bad_manifest_no_seed, cfg)

    # Ca 2: Thiếu cấu hình môi trường và không truyền pair
    bad_manifest_no_env = {
        "run_id": "20261010T080000Z_elbow_s42",
        "status": "done",
        "seed": 42,
        "resumed_from": None,
        "config": {},
    }
    with pytest.raises(TrainSetUnknown, match="cấu hình môi trường"):
        check_disjoint(bad_manifest_no_env, cfg)

    # Ca 3: Đường dẫn run không tồn tại
    non_existent = tmp_path / "non_existent_run"
    with pytest.raises(TrainSetUnknown, match="Không tìm thấy"):
        check_disjoint(non_existent, cfg)


def test_resume_chain_seeds_collected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-008, INV-001, AC-4: Thu thập đầy đủ chuỗi hạt giống từ các run cha và chặn trùng lặp."""
    monkeypatch.chdir(tmp_path)
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Run gốc (ông nội): seed = 10
    run_grandparent_dir = runs_dir / "run_grandparent"
    run_grandparent_dir.mkdir()
    (run_grandparent_dir / "manifest.json").write_text(
        json.dumps({
            "run_id": "run_grandparent",
            "seed": 10,
            "status": "done",
            "resumed_from": None,
            "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
        }),
        encoding="utf-8",
    )

    # Run cha: seed = 20, kế thừa từ run_grandparent
    run_parent_dir = runs_dir / "run_parent"
    run_parent_dir.mkdir()
    (run_parent_dir / "manifest.json").write_text(
        json.dumps({
            "run_id": "run_parent",
            "seed": 20,
            "status": "done",
            "resumed_from": {
                "run_id": "run_grandparent",
                "checkpoint": "checkpoint_final.pt",
                "checkpoint_sha256": "0" * 64,
            },
            "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
        }),
        encoding="utf-8",
    )

    # Run hiện tại (con): seed = 30, kế thừa từ run_parent
    run_child_dir = runs_dir / "run_child"
    run_child_dir.mkdir()
    (run_child_dir / "manifest.json").write_text(
        json.dumps({
            "run_id": "run_child",
            "seed": 30,
            "status": "done",
            "resumed_from": {
                "run_id": "run_parent",
                "checkpoint": "checkpoint_mid.pt",
                "checkpoint_sha256": "0" * 64,
            },
            "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
        }),
        encoding="utf-8",
    )

    cfg = EvalConfig.load(overrides={"paths.runs_dir": "runs"})
    pair = _create_sample_target_pair()

    # Thu thập chuỗi hạt giống thành công: [30, 20, 10]
    report = check_disjoint(run_child_dir, cfg, pair)
    assert report.train_seeds == (30, 20, 10)

    # Nếu seed đánh giá trùng với hạt giống của run ông nội (10) => Bị từ chối!
    bad_cfg = EvalConfig(
        schema_version=cfg.schema_version,
        seeds=type(cfg.seeds)(episode_base=1000, random_policy=10),
        episodes=cfg.episodes,
        criterion=cfg.criterion,
        stats=cfg.stats,
        logs=cfg.logs,
        charts=cfg.charts,
        paths=cfg.paths,
    )
    with pytest.raises(LeakageError, match="trùng với seed"):
        check_disjoint(run_child_dir, bad_cfg, pair)


def test_fingerprint_mismatch_rejected() -> None:
    """FR-008, INV-001, AC-4: Từ chối khi mã băm fingerprint không khớp hồ sơ hoặc kỳ vọng."""
    cfg = EvalConfig.load()
    pair = _create_sample_target_pair()

    # Ca 1: Hồ sơ run có fingerprint khác với tập mục tiêu
    manifest_wrong_fp = {
        "run_id": "20261010T080000Z_elbow_s42",
        "status": "done",
        "seed": 42,
        "target_fingerprint_sha256": "a" * 64,
        "resumed_from": None,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
    }
    with pytest.raises(LeakageError, match="fingerprint"):
        check_disjoint(manifest_wrong_fp, cfg, pair)

    # Ca 2: Cấu hình người dùng ghim expect_fingerprint_sha256 khác với tập mục tiêu
    cfg_wrong_expected = EvalConfig(
        schema_version=cfg.schema_version,
        seeds=cfg.seeds,
        episodes=cfg.episodes,
        criterion=cfg.criterion,
        stats=cfg.stats,
        logs=cfg.logs,
        charts=cfg.charts,
        paths=type(cfg.paths)(
            runs_dir=cfg.paths.runs_dir,
            env_config_override=cfg.paths.env_config_override,
            expect_fingerprint_sha256="b" * 64,
        ),
    )
    manifest_clean = {
        "run_id": "20261010T080000Z_elbow_s42",
        "status": "done",
        "seed": 42,
        "resumed_from": None,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
    }
    with pytest.raises(LeakageError, match="fingerprint"):
        check_disjoint(manifest_clean, cfg_wrong_expected, pair)


def test_rebuild_target_pair_from_env_config() -> None:
    """FR-008, INV-001, AC-4: Tự động tái dựng TargetSetPair từ cấu hình khi không truyền pair."""
    cfg = EvalConfig.load(overrides={"seeds.episode_base": 12345, "episodes.repeats": 1})
    manifest_data = {
        "run_id": "20261010T080000Z_elbow_s42",
        "status": "done",
        "seed": 42,
        "resumed_from": None,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
        "model": {"sha256": "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f"},
    }

    report = check_disjoint(manifest_data, cfg, pair=None)
    assert report.passed is True
    assert report.train_target_provenance == "rebuilt_from_config"
    assert report.n_train_targets > 0
    assert report.n_eval_targets > 0
    assert report.min_cross_distance_m >= report.min_required_m


def test_manifest_fingerprint_provenance_matched() -> None:
    """FR-008, INV-001, AC-4: Ghi nhận provenance là manifest_fingerprint khi băm khớp."""
    cfg = EvalConfig.load()
    pair = _create_sample_target_pair()

    manifest_data = {
        "run_id": "20261010T080000Z_elbow_s42",
        "status": "done",
        "seed": 42,
        "target_fingerprint_sha256": pair.fingerprint_sha256,
        "resumed_from": None,
        "config": {"env_config": "src/mma_ai/environment/elbow_env.yaml"},
    }

    report = check_disjoint(manifest_data, cfg, pair)
    assert report.passed is True
    assert report.train_target_provenance == "manifest_fingerprint"
    assert report.provenance == "manifest_fingerprint"
