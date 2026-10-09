"""Kiểm thử tích hợp bảo vệ lỗi qua giao diện dòng lệnh huấn luyện (T325).

Xác minh và đảm bảo các cơ chế bảo vệ lỗi số học và tính ổn định hệ thống:
- FR-007, INV-004: Quét tính hữu hạn (finite scanning), phát hiện NaN/Inf trong tổn thất (loss)
  hoặc tham số mô hình sẽ dừng ngay tiến trình huấn luyện, tuyệt đối không lưu điểm kiểm tra
  (checkpoint) chứa NaN, giữ nguyên điểm kiểm tra hợp lệ gần nhất và đánh dấu hồ sơ thí nghiệm
  (experiment manifest) ở trạng thái 'error'.
- FR-017, NFR-REL-001: Ngoại lệ mất ổn định vật lý (PhysicsInstabilityError) từ môi trường
  mô phỏng được truyền nguyên văn lên tầng giao diện dòng lệnh (CLI), thoát mã 1 và hồ sơ 'error'.
- FR-015, INV-004: Lỗi ghi đĩa điểm kiểm tra (CheckpointIOError) dừng tiến trình ngay lập tức
  với mã 1, nêu rõ nguyên nhân lỗi nhập xuất (I/O error), không tiếp tục khi thiếu checkpoint.
- FR-015, AC-1: Tín hiệu ngắt từ người dùng (SIGINT / KeyboardInterrupt) kết thúc với mã thoát 130,
  đồng thời cập nhật trạng thái hồ sơ thí nghiệm thành 'interrupted'.
- AC-1: Tiêu chí nghiệm thu kiểm thử bảo vệ lỗi qua giao diện dòng lệnh (CLI).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from train_fixtures import list_runs, load_manifest, smoke_config

from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.learning.cli import _build_parser, main
from mma_ai.learning.errors import (
    CheckpointIOError,
    NonFiniteError,
    TrainError,
)


def test_nan_guard_contract_independent_assertion() -> None:
    """FR-007, FR-015, FR-017, INV-004, NFR-REL-001: Khẳng định độc lập trên base về bảo vệ lỗi.

    Bảo đảm kiểm thử độc lập không bị bỏ qua khi thiếu phụ thuộc tuỳ chọn (optional dependency).
    Xác minh các lớp ngoại lệ bảo vệ lỗi tuân thủ đúng hợp đồng mã thoát (exit codes) và kế thừa.
    """
    # 1. Khẳng định mã thoát của các lỗi số học và nhập xuất theo hợp đồng cli.md
    assert NonFiniteError.exit_code == 1, "NonFiniteError phải có exit_code = 1"
    assert CheckpointIOError.exit_code == 1, "CheckpointIOError phải có exit_code = 1"
    assert issubclass(NonFiniteError, TrainError), "NonFiniteError phải kế thừa TrainError"
    assert issubclass(CheckpointIOError, TrainError), "CheckpointIOError phải kế thừa TrainError"
    assert issubclass(PhysicsInstabilityError, Exception), (
        "PhysicsInstabilityError phải kế thừa Exception"
    )

    # 2. Khẳng định thông điệp tiếng Việt mang đủ ngữ cảnh
    err = NonFiniteError("Phát hiện giá trị NaN tại lượt 2 trong policy_loss")
    assert "NaN" in str(err)
    assert err.exit_code == 1

    # 3. Khẳng định parser CLI hỗ trợ đầy đủ cờ hợp đồng
    parser = _build_parser()
    actions = {a.dest for a in parser._actions}
    assert {"stage", "seed", "config", "total_steps"}.issubset(actions)


def test_nan_loss_stops_without_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-007, INV-004, NFR-REL-001, AC-1: Tổn thất NaN dừng huấn luyện, không lưu checkpoint NaN.

    Tiêm giá trị không hữu hạn (NaN) vào tổn thất chính sách (policy loss) ở lượt cập nhật 2:
    - Mã thoát (exit code) phải là 1.
    - Thông báo lỗi stderr phải nêu rõ chỉ số lượt và đại lượng bị lỗi (lượt 2, policy_loss).
    - Thư mục checkpoints tuyệt đối không chứa checkpoint của lượt 2 hoặc checkpoint chứa NaN.
    - Checkpoint hợp lệ gần nhất (lượt 1) vẫn còn nguyên vẹn trên đĩa và mọi tensor đều hữu hạn.
    - Hồ sơ thí nghiệm (manifest.json) chuyển sang trạng thái 'error'.
    """
    pytest.importorskip("torch", reason="Cần PyTorch để thực thi huấn luyện")
    import torch

    from mma_ai.learning.ppo import PPOAgent

    # Thiết lập cấu hình chạy 2 lượt cập nhật (total 4096 bước, mỗi lượt 2048 bước, lưu mỗi lượt)
    config_file = smoke_config(
        tmp_path,
        total_timesteps=4096,
        n_steps=2048,
        every_updates=1,
    )
    runs_dir = tmp_path / "runs"

    original_update = PPOAgent.update
    update_count = 0

    def mock_update(agent_self: Any, buffer: Any) -> Any:
        nonlocal update_count
        update_count += 1
        if update_count >= 2:
            raise NonFiniteError(
                f"Giá trị policy_loss không hữu hạn (NaN) tại lượt cập nhật {update_count}"
            )
        return original_update(agent_self, buffer)

    monkeypatch.setattr(PPOAgent, "update", mock_update)

    exit_code = main(["--stage", "elbow", "--config", str(config_file)])
    captured = capsys.readouterr()

    # 1. Khẳng định mã thoát dòng lệnh là 1
    assert exit_code == 1, (
        f"Kỳ vọng mã thoát 1 khi gặp NaN nhưng nhận {exit_code}.\nStderr: {captured.err}"
    )

    # 2. Khẳng định thông báo stderr nêu rõ lượt cập nhật và đại lượng lỗi
    assert "lượt cập nhật 2" in captured.err, (
        f"Thông báo lỗi phải nêu rõ lượt cập nhật 2: {captured.err}"
    )
    assert "policy_loss" in captured.err, (
        f"Thông báo lỗi phải nêu rõ đại lượng policy_loss: {captured.err}"
    )

    # 3. Kiểm tra hồ sơ manifest.json ghi nhận trạng thái 'error'
    created_runs = list_runs(runs_dir)
    assert len(created_runs) == 1, "Phải tạo duy nhất một thư mục lượt chạy"
    run_dir = created_runs[0]

    manifest = load_manifest(run_dir)
    assert manifest["status"] == "error", f"Trạng thái hồ sơ phải là 'error': {manifest['status']}"
    assert manifest["error"] is not None, "Hồ sơ lỗi phải chứa thông tin chi tiết lỗi"
    assert manifest["error"]["kind"] == "non_finite", (
        f"Loại lỗi trong hồ sơ phải là 'non_finite': {manifest['error']['kind']}"
    )

    # 4. Kiểm tra điểm kiểm tra (checkpoint): lượt 1 còn nguyên, lượt 2 không tồn tại
    checkpoints_dir = run_dir / "checkpoints"
    ckpt_u1 = checkpoints_dir / "ckpt_u000001.pt"
    assert ckpt_u1.is_file(), "Điểm kiểm tra hợp lệ gần nhất (lượt 1) phải còn nguyên vẹn trên đĩa"

    ckpt_u2 = checkpoints_dir / "ckpt_u000002.pt"
    assert not ckpt_u2.exists(), "Tuyệt đối không lưu điểm kiểm tra tại lượt 2 phát sinh NaN"
    ckpt_u2_final = checkpoints_dir / "ckpt_u000002_final.pt"
    assert not ckpt_u2_final.exists(), "Không được lưu điểm kiểm tra final khi dừng do lỗi NaN"

    # Danh sách checkpoint trong manifest chỉ chứa lượt 1
    assert len(manifest["checkpoints"]) == 1, "Hồ sơ manifest chỉ được ghi nhận checkpoint hợp lệ"
    assert manifest["checkpoints"][0]["update_idx"] == 1

    # 5. Xác minh toàn bộ tensor trong checkpoint hợp lệ gần nhất đều hữu hạn (finite)
    loaded_data = torch.load(ckpt_u1, weights_only=True)
    assert isinstance(loaded_data, dict), "Dữ liệu checkpoint nạp phải là từ điển"
    for comp_key in ("actor", "critic"):
        comp_sd = loaded_data.get(comp_key, {})
        for param_name, tensor_val in comp_sd.items():
            if isinstance(tensor_val, torch.Tensor):
                assert torch.isfinite(tensor_val).all(), (
                    f"Phát hiện giá trị không hữu hạn trong tham số '{param_name}' của {comp_key}"
                )


