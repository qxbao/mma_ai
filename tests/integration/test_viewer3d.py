"""Kiểm thử tích hợp cho thành phần hiển thị 3D tuỳ chọn View3D (viewer3d.py).

Hiện thực và kiểm chứng các yêu cầu:
- FR-022: Hiển thị 3D khuỷu tay chạy ở tiến trình riêng, bật/tắt được và mặc định tắt;
  huấn luyện mặc định không giao diện (headless); nạp chính sách (policy) mới nhất
  từ checkpoints/latest.json.
- INV-005: Giao diện chỉ-đọc (read-only); không được sửa hay ghi vào thư mục run, checkpoint
  hay tiến trình huấn luyện; không import learning.trainer hoặc learning.ppo.
- NFR-HEADLESS-001: Khi thiếu biến môi trường DISPLAY hoặc WAYLAND_DISPLAY, in "3D không khả dụng"
  ra stderr và thoát với mã 0 (exit 0), không ném lỗi làm gián đoạn chương trình.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _get_view3d_class() -> type[Any]:
    from mma_ai.monitoring.viewer3d import View3D

    return View3D


def _compute_directory_hashes(directory: Path) -> dict[str, str]:
    """Tính toán bảng băm (hash table) SHA-256 cho toàn bộ các tệp trong thư mục."""
    hashes: dict[str, str] = {}
    for item in sorted(directory.rglob("*")):
        if item.is_file():
            content = item.read_bytes()
            rel_name = str(item.relative_to(directory))
            hashes[rel_name] = hashlib.sha256(content).hexdigest()
    return hashes


def test_regress_tdd_red_viewer3d_module_is_present() -> None:
    """FR-022: Mô-đun viewer3d phải được đóng gói trong mma_ai.monitoring."""
    assert importlib.util.find_spec("mma_ai.monitoring.viewer3d") is not None


def test_view3d_off_by_default(tmp_path: Path) -> None:
    """FR-022: Cấu hình hiển thị 3D mặc định tắt và View3D không tự chạy nền khi khởi tạo."""
    # 1. Kiểm tra cấu hình huấn luyện mặc định có view3d tắt
    from mma_ai.learning.train_config import TrainConfig

    cfg = TrainConfig.load()
    assert cfg.ui.view3d is False, "Cấu hình ui.view3d phải mặc định là false"

    # 2. Khởi tạo đối tượng View3D, đảm bảo trạng thái ban đầu không hoạt động
    View3D = _get_view3d_class()
    viewer = View3D(tmp_path)
    assert viewer.is_running is False, "Đối tượng View3D không được tự chạy khi khởi tạo"


def test_view3d_unavailable_without_display_exit0(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """NFR-HEADLESS-001, FR-022: Thiếu màn hình thì in '3D không khả dụng' và thoát mã 0."""
    # Xoá biến môi trường màn hình hiển thị
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    View3D = _get_view3d_class()
    viewer = View3D(tmp_path)
    exit_code = viewer.run()

    # Kiểm tra mã thoát 0 không ném ngoại lệ
    assert exit_code == 0, "Khi thiếu màn hình, run() phải thoát với mã 0"

    # Kiểm tra đầu ra lỗi chuẩn (stderr) in đúng thông điệp quy định
    captured = capsys.readouterr()
    assert "3D không khả dụng" in captured.err, (
        f"Kỳ vọng '3D không khả dụng' trong stderr, thực tế nhận: {captured.err!r}"
    )


def test_viewer_reads_only_latest_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-005: View3D chỉ đọc latest.json và checkpoint, tuyệt đối không sửa thư mục run."""
    run_dir = tmp_path / "test_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir = run_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    # Tạo tệp latest.json và một tệp checkpoint giả lập
    fake_ckpt = checkpoints_dir / "ckpt_u000001.pt"
    fake_ckpt.write_bytes(b"dummy_pt_content")

    latest_meta = {
        "schema_version": "1.0.0",
        "path": "checkpoints/ckpt_u000001.pt",
        "kind": "periodic",
        "update_idx": 1,
        "env_steps": 2048,
        "sha256": hashlib.sha256(b"dummy_pt_content").hexdigest(),
        "created_utc": "2026-10-10T00:00:00Z",
        "model_sha256": "dummy_model",
        "components": ["actor", "critic"],
        "library_versions": {},
        "finite": True,
    }
    latest_file = checkpoints_dir / "latest.json"
    latest_file.write_text(json.dumps(latest_meta, ensure_ascii=False), encoding="utf-8")

    progress_file = run_dir / "progress.json"
    progress_file.write_text(json.dumps({"status": "running", "update_idx": 1}), encoding="utf-8")

    # Tính bảng băm trạng thái trước khi khởi chạy
    hashes_before = _compute_directory_hashes(run_dir)
    assert len(hashes_before) > 0, "Thư mục run phải có tệp trước kiểm thử"

    # Tạo đối tượng View3D và chạy mô phỏng 1 chu kỳ kiểm tra
    View3D = _get_view3d_class()
    viewer = View3D(run_dir, poll_interval_s=0.01)

    # Giả lập môi trường có màn hình và mock mujoco.viewer
    monkeypatch.setenv("DISPLAY", ":0")

    mock_passive_viewer = MagicMock()
    # Cho vòng lặp chạy đúng 1 lần rồi dừng
    mock_passive_viewer.is_running.side_effect = [True, False]

    # Mock môi trường để kiểm tra luồng đọc dữ liệu mà không cần tải mô hình vật lý nặng
    mock_env = MagicMock()
    mock_env.reset.return_value = ([0.0] * 14, {})
    mock_env.step.return_value = ([0.0] * 14, 1.0, True, False, {})
    mock_env.action_space.shape = (6,)
    mock_env.model = MagicMock()
    mock_env.data = MagicMock()

    # Mock policy loader để không phụ thuộc torch nặng
    mock_policy = MagicMock()
    mock_policy.act_deterministic.return_value = [0.1] * 6
    viewer._try_load_latest_policy = MagicMock(return_value=mock_policy)

    try:
        with patch("mujoco.viewer.launch_passive", return_value=mock_passive_viewer):
            exit_code = viewer.run(env=mock_env, max_episodes=1)
            assert exit_code == 0
    finally:
        sys.modules.pop("mujoco.viewer", None)

    # Tính bảng băm trạng thái sau khi View3D chạy
    hashes_after = _compute_directory_hashes(run_dir)

    # Khẳng định bất biến INV-005: Toàn bộ thư mục run không bị biến đổi
    assert hashes_before == hashes_after, (
        "Thư mục run đã bị thay đổi sau khi View3D chạy; vi phạm bất biến chỉ-đọc INV-005!"
    )


