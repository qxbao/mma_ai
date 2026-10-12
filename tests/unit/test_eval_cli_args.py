"""Kiểm thử đơn vị cho giao diện dòng lệnh đánh giá cli.py (CLI-004, CMD-EVL-0001).

Bao phủ và kiểm chứng toàn diện các yêu cầu chức năng, bất biến và hợp đồng:
- FR-001, CMD-EVL-0001: Lệnh CLI đánh giá điểm kiểm tra (checkpoint) với các tham số hợp lệ.
- FR-007, INV-006: Tuyệt đối không có cờ ghi đè tiêu chí kết luận (criterion) hay mức tin cậy.
- FR-015, AC-5: Xử lý lỗi điểm kiểm tra không dùng được (mã 4), không in chỉ số trên stdout.
- FR-018: Quản lý tham số dòng lệnh và chuyển tiếp cấu hình ghi đè hợp lệ.
- INV-003: Tuyệt đối không có cờ nhận hành động mô phỏng hay toạ độ mục tiêu tay từ người dùng.
- INV-004: Thoát mã lỗi chuẩn xác khi có ngoại lệ và không in kết quả giả mạo trên stdout.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mma_ai.evaluation.cli import _build_parser, main
from mma_ai.evaluation.errors import (
    CheckpointUnusable,
    EvalConfigError,
    EvalWriteError,
    LeakageError,
    TrainSetUnknown,
)
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.runner import EvalResult
from mma_ai.evaluation.stats import Verdict


def test_006_inv_005_ac_4_main_configures_utf8_before_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """006 INV-005 AC-4: CLI cấu hình UTF-8 trước khi phân tích tham số."""
    events: list[str] = []

    class Parser:
        def parse_args(self, args: list[str] | None) -> None:
            events.append("parse")
            raise SystemExit(2)

    monkeypatch.setattr(
        "mma_ai.evaluation.cli.ensure_utf8_stdio",
        lambda: events.append("utf8"),
        raising=False,
    )
    monkeypatch.setattr("mma_ai.evaluation.cli._build_parser", lambda: Parser())

    assert main(["--unknown"]) == 2
    assert events == ["utf8", "parse"]


def test_no_criterion_override_flag() -> None:
    """FR-007, INV-003, INV-006: Kiểm tra không có cờ ghi đè tiêu chí kết luận hay hành động."""
    parser = _build_parser()
    actions = parser._actions
    all_flags = {flag for action in actions for flag in action.option_strings}

    # Bất biến INV-006: Cấm mọi cờ ghi đè tiêu chí kết luận
    forbidden_criterion_flags = {
        "--criterion",
        "--confidence-level",
        "--primary-metric",
        "--rule",
        "--alpha",
    }
    for flag in forbidden_criterion_flags:
        assert flag not in all_flags, f"Phát hiện cờ bị cấm theo INV-006: {flag}"

    # Bất biến INV-003: Cấm mọi cờ nhận hành động hay toạ độ tay
    forbidden_action_flags = {
        "--action",
        "--actions",
        "--target-pos",
        "--hand-pos",
        "--force",
        "--ctrl",
    }
    for flag in forbidden_action_flags:
        assert flag not in all_flags, f"Phát hiện cờ bị cấm theo INV-003: {flag}"

    # Chỉ cho phép đúng 6 cờ cấu hình và cờ trợ giúp --help
    allowed_flags = {
        "-h",
        "--help",
        "--checkpoint",
        "--config",
        "--out",
        "--repeats",
        "--eval-seed",
        "--runs-dir",
    }
    assert all_flags == allowed_flags, (
        f"Danh sách cờ không khớp quy định hợp đồng: {all_flags.difference(allowed_flags)}"
    )


def test_missing_checkpoint_arg_exit2(capsys: pytest.CaptureFixture[str]) -> None:
    """FR-001, FR-018, CMD-EVL-0001: Thiếu tham số bắt buộc --checkpoint phải thoát mã 2."""
    # Gọi main không truyền tham số
    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "checkpoint" in captured.err.lower() or "bắt buộc" in captured.err.lower()
    # Không được in chỉ số nào ra stdout
    assert "chỉ số" not in captured.out.lower()
    assert "kết luận" not in captured.out.lower()


def test_error_exit_code_and_no_metrics_on_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    """FR-015, INV-004, AC-5: Các lỗi nghiệp vụ trả mã thoát tương ứng và không in chỉ số."""
    error_cases = [
        (CheckpointUnusable("Checkpoint bị hỏng cấu trúc (corrupted)"), 4),
        (EvalConfigError("Cấu hình số lần lặp không hợp lệ"), 2),
        (LeakageError("Rò rỉ tập mục tiêu huấn luyện"), 5),
        (TrainSetUnknown("Không tìm thấy manifest.json của run"), 5),
        (EvalWriteError("Không có quyền ghi vào thư mục eval"), 7),
        (RuntimeError("Lỗi hệ thống không lường trước"), 1),
    ]

    for err_instance, expected_code in error_cases:
        with patch("mma_ai.evaluation.cli.evaluate_checkpoint", side_effect=err_instance):
            exit_code = main(["--checkpoint", "dummy_run/checkpoints/latest.pt"])
            captured = capsys.readouterr()

            assert exit_code == expected_code, (
                f"Lỗi {type(err_instance).__name__} phải có mã thoát "
                f"{expected_code}, nhận được {exit_code}"
            )
            # Thông điệp lỗi phải nằm trên stderr và nêu rõ ngữ cảnh
            assert str(err_instance) in captured.err
            # Tuyệt đối không in bất kỳ chỉ số hay tóm tắt kết quả nào ra stdout
            assert "kết luận" not in captured.out.lower()
            assert "tỷ lệ thành công" not in captured.out.lower()
            assert "success_rate" not in captured.out.lower()


def test_keyboard_interrupt_exit130(capsys: pytest.CaptureFixture[str]) -> None:
    """INV-004, CMD-EVL-0001: Người dùng ngắt bằng Ctrl-C (KeyboardInterrupt) phải thoát mã 130."""
    with patch("mma_ai.evaluation.cli.evaluate_checkpoint", side_effect=KeyboardInterrupt):
        exit_code = main(["--checkpoint", "dummy_run/checkpoints/latest.pt"])
        captured = capsys.readouterr()

        assert exit_code == 130
        assert "ngắt" in captured.err.lower() or "ctrl-c" in captured.err.lower()
        assert captured.out == ""


def test_successful_evaluation_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-001, FR-013, CMD-EVL-0001: Đánh giá thành công in tóm tắt trên stdout và thoát 0."""
    mock_report: dict[str, Any] = {
        "status": "done",
        "eval_id": "20261010T120000Z_e12345",
        "limits": [
            "50 episode mỗi chính sách: khoảng tin cậy của hiệu rộng xấp xỉ 0.34.",
            "Kết luận chỉ áp dụng cho checkpoint này.",
        ],
        "policies": {
            "learned": {
                "success_rate": {"value": 0.8, "ci_low": 0.65, "ci_high": 0.90},
                "final_distance_m": {"value": 0.025, "ci_low": 0.018, "ci_high": 0.032},
                "mean_return": {"value": 85.5, "ci_low": 75.0, "ci_high": 92.0},
                "effort": {"value": 0.35, "ci_low": 0.30, "ci_high": 0.40},
                "abnormal_rate": {"value": 0.0, "ci_low": 0.0, "ci_high": 0.05},
            },
            "random": {
                "success_rate": {"value": 0.2, "ci_low": 0.10, "ci_high": 0.32},
                "final_distance_m": {"value": 0.120, "ci_low": 0.105, "ci_high": 0.138},
                "mean_return": {"value": 12.0, "ci_low": 8.0, "ci_high": 16.0},
                "effort": {"value": 0.50, "ci_low": 0.48, "ci_high": 0.52},
                "abnormal_rate": {"value": 0.0, "ci_low": 0.0, "ci_high": 0.05},
            },
        },
        "comparison": {
            "difference": 0.6,
            "ci_low": 0.42,
            "ci_high": 0.74,
            "confidence_level": 0.95,
            "better": True,
        },
    }

    mock_verdict = Verdict(
        better=True,
        difference=0.6,
        ci_low=0.42,
        ci_high=0.74,
        method="newcombe_wilson_hybrid",
    )

    eval_dir = tmp_path / "runs" / "run_001" / "eval" / "20261010T120000Z_e12345"
    eval_dir.mkdir(parents=True, exist_ok=True)

    mock_result = EvalResult(
        eval_dir=eval_dir,
        report=mock_report,
        charts_status="complete",
        status="done",
        exit_code=0,
        eval_id="20261010T120000Z_e12345",
        verdict=mock_verdict,
    )

    with patch("mma_ai.evaluation.cli.evaluate_checkpoint", return_value=mock_result):
        exit_code = main(["--checkpoint", "runs/run_001/checkpoints/latest.pt"])
        captured = capsys.readouterr()

        assert exit_code == 0
        assert captured.err == ""
        # Kiểm tra nội dung tóm tắt tiếng Việt trên stdout
        assert "kết quả đánh giá chính sách" in captured.out.lower()
        assert "tốt hơn" in captured.out.lower()
        assert "0.60" in captured.out or "0.6" in captured.out
        assert "0.42" in captured.out
        assert "0.74" in captured.out
        assert "chính sách đã học (learned policy)" in captured.out.lower()
        assert "chính sách ngẫu nhiên (random policy)" in captured.out.lower()
        assert "đường dẫn kết quả" in captured.out.lower()
        assert "giới hạn" in captured.out.lower()


