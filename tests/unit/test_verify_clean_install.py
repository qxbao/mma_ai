"""Kiểm thử đơn vị cho quy trình xác minh cài đặt môi trường sạch (verify_clean_install).

Chứng minh các yêu cầu và bất biến:
- AC-5: Cài đặt và kiểm thử trong môi trường ảo sạch, có nhật ký logs/m1/verify_clean_install.json.
- NFR-INST-001: uv sync --frozen và bộ test môi trường xanh trong môi trường ảo mới.
- FR-016: Không tự giả định tương thích, khoá phụ thuộc và xác minh cài đặt sạch.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from mma_ai.environment.verify_clean_install import main


class MockRunner:
    """Bộ chạy lệnh giả lập (mock command runner) có thể tiêm vào quy trình xác minh."""

    def __init__(self, sync_exit: int = 0, pytest_exit: int = 0) -> None:
        self.sync_exit = sync_exit
        self.pytest_exit = pytest_exit
        self.executed_commands: list[list[str]] = []

    def __call__(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> int:
        self.executed_commands.append(cmd)
        cmd_str = " ".join(cmd)
        if "sync" in cmd_str:
            return self.sync_exit
        if "pytest" in cmd_str:
            return self.pytest_exit
        return 0


def test_record_has_all_fields(tmp_path: Path) -> None:
    """AC-5, NFR-INST-001, FR-016: Bản ghi JSON có đủ các trường yêu cầu khi cả hai bước đạt."""
    # Chuẩn bị thư mục dự án giả lập có tệp uv.lock
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "uv.lock").write_text("# lockfile\n", encoding="utf-8")
    (project_root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")

    output_path = project_root / "logs" / "m1" / "verify_clean_install.json"
    mock_runner = MockRunner(sync_exit=0, pytest_exit=0)

    exit_code = main(
        argv=[],
        runner=mock_runner,
        project_root=project_root,
        output_path=output_path,
    )

    assert exit_code == 0, "Mã thoát phải là 0 khi cả hai bước uv sync và pytest đều thành công"
    assert output_path.is_file(), f"Phải ghi tệp bản ghi tại {output_path}"

    with output_path.open("r", encoding="utf-8") as f:
        record: dict[str, Any] = json.load(f)

    # Khẳng định có đầy đủ các trường cốt lõi theo đặc tả
    assert "commands_run" in record, "Bản ghi phải có trường commands_run"
    assert isinstance(record["commands_run"], list)
    assert len(record["commands_run"]) >= 2, "commands_run phải có ít nhất lệnh sync và pytest"

    assert "python_version" in record, "Bản ghi phải có trường python_version"
    assert isinstance(record["python_version"], str) and len(record["python_version"]) > 0

    assert "exit_codes" in record or "step_exit_codes" in record
    step_codes = record.get("exit_codes") or record.get("step_exit_codes")
    assert isinstance(step_codes, dict)
    assert step_codes.get("sync") == 0
    assert step_codes.get("pytest") == 0

    assert "installed_versions" in record or "libraries" in record
    versions = record.get("installed_versions") or record.get("libraries")
    assert isinstance(versions, dict)
    for pkg in ["gymnasium", "mujoco", "myo-sim", "numpy"]:
        assert pkg in versions, f"Thiếu phiên bản gói bắt buộc: {pkg}"
        assert isinstance(versions[pkg], str) and len(versions[pkg]) > 0

    assert "duration_seconds" in record or "duration_s" in record, "Bản ghi phải có thời lượng"
    duration = record.get("duration_seconds", record.get("duration_s"))
    assert isinstance(duration, (int, float)) and duration >= 0


def test_exit_nonzero_when_sync_fails(tmp_path: Path) -> None:
    """AC-5, NFR-INST-001, FR-016: Thoát mã khác 0 khi bước uv sync thất bại, không chạy pytest."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "uv.lock").write_text("# lockfile\n", encoding="utf-8")

    output_path = project_root / "logs" / "m1" / "verify_clean_install.json"
    mock_runner = MockRunner(sync_exit=1, pytest_exit=0)

    exit_code = main(
        argv=[],
        runner=mock_runner,
        project_root=project_root,
        output_path=output_path,
    )

    assert exit_code != 0, "Mã thoát phải khác 0 khi uv sync thất bại"

    # Kiểm tra lệnh đã thực thi: không được gọi pytest khi sync thất bại
    executed = [" ".join(c) for c in mock_runner.executed_commands]
    assert any("sync" in c for c in executed), "Phải gọi lệnh sync"
    assert not any("pytest" in c for c in executed), "Không được gọi pytest khi sync đã thất bại"

    # Tệp nhật ký vẫn phải ghi nhận thất bại
    assert output_path.is_file(), "Vẫn phải ghi nhật ký thất bại để làm bằng chứng"
    with output_path.open("r", encoding="utf-8") as f:
        record = json.load(f)
    step_codes = record.get("exit_codes") or record.get("step_exit_codes", {})
    assert step_codes.get("sync") == 1


