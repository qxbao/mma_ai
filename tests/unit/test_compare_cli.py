"""Kiểm thử đơn vị cho CLI so sánh hai lượt chạy (compare_cli.py).

Hiện thực chu trình TDD đỏ-trước (RED-first) cho task T318 (FR-014, CMD-TRN-0003, NFR-REPRO-001).
Kiểm tra các trường hợp:
1. test_exit0_within_tolerance: Hai lượt chạy trong dung sai, in tiếng Việt, mã 0.
2. test_exit1_outside: Hai lượt chạy ngoài dung sai, in tiếng Việt, mã 1.
3. test_incomparable_message: Khác loại thiết bị không thể so sánh, in tiếng Việt, mã 1.
4. test_missing_manifest_exit2: Thiếu hoặc hỏng hồ sơ run manifest, in lỗi ra stderr, mã 2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mma_ai.learning.compare_cli import main
from mma_ai.learning.manifest import build_manifest, write_manifest


def _dummy_config(tolerance: float = 1e-6) -> dict[str, Any]:
    """Tạo cấu hình giả lập (dummy config) cho kiểm thử."""
    return {
        "schema_version": "1.0.0",
        "stage": "elbow",
        "seed": 42,
        "reproducibility": {
            "rel_tolerance": tolerance,
            "head_updates": 10,
            "torch_threads": 1,
            "deterministic_algorithms": True,
        },
        "ui": {
            "mode": "none",
            "url": None,
            "view3d": False,
        },
    }


def _dummy_model() -> dict[str, Any]:
    """Tạo thông tin mô hình giả lập (dummy model) cho kiểm thử."""
    return {
        "sha256": "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
        "source": "myo_sim/models/legacy/elbow/myoelbow_1dof6muscles.xml",
        "muscle_names": ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"],
    }


def _create_run_dir(
    base_dir: Path,
    name: str,
    *,
    returns: list[float],
    tolerance: float = 1e-6,
    device_kind: str = "cpu",
    versions: dict[str, str] | None = None,
    threads: int = 1,
) -> Path:
    """Dựng thư mục run với hồ sơ manifest hợp lệ bằng build_manifest và write_manifest."""
    run_dir = base_dir / name
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        run_id=f"20261010T080000Z_elbow_s42_{name}",
        config=_dummy_config(tolerance=tolerance),
        seed=42,
        model=_dummy_model(),
        device={"kind": device_kind, "name": "CPU Test", "cuda_available": False},
        library_versions=versions,
    )
    # Cập nhật số liệu và bất biến tái lập vào manifest
    manifest["reward_metrics"]["head_mean_return"] = returns
    manifest["reproducibility"]["rel_tolerance"] = tolerance
    manifest["reproducibility"]["device_kind"] = device_kind
    manifest["reproducibility"]["torch_threads"] = threads

    write_manifest(run_dir, manifest)
    return run_dir


def test_exit0_within_tolerance(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """FR-014, CMD-TRN-0003: Hai run trong dung sai tái lập thoát mã 0 và in tiếng Việt."""
    run_a = _create_run_dir(
        tmp_path,
        "run_a",
        returns=[100.0, -10.0, 50.0],
        tolerance=1e-5,
    )
    run_b = _create_run_dir(
        tmp_path,
        "run_b",
        returns=[100.0001, -10.00001, 50.00005],
        tolerance=1e-5,
    )

    exit_code = main([str(run_a), str(run_b)])
    assert exit_code == 0

    captured = capsys.readouterr()
    stdout = captured.out
    # Kiểm tra thông tin tiếng Việt (song ngữ nếu áp dụng)
    assert "Số điểm đầu (K): 3" in stdout or "3" in stdout
    assert "Dung sai tương đối (relative tolerance)" in stdout or "dung sai" in stdout.lower()
    assert "cpu" in stdout.lower()
    assert "trong dung sai" in stdout.lower() or "tái lập thành công" in stdout.lower()


def test_exit1_outside(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """FR-014, CMD-TRN-0003: Hai run lệch vượt dung sai trả về mã thoát 1 và in độ lệch lớn nhất."""
    run_a = _create_run_dir(
        tmp_path,
        "run_a",
        returns=[100.0, -10.0],
        tolerance=1e-6,
    )
    run_b = _create_run_dir(
        tmp_path,
        "run_b",
        returns=[100.05, -10.0],
        tolerance=1e-6,
    )

    exit_code = main([str(run_a), str(run_b)])
    assert exit_code == 1

    captured = capsys.readouterr()
    stdout = captured.out
    assert "ngoài dung sai" in stdout.lower() or "vượt dung sai" in stdout.lower()
    assert "lệch tương đối lớn nhất" in stdout.lower() or "độ lệch" in stdout.lower()


def test_incomparable_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """FR-014, CMD-TRN-0003: Khác thiết bị trả về mã 1 và in lý do tiếng Việt rõ ràng."""
    run_a = _create_run_dir(
        tmp_path,
        "run_a",
        returns=[100.0],
        device_kind="cpu",
    )
    run_b = _create_run_dir(
        tmp_path,
        "run_b",
        returns=[100.0],
        device_kind="cuda",
    )

    exit_code = main([str(run_a), str(run_b)])
    assert exit_code == 1

    captured = capsys.readouterr()
    stdout = captured.out
    assert "không thể so sánh" in stdout.lower() or "không so sánh được" in stdout.lower()
    assert "thiết bị" in stdout.lower()


def test_missing_manifest_exit2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CMD-TRN-0003: Thiếu hoặc hỏng hồ sơ run manifest trả về mã thoát 2 và in lỗi ra stderr."""
    empty_dir = tmp_path / "empty_run"
    empty_dir.mkdir()

    valid_run = _create_run_dir(tmp_path, "valid_run", returns=[1.0])

    # 1. Thư mục không có manifest.json
    exit_code_missing = main([str(empty_dir), str(valid_run)])
    assert exit_code_missing == 2
    captured_missing = capsys.readouterr()
    assert "lỗi" in captured_missing.err.lower() or "không tìm thấy" in captured_missing.err.lower()

    # 2. Thư mục có manifest.json bị hỏng (corrupted JSON)
    corrupt_dir = tmp_path / "corrupt_run"
    corrupt_dir.mkdir()
    (corrupt_dir / "manifest.json").write_text("{invalid json", encoding="utf-8")

    exit_code_corrupt = main([str(corrupt_dir), str(valid_run)])
    assert exit_code_corrupt == 2
    captured_corrupt = capsys.readouterr()
    assert "lỗi" in captured_corrupt.err.lower() or "hỏng" in captured_corrupt.err.lower()

    # 3. Thiếu tham số dòng lệnh
    exit_code_no_args = main([])
    assert exit_code_no_args == 2