def test_incomplete_charts_exit6(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-010, FR-011, AC-3: Thiếu biểu đồ vẫn lưu số, in cảnh báo ra stderr và thoát mã 6."""
    mock_report: dict[str, Any] = {
        "status": "done_charts_incomplete",
        "eval_id": "20261010T120000Z_e12345",
        "limits": ["Giới hạn đánh giá"],
        "charts": {
            "status": "incomplete",
            "reason": "Thiếu dữ liệu chuỗi loss và activation",
        },
        "policies": {
            "learned": {
                "success_rate": {"value": 0.5, "ci_low": 0.35, "ci_high": 0.65},
                "final_distance_m": {"value": 0.05, "ci_low": 0.04, "ci_high": 0.06},
                "mean_return": {"value": 50.0, "ci_low": 40.0, "ci_high": 60.0},
                "effort": {"value": 0.4, "ci_low": 0.35, "ci_high": 0.45},
                "abnormal_rate": {"value": 0.0, "ci_low": 0.0, "ci_high": 0.05},
            },
            "random": {
                "success_rate": {"value": 0.2, "ci_low": 0.1, "ci_high": 0.3},
                "final_distance_m": {"value": 0.1, "ci_low": 0.09, "ci_high": 0.11},
                "mean_return": {"value": 20.0, "ci_low": 15.0, "ci_high": 25.0},
                "effort": {"value": 0.5, "ci_low": 0.45, "ci_high": 0.55},
                "abnormal_rate": {"value": 0.0, "ci_low": 0.0, "ci_high": 0.05},
            },
        },
        "comparison": {
            "difference": 0.3,
            "ci_low": 0.1,
            "ci_high": 0.5,
            "confidence_level": 0.95,
            "better": True,
        },
    }

    eval_dir = tmp_path / "runs" / "run_001" / "eval" / "20261010T120000Z_e12345"
    eval_dir.mkdir(parents=True, exist_ok=True)

    mock_result = EvalResult(
        eval_dir=eval_dir,
        report=mock_report,
        charts_status="incomplete",
        status="done_charts_incomplete",
        exit_code=6,
        eval_id="20261010T120000Z_e12345",
        verdict=None,
    )

    with patch("mma_ai.evaluation.cli.evaluate_checkpoint", return_value=mock_result):
        exit_code = main(["--checkpoint", "runs/run_001/checkpoints/latest.pt"])
        captured = capsys.readouterr()

        assert exit_code == 6
        assert "thiếu dữ liệu chuỗi loss và activation" in captured.err.lower()
        # Vẫn in kết quả tóm tắt số liệu ra stdout
        assert "kết quả đánh giá chính sách" in captured.out.lower()


def test_cli_overrides_passed_to_config_load() -> None:
    """FR-018, API-EVL-0001: Các cờ tuỳ chọn được ánh xạ thành overrides cho EvalConfig.load."""
    mock_cfg = MagicMock(spec=EvalConfig)
    mock_result = MagicMock(spec=EvalResult)
    mock_result.exit_code = 0
    mock_result.eval_dir = Path("runs/test/eval/eval_001")
    mock_result.eval_id = "eval_001"
    mock_result.status = "done"
    mock_result.report = {"limits": [], "policies": {}, "comparison": {}}

    with (
        patch("mma_ai.evaluation.cli.EvalConfig.load", return_value=mock_cfg) as mock_load,
        patch("mma_ai.evaluation.cli.evaluate_checkpoint", return_value=mock_result) as mock_eval,
    ):
            exit_code = main(
                [
                    "--checkpoint",
                    "runs/test/checkpoints/latest.pt",
                    "--config",
                    "configs/my_eval.yaml",
                    "--out",
                    "custom_out_dir",
                    "--repeats",
                    "5",
                    "--eval-seed",
                    "9999",
                    "--runs-dir",
                    "custom_runs",
                ]
            )

            assert exit_code == 0
            mock_load.assert_called_once_with(
                path="configs/my_eval.yaml",
                overrides={
                    "episodes.repeats": 5,
                    "seeds.episode_base": 9999,
                    "paths.runs_dir": "custom_runs",
                },
            )
            mock_eval.assert_called_once_with(
                checkpoint="runs/test/checkpoints/latest.pt",
                cfg=mock_cfg,
                out_dir="custom_out_dir",
            )


def test_cli_no_training_imports() -> None:
    """FR-014, INV-005: Kiểm tra cli.py không nhập learning.trainer hay learning.ppo."""
    cli_path = Path(__file__).parents[2] / "src" / "mma_ai" / "evaluation" / "cli.py"
    assert cli_path.is_file(), "Tệp cli.py phải tồn tại"

    code = cli_path.read_text(encoding="utf-8")
    tree = ast.parse(code, filename=str(cli_path))

    forbidden_modules = {
        "mma_ai.learning.trainer",
        "mma_ai.learning.ppo",
        "learning.trainer",
        "learning.ppo",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_modules, (
                    f"cli.py không được phép nhập '{alias.name}'"
                )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert mod not in forbidden_modules, f"cli.py không được phép nhập từ '{mod}'"
