"""Kiểm thử đơn vị cho CLI giao diện quan sát huấn luyện (test_watch_cli.py).

Hiện thực và bảo vệ các yêu cầu:
- CMD-TRN-0002: Lệnh quan sát huấn luyện CLI với các cờ --run, --port, --view3d.
- FR-020: Khởi chạy máy chủ HTTP giao diện quan sát tiến trình thời gian thực.
- FR-021: Giao diện chỉ-đọc; ui.json là tệp duy nhất được phép ghi vào thư mục run.
- FR-022: Hiển thị 3D (--view3d) mặc định tắt, khi bật thì chạy ở tiến trình riêng.
- INV-005: Giao diện quan sát chỉ đọc dữ liệu huấn luyện, không nhập learning.trainer
  hoặc learning.ppo.
"""

from __future__ import annotations

import ast
import json
import os
import socket
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mma_ai.monitoring import cli


def test_no_training_imports() -> None:
    """INV-005, FR-021: CLI quan sát tuyệt đối không nhập learning.trainer hoặc learning.ppo."""
    cli_path = Path(cli.__file__).resolve()
    tree = ast.parse(cli_path.read_text(encoding="utf-8"), filename=str(cli_path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                assert "learning.trainer" not in name, (
                    f"INV-005: Nghiêm cấm nhập learning.trainer tại {cli_path}"
                )
                assert "learning.ppo" not in name, (
                    f"INV-005: Nghiêm cấm nhập learning.ppo tại {cli_path}"
                )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert "learning.trainer" not in mod, (
                f"INV-005: Nghiêm cấm nhập từ learning.trainer tại {cli_path}"
            )
            assert "learning.ppo" not in mod, (
                f"INV-005: Nghiêm cấm nhập từ learning.ppo tại {cli_path}"
            )

    # Khẳng định trên môi trường runtime sys.modules
    assert "mma_ai.learning.trainer" not in sys.modules, (
        "INV-005: Module mma_ai.learning.trainer không được có mặt trong sys.modules"
    )
    assert "mma_ai.learning.ppo" not in sys.modules, (
        "INV-005: Module mma_ai.learning.ppo không được có mặt trong sys.modules"
    )


def test_writes_ui_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """FR-020, FR-021, CMD-TRN-0002, INV-005: Ghi ui.json {url, pid} vào thư mục run và in URL."""
    run_dir = tmp_path / "run_test_001"
    run_dir.mkdir(parents=True)

    # Chuẩn bị stop_event để dừng vòng lặp phục vụ ngay sau khi máy chủ sẵn sàng
    stop_event = threading.Event()
    stop_event.set()

    exit_code = cli.main(
        ["--run", str(run_dir), "--port", "0"],
        stop_event=stop_event,
    )
    assert exit_code == 0, f"CLI phải thoát mã 0 khi kết thúc bình thường, nhận {exit_code}"

    # 1. Kiểm tra tệp ui.json tồn tại trong thư mục run
    ui_json_path = run_dir / "ui.json"
    assert ui_json_path.is_file(), "ui.json phải được tạo trong thư mục run"

    data = json.loads(ui_json_path.read_text(encoding="utf-8"))
    assert "url" in data, "ui.json phải chứa trường 'url'"
    assert "pid" in data, "ui.json phải chứa trường 'pid'"
    assert data["url"].startswith("http://127.0.0.1:") or data["url"].startswith("http://localhost:")
    assert isinstance(data["pid"], int) and data["pid"] == os.getpid()

    # 2. INV-005, FR-021: ui.json là tệp duy nhất được phép ghi vào thư mục run
    created_files = [p.name for p in run_dir.iterdir()]
    assert created_files == ["ui.json"], (
        "INV-005: ui.json là tệp DUY NHẤT tiến trình giao diện được phép ghi, "
        f"thực tế có: {created_files}"
    )

    # 3. Kiểm tra URL được in ra stdout
    captured = capsys.readouterr()
    assert data["url"] in captured.out, "URL máy chủ phải được in ra stdout"


def test_006_ac_1_main_configures_utf8_before_argument_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """006 AC-1, AC-4: cấu hình UTF-8 trước khi CLI có thể phát thông báo lỗi."""
    configured: list[bool] = []
    monkeypatch.setattr(
        cli, "ensure_utf8_stdio", lambda: configured.append(True), raising=False
    )

    with pytest.raises(SystemExit):
        cli.main(["--unknown"])

    assert configured == [True]


def test_006_inv_003_atomic_ui_write_cleans_temporary_file_on_failure(
    tmp_path: Path,
) -> None:
    """006 INV-003, INV-005, AC-4: lỗi thay ui.json không để lại tệp tạm."""
    run_dir = tmp_path / "run_atomic_failure"
    run_dir.mkdir()
    stop_event = threading.Event()
    stop_event.set()

    with patch(
        "mma_ai.compat.fsio.replace_atomic", side_effect=OSError("lỗi giả lập")
    ):
        exit_code = cli.main(
            ["--run", str(run_dir), "--port", "0"], stop_event=stop_event
        )

    assert exit_code == 1
    assert sorted(path.name for path in run_dir.iterdir()) == []


def test_port_in_use_exits_nonzero_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CMD-TRN-0002, FR-020, INV-005: Cổng mạng bị chiếm thoát khác 0 và in thông báo tiếng Việt."""
    run_dir = tmp_path / "run_port_conflict"
    run_dir.mkdir(parents=True)

    # Chiếm trước một cổng mạng cục bộ
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    occupied_port = sock.getsockname()[1]

    try:
        exit_code = cli.main(["--run", str(run_dir), "--port", str(occupied_port)])
        assert exit_code != 0, "CLI phải trả về mã thoát khác 0 khi cổng bị chiếm"

        captured = capsys.readouterr()
        # Thông báo lỗi tiếng Việt phải nêu lý do ở stderr
        assert len(captured.err) > 0, "Lỗi cổng bị chiếm phải được ghi ra stderr"
        err_lower = captured.err.lower()
        assert any(keyword in err_lower for keyword in ["cổng", "port", "lỗi", "không thể"]), (
            f"Thông báo lỗi phải diễn giải bằng tiếng Việt rõ ràng: {captured.err}"
        )
    finally:
        sock.close()


def test_view3d_flag_off_by_default(tmp_path: Path) -> None:
    """FR-022, CMD-TRN-0002, INV-005: Cờ --view3d mặc định tắt và chỉ khởi chạy khi bật."""
    run_dir = tmp_path / "run_view3d"
    run_dir.mkdir(parents=True)

    stop_event = threading.Event()
    stop_event.set()

    with patch("multiprocessing.Process") as mock_process_cls:
        # Trường hợp 1: Không truyền cờ --view3d
        exit_code = cli.main(
            ["--run", str(run_dir), "--port", "0"],
            stop_event=stop_event,
        )
        assert exit_code == 0
        assert not mock_process_cls.called, (
            "FR-022: Khi không có cờ --view3d, không được tạo tiến trình View3D"
        )

    with patch("multiprocessing.Process") as mock_process_cls:
        mock_instance = MagicMock()
        mock_process_cls.return_value = mock_instance

        # Trường hợp 2: Có truyền cờ --view3d
        exit_code = cli.main(
            ["--run", str(run_dir), "--port", "0", "--view3d"],
            stop_event=stop_event,
        )
        assert exit_code == 0
        assert mock_process_cls.called, (
            "FR-022: Khi có cờ --view3d, phải khởi chạy View3D ở tiến trình riêng"
        )
        assert mock_instance.start.called, "Tiến trình View3D phải được gọi start()"


def test_missing_run_argument_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    """CMD-TRN-0002: Tham số --run là bắt buộc, thiếu sẽ thoát khác 0."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code != 0


def test_nonexistent_run_dir_exits_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CMD-TRN-0002: Thư mục run không tồn tại phải thoát khác 0 và thông báo tiếng Việt."""
    missing_dir = tmp_path / "khong_ton_tai"
    exit_code = cli.main(["--run", str(missing_dir)])
    assert exit_code != 0

    captured = capsys.readouterr()
    assert len(captured.err) > 0
    assert any(w in captured.err.lower() for w in ["không tồn tại", "thư mục", "lỗi"])


def test_keyboard_interrupt_handles_cleanly(tmp_path: Path) -> None:
    """CMD-TRN-0002, INV-005: Khi nhận KeyboardInterrupt (Ctrl-C), CLI đóng sạch và thoát 0."""
    run_dir = tmp_path / "run_ctrl_c"
    run_dir.mkdir(parents=True)

    with patch("time.sleep", side_effect=KeyboardInterrupt):
        exit_code = cli.main(["--run", str(run_dir), "--port", "0"])
        assert exit_code == 0, "KeyboardInterrupt phải được xử lý nhẹ nhàng và trả mã 0"


def test_ui_json_write_failure_exits_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """INV-005, FR-021: Lỗi ghi ui.json đóng máy chủ và thoát khác 0 kèm thông báo tiếng Việt."""
    run_dir = tmp_path / "run_write_err"
    run_dir.mkdir(parents=True)

    with patch(
        "mma_ai.compat.fsio.replace_atomic",
        side_effect=OSError("Lỗi ghi đĩa giả lập"),
    ):
        exit_code = cli.main(["--run", str(run_dir), "--port", "0"])
        assert exit_code != 0, "Lỗi ghi ui.json phải thoát khác 0"

        captured = capsys.readouterr()
        assert len(captured.err) > 0
        assert any(w in captured.err.lower() for w in ["lỗi", "ui.json", "ghi"])


def test_module_main_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """CMD-TRN-0002: Khối __main__ gọi main() và thoát sys.exit tương ứng."""
    monkeypatch.setattr(sys, "argv", ["mma_ai.monitoring.cli"])
    monkeypatch.delitem(sys.modules, "mma_ai.monitoring.cli", raising=False)
    import runpy

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("mma_ai.monitoring.cli", run_name="__main__")
    assert exc_info.value.code != 0
