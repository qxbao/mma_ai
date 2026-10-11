"""Kiểm thử tham số dòng lệnh và quy trình điều phối CLI huấn luyện (test_train_cli_args.py).

Hiện thực các bài kiểm thử xác nhận hợp đồng CMD-TRN-0001 và các bất biến:
- FR-001: Huấn luyện PPO trên mô hình cánh tay khuỷu (ElbowReachEnv).
- FR-009: Tiếp tục huấn luyện từ điểm kiểm tra (checkpoint resume).
- FR-013: Báo cáo thông lượng môi trường (env steps/second) và thời gian thực (wall-clock).
- FR-015: Ánh xạ mã thoát (exit code) chuẩn xác theo hợp đồng cli.md.
- FR-018: Quản lý cấu hình huấn luyện và áp dụng ghi đè (overrides) từ tham số dòng lệnh.
- FR-020: Khởi chạy giao diện quan sát ở tiến trình riêng biệt khi bật tuỳ chọn web.
- FR-022: Tuỳ chọn hiển thị 3D không ảnh hưởng đến tính chất chạy không màn hình (headless).
- FR-023: Khả năng cấu hình tham số đo đạc hiệu năng.
- INV-002: Bất biến không gian hành động — nghiêm cấm cờ nhận lực hay toạ độ tay từ CLI.
- INV-005: Tính độc lập của giao diện quan sát — lỗi giao diện không làm dừng huấn luyện.
"""

from __future__ import annotations

import importlib.util
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

import mma_ai.learning.cli as cli
from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.learning.cli import main
from mma_ai.learning.errors import CheckpointIOError, NonFiniteError


def test_regress_tdd_red_train_cli_module_is_present() -> None:
    """FR-015, CMD-TRN-0001: Khẳng định độc lập mô-đun learning.cli tồn tại trên base."""
    assert importlib.util.find_spec("mma_ai.learning.cli") is not None


class _DummyEnv:
    """Môi trường giả lập cho kiểm thử CLI không phụ thuộc MuJoCo."""

    def __init__(self) -> None:
        self.split = "train"
        self.model_sha256 = "dummy_sha256"

    def model_record(self) -> dict[str, Any]:
        return {
            "xml_sha256": "dummy_sha256",
            "muscle_names": ["m1", "m2", "m3", "m4", "m5", "m6"],
        }


@dataclass(frozen=True)
class _DummyRunResult:
    run_id: str
    status: str
    env_steps: int
    n_updates: int
    wall_clock_seconds: float
    env_steps_per_second: float
    checkpoints: list[Any]
    manifest_path: Path


def _make_dummy_result(run_dir_path: Path) -> _DummyRunResult:
    """Tạo kết quả huấn luyện giả lập đáp ứng hợp đồng RunResult."""
    return _DummyRunResult(
        run_id="20261010T000000Z_elbow_s42",
        status="done",
        env_steps=4096,
        n_updates=2,
        wall_clock_seconds=5.25,
        env_steps_per_second=780.19,
        checkpoints=[],
        manifest_path=run_dir_path / "manifest.json",
    )


def test_stage_unknown_exit3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-015, CMD-TRN-0001: Stage chưa triển khai phải thoát mã 3 và không tạo thư mục run."""
    monkeypatch.chdir(tmp_path)
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(["--stage", "balance", "--runs-dir", "runs"])
    captured = capsys.readouterr()

    assert exit_code == 3
    assert "chưa triển khai: stage 'balance' (M1 chỉ hỗ trợ 'elbow')" in captured.err
    # Khẳng định không tạo bất kỳ thư mục run nào
    assert list(runs_dir.iterdir()) == []

    # Thử nghiệm thêm với stage locomotion
    exit_code_loco = main(["--stage", "locomotion", "--runs-dir", "runs"])
    captured_loco = capsys.readouterr()
    assert exit_code_loco == 3
    assert "chưa triển khai: stage 'locomotion' (M1 chỉ hỗ trợ 'elbow')" in captured_loco.err
    assert list(runs_dir.iterdir()) == []


def test_invalid_config_exit2_before_run_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-018, CMD-TRN-0001: Cấu hình sai thoát mã 2 trước khi tạo thư mục run."""
    monkeypatch.chdir(tmp_path)
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    bad_config_file = tmp_path / "bad_config.yaml"
    bad_config_file.write_text("stage: invalid_root_keys\n", encoding="utf-8")

    exit_code = main([
        "--stage", "elbow",
        "--config", str(bad_config_file),
        "--runs-dir", "runs",
    ])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Cấu hình" in captured.err or "lỗi" in captured.err.lower()
    # Khẳng định tuyệt đối không có thư mục run nào được tạo ra
    assert list(runs_dir.iterdir()) == []


