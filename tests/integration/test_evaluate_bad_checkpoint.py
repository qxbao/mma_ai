"""Kiểm thử tích hợp checkpoint lỗi qua CLI (T422).

Trace: 004 FR-015 / INV-004 / SC-005 / AC-5
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from eval_fixtures import make_run_dir, run_cli

from mma_ai.evaluation.errors import CheckpointUnusable, EvalError
from mma_ai.evaluation.runner import evaluate_checkpoint


def _assert_no_evaluation_output(run_dir: Path) -> None:
    eval_dir = run_dir / "eval"
    assert not eval_dir.exists(), f"Không được tạo thư mục kết quả sau lỗi checkpoint: {eval_dir}"
    assert not list(run_dir.rglob("episodes.csv")), (
        "Không được tạo tệp episodes.csv sau lỗi checkpoint."
    )
    assert not list(run_dir.rglob("*.png")), "Không được tạo biểu đồ sau lỗi checkpoint."
    assert not list(run_dir.rglob(".tmp-*")), "Không được để lại thư mục tạm sau lỗi checkpoint."


def _update_checkpoint_digests(run_dir: Path, checkpoint: Path) -> None:
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    for metadata in (
        run_dir / "checkpoints" / "latest.json",
        checkpoint.with_name(f"{checkpoint.stem}.meta.json"),
    ):
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        payload["sha256"] = digest
        metadata.write_text(json.dumps(payload), encoding="utf-8")


def _load_torch() -> Any:
    return pytest.importorskip("torch", reason="Cần torch để tạo checkpoint lỗi có cấu trúc.")


def test_004_ac_5_independent_checkpoint_error_contract() -> None:
    """004 AC-5, FR-015, INV-004: Hợp đồng checkpoint lỗi dùng mã thoát 4."""
    assert callable(evaluate_checkpoint)
    assert issubclass(CheckpointUnusable, EvalError)
    assert CheckpointUnusable.exit_code == 4
    assert callable(make_run_dir)
    assert callable(run_cli)


def test_004_ac_5_missing_checkpoint_exit4_no_output(tmp_path: Path) -> None:
    """004 AC-5, FR-015, INV-004: Checkpoint không tồn tại nêu đường dẫn, mã 4, không chỉ số."""
    run_dir = make_run_dir(tmp_path / "missing_checkpoint", seed=42)
    missing = run_dir / "checkpoints" / "khong-ton-tai.pt"

    result = run_cli(["--checkpoint", str(missing)])

    assert result.exit_code == 4
    assert str(missing) in result.stderr
    assert "không tồn tại" in result.stderr.lower()
    assert "KẾT QUẢ ĐÁNH GIÁ CHÍNH SÁCH" not in result.stdout
    _assert_no_evaluation_output(run_dir)


def test_004_ac_5_corrupt_checkpoint_exit4_names_cause(tmp_path: Path) -> None:
    """004 AC-5, FR-015, INV-004: Checkpoint hỏng nêu nguyên nhân và mã thoát 4."""
    run_dir = make_run_dir(tmp_path / "corrupt_checkpoint", seed=42)
    checkpoint = run_dir / "checkpoints" / "ckpt_u000001.pt"
    checkpoint.write_bytes(b"checkpoint bi hong")
    _update_checkpoint_digests(run_dir, checkpoint)

    result = run_cli(["--checkpoint", str(run_dir / "checkpoints" / "latest.json")])

    assert result.exit_code == 4
    assert "hỏng" in result.stderr.lower()
    assert str(checkpoint) in result.stderr
    assert "KẾT QUẢ ĐÁNH GIÁ CHÍNH SÁCH" not in result.stdout
    _assert_no_evaluation_output(run_dir)


def test_004_ac_5_missing_component_exit4(tmp_path: Path) -> None:
    """004 AC-5, FR-015, INV-004: Thiếu thành phần bắt buộc bị từ chối trước khi đánh giá."""
    torch = _load_torch()
    run_dir = make_run_dir(tmp_path / "missing_component", seed=42)
    checkpoint = run_dir / "checkpoints" / "ckpt_u000001.pt"
    payload = torch.load(checkpoint, weights_only=True)
    del payload["optimizer"]
    torch.save(payload, checkpoint)
    _update_checkpoint_digests(run_dir, checkpoint)

    result = run_cli(["--checkpoint", str(run_dir / "checkpoints" / "latest.json")])

    assert result.exit_code == 4
    assert "thiếu" in result.stderr.lower()
    assert "optimizer" in result.stderr
    _assert_no_evaluation_output(run_dir)


def test_004_ac_5_xml_hash_mismatch_exit4(tmp_path: Path) -> None:
    """004 AC-5, FR-015, INV-004: Lệch mã băm XML phải bị từ chối."""
    run_dir = make_run_dir(tmp_path / "xml_hash_mismatch", seed=42)
    checkpoint = run_dir / "checkpoints" / "ckpt_u000001.pt"
    torch = _load_torch()
    payload = torch.load(checkpoint, weights_only=True)
    original_hash = str(payload["model_sha256"])
    changed_hash = "f" * 64
    payload["model_sha256"] = changed_hash
    torch.save(payload, checkpoint)
    _update_checkpoint_digests(run_dir, checkpoint)

    result = run_cli(["--checkpoint", str(run_dir / "checkpoints" / "latest.json")])

    assert result.exit_code == 4
    assert "mã băm xml" in result.stderr.lower()
    assert original_hash in result.stderr
    assert changed_hash in result.stderr
    _assert_no_evaluation_output(run_dir)


def test_004_inv_004_no_eval_dir_after_checkpoint_error(tmp_path: Path) -> None:
    """004 INV-004, AC-5: Lỗi checkpoint không tạo eval, biểu đồ, tệp episode hay thư mục tạm."""
    run_dir = make_run_dir(tmp_path / "no_output_after_error", seed=42)
    checkpoint = run_dir / "checkpoints" / "ckpt_u000001.pt"
    checkpoint.write_bytes(b"du lieu checkpoint hong")
    _update_checkpoint_digests(run_dir, checkpoint)

    result = run_cli(["--checkpoint", str(run_dir / "checkpoints" / "latest.json")])

    assert result.exit_code == 4
    _assert_no_evaluation_output(run_dir)


def test_004_ac_5_errors_are_vietnamese_with_context(tmp_path: Path) -> None:
    """004 AC-5, FR-015: Lỗi hiển thị tiếng Việt và nêu ngữ cảnh đường dẫn checkpoint."""
    run_dir = make_run_dir(tmp_path / "vietnamese_error", seed=42)
    missing = run_dir / "checkpoints" / "khong-co.pt"

    result = run_cli(["--checkpoint", str(missing)])

    assert result.exit_code == 4
    assert "Lỗi đánh giá" in result.stderr
    assert str(missing) in result.stderr
    assert any(term in result.stderr.lower() for term in ("không", "tệp", "checkpoint"))
    assert "KẾT QUẢ ĐÁNH GIÁ CHÍNH SÁCH" not in result.stdout