def test_import_does_not_require_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """NFR-HEADLESS-001: Nhập mô-đun viewer3d không yêu cầu màn hình và không nạp viewer."""
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    # Cô lập hiệu ứng thu thập và dọn module sau/trước kiểm thử
    sys.modules.pop("mujoco.viewer", None)
    sys.modules.pop("mma_ai.monitoring.viewer3d", None)

    import mma_ai.monitoring.viewer3d as v3d

    assert hasattr(v3d, "View3D"), "Mô-đun viewer3d phải định nghĩa lớp View3D"

    # Kiểm tra rằng mujoco.viewer không được tự động nhập ở cấp độ mô-đun
    assert "mujoco.viewer" not in sys.modules, (
        "mujoco.viewer không được nạp ở module level khi import viewer3d"
    )


def test_no_training_imports() -> None:
    """INV-005: viewer3d không được nhập (import) learning.trainer hoặc learning.ppo."""
    viewer3d_path = Path(__file__).parents[2] / "src/mma_ai/monitoring/viewer3d.py"
    assert viewer3d_path.is_file(), f"Tệp {viewer3d_path} phải tồn tại"

    content = viewer3d_path.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(viewer3d_path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "learning.trainer" not in alias.name, (
                    f"Cấm import '{alias.name}' theo bất biến INV-005"
                )
                assert "learning.ppo" not in alias.name, (
                    f"Cấm import '{alias.name}' theo bất biến INV-005"
                )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert "learning.trainer" not in mod, (
                f"Cấm import from '{mod}' theo bất biến INV-005"
            )
            assert "learning.ppo" not in mod, (
                f"Cấm import from '{mod}' theo bất biến INV-005"
            )


def test_real_window_requires_display(tmp_path: Path) -> None:
    """FR-022: Ca cửa sổ thật; khi không có màn hình thì khẳng định trạng thái không khả dụng."""
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    View3D = _get_view3d_class()
    viewer = View3D(tmp_path)

    if not has_display:
        # Môi trường CI hoặc không có màn hình: kiểm tra rõ ràng trạng thái headless
        assert viewer.has_display() is False, (
            "Hệ thống phải xác định chính xác trạng thái không có màn hình hiển thị"
        )
        exit_code = viewer.run()
        assert exit_code == 0
    else:
        # Nếu có màn hình thật, có thể chạy kiểm tra trạng thái khởi tạo
        assert viewer.has_display() is True
