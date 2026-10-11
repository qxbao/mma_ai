"""Kiểm thử đơn vị cho fixture dùng chung trong kiểm thử tích hợp đánh giá (eval_fixtures.py).

Bao phủ các yêu cầu và bất biến theo hợp đồng:
- FR-020: Bộ fixture và tiện ích kiểm thử tự động (automated test suite) cho quy trình đánh giá.
- FR-013: Lưu trữ hồ sơ lượt chạy (run manifest) và điểm kiểm tra (checkpoint) phục vụ đánh giá.
- INV-001: Bảo vệ tính toàn vẹn và không giao cắt của thư mục lượt chạy.
- INV-003: Đảm bảo chính sách kịch bản (scripted policy) tuân thủ hành động trong [0, 1]^6.
- INV-004: Ngăn chặn tác động ngoài ý muốn tới các tệp gốc.
- INV-005: Đảm bảo tính bất biến (immutability) của thư mục lượt chạy qua phép băm cấu trúc cây tệp.
- NFR-HEADLESS-001: Chạy dòng lệnh ở chế độ không màn hình (headless) loại bỏ biến DISPLAY.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from eval_fixtures import (
    CliRunResult,
    hash_tree,
    make_run_dir,
    run_cli,
    scripted_policy,
)

_EXPECTED_MODEL_SHA256 = "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f"


def test_fr_020_fr_013_make_run_dir_defaults(tmp_path: Path) -> None:
    """FR-020, FR-013, INV-001: make_run_dir tạo cấu trúc thư mục run chuẩn mặc định."""
    run_dir = make_run_dir(tmp_path)
    assert run_dir.is_dir(), "Thư mục run phải tồn tại"

    # Kiểm tra manifest.json theo hợp đồng 003
    manifest_file = run_dir / "manifest.json"
    assert manifest_file.is_file(), "manifest.json phải tồn tại trong thư mục run"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    assert manifest["seed"] == 42, "Hạt giống mặc định phải là 42"
    assert manifest["status"] == "done", "Trạng thái mặc định phải là 'done'"
    assert "env_config" in manifest["config"], "Hồ sơ run phải chứa cấu hình môi trường"
    assert manifest["model"]["sha256"] == _EXPECTED_MODEL_SHA256
    assert len(manifest["model"]["muscle_names"]) == 6, "Phải có đủ danh sách 6 tên cơ"

    # Kiểm tra thư mục checkpoints và tệp con trỏ latest.json
    checkpoints_dir = run_dir / "checkpoints"
    assert checkpoints_dir.is_dir(), "Thư mục checkpoints phải tồn tại"
    latest_file = checkpoints_dir / "latest.json"
    assert latest_file.is_file(), "Tệp latest.json phải tồn tại"

    latest_data = json.loads(latest_file.read_text(encoding="utf-8"))
    assert "path" in latest_data, "latest.json phải có trường 'path'"
    resolved_pt = run_dir / latest_data["path"]
    assert resolved_pt.is_file(), "Tệp checkpoint .pt được trỏ bởi latest.json phải tồn tại"

    # Kiểm tra tệp nhật ký metrics.jsonl
    metrics_file = run_dir / "metrics.jsonl"
    assert metrics_file.is_file(), "metrics.jsonl phải tồn tại khi with_log=True"
    lines = [
        json.loads(line)
        for line in metrics_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 1, "metrics.jsonl phải có ít nhất một bản ghi"
    first_row = lines[0]

    # Kiểm tra đủ 3 nhóm loss, reward, activation
    assert any(k.startswith("loss/") for k in first_row), "Phải có thẻ tiền tố loss/"
    assert any(k.startswith("reward/") for k in first_row), "Phải có thẻ tiền tố reward/"
    for muscle in manifest["model"]["muscle_names"]:
        assert f"activation/{muscle}" in first_row, f"Phải có thẻ activation/{muscle}"


def test_fr_020_make_run_dir_drop_series(tmp_path: Path) -> None:
    """FR-020: make_run_dir cho phép loại bỏ các chuỗi dữ liệu (drop_series) trong nhật ký."""
    run_dir = make_run_dir(tmp_path, drop_series=("loss", "activation/BRA"))
    metrics_file = run_dir / "metrics.jsonl"
    assert metrics_file.is_file()

    lines = [
        json.loads(line)
        for line in metrics_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in lines:
        assert not any(
            k.startswith("loss/") for k in row
        ), "Mọi thẻ loss/ phải bị loại bỏ khi drop_series chứa 'loss'"
        assert "activation/BRA" not in row, "Thẻ activation/BRA phải bị loại bỏ"
        assert "activation/BIClong" in row, "Các thẻ activation khác vẫn phải được giữ lại"


def test_fr_020_make_run_dir_without_log(tmp_path: Path) -> None:
    """FR-020: make_run_dir không tạo tệp metrics.jsonl khi with_log=False."""
    run_dir = make_run_dir(tmp_path, with_log=False)
    assert not (run_dir / "metrics.jsonl").exists()


def test_fr_020_make_run_dir_custom_params(tmp_path: Path) -> None:
    """FR-020, FR-013, INV-001: make_run_dir áp dụng đúng hạt giống, trạng thái và resumed_from."""
    resumed = {
        "run_id": "20261010T000000Z_elbow_s10",
        "checkpoint": "checkpoints/ckpt_u000001.pt",
        "checkpoint_sha256": "0" * 64,
    }
    run_dir = make_run_dir(tmp_path, status="running", seed=999, resumed_from=resumed)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["seed"] == 999
    assert manifest["status"] == "running"
    assert manifest["resumed_from"] is not None
    assert manifest["resumed_from"]["run_id"] == "20261010T000000Z_elbow_s10"


def test_fr_020_nfr_headless_001_run_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-020, NFR-HEADLESS-001: run_cli thực thi lệnh và loại bỏ biến môi trường DISPLAY."""
    monkeypatch.setenv("DISPLAY", ":42")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-42")

    # Gọi lệnh với --help để hoàn tất nhanh mà không cần tài nguyên nặng
    result = run_cli(["--help"])
    assert isinstance(result, CliRunResult)
    assert isinstance(result, tuple)
    assert len(result) == 3
    assert result.returncode == 0
    assert result.exit_code == 0
    assert "--checkpoint" in result.stdout

    # Gọi với đối số thiếu checkpoint bắt buộc sẽ trả mã lỗi 2
    err_res = run_cli([])
    assert err_res.returncode == 2
    assert err_res.exit_code == 2


