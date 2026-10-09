"""Kiểm thử đơn vị cho tính tái lập (reproducibility) của các lượt chạy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest


def _write_manifest(
    run_dir: Path,
    *,
    returns: list[float],
    device_kind: str = "cpu",
    versions: dict[str, str] | None = None,
    threads: int = 1,
    tolerance: float = 1e-6,
) -> Path:
    run_dir.mkdir()
    manifest = {
        "reward_metrics": {"head_mean_return": returns},
        "reproducibility": {
            "rel_tolerance": tolerance,
            "device_kind": device_kind,
            "torch_threads": threads,
        },
        "device": {"kind": device_kind},
        "library_versions": versions or {"torch": "2.0", "numpy": "1.0"},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run_dir


def test_fr_014_compare_within_tolerance(tmp_path: Path) -> None:
    """FR-014: Hai chuỗi sai khác trong dung sai được báo tương đương."""
    from mma_ai.learning.repro import compare_runs

    first = _write_manifest(tmp_path / "first", returns=[100.0, -10.0])
    second = _write_manifest(tmp_path / "second", returns=[100.00005, -10.000005])
    report = compare_runs(first, second)
    assert report.comparable is True
    assert report.matches is True
    assert report.reason is None


def test_fr_014_compare_outside_tolerance(tmp_path: Path) -> None:
    """FR-014: Một điểm vượt dung sai phải làm hai lượt chạy khác nhau."""
    from mma_ai.learning.repro import compare_runs

    first = _write_manifest(tmp_path / "first", returns=[100.0])
    second = _write_manifest(tmp_path / "second", returns=[100.001])
    report = compare_runs(first, second)
    assert report.comparable is True
    assert report.matches is False
    assert report.reason is not None


def test_fr_014_not_comparable_different_device(tmp_path: Path) -> None:
    """FR-014: Khác loại thiết bị không được kết luận bằng hoặc khác."""
    from mma_ai.learning.repro import compare_runs

    first = _write_manifest(tmp_path / "first", returns=[1.0], device_kind="cpu")
    second = _write_manifest(tmp_path / "second", returns=[1.0], device_kind="cuda")
    report = compare_runs(first, second)
    assert report.comparable is False
    assert report.matches is None
    assert report.reason is not None
    assert "thiết bị" in report.reason.lower()


@dataclass(frozen=True)
class _ReproducibilityConfig:
    torch_threads: int = 1
    deterministic_algorithms: bool = True


def test_fr_001_seed_everything_same_draws() -> None:
    """FR-001: Cùng seed gốc tái tạo được luồng NumPy và Torch."""
    torch = pytest.importorskip("torch")
    from mma_ai.learning.repro import seed_everything

    first_rng = seed_everything(42, _ReproducibilityConfig())
    first = (first_rng.random(4), torch.rand(4).tolist())
    second_rng = seed_everything(42, _ReproducibilityConfig())
    second = (second_rng.random(4), torch.rand(4).tolist())
    assert np.array_equal(first[0], second[0])
    assert first[1] == second[1]


def teardown_module() -> None:
    """Dọn dẹp các mô-đun trì hoãn để bảo vệ ranh giới kiểm thử."""
    import sys

    sys.modules.pop("mma_ai.learning.repro", None)
    sys.modules.pop("mma_ai.learning", None)