def test_exit_nonzero_when_pytest_fails(tmp_path: Path) -> None:
    """AC-5, NFR-INST-001, FR-016: Thoát mã khác 0 khi uv sync thành công nhưng pytest thất bại."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "uv.lock").write_text("# lockfile\n", encoding="utf-8")

    output_path = project_root / "logs" / "m1" / "verify_clean_install.json"
    mock_runner = MockRunner(sync_exit=0, pytest_exit=2)

    exit_code = main(
        argv=[],
        runner=mock_runner,
        project_root=project_root,
        output_path=output_path,
    )

    assert exit_code != 0, "Mã thoát phải khác 0 khi pytest thất bại (chỉ 0 khi cả hai bước mã 0)"

    with output_path.open("r", encoding="utf-8") as f:
        record = json.load(f)
    step_codes = record.get("exit_codes") or record.get("step_exit_codes", {})
    assert step_codes.get("sync") == 0
    assert step_codes.get("pytest") == 2


def test_refuses_without_lockfile(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-5, NFR-INST-001, FR-016: Từ chối chạy khi thiếu tệp uv.lock kèm thông báo tiếng Việt."""
    project_root = tmp_path / "project_no_lock"
    project_root.mkdir()
    # Không tạo tệp uv.lock

    mock_runner = MockRunner(sync_exit=0, pytest_exit=0)

    exit_code = main(
        argv=[],
        runner=mock_runner,
        project_root=project_root,
    )

    assert exit_code != 0, "Phải từ chối chạy (mã thoát khác 0) khi thiếu uv.lock"
    assert len(mock_runner.executed_commands) == 0, "Không được chạy lệnh nào khi thiếu uv.lock"

    captured = capsys.readouterr()
    combined_output = captured.out + captured.err
    # Thông báo tiếng Việt nêu lý do thiếu uv.lock
    assert "uv.lock" in combined_output, "Thông báo phải nhắc đến tệp uv.lock"
    assert any(
        kw in combined_output.lower()
        for kw in ["không tìm thấy", "thiếu", "từ chối", "khóa", "khoá"]
    ), f"Thông báo phải bằng tiếng Việt nêu lý do, nhận được: {combined_output}"


def test_record_paths_relative(tmp_path: Path) -> None:
    """AC-5, NFR-INST-001, FR-016: Toàn bộ đường dẫn trong JSON phải là đường dẫn tương đối."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "uv.lock").write_text("# lockfile\n", encoding="utf-8")

    output_path = project_root / "logs" / "m1" / "verify_clean_install.json"
    mock_runner = MockRunner(sync_exit=0, pytest_exit=0)

    exit_code = main(
        argv=[],
        runner=mock_runner,
        project_root=project_root,
        output_path=output_path,
    )
    assert exit_code == 0

    with output_path.open("r", encoding="utf-8") as f:
        record = json.load(f)

    # Đệ quy kiểm tra mọi giá trị chuỗi trong bản ghi không được là đường dẫn tuyệt đối
    def assert_no_absolute_paths(obj: Any, key_path: str = "") -> None:
        if isinstance(obj, str):
            # Không bắt đầu bằng dấu gạch chéo Unix tuyệt đối
            assert not obj.startswith("/"), (
                f"Phát hiện đường dẫn tuyệt đối tại '{key_path}': {obj}"
            )
            # Không phải đường dẫn tuyệt đối hệ thống
            assert not Path(obj).is_absolute(), (
                f"Phát hiện đường dẫn tuyệt đối tại '{key_path}': {obj}"
            )
        elif isinstance(obj, dict):
            for k, v in obj.items():
                assert_no_absolute_paths(v, f"{key_path}.{k}" if key_path else str(k))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                assert_no_absolute_paths(item, f"{key_path}[{i}]")

    assert_no_absolute_paths(record)