def test_env_instability_reported_status_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-017, NFR-REL-001, AC-1: Ngoại lệ mất ổn định vật lý truyền nguyên văn, hồ sơ 'error'.

    Tiêm ngoại lệ PhysicsInstabilityError vào bước mô phỏng môi trường (env.step):
    - CLI truyền nguyên văn thông điệp lỗi và thoát với mã 1.
    - Hồ sơ thí nghiệm ghi nhận status 'error' với error.kind là 'env_instability'.
    """
    pytest.importorskip("torch", reason="Cần PyTorch để thực thi huấn luyện")
    from mma_ai.environment.single_agent import ElbowReachEnv

    config_file = smoke_config(
        tmp_path,
        total_timesteps=4096,
        n_steps=2048,
        every_updates=1,
    )
    runs_dir = tmp_path / "runs"

    original_step = ElbowReachEnv.step
    step_count = 0
    injected_message = "Mô phỏng mất ổn định động học trong MuJoCo tại bước 3."

    def mock_step(env_self: Any, action: Any) -> Any:
        nonlocal step_count
        step_count += 1
        if step_count >= 3:
            raise PhysicsInstabilityError(injected_message)
        return original_step(env_self, action)

    monkeypatch.setattr(ElbowReachEnv, "step", mock_step)

    exit_code = main(["--stage", "elbow", "--config", str(config_file)])
    captured = capsys.readouterr()

    # 1. Khẳng định mã thoát là 1 và thông điệp lỗi nguyên văn xuất hiện ở stderr
    assert exit_code == 1, (
        f"Kỳ vọng mã thoát 1 khi mất ổn định vật lý nhưng nhận {exit_code}.\nStderr: {captured.err}"
    )
    assert injected_message in captured.err, (
        f"Thông điệp ngoại lệ gốc phải xuất hiện nguyên văn ở stderr: {captured.err}"
    )

    # 2. Khẳng định hồ sơ manifest.json ghi nhận status 'error'
    run_dir = list_runs(runs_dir)[0]
    manifest = load_manifest(run_dir)
    assert manifest["status"] == "error", f"Trạng thái hồ sơ phải là 'error': {manifest['status']}"
    assert manifest["error"] is not None, "Hồ sơ phải có thông tin lỗi"
    assert manifest["error"]["kind"] == "env_instability", (
        f"Loại lỗi trong hồ sơ phải là 'env_instability': {manifest['error']['kind']}"
    )
    assert injected_message in str(manifest["error"]["message"]), (
        "Thông điệp lỗi trong manifest phải chứa nội dung ngoại lệ gốc"
    )


def test_checkpoint_write_failure_stops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-015, INV-004, AC-1: Lỗi ghi đĩa điểm kiểm tra (CheckpointIOError) dừng chạy ngay lập tức.

    Tiêm lỗi nhập xuất đĩa (I/O error) khi thực hiện lưu checkpoint:
    - CLI bắt CheckpointIOError, in thông điệp nêu rõ lý do và thoát với mã 1.
    - Tiến trình huấn luyện dừng ngay lập tức, không tiếp tục các lượt cập nhật sau.
    - Hồ sơ thí nghiệm manifest.json ghi nhận trạng thái 'error'.
    """
    pytest.importorskip("torch", reason="Cần PyTorch để thực thi huấn luyện")
    import mma_ai.learning.checkpoint as checkpoint_mod
    import mma_ai.learning.trainer as trainer_mod

    config_file = smoke_config(
        tmp_path,
        total_timesteps=4096,
        n_steps=2048,
        every_updates=1,
    )
    runs_dir = tmp_path / "runs"

    io_error_reason = "Thiết bị lưu trữ hết dung lượng (ENOSPC: No space left on device)"

    def mock_save_checkpoint(*args: Any, **kwargs: Any) -> Any:
        raise CheckpointIOError(f"Lỗi ghi đĩa khi lưu tệp checkpoint: {io_error_reason}")

    monkeypatch.setattr(checkpoint_mod, "save_checkpoint", mock_save_checkpoint)
    monkeypatch.setattr(trainer_mod, "save_checkpoint", mock_save_checkpoint)

    exit_code = main(["--stage", "elbow", "--config", str(config_file)])
    captured = capsys.readouterr()

    # 1. Khẳng định mã thoát là 1 và nêu rõ lý do lỗi nhập xuất
    assert exit_code == 1, (
        f"Kỳ vọng mã thoát 1 khi lỗi ghi checkpoint nhưng nhận {exit_code}.\nStderr: {captured.err}"
    )
    assert "checkpoint I/O error" in captured.err.lower() or "nhập xuất" in captured.err, (
        f"Thông báo lỗi phải nêu rõ lỗi nhập xuất checkpoint: {captured.err}"
    )
    assert io_error_reason in captured.err, (
        f"Thông báo lỗi phải nêu rõ nguyên nhân ENOSPC: {captured.err}"
    )

    # 2. Khẳng định hồ sơ manifest.json ghi nhận trạng thái 'error'
    run_dir = list_runs(runs_dir)[0]
    manifest = load_manifest(run_dir)
    assert manifest["status"] == "error", f"Trạng thái hồ sơ phải là 'error': {manifest['status']}"
    assert manifest["error"] is not None, "Hồ sơ phải có thông tin lỗi"
    assert manifest["error"]["kind"] == "checkpoint_io", (
        f"Loại lỗi trong hồ sơ phải là 'checkpoint_io': {manifest['error']['kind']}"
    )

    # 3. Không tiếp tục huấn luyện mà không có checkpoint
    assert len(manifest["checkpoints"]) == 0, "Không được ghi nhận checkpoint khi lưu thất bại"
    checkpoints_dir = run_dir / "checkpoints"
    assert list(checkpoints_dir.glob("*.pt")) == [], "Không có tệp .pt nào được tạo thành công"


