"""Kiểm thử stage chưa triển khai qua CLI huấn luyện (T336).

Hiện thực và xác minh:
- FR-015, SC-005, AC-5, US7: CLI chỉ hỗ trợ stage 'elbow' ở M1; mọi stage khác
  ('balance', 'locomotion', 'selfplay', hay giá trị lạ) báo rõ "chưa triển khai",
  mã thoát 3 ra stderr.
- SC-005, AC-5: Không có thư mục run, không checkpoint, runs_dir không bị tạo khi stage
  chưa được triển khai.
"""

from __future__ import annotations

from pathlib import Path

from train_fixtures import list_runs, run_train_cli, smoke_config

from mma_ai.learning.cli import _build_parser


def test_red_stage_contract_independent_assertion() -> None:
    """FR-015, SC-005, AC-5: Khẳng định độc lập chứng minh cờ --stage tồn tại và mặc định elbow."""
    parser = _build_parser()
    actions = {action.dest: action for action in parser._actions}
    assert "stage" in actions, "CLI parser phải có tham số --stage"
    stage_action = actions["stage"]
    assert stage_action.default == "elbow", "Giá trị mặc định của --stage phải là 'elbow'"


def test_stage_not_implemented_exit3(tmp_path: Path) -> None:
    """AC-5, US7: --stage balance, locomotion, selfplay báo 'chưa triển khai' và thoát mã 3."""
    config_file = smoke_config(tmp_path)
    runs_dir = tmp_path / "runs"

    unimplemented_stages = ["balance", "locomotion", "selfplay"]
    for stage_name in unimplemented_stages:
        result = run_train_cli(
            ["--stage", stage_name, "--config", str(config_file)],
            timeout=30.0,
        )
        assert result.exit_code == 3, (
            f"Kỳ vọng mã thoát 3 cho stage '{stage_name}', nhận {result.exit_code}.\n"
            f"Stderr: {result.stderr}\nStdout: {result.stdout}"
        )
        expected_msg = f"chưa triển khai: stage '{stage_name}' (M1 chỉ hỗ trợ 'elbow')"
        assert expected_msg in result.stderr, (
            f"Stderr không chứa thông báo chuẩn cho stage '{stage_name}': {result.stderr}"
        )
        assert list_runs(runs_dir) == [], (
            f"Không được tạo thư mục run khi stage '{stage_name}' chưa triển khai"
        )


def test_unknown_stage_exit3(tmp_path: Path) -> None:
    """AC-5, US7: Giá trị stage lạ cũng báo 'chưa triển khai' và thoát mã 3."""
    config_file = smoke_config(tmp_path)
    runs_dir = tmp_path / "runs"

    unknown_stages = ["unknown_stage", "boxing", "kickboxing", "xyz_123"]
    for stage_name in unknown_stages:
        result = run_train_cli(
            ["--stage", stage_name, "--config", str(config_file)],
            timeout=30.0,
        )
        assert result.exit_code == 3, (
            f"Kỳ vọng mã thoát 3 cho stage lạ '{stage_name}', nhận {result.exit_code}.\n"
            f"Stderr: {result.stderr}"
        )
        expected_msg = f"chưa triển khai: stage '{stage_name}' (M1 chỉ hỗ trợ 'elbow')"
        assert expected_msg in result.stderr, (
            f"Stderr không chứa thông báo chuẩn cho stage lạ '{stage_name}': {result.stderr}"
        )
        assert list_runs(runs_dir) == [], (
            f"Không được tạo thư mục run khi stage lạ '{stage_name}' chưa triển khai"
        )


def test_no_run_dir_for_unimplemented(tmp_path: Path) -> None:
    """AC-5, US7: Không tạo thư mục run, không checkpoint khi stage chưa triển khai."""
    # Chỉ định đường dẫn runs_dir chưa tồn tại để kiểm tra không bị tạo
    custom_runs_dir = tmp_path / "non_existent_runs"
    assert not custom_runs_dir.exists(), "custom_runs_dir không được tồn tại trước khi chạy"

    result = run_train_cli(
        ["--stage", "balance", "--runs-dir", str(custom_runs_dir)],
        timeout=30.0,
    )

    assert result.exit_code == 3, f"Nhận mã thoát {result.exit_code}"
    assert not custom_runs_dir.exists(), (
        f"Thư mục runs_dir '{custom_runs_dir}' không được phép tạo khi stage chưa triển khai"
    )

    # Trường hợp thư mục runs_dir đã tồn tại từ trước thì không được chứa run con nào
    existing_runs_dir = tmp_path / "existing_runs"
    existing_runs_dir.mkdir(parents=True, exist_ok=True)
    result2 = run_train_cli(
        ["--stage", "locomotion", "--runs-dir", str(existing_runs_dir)],
        timeout=30.0,
    )
    assert result2.exit_code == 3, f"Nhận mã thoát {result2.exit_code}"
    assert list_runs(existing_runs_dir) == [], (
        "Không được tạo bất kỳ thư mục run hay checkpoint nào bên trong runs_dir"
    )