def test_overrides_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-001, FR-018, CMD-TRN-0001: Các cờ dòng lệnh ghi đè chính xác vào cấu hình huấn luyện."""
    monkeypatch.chdir(tmp_path)
    captured_cfg: list[Any] = []

    class MockTrainer:
        def __init__(self, cfg: Any, env: Any, run_dir: Any, **kwargs: Any) -> None:
            captured_cfg.append(cfg)
            self.run_dir = run_dir

        def run(self) -> _DummyRunResult:
            return _make_dummy_result(self.run_dir.path)

    monkeypatch.setattr(cli, "Trainer", MockTrainer)
    monkeypatch.setattr(cli, "make_env", lambda **kwargs: _DummyEnv())

    exit_code = main([
        "--stage", "elbow",
        "--seed", "12345",
        "--total-steps", "4096",
        "--runs-dir", "runs_custom",
        "--ui", "none",
        "--ui-port", "9090",
        "--view3d",
    ])

    assert exit_code == 0
    assert len(captured_cfg) == 1
    cfg = captured_cfg[0]

    assert cfg.seed == 12345
    assert cfg.schedule.total_timesteps == 4096
    assert cfg.paths.runs_dir == "runs_custom"
    assert cfg.ui.mode == "none"
    assert cfg.ui.port == 9090
    assert cfg.ui.view3d is True


def test_ui_none_does_not_spawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-020, INV-005: Tuỳ chọn --ui none tuyệt đối không khởi chạy tiến trình quan sát."""
    monkeypatch.chdir(tmp_path)
    mock_popen = MagicMock()
    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    class MockTrainer:
        def __init__(self, cfg: Any, env: Any, run_dir: Any, **kwargs: Any) -> None:
            self.run_dir = run_dir

        def run(self) -> _DummyRunResult:
            return _make_dummy_result(self.run_dir.path)

    monkeypatch.setattr(cli, "Trainer", MockTrainer)
    monkeypatch.setattr(cli, "make_env", lambda **kwargs: _DummyEnv())

    exit_code = main([
        "--stage", "elbow",
        "--runs-dir", "runs",
        "--ui", "none",
    ])

    assert exit_code == 0
    mock_popen.assert_not_called()