def test_interrupt_marks_interrupted(tmp_path: Path) -> None:
    """FR-015, AC-1: Tín hiệu ngắt SIGINT thoát với mã 130 và hồ sơ chuyển thành 'interrupted'.

    Khởi chạy CLI huấn luyện qua tiến trình con thực tế và gửi tín hiệu SIGINT trong lúc chạy:
    - Tiến trình con kết thúc với mã thoát 130 (chuẩn UNIX khi bị ngắt bởi Ctrl-C).
    - Thông điệp trên stderr xác nhận bị ngắt bởi người dùng.
    - Hồ sơ thí nghiệm manifest.json chuyển sang trạng thái 'interrupted'.
    """
    pytest.importorskip("torch", reason="Cần PyTorch để thực thi huấn luyện")

    # Cấu hình số bước lớn (100000) để tiến trình có đủ thời gian chạy vòng lặp huấn luyện
    config_file = smoke_config(
        tmp_path,
        total_timesteps=100000,
        n_steps=2048,
    )
    runs_dir = tmp_path / "runs"

    cmd = [
        sys.executable,
        "-m",
        "mma_ai.learning.cli",
        "--stage",
        "elbow",
        "--config",
        str(config_file),
    ]

    clean_env = os.environ.copy()
    clean_env.pop("DISPLAY", None)
    clean_env.pop("WAYLAND_DISPLAY", None)

    proc = subprocess.Popen(
        cmd,
        env=clean_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(Path.cwd()),
    )

    # Đợi thư mục lượt chạy và tệp manifest.json ban đầu xuất hiện
    run_dir: Path | None = None
    deadline = time.time() + 20.0
    while time.time() < deadline:
        runs = list_runs(runs_dir)
        if runs:
            candidate = runs[-1] / "manifest.json"
            if candidate.is_file():
                run_dir = runs[-1]
                break
        time.sleep(0.1)

    assert run_dir is not None, "Tiến trình huấn luyện không tạo được thư mục lượt chạy kịp thời"

    # Đợi thêm 1.5 giây để tiến trình bước vào vòng lặp thu mẫu huấn luyện
    time.sleep(1.5)

    # Gửi tín hiệu SIGINT (tương đương Ctrl-C từ bàn phím)
    proc.send_signal(signal.SIGINT)

    try:
        stdout, stderr = proc.communicate(timeout=15.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        pytest.fail(f"Tiến trình huấn luyện không dừng kịp thời sau SIGINT. Stderr: {stderr}")

    # 1. Khẳng định mã thoát dòng lệnh là 130
    assert proc.returncode == 130, (
        f"Kỳ vọng mã thoát 130 sau khi nhận SIGINT nhưng nhận {proc.returncode}.\nStderr: {stderr}"
    )

    # 2. Khẳng định stderr có thông điệp ngắt bởi người dùng
    assert "Huấn luyện bị ngắt bởi người dùng (Ctrl-C)." in stderr, (
        f"Thiếu thông báo ngắt trong stderr: {stderr}"
    )

    # 3. Khẳng định hồ sơ manifest.json chuyển sang trạng thái 'interrupted'
    manifest = load_manifest(run_dir)
    assert manifest["status"] == "interrupted", (
        f"Trạng thái trong hồ sơ manifest phải là 'interrupted': {manifest.get('status')}"
    )