def test_fr_020_inv_005_hash_tree_immutability(tmp_path: Path) -> None:
    """FR-020, INV-005: hash_tree phát hiện mọi biến đổi cấu trúc hoặc nội dung thư mục."""
    test_dir = tmp_path / "tree_test"
    test_dir.mkdir()
    (test_dir / "a.txt").write_text("hello", encoding="utf-8")
    (test_dir / "b.json").write_text("{}", encoding="utf-8")

    h1 = hash_tree(test_dir)
    assert isinstance(h1, str)
    assert len(h1) == 64

    # Băm lại cùng thư mục không đổi phải cho cùng mã băm
    h2 = hash_tree(test_dir)
    assert h1 == h2

    # Biến đổi nội dung tệp
    (test_dir / "a.txt").write_text("hello world", encoding="utf-8")
    h3 = hash_tree(test_dir)
    assert h1 != h3

    # Thêm tệp mới
    (test_dir / "c.txt").write_text("new file", encoding="utf-8")
    h4 = hash_tree(test_dir)
    assert h3 != h4


def test_fr_020_inv_003_scripted_policy() -> None:
    """FR-020, INV-003: scripted_policy tạo chính sách với giao diện act tuân thủ [0, 1]^6."""
    p_zero = scripted_policy("zero")
    a_zero = p_zero.act()
    assert isinstance(a_zero, np.ndarray)
    assert a_zero.shape == (6,)
    assert a_zero.dtype in (np.float32, np.float64)
    assert np.all(a_zero == 0.0)
    assert np.all(a_zero >= 0.0) and np.all(a_zero <= 1.0)

    p_const = scripted_policy("constant", value=0.75)
    a_const = p_const.act()
    assert isinstance(a_const, np.ndarray)
    assert a_const.shape == (6,)
    assert np.allclose(a_const, 0.75)
    assert np.all(a_const >= 0.0) and np.all(a_const <= 1.0)

    # Loại chính sách không hợp lệ phải ném ValueError
    with pytest.raises(ValueError, match="chính sách kịch bản không hợp lệ"):
        scripted_policy("unsupported_kind")