def test_ui_spawn_failure_warns_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-020, INV-005: Giao diện thất bại phải in cảnh báo nhưng train vẫn tiếp tục."""
    monkeypatch.chdir(tmp_path)

    def _failing_popen(*args: Any, **kwargs: Any) -> Any:
        raise OSError("Không thể tạo tiến trình giao diện con")

    monkeypatch.setattr(subprocess, "Popen", _failing_popen)

    trainer_called = False

    class MockTrainer:
        def __init__(self, cfg: Any, env: Any, run_dir: Any, **kwargs: Any) -> None:
            self.run_dir = run_dir

        def run(self) -> _DummyRunResult:
            nonlocal trainer_called
            trainer_called = True
            return _make_dummy_result(self.run_dir.path)

    monkeypatch.setattr(cli, "Trainer", MockTrainer)
    monkeypatch.setattr(cli, "make_env", lambda **kwargs: _DummyEnv())

    exit_code = main([
        "--stage", "elbow",
        "--runs-dir", "runs",
        "--ui", "web",
    ])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert trainer_called is True
    assert "Cảnh báo" in captured.err or "giao diện quan sát" in captured.err


def test_inv002_forbidden_action_flags_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    """INV-002: Bất biến không gian hành động — nghiêm cấm cờ nhận lực, toạ độ hay hành động."""
    for forbidden_flag in ["--action", "--force", "--coord", "--hand-target"]:
        exit_code = main(["--stage", "elbow", forbidden_flag, "0.5"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "unrecognized" in captured.err.lower() or "không hợp lệ" in captured.err.lower()


def test_resume_checkpoint_invalid_exit4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-009, FR-015, CMD-TRN-0001: Nạp điểm kiểm tra không tồn tại hoặc lỗi phải thoát mã 4."""
    monkeypatch.chdir(tmp_path)
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    nonexistent_ckpt = tmp_path / "nonexistent.pt"

    exit_code = main([
        "--stage", "elbow",
        "--resume", str(nonexistent_ckpt),
        "--runs-dir", "runs",
        "--ui", "none",
    ])
    captured = capsys.readouterr()

    assert exit_code == 4
    assert "checkpoint" in captured.err.lower() or "điểm kiểm tra" in captured.err.lower()
    assert list(runs_dir.iterdir()) == []


def test_training_errors_exit1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-015, CMD-TRN-0001: Lỗi NaN/Inf hay mất ổn định vật lý phải trả về mã thoát 1."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "make_env", lambda **kwargs: _DummyEnv())

    exceptions: list[Exception] = [
        NonFiniteError("Phát hiện NaN trong loss"),
        PhysicsInstabilityError("Mô phỏng mất ổn định"),
        CheckpointIOError("Lỗi ghi đĩa"),
    ]
    for exc in exceptions:
        class FailingTrainer:
            def __init__(self, cfg: Any, env: Any, run_dir: Any, **kwargs: Any) -> None:
                pass

            def run(self) -> _DummyRunResult:
                raise exc

        monkeypatch.setattr(cli, "Trainer", FailingTrainer)

        exit_code = main([
            "--stage", "elbow",
            "--runs-dir", "runs",
            "--ui", "none",
        ])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "Lỗi" in captured.err or "lỗi" in captured.err


def test_keyboard_interrupt_exit130(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-015, CMD-TRN-0001: Ngắt tín hiệu bàn phím (Ctrl-C) phải trả về mã thoát 130."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "make_env", lambda **kwargs: _DummyEnv())

    class InterruptedTrainer:
        def __init__(self, cfg: Any, env: Any, run_dir: Any, **kwargs: Any) -> None:
            pass

        def run(self) -> _DummyRunResult:
            raise KeyboardInterrupt()

    monkeypatch.setattr(cli, "Trainer", InterruptedTrainer)

    exit_code = main([
        "--stage", "elbow",
        "--runs-dir", "runs",
        "--ui", "none",
    ])
    captured = capsys.readouterr()

    assert exit_code == 130
    assert "ngắt" in captured.err.lower() or "ctrl-c" in captured.err.lower()


def test_report_stdout_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-013, FR-023, CMD-TRN-0001: Báo cáo env steps/s, wall-clock và URL trên stdout."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "make_env", lambda **kwargs: _DummyEnv())

    class MockTrainer:
        def __init__(self, cfg: Any, env: Any, run_dir: Any, **kwargs: Any) -> None:
            self.run_dir = run_dir

        def run(self) -> _DummyRunResult:
            return _make_dummy_result(self.run_dir.path)

    monkeypatch.setattr(cli, "Trainer", MockTrainer)

    exit_code = main([
        "--stage", "elbow",
        "--runs-dir", "runs",
        "--ui", "none",
    ])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "env steps/second" in captured.out
    assert "wall-clock" in captured.out
    assert "Giao diện quan sát" in captured.out or "URL" in captured.out
