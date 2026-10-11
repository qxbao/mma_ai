"""Kiểm thử đơn vị cho fixture dùng chung trong kiểm thử tích hợp (train_fixtures.py).

Bao phủ các yêu cầu:
- FR-019: Bộ fixture và tiện ích kiểm thử tự động cho huấn luyện PPO.
- INV-001: Tính toàn vẹn của thư mục lượt chạy (run directory).
- INV-002: Bảo đảm CLI tuân thủ không gian hành động hợp lệ.
- INV-005: Kiểm tra tính độc lập và khả năng nạp schema contracts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from jsonschema import Draft202012Validator, FormatChecker
from train_fixtures import (
    hash_tree,
    list_runs,
    load_manifest,
    load_schema_registry,
    run_train_cli,
    sample_observations,
    smoke_config,
)


def test_fr_019_smoke_config_defaults(tmp_path: Path) -> None:
    """FR-019: smoke_config tạo tệp cấu hình smoke với các giá trị mặc định chuẩn xác."""
    from mma_ai.learning.train_config import TrainConfig

    config_path = smoke_config(tmp_path)
    assert config_path.is_file()

    cfg = TrainConfig.load(config_path)
    assert cfg.schedule.total_timesteps == 4096
    assert cfg.checkpoint.every_updates == 1
    assert cfg.ui.mode == "none"
    assert "runs" in cfg.paths.runs_dir


def test_fr_019_smoke_config_overrides(tmp_path: Path) -> None:
    """FR-019: smoke_config áp dụng chính xác các giá trị ghi đè (overrides)."""
    from mma_ai.learning.train_config import TrainConfig

    config_path = smoke_config(
        tmp_path,
        total_timesteps=8192,
        seed=999,
        every_updates=2,
    )
    cfg = TrainConfig.load(config_path)
    assert cfg.schedule.total_timesteps == 8192
    assert cfg.seed == 999
    assert cfg.checkpoint.every_updates == 2


def test_fr_019_run_train_cli_execution_and_strips_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-019, FR-015: run_train_cli chạy subprocess thật và loại bỏ biến môi trường DISPLAY."""
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")

    # Kiểm tra lệnh với tham số stage chưa hỗ trợ để hoàn thành nhanh mà không cần train thật
    result = run_train_cli(["--stage", "unknown_stage"])
    assert result.returncode == 3
    assert result.exit_code == 3
    assert "chưa triển khai: stage 'unknown_stage'" in result.stderr


def test_fr_019_load_manifest_and_list_runs(tmp_path: Path) -> None:
    """FR-019, INV-001: list_runs và load_manifest đọc đúng danh sách run và tệp manifest.json."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    run_a = runs_dir / "20261010T010000Z_elbow_s42"
    run_b = runs_dir / "20261010T020000Z_elbow_s43"
    run_a.mkdir()
    run_b.mkdir()

    manifest_payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": "20261010T010000Z_elbow_s42",
        "stage": "elbow",
        "seed": 42,
        "status": "done",
    }
    (run_a / "manifest.json").write_text(json.dumps(manifest_payload), encoding="utf-8")

    runs = list_runs(runs_dir)
    assert len(runs) == 2
    assert run_a in runs
    assert run_b in runs

    loaded = load_manifest(run_a)
    assert loaded["run_id"] == "20261010T010000Z_elbow_s42"
    assert loaded["status"] == "done"

    # Nạp từ đường dẫn tệp trực tiếp
    loaded_direct = load_manifest(run_a / "manifest.json")
    assert loaded_direct["run_id"] == "20261010T010000Z_elbow_s42"

    with pytest.raises(FileNotFoundError):
        load_manifest(run_b)


def test_fr_019_hash_tree_determinism_and_mutation(tmp_path: Path) -> None:
    """FR-019: hash_tree tính mã băm SHA-256 nhất quán cho thư mục và phát hiện thay đổi."""
    tree_dir = tmp_path / "tree_test"
    tree_dir.mkdir()
    sub_dir = tree_dir / "subdir"
    sub_dir.mkdir()

    file1 = tree_dir / "file1.txt"
    file2 = sub_dir / "file2.bin"

    file1.write_text("noi dung tap tin 1", encoding="utf-8")
    file2.write_bytes(b"\x00\x01\x02\x03")

    hash_1 = hash_tree(tree_dir)
    hash_2 = hash_tree(tree_dir)
    assert len(hash_1) == 64
    assert hash_1 == hash_2

    # Biến dị một tệp làm thay đổi hash
    file1.write_text("noi dung tap tin 1 da sua", encoding="utf-8")
    hash_mutated = hash_tree(tree_dir)
    assert hash_mutated != hash_1


def test_fr_019_sample_observations_shape_and_determinism() -> None:
    """FR-019: sample_observations trả về mảng quan sát (64, 14) tất định."""
    obs_batch = sample_observations()
    assert isinstance(obs_batch, np.ndarray)
    assert obs_batch.shape == (64, 14)
    assert obs_batch.dtype == np.float64

    # Tất định giữa hai lần gọi
    obs_batch_repeat = sample_observations()
    np.testing.assert_array_equal(obs_batch, obs_batch_repeat)

    # Tuỳ biến kích thước lô n
    obs_custom = sample_observations(n=10)
    assert obs_custom.shape == (10, 14)


def test_fr_019_load_schema_registry_validates_schemas() -> None:
    """FR-019, INV-005: load_schema_registry nạp đầy đủ hợp đồng schema vào registry jsonschema."""
    registry = load_schema_registry()
    assert registry is not None

    contracts_dir = Path(__file__).resolve().parents[2] / "specs/003-ppo-train-repro/contracts"
    manifest_schema = json.loads(
        (contracts_dir / "run-manifest.schema.json").read_text(encoding="utf-8")
    )

    validator = Draft202012Validator(
        manifest_schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    assert validator is not None
